"""
Client extensions for MCP NATS transport that add callback functionality.

This module extends the standard MCP client with asynchronous operation support
through callbacks, allowing long-running operations to complete in the background
while the client continues other work.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from mcp.client.session import ClientSession
from .callbacks import CallbackManager

logger = logging.getLogger(__name__)

class CallbackEnabledClient:
    """Extends MCP ClientSession with callback functionality."""
    
    def __init__(self, client_session: ClientSession, nats_client):
        """
        Initialize a callback-enabled client wrapper.
        
        Args:
            client_session: The MCP client session to wrap
            nats_client: The NATS client instance
        """
        self.client = client_session
        self.callback_manager = CallbackManager(nats_client)
        self._active_callbacks = {}
        
    async def call_tool_async(self, 
                        tool_name: str, 
                        arguments: Dict[str, Any], 
                        timeout: int = 3600,
                        handle_progress: bool = True,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Call a tool asynchronously and get a callback when it completes.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Maximum time to wait for the tool to complete
            handle_progress: Whether to handle progress updates
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dict containing callback_id that can be used to get results later
        """
        # Register a callback
        callback_info = await self.callback_manager.register_callback(timeout)
        
        # Add callback information to arguments
        enriched_args = {
            **arguments,
            "_callback": {
                "subject": callback_info["callback_subject"],
                "handle_progress": handle_progress
            }
        }
        
        # Call the tool (will return quickly with just an acknowledgment)
        try:
            ack = await self.client.call_tool(tool_name, enriched_args)
            
            # Store callback info
            self._active_callbacks[callback_info["callback_id"]] = {
                "tool": tool_name,
                "arguments": arguments,
                "progress_callback": progress_callback
            }
            
            # Return information about the pending callback
            return {
                "callback_id": callback_info["callback_id"],
                "acknowledgment": ack
            }
        except Exception as e:
            # Clean up callback if the call fails
            await self.callback_manager.wait_for_callback(callback_info["callback_id"], 0)
            raise e
        
    async def get_async_result(self, callback_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the result of an asynchronous tool call.
        
        Args:
            callback_id: The ID returned from call_tool_async
            timeout: Maximum time to wait for result
            
        Returns:
            The tool call result when it completes
        """
        try:
            result = await self.callback_manager.wait_for_callback(callback_id, timeout)
            
            # Clean up from active callbacks
            if callback_id in self._active_callbacks:
                del self._active_callbacks[callback_id]
                
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for callback {callback_id}")
            raise
        except KeyError:
            logger.warning(f"Callback {callback_id} not found")
            raise
            
    async def cancel_async_call(self, callback_id: str) -> bool:
        """
        Attempt to cancel an asynchronous call.
        
        Note: This does not guarantee the operation will be canceled on the server,
        but it will stop waiting for the result.
        
        Args:
            callback_id: The ID returned from call_tool_async
            
        Returns:
            True if the callback was found and canceled, False otherwise
        """
        if callback_id in self._active_callbacks:
            # Clean up callback
            self.callback_manager._cleanup_callback(callback_id)
            del self._active_callbacks[callback_id]
            return True
        return False
        
    async def list_pending_calls(self) -> Dict[str, Dict[str, Any]]:
        """
        List all pending asynchronous calls.
        
        Returns:
            Dictionary of callback IDs to call information
        """
        return self._active_callbacks
        
    async def close(self):
        """Clean up all callbacks."""
        await self.callback_manager.close()