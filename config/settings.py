# ==============================================================================
# Settings & Configuration Management
# ==============================================================================

from pydantic_settings import BaseSettings
from typing import Optional

class SovereignSettings(BaseSettings):
    """Master configuration for Sovereign Commander"""
    
    # ZMQ
    zmq_endpoint: str = "tcp://127.0.0.1:5555"
    zmq_heartbeat_interval: int = 2
    zmq_heartbeat_timeout: int = 5
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_pool_size: int = 50
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sovereign_commander"
    postgres_user: str = "postgres"
    postgres_password: str = "changeme"
    postgres_pool_size: int = 20
    
    # Cold Dump
    cold_dump_interval_minutes: int = 5
    cold_dump_batch_size: int = 1000
    
    # Auth Vault
    auth_vault_token_ttl_minutes: int = 15
    auth_vault_secret_path: str = "/opt/sovereign/secrets"
    
    # LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo"
    anthropic_api_key: Optional[str] = None
    
    # QA
    qa_static_analysis_timeout: int = 30
    qa_llm_review_timeout: int = 120
    qa_rejection_rate_target: float = 0.90
    
    # Logging
    log_level: str = "INFO"
    prometheus_port: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = SovereignSettings()
