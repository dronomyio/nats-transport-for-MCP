"""
Example demonstrating async callbacks with MCP over NATS transport.

This example shows:
1. Setting up a callback-enabled MCP server
2. Registering async-aware tools that support progress reporting
3. Connecting with a callback-enabled client
4. Making asynchronous requests and receiving callbacks

Requirements:
- NATS server running (e.g., `docker run -p 4222:4222 nats`)
- MCP Python SDK installed

Run this example:
```
python -m examples.callback_example
```
"""

import asyncio
import logging
import time
import sys
import os

# Add the parent directory to sys.path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import anyio
from mcp.client.session import ClientSession
from mcp.server.fastmcp.server import FastMcpServer
from mcp.shared.session import Session

from src.client import NatsClientParameters, nats_client
from src.server import NatsServerParameters, nats_server
from src.client_extensions import CallbackEnabledClient
from src.server_extensions import CallbackEnabledServer, async_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Define async-aware tools that support progress reporting
@async_tool
async def generate_report(report_type: str, size: int = 100, report_progress=None) -> str:
    """
    Generate a mock report of the specified type and size.
    This is a long-running operation that reports progress.
    
    Args:
        report_type: Type of report to generate
        size: Size of the report (higher = longer processing time)
        report_progress: Function to report progress (injected by server)
        
    Returns:
        The generated report text
    """
    logger.info(f"Starting report generation: {report_type}, size={size}")
    
    # Simulate a long running task
    report_lines = []
    total_steps = size
    
    for i in range(total_steps):
        # Simulate work
        await asyncio.sleep(0.1)  # 100ms per step
        
        # Add a line to the report
        report_lines.append(f"Line {i+1}: Data for {report_type} report")
        
        # Report progress if available
        if report_progress:
            progress = (i + 1) / total_steps
            await report_progress(
                progress, 
                total_steps, 
                f"Generating report: {int(progress * 100)}% complete"
            )
            
            logger.debug(f"Reported progress: {progress:.2f}")
    
    # Simulate final processing
    await asyncio.sleep(0.5)
    
    # Return the complete report
    report_text = "\n".join(report_lines)
    return f"# {report_type.upper()} REPORT\n\n{report_text}"


@async_tool
async def data_processing(data: str, iterations: int = 5, report_progress=None) -> dict:
    """
    Process data with multiple iterations, reporting progress.
    
    Args:
        data: Input data to process
        iterations: Number of processing iterations
        report_progress: Function to report progress (injected by server)
        
    Returns:
        Dict with processing results
    """
    logger.info(f"Starting data processing: {len(data)} bytes, {iterations} iterations")
    
    results = {}
    
    for i in range(iterations):
        # Simulate processing step
        await asyncio.sleep(0.3)
        
        # Store result for this iteration
        results[f"iteration_{i+1}"] = {
            "input_size": len(data),
            "timestamp": time.time(),
            "sample": data[:10] + "..." if len(data) > 10 else data
        }
        
        # Report progress if available
        if report_progress:
            progress = (i + 1) / iterations
            await report_progress(
                progress, 
                iterations, 
                f"Processing iteration {i+1}/{iterations}"
            )
    
    return {
        "status": "success",
        "input_size": len(data),
        "iterations_completed": iterations,
        "results": results
    }


async def run_server():
    """Run an MCP server with callback support."""
    # Create the standard MCP server
    server = FastMcpServer()
    
    # Configure NATS transport
    nats_params = NatsServerParameters(
        url="nats://localhost:4222",
        service_name="mcp.service",
        server_id="callback-demo-server",
    )
    
    logger.info("Starting MCP server with callback support")
    
    # Start the server using NATS transport
    async with nats_server(nats_params) as (read_stream, write_stream):
        # Create a callback-enabled server wrapper
        callback_server = CallbackEnabledServer(server, nats_params._nats_client)
        
        # Register our async-aware tools
        # Note: These are registered directly with the FastMcpServer
        server.tools.register(generate_report)
        server.tools.register(data_processing)
        
        # Create a session and run the server
        session = Session()
        try:
            await server.run(session, read_stream, write_stream)
        except Exception as e:
            logger.exception(f"Server error: {e}")
        finally:
            await callback_server.close()


async def run_client():
    """Run an MCP client with callback support."""
    # Wait to ensure server is running
    await asyncio.sleep(1)
    
    # Configure NATS transport
    nats_params = NatsClientParameters(
        url="nats://localhost:4222",
        service_name="mcp.service",
        client_id="callback-demo-client",
    )
    
    logger.info("Starting MCP client with callback support")
    
    # Connect to the server using NATS transport
    async with nats_client(nats_params) as (read_stream, write_stream):
        # Create standard MCP client session
        mcp_client = ClientSession()
        await mcp_client.initialize(read_stream, write_stream)
        
        # Create callback-enabled client wrapper
        callback_client = CallbackEnabledClient(mcp_client, nats_params._nats_client)
        
        try:
            # Get available tools
            tools = await mcp_client.list_tools()
            logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
            
            # Start a long-running report generation task asynchronously
            logger.info("Starting async report generation...")
            report_task = await callback_client.call_tool_async(
                "generate_report", 
                {"report_type": "Financial", "size": 20}
            )
            report_id = report_task["callback_id"]
            logger.info(f"Report generation started with callback ID: {report_id}")
            
            # While the report is generating, start another task
            logger.info("Starting async data processing...")
            process_task = await callback_client.call_tool_async(
                "data_processing", 
                {"data": "Sample data for processing", "iterations": 3}
            )
            process_id = process_task["callback_id"]
            logger.info(f"Data processing started with callback ID: {process_id}")
            
            # Check pending tasks
            pending = await callback_client.list_pending_calls()
            logger.info(f"Pending tasks: {len(pending)}")
            
            # Wait for data processing to complete while report is still running
            logger.info(f"Waiting for data processing result...")
            process_result = await callback_client.get_async_result(process_id)
            logger.info(f"Data processing completed: {process_result['status']}")
            logger.info(f"Completed iterations: {process_result['result']['iterations_completed']}")
            
            # Now wait for the report
            logger.info(f"Waiting for report generation result...")
            report_result = await callback_client.get_async_result(report_id)
            logger.info(f"Report generation completed: {report_result['status']}")
            
            # Show part of the report
            report_text = report_result["result"]
            logger.info(f"Report preview: {report_text[:100]}...")
            
        except Exception as e:
            logger.exception(f"Client error: {e}")
        finally:
            await callback_client.close()


async def run_example():
    """Run both server and client using an exit stack."""
    # Start the server in a separate task
    server_task = asyncio.create_task(run_server())
    
    try:
        # Run the client
        await run_client()
    finally:
        # Cancel the server task when done
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


def main():
    """Main entry point."""
    try:
        anyio.run(run_example)
    except KeyboardInterrupt:
        logger.info("Example stopped by user")


if __name__ == "__main__":
    main()