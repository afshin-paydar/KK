from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://kk:kk@localhost:5432/kk"

    # IDaaS (operator auth)
    idaas_issuer: str = ""
    idaas_audience: str = "kk-dashboard"
    idaas_jwks_url: str = ""

    # Qwen / DashScope (backend-only secret)
    qwen_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_api_key: str = ""
    qwen_default_model: str = "qwen-plus"

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 8883
    mqtt_ca_cert: str = "./pki/ca-chain.pem"
    mqtt_client_cert: str = "./pki/backend-client.pem"
    mqtt_client_key: str = "./pki/backend-client.key"

    # PKI
    pki_ca_cert: str = "./pki/intermediate-ca.pem"
    pki_ca_key: str = "./pki/intermediate-ca.key"
    pki_device_cert_ttl_days: int = 30

    # App
    enrollment_token_ttl_minutes: int = 60
    log_level: str = "info"

    # Dev mode (LOCAL ONLY — never enable in production)
    dev_auth: bool = False          # bypass IDaaS, accept a stub admin operator
    dev_create_tables: bool = False  # auto-create tables on startup (no migrations)
    enable_mqtt_bridge: bool = True  # run the MQTT decision-loop bridge task


@lru_cache
def get_settings() -> Settings:
    return Settings()
