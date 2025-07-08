#!/usr/bin/env python3
"""
Test script to verify WebSocket connection handling fixes
"""

import asyncio
import websockets
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection and disconnection handling"""
    
    # Test basic connection
    try:
        uri = "ws://localhost:8080/ws/test_client_123"
        logger.info(f"Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            logger.info("Connection established")
            
            # Send a ping message
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            logger.info("Sent ping message")
            
            # Wait for pong response
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
            # Test abrupt disconnection
            logger.info("Closing connection abruptly...")
            await websocket.close()
            logger.info("Connection closed")
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")

async def test_multiple_rapid_connections():
    """Test rapid connection/disconnection cycles"""
    
    for i in range(5):
        try:
            uri = f"ws://localhost:8080/ws/test_client_{i}"
            logger.info(f"Test {i+1}/5: Connecting to {uri}")
            
            async with websockets.connect(uri) as websocket:
                # Send a message and immediately disconnect
                message = {"type": "ping"}
                await websocket.send(json.dumps(message))
                
                # Wait briefly then close
                await asyncio.sleep(0.1)
                await websocket.close()
                
            logger.info(f"Test {i+1}/5: Completed successfully")
            
        except Exception as e:
            logger.error(f"Test {i+1}/5: Failed with error: {e}")

async def main():
    logger.info("Starting WebSocket connection tests...")
    
    # Test 1: Basic connection
    logger.info("=== Test 1: Basic Connection ===")
    await test_websocket_connection()
    
    await asyncio.sleep(1)
    
    # Test 2: Multiple rapid connections
    logger.info("=== Test 2: Multiple Rapid Connections ===")
    await test_multiple_rapid_connections()
    
    logger.info("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())