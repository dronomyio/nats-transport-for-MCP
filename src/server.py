"""
NATS Server Transport Module

This module provides functionality for creating a NATS-based transport layer
that can be used to communicate with an MCP client through NATS messaging system.
It uses the NATS micro-services API for better service discovery and monitoring.

Features:
- Full integration with NATS JetStream micro-services API
- Service discovery and observability through 'nats service' commands
- Automatic stats collection and monitoring
- Fallback to traditional NATS subscriptions when micro-services API is not available

Example usage:
```
    async def run_server():
        nats_config = NatsServerParameters(
            url="nats://localhost:4222",
            service_name="mcp.service",
            description="My MCP Service",
            version="1.0.0",
            metadata={"environment": "production"}
        )
        async with nats_server(nats_config) as (read_stream, write_stream):
            # read_stream contains incoming JSONRPCMessages from clients
            # write_stream allows sending JSONRPCMessages to clients
            server = await create_my_server()
            await server.run(read_stream, write_stream, init_options)

    anyio.run(run_server)
```

When the server is running, you can use NATS CLI to view service information:
```
    nats service list               # List all services
    nats service info mcp.service   # Get info about the MCP service
    nats service stats mcp.service  # View service statistics
```
"""

import json
import logging
import uuid
import time
import contextlib
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple, List, Any

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
import nats
from nats.aio.msg import Msg
from pydantic import BaseModel, Field

# Import the micro module
try:
    import nats.micro
    HAS_MICRO = True
