from pydantic import BaseModel
from typing import List, Optional, Any

# --- Shared Models ---

class Choice(BaseModel):
    id: int
    text: str

class StorySegment(BaseModel):
    role: str # "assistant" (story) or "user" (choice)
    content: str

# --- Request Models ---

class GameCreate(BaseModel):
    story_type: str

class GameUpdate(BaseModel):
    choice_text: str

# --- Response Models ---

class Scene(BaseModel):
    content: str
    choices: List[Choice]
    current_node_id: str

class GameCreateResponse(BaseModel):
    game_id: int
    status: str

class GameStateResponse(BaseModel):
    game_id: int
    scene: Scene
    author: str
    title: str
    story_map: dict
    story_history: List[StorySegment]
