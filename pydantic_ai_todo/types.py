"""Type definitions for pydantic-ai-todo."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Todo(BaseModel):
    """A todo item for task tracking.

    Attributes:
        id: Unique identifier for the todo (auto-generated 8-char hex string).
        content: The task description in imperative form (e.g., 'Implement feature X').
        status: Task status - 'pending', 'in_progress', or 'completed'.
        active_form: Present continuous form shown during execution
            (e.g., 'Implementing feature X').
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    content: str
    status: Literal["pending", "in_progress", "completed"]
    active_form: str


class TodoItem(BaseModel):
    """Input model for the write_todos tool.

    This is the model that agents use when calling write_todos.
    It has the same fields as Todo but with Field descriptions for LLM guidance.
    """

    id: str | None = Field(
        default=None,
        description="Unique identifier for the todo. Auto-generated if not provided.",
    )
    content: str = Field(
        ..., description="The task description in imperative form (e.g., 'Implement feature X')"
    )
    status: Literal["pending", "in_progress", "completed"] = Field(
        ..., description="Task status: pending, in_progress, or completed"
    )
    active_form: str = Field(
        ...,
        description="Present continuous form during execution (e.g., 'Implementing feature X')",
    )
