from typing import Optional
import datetime
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    story_type: str
    writing_style: Optional[str] = Field(default=None)
    author: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    story_map: Optional[str] = Field(default=None)  # Store story map as JSON string
    story_history: Optional[str] = Field(default="[]")  # Store story history as JSON string
    current_scene_json: Optional[str] = Field(default=None) # Store current scene as JSON string
    current_node_id: str = Field(default="start")
    created_at: datetime.datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
    )
    updated_at: datetime.datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    )