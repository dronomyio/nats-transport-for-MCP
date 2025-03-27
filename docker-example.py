"""
Docker example for NATS transport with MCP.

This is a simple example that runs both the server and client in the same process,
making it easier to run in Docker.
"""

import asyncio
import logging
import os
import sys
from contextlib import AsyncExitStack

import anyio
from nats.aio.client import Client as NatsClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Echo tool definition
async def echo(text: str) -> str:
    """Echo the input text back to the client."""
    return text

async def run_server(nats_url):
    """Run a simple server that publishes an echo service."""
    # Connect to NATS
    nc = NatsClient()
    await nc.connect(nats_url)
    logger.info(f"Server connected to NATS at {nats_url}")
    
    # Set up a service for echo
    async def handle_echo_request(msg):
        logger.info(f"Received echo request: {msg.data.decode()}")
        # Reply with the same data
        await msg.respond(msg.data)
        logger.info(f"Sent echo response: {msg.data.decode()}")
    
    # Subscribe to the echo subject
    sub = await nc.subscribe("mcp.service.echo", cb=handle_echo_request)
    logger.info("Server subscribed to mcp.service.echo")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Server shutting down")
    finally:
        await sub.unsubscribe()
        await nc.close()

async def run_client(nats_url):
    """Run a client that calls the echo service."""
    # Wait for the server to start
    await asyncio.sleep(5)
    
    # Connect to NATS
    nc = NatsClient()
    await nc.connect(nats_url)
    logger.info(f"Client connected to NATS at {nats_url}")
    
    # Send a request to the echo service
    try:
        message = "Hello via NATS service!"
        logger.info(f"Sending echo request: {message}")
        response = await nc.request("mcp.service.echo", message.encode(), timeout=10)
        response_text = response.data.decode()
        logger.info(f"Received echo response: {response_text}")
        
        # Verify the response
        if response_text == message:
            logger.info("Success! The echo service is working correctly")
        else:
            logger.error(f"Error: Expected '{message}' but got '{response_text}'")
    except Exception as e:
        logger.exception(f"Error calling echo service: {e}")
    finally:
        await nc.close()
        logger.info("Client disconnected")

async def run_example():
    """Run both server and client."""
    # Get NATS URL from environment or use default
    nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
    
    # Start the server and client
    server_task = asyncio.create_task(run_server(nats_url))
    
    # Run the client
    try:
        await run_client(nats_url)
    finally:
        # Cancel the server task when done
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

def main():
    """Main entry point."""
    try:
        asyncio.run(run_example())
    except KeyboardInterrupt:
        logger.info("Example stopped by user")

if __name__ == "__main__":
    main()