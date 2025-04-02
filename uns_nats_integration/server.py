#!/usr/bin/env python3
"""
UNS-MCP Server with NATS transport

This module implements a MCP server that provides Unstructured API tools
and connectors while using NATS.io as the transport mechanism.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add parent directory to path to access UNS-MCP and nats-transport
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from typing import AsyncIterator, Dict, List, Optional, Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.fastmcp import Context, FastMCP
    
try:
    from unstructured_client import UnstructuredClient
    UNSTRUCTURED_CLIENT_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_CLIENT_AVAILABLE = False
    print("Warning: unstructured_client not available. Install with 'pip install unstructured-client'")

# Import local modules
from uns_nats_integration.config import Config, UnstructuredConfig
from uns_nats_integration.connectors import register_connectors

# Import NATS transport
try:
    from nats-transport.src.server import nats_server, NatsServerParameters
    NATS_TRANSPORT_AVAILABLE = True
except ImportError:
    NATS_TRANSPORT_AVAILABLE = False
    print("Warning: nats-transport not available. Make sure the module is in your path.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("uns-nats-server")


def load_environment_variables() -> bool:
    """Load environment variables from .env file.
    
    Returns:
        True if all required variables are present, False otherwise
    """
    load_dotenv(override=True)
    required_vars = ["NATS_URL"]
    
    if UNSTRUCTURED_CLIENT_AVAILABLE:
        required_vars.append("UNSTRUCTURED_API_KEY")

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage Unstructured API client lifecycle"""
    context = {}
    
    if UNSTRUCTURED_CLIENT_AVAILABLE:
        config = Config.from_env()
        
        if config.unstructured and config.unstructured.api_key:
            try:
                client = UnstructuredClient(api_key_auth=config.unstructured.api_key)
                context["client"] = client
                logger.info("Unstructured API client initialized")
                
                if config.unstructured.debug_requests:
                    try:
                        from UNS-MCP.uns_mcp.custom_http_client import CustomHttpClient
                        import httpx
                        context["client"] = UnstructuredClient(
                            api_key_auth=config.unstructured.api_key, 
                            async_client=CustomHttpClient(httpx.AsyncClient())
                        )
                        logger.info("Debug HTTP client enabled for Unstructured API")
                    except ImportError:
                        logger.warning("Could not import custom HTTP client for debugging")
            except Exception as e:
                logger.error(f"Error initializing Unstructured API client: {e}")
    
    try:
        yield context
    finally:
        # No cleanup needed for the API client
        pass


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server instance"""
    # Create MCP server instance
    mcp = FastMCP(
        "Unstructured API via NATS",
        lifespan=app_lifespan,
        dependencies=["unstructured-client", "python-dotenv", "nats-py"],
    )
    
    # Register UNS-MCP connectors
    registered = register_connectors(mcp)
    logger.info(f"Registered connectors: {', '.join(registered)}")
    
    # Register UNS-MCP tools
    try:
        register_uns_tools(mcp)
        logger.info("UNS-MCP tools registered")
    except Exception as e:
        logger.error(f"Error registering UNS-MCP tools: {e}")
    
    return mcp


def register_uns_tools(mcp: FastMCP) -> None:
    """Register UNS-MCP tools with the MCP server"""
    try:
        # Try to import core tools from UNS-MCP
        from UNS-MCP.uns_mcp.server import (
            list_sources, get_source_info, list_destinations,
            get_destination_info, list_workflows, get_workflow_info,
            create_workflow, run_workflow, update_workflow,
            delete_workflow, list_jobs, get_job_info, cancel_job,
        )
        
        # Register all tools
        tools = [
            list_sources, get_source_info, list_destinations,
            get_destination_info, list_workflows, get_workflow_info,
            create_workflow, run_workflow, update_workflow,
            delete_workflow, list_jobs, get_job_info, cancel_job,
        ]
        
        for tool in tools:
            mcp.add_tool(tool)
            
    except ImportError as e:
        logger.error(f"Could not import UNS-MCP tools: {e}")
        raise


async def run_server():
    """Run the UNS-MCP server with NATS transport"""
    if not load_environment_variables():
        logger.error("Missing required environment variables. Exiting.")
        return
    
    if not NATS_TRANSPORT_AVAILABLE:
        logger.error("NATS transport not available. Cannot start server.")
        return
    
    # Get configuration
    config = Config.from_env()
    
    # Create and configure the MCP server
    mcp = create_mcp_server()
    
    # Configure NATS server
    nats_params = NatsServerParameters(
        url=config.nats.url,
        service_name=config.nats.service_name,
        server_id=f"{config.nats.server_id_prefix}-{os.getpid()}",
        description="Unstructured API MCP Server",
        version="1.0.0",
        metadata={
            "provider": "unstructured-api",
            "transport": "nats",
        },
        queue_group=config.nats.queue_group,
    )
    
    logger.info(f"Starting UNS-MCP server with NATS transport at {config.nats.url}")
    logger.info(f"Service name: {config.nats.service_name}")
    
    try:
        # Start the server with NATS transport
        async with nats_server(nats_params) as (read_stream, write_stream):
            mcp_server = mcp._mcp_server
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error running server: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down")