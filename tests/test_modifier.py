"""
Tests for build modification functions.
"""

try:
    import pytest
except ImportError:
    pytest = None

from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.modifier import (
    modify_passive_tree_nodes,
    modify_character_level,
    modify_gem_level,
    get_passive_tree_summary,
    get_skill_groups_summary,
    BuildModificationError,
)


def test_get_passive_tree_summary():
    """Test extracting passive tree summary."""
    # Load build2
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    assert summary['total_nodes'] > 0
    assert len(summary['allocated_nodes']) > 0
    assert summary['class_name'] != 'Unknown'
    print(f"Tree summary: {summary['total_nodes']} nodes, class: {summary['class_name']}, ascendancy: {summary['ascendancy_name']}")


def test_get_skill_groups_summary():
    """Test extracting skill groups summary."""
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    groups = get_skill_groups_summary(xml)

    assert len(groups) > 0
    print(f"\nFound {len(groups)} skill groups:")
    for group in groups:
        print(f"  Group {group['index']} ({group['slot']}): {len(group['gems'])} gems")
        for gem in group['gems']:
            print(f"    - {gem['name']} (L{gem['level']}, Q{gem['quality']})")


def test_modify_character_level():
    """Test changing character level."""
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)

    # Get original level
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    original_level = int(root.find("Build").get("level"))

    # Modify level
    new_level = 95
    modified_xml = modify_character_level(xml, new_level)

    # Verify change
    root = ET.fromstring(modified_xml)
    assert int(root.find("Build").get("level")) == new_level

    # Test round-trip encoding
    new_code = encode_pob_code(modified_xml)
    assert len(new_code) > 0

    print(f"\nLevel changed: {original_level} → {new_level}")


def test_modify_passive_tree_nodes():
    """Test adding/removing passive tree nodes."""
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)

    # Get original summary
    original_summary = get_passive_tree_summary(xml)
    original_count = original_summary['total_nodes']
    original_nodes = original_summary['allocated_nodes']

    # Pick some nodes to test with
    # Take first 3 nodes to remove, and add some new ones
    nodes_to_remove = list(original_nodes)[:3]
    nodes_to_add = [99999, 99998, 99997, 99996]  # Arbitrary node IDs

    # Modify tree
    modified_xml = modify_passive_tree_nodes(
        xml,
        nodes_to_add=nodes_to_add,
        nodes_to_remove=nodes_to_remove
    )

    # Verify changes
    new_summary = get_passive_tree_summary(modified_xml)
    new_count = new_summary['total_nodes']
    new_nodes = new_summary['allocated_nodes']

    # Should have: original - 3 removed + 4 added = original + 1
    assert new_count == original_count - len(nodes_to_remove) + len(nodes_to_add)

    # Verify removed nodes are gone
    for node_id in nodes_to_remove:
        assert node_id not in new_nodes

    # Verify added nodes are present
    for node_id in nodes_to_add:
        assert node_id in new_nodes

    # Test round-trip
    new_code = encode_pob_code(modified_xml)
    assert len(new_code) > 0

    print(f"\nPassive tree modified: {original_count} → {new_count} nodes")
    print(f"  Removed {len(nodes_to_remove)} nodes")
    print(f"  Added {len(nodes_to_add)} nodes")


def test_modify_gem_level():
    """Test modifying gem level and quality."""
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)

    # Get skill groups to find a gem to modify
    groups = get_skill_groups_summary(xml)
    assert len(groups) > 0

    # Find first active gem
    target_group = None
    target_gem = None
    for group in groups:
        if group['gems']:
            target_group = group['index']
            target_gem = group['gems'][0]
            break

    assert target_group is not None
    assert target_gem is not None

    original_level = target_gem['level']
    original_quality = target_gem['quality']

    # Modify gem
    new_level = 21
    new_quality = 23
    modified_xml = modify_gem_level(
        xml,
        socket_group_index=target_group,
        gem_name=target_gem['name'],
        new_level=new_level,
        new_quality=new_quality
    )

    # Verify change
    new_groups = get_skill_groups_summary(modified_xml)
    modified_gem = new_groups[target_group - 1]['gems'][0]

    assert modified_gem['level'] == new_level
    assert modified_gem['quality'] == new_quality

    # Test round-trip
    new_code = encode_pob_code(modified_xml)
    assert len(new_code) > 0

    print(f"\nGem '{target_gem['name']}' modified:")
    print(f"  Level: {original_level} → {new_level}")
    print(f"  Quality: {original_quality} → {new_quality}")


def test_invalid_xml_handling():
    """Test error handling for invalid XML."""
    if pytest:
        with pytest.raises(BuildModificationError):
            modify_character_level("not valid xml", 90)

        with pytest.raises(BuildModificationError):
            modify_passive_tree_nodes("not valid xml", [123])
    else:
        # Manual error checking without pytest
        try:
            modify_character_level("not valid xml", 90)
            assert False, "Should have raised BuildModificationError"
        except BuildModificationError:
            pass

        try:
            modify_passive_tree_nodes("not valid xml", [123])
            assert False, "Should have raised BuildModificationError"
        except BuildModificationError:
            pass


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Build Modification Functions")
    print("=" * 70)

    test_get_passive_tree_summary()
    test_get_skill_groups_summary()
    test_modify_character_level()
    test_modify_passive_tree_nodes()
    test_modify_gem_level()
    test_invalid_xml_handling()

    print("\n" + "=" * 70)
    print("✓ All modifier tests passed!")
    print("=" * 70)
