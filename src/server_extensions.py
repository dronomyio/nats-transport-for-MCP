"""
Server extensions for MCP NATS transport that add callback functionality.

This module extends the standard MCP server with asynchronous operation support
through callbacks, allowing long-running operations to complete in the background
while sending progress updates and final results via callbacks.
"""

import asyncio
import inspect
import logging
import functools
from typing import Dict, Any, Callable, Awaitable

from mcp.server.fastmcp.server import FastMcpServer
from mcp.server.fastmcp.tools import tool
from .callbacks import CallbackManager

logger = logging.getLogger(__name__)

class CallbackEnabledServer:
    """Extends FastMcpServer with callback functionality."""
    
    def __init__(self, server: FastMcpServer, nats_client):
        """
        Initialize a callback-enabled server wrapper.
        
        Args:
            server: The MCP server to wrap
            nats_client: The NATS client instance
        """
        self.server = server
        self.callback_manager = CallbackManager(nats_client)
        self.nats_client = nats_client
        
        # Wrap tool execution to handle callbacks
        self._wrap_tool_handlers()
        
    def _wrap_tool_handlers(self):
        """Wrap all tool handlers to support callbacks."""
        for tool_name, tool_obj in self.server.tools._tools.items():
            original_handler = tool_obj.handler
            
            @functools.wraps(original_handler)
            async def wrapped_handler(*args, **kwargs):
                # Check if the last argument has callback info
                callback_info = kwargs.pop("_callback", None)
                
                if callback_info and "subject" in callback_info:
                    # This is a callback-enabled call
                    callback_subject = callback_info["subject"]
                    handle_progress = callback_info.get("handle_progress", True)
                    
                    # Define a progress reporter for this call
                    async def report_progress(progress, total=None, message=None):
                        if handle_progress:
                            await self.callback_manager.send_progress_callback(
                                callback_subject, progress, total, message
                            )
                    
                    # Add progress reporter to kwargs if the original handler accepts it
                    if "report_progress" in inspect.signature(original_handler).parameters:
                        kwargs["report_progress"] = report_progress
                    
                    # Send immediate acknowledgment through normal response
                    ack_response = {
                        "status": "accepted", 
                        "message": f"Processing {tool_name} asynchronously"
                    }
                    
                    # Process in background
                    async def background_process():
                        try:
                            # Call the original handler
                            result = await original_handler(*args, **kwargs)
                            
                            # Send result via callback
                            await self.callback_manager.send_callback(callback_subject, {
                                "status": "completed",
                                "result": result
                            })
                            logger.info(f"Completed async execution of {tool_name} and sent callback")
                        except Exception as e:
                            logger.exception(f"Error in background execution of {tool_name}: {e}")
                            # Send error via callback
                            await self.callback_manager.send_callback(callback_subject, {
                                "status": "error",
                                "error": str(e)
                            })
                    
                    # Start processing
                    asyncio.create_task(background_process())
                    
                    # Return acknowledgment immediately
                    return ack_response
                else:
                    # Regular synchronous call
                    return await original_handler(*args, **kwargs)
            
            # Replace the original handler
            tool_obj.handler = wrapped_handler
            
    def register_async_tool(self, func: Callable[..., Awaitable[Any]]):
        """
        Register a new async-aware tool that accepts a progress reporter.
        
        This decorator is similar to @tool but adds support for progress reporting.
        
        Args:
            func: The async function to register
        """
        # Register with the server
        self.server.tools.register(func)
        
        # The handler is already wrapped by _wrap_tool_handlers
        
    async def close(self):
        """Clean up resources."""
        await self.callback_manager.close()

# Helper decorator for async-aware tools
def async_tool(func):
    """
    Decorator for registering async-aware tools that support progress reporting.
    
    The decorated function can have a report_progress parameter:
    
    @async_tool
    async def long_task(param1, param2, report_progress=None):
        # Do some work
        if report_progress:
            await report_progress(0.5, 1.0, "Halfway done")
        # Do more work
        return result
    """
    @tool
    @functools.wraps(func)
    async def wrapper(*args, report_progress=None, **kwargs):
        return await func(*args, report_progress=report_progress, **kwargs)
    
    return wrapper