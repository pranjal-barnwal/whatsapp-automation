"""Launcher for the WhatsApp automation tool.

Run with:  python main.py [options]

All the logic lives in the ``src`` package; this file only
wires up the command-line entry point (see ``src/cli.py``).
"""
from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
