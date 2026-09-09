# Scripts Directory

Utility scripts for development, debugging, and analysis.

## Top-level scripts

- **benchmark_evaluation.py** - Reproduces the timings in `docs/PERFORMANCE.md` (worker start, full reload, `LOAD`/`SET`/`DELTA`, pool throughput). Run this before and after touching the evaluation path.
- **compare_optimizers.py** - Runs greedy and genetic on a build and saves both results to `output/`.
- **test_genetic_optimizer.py** - Quick genetic optimizer smoke run.
- **decompress_timeless_data.py** - Unpacks PoB's timeless jewel LUT data.
- **run_gui.py** - Launches the shelved PyQt GUI (requires the `gui` extra).

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
# Benchmark the evaluation path
venv/bin/python3 scripts/benchmark_evaluation.py --workers 8

# Run analysis
venv/bin/python3 scripts/analysis/analyze_tree.py

# Run demos
python scripts/demos/demo_codec.py

# Run debug tools
python scripts/debug/trace_tree_loading.py
```

## Note

For formal tests, see the `tests/` directory in the project root.
