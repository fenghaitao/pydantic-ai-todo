"""Event system for todo operations.

This module provides an event-driven system for reacting to todo changes.
It supports both sync and async callbacks for integration with external systems.

Example:
    ```python
    from pydantic_ai_todo import TodoEventEmitter, TodoEventType

    emitter = TodoEventEmitter()

    @emitter.on_created
    async def notify_created(event):
        print(f"Todo created: {event.todo.content}")

    @emitter.on_completed
    async def notify_completed(event):
        print(f"Todo completed: {event.todo.content}")
    ```
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import TypeAlias

from pydantic import BaseModel, Field

from pydantic_ai_todo.types import Todo


class TodoEventType(str, Enum):
    """Types of events that can be emitted for todo operations.

    Attributes:
        CREATED: A new todo was created.
        UPDATED: A todo was modified (any field change).
        STATUS_CHANGED: A todo's status was changed.
        DELETED: A todo was removed.
        COMPLETED: A todo was marked as completed.
    """

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    DELETED = "deleted"
    COMPLETED = "completed"


class TodoEvent(BaseModel):
    """Event data emitted when a todo changes.

    Attributes:
        event_type: The type of event that occurred.
        todo: The todo item affected by the event.
        timestamp: When the event occurred (UTC).
        previous_state: The todo state before the change (for updates).
    """

    event_type: TodoEventType
    todo: Todo
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_state: Todo | None = None


# Type alias for event callbacks (sync or async)
EventCallback: TypeAlias = Callable[[TodoEvent], None | Awaitable[None]]


class TodoEventEmitter:
    """Event emitter for todo operations.

    Manages registration and invocation of event listeners.
    Supports both synchronous and asynchronous callbacks.

    Example:
        ```python
        emitter = TodoEventEmitter()

        # Register callback for specific event type
        def on_created(event: TodoEvent):
            print(f"Created: {event.todo.content}")

        emitter.on(TodoEventType.CREATED, on_created)

        # Or use decorator syntax
        @emitter.on_created
        async def handle_created(event: TodoEvent):
            await notify_slack(event.todo)
        ```
    """

    def __init__(self) -> None:
        self._listeners: dict[TodoEventType, list[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        """Register a callback for an event type.

        Args:
            event_type: The type of event to listen for.
            callback: Function to call when event occurs (sync or async).

        Returns:
            The callback function (for decorator usage).
        """
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        """Unregister a callback for an event type.

        Args:
            event_type: The type of event.
            callback: The callback to remove.

        Returns:
            True if callback was removed, False if not found.
        """
        try:
            self._listeners[event_type].remove(callback)
            return True
        except ValueError:
            return False

    async def emit(self, event: TodoEvent) -> None:
        """Emit an event to all registered listeners.

        Calls all registered callbacks for the event type.
        Supports both sync and async callbacks.

        Args:
            event: The event to emit.
        """
        for callback in self._listeners[event.event_type]:
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result

    # Convenience decorators for common event types

    def on_created(self, callback: EventCallback) -> EventCallback:
        """Decorator to register a callback for CREATED events.

        Example:
            ```python
            @emitter.on_created
            async def handle_created(event: TodoEvent):
                print(f"New todo: {event.todo.content}")
            ```
        """
        return self.on(TodoEventType.CREATED, callback)

    def on_completed(self, callback: EventCallback) -> EventCallback:
        """Decorator to register a callback for COMPLETED events.

        Example:
            ```python
            @emitter.on_completed
            async def handle_completed(event: TodoEvent):
                print(f"Completed: {event.todo.content}")
            ```
        """
        return self.on(TodoEventType.COMPLETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        """Decorator to register a callback for STATUS_CHANGED events.

        Example:
            ```python
            @emitter.on_status_changed
            async def handle_status_change(event: TodoEvent):
                old = event.previous_state.status if event.previous_state else None
                print(f"Status: {old} -> {event.todo.status}")
            ```
        """
        return self.on(TodoEventType.STATUS_CHANGED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        """Decorator to register a callback for UPDATED events.

        Example:
            ```python
            @emitter.on_updated
            async def handle_update(event: TodoEvent):
                print(f"Updated: {event.todo.id}")
            ```
        """
        return self.on(TodoEventType.UPDATED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        """Decorator to register a callback for DELETED events.

        Example:
            ```python
            @emitter.on_deleted
            async def handle_delete(event: TodoEvent):
                print(f"Deleted: {event.todo.id}")
            ```
        """
        return self.on(TodoEventType.DELETED, callback)
