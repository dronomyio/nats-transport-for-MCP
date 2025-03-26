"""
MCP NATS Transport

This package provides NATS transport implementations for the Model Context Protocol.
"""

from .client import NatsClientParameters, nats_client
from .server import NatsServerParameters, nats_server

__version__ = "0.1.0"