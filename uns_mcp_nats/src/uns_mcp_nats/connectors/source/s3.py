"""S3 source connector adapter for UNS-MCP with NATS transport."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP, Context

# Try to import from UNS-MCP first
try:
    from UNS_MCP.connectors.source.s3 import register_s3_source
    DIRECT_IMPORT = True
except ImportError:
    DIRECT_IMPORT = False

logger = logging.getLogger("uns-mcp-nats.connectors.source.s3")


class S3SourceConnectorAdapter:
    """Adapter for S3 source connector."""
    
    name = "s3_source"
    description = "Amazon S3 source connector"
    
    @classmethod
    def register(cls, mcp_server: FastMCP) -> None:
        """Register S3 source connector with the MCP server.
        
        This method either:
        1. Uses the original UNS-MCP connector implementation if available
        2. Provides a local adapter implementation otherwise
        
        Args:
            mcp_server: The FastMCP server instance
        """
        if DIRECT_IMPORT:
            # Use the original implementation if available
            register_s3_source(mcp_server)
            logger.info("Registered S3 source connector from UNS-MCP")
        else:
            # Otherwise, provide a local adapter implementation
            cls._register_local_adapter(mcp_server)
            logger.info("Registered local S3 source connector adapter")
    
    @classmethod
    def _register_local_adapter(cls, mcp_server: FastMCP) -> None:
        """Register a local adapter implementation for S3 source connector.
        
        This is used when the original UNS-MCP implementation is not available.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        @mcp_server.tool()
        async def create_s3_source(
            ctx: Context,
            name: str,
            bucket_name: str,
            aws_access_key_id: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            region_name: Optional[str] = None,
            prefix: Optional[str] = None,
        ) -> str:
            """Create a new S3 source connector.
            
            Args:
                name: Name of the source connector
                bucket_name: Name of the S3 bucket
                aws_access_key_id: AWS access key ID (uses environment variables if not provided)
                aws_secret_access_key: AWS secret access key (uses environment variables if not provided)
                region_name: AWS region name (uses environment variables if not provided)
                prefix: Prefix filter for S3 objects
                
            Returns:
                String response with the created source connector information
            """
            # In a real implementation, this would interact with the Unstructured API
            # For now, we'll just return a placeholder message
            return f"Created S3 source connector '{name}' for bucket '{bucket_name}'\n(Note: This is a placeholder adapter implementation)"
        
        @mcp_server.tool()
        async def list_s3_sources(ctx: Context) -> str:
            """List all S3 source connectors.
            
            Returns:
                String response with the list of S3 source connectors
            """
            # In a real implementation, this would interact with the Unstructured API
            # For now, we'll just return a placeholder message
            return "No S3 source connectors found\n(Note: This is a placeholder adapter implementation)"