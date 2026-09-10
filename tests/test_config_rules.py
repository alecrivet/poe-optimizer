"""Tests for poe.ninja-style PoB config defaults on imported characters."""

import re
import shutil
from pathlib import Path

import pytest

from src.ggg.config_rules import ON_KILL, apply_default_config, collect_sources, evaluate_rules

FIXTURE = Path(__file__).parent / "fixtures" / "builds" / "cyclone_slayer.xml"
POB_SRC = Path(__file__).parent.parent / "PathOfBuilding" / "src"
needs_pob = pytest.mark.skipif(
    shutil.which("luajit") is None or not (POB_SRC / "HeadlessWrapper.lua").exists(),
    reason="luajit and the PathOfBuilding submodule are required",
)


def stripped_fixture() -> str:
    """The fixture as an account import would look: no config, no active flasks."""
    xml = FIXTURE.read_text()
    xml = re.sub(r"<Config .*?</Config>", "<Config></Config>", xml, flags=re.S)
    return xml.replace(' active="true"', "")


class TestSources:
    def test_collects_items_gems_class_and_tree(self):
        src = collect_sources(FIXTURE.read_text())
        assert "ascendancy:Slayer" in src
        assert "Cyclone of Tumult" in src
        assert any("Leeched as Life" in s for s in src)           # item mod
        assert any("Endurance Charge on Melee Critical" in s for s in src)  # passive stat

    def test_on_kill_lines_are_excluded(self):
        assert ON_KILL.search("Gain a Frenzy Charge on Kill")
        assert ON_KILL.search("20% increased Damage if you've Killed Recently")
        assert not ON_KILL.search("Gain a Frenzy Charge on Hit")


class TestRules:
    def test_fixture_rules(self):
        found = {a.var: a for a in evaluate_rules(stripped_fixture())}
        assert "channellingCycloneCheck" in found
        assert "conditionFullLife" in found and "Slayer" in found["conditionFullLife"].reason
        assert "conditionLeeching" in found
        assert "buffLifetap" in found and "buffInfusion" in found
        assert "useEnduranceCharges" in found
        # Assassin's Mark grants power charges on kill only; not a source. The
        # block node is one, so the var may be on, but never because of the mark.
        if "usePowerCharges" in found:
            assert "Assassin" not in found["usePowerCharges"].reason
        assert "conditionEnemyMaimed" not in found   # "immunity to maim" is not a source
        assert "useFrenzyCharges" not in found       # no frenzy generation on this build
        assert "conditionMinionsDiedRecently" not in found  # "your Minions take reduced reflect" is not a minion build
        assert "conditionBeenHitRecently" not in found      # "when Hit by your Skills" is about enemies
        assert "buffFortification" in found and "Overlord" in found["buffFortification"].reason
        assert found["multiplierRage"].value == 100 and "Rage on Melee Hit" in found["multiplierRage"].reason
        assert found["prideEffect"].value == "MAX"
        # "everyone" rules from poe.ninja
        for var in ("conditionCritRecently", "conditionEnemyChilled", "conditionEnemyIgnited", "conditionEnemyBleeding", "multiplierNearbyEnemies"):
            assert var in found

    def test_crit_recently_off_with_resolute_technique(self):
        xml = stripped_fixture().replace("<Item id=\"1\">", "<Item id=\"1\">Resolute Technique\n", 1)
        found = {a.var for a in evaluate_rules(xml)}
        assert "conditionCritRecently" not in found

    def test_numeric_values_are_written_as_numbers(self):
        xml, _ = apply_default_config(stripped_fixture())
        assert '<Input name="multiplierRage" number="100"' in xml
        assert '<Input name="multiplierNearbyEnemies" number="1"' in xml
        assert '<Input name="prideEffect" string="MAX"' in xml

    def test_apply_writes_config_and_flasks(self):
        xml, assumptions = apply_default_config(stripped_fixture())
        labels = {a.label for a in assumptions}
        assert "Pinnacle boss" in labels and "5 flasks active" in labels
        assert '<Input name="enemyIsBoss" string="Pinnacle"' in xml
        assert '<Input name="DisableEHPGainOnBlock" boolean="true"' in xml
        assert '<Input name="BrandsAttachedToEnemy" number="1"' in xml
        assert '<Input name="channellingCycloneCheck" boolean="true"' in xml
        assert xml.count('active="true"') == 5
        # Existing inputs are preserved, not duplicated
        again, _ = apply_default_config(xml)
        assert again.count('name="channellingCycloneCheck"') == 1

    def test_no_kill_conditions_are_assumed(self):
        xml, _ = apply_default_config(stripped_fixture())
        assert "conditionKilledRecently" not in xml


@needs_pob
class TestEffect:
    def test_rules_raise_stats_from_raw_import_toward_hand_config(self):
        from src.pob.worker_pool import PoBWorker

        raw = stripped_fixture()
        ruled, _ = apply_default_config(raw)
        w = PoBWorker(worker_id=0)
        assert w.start()
        try:
            r_raw = w.evaluate(raw).stats
            r_ruled = w.evaluate(ruled).stats
            r_hand = w.evaluate(FIXTURE.read_text()).stats
        finally:
            w.stop()
        # Raw import is far below the owner's config; rules land above it
        # (this build has charge sources its owner chose not to assume).
        assert r_raw["combinedDPS"] < r_hand["combinedDPS"] < r_ruled["combinedDPS"]
        assert r_raw["totalEHP"] < r_hand["totalEHP"] < r_ruled["totalEHP"]
