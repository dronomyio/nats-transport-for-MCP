"""Configuration module for UNS-MCP with NATS transport."""

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field


class NatsConfig(BaseModel):
    """NATS configuration settings."""
    
    url: str = "nats://localhost:4222"
    """The URL of the NATS server to connect to."""
    
    service_name: str = "uns.mcp.service"
    """The name of the MCP service to connect to."""
    
    client_id_prefix: str = "uns-mcp-client"
    """Prefix for client ID generation."""
    
    server_id_prefix: str = "uns-mcp-server"
    """Prefix for server ID generation."""
    
    queue_group: str = "uns-mcp-servers"
    """Queue group for load balancing across servers."""
    
    request_timeout: float = 30.0
    """Timeout in seconds for service requests."""


class UnstructuredConfig(BaseModel):
    """Unstructured API configuration."""
    
    api_key: str
    """Unstructured API key for authentication."""
    
    debug_requests: bool = False
    """Enable debug mode for HTTP requests."""


class UNSMcpNatsConfig(BaseModel):
    """Main configuration class for UNS-MCP with NATS transport."""
    
    nats: NatsConfig = Field(default_factory=NatsConfig)
    """NATS configuration."""
    
    unstructured: Optional[UnstructuredConfig] = None
    """Unstructured API configuration."""
    
    @classmethod
    def from_env(cls) -> "UNSMcpNatsConfig":
        """Load configuration from environment variables.
        
        Returns:
            UNSMcpNatsConfig: Configuration object loaded from environment variables.
        """
        # Load NATS configuration
        nats_config = NatsConfig(
            url=os.getenv("NATS_URL", "nats://localhost:4222"),
            service_name=os.getenv("NATS_SERVICE_NAME", "uns.mcp.service"),
            client_id_prefix=os.getenv("NATS_CLIENT_PREFIX", "uns-mcp-client"),
            server_id_prefix=os.getenv("NATS_SERVER_PREFIX", "uns-mcp-server"),
            queue_group=os.getenv("NATS_QUEUE_GROUP", "uns-mcp-servers"),
            request_timeout=float(os.getenv("NATS_REQUEST_TIMEOUT", "30.0")),
        )
        
        # Load Unstructured API configuration if key is present
        unstructured_config = None
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if api_key:
            unstructured_config = UnstructuredConfig(
                api_key=api_key,
                debug_requests=os.getenv("DEBUG_API_REQUESTS", "").lower() == "true"
            )
        
        return cls(
            nats=nats_config,
            unstructured=unstructured_config
        )
    
    @classmethod
    def from_dotenv(cls, env_file: str = ".env") -> "UNSMcpNatsConfig":
        """Load configuration from .env file.
        
        Args:
            env_file: Path to the .env file.
            
        Returns:
            UNSMcpNatsConfig: Configuration object loaded from .env file.
        """
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_file)
        except ImportError:
            pass  # Dotenv is optional
            
        return cls.from_env()