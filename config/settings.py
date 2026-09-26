# ==============================================================================
# Settings & Configuration Management
# ==============================================================================
# Models the real keys found in project .env (see .env.example).
# Unknown/legacy keys are ignored (extra="ignore") instead of raising.
# ==============================================================================


from pydantic_settings import BaseSettings


class SovereignSettings(BaseSettings):
    """Master configuration for Sovereign Commander"""

    # ZMQ Neural Bus (names match matrix_main.py / neural_bus.py)
    zmq_router_url: str = "tcp://127.0.0.1:5555"
    zmq_bus_url: str = "tcp://127.0.0.1:5555"
    zmq_endpoint: str = "tcp://127.0.0.1:5555"  # legacy alias
    zmq_heartbeat_interval: int = 2
    zmq_heartbeat_timeout: int = 5

    # Sovereign bus identity
    sovereign_bus_secret: str | None = None
    matrix_memory_root: str = "./memory"
    commander_auth_token: str = ""

    # Local inference (Ollama)
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_default_model: str = "llama3.2"

    # Cloud inference (Groq LPU pool — positional 001=dranashilal,
    # 002=r11salfd, 003=tarek)
    groq_api_key: str | None = None
    groq_api_key_001: str | None = None
    groq_api_key_002: str | None = None
    groq_api_key_003: str | None = None
    groq_account_001_email: str | None = None
    groq_account_002_email: str | None = None
    groq_account_003_email: str | None = None

    # Identity (Clerk)
    clerk_secret_key: str | None = None
    clerk_pem_public_key: str | None = None

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
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

    # LLM (legacy vendor slots)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo"
    anthropic_api_key: str | None = None

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
        # .env carries keys not modeled above — ignore extras instead of raising.
        extra = "ignore"


settings = SovereignSettings()
