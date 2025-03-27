"""
Example demonstrating how to use NATS transport with MCP.

This example shows:
1. Setting up a NATS-based MCP server
2. Connecting to it with a NATS-based MCP client
3. Exchanging messages between them using the NATS services API

Requirements:
- NATS server running (e.g., `docker run -p 4222:4222 nats`)
- MCP Python SDK installed

Run this example:
```
python -m examples.simple_example
```
"""

import asyncio
import logging
from contextlib import AsyncExitStack

import sys
import os

# Add the parent directory to sys.path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import anyio
from src.client import NatsClientParameters, nats_client
from mcp.client.session import ClientSession
from mcp.server.fastmcp.server import FastMcpServer
from src.server import NatsServerParameters, nats_server
from mcp.server.fastmcp.tools import Tool, tool
from mcp.shared.session import Session

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Define a simple echo tool for the server
@tool
async def echo(text: str) -> str:
    """Echo the input text back to the client."""
    return text


async def run_server():
    """Run a simple MCP server using NATS transport."""
    # Create the server
    server = FastMcpServer()
    
    # Register our echo tool
    server.tools.register(echo)
    
    # Configure NATS transport with service
    nats_params = NatsServerParameters(
        url="nats://localhost:4222",
        service_name="mcp.service",
        server_id="echo-server-1",
    )
    
    logger.info("Starting MCP server with NATS transport")
    
    # Start the server using NATS transport
    async with nats_server(nats_params) as (read_stream, write_stream):
        # Create a session and run the server
        session = Session()
        try:
            await server.run(session, read_stream, write_stream)
        except Exception as e:
            logger.exception(f"Server error: {e}")


async def run_client():
    """Run a simple MCP client using NATS transport."""
    # Wait a bit to ensure server is running
    await asyncio.sleep(1)
    
    # Configure NATS transport with service
    nats_params = NatsClientParameters(
        url="nats://localhost:4222",
        service_name="mcp.service",
        client_id="echo-client-1",
    )
    
    logger.info("Starting MCP client with NATS transport")
    
    # Connect to the server using NATS transport
    async with nats_client(nats_params) as (read_stream, write_stream):
        # Create a client session
        client = ClientSession()
        
        # Run initialization
        await client.initialize(read_stream, write_stream)
        
        # Get the list of tools
        tools = await client.list_tools()
        logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
        
        # Call the echo tool
        result = await client.call_tool("echo", {"text": "Hello via NATS service!"})
        logger.info(f"Echo result: {result.content[0].text}")


async def run_example():
    """Run both server and client using an exit stack."""
    async with AsyncExitStack() as stack:
        # Start the server in a separate task
        server_task = asyncio.create_task(run_server())
        
        # Run the client
        await run_client()
        
        # Cancel the server task when done
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


def main():
    """Main entry point."""
    try:
        anyio.run(run_example)
    except KeyboardInterrupt:
        logger.info("Example stopped by user")


if __name__ == "__main__":
    main()