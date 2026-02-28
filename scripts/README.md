# Scripts Directory

Utility scripts for development, debugging, and analysis.

## Structure

### `analysis/`
Analysis tools for examining builds and tree modifications.

- **analyze_tree.py** - Analyzes passive tree nodes to identify inefficient allocations for reallocation

### `debug/`
Debugging tools used during development to investigate issues.

- **debug_node_removal.py** - Verifies XML modification correctness
- **debug_tree_parsing.py** - Tests HeadlessWrapper tree parsing
- **trace_tree_loading.py** - Traces tree loading process in HeadlessWrapper

### `demos/`
Demo scripts showing basic functionality.

- **demo_codec.py** - Demonstrates PoB code encoding/decoding
- **demo_pob_integration.py** - Demonstrates basic PoB integration

## Usage

All scripts can be run directly from the project root:

```bash
# Run analysis
python scripts/analysis/analyze_tree.py

# Run demos
python scripts/demos/demo_codec.py

# Run debug tools
python scripts/debug/trace_tree_loading.py
```

## Note

For formal tests, see the `tests/` directory in the project root.
