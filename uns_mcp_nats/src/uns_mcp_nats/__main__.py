"""Command-line interface for UNS-MCP with NATS transport."""

import argparse
import asyncio
import logging
import sys

from .client import run_client
from .server import run_server
from .config import UNSMcpNatsConfig


def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="UNS-MCP with NATS transport",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Add subparsers for server and client modes
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run")
    
    # Server subparser
    server_parser = subparsers.add_parser("server", help="Run the server")
    server_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    
    # Client subparser
    client_parser = subparsers.add_parser("client", help="Run the client")
    client_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    client_parser.add_argument(
        "--confirm",
        action="store_true",
        default=True,
        help="Confirm tool use before execution",
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Load configuration from environment variables
    config = UNSMcpNatsConfig.from_dotenv()
    
    # Run the appropriate mode
    if args.mode == "server":
        asyncio.run(run_server(config))
    elif args.mode == "client":
        asyncio.run(run_client(config))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()