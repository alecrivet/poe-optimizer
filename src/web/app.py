"""
Local web UI for poe-optimizer.

    poe-optimizer web            # starts on http://127.0.0.1:8765 and opens a browser

Serves a static single-page front end from ``src/web/static`` and a small
JSON API over the optimizer (see docs/plans/2026-09-frontend.md).
Loopback only; there is no auth and no multi-user handling by design.
"""

from __future__ import annotations

import json
import logging
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .jobs import JobOptions, JobRunner

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------- #
# Request models
# ---------------------------------------------------------------------- #

class BuildRequest(BaseModel):
    code: Optional[str] = None
    xml: Optional[str] = None
    account: Optional[str] = None
    character: Optional[str] = None
    poesessid: Optional[str] = None
    realm: str = "pc"


class AssumptionsRequest(BaseModel):
    disabled: list = []


class JobRequest(BaseModel):
    build_id: str
    objective: str = "dps"
    allow_point_change: bool = False
    max_point_change: int = 5
    iterations: int = 15


# ---------------------------------------------------------------------- #
# Build handling
# ---------------------------------------------------------------------- #

def build_card(build_xml: str, source: str) -> Dict[str, Any]:
    """Summarise a build for the first screen."""
    from src.optimizer.constraints import count_passive_points_in_xml
    from src.pob.jewel.registry import JewelRegistry
    from src.pob.modifier import get_main_skill_info, get_passive_tree_summary
    from src.pob.xml_parser import get_build_summary
    import re

    stats = get_build_summary(build_xml)
    tree = get_passive_tree_summary(build_xml)
    level = None
    m = re.search(r'<Build\s[^>]*level="(\d+)"', build_xml)
    if m:
        level = int(m.group(1))

    main_skill = None
    try:
        groups = get_main_skill_info(build_xml)
        for g in groups:
            actives = [gem["name"] for gem in g.get("gems", [])
                       if gem.get("enabled", True) and gem.get("gem_idx") not in g.get("support_indices", [])]
            if actives:
                main_skill = actives[0]
                break
    except Exception:
        logger.debug("main skill detection failed", exc_info=True)

    jewels = {"timeless": 0, "cluster": 0, "unique": 0}
    try:
        reg = JewelRegistry.from_build_xml(build_xml)
        jewels = {
            "timeless": len(reg.timeless_jewels),
            "cluster": len(reg.cluster_jewels),
            "unique": len(reg.unique_jewels),
        }
    except Exception:
        logger.debug("jewel parse failed", exc_info=True)

    dps = float(stats.get("combinedDPS", 0) or 0)
    life = float(stats.get("life", 0) or 0)
    ehp = float(stats.get("totalEHP", 0) or 0)
    has_stats = dps > 0 or life > 0

    return {
        "class": tree.get("class_name"),
        "ascendancy": tree.get("ascendancy_name"),
        "level": level,
        "main_skill": main_skill,
        "tree_version": tree.get("tree_version"),
        "points": count_passive_points_in_xml(build_xml),
        "node_count": len(tree.get("allocated_nodes", [])),
        "stats": {"dps": dps, "life": life, "ehp": ehp,
                  "energy_shield": float(stats.get("energyShield", 0) or 0)},
        "stats_source": "pob" if (has_stats and source != "account") else ("estimated" if has_stats else "none"),
        "jewels": jewels,
        "source": source,
    }


def _load_build(req: BuildRequest) -> tuple:
    """Return (xml, source) for a build request."""
    from src.pob.codec import decode_pob_code

    if req.xml:
        xml = req.xml.strip()
        if not xml.startswith("<"):
            raise HTTPException(400, "xml must be a Path of Building XML document")
        return xml, "xml"

    if req.code:
        code = req.code.strip()
        if code.startswith("<"):
            return code, "xml"
        try:
            return decode_pob_code(code), "code"
        except Exception as e:
            raise HTTPException(400, f"That doesn't look like a Path of Building code: {e}")

    if req.account and req.character:
        return _import_character(req), "account"

    raise HTTPException(400, "Provide a Path of Building code, XML, or an account and character name")


def _ggg_client(poesessid: Optional[str], realm: str):
    from src.ggg.client import GGGClient, Realm
    try:
        realm_enum = Realm(realm)
    except ValueError:
        raise HTTPException(400, f"Unknown realm '{realm}'")
    return GGGClient(poesessid=poesessid or None, realm=realm_enum)


_import_evaluator = None  # set by create_app so the importer can use PoB workers


