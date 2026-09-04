from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .database import Base, engine
from . import models
from .seed import seed_database

from .routers import products, negotiations, webhooks


app = FastAPI(
    title="Agent-to-Agent Price Negotiation",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

seed_database()


BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

@app.get("/ui")
def frontend():
    return FileResponse(
        BASE_DIR / "templates" / "index.html"
    )

app.include_router(products.router)
app.include_router(negotiations.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {
        "message": "Agent-to-Agent Price Negotiation API",
        "status": "running"
    }