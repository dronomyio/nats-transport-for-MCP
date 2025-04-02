"""Connector registration for UNS-MCP with NATS transport."""

import logging
import os
import importlib
import pkgutil
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("uns-mcp-nats.connectors")

# Maintain a registry of connector implementations
connector_registry = {}


def register_connector(name: str, connector_class: Any) -> None:
    """Register a connector implementation.
    
    Args:
        name: Name of the connector.
        connector_class: Connector implementation class.
    """
    connector_registry[name] = connector_class
    logger.debug(f"Registered connector: {name}")


def register_connectors(mcp_server: FastMCP) -> List[str]:
    """Register all UNS-MCP connectors with the MCP server.
    
    This function tries multiple approaches to register connectors:
    1. First, it tries to import UNS-MCP connectors directly
    2. If that fails, it tries to load local adapter implementations
    3. If no connectors are found, it logs a warning
    
    Args:
        mcp_server: The FastMCP server instance.
        
    Returns:
        List of registered connector names.
    """
    registered_connectors = []
    
    # First try: Import directly from UNS-MCP if available
    try:
        # Import UNS-MCP connectors
        from UNS_MCP.connectors import register_connectors as register_all_uns_connectors
        
        # Register all connectors from UNS-MCP
        register_all_uns_connectors(mcp_server)
        
        # Track registered connectors for logging
        try:
            from UNS_MCP.connectors.source import __init__ as source_init
            source_dir = os.path.dirname(source_init.__file__)
            source_modules = [f[:-3] for f in os.listdir(source_dir) 
                             if f.endswith('.py') and not f.startswith('__')]
            
            from UNS_MCP.connectors.destination import __init__ as dest_init
            dest_dir = os.path.dirname(dest_init.__file__)
            dest_modules = [f[:-3] for f in os.listdir(dest_dir) 
                           if f.endswith('.py') and not f.startswith('__')]
            
            registered_connectors = source_modules + dest_modules
            logger.info(f"Registered UNS-MCP connectors: {', '.join(registered_connectors)}")
            return registered_connectors
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not determine UNS-MCP connector names: {e}")
    
    except ImportError as e:
        logger.warning(f"Could not import UNS-MCP connectors: {e}")
        logger.info("Will try to use local connector adapters...")
    
    # Second try: Use local adapter implementations
    try:
        # Import local connector modules
        from . import source, destination
        
        # Register source connectors
        for name in source.get_available_connectors():
            adapter = source.get_connector(name)
            if adapter:
                adapter.register(mcp_server)
                registered_connectors.append(f"source.{name}")
        
        # Register destination connectors
        for name in destination.get_available_connectors():
            adapter = destination.get_connector(name)
            if adapter:
                adapter.register(mcp_server)
                registered_connectors.append(f"destination.{name}")
        
        if registered_connectors:
            logger.info(f"Registered local connector adapters: {', '.join(registered_connectors)}")
            return registered_connectors
    
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not load local connector adapters: {e}")
    
    # If we get here, no connectors were registered
    logger.warning("No connectors registered. Document processing capabilities will be limited.")
    return registered_connectors


# Import connector submodules to register adapters
try:
    from . import source, destination
except ImportError:
    logger.warning("Could not import connector submodules. You may need to install additional dependencies.")