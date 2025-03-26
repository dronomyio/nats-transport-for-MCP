"""
NATS Client Transport Module

This module provides functionality for creating a NATS-based transport layer
that can be used to communicate with an MCP server through NATS messaging system.

Example usage:
```
    async def run_client():
        nats_config = NatsClientParameters(
            url="nats://localhost:4222",
            request_subject="mcp.request",
            response_subject="mcp.response"
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
from contextlib import asynccontextmanager

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel, Field
from nats.aio.client import Client as NatsClient
from pydantic import ValidationError

import mcp.types as types

logger = logging.getLogger(__name__)


class NatsClientParameters(BaseModel):
    """Parameters for connecting to a NATS server as a client."""
    
    url: str = "nats://localhost:4222"
    """The URL of the NATS server to connect to."""
    
    request_subject: str
    """The subject to publish requests to."""
    
    response_subject: str 
    """The subject to receive responses from."""
    
    client_id: str = Field(default_factory=lambda: f"mcp-client-{anyio.to_thread.current_default_thread_limiter().statistics().borrowed_tokens}")
    """A unique identifier for this client."""
    
    connect_timeout: float = 10.0
    """Timeout in seconds for connecting to the NATS server."""


@asynccontextmanager
async def nats_client(params: NatsClientParameters):
    """
    Client transport for NATS: this will connect to a server by establishing
    a connection to a NATS server and communicating via pub/sub messaging.
    
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
    
    async def nats_reader():
        """Reads messages from NATS and forwards them to read_stream_writer."""
        try:
            async with read_stream_writer:
                # Subscribe to response subject
                sub = await nc.subscribe(
                    params.response_subject, 
                    queue=f"mcp-client-{params.client_id}"
                )
                
                logger.debug(f"Subscribed to {params.response_subject}")
                
                async for msg in sub.messages:
                    try:
                        raw_text = msg.data.decode('utf-8')
                        message = types.JSONRPCMessage.model_validate_json(raw_text)
                        await read_stream_writer.send(message)
                    except ValidationError as exc:
                        # If JSON parse or model validation fails, send the exception
                        await read_stream_writer.send(exc)
                    except Exception as exc:
                        logger.exception(f"Error processing NATS message: {exc}")
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
                    
                    # Publish to request subject
                    await nc.publish(
                        params.request_subject,
                        json_data.encode('utf-8')
                    )
                    logger.debug(f"Published message to {params.request_subject}")
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