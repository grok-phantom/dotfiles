#!/usr/bin/env python3
"""Compatibility entry point for the reviewed Quicklook patch."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotfiles_lib.quicklook import main

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