def _import_character(req: BuildRequest) -> str:
    """
    Import through PoB's own ImportTab (exact items, gems, jewels, cluster
    nodes, tattoos, bloodline ascendancy), falling back to the Python
    converter if no PoB worker is available.
    """
    from src.ggg.converter import ConversionOptions, GGGToPoB
    from src.ggg.exceptions import CharacterNotFoundError, GGGAPIError, PrivateProfileError
    from src.pob.modifier import select_main_socket_group

    client = _ggg_client(req.poesessid, req.realm)
    try:
        characters = client.get_characters(req.account)
        character = next((c for c in characters if c.name.lower() == req.character.lower()), None)
        if character is None:
            raise HTTPException(404, f"No character named '{req.character}' on account '{req.account}'")

        if _import_evaluator is not None:
            try:
                char_obj = client.get_character_for_pob(req.account, character.name)
                res = _import_evaluator.import_character(char_obj)
                if res is not None and res.success and res.xml:
                    xml, _ = select_main_socket_group(res.xml)
                    return xml
                logger.warning("PoB importer failed (%s); using Python converter", getattr(res, "error", "no worker"))
            except (PrivateProfileError, CharacterNotFoundError, GGGAPIError):
                raise
            except Exception:
                logger.warning("PoB importer failed; using Python converter", exc_info=True)

        passives = client.get_passive_skills(req.account, character.name)
        items = client.get_items(req.account, character.name)
        # Convert without defaults first so assumptions can be re-applied later
        converter = GGGToPoB(ConversionOptions(include_items=True, include_passives=True,
                                               apply_config_defaults=False))
        try:
            return converter.convert(character, items=items, passives=passives)
        except Exception as e:  # pragma: no cover - depends on live API data
            # Log the raw items so the odd shape can be inspected and fixed.
            for it in getattr(items, "items", []) or []:
                raw = getattr(it, "_raw_data", None)
                if raw is not None:
                    odd = {k: type(v).__name__ for k, v in raw.items() if k.endswith("Mods") and v and not all(isinstance(x, str) for x in v)}
                    if odd:
                        logger.warning("Item %r (%s) has non-string mod entries: %s :: %s",
                                       raw.get("name"), raw.get("typeLine"), odd, json.dumps(raw)[:2000])
            logger.exception("Converting %s/%s to PoB failed", req.account, character.name)
            raise HTTPException(502, f"Imported {character.name} but could not convert an item to Path of Building format: {e}. "
                                     "Try exporting the build from PoB and pasting the code instead.")
    except PrivateProfileError:
        raise HTTPException(403, "This profile is private. Add your POESESSID to import it.")
    except CharacterNotFoundError as e:
        raise HTTPException(404, str(e))
    except GGGAPIError as e:
        raise HTTPException(502, f"Path of Exile account API error: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass


def _apply_assumptions(raw_xml: str, disabled: set) -> tuple:
    """Apply config defaults to an imported build, minus the disabled ones."""
    from src.ggg.config_rules import apply_default_config, describe

    xml, assumptions = apply_default_config(raw_xml)
    kept = [a for a in assumptions if a.var not in disabled]
    if len(kept) != len(assumptions):
        # Rebuild without the disabled inputs / flasks
        root = ET.fromstring(xml)
        for inp in root.iter("Input"):
            if inp.get("name") in disabled and inp.get("boolean"):
                inp.set("boolean", "false")
        if "flasks" in disabled:
            for slot in root.iter("Slot"):
                if (slot.get("name") or "").startswith("Flask"):
                    slot.attrib.pop("active", None)
        if "enemy" in disabled:
            for inp in root.iter("Input"):
                if inp.get("name") == "enemyIsBoss":
                    inp.set("string", "None")
        xml = ET.tostring(root, encoding="unicode")
    out = describe(assumptions)
    for a in out:
        a["enabled"] = a["var"] not in disabled
    return xml, out


class _Evaluator:
    """One lazily started PoB worker for quick headless stat estimates."""

    def __init__(self):
        self.pool = None

    def _ensure(self):
        from src.pob.worker_pool import PoBWorkerPool
        if self.pool is None:
            self.pool = PoBWorkerPool(num_workers=1)
            self.pool.start()
        return self.pool

    def import_character(self, character: Dict[str, Any]):
        try:
            return self._ensure().import_character(character, timeout=180)
        except Exception:
            logger.warning("PoB import failed", exc_info=True)
            return None

    def stats(self, xml: str) -> Optional[Dict[str, float]]:
        try:
            res = self._ensure().evaluate(xml, timeout=120)
            if not res.success:
                logger.warning("headless estimate failed: %s", res.error)
                return None
            st = res.stats
            return {"dps": float(st.get("combinedDPS", 0)), "life": float(st.get("life", 0)),
                    "ehp": float(st.get("totalEHP", 0)), "energy_shield": float(st.get("energyShield", 0))}
        except Exception:
            logger.warning("headless estimate failed", exc_info=True)
            return None

    def shutdown(self):
        if self.pool is not None:
            self.pool.shutdown()
            self.pool = None


# ---------------------------------------------------------------------- #
# App factory
# ---------------------------------------------------------------------- #

def create_app(pob_path: Optional[Path] = None, workers: Optional[int] = None) -> FastAPI:
    app = FastAPI(title="poe-optimizer", docs_url="/api/docs", redoc_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=2048)

    runner = JobRunner(workers=workers)
    builds: Dict[str, Dict[str, Any]] = {}
    evaluator = _Evaluator()
    app.state.runner = runner
    app.state.builds = builds
    app.state.evaluator = evaluator
    global _import_evaluator
    _import_evaluator = evaluator

    @app.on_event("shutdown")
    def _shutdown():
        runner.stop()
        evaluator.shutdown()

    # -------------------------------------------------------------- #
    # Static front end
    # -------------------------------------------------------------- #

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            return JSONResponse({"message": "poe-optimizer API is running; front end not built", "docs": "/api/docs"})
        return FileResponse(str(index_file), headers={"Cache-Control": "no-cache"})

    # -------------------------------------------------------------- #
    # Builds
    # -------------------------------------------------------------- #

    def _finish_import(build_id: str, raw_xml: str, disabled: set) -> Dict[str, Any]:
        xml, assumptions = _apply_assumptions(raw_xml, disabled)
        card = build_card(xml, "account")
        est = evaluator.stats(xml)
        if est:
            card["stats"] = est
            card["stats_source"] = "estimated"
        card["assumptions"] = assumptions
        builds[build_id] = {"xml": xml, "raw_xml": raw_xml, "disabled": set(disabled), "card": card}
        return card

    @app.post("/api/builds")
    def create_build(req: BuildRequest):
        xml, source = _load_build(req)
        build_id = uuid.uuid4().hex[:12]
        try:
            if source == "account":
                card = _finish_import(build_id, xml, set())
            else:
                card = build_card(xml, source)
                card["assumptions"] = []
                builds[build_id] = {"xml": xml, "card": card}
        except HTTPException:
            raise
        except Exception as e:
            logger.debug("build card failed", exc_info=True)
            raise HTTPException(400, f"Could not read that build: {e}")
        return {"build_id": build_id, **card}

    @app.patch("/api/builds/{build_id}/assumptions")
    def patch_assumptions(build_id: str, req: AssumptionsRequest):
        b = builds.get(build_id)
        if not b:
            raise HTTPException(404, "Unknown build")
        if "raw_xml" not in b:
            raise HTTPException(400, "Assumptions only apply to imported characters")
        card = _finish_import(build_id, b["raw_xml"], set(req.disabled))
        return {"build_id": build_id, **card}

    @app.get("/api/builds/{build_id}")
    def get_build(build_id: str):
        b = builds.get(build_id)
        if not b:
            raise HTTPException(404, "Unknown build")
        return {"build_id": build_id, **b["card"]}

    @app.get("/api/accounts/{account}/characters")
    def list_characters(account: str, realm: str = "pc",
                        x_poesessid: Optional[str] = Header(default=None)):
        from src.ggg.exceptions import GGGAPIError, PrivateProfileError
        client = _ggg_client(x_poesessid, realm)
        try:
            chars = client.get_characters(account)
        except PrivateProfileError:
            raise HTTPException(403, "This profile is private. Add your POESESSID to list its characters.")
        except GGGAPIError as e:
            raise HTTPException(502, f"Path of Exile account API error: {e}")
        finally:
            try:
                client.close()
            except Exception:
                pass
        return {"account": account, "characters": [
            {"name": c.name, "league": c.league, "class": c.class_name,
             "ascendancy": c.ascendancy_name, "level": c.level} for c in chars]}

    # -------------------------------------------------------------- #
    # Jobs
    # -------------------------------------------------------------- #

    @app.post("/api/jobs")
    def create_job(req: JobRequest):
        b = builds.get(req.build_id)
        if not b:
            raise HTTPException(404, "Unknown build; import it again")
        try:
            job_id = runner.submit(b["xml"], JobOptions(
                objective=req.objective,
                allow_point_change=req.allow_point_change,
                max_point_change=req.max_point_change,
                iterations=req.iterations,
                workers=workers,
            ))
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"job_id": job_id}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        snap = runner.snapshot(job_id)
        if snap is None:
            raise HTTPException(404, "Unknown job")
        return snap

    @app.get("/api/jobs/{job_id}/events")
    def job_events(job_id: str):
        if runner.get(job_id) is None:
            raise HTTPException(404, "Unknown job")

        def stream():
            for ev in runner.events(job_id):
                yield f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        if not runner.cancel(job_id):
            raise HTTPException(404, "Unknown job")
        return {"ok": True}

    # -------------------------------------------------------------- #
    # Tree data for drawing
    # -------------------------------------------------------------- #

    @app.get("/api/tree/{version}")
    def tree(version: str):
        from .tree_data import get_tree_data, tree_data_to_dict
        try:
            td = get_tree_data(None if version in ("latest", "") else version)
        except Exception as e:
            raise HTTPException(404, f"Tree version not available: {e}")
        return JSONResponse(tree_data_to_dict(td), headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


def run(host: str = "127.0.0.1", port: int = 8765, workers: Optional[int] = None,
        open_browser: bool = True) -> None:
    """Start the server (blocking). Used by ``poe-optimizer web``."""
    import threading
    import webbrowser

    import uvicorn

    app = create_app(workers=workers)
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"poe-optimizer web UI: {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=host, port=port, log_level="warning")
