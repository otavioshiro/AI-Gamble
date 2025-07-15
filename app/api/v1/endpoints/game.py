import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import game as game_schema
from app.services import story_generator
from app.crud import crud_game
from app.database import get_session

router = APIRouter()

@router.post("/game", response_model=game_schema.GameStateResponse, status_code=201)
async def create_game(
    game_in: game_schema.GameCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Starts a new game, generates the initial state, and saves it to the database.
    """
    logging.info(f"Starting new game for story type '{game_in.story_type}'")
    
    initial_data = await story_generator.generate_initial_scene(game_in.story_type)
    
    game_to_create = crud_game.GameCreateSchema(
        story_type=game_in.story_type,
        writing_style=initial_data["writing_style"],
        author=initial_data["author"],
        title=initial_data["title"],
        story_map=json.dumps(initial_data["story_map"], ensure_ascii=False),
        story_history=json.dumps(initial_data["story_history"], ensure_ascii=False),
        current_scene_json=json.dumps(initial_data["scene_data"], ensure_ascii=False)
    )
    
    game = await crud_game.create_game(db, game=game_to_create)
    
    return game_schema.GameStateResponse(
        game_id=game.id,
        scene=initial_data["scene_data"],
        author=game.author,
        title=game.title,
        story_map=initial_data["story_map"],
        story_history=initial_data["story_history"]
    )

@router.post("/game/{game_id}/choice", response_model=game_schema.GameStateResponse)
async def next_scene(
    game_id: int,
    choice_in: game_schema.GameUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Processes a player's choice, generates the next part of the story, and saves the new state.
    """
    game = await crud_game.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    try:
        story_map = json.loads(game.story_map)
        story_history = json.loads(game.story_history)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse game state.")

    next_data = await story_generator.generate_next_scene(
        writing_style=game.writing_style,
        story_map=story_map,
        story_history=story_history,
        choice_text=choice_in.choice_text
    )

    updated_history_str = json.dumps(next_data["story_history"], ensure_ascii=False)
    updated_scene_str = json.dumps(next_data["scene_data"], ensure_ascii=False)
    
    await crud_game.update_game_state(
        db, 
        game_id=game_id, 
        story_history=updated_history_str, 
        current_scene_json=updated_scene_str
    )

    return game_schema.GameStateResponse(
        game_id=game.id,
        scene=next_data["scene_data"],
        author=game.author,
        title=game.title,
        story_map=story_map,
        story_history=next_data["story_history"]
    )

@router.get("/game/{game_id}", response_model=game_schema.GameStateResponse)
async def get_game_state(game_id: int, db: AsyncSession = Depends(get_session)):
    """
    Retrieves the full current state of a game directly from the database.
    """
    game = await crud_game.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    try:
        story_map = json.loads(game.story_map)
        story_history = json.loads(game.story_history)
        scene = json.loads(game.current_scene_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Failed to parse stored game state.")

    return game_schema.GameStateResponse(
        game_id=game.id,
        scene=scene,
        author=game.author,
        title=game.title,
        story_map=story_map,
        story_history=story_history
    )

@router.delete("/game/{game_id}", status_code=204)
async def delete_game_session(game_id: int, db: AsyncSession = Depends(get_session)):
    """
    Deletes a game session.
    """
    game = await crud_game.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    await crud_game.delete_game(db, game_id=game_id)
    logging.info(f"Deleted game {game_id}")
    return