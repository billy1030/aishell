"""Data models for aishell AI Skills."""

from typing import List
from pydantic import BaseModel, Field


class Skill(BaseModel):
    """Represents a loadable AI skill with trigger metadata and instructions."""

    name: str
    description: str
    instructions: str
    triggers: List[str] = Field(default_factory=list)
    source: str = "builtin"  # "builtin", "user", or "project"

