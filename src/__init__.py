"""
MCP NATS Transport

This package provides NATS transport implementations for the Model Context Protocol,
including support for asynchronous callbacks and progress reporting.
"""

from .client import NatsClientParameters, nats_client
from .server import NatsServerParameters, nats_server
from .callbacks import CallbackManager
from .client_extensions import CallbackEnabledClient
from .server_extensions import CallbackEnabledServer, async_tool

__version__ = "0.1.0"