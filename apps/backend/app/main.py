"""Knock Knock backend entrypoint.

Control plane API + enrollment + (optionally) the MQTT bridge background task.
"""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import devices, enrollment, policies
from app.config import get_settings
from app.database import Base, engine
from app.services.mqtt_bridge import run_bridge

# Import models so they register on Base.metadata for dev_create_tables.
from app import models  # noqa: F401,E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Dev convenience: create tables without migrations. LOCAL ONLY.
    if settings.dev_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    bridge_task = None
    if settings.enable_mqtt_bridge:
        bridge_task = asyncio.create_task(run_bridge())

    yield

    if bridge_task is not None:
        bridge_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bridge_task


app = FastAPI(title="Knock Knock API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dashboard dev origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(enrollment.router)
app.include_router(policies.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
