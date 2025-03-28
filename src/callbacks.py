"""
Callback mechanism for asynchronous operations with MCP NATS transport.

This module provides a callback system that enables asynchronous long-running
operations in MCP over NATS transport. It allows clients to initiate operations
that may take a long time to complete, and receive the results asynchronously
via callbacks when they're ready.
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

class CallbackManager:
    """Manages NATS-based callbacks for asynchronous MCP operations."""
    
    def __init__(self, nats_client, base_subject="mcp.callbacks"):
        """
        Initialize the callback manager.
        
        Args:
            nats_client: The NATS client instance
            base_subject: Base subject for callbacks
        """
        self.nc = nats_client
        self.base_subject = base_subject
        self._subscriptions = {}
        self._pending_callbacks = {}
        
    async def register_callback(self, 
                          timeout: int = 3600, 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Register a new callback and return the callback information.
        
        Args:
            timeout: Maximum time in seconds to wait for callback
            metadata: Additional information to include with the callback
            
        Returns:
            Dict containing callback subject and ID
        """
        callback_id = str(uuid.uuid4())
        callback_subject = f"{self.base_subject}.{callback_id}"
        
        # Create a future to be resolved when callback arrives
        future = asyncio.Future()
        
        # Store in pending callbacks
        self._pending_callbacks[callback_id] = {
            "future": future,
            "metadata": metadata or {}
        }
        
        # Set up subscription if not already subscribed
        if callback_subject not in self._subscriptions:
            sub = await self.nc.subscribe(callback_subject, cb=self._handle_callback)
            self._subscriptions[callback_subject] = sub
        
        return {
            "callback_id": callback_id,
            "callback_subject": callback_subject
        }
    
    async def wait_for_callback(self, callback_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Wait for a callback to be received.
        
        Args:
            callback_id: The ID of the registered callback
            timeout: Maximum time to wait in seconds
            
        Returns:
            The callback data
            
        Raises:
            asyncio.TimeoutError: If timeout is reached
            KeyError: If callback_id is not registered
        """
        if callback_id not in self._pending_callbacks:
            raise KeyError(f"Callback ID {callback_id} not registered")
            
        future = self._pending_callbacks[callback_id]["future"]
        
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            # Clean up on timeout
            self._cleanup_callback(callback_id)
            raise
    
    async def send_callback(self, subject: str, data: Dict[str, Any]) -> None:
        """
        Send a callback to a specific subject.
        
        Args:
            subject: The callback subject
            data: The data to send
        """
        await self.nc.publish(subject, json.dumps(data).encode())
        
    async def send_progress_callback(self, 
                               subject: str, 
                               progress: float, 
                               total: Optional[float] = None, 
                               message: Optional[str] = None) -> None:
        """
        Send a progress update callback.
        
        Args:
            subject: The callback subject
            progress: Current progress value
            total: Total value (if known)
            message: Optional status message
        """
        data = {
            "status": "progress",
            "progress": progress
        }
        
        if total is not None:
            data["total"] = total
            
        if message is not None:
            data["message"] = message
            
        await self.send_callback(subject, data)
        
    async def _handle_callback(self, msg):
        """Handle incoming callback messages."""
        # Extract callback ID from subject
        parts = msg.subject.split(".")
        if len(parts) < 3:
            logger.warning(f"Received callback with invalid subject format: {msg.subject}")
            return
            
        callback_id = parts[-1]
        
        if callback_id not in self._pending_callbacks:
            logger.warning(f"Received callback for unknown ID: {callback_id}")
            return
            
        try:
            # Parse callback data
            callback_data = json.loads(msg.data.decode())
            
            # Retrieve the future
            future = self._pending_callbacks[callback_id]["future"]
            
            # If this is a progress update and the future is not done,
            # we don't resolve it yet, just log the progress
            if callback_data.get("status") == "progress" and not future.done():
                logger.debug(f"Progress update for {callback_id}: {callback_data.get('progress')}")
                return
                
            # For final results or errors, resolve the future if not already done
            if not future.done():
                future.set_result(callback_data)
                
            # Clean up if this is a final callback
            if callback_data.get("status") in ("completed", "error"):
                self._cleanup_callback(callback_id)
                
        except Exception as e:
            logger.exception(f"Error handling callback: {e}")
            
    def _cleanup_callback(self, callback_id: str) -> None:
        """Clean up resources for a callback."""
        if callback_id in self._pending_callbacks:
            callback_subject = f"{self.base_subject}.{callback_id}"
            
            # Unsubscribe if this is the only callback using this subscription
            if callback_subject in self._subscriptions:
                asyncio.create_task(self._subscriptions[callback_subject].unsubscribe())
                del self._subscriptions[callback_subject]
                
            # Remove from pending callbacks
            del self._pending_callbacks[callback_id]
            
    async def close(self):
        """Clean up all subscriptions."""
        for subject, sub in list(self._subscriptions.items()):
            try:
                await sub.unsubscribe()
            except Exception as e:
                logger.warning(f"Error unsubscribing from {subject}: {e}")
                
        self._subscriptions.clear()
        self._pending_callbacks.clear()