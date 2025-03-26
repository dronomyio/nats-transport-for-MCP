"""
Distributed MCP Example with NATS Transport

This example demonstrates using NATS as a transport layer for MCP in a distributed scenario:
- Multiple MCP servers with different tools
- Multiple MCP clients connecting through NATS
- Automatic service discovery and load balancing

Requirements:
- NATS server running (e.g., `docker run -p 4222:4222 nats`)
- MCP Python SDK installed

Run this example:
```
python -m examples.fastmcp.distributed_nats
```
"""

import asyncio
import logging
import random
import time
from contextlib import AsyncExitStack
from typing import List, Dict, Any

import anyio
import sys
import os

# Add the parent directory to sys.path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.client import NatsClientParameters, nats_client
from mcp.client.session import ClientSession
from mcp.server.fastmcp.prompts import Prompt, prompt
from mcp.server.fastmcp.server import FastMcpServer
from mcp.server.fastmcp.tools import Tool, tool
from src.server import NatsServerParameters, nats_server
from mcp.shared.session import Session
from mcp.types import TextContent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Define different servers with specialized tools

# Weather tools for server 1
@tool
async def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Simulate API call
    await asyncio.sleep(0.5)
    conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
    temperature = random.randint(0, 35)
    return f"Weather in {location}: {random.choice(conditions)}, {temperature}°C"

@tool
async def get_forecast(location: str, days: int = 3) -> Dict[str, Any]:
    """Get a weather forecast for a number of days."""
    # Simulate API call
    await asyncio.sleep(0.8)
    conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
    forecast = {}
    for i in range(days):
        day = time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400 * i))
        forecast[day] = {
            "condition": random.choice(conditions),
            "temperature": random.randint(0, 35),
            "humidity": random.randint(30, 90)
        }
    return forecast

# Calculator tools for server 2
@tool
async def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@tool
async def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

@tool
async def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@tool
async def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Text manipulation tools for server 3
@tool
async def reverse_text(text: str) -> str:
    """Reverse the input text."""
    return text[::-1]

@tool
async def count_words(text: str) -> int:
    """Count the number of words in the text."""
    return len(text.split())

@tool
async def to_uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

@tool
async def to_lowercase(text: str) -> str:
    """Convert text to lowercase."""
    return text.lower()

# Define server creation functions
async def create_weather_server():
    """Create a server with weather tools."""
    server = FastMcpServer()
    server.tools.register(get_weather)
    server.tools.register(get_forecast)
    
    # Define a weather prompt
    @prompt
    def weather_prompt(location: str = "New York"):
        """Get weather information for a location."""
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"What's the weather like in {location}?"
                }
            }
        ]
    
    server.prompts.register(weather_prompt)
    return server

async def create_calculator_server():
    """Create a server with calculator tools."""
    server = FastMcpServer()
    server.tools.register(add)
    server.tools.register(subtract)
    server.tools.register(multiply)
    server.tools.register(divide)
    return server

async def create_text_server():
    """Create a server with text manipulation tools."""
    server = FastMcpServer()
    server.tools.register(reverse_text)
    server.tools.register(count_words)
    server.tools.register(to_uppercase)
    server.tools.register(to_lowercase)
    return server

# Run server with specified configuration
async def run_server(server_type: str, request_subject: str, response_subject: str):
    """Run an MCP server with the specified configuration."""
    # Create the appropriate server
    if server_type == "weather":
        server = await create_weather_server()
        logger.info("Starting Weather MCP server")
    elif server_type == "calculator":
        server = await create_calculator_server()
        logger.info("Starting Calculator MCP server")
    elif server_type == "text":
        server = await create_text_server()
        logger.info("Starting Text MCP server")
    else:
        raise ValueError(f"Unknown server type: {server_type}")
    
    # Configure NATS transport
    nats_params = NatsServerParameters(
        request_subject=request_subject,
        response_subject=response_subject,
        server_id=f"mcp-{server_type}-server",
    )
    
    # Start the server using NATS transport
    async with nats_server(nats_params) as (read_stream, write_stream):
        # Create a session and run the server
        session = Session()
        try:
            await server.run(session, read_stream, write_stream)
        except Exception as e:
            logger.exception(f"Server error: {e}")

# Client to interact with all servers
async def run_client(client_id: int, request_subject: str, response_subject: str):
    """Run an MCP client that interacts with all servers."""
    # Wait to ensure servers are running
    await asyncio.sleep(2)
    
    # Configure NATS transport
    nats_params = NatsClientParameters(
        request_subject=request_subject,
        response_subject=response_subject,
        client_id=f"mcp-client-{client_id}",
    )
    
    logger.info(f"Starting MCP client {client_id}")
    
    # Connect to the servers using NATS transport
    async with nats_client(nats_params) as (read_stream, write_stream):
        # Create a client session
        client = ClientSession()
        
        # Run initialization
        await client.initialize(read_stream, write_stream)
        
        # Get the list of tools (from all servers via NATS)
        tools = await client.list_tools()
        logger.info(f"Client {client_id} available tools: {[tool.name for tool in tools.tools]}")
        
        # Try calling tools from different servers
        try:
            # Call weather tool
            weather_result = await client.call_tool("get_weather", {"location": "London"})
            logger.info(f"Client {client_id} weather result: {weather_result.content[0].text}")
            
            # Call calculator tool
            calc_result = await client.call_tool("add", {"a": 5, "b": 3})
            logger.info(f"Client {client_id} calculator result: {calc_result.content[0].text}")
            
            # Call text tool
            text_result = await client.call_tool("to_uppercase", {"text": "hello world"})
            logger.info(f"Client {client_id} text result: {text_result.content[0].text}")
            
            # Try to get available prompts
            try:
                prompts = await client.list_prompts()
                if prompts.prompts:
                    logger.info(f"Client {client_id} available prompts: {[p.name for p in prompts.prompts]}")
                    
                    # Try using a weather prompt
                    prompt_result = await client.get_prompt("weather_prompt", {"location": "Tokyo"})
                    logger.info(f"Client {client_id} prompt result: {prompt_result.messages[0].content.text}")
            except Exception as e:
                logger.error(f"Client {client_id} error getting prompts: {e}")
                
        except Exception as e:
            logger.exception(f"Client {client_id} error: {e}")

async def run_example():
    """Run the complete distributed example."""
    # Define shared NATS subjects
    request_subject = "mcp.request"
    response_subject = "mcp.response"
    
    async with AsyncExitStack() as stack:
        # Start all servers in separate tasks
        server_tasks = [
            asyncio.create_task(run_server("weather", request_subject, response_subject)),
            asyncio.create_task(run_server("calculator", request_subject, response_subject)),
            asyncio.create_task(run_server("text", request_subject, response_subject)),
        ]
        
        # Start multiple clients
        client_tasks = [
            asyncio.create_task(run_client(i, request_subject, response_subject))
            for i in range(3)  # Create 3 clients
        ]
        
        # Wait for clients to complete
        for client_task in client_tasks:
            try:
                await client_task
            except Exception as e:
                logger.exception(f"Client task error: {e}")
        
        # Cancel server tasks when done
        for server_task in server_tasks:
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