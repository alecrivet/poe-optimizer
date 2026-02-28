"""
PoB Calculator - Python wrapper for Path of Building's calculation engine.

This module provides a Python interface to Path of Building's headless mode,
allowing us to evaluate builds and get accurate DPS, EHP, and other statistics.

Note: Primary method now uses pre-calculated stats from XML (more reliable),
with Lua calculation as fallback.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from .xml_parser import get_build_summary, parse_pob_stats

logger = logging.getLogger(__name__)


class PoBCalculatorError(Exception):
    """Base exception for PoB calculator errors."""
    pass


class PoBCalculator:
    """
    Python wrapper for Path of Building's calculation engine.

    This class handles:
    - Validating PoB installation
    - Running PoB's headless mode via subprocess
    - Parsing calculation results
    - Error handling and cleanup

    Example:
        >>> calc = PoBCalculator()
        >>> with open('my_build.xml') as f:
        >>>     build_xml = f.read()
        >>> stats = calc.evaluate_build(build_xml)
        >>> print(f"DPS: {stats['totalDPS']}, Life: {stats['life']}")
    """

    def __init__(self, pob_path: Optional[str] = None, lua_command: str = "luajit"):
        """
        Initialize the PoB Calculator.

        Args:
            pob_path: Path to PathOfBuilding directory. Defaults to ./PathOfBuilding
            lua_command: Lua command to use (luajit, lua5.1, or lua). Defaults to luajit.

        Raises:
            PoBCalculatorError: If PoB installation is invalid.
        """
        # Set default paths
        if pob_path is None:
            # Assume PathOfBuilding is in the project root
            project_root = Path(__file__).parent.parent.parent
            pob_path = project_root / "PathOfBuilding"

        self.pob_path = Path(pob_path).resolve()
        self.pob_src_path = self.pob_path / "src"
        self.lua_command = lua_command

        # Path to our Lua evaluator script
        # Use manual tree loading evaluator (workaround for HeadlessWrapper not calling TreeTab:Load())
        self.evaluator_script = Path(__file__).parent / "evaluator_manual_tree.lua"

        # Validate installation
        self._validate_installation()

        logger.info(f"Initialized PoBCalculator with PoB path: {self.pob_path}")

    def _validate_installation(self) -> None:
        """
        Validate that PoB and Lua are properly installed.

        Raises:
            PoBCalculatorError: If validation fails.
        """
        # Check PoB directory exists
        if not self.pob_path.exists():
            raise PoBCalculatorError(
                f"PathOfBuilding directory not found at: {self.pob_path}\n"
                "Make sure the PathOfBuilding submodule is initialized:\n"
                "  git submodule update --init --recursive"
            )

        # Check HeadlessWrapper.lua exists
        headless_wrapper = self.pob_src_path / "HeadlessWrapper.lua"
        if not headless_wrapper.exists():
            raise PoBCalculatorError(
                f"HeadlessWrapper.lua not found at: {headless_wrapper}\n"
                "The PathOfBuilding installation appears incomplete."
            )

        # Check our evaluator script exists
        if not self.evaluator_script.exists():
            raise PoBCalculatorError(
                f"Evaluator script not found at: {self.evaluator_script}\n"
                "The poe-optimizer installation appears incomplete."
            )

        # Check Lua is installed
        try:
            result = subprocess.run(
                [self.lua_command, "-v"],
                capture_output=True,
                text=True,
                timeout=5
            )
            logger.debug(f"Lua version: {result.stdout.strip() or result.stderr.strip()}")
        except FileNotFoundError:
            raise PoBCalculatorError(
                f"Lua command '{self.lua_command}' not found.\n"
                "Please install Lua 5.1, LuaJIT, or set lua_command parameter.\n"
                "  macOS: brew install luajit\n"
                "  Ubuntu: apt-get install luajit"
            )
        except subprocess.TimeoutExpired:
            raise PoBCalculatorError(
                f"Lua command '{self.lua_command}' timed out when checking version."
            )

    def evaluate_build(self, build_xml: str, timeout: int = 30, use_xml_stats: bool = True) -> Dict:
        """
        Evaluate a PoB build and return statistics.

        This method first attempts to extract pre-calculated stats from the XML
        (faster and more reliable), falling back to Lua calculation if needed.

        Args:
            build_xml: PoB build XML content
            timeout: Maximum time in seconds to wait for Lua evaluation (default: 30)
            use_xml_stats: If True, prefer pre-calculated XML stats (default: True)

        Returns:
            Dict containing build statistics:
                - totalDPS: Total DPS of main skill
                - combinedDPS: Combined DPS (most accurate for real builds)
                - fullDPS: Full DPS from all skills
                - totalEHP: Effective Hit Pool
                - life: Maximum life
                - energyShield: Maximum energy shield
                - fireRes, coldRes, lightningRes, chaosRes: Resistances
                - strength, dexterity, intelligence: Attributes
                - and many more stats...

        Raises:
            PoBCalculatorError: If evaluation fails
        """
        # Strategy 1: Try to get pre-calculated stats from XML
        if use_xml_stats:
            try:
                stats = get_build_summary(build_xml)
                # Check if we got meaningful stats
                if stats.get('combinedDPS', 0) > 0 or stats.get('life', 0) > 0:
                    logger.debug(f"Using pre-calculated XML stats. Combined DPS: {stats.get('combinedDPS', 0):,.0f}, "
                                f"Life: {stats.get('life', 0):,.0f}")
                    return stats
                else:
                    logger.debug("XML stats empty or zero, falling back to Lua calculation")
            except Exception as e:
                logger.warning(f"Failed to parse XML stats, falling back to Lua: {e}")

        # Strategy 2: Fall back to Lua calculation (for builds without pre-calculated stats)
        logger.debug("Using Lua calculation engine")
        return self._evaluate_with_lua(build_xml, timeout)

    def _evaluate_with_lua(self, build_xml: str, timeout: int = 30) -> Dict:
        """
        Evaluate build using PoB's Lua calculation engine.

        This is the fallback method when pre-calculated XML stats aren't available.
        Note: HeadlessWrapper has limitations and may not accurately calculate
        complex builds with multiple skills.

        Args:
            build_xml: PoB build XML content
            timeout: Maximum time in seconds to wait for evaluation

        Returns:
            Dict containing calculated statistics

        Raises:
            PoBCalculatorError: If evaluation fails
        """
        # Create temporary file for build XML
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.xml',
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(build_xml)
            temp_path = temp_file.name

        try:
            # Run the Lua evaluator
            result = subprocess.run(
                [self.lua_command, str(self.evaluator_script), temp_path],
                cwd=str(self.pob_src_path),  # Run from PoB src directory
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                # Try to parse JSON error from stderr
                try:
                    error_data = json.loads(error_msg)
                    if not error_data.get('success', True):
                        error_msg = error_data.get('error', error_msg)
                except json.JSONDecodeError:
                    pass

                raise PoBCalculatorError(
                    f"PoB evaluation failed (exit code {result.returncode}):\n{error_msg}"
                )

            # Parse JSON output
            # PoB prints debug messages to stdout, so we need to extract just the JSON
            # The JSON is typically on the last line
            try:
                # Try to find JSON in the output (look for lines starting with '{')
                json_lines = [line for line in result.stdout.split('\n') if line.strip().startswith('{')]
                if not json_lines:
                    raise PoBCalculatorError(
                        f"No JSON output found in PoB response.\n"
                        f"Output was: {result.stdout[:500]}"
                    )

                # Use the last JSON line (should be our result)
                json_str = json_lines[-1].strip()
                output = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output:\n{result.stdout}")
                raise PoBCalculatorError(
                    f"Failed to parse PoB output as JSON: {e}\n"
                    f"Output was: {result.stdout[:500]}"
                )

            # Check success flag
            if not output.get('success', False):
                error = output.get('error', 'Unknown error')
                raise PoBCalculatorError(f"PoB evaluation failed: {error}")

            # Extract and return stats
            stats = output.get('stats', {})
            logger.debug(f"Lua evaluation successful. DPS: {stats.get('fullDPS', 0)}, "
                        f"Life: {stats.get('life', 0)}")

            return stats

        except subprocess.TimeoutExpired:
            raise PoBCalculatorError(
                f"PoB evaluation timed out after {timeout} seconds.\n"
                "The build may be too complex or PoB may be stuck."
            )

        except Exception as e:
            if isinstance(e, PoBCalculatorError):
                raise
            raise PoBCalculatorError(f"Unexpected error during evaluation: {e}")

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {e}")

    def __repr__(self) -> str:
        return f"PoBCalculator(pob_path={self.pob_path}, lua_command={self.lua_command})"
