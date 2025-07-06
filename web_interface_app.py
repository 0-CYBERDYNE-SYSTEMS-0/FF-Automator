#!/usr/bin/env python3
"""
Launch script for the elegant JavaScript interface to macOS automation.
This serves as an alternative to the Gradio interface with enhanced UX.
"""

import os
import sys
import asyncio
import signal
import webbrowser
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi.staticfiles import StaticFiles

# Import the FastAPI app
from web_interface.api.main import app

def setup_static_files():
	"""Mount static files for the web interface"""
	static_path = project_root / "web_interface" / "static"
	if static_path.exists():
		app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
	else:
		print(f"Warning: Static files directory not found at {static_path}")

def open_browser(host: str, port: int):
	"""Open the web interface in the default browser"""
	url = f"http://{host}:{port}"
	print(f"🌐 Opening web interface at {url}")
	webbrowser.open(url)

def signal_handler(signum, frame):
	"""Handle shutdown signals gracefully"""
	print("\n🛑 Shutting down web interface...")
	sys.exit(0)

async def async_main():
	"""Async main function"""
	# Configuration
	host = os.getenv('WEB_HOST', '127.0.0.1')
	port = int(os.getenv('WEB_PORT', 8080))
	
	# Setup static files
	setup_static_files()
	
	print("🚀 Starting macOS Automation - Elegant Web Interface")
	print(f"📁 Project root: {project_root}")
	print(f"🌐 Server: http://{host}:{port}")
	print("💡 This interface provides a modern, elegant alternative to the Gradio app")
	print("🔄 The original Gradio app remains unchanged and can still be accessed via 'python gradio_app/app.py'")
	print("\n" + "="*60)
	
	# Schedule browser opening after a short delay
	async def open_browser_delayed():
		await asyncio.sleep(3)
		open_browser(host, port)
	
	# Create task for browser opening
	browser_task = asyncio.create_task(open_browser_delayed())
	
	# Create and configure uvicorn
	config = uvicorn.Config(
		app=app,
		host=host,
		port=port,
		log_level="info",
		access_log=True,
		reload=False,  # Set to True for development
		reload_dirs=[str(project_root / "web_interface")] if False else None
	)
	
	server = uvicorn.Server(config)
	
	try:
		# Start the server
		await server.serve()
	except KeyboardInterrupt:
		print("\n🛑 Server stopped by user")
		browser_task.cancel()

def main():
	"""Main entry point for the web interface"""
	# Register signal handlers
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	
	try:
		asyncio.run(async_main())
	except KeyboardInterrupt:
		print("\n🛑 Server stopped by user")
	except Exception as e:
		print(f"❌ Error starting server: {e}")
		sys.exit(1)

if __name__ == "__main__":
	main()