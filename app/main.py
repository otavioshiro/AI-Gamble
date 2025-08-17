import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.services.sse_service import redis_client, sse_generator
from app.api.v1.endpoints import game
from app.scheduler import scheduler, setup_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    # Startup
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    await init_db()
    await redis_client.connect()
    setup_scheduler()
    scheduler.start()
    
    yield
    
    # Shutdown
    await redis_client.close()
    scheduler.shutdown()

app = FastAPI(title="AI Gamble Game", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """
    Serves the main game page.
    """
    return FileResponse('templates/index.html')

@app.get("/events/{game_id}")
async def sse_events(request: Request, game_id: int):
    """
    Endpoint for Server-Sent Events (SSE) to stream game updates.
    """
    return StreamingResponse(sse_generator(game_id), media_type="text/event-stream")

# Include API routers
app.include_router(game.router, prefix="/api/v1", tags=["game"])
