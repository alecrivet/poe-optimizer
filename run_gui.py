#!/usr/bin/env python3
"""
Launcher for PoE Build Optimizer Desktop GUI

Usage:
    python run_gui.py
"""

import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        from src.gui.main_window import main
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("\nMake sure PyQt6 is installed:")
        print("  pip install PyQt6 PyQt6-WebEngine")
        sys.exit(1)
    except Exception as e:
        logging.exception("Application error")
        sys.exit(1)
