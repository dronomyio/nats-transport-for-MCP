"""Connector registration for UNS-MCP with NATS transport"""
import sys
import os
from pathlib import Path
from typing import List

# Add parent directory to path to access UNS-MCP
parent_dir = str(Path(__file__).parents[2])
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from mcp.server.fastmcp import FastMCP

def register_connectors(mcp_server: FastMCP) -> List[str]:
    """Register all UNS-MCP connectors with the MCP server

    Args:
        mcp_server: The FastMCP server instance

    Returns:
        List of registered connector names
    """
    registered_connectors = []
    
    try:
        # Import UNS-MCP connectors
        from UNS-MCP.connectors import register_connectors as register_all_uns_connectors
        
        # Register all connectors from UNS-MCP
        register_all_uns_connectors(mcp_server)
        
        # Track registered connectors for logging
        from UNS-MCP.connectors.source import __init__
        source_dir = os.path.dirname(__init__.__file__)
        source_modules = [f[:-3] for f in os.listdir(source_dir) 
                         if f.endswith('.py') and not f.startswith('__')]
        
        from UNS-MCP.connectors.destination import __init__
        dest_dir = os.path.dirname(__init__.__file__)
        dest_modules = [f[:-3] for f in os.listdir(dest_dir) 
                       if f.endswith('.py') and not f.startswith('__')]
        
        registered_connectors = source_modules + dest_modules
        
    except ImportError as e:
        print(f"Warning: Could not import UNS-MCP connectors: {e}")
        print("Continuing without connector registration")
    
    return registered_connectors