#!/usr/bin/env python3
"""Start core-dispatch transmitter via CLI."""
import sys

from core_dispatch.launch_control.cli import cli

if __name__ == "__main__":
    # Delegate to core-dispatch CLI transmitter command
    sys.argv.insert(1, "transmitter")
    cli()