except ImportError:
    HAS_MICRO = False
    # Fallback definitions if micro module is not available
    logger = logging.getLogger(__name__)
    logger.warning("NATS micro module not available. Using fallback implementation.")

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
    
    description: Optional[str] = "MCP Server using NATS transport"
    """Description of the service for service discovery."""
    
    version: str = "1.0.0"
    """Version of the service."""
    
    metadata: Optional[Dict[str, str]] = None
    """Additional metadata for the service."""
    
    connect_timeout: float = 10.0
    """Timeout in seconds for connecting to the NATS server."""
    
    service_timeout: float = 30.0
    """Timeout in seconds for service requests."""
    
    # Fallback to queue groups if micro module is not available
    queue_group: Optional[str] = None
    """
    Queue group for load balancing requests across multiple servers.
    Only used if the micro module is not available.
    If None, a queue group based on server_id will be used.
    """


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
    
    # Connect to NATS server using the new API
    # We'll create an AsyncExitStack automatically managed by the context manager
    nc = await nats.connect(
        servers=params.url,
        connect_timeout=params.connect_timeout,
        name=params.server_id,
    )
    
    logger.info(f"Connected to NATS server at {params.url} as {params.server_id}")
    
    # Keep track of in-flight requests by their ID
    in_flight_requests: Dict[str, Tuple[Msg, types.JSONRPCMessage]] = {}
    
    # Function to handle incoming requests from micro-services
    async def handle_request(req):
        try:
            # Parse the message data as JSON-RPC
            raw_text = req.data.decode('utf-8')
            request = types.JSONRPCMessage.model_validate_json(raw_text)
            
            # Check if this is a request (has an ID) or a notification (no ID)
            is_request = isinstance(request.root, types.JSONRPCRequest)
            
            # Forward the message to the MCP server through the read_stream
            await read_stream_writer.send(request)
            
            if is_request:
                # For requests, keep track of it to match with response later
                request_id = str(request.root.id)
                in_flight_requests[request_id] = (req, request)
                logger.debug(f"Received request with ID {request_id}")
            else:
                # For notifications, no response is expected
                logger.debug(f"Received notification: {request.root.method}")
        except Exception as exc:
            # If message parsing fails, send the exception
            logger.exception(f"Error handling request: {exc}")
            await read_stream_writer.send(exc)
            
            # If this was a request, send an error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,  # We don't know the ID since parsing failed
                "error": {
                    "code": -32700,  # Parse error code
                    "message": f"Parse error: {str(exc)}"
                }
            }
            await req.respond(json.dumps(error_response).encode('utf-8'))
    
    # Handle responses from the MCP server
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
                            req, request = in_flight_requests.pop(response_id)
                            
                            # Convert the response to JSON
                            response_json = message.model_dump_json(by_alias=True, exclude_none=True)
                            
                            # Send the response using the micro-services request object
                            await req.respond(response_json.encode('utf-8'))
                            logger.debug(f"Sent response for request {response_id}")
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
                            # Use the new API for publishing
                            await nc.publish(subject, response_json.encode('utf-8'))
        except anyio.ClosedResourceError:
            logger.debug("Response handler closed")
    
    # Check if micro module is available and use it if possible
    if HAS_MICRO:
        try:
            # Create a micro service using the new nats.micro.add_service API
            service = await nats.micro.add_service(
                nc, 
                name=params.service_name,
                version=params.version,
                description=params.description,
                metadata=params.metadata or {}
            )
            
            # Create a main MCP group
            mcp_group = service.add_group(name="mcp")
            
            # Add endpoint that captures all possible method calls
            # In NATS micro, we use '>' as the wildcard for capturing all tokens
            await mcp_group.add_endpoint(
                name=">",
                handler=handle_request
            )
            
            logger.info(f"Started NATS micro service: {params.service_name} with ID {params.server_id}")
            
            # Define a task to periodically log service stats
            async def log_service_stats():
                while True:
                    try:
                        stats = await service.stats()
                        logger.info(f"Service stats: Requests: {stats.total_requests}, "
                                   f"Errors: {stats.total_errors}, "
                                   f"Average processing time: {stats.average_processing_time:.2f}ms")
                    except Exception as e:
                        logger.error(f"Error getting service stats: {e}")
                    await anyio.sleep(60)  # Log stats every minute
            
            try:
                # Start the response handler task and stats logging
                async with anyio.create_task_group() as tg:
                    tg.start_soon(handle_responses)
                    tg.start_soon(log_service_stats)
                    
                    # Yield the streams to the caller
                    yield (read_stream, write_stream)
                    
                    # Once the caller's 'async with' block exits, we cancel the task group
                    tg.cancel_scope.cancel()
            finally:
                # The service will be closed automatically by the AsyncExitStack
                # when we exit the async with block that created it
                
                # Close NATS connection when done
                await nc.close()
                logger.info("NATS micro service stopped and connection closed")
                
        except Exception as exc:
            logger.exception(f"Error starting NATS micro service: {exc}")
            # Fall back to using regular subscription
            logger.warning("Falling back to regular NATS subscription")
            await _fallback_subscription(nc, params, handle_request, handle_responses, 
                                      read_stream, write_stream, read_stream_writer, write_stream_reader)
    else:
        # Use regular subscription as fallback
        await _fallback_subscription(nc, params, handle_request, handle_responses, 
                                  read_stream, write_stream, read_stream_writer, write_stream_reader)


async def _fallback_subscription(nc, params, handle_request, handle_responses, 
                              read_stream, write_stream, read_stream_writer, write_stream_reader):
    """Fallback to using regular subscription if micro module is not available."""
    # Create queue group if not specified
    queue_group = params.queue_group or f"mcp-servers-{params.service_name}"
    
    # Subscribe to the service subject
    service_subject = f"{params.service_name}.>"
    
    # Create a wrapper function to adapt the old callback style to the new one
    async def msg_handler(msg):
        # Create a simple request-like object with respond method
        class RequestWrapper:
            def __init__(self, msg):
                self.msg = msg
                self.data = msg.data
                self.reply = msg.reply
            
            async def respond(self, data):
                if self.reply:
                    await self.msg.respond(data)
        
        # Call the handler with our wrapper
        await handle_request(RequestWrapper(msg))
    
    # Subscribe using the new API
    sub = await nc.subscribe(service_subject, queue=queue_group, cb=msg_handler)
    
    logger.info(f"Subscribed to service subject {service_subject} with queue group {queue_group}")
    
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
        await sub.drain()
        # Close NATS connection when done
        await nc.drain()
        logger.info("NATS connection closed")