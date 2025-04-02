#!/usr/bin/env python3
"""
UNS-MCP Client with NATS transport

This module implements a client for the UNS-MCP server using NATS.io as
the transport mechanism, allowing LLM-powered interaction with the
Unstructured API tools and connectors.
"""

import asyncio
import logging
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path to access parent modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic not available. Install with 'pip install anthropic'")

from dotenv import load_dotenv
from mcp import ClientSession

try:
    from rich import print
    from rich.prompt import Confirm, Prompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: rich not available. Install with 'pip install rich'")

# Import local config
from uns_nats_integration.config import Config

# Import NATS transport
try:
    from nats-transport.src.client import nats_client, NatsClientParameters
    NATS_TRANSPORT_AVAILABLE = True
except ImportError:
    NATS_TRANSPORT_AVAILABLE = False
    print("Warning: nats-transport not available. Make sure the module is in your path.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("uns-nats-client")

# Load environment variables
load_dotenv()


class UNSMcpClient:
    """Client for UNS-MCP server with NATS transport and LLM integration"""
    
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.history = []
        self.available_tools = []
        
        # Initialize LLM client if available
        if ANTHROPIC_AVAILABLE:
            self.anthropic = Anthropic()
        else:
            self.anthropic = None
            logger.warning("Anthropic client not available")
    
    async def connect_to_server(self, nats_url: str, service_name: str):
        """Connect to UNS-MCP server via NATS transport
        
        Args:
            nats_url: URL of the NATS server
            service_name: Name of the MCP service
        """
        if not NATS_TRANSPORT_AVAILABLE:
            logger.error("NATS transport not available. Cannot connect to server.")
            return
        
        # Configure NATS client
        nats_params = NatsClientParameters(
            url=nats_url,
            service_name=service_name,
            client_id=f"uns-mcp-client-{os.getpid()}"
        )
        
        logger.info(f"Connecting to UNS-MCP server at {nats_url}")
        
        # Create NATS transport
        nats_transport = await self.exit_stack.enter_async_context(nats_client(nats_params))
        
        # Initialize session
        self.session = ClientSession(*nats_transport)
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"Connected to server with tools: {[tool.name for tool in tools]}")
        
        self.available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]

    async def process_query(self, query: str, confirm_tool_use: bool = True):
        """Process a query using Claude and available tools
        
        Args:
            query: The user's query to process
            confirm_tool_use: Whether to confirm tool use before execution
        """
        if not self.anthropic:
            logger.error("Anthropic client not available")
            return
        
        self.history.append({"role": "user", "content": query})

        # Get response from Claude
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=self.history,
            tools=self.available_tools,
        )
        logger.debug(f"ASSISTANT response: {response}")
        
        content_to_process = response.content.copy()
        max_model_calls = 10
        model_call = 1
        
        while content_to_process and model_call <= max_model_calls:
            content_item = content_to_process.pop(0)
            self.history.append({"role": "assistant", "content": [content_item]})

            if content_item.type == "text":
                if RICH_AVAILABLE:
                    print(f"\n[bold red]ASSISTANT[/bold red]\n{content_item.text}")
                else:
                    print(f"\nASSISTANT\n{content_item.text}")
            elif content_item.type == "tool_use":
                tool_name = content_item.name
                tool_args = content_item.input

                # Confirm tool execution if needed
                should_execute_tool = True
                if confirm_tool_use:
                    if RICH_AVAILABLE:
                        should_execute_tool = Confirm.ask(
                            f"\n[bold cyan]TOOL CALL[/bold cyan]\nAccept execution of "
                            f"{tool_name} with args {tool_args}?",
                            default=True,
                        )
                    else:
                        print(f"\nTOOL CALL\nExecute {tool_name} with args {tool_args}? (y/n) [y]: ", end="")
                        answer = input().lower()
                        should_execute_tool = answer != "n"
                else:
                    if RICH_AVAILABLE:
                        print(f"\n[bold cyan]TOOL CALL[/bold cyan]\n"
                              f"Executing {tool_name} with args {tool_args}\n")
                    else:
                        print(f"\nTOOL CALL\nExecuting {tool_name} with args {tool_args}\n")

                if should_execute_tool:
                    # Execute the tool
                    result = await self.session.call_tool(tool_name, tool_args)
                    logger.debug(f"TOOL result: {result}")

                    # Display the result
                    for result_item in result.content:
                        if RICH_AVAILABLE:
                            print(f"\n[bold cyan]TOOL OUTPUT[/bold cyan]:\n{result_item.text}\n")
                        else:
                            print(f"\nTOOL OUTPUT:\n{result_item.text}\n")

                    # Add the result to history
                    self.history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content_item.id,
                            "content": result.content,
                        }],
                    })
                else:
                    # User declined tool execution
                    message = f"User declined execution of {tool_name} with args {tool_args}"
                    self.history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content_item.id,
                            "content": message,
                            "is_error": True,
                        }],
                    })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=self.history,
                    tools=self.available_tools,
                )
                model_call += 1
                logger.debug(f"ASSISTANT response: {response}")
                content_to_process.extend(response.content)
            else:
                logger.error(f"Unsupported content type: {content_item.type}")

    async def chat_loop(self, confirm_tool_use: bool = True):
        """Run an interactive chat loop
        
        Args:
            confirm_tool_use: Whether to confirm tool use before execution
        """
        logger.info("UNS-MCP Client Started!")
        logger.info("Type your queries or 'quit' to exit.")

        while True:
            try:
                if RICH_AVAILABLE:
                    query = Prompt.ask("\n[bold green]Query[/bold green] (q/quit to end chat)")
                else:
                    print("\nQuery (q/quit to end chat): ", end="")
                    query = input()
                    
                query = query.strip()

                if query.lower() in ["quit", "q"]:
                    break

                if not query:
                    continue

                await self.process_query(query, confirm_tool_use)
            except Exception as e:
                logger.error(f"Error: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client"""
    # Check for required modules
    if not NATS_TRANSPORT_AVAILABLE:
        logger.error("NATS transport not available. Cannot run client.")
        return
    
    if not ANTHROPIC_AVAILABLE:
        logger.error("Anthropic client not available. Cannot run client.")
        return
    
    # Get configuration
    config = Config.from_env()
    
    client = UNSMcpClient()
    try:
        await client.connect_to_server(config.nats.url, config.nats.service_name)
        confirm_tool_use = os.getenv("CONFIRM_TOOL_USE", "true").lower() == "true"
        await client.chat_loop(confirm_tool_use=confirm_tool_use)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client shutting down")