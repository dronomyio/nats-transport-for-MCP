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

# Add parent directory to path if running from examples directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uns_mcp_nats import UNSMcpNatsClient, UNSMcpNatsConfig

try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None
    print("Warning: rich not available. Install with 'pip install rich'")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uns-mcp-nats-example")


async def run_simple_workflow():
    """Run a simple workflow example using UNS-MCP with NATS transport."""
    # Load configuration from .env file or environment variables
    config = UNSMcpNatsConfig.from_dotenv()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold]UNS-MCP with NATS Transport: Simple Workflow Example[/bold]",
            border_style="green"
        ))
        
        console.print(f"Connecting to UNS-MCP server via NATS at [bold]{config.nats.url}[/bold]")
        console.print(f"Service name: [bold]{config.nats.service_name}[/bold]")
    else:
        print("\nUNS-MCP with NATS Transport: Simple Workflow Example")
        print(f"Connecting to UNS-MCP server via NATS at {config.nats.url}")
        print(f"Service name: {config.nats.service_name}")
    
    # Create and connect client
    client = UNSMcpNatsClient(config)
    await client.connect()
    
    try:
        if not client.session:
            logger.error("Failed to connect to server")
            return
            
        # Step 1: List sources
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]Step 1: Listing available sources[/bold cyan]")
        else:
            print("\nStep 1: Listing available sources")
            
        result = await client.session.call_tool("list_sources", {})
        for item in result.content:
            if RICH_AVAILABLE:
                console.print(item.text)
            else:
                print(item.text)
        
        # Step 2: List destinations
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]Step 2: Listing available destinations[/bold cyan]")
        else:
            print("\nStep 2: Listing available destinations")
            
        result = await client.session.call_tool("list_destinations", {})
        for item in result.content:
            if RICH_AVAILABLE:
                console.print(item.text)
            else:
                print(item.text)
        
        # Step 3: List workflows
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]Step 3: Listing existing workflows[/bold cyan]")
        else:
            print("\nStep 3: Listing existing workflows")
            
        result = await client.session.call_tool("list_workflows", {})
        for item in result.content:
            if RICH_AVAILABLE:
                console.print(item.text)
            else:
                print(item.text)
        
        if RICH_AVAILABLE:
            console.print("\n[bold green]Example completed successfully![/bold green]")
        else:
            print("\nExample completed successfully!")
            
        print("\nTo create and run an actual workflow, you would need to:")
        print("1. Create a source connector (e.g., S3)")
        print("2. Create a destination connector (e.g., MongoDB)")
        print("3. Create a workflow using the 'create_workflow' tool")
        print("4. Run the workflow and monitor its progress")
    finally:
        # Clean up resources
        await client.cleanup()


async def main():
    """Main function."""
    try:
        await run_simple_workflow()
    except Exception as e:
        logger.error(f"Error running example: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n[bold]Example terminated by user[/bold]")
        else:
            print("\nExample terminated by user")