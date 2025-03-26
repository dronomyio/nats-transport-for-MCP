"""
NATS Server Transport Module

This module provides functionality for creating a NATS-based transport layer
that can be used to communicate with an MCP client through NATS messaging system.

Example usage:
```
    async def run_server():
        nats_config = NatsServerParameters(
            url="nats://localhost:4222",
            request_subject="mcp.request",
            response_subject="mcp.response"
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
from contextlib import asynccontextmanager

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel, Field
from nats.aio.client import Client as NatsClient

import mcp.types as types

logger = logging.getLogger(__name__)


class NatsServerParameters(BaseModel):
    """Parameters for connecting to a NATS server as an MCP server."""
    
    url: str = "nats://localhost:4222"
    """The URL of the NATS server to connect to."""
    
    request_subject: str
    """The subject to receive requests on."""
    
    response_subject: str
    """The subject to publish responses to."""
    
    server_id: str = Field(default_factory=lambda: f"mcp-server-{anyio.to_thread.current_default_thread_limiter().statistics().borrowed_tokens}")
    """A unique identifier for this server."""
    
    connect_timeout: float = 10.0
    """Timeout in seconds for connecting to the NATS server."""


@asynccontextmanager
async def nats_server(params: NatsServerParameters):
    """
    Server transport for NATS: this will communicate with MCP clients by
    establishing a connection to a NATS server and using pub/sub messaging.
    
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
    
    async def nats_reader():
        """Reads messages from NATS and forwards them to read_stream_writer."""
        try:
            async with read_stream_writer:
                # Subscribe to request subject
                sub = await nc.subscribe(
                    params.request_subject, 
                    queue=f"mcp-server-{params.server_id}"
                )
                
                logger.debug(f"Subscribed to {params.request_subject}")
                
                async for msg in sub.messages:
                    try:
                        raw_text = msg.data.decode('utf-8')
                        message = types.JSONRPCMessage.model_validate_json(raw_text)
                        await read_stream_writer.send(message)
                    except Exception as exc:
                        # If JSON parse or model validation fails, send the exception
                        await read_stream_writer.send(exc)
        except anyio.ClosedResourceError:
            logger.debug("NATS reader closed")
        finally:
            # Unsubscribe when done
            await sub.unsubscribe()
    
    async def nats_writer():
        """Reads messages from write_stream_reader and publishes them to NATS."""
        try:
            async with write_stream_reader:
                async for message in write_stream_reader:
                    # Convert to a dict, then to JSON
                    msg_dict = message.model_dump(
                        by_alias=True, mode="json", exclude_none=True
                    )
                    json_data = json.dumps(msg_dict)
                    
                    # Publish to response subject
                    await nc.publish(
                        params.response_subject,
                        json_data.encode('utf-8')
                    )
                    logger.debug(f"Published message to {params.response_subject}")
        except anyio.ClosedResourceError:
            logger.debug("NATS writer closed")
    
    try:
        # Start reader and writer tasks
        async with anyio.create_task_group() as tg:
            tg.start_soon(nats_reader)
            tg.start_soon(nats_writer)
            
            # Yield the streams to the caller
            yield (read_stream, write_stream)
            
            # Once the caller's 'async with' block exits, we cancel the task group
            tg.cancel_scope.cancel()
    finally:
        # Close NATS connection when done
        await nc.close()
        logger.info("NATS connection closed")