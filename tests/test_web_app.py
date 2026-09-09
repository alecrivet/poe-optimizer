"""Tests for the local web UI (src/web/app.py, src/web/jobs.py)."""

import json
import shutil
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from src.web.app import build_card, create_app  # noqa: E402
from src.web.jobs import JobOptions, JobRunner  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "builds"
POB_SRC = Path(__file__).parent.parent / "PathOfBuilding" / "src"
needs_pob = pytest.mark.skipif(
    shutil.which("luajit") is None or not (POB_SRC / "HeadlessWrapper.lua").exists(),
    reason="luajit and the PathOfBuilding submodule are required",
)


@pytest.fixture
def client():
    return TestClient(create_app(workers=2))


class TestBuilds:
    def test_health_and_index(self, client):
        assert client.get("/api/health").json() == {"ok": True}
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200

    def test_build_from_xml_and_code(self, client):
        xml = (FIXTURES / "cyclone_slayer.xml").read_text()
        r = client.post("/api/builds", json={"xml": xml})
        assert r.status_code == 200, r.text
        card = r.json()
        assert card["class"] == "Duelist" and card["ascendancy"] == "Slayer"
        assert card["level"] == 96 and card["points"] == 119
        assert card["main_skill"] == "Cyclone of Tumult"
        assert card["stats_source"] == "pob" and card["stats"]["dps"] > 1e6
        assert card["jewels"]["timeless"] == 1
        assert client.get(f"/api/builds/{card['build_id']}").json()["points"] == 119

        code = (FIXTURES / "cyclone_slayer.txt").read_text().strip()
        r = client.post("/api/builds", json={"code": code})
        assert r.status_code == 200 and r.json()["points"] == 119

    def test_bad_inputs(self, client):
        assert client.post("/api/builds", json={"code": "not a code"}).status_code == 400
        assert client.post("/api/builds", json={}).status_code == 400
        assert client.post("/api/jobs", json={"build_id": "nope"}).status_code == 404
        assert client.get("/api/jobs/nope").status_code == 404

    def test_build_card_marks_account_imports_as_estimated(self):
        xml = (FIXTURES / "cyclone_slayer.xml").read_text()
        assert build_card(xml, "account")["stats_source"] == "estimated"
        assert build_card(xml, "code")["stats_source"] == "pob"


class TestJobOptions:
    def test_validation(self):
        JobOptions().validate()
        with pytest.raises(ValueError):
            JobOptions(objective="gold").validate()
        with pytest.raises(ValueError):
            JobOptions(iterations=0).validate()


class TestTreeEndpoint:
    def test_tree_json(self, client):
        r = client.get("/api/tree/3_29")
        assert r.status_code == 200
        data = r.json()
        assert len(data["nodes"]) > 2900 and data["edges"]
        assert set(data["nodes"][0]) >= {"i", "x", "y", "n", "t"}
        assert client.get("/api/tree/9_99").status_code == 404


@needs_pob
class TestJobsEndToEnd:
    def test_submit_stream_result_and_cancel(self, client):
        xml = (FIXTURES / "cyclone_slayer.xml").read_text()
        build_id = client.post("/api/builds", json={"xml": xml}).json()["build_id"]
        job_id = client.post("/api/jobs", json={"build_id": build_id, "objective": "dps", "iterations": 1}).json()["job_id"]

        types = []
        iterations = []
        with client.stream("GET", f"/api/jobs/{job_id}/events") as r:
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:])
                types.append(ev["type"])
                if ev["type"] == "iteration":
                    iterations.append(ev)
        assert "started" in types and types[-1] == "done"
        assert len(iterations) == 1
        ev = iterations[0]
        assert ev["points_used"] == 119 and ev["marginal_pct"] > 0
        assert ev["removed"] or ev["added"] or ev["masteries"]

        snap = client.get(f"/api/jobs/{job_id}").json()
        assert snap["status"] == "done"
        res = snap["result"]
        assert res["change_pct"]["dps"] > 0
        assert len(res["final_nodes"]) >= 100 and res["pob_code"]
        assert res["changes"][0]["removed"] is not None

        # Cancelling a finished job is harmless; cancelling an unknown one is 404
        assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
        assert client.post("/api/jobs/nope/cancel").status_code == 404
