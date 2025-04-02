"""MongoDB destination connector adapter for UNS-MCP with NATS transport."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from mcp.server.fastmcp import FastMCP, Context

# Try to import from UNS-MCP first
try:
    from UNS_MCP.connectors.destination.mongo import register_mongo_destination
    DIRECT_IMPORT = True
except ImportError:
    DIRECT_IMPORT = False

logger = logging.getLogger("uns-mcp-nats.connectors.destination.mongo")


class MongoDestinationConnectorAdapter:
    """Adapter for MongoDB destination connector."""
    
    name = "mongo_destination"
    description = "MongoDB destination connector"
    
    @classmethod
    def register(cls, mcp_server: FastMCP) -> None:
        """Register MongoDB destination connector with the MCP server.
        
        This method either:
        1. Uses the original UNS-MCP connector implementation if available
        2. Provides a local adapter implementation otherwise
        
        Args:
            mcp_server: The FastMCP server instance
        """
        if DIRECT_IMPORT:
            # Use the original implementation if available
            register_mongo_destination(mcp_server)
            logger.info("Registered MongoDB destination connector from UNS-MCP")
        else:
            # Otherwise, provide a local adapter implementation
            cls._register_local_adapter(mcp_server)
            logger.info("Registered local MongoDB destination connector adapter")
    
    @classmethod
    def _register_local_adapter(cls, mcp_server: FastMCP) -> None:
        """Register a local adapter implementation for MongoDB destination connector.
        
        This is used when the original UNS-MCP implementation is not available.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        @mcp_server.tool()
        async def create_mongo_destination(
            ctx: Context,
            name: str,
            connection_string: str,
            database_name: str,
            collection_name: str,
            fields: Optional[List[str]] = None,
        ) -> str:
            """Create a new MongoDB destination connector.
            
            Args:
                name: Name of the destination connector
                connection_string: MongoDB connection string
                database_name: Name of the MongoDB database
                collection_name: Name of the MongoDB collection
                fields: Fields to include in the documents
                
            Returns:
                String response with the created destination connector information
            """
            # In a real implementation, this would interact with the Unstructured API
            # For now, we'll just return a placeholder message
            return f"Created MongoDB destination connector '{name}' for database '{database_name}', collection '{collection_name}'\n(Note: This is a placeholder adapter implementation)"
        
        @mcp_server.tool()
        async def list_mongo_destinations(ctx: Context) -> str:
            """List all MongoDB destination connectors.
            
            Returns:
                String response with the list of MongoDB destination connectors
            """
            # In a real implementation, this would interact with the Unstructured API
            # For now, we'll just return a placeholder message
            return "No MongoDB destination connectors found\n(Note: This is a placeholder adapter implementation)"