from fastapi import FastAPI

from .database import (
    Base,
    engine
)

from . import models

from .routers import (
    products,
    negotiations,
    webhooks
)


app = FastAPI(
    title="Agent-to-Agent Price Negotiation",
    version="1.0.0"
)
app.include_router(
    webhooks.router
)

Base.metadata.create_all(
    bind=engine
)


app.include_router(
    products.router
)

app.include_router(
    negotiations.router
)


@app.get("/")
def root():

    return {
        "message":
            "Agent-to-Agent Price Negotiation API",

        "status":
            "running"
    }