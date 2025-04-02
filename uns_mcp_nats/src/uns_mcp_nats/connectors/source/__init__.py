"""Source connector adapters for UNS-MCP with NATS transport."""

import logging
import importlib
import pkgutil
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("uns-mcp-nats.connectors.source")

# Registry of available source connectors
_source_connectors = {}


class SourceConnectorAdapter:
    """Base class for source connector adapters."""
    
    name = "base_source"
    description = "Base source connector adapter"
    
    @classmethod
    def register(cls, mcp_server: FastMCP) -> None:
        """Register this connector with the MCP server.
        
        Args:
            mcp_server: The FastMCP server instance
        """
        logger.info(f"Registering source connector: {cls.name}")
        # Implementation depends on connector specifics


def register_source_connector(name: str, adapter_class: type) -> None:
    """Register a source connector adapter.
    
    Args:
        name: Name of the connector
        adapter_class: Adapter class for the connector
    """
    _source_connectors[name] = adapter_class
    logger.debug(f"Registered source connector adapter: {name}")


def get_available_connectors() -> List[str]:
    """Get a list of available source connectors.
    
    Returns:
        List of source connector names
    """
    return list(_source_connectors.keys())


def get_connector(name: str) -> Optional[Any]:
    """Get a source connector adapter by name.
    
    Args:
        name: Name of the connector
        
    Returns:
        Connector adapter class or None if not found
    """
    return _source_connectors.get(name)


# Import all modules in this package to register connectors
for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        module = importlib.import_module(f"{__name__}.{name}")
        logger.debug(f"Imported source connector module: {name}")
    except ImportError as e:
        logger.warning(f"Could not import source connector module {name}: {e}")


# Try to import UNS-MCP source connectors
try:
    # These imports will register the connectors via the adapter modules
    from .s3 import S3SourceConnectorAdapter
    from .gdrive import GDriveSourceConnectorAdapter
    from .azure import AzureSourceConnectorAdapter
    from .onedrive import OneDriveSourceConnectorAdapter
    from .salesforce import SalesforceSourceConnectorAdapter
    
    # Register all adapter classes
    register_source_connector("s3", S3SourceConnectorAdapter)
    register_source_connector("gdrive", GDriveSourceConnectorAdapter)
    register_source_connector("azure", AzureSourceConnectorAdapter)
    register_source_connector("onedrive", OneDriveSourceConnectorAdapter)
    register_source_connector("salesforce", SalesforceSourceConnectorAdapter)
    
except ImportError as e:
    logger.warning(f"Could not import source connector adapters: {e}")
    logger.info("Source connectors will be loaded directly from UNS-MCP if available")