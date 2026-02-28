"""
Tests for tree version auto-detection.
"""

import pytest
from unittest.mock import patch

from src.pob.tree_version import (
    discover_tree_versions,
    get_latest_tree_version,
    get_latest_tree_version_or_raise,
    get_tree_version_from_xml,
    resolve_tree_version,
    _version_sort_key,
)


# --- Discovery tests (use real PoB submodule) ---

def test_discover_tree_versions():
    """discover_tree_versions finds versions from the real PoB submodule."""
    versions = discover_tree_versions("./PathOfBuilding")
    assert len(versions) > 0
    # The latest standard version should be present
    latest = get_latest_tree_version("./PathOfBuilding")
    assert latest in versions


def test_discover_tree_versions_missing_path():
    """Returns empty list for missing path."""
    versions = discover_tree_versions("/nonexistent/path")
    assert versions == []


# --- Sort order tests ---

def test_version_sort_order():
    """Standard versions sort before alternate/ruthless of the same minor."""
    assert _version_sort_key("3_27") < _version_sort_key("3_27_alternate")
    assert _version_sort_key("3_27_alternate") < _version_sort_key("3_27_ruthless")
    assert _version_sort_key("3_27_ruthless") < _version_sort_key("3_27_ruthless_alternate")


def test_version_sort_minor_comparison():
    """Higher minor version sorts after lower, regardless of suffix."""
    assert _version_sort_key("3_27") > _version_sort_key("3_26_alternate")
    assert _version_sort_key("3_27") > _version_sort_key("3_26")


def test_discover_returns_sorted():
    """Versions are returned in sorted order."""
    versions = discover_tree_versions("./PathOfBuilding")
    keys = [_version_sort_key(v) for v in versions]
    assert keys == sorted(keys)


# --- get_latest_tree_version ---

def test_get_latest_tree_version():
    """Returns latest standard (non-alternate, non-ruthless) version."""
    latest = get_latest_tree_version("./PathOfBuilding")
    assert latest is not None
    # Should be a standard version (no suffix)
    assert "alternate" not in latest
    assert "ruthless" not in latest
    # Should be at least 3_26 (known minimum)
    assert _version_sort_key(latest) >= _version_sort_key("3_26")


def test_get_latest_tree_version_missing_path():
    """Returns None for missing path."""
    assert get_latest_tree_version("/nonexistent/path") is None


# --- get_tree_version_from_xml ---

SAMPLE_XML_WITH_VERSION = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"/>
    <Tree activeSpec="1">
        <Spec title="Test" treeVersion="3_27" classId="1" ascendClassId="1"
              nodes="1,2,3" activeSpec="true"/>
    </Tree>
</PathOfBuilding>
"""

SAMPLE_XML_NO_VERSION = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"/>
    <Tree activeSpec="1">
        <Spec title="Test" classId="1" ascendClassId="1" nodes="1,2,3"/>
    </Tree>
</PathOfBuilding>
"""


def test_get_tree_version_from_xml():
    """Extracts treeVersion from sample XML."""
    assert get_tree_version_from_xml(SAMPLE_XML_WITH_VERSION) == "3_27"


def test_get_tree_version_from_xml_missing():
    """Returns None when treeVersion attribute is absent."""
    assert get_tree_version_from_xml(SAMPLE_XML_NO_VERSION) is None


def test_get_tree_version_from_xml_invalid():
    """Returns None for invalid XML."""
    assert get_tree_version_from_xml("not xml at all") is None


# --- resolve_tree_version ---

def test_resolve_explicit_overrides_xml():
    """Explicit tree version takes precedence over XML."""
    version = resolve_tree_version(
        build_xml=SAMPLE_XML_WITH_VERSION,
        explicit="3_26",
        pob_path="./PathOfBuilding",
    )
    assert version == "3_26"


def test_resolve_xml_version():
    """Falls back to XML version when no explicit."""
    version = resolve_tree_version(
        build_xml=SAMPLE_XML_WITH_VERSION,
        pob_path="./PathOfBuilding",
    )
    assert version == "3_27"


def test_resolve_fallback_to_latest():
    """Falls back to latest when no explicit and no XML version."""
    version = resolve_tree_version(
        build_xml=SAMPLE_XML_NO_VERSION,
        pob_path="./PathOfBuilding",
    )
    # Should get a valid version
    assert version is not None
    assert "alternate" not in version
    assert "ruthless" not in version


def test_resolve_fallback_with_warning(caplog):
    """Warns when XML version is not available, falls back to latest."""
    xml_with_old_version = SAMPLE_XML_WITH_VERSION.replace(
        'treeVersion="3_27"', 'treeVersion="99_99"'
    )
    import logging
    with caplog.at_level(logging.WARNING):
        version = resolve_tree_version(
            build_xml=xml_with_old_version,
            pob_path="./PathOfBuilding",
        )
    assert version is not None
    assert "99_99" in caplog.text


def test_resolve_raises_when_no_versions():
    """Raises ValueError when no tree versions can be found."""
    with pytest.raises(ValueError, match="No tree versions found"):
        resolve_tree_version(pob_path="/nonexistent/path")
