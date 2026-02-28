"""
Tree Version Detection

Auto-detects available passive tree versions from the PathOfBuilding
submodule's TreeData directory, eliminating hardcoded version strings.
"""

import re
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Suffix ranking for sort order: standard < alternate < ruthless < ruthless_alternate
_SUFFIX_RANK = {
    "": 0,
    "alternate": 1,
    "ruthless": 2,
    "ruthless_alternate": 3,
}

_VERSION_PATTERN = re.compile(r"^(\d+)_(\d+)(?:_(alternate|ruthless|ruthless_alternate))?$")


def _version_sort_key(version: str):
    """Sort key: (major, minor, suffix_rank)."""
    m = _VERSION_PATTERN.match(version)
    if not m:
        return (0, 0, 0)
    major, minor = int(m.group(1)), int(m.group(2))
    suffix = m.group(3) or ""
    return (major, minor, _SUFFIX_RANK.get(suffix, 99))


def discover_tree_versions(pob_path: str = "./PathOfBuilding") -> List[str]:
    """
    Scan TreeData/ for valid tree version directories.

    Returns sorted list of version strings (e.g. ["3_26", "3_26_alternate", "3_27"]).
    """
    tree_data_dir = Path(pob_path) / "src" / "TreeData"
    if not tree_data_dir.is_dir():
        logger.warning(f"TreeData directory not found: {tree_data_dir}")
        return []

    versions = []
    for entry in tree_data_dir.iterdir():
        if entry.is_dir() and _VERSION_PATTERN.match(entry.name):
            versions.append(entry.name)

    versions.sort(key=_version_sort_key)
    return versions


def get_latest_tree_version(pob_path: str = "./PathOfBuilding") -> Optional[str]:
    """
    Return the latest standard (non-ruthless, non-alternate) tree version.

    Returns None if no versions found.
    """
    versions = discover_tree_versions(pob_path)
    standard = [v for v in versions if _VERSION_PATTERN.match(v) and not _VERSION_PATTERN.match(v).group(3)]
    return standard[-1] if standard else None


def get_tree_version_from_xml(build_xml: str) -> Optional[str]:
    """
    Extract treeVersion from the active <Spec> element in build XML.

    Returns None if not found.
    """
    try:
        root = ET.fromstring(build_xml)
        tree_elem = root.find(".//Tree")
        if tree_elem is None:
            return None
        spec_elem = tree_elem.find(".//Spec[@activeSpec='true']") or tree_elem.find(".//Spec")
        if spec_elem is None:
            return None
        return spec_elem.get("treeVersion")
    except ET.ParseError:
        return None


def resolve_tree_version(
    build_xml: Optional[str] = None,
    explicit: Optional[str] = None,
    pob_path: str = "./PathOfBuilding",
) -> str:
    """
    Resolve tree version with priority: explicit > XML > latest.

    Warns and falls back to latest if the resolved version is not available.

    Raises ValueError if no tree version can be determined.
    """
    available = discover_tree_versions(pob_path)
    available_set = set(available)

    # Priority 1: explicit override
    if explicit:
        if explicit in available_set:
            return explicit
        logger.warning(
            f"Explicit tree version '{explicit}' not found in TreeData. "
            f"Available: {available}"
        )
        # Fall through to latest

    # Priority 2: from build XML
    if build_xml:
        xml_version = get_tree_version_from_xml(build_xml)
        if xml_version and xml_version in available_set:
            return xml_version
        if xml_version:
            logger.warning(
                f"Build XML tree version '{xml_version}' not available in TreeData. "
                f"Falling back to latest."
            )

    # Priority 3: latest standard version
    latest = get_latest_tree_version(pob_path)
    if latest:
        return latest

    raise ValueError(
        f"No tree versions found in {pob_path}/src/TreeData/. "
        "Is the PathOfBuilding submodule initialized?"
    )
