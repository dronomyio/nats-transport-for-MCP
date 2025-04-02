"""Configuration for UNS-MCP with NATS transport"""
import os
from typing import Dict, Optional
from pydantic import BaseModel

class NatsConfig(BaseModel):
    """NATS configuration settings"""
    url: str = "nats://localhost:4222"
    service_name: str = "uns.mcp.service"
    client_id_prefix: str = "uns-mcp-client"
    server_id_prefix: str = "uns-mcp-server" 
    queue_group: str = "uns-mcp-servers"
    request_timeout: float = 30.0

class UnstructuredConfig(BaseModel):
    """Unstructured API configuration"""
    api_key: str
    debug_requests: bool = False

class Config(BaseModel):
    """Main configuration class"""
    nats: NatsConfig = NatsConfig()
    unstructured: Optional[UnstructuredConfig] = None
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
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