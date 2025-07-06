#!/usr/bin/env python3
"""
macOS-use Interactive CLI
A natural language interface for controlling macOS applications
"""

import sys
import os

# Add the package to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mlx_use.cli.service import main

if __name__ == "__main__":
	main()