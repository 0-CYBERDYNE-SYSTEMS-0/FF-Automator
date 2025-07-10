#!/usr/bin/env python3
"""
Demo script showing how to use the enhanced CLI interface
"""

import sys
import os

# Add the package to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mlx_use.cli.service import InteractiveCLI
import asyncio


async def demo():
	"""Demonstrate CLI usage"""
	print('🚀 Starting macOS-use Enhanced CLI Demo')
	print('=' * 50)

	# Initialize CLI
	cli = InteractiveCLI()

	print('🎯 Demo Commands to try:')
	print("  • 'open calculator'")
	print("  • 'take a screenshot'")
	print("  • 'help' - for help")
	print("  • 'sessions' - list sessions")
	print("  • 'new session demo' - create named session")
	print("  • 'quit' - to exit")
	print()

	# Run the CLI
	await cli.run()


if __name__ == '__main__':
	asyncio.run(demo())
