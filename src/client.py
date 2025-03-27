"""
NATS Client Transport Module

This module provides functionality for creating a NATS-based transport layer
that can be used to communicate with an MCP server through NATS messaging system.

Example usage:
```
    async def run_client():
        nats_config = NatsClientParameters(
            url="nats://localhost:4222",
            service_name="mcp.service"
        )
        async with nats_client(nats_config) as (read_stream, write_stream):
            # read_stream contains incoming JSONRPCMessages from the server
            # write_stream allows sending JSONRPCMessages to the server
            client = await create_my_client()
            await client.run(read_stream, write_stream)

    anyio.run(run_client)
```
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from nats.aio.client import Client as NatsClient
from pydantic import BaseModel, Field, ValidationError

import mcp.types as types

logger = logging.getLogger(__name__)


class NatsClientParameters(BaseModel):
    """Parameters for connecting to a NATS server as a client."""
    
    url: str = "nats://localhost:4222"
    """The URL of the NATS server to connect to."""
    
    service_name: str = "mcp.service"
    """The name of the MCP service to connect to."""
    
    client_id: str = Field(default_factory=lambda: f"mcp-client-{uuid.uuid4().hex[:8]}")
    """A unique identifier for this client."""
    
    connect_timeout: float = 10.0
    """Timeout in seconds for connecting to the NATS server."""
    
    request_timeout: float = 30.0
    """Timeout in seconds for service requests."""
    
    subscription_subjects: Optional[Dict[str, str]] = None
    """Custom subscription subjects for notifications."""


@asynccontextmanager
async def nats_client(params: NatsClientParameters):
    """
    Client transport for NATS: this will connect to a server by establishing
    a connection to a NATS server and communicating via service requests.
    
    Yields a tuple of (read_stream, write_stream) where:
    - read_stream: A stream from which to read incoming JSONRPCMessage objects
    - write_stream: A stream to which to write outgoing JSONRPCMessage objects
    """
    # Create in-memory streams for message passing
    read_stream: MemoryObjectReceiveStream[types.JSONRPCMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[types.JSONRPCMessage | Exception]
    
    write_stream: MemoryObjectSendStream[types.JSONRPCMessage]
    write_stream_reader: MemoryObjectReceiveStream[types.JSONRPCMessage]
    
    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)
    
    # Create NATS client
    nc = NatsClient()
    
    # Connect to NATS server
    await nc.connect(
        params.url,
        connect_timeout=params.connect_timeout,
        name=params.client_id,
    )
    
    logger.info(f"Connected to NATS server at {params.url} as {params.client_id}")
    
    # Map of notification subscriptions
    subscriptions = {}
    
    # Set up notification subscriptions if provided
    if params.subscription_subjects:
        for notification_type, subject in params.subscription_subjects.items():
            async def notification_handler(msg):
                try:
                    raw_text = msg.data.decode('utf-8')
                    message = types.JSONRPCMessage.model_validate_json(raw_text)
                    await read_stream_writer.send(message)
                except ValidationError as exc:
                    await read_stream_writer.send(exc)
                except Exception as exc:
                    logger.exception(f"Error processing notification: {exc}")
                    await read_stream_writer.send(exc)
            
            sub = await nc.subscribe(subject, cb=notification_handler)
            subscriptions[notification_type] = sub
            logger.debug(f"Subscribed to {notification_type} notifications on subject {subject}")
    
    # Subscribe to general notifications
    notification_subject = f"{params.service_name}.notifications.>"
    
    async def handle_notification(msg):
        try:
            raw_text = msg.data.decode('utf-8')
            message = types.JSONRPCMessage.model_validate_json(raw_text)
            await read_stream_writer.send(message)
        except ValidationError as exc:
            await read_stream_writer.send(exc)
        except Exception as exc:
            logger.exception(f"Error processing notification: {exc}")
            await read_stream_writer.send(exc)
    
    notification_sub = await nc.subscribe(notification_subject, cb=handle_notification)
    logger.debug(f"Subscribed to notifications on {notification_subject}")
    
    async def request_handler():
        """Reads messages from write_stream_reader and sends requests to the server."""
        try:
            async with write_stream_reader:
                async for message in write_stream_reader:
                    # Check if this is a request or notification
                    is_request = isinstance(message.root, types.JSONRPCRequest)
                    
                    # Convert to JSON
                    message_json = message.model_dump_json(by_alias=True, exclude_none=True)
                    
                    if is_request:
                        # For requests, use request/reply pattern
                        method_name = message.root.method
                        subject = f"{params.service_name}.{method_name}"
                        
                        try:
                            # Use the NATS request method for proper request/reply
                            logger.debug(f"Sending request to {subject}")
                            response = await nc.request(
                                subject, 
                                message_json.encode('utf-8'),
                                timeout=params.request_timeout
                            )
                            
                            # Process the response
                            try:
                                response_text = response.data.decode('utf-8')
                                response_message = types.JSONRPCMessage.model_validate_json(response_text)
                                await read_stream_writer.send(response_message)
                            except ValidationError as exc:
                                await read_stream_writer.send(exc)
                        except Exception as exc:
                            # Create an error response if the request fails
                            logger.exception(f"Error sending request: {exc}")
                            request_id = message.root.id
                            error_response = types.JSONRPCError(
                                jsonrpc="2.0",
                                id=request_id,
                                error=types.ErrorData(
                                    code=-32000,  # Generic error code
                                    message=f"Request failed: {str(exc)}",
                                    data=None
                                )
                            )
                            error_message = types.JSONRPCMessage.model_validate(error_response)
                            await read_stream_writer.send(error_message)
                    else:
                        # For notifications, just publish
                        method_name = message.root.method
                        subject = f"{params.service_name}.{method_name}"
                        
                        logger.debug(f"Publishing notification to {subject}")
                        await nc.publish(subject, message_json.encode('utf-8'))
        except anyio.ClosedResourceError:
            logger.debug("Request handler closed")
    
    try:
        # Start the request handler task
        async with anyio.create_task_group() as tg:
            tg.start_soon(request_handler)
            
            # Yield the streams to the caller
            yield (read_stream, write_stream)
            
            # Once the caller's 'async with' block exits, we cancel the task group
            tg.cancel_scope.cancel()
    finally:
        # Clean up subscriptions
        for sub in subscriptions.values():
            await sub.unsubscribe()
        
        await notification_sub.unsubscribe()
        
        # Close NATS connection when done
        await nc.close()
        logger.info("NATS connection closed")