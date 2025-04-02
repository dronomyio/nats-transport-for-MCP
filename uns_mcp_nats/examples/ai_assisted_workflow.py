#!/usr/bin/env python3
"""
UNS-MCP with NATS Transport: AI-Assisted Workflow Example

This example demonstrates how to:
1. Connect to the UNS-MCP server via NATS transport
2. Use Claude to create and manage document processing workflows
3. Have an AI-powered conversation about document processing
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path if running from examples directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uns_mcp_nats import UNSMcpNatsClient, UNSMcpNatsConfig

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Error: anthropic not available. Install with 'pip install anthropic'")
    sys.exit(1)

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
logger = logging.getLogger("uns-mcp-nats-ai-example")


async def run_ai_assisted_workflow():
    """Run an AI-assisted workflow using Claude and UNS-MCP via NATS."""
    # Verify necessary environment variables
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        error_msg = "Error: ANTHROPIC_API_KEY environment variable not set"
        if RICH_AVAILABLE:
            console.print(f"[bold red]{error_msg}[/bold red]")
        else:
            print(error_msg)
        return
    
    # Load configuration from .env file or environment variables
    config = UNSMcpNatsConfig.from_dotenv()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold]UNS-MCP with NATS Transport: AI-Assisted Workflow Example[/bold]",
            border_style="blue"
        ))
    else:
        print("\nUNS-MCP with NATS Transport: AI-Assisted Workflow Example")
    
    # Create and connect client
    client = UNSMcpNatsClient(config)
    await client.connect()
    
    try:
        if not client.session:
            logger.error("Failed to connect to server")
            return
            
        # Use client's built-in chat loop with custom initial prompt
        client.history = [{
            "role": "user", 
            "content": "Help me create a document processing workflow using Unstructured API. "
                      "Start by showing me available sources and destinations."
        }]
        
        # Run the chat loop
        await client.chat_loop()
    finally:
        # Clean up resources
        await client.cleanup()


async def main():
    """Main function."""
    try:
        await run_ai_assisted_workflow()
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