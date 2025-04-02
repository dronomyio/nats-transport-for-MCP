#!/usr/bin/env python3
"""
UNS-MCP with NATS Transport: Simple Workflow Example

This example demonstrates how to:
1. Connect to the UNS-MCP server via NATS transport
2. List available sources and destinations
3. Create a simple workflow
4. Run the workflow and monitor its progress
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parents[1])
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from rich import print
from rich.console import Console
from rich.panel import Panel

# Import NATS transport
from nats-transport.src.client import nats_client, NatsClientParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uns-nats-example")

# Load environment variables
load_dotenv()

console = Console()

async def run_simple_workflow():
    """Run a simple workflow example using UNS-MCP with NATS transport"""
    # Get NATS parameters from environment
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    service_name = os.getenv("NATS_SERVICE_NAME", "uns.mcp.service")
    
    console.print(Panel.fit(
        "[bold]UNS-MCP with NATS Transport: Simple Workflow Example[/bold]",
        border_style="green"
    ))
    
    console.print(f"Connecting to UNS-MCP server via NATS at [bold]{nats_url}[/bold]")
    console.print(f"Service name: [bold]{service_name}[/bold]")
    
    # Configure NATS client
    nats_params = NatsClientParameters(
        url=nats_url,
        service_name=service_name,
        client_id=f"uns-mcp-example-{os.getpid()}"
    )
    
    # Create transport using NATS
    async with nats_client(nats_params) as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        
        # List available tools
        response = await session.list_tools()
        tools = response.tools
        
        console.print("\n[bold yellow]Available Tools:[/bold yellow]")
        for tool in tools:
            console.print(f"- {tool.name}")
        
        # Step 1: List sources
        console.print("\n[bold cyan]Step 1: Listing available sources[/bold cyan]")
        result = await session.call_tool("list_sources", {})
        for item in result.content:
            console.print(item.text)
        
        # Step 2: List destinations
        console.print("\n[bold cyan]Step 2: Listing available destinations[/bold cyan]")
        result = await session.call_tool("list_destinations", {})
        for item in result.content:
            console.print(item.text)
        
        # Step 3: List workflows
        console.print("\n[bold cyan]Step 3: Listing existing workflows[/bold cyan]")
        result = await session.call_tool("list_workflows", {})
        for item in result.content:
            console.print(item.text)
        
        console.print("\n[bold green]Example completed successfully![/bold green]")
        console.print("To create and run an actual workflow, you would need to:")
        console.print("1. Create a source connector (e.g., S3)")
        console.print("2. Create a destination connector (e.g., MongoDB)")
        console.print("3. Create a workflow using the 'create_workflow' tool")
        console.print("4. Run the workflow and monitor its progress")
        

async def run_ai_assisted_workflow():
    """Run an AI-assisted workflow using Claude and UNS-MCP via NATS"""
    # Verify necessary environment variables
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        console.print("[bold red]Error: ANTHROPIC_API_KEY environment variable not set[/bold red]")
        return
    
    # Get NATS parameters from environment
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    service_name = os.getenv("NATS_SERVICE_NAME", "uns.mcp.service")
    
    console.print(Panel.fit(
        "[bold]UNS-MCP with NATS Transport: AI-Assisted Workflow Example[/bold]",
        border_style="blue"
    ))
    
    # Initialize Anthropic client
    anthropic = Anthropic()
    
    # Configure NATS client
    nats_params = NatsClientParameters(
        url=nats_url,
        service_name=service_name,
        client_id=f"uns-mcp-ai-example-{os.getpid()}"
    )
    
    # Create transport using NATS
    async with nats_client(nats_params) as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        
        # List available tools
        response = await session.list_tools()
        tools = response.tools
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]
        
        # Initial prompt to Claude
        message_history = [{
            "role": "user", 
            "content": "Help me create a document processing workflow using Unstructured API. "
                      "Start by showing me available sources and destinations."
        }]
        
        # Get initial response from Claude
        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=message_history,
            tools=available_tools,
        )
        
        # Process Claude's response
        content_to_process = response.content.copy()
        
        while content_to_process:
            content_item = content_to_process.pop(0)
            message_history.append({"role": "assistant", "content": [content_item]})
            
            if content_item.type == "text":
                console.print(f"\n[bold purple]CLAUDE:[/bold purple] {content_item.text}")
            elif content_item.type == "tool_use":
                tool_name = content_item.name
                tool_args = content_item.input
                
                console.print(f"\n[bold yellow]TOOL CALL:[/bold yellow] {tool_name}")
                console.print(f"[bold yellow]ARGS:[/bold yellow] {tool_args}")
                
                # Execute the tool
                result = await session.call_tool(tool_name, tool_args)
                
                # Display the result
                for result_item in result.content:
                    console.print(f"\n[bold green]TOOL OUTPUT:[/bold green]\n{result_item.text}\n")
                
                # Add the result to history
                message_history.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": content_item.id,
                        "content": result.content,
                    }],
                })
                
                # Get next response from Claude
                response = anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=message_history,
                    tools=available_tools,
                )
                
                content_to_process.extend(response.content)


async def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--ai":
        await run_ai_assisted_workflow()
    else:
        await run_simple_workflow()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold]Example terminated by user[/bold]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")