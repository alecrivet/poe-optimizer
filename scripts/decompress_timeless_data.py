#!/usr/bin/env python3
"""
Decompress Timeless Jewel Data Files

This script decompresses the timeless jewel .zip files from PathOfBuilding
into .bin format for use in headless mode (which lacks zlib support).

The decompressed files are stored in our project's data directory,
not in the PathOfBuilding submodule.
"""

import os
import zlib
from pathlib import Path


def decompress_zlib_raw(data: bytes) -> bytes:
    """Decompress raw zlib data (no gzip/zip header)."""
    # PoB uses raw deflate compression
    # Try raw deflate first (-15), then with header (15)
    for wbits in [-15, 15, -zlib.MAX_WBITS, zlib.MAX_WBITS]:
        try:
            return zlib.decompress(data, wbits)
        except zlib.error:
            continue

    # Last resort: try as-is
    try:
        return zlib.decompress(data)
    except zlib.error as e:
        raise ValueError(f"Failed to decompress data: {e}")


def decompress_timeless_jewel_files(output_to_pob: bool = True):
    """
    Decompress all timeless jewel data files.

    Args:
        output_to_pob: If True, output directly to PoB's Data directory.
                       If False, output to our data/timeless_jewels directory.
    """
    # Paths
    project_root = Path(__file__).parent.parent
    pob_data_dir = project_root / "PathOfBuilding" / "src" / "Data" / "TimelessJewelData"

    if output_to_pob:
        # Output directly to PoB's directory (files are gitignored)
        output_dir = pob_data_dir
    else:
        # Output to our own data directory
        output_dir = project_root / "data" / "timeless_jewels"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Jewel types to decompress
    jewel_types = [
        "LethalPride",
        "BrutalRestraint",
        "MilitantFaith",
        "ElegantHubris",
        # GloriousVanity is split into parts
    ]

    print(f"Decompressing timeless jewel data from {pob_data_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Process single-file jewels
    for jewel_type in jewel_types:
        zip_path = pob_data_dir / f"{jewel_type}.zip"
        bin_path = output_dir / f"{jewel_type}.bin"

        if not zip_path.exists():
            print(f"  SKIP {jewel_type}: .zip not found")
            continue

        if bin_path.exists():
            # Check if .bin is newer than .zip
            if bin_path.stat().st_mtime > zip_path.stat().st_mtime:
                print(f"  SKIP {jewel_type}: .bin is up to date")
                continue

        print(f"  Processing {jewel_type}...", end=" ")
        try:
            compressed_data = zip_path.read_bytes()
            decompressed_data = decompress_zlib_raw(compressed_data)
            bin_path.write_bytes(decompressed_data)
            print(f"OK ({len(compressed_data):,} -> {len(decompressed_data):,} bytes)")
        except Exception as e:
            print(f"FAILED: {e}")

    # Process GloriousVanity (split into parts)
    gv_parts = sorted(pob_data_dir.glob("GloriousVanity.zip.part*"))
    if gv_parts:
        bin_path = output_dir / "GloriousVanity.bin"

        # Check if already processed
        newest_part = max(p.stat().st_mtime for p in gv_parts)
        if bin_path.exists() and bin_path.stat().st_mtime > newest_part:
            print(f"  SKIP GloriousVanity: .bin is up to date")
        else:
            print(f"  Processing GloriousVanity ({len(gv_parts)} parts)...", end=" ")
            try:
                # Concatenate all parts in order
                compressed_data = b""
                for part_path in gv_parts:
                    compressed_data += part_path.read_bytes()

                decompressed_data = decompress_zlib_raw(compressed_data)
                bin_path.write_bytes(decompressed_data)
                print(f"OK ({len(compressed_data):,} -> {len(decompressed_data):,} bytes)")
            except Exception as e:
                print(f"FAILED: {e}")

    # Copy supporting Lua files (only needed if outputting to separate directory)
    if not output_to_pob:
        for lua_file in ["LegionPassives.lua", "NodeIndexMapping.lua", "LegionTradeIds.lua"]:
            src = pob_data_dir / lua_file
            dst = output_dir / lua_file
            if src.exists():
                if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                    dst.write_bytes(src.read_bytes())
                    print(f"  Copied {lua_file}")

    print()
    print("Done! Decompressed files are in:", output_dir)
    print()
    print("Files created:")
    for f in sorted(output_dir.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")


if __name__ == "__main__":
    decompress_timeless_jewel_files()
