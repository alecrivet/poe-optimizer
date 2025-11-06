"""
Test mastery node handling in modifier.py

Verifies that mastery effects are correctly:
1. Parsed from XML
2. Removed when nodes are removed
3. Preserved when unrelated nodes are modified
4. Formatted back to XML correctly
"""

import pytest
from src.pob.modifier import (
    modify_passive_tree_nodes,
    get_passive_tree_summary,
    _parse_mastery_effects,
    _format_mastery_effects,
)
from src.pob.codec import decode_pob_code


def test_parse_mastery_effects():
    """Test parsing mastery effects string."""
    # Test valid format
    mastery_str = "{53188,64875},{27872,29161},{34723,40307}"
    result = _parse_mastery_effects(mastery_str)

    assert len(result) == 3
    assert result[53188] == 64875
    assert result[27872] == 29161
    assert result[34723] == 40307


def test_format_mastery_effects():
    """Test formatting mastery effects to string."""
    mastery_dict = {
        53188: 64875,
        27872: 29161,
        34723: 40307,
    }

    result = _format_mastery_effects(mastery_dict)

    # Should be sorted by node ID
    assert result == "{27872,29161},{34723,40307},{53188,64875}"


def test_round_trip_mastery_effects():
    """Test parse -> format round trip."""
    original = "{53188,64875},{27872,29161}"
    parsed = _parse_mastery_effects(original)
    formatted = _format_mastery_effects(parsed)

    # Parse again to compare dicts (order might differ)
    parsed_again = _parse_mastery_effects(formatted)

    assert parsed == parsed_again


def test_mastery_removal_with_node():
    """Test that mastery effects are removed when their nodes are removed."""
    # Load real build with masteries
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    original_masteries = summary['mastery_effects'].copy()
    print(f"\nOriginal masteries: {original_masteries}")

    # Remove a node that has a mastery
    if original_masteries:
        mastery_node_to_remove = list(original_masteries.keys())[0]
        print(f"Removing node {mastery_node_to_remove} which has mastery")

        modified_xml = modify_passive_tree_nodes(
            xml,
            nodes_to_remove=[mastery_node_to_remove]
        )

        new_summary = get_passive_tree_summary(modified_xml)
        new_masteries = new_summary['mastery_effects']

        print(f"New masteries: {new_masteries}")

        # Mastery should be removed
        assert mastery_node_to_remove not in new_masteries
        assert len(new_masteries) == len(original_masteries) - 1
    else:
        pytest.skip("Build has no mastery effects")


def test_mastery_preservation():
    """Test that unrelated mastery effects are preserved."""
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    original_masteries = summary['mastery_effects'].copy()
    mastery_nodes = set(original_masteries.keys())

    # Remove a node that is NOT a mastery
    non_mastery_nodes = summary['allocated_nodes'] - mastery_nodes
    if non_mastery_nodes:
        node_to_remove = list(non_mastery_nodes)[0]
        print(f"\nRemoving non-mastery node {node_to_remove}")

        modified_xml = modify_passive_tree_nodes(
            xml,
            nodes_to_remove=[node_to_remove]
        )

        new_summary = get_passive_tree_summary(modified_xml)

        # All masteries should be preserved
        assert new_summary['mastery_effects'] == original_masteries
    else:
        pytest.skip("All allocated nodes are masteries")


def test_get_tree_summary_includes_masteries():
    """Test that tree summary includes mastery information."""
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    # Should have mastery_effects key
    assert 'mastery_effects' in summary
    assert isinstance(summary['mastery_effects'], dict)

    # Mastery nodes should be in allocated nodes
    for mastery_node in summary['mastery_effects'].keys():
        assert mastery_node in summary['allocated_nodes'], \
            f"Mastery node {mastery_node} not in allocated nodes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
