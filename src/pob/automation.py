"""
PoB Desktop Automation - Recalculate Modified Builds

This module automates the Path of Building desktop app to recalculate
builds after modification. Works on macOS using AppleScript.

Workflow:
1. Modify build XML
2. Encode to PoB code
3. Use this module to import → recalculate → export
4. Parse updated XML for fresh stats

Platform Support:
- macOS: AppleScript automation (implemented)
- Windows: TODO - Use pyautogui or similar
- Linux: TODO - Use xdotool or similar
"""

import subprocess
import time
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PoBAutomationError(Exception):
    """Raised when PoB automation fails."""
    pass


class PoBAutomation:
    """
    Automates Path of Building desktop app for build recalculation.

    Example:
        >>> automation = PoBAutomation()
        >>> # Modify build
        >>> modified_xml = modify_passive_tree_nodes(xml, nodes_to_add=[123, 456])
        >>> modified_code = encode_pob_code(modified_xml)
        >>> # Recalculate via PoB app
        >>> recalculated_code = automation.recalculate_build(modified_code)
        >>> # Parse fresh stats
        >>> fresh_xml = decode_pob_code(recalculated_code)
        >>> stats = get_build_summary(fresh_xml)
    """

    def __init__(self, pob_app_path: Optional[str] = None):
        """
        Initialize PoB automation.

        Args:
            pob_app_path: Path to PoB .app on macOS. If None, uses default location.
        """
        self.pob_app_path = pob_app_path or "/Applications/Path of Building.app"

        # Verify PoB is installed
        if not Path(self.pob_app_path).exists():
            raise PoBAutomationError(
                f"Path of Building not found at: {self.pob_app_path}\n"
                "Please install PoB from https://pathofbuilding.community/"
            )

        logger.info(f"Initialized PoB automation: {self.pob_app_path}")

    def recalculate_build(
        self,
        pob_code: str,
        calculation_timeout: int = 10,
        close_after: bool = False
    ) -> str:
        """
        Import build code into PoB, wait for recalculation, and export.

        Args:
            pob_code: PoB import code to recalculate
            calculation_timeout: Seconds to wait for calculations (default: 10)
            close_after: Close PoB after exporting (default: False)

        Returns:
            New PoB code with recalculated stats

        Raises:
            PoBAutomationError: If automation fails
        """
        logger.info("Starting PoB build recalculation...")

        try:
            # Step 1: Launch PoB if not running
            self._launch_pob()

            # Step 2: Import build code
            self._import_code(pob_code)

            # Step 3: Wait for calculations
            logger.debug(f"Waiting {calculation_timeout}s for PoB to recalculate...")
            time.sleep(calculation_timeout)

            # Step 4: Export build
            recalculated_code = self._export_code()

            # Step 5: Optionally close PoB
            if close_after:
                self._close_pob()

            logger.info("✓ Build recalculation complete")
            return recalculated_code

        except subprocess.CalledProcessError as e:
            raise PoBAutomationError(f"AppleScript execution failed: {e}")
        except Exception as e:
            raise PoBAutomationError(f"Automation error: {e}")

    def _launch_pob(self):
        """Launch Path of Building app."""
        logger.debug("Launching Path of Building...")

        applescript = f'''
        tell application "{self.pob_app_path}"
            activate
        end tell
        delay 2
        '''

        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )

        logger.debug("✓ PoB launched")

    def _import_code(self, pob_code: str):
        """
        Import PoB code into the app.

        Uses keyboard shortcuts:
        - Cmd+I: Open import dialog
        - Paste code
        - Enter: Import
        """
        logger.debug("Importing build code...")

        # Escape quotes in the code for AppleScript
        escaped_code = pob_code.replace('"', '\\"').replace("'", "\\'")

        applescript = f'''
        tell application "System Events"
            tell process "Path of Building"
                -- Open import dialog (Cmd+I)
                keystroke "i" using command down
                delay 1

                -- Paste build code
                set the clipboard to "{escaped_code}"
                keystroke "v" using command down
                delay 0.5

                -- Press Enter to import
                keystroke return
                delay 2
            end tell
        end tell
        '''

        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )

        logger.debug("✓ Build imported")

    def _export_code(self) -> str:
        """
        Export current build as PoB code.

        Uses keyboard shortcuts:
        - Cmd+E: Export (copy to clipboard)
        - Read clipboard

        Returns:
            Exported PoB code
        """
        logger.debug("Exporting build code...")

        applescript = '''
        tell application "System Events"
            tell process "Path of Building"
                -- Copy build code to clipboard (Cmd+Shift+C or similar)
                -- Note: Actual shortcut may vary, this is a placeholder
                keystroke "c" using {command down, shift down}
                delay 1
            end tell
        end tell

        -- Read clipboard
        return the clipboard as text
        '''

        result = subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )

        exported_code = result.stdout.strip()

        if not exported_code or len(exported_code) < 100:
            raise PoBAutomationError("Export failed - clipboard empty or invalid")

        logger.debug(f"✓ Build exported ({len(exported_code)} chars)")
        return exported_code

    def _close_pob(self):
        """Close Path of Building app."""
        logger.debug("Closing Path of Building...")

        applescript = f'''
        tell application "{self.pob_app_path}"
            quit
        end tell
        '''

        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )

        logger.debug("✓ PoB closed")
