"""
NATS Server Transport Module

This module provides functionality for creating a NATS-based transport layer
that can be used to communicate with an MCP client through NATS messaging system.

Example usage:
```
    async def run_server():
        nats_config = NatsServerParameters(
            url="nats://localhost:4222",
            service_name="mcp.service"
        )
        async with nats_server(nats_config) as (read_stream, write_stream):
            # read_stream contains incoming JSONRPCMessages from clients
            # write_stream allows sending JSONRPCMessages to clients
            server = await create_my_server()
            await server.run(read_stream, write_stream, init_options)

    anyio.run(run_server)
```
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg
from pydantic import BaseModel, Field

import mcp.types as types

logger = logging.getLogger(__name__)


class NatsServerParameters(BaseModel):
    """Parameters for connecting to a NATS server as an MCP server."""
    
    url: str = "nats://localhost:4222"
    """The URL of the NATS server to connect to."""
    
    service_name: str = "mcp.service"
    """The name of the MCP service (used as the subject prefix for the service)."""
    
    server_id: str = Field(default_factory=lambda: f"mcp-server-{uuid.uuid4().hex[:8]}")
    """A unique identifier for this server."""
    
    queue_group: Optional[str] = None
    """
    Queue group for load balancing requests across multiple servers.
    If None, a queue group based on server_id will be used.
    """
    
    connect_timeout: float = 10.0
    """Timeout in seconds for connecting to the NATS server."""
    
    service_timeout: float = 30.0
    """Timeout in seconds for service requests."""


@asynccontextmanager
async def nats_server(params: NatsServerParameters):
    """
    Server transport for NATS: this will communicate with MCP clients by
    establishing a connection to a NATS server and creating a NATS service
    for handling JSON-RPC requests.
    
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
        name=params.server_id,
    )
    
    logger.info(f"Connected to NATS server at {params.url} as {params.server_id}")
    
    # Keep track of in-flight requests by their ID
    in_flight_requests: Dict[str, Tuple[Msg, types.JSONRPCMessage]] = {}
    
    # Create queue group if not specified
    queue_group = params.queue_group or f"mcp-servers-{params.service_name}"
    
    # Function to handle incoming requests
    async def handle_request(msg: Msg):
        try:
            # Parse the message data as JSON-RPC
            raw_text = msg.data.decode('utf-8')
            request = types.JSONRPCMessage.model_validate_json(raw_text)
            
            # Check if this is a request (has an ID) or a notification (no ID)
            is_request = isinstance(request.root, types.JSONRPCRequest)
            
            # Forward the message to the MCP server through the read_stream
            await read_stream_writer.send(request)
            
            if is_request:
                # For requests, keep track of it to match with response later
                request_id = str(request.root.id)
                in_flight_requests[request_id] = (msg, request)
                logger.debug(f"Received request with ID {request_id}")
            else:
                # For notifications, no response is expected
                logger.debug(f"Received notification: {request.root.method}")
        except Exception as exc:
            # If message parsing fails, send the exception
            logger.exception(f"Error handling request: {exc}")
            await read_stream_writer.send(exc)
            
            # If this was a request, send an error response
            if msg.reply:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,  # We don't know the ID since parsing failed
                    "error": {
                        "code": -32700,  # Parse error code
                        "message": f"Parse error: {str(exc)}"
                    }
                }
                await msg.respond(json.dumps(error_response).encode('utf-8'))
    
    # Subscribe to the service subject
    service_subject = f"{params.service_name}.>"
    sub = await nc.subscribe(service_subject, queue=queue_group, cb=handle_request)
    
    logger.info(f"Subscribed to service subject {service_subject} with queue group {queue_group}")
    
    async def handle_responses():
        """Reads messages from write_stream_reader and sends responses."""
        try:
            async with write_stream_reader:
                async for message in write_stream_reader:
                    # Check if this is a response to a request
                    is_response = isinstance(message.root, (types.JSONRPCResponse, types.JSONRPCError))
                    
                    if is_response:
                        # Get the request ID
                        response_id = str(message.root.id)
                        
                        # Find the matching request
                        if response_id in in_flight_requests:
                            msg, request = in_flight_requests.pop(response_id)
                            
                            # Convert the response to JSON
                            response_json = message.model_dump_json(by_alias=True, exclude_none=True)
                            
                            # If the client is expecting a reply, send it
                            if msg.reply:
                                await msg.respond(response_json.encode('utf-8'))
                                logger.debug(f"Sent response for request {response_id}")
                            else:
                                logger.warning(f"Request {response_id} has no reply subject")
                        else:
                            logger.warning(f"Response for unknown request ID: {response_id}")
                    else:
                        # This is a notification or an unexpected message type
                        logger.debug(f"Sending notification: {message.root.method if hasattr(message.root, 'method') else 'unknown'}")
                        method = getattr(message.root, 'method', None)
                        if method:
                            # For notifications, publish to the appropriate subject
                            subject = f"{params.service_name}.{method.replace('notifications/', '')}"
                            response_json = message.model_dump_json(by_alias=True, exclude_none=True)
                            await nc.publish(subject, response_json.encode('utf-8'))
        except anyio.ClosedResourceError:
            logger.debug("Response handler closed")
    
    try:
        # Start the response handler task
        async with anyio.create_task_group() as tg:
            tg.start_soon(handle_responses)
            
            # Yield the streams to the caller
            yield (read_stream, write_stream)
            
            # Once the caller's 'async with' block exits, we cancel the task group
            tg.cancel_scope.cancel()
    finally:
        # Clean up
        await sub.unsubscribe()
        # Close NATS connection when done
        await nc.close()
        logger.info("NATS connection closed")