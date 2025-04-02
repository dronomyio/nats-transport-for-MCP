"""Server module for UNS-MCP with NATS transport."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional, Any

from mcp.server import Server
from mcp.server.fastmcp import Context, FastMCP

try:
    from unstructured_client import UnstructuredClient
    UNSTRUCTURED_CLIENT_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_CLIENT_AVAILABLE = False
    logging.warning("unstructured_client not available. Install with 'pip install unstructured-client'")

# Import local configuration
from .config import UNSMcpNatsConfig

# Import NATS transport from parent project
try:
    from nats_transport import nats_server, NatsServerParameters
    NATS_TRANSPORT_AVAILABLE = True
except ImportError:
    try:
        # Try importing from parent project
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from src import nats_server, NatsServerParameters
        NATS_TRANSPORT_AVAILABLE = True
    except ImportError:
        NATS_TRANSPORT_AVAILABLE = False
        logging.warning("nats_transport not available. Make sure the module is in your path.")

logger = logging.getLogger("uns-mcp-nats-server")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage Unstructured API client lifecycle.
    
    Args:
        server: The FastMCP server instance.
        
    Yields:
        Dict containing the Unstructured API client.
    """
    context = {}
    
    if UNSTRUCTURED_CLIENT_AVAILABLE:
        config = UNSMcpNatsConfig.from_env()
        
        if config.unstructured and config.unstructured.api_key:
            try:
                client = UnstructuredClient(api_key_auth=config.unstructured.api_key)
                context["client"] = client
                logger.info("Unstructured API client initialized")
                
                if config.unstructured.debug_requests:
                    try:
                        # Import custom HTTP client if available
                        from UNS_MCP.uns_mcp.custom_http_client import CustomHttpClient
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


class UNSMcpNatsServer:
    """UNS-MCP server using NATS transport."""
    
    def __init__(self, config: Optional[UNSMcpNatsConfig] = None):
        """Initialize the UNS-MCP server with NATS transport.
        
        Args:
            config: Optional UNSMcpNatsConfig instance. If not provided, 
                   configuration is loaded from environment variables.
        """
        self.config = config or UNSMcpNatsConfig.from_env()
        self.mcp = self._create_mcp_server()
    
    def _create_mcp_server(self) -> FastMCP:
        """Create and configure the MCP server instance.
        
        Returns:
            FastMCP: Configured MCP server instance.
        """
        # Create MCP server instance
        mcp = FastMCP(
            "Unstructured API via NATS",
            lifespan=app_lifespan,
            dependencies=["unstructured-client", "python-dotenv", "nats-py"],
        )
        
        # Register UNS-MCP connectors if available
        try:
            from UNS_MCP.connectors import register_connectors
            register_connectors(mcp)
            logger.info("UNS-MCP connectors registered")
        except ImportError as e:
            logger.warning(f"Could not import UNS-MCP connectors: {e}")
        
        # Register UNS-MCP tools if available
        try:
            self._register_uns_tools(mcp)
            logger.info("UNS-MCP tools registered")
        except Exception as e:
            logger.error(f"Error registering UNS-MCP tools: {e}")
        
        return mcp
    
    def _register_uns_tools(self, mcp: FastMCP) -> None:
        """Register UNS-MCP tools with the MCP server.
        
        Args:
            mcp: The FastMCP server instance.
        """
        try:
            # Try to import core tools from UNS-MCP
            from UNS_MCP.uns_mcp.server import (
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
    
    async def run(self) -> None:
        """Run the UNS-MCP server with NATS transport."""
        if not NATS_TRANSPORT_AVAILABLE:
            logger.error("NATS transport not available. Cannot start server.")
            return
        
        # Configure NATS server
        nats_params = NatsServerParameters(
            url=self.config.nats.url,
            service_name=self.config.nats.service_name,
            server_id=f"{self.config.nats.server_id_prefix}-{os.getpid()}",
            description="Unstructured API MCP Server",
            version="1.0.0",
            metadata={
                "provider": "unstructured-api",
                "transport": "nats",
            },
            queue_group=self.config.nats.queue_group,
        )
        
        logger.info(f"Starting UNS-MCP server with NATS transport at {self.config.nats.url}")
        logger.info(f"Service name: {self.config.nats.service_name}")
        
        try:
            # Start the server with NATS transport
            async with nats_server(nats_params) as (read_stream, write_stream):
                mcp_server = self.mcp._mcp_server
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Error running server: {e}")


async def run_server(config: Optional[UNSMcpNatsConfig] = None) -> None:
    """Run the UNS-MCP server with NATS transport.
    
    This is a convenience function to run the server from the command line.
    
    Args:
        config: Optional UNSMcpNatsConfig instance. If not provided, 
               configuration is loaded from environment variables.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Prepare and run server
    server = UNSMcpNatsServer(config)
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down")