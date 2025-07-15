from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import AsyncSessionLocal
from app.crud import crud_game
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

async def prune_inactive_games_job():
    """
    An async job function wrapper to be called by the scheduler.
    """
    logger.info("Scheduled job: Starting cleanup of inactive games...")
    db: AsyncSession = AsyncSessionLocal()
    try:
        deleted_count = await crud_game.remove_inactive_games(
            db, 
            inactive_hours=settings.INACTIVE_GAME_CLEANUP_HOURS
        )
        logger.info(f"Scheduled job: Cleanup finished. Deleted {deleted_count} inactive games.")
    except Exception as e:
        logger.error(f"Scheduled job failed: {e}")
    finally:
        await db.close()

def setup_scheduler():
    """
    Adds jobs to the scheduler.
    """
    scheduler.add_job(
        prune_inactive_games_job, 
        'interval', 
        hours=settings.INACTIVE_GAME_CLEANUP_HOURS,
        id="prune_games_job",
        replace_existing=True
    )
    logger.info("Cleanup job has been added to the scheduler. It will run every %d hours.", settings.INACTIVE_GAME_CLEANUP_HOURS)