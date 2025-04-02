"""Destination connector adapters for UNS-MCP with NATS transport."""

import logging
import importlib
import pkgutil
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("uns-mcp-nats.connectors.destination")

# Registry of available destination connectors
_destination_connectors = {}


class DestinationConnectorAdapter:
    """Base class for destination connector adapters."""
    
    name = "base_destination"
    description = "Base destination connector adapter"
    
    @classmethod
    def register(cls, mcp_server: FastMCP) -> None:
        """Register this connector with the MCP server.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        logger.info(f"Registering destination connector: {cls.name}")
        # Implementation depends on connector specifics


def register_destination_connector(name: str, adapter_class: type) -> None:
    """Register a destination connector adapter.
    
    Args:
        name: Name of the connector
        adapter_class: Adapter class for the connector
    """
    _destination_connectors[name] = adapter_class
    logger.debug(f"Registered destination connector adapter: {name}")


def get_available_connectors() -> List[str]:
    """Get a list of available destination connectors.
    
    Returns:
        List of destination connector names
    """
    return list(_destination_connectors.keys())


def get_connector(name: str) -> Optional[Any]:
    """Get a destination connector adapter by name.
    
    Args:
        name: Name of the connector
        
    Returns:
        Connector adapter class or None if not found
    """
    return _destination_connectors.get(name)


# Import all modules in this package to register connectors
for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        module = importlib.import_module(f"{__name__}.{name}")
        logger.debug(f"Imported destination connector module: {name}")
    except ImportError as e:
        logger.warning(f"Could not import destination connector module {name}: {e}")


# Try to import UNS-MCP destination connectors
try:
    # These imports will register the connectors via the adapter modules
    from .s3 import S3DestinationConnectorAdapter
    from .mongo import MongoDestinationConnectorAdapter
    from .pinecone import PineconeDestinationConnectorAdapter
    from .neo4j import Neo4jDestinationConnectorAdapter
    from .weaviate import WeaviateDestinationConnectorAdapter
    from .astra import AstraDestinationConnectorAdapter
    from .databricks_vdt import DatabricksVDTDestinationConnectorAdapter
    from .databricksvolumes import DatabricksVolumesDestinationConnectorAdapter
    
    # Register all adapter classes
    register_destination_connector("s3", S3DestinationConnectorAdapter)
    register_destination_connector("mongo", MongoDestinationConnectorAdapter)
    register_destination_connector("pinecone", PineconeDestinationConnectorAdapter)
    register_destination_connector("neo4j", Neo4jDestinationConnectorAdapter)
    register_destination_connector("weaviate", WeaviateDestinationConnectorAdapter)
    register_destination_connector("astra", AstraDestinationConnectorAdapter)
    register_destination_connector("databricks_vdt", DatabricksVDTDestinationConnectorAdapter)
    register_destination_connector("databricksvolumes", DatabricksVolumesDestinationConnectorAdapter)
    
except ImportError as e:
    logger.warning(f"Could not import destination connector adapters: {e}")
    logger.info("Destination connectors will be loaded directly from UNS-MCP if available")