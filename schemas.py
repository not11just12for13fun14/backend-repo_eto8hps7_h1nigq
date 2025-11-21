"""
Database Schemas for the Journaling App

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name (e.g., Entry -> "entry").
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date


class User(BaseModel):
    email: str = Field(..., description="Unique email for the user")
    name: str = Field(..., description="Display name")
    avatar: Optional[str] = Field(None, description="Avatar image URL")
    bio: Optional[str] = Field(None, description="Short bio")
    theme: str = Field("aurora", description="Selected theme id")
    font: str = Field("Inter", description="Preferred UI font family")
    goals: Optional[List[str]] = Field(default_factory=list, description="Personal goals list")


class Entry(BaseModel):
    user_email: str = Field(..., description="Owner user email")
    date: date = Field(..., description="Entry date (YYYY-MM-DD)")
    mood: Optional[str] = Field(None, description="Mood label")
    answers: Dict[str, str] = Field(default_factory=dict, description="Guided answers map")
    thoughts: Optional[str] = Field(None, description="Free-form thoughts")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Trackers like sleep, water, caffeine, exercise mins, etc.")
    tags: List[str] = Field(default_factory=list, description="Keywords extracted from content")
    doodle: Dict[str, Any] = Field(default_factory=dict, description="Structured doodle description generated from the entry")


class Todo(BaseModel):
    user_email: str = Field(..., description="Owner user email")
    date: date = Field(..., description="Scheduled date")
    title: str = Field(..., description="Task title")
    done: bool = Field(False, description="Completion status")
    notes: Optional[str] = Field(None, description="Optional notes")
