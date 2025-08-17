import json
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models import game as game_model
from datetime import datetime, timedelta, timezone

# Pydantic schema for creating a game, mirroring the model fields
class GameCreateSchema(BaseModel):
    story_type: str
    writing_style: str
    author: str
    title: str
    story_map: str          # JSON string
    story_history: str      # JSON string
    current_scene_json: str # JSON string

class GameUpdateSchema(BaseModel):
    writing_style: str
    author: str
    title: str
    story_map: str
    story_history: str
    current_scene_json: str

async def create_game(db: AsyncSession, game: GameCreateSchema) -> game_model.Game:
    """
    Creates a new game in the database from a schema object.
    """
    new_game = game_model.Game(**game.dict())
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return new_game

async def get_game(db: AsyncSession, game_id: int) -> Optional[game_model.Game]:
    """
    Retrieves a game by its ID.
    """
    result = await db.execute(select(game_model.Game).where(game_model.Game.id == game_id))
    return result.scalars().first()

async def update_game(db: AsyncSession, game_id: int, game_in: GameUpdateSchema) -> Optional[game_model.Game]:
    """
    Updates a game with a full set of generated data.
    """
    result = await db.execute(select(game_model.Game).where(game_model.Game.id == game_id))
    game = result.scalars().first()
    if game:
        update_data = game_in.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(game, key, value)
        await db.commit()
        await db.refresh(game)
    return game

async def update_game_state(db: AsyncSession, game_id: int, story_history: str, current_scene_json: str) -> Optional[game_model.Game]:
    """
    Updates the story history and current scene for a specific game.
    """
    result = await db.execute(select(game_model.Game).where(game_model.Game.id == game_id))
    game = result.scalars().first()
    if game:
        game.story_history = story_history
        game.current_scene_json = current_scene_json
        await db.commit()
        await db.refresh(game)
    return game

async def delete_game(db: AsyncSession, game_id: int):
    """

    Deletes a game.
    """
    result = await db.execute(select(game_model.Game).where(game_model.Game.id == game_id))
    game = result.scalars().first()
    if game:
        await db.delete(game)
        await db.commit()

async def remove_inactive_games(db: AsyncSession, inactive_hours: int) -> int:
    """
    Deletes games that have not been updated for a specified number of hours.
    
    :param db: The async database session.
    :param inactive_hours: The threshold in hours for a game to be considered inactive.
    :return: The number of games deleted.
    """
    threshold = datetime.now(timezone.utc) - timedelta(hours=inactive_hours)
    
    result = await db.execute(
        select(game_model.Game)
        .where(game_model.Game.updated_at < threshold)
    )
    inactive_games = result.scalars().all()
    
    count = len(inactive_games)
    
    if count > 0:
        for game in inactive_games:
            await db.delete(game)
        await db.commit()
        
    return count
