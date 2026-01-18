"""Storage abstraction for todo items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from pydantic_ai_todo.types import Todo


@runtime_checkable
class TodoStorageProtocol(Protocol):
    """Protocol for todo storage implementations.

    Any class that has a `todos` property (read/write) implementing
    `list[Todo]` can be used as storage for the todo toolset.

    Example:
        ```python
        class MyCustomStorage:
            def __init__(self):
                self._todos: list[Todo] = []

            @property
            def todos(self) -> list[Todo]:
                return self._todos

            @todos.setter
            def todos(self, value: list[Todo]) -> None:
                self._todos = value
        ```
    """

    @property
    def todos(self) -> list[Todo]:
        """Get the current list of todos."""
        ...

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        """Set the list of todos."""
        ...


@dataclass
class TodoStorage:
    """Default in-memory todo storage.

    Simple implementation that stores todos in memory.
    Use this for standalone agents or testing.

    Example:
        ```python
        from pydantic_ai_todo import create_todo_toolset, TodoStorage

        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        # After agent runs, access todos directly
        print(storage.todos)
        ```
    """

    _todos: list[Todo] = field(default_factory=lambda: [])

    @property
    def todos(self) -> list[Todo]:
        """Get the current list of todos."""
        return self._todos

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        """Set the list of todos."""
        self._todos = value


class AsyncTodoStorageProtocol(Protocol):
    """Protocol for async todo storage implementations.

    This protocol defines the interface for async storage backends
    that support true persistence (database, file, etc.).

    Example:
        ```python
        class MyAsyncStorage:
            async def get_todos(self) -> list[Todo]:
                return await db.fetch_todos()

            async def set_todos(self, todos: list[Todo]) -> None:
                await db.save_todos(todos)

            async def get_todo(self, id: str) -> Todo | None:
                return await db.get_todo(id)

            async def add_todo(self, todo: Todo) -> Todo:
                return await db.insert_todo(todo)

            async def update_todo(self, id: str, **fields) -> Todo | None:
                return await db.update_todo(id, fields)

            async def remove_todo(self, id: str) -> bool:
                return await db.delete_todo(id)
        ```
    """

    async def get_todos(self) -> list[Todo]:
        """Get all todos."""
        ...

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos with the provided list."""
        ...

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID."""
        ...

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo and return it."""
        ...

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID. Returns None if not found."""
        ...

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID. Returns True if removed, False if not found."""
        ...


class AsyncMemoryStorage:
    """Async in-memory todo storage.

    Implements AsyncTodoStorageProtocol for testing and simple use cases.
    Data is stored in memory and lost when the process ends.

    Example:
        ```python
        from pydantic_ai_todo import AsyncMemoryStorage, create_todo_toolset

        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage)

        # After agent runs, access todos
        todos = await storage.get_todos()
        ```
    """

    def __init__(self) -> None:
        self._todos: list[Todo] = []

    async def get_todos(self) -> list[Todo]:
        """Get all todos."""
        return list(self._todos)

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos with the provided list."""
        self._todos = list(todos)

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID."""
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo and return it."""
        self._todos.append(todo)
        return todo

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID. Returns None if not found."""
        for todo in self._todos:
            if todo.id == id:
                if content is not None:
                    todo.content = content
                if status is not None:
                    todo.status = status
                if active_form is not None:
                    todo.active_form = active_form
                if parent_id is not None:
                    todo.parent_id = parent_id
                if depends_on is not None:
                    todo.depends_on = depends_on
                return todo
        return None

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID. Returns True if removed, False if not found."""
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False


def create_storage(backend: Literal["memory"] = "memory") -> AsyncMemoryStorage:
    """Factory function to create storage backends.

    Args:
        backend: The storage backend to use. Currently only "memory" is supported.

    Returns:
        An async storage instance.

    Example:
        ```python
        from pydantic_ai_todo import create_storage

        storage = create_storage("memory")
        toolset = create_todo_toolset(async_storage=storage)
        ```
    """
    if backend == "memory":
        return AsyncMemoryStorage()
    # This line is unreachable due to Literal type, but keeps future extensibility clear
    raise ValueError(f"Unknown storage backend: {backend}")  # pragma: no cover
