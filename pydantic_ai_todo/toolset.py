"""Todo toolset for pydantic-ai agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic_ai.toolsets import FunctionToolset

from pydantic_ai_todo.storage import (
    AsyncTodoStorageProtocol,
    TodoStorage,
    TodoStorageProtocol,
)
from pydantic_ai_todo.types import Todo, TodoItem

TODO_TOOL_DESCRIPTION = """
Use this tool to create and manage a structured task list for your current session.
This helps you track progress, organize complex tasks, and demonstrate thoroughness.

## When to Use This Tool
Use this tool in these scenarios:
1. Complex multi-step tasks - When a task requires 3 or more distinct steps
2. Non-trivial tasks - Tasks that require careful planning
3. User provides multiple tasks - When users provide a list of things to be done
4. After receiving new instructions - Capture user requirements as todos
5. When starting a task - Mark it as in_progress BEFORE beginning work
6. After completing a task - Mark it as completed immediately

## Task States
- pending: Task not yet started
- in_progress: Currently working on (limit to ONE at a time)
- completed: Task finished successfully

## Important
- Exactly ONE task should be in_progress at any time
- Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
- If you encounter blockers, keep the task as in_progress and create a new task for the blocker
"""

TODO_SYSTEM_PROMPT = """
## Task Management

You have access to todo tools to track your tasks:
- `read_todos` - View current tasks with their IDs and statuses
- `write_todos` - Replace the entire todo list
- `add_todo` - Add a single new task
- `update_todo_status` - Change a task's status by ID
- `remove_todo` - Delete a task by ID

When working on tasks:
1. Break down complex tasks into smaller steps
2. Mark exactly one task as in_progress at a time
3. Mark tasks as completed immediately after finishing
"""

READ_TODO_DESCRIPTION = """
Read the current todo list state.

Use this tool to check the current status of all tasks before:
- Deciding what to work on next
- Updating task statuses
- Reporting progress to the user

Returns all todos with their ID, current status (pending, in_progress, completed), and content.
"""

ADD_TODO_DESCRIPTION = """
Add a single new todo item to the list.

Use this tool to add a new task without replacing existing todos.
Returns the ID of the newly created todo.
"""

UPDATE_TODO_STATUS_DESCRIPTION = """
Update the status of an existing todo by its ID.

Use this tool to change a todo's status to pending, in_progress, or completed.
Returns confirmation or error if the todo is not found.
"""

REMOVE_TODO_DESCRIPTION = """
Remove a todo from the list by its ID.

Use this tool to delete a task that is no longer needed.
Returns confirmation or error if the todo is not found.
"""


def create_todo_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    async_storage: AsyncTodoStorageProtocol | None = None,
    id: str | None = None,
) -> FunctionToolset[Any]:
    """Create a todo toolset for task management.

    This toolset provides read_todos and write_todos tools for AI agents
    to track and manage tasks during a session.

    Args:
        storage: Optional sync storage backend. Defaults to in-memory TodoStorage.
            You can provide a custom storage implementing TodoStorageProtocol.
            Ignored if async_storage is provided.
        async_storage: Optional async storage backend implementing AsyncTodoStorageProtocol.
            When provided, all operations use async methods for true persistence.
        id: Optional unique ID for the toolset.

    Returns:
        FunctionToolset compatible with any pydantic-ai agent.

    Example (standalone):
        ```python
        from pydantic_ai import Agent
        from pydantic_ai_todo import create_todo_toolset

        agent = Agent("openai:gpt-4.1", toolsets=[create_todo_toolset()])
        result = await agent.run("Create a todo list for my project")
        ```

    Example (with sync storage):
        ```python
        from pydantic_ai_todo import create_todo_toolset, TodoStorage

        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        # After agent runs, access todos directly
        print(storage.todos)
        ```

    Example (with async storage):
        ```python
        from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage)

        # After agent runs, access todos
        todos = await storage.get_todos()
        ```
    """
    # Use async storage if provided, otherwise fall back to sync storage
    if async_storage is not None:
        return _create_async_toolset(async_storage, id=id)
    else:
        return _create_sync_toolset(storage, id=id)


def _create_sync_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    id: str | None = None,
) -> FunctionToolset[Any]:
    """Create toolset with sync storage (backwards compatible)."""
    _storage = storage if storage is not None else TodoStorage()

    toolset: FunctionToolset[Any] = FunctionToolset(id=id)

    @toolset.tool(description=READ_TODO_DESCRIPTION)
    async def read_todos() -> str:
        """Read the current todo list."""
        if not _storage.todos:
            return "No todos in the list. Use write_todos to create tasks."

        lines = ["Current todos:"]
        for i, todo in enumerate(_storage.todos, 1):
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[*]",
                "completed": "[x]",
            }.get(todo.status, "[ ]")
            lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

        # Add summary
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in _storage.todos:
            counts[todo.status] += 1

        lines.append("")
        lines.append(
            f"Summary: {counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

        return "\n".join(lines)

    @toolset.tool(description=TODO_TOOL_DESCRIPTION)
    async def write_todos(todos: list[TodoItem]) -> str:
        """Update the todo list with new items.

        Args:
            todos: List of todo items with content, status, and active_form.
        """
        new_todos: list[Todo] = []
        for t in todos:
            if t.id is not None:
                new_todos.append(
                    Todo(id=t.id, content=t.content, status=t.status, active_form=t.active_form)
                )
            else:
                new_todos.append(
                    Todo(content=t.content, status=t.status, active_form=t.active_form)
                )
        _storage.todos = new_todos

        # Count by status
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in _storage.todos:
            counts[todo.status] += 1

        return (
            f"Updated {len(todos)} todos: "
            f"{counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

    @toolset.tool(description=ADD_TODO_DESCRIPTION)
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form shown during execution.

        Returns:
            Confirmation message with the new todo's ID.
        """
        new_todo = Todo(content=content, status="pending", active_form=active_form)
        _storage.todos = [*_storage.todos, new_todo]
        return f"Added todo '{content}' with ID: {new_todo.id}"

    @toolset.tool(description=UPDATE_TODO_STATUS_DESCRIPTION)
    async def update_todo_status(todo_id: str, status: str) -> str:
        """Update the status of an existing todo.

        Args:
            todo_id: The ID of the todo to update.
            status: New status (pending, in_progress, or completed).

        Returns:
            Confirmation message or error if not found.
        """
        valid_statuses = {"pending", "in_progress", "completed"}
        if status not in valid_statuses:
            return f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"

        for todo in _storage.todos:
            if todo.id == todo_id:
                todo.status = status  # type: ignore[assignment]
                return f"Updated todo '{todo.content}' status to '{status}'"

        return f"Todo with ID '{todo_id}' not found"

    @toolset.tool(description=REMOVE_TODO_DESCRIPTION)
    async def remove_todo(todo_id: str) -> str:
        """Remove a todo from the list.

        Args:
            todo_id: The ID of the todo to remove.

        Returns:
            Confirmation message or error if not found.
        """
        for i, todo in enumerate(_storage.todos):
            if todo.id == todo_id:
                removed = _storage.todos.pop(i)
                return f"Removed todo '{removed.content}' (ID: {todo_id})"

        return f"Todo with ID '{todo_id}' not found"

    return toolset


def _create_async_toolset(
    storage: AsyncTodoStorageProtocol,
    *,
    id: str | None = None,
) -> FunctionToolset[Any]:
    """Create toolset with async storage for true persistence."""
    toolset: FunctionToolset[Any] = FunctionToolset(id=id)

    @toolset.tool(description=READ_TODO_DESCRIPTION)
    async def read_todos() -> str:
        """Read the current todo list."""
        todos = await storage.get_todos()
        if not todos:
            return "No todos in the list. Use write_todos to create tasks."

        lines = ["Current todos:"]
        for i, todo in enumerate(todos, 1):
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[*]",
                "completed": "[x]",
            }.get(todo.status, "[ ]")
            lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

        # Add summary
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in todos:
            counts[todo.status] += 1

        lines.append("")
        lines.append(
            f"Summary: {counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

        return "\n".join(lines)

    @toolset.tool(description=TODO_TOOL_DESCRIPTION)
    async def write_todos(todos: list[TodoItem]) -> str:
        """Update the todo list with new items.

        Args:
            todos: List of todo items with content, status, and active_form.
        """
        new_todos: list[Todo] = []
        for t in todos:
            if t.id is not None:
                new_todos.append(
                    Todo(id=t.id, content=t.content, status=t.status, active_form=t.active_form)
                )
            else:
                new_todos.append(
                    Todo(content=t.content, status=t.status, active_form=t.active_form)
                )
        await storage.set_todos(new_todos)

        # Count by status
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in new_todos:
            counts[todo.status] += 1

        return (
            f"Updated {len(todos)} todos: "
            f"{counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

    @toolset.tool(description=ADD_TODO_DESCRIPTION)
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form shown during execution.

        Returns:
            Confirmation message with the new todo's ID.
        """
        new_todo = Todo(content=content, status="pending", active_form=active_form)
        await storage.add_todo(new_todo)
        return f"Added todo '{content}' with ID: {new_todo.id}"

    @toolset.tool(description=UPDATE_TODO_STATUS_DESCRIPTION)
    async def update_todo_status(
        todo_id: str, status: Literal["pending", "in_progress", "completed"]
    ) -> str:
        """Update the status of an existing todo.

        Args:
            todo_id: The ID of the todo to update.
            status: New status (pending, in_progress, or completed).

        Returns:
            Confirmation message or error if not found.
        """
        updated = await storage.update_todo(todo_id, status=status)
        if updated:
            return f"Updated todo '{updated.content}' status to '{status}'"
        return f"Todo with ID '{todo_id}' not found"

    @toolset.tool(description=REMOVE_TODO_DESCRIPTION)
    async def remove_todo(todo_id: str) -> str:
        """Remove a todo from the list.

        Args:
            todo_id: The ID of the todo to remove.

        Returns:
            Confirmation message or error if not found.
        """
        # Get todo content before removing for the message
        todo = await storage.get_todo(todo_id)
        if todo:
            await storage.remove_todo(todo_id)
            return f"Removed todo '{todo.content}' (ID: {todo_id})"
        return f"Todo with ID '{todo_id}' not found"

    return toolset


def get_todo_system_prompt(storage: TodoStorageProtocol | None = None) -> str:
    """Generate dynamic system prompt section for todos.

    Args:
        storage: Optional sync storage to read current todos from.

    Returns:
        System prompt section with current todos, or base prompt if no todos.

    Note:
        For async storage, use get_todo_system_prompt_async instead.
    """
    if storage is None or not storage.todos:
        return TODO_SYSTEM_PROMPT

    lines = [TODO_SYSTEM_PROMPT, "", "## Current Todos"]

    for todo in storage.todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} {todo.content}")

    return "\n".join(lines)


async def get_todo_system_prompt_async(
    storage: AsyncTodoStorageProtocol | None = None,
) -> str:
    """Generate dynamic system prompt section for todos (async version).

    Args:
        storage: Optional async storage to read current todos from.

    Returns:
        System prompt section with current todos, or base prompt if no todos.
    """
    if storage is None:
        return TODO_SYSTEM_PROMPT

    todos = await storage.get_todos()
    if not todos:
        return TODO_SYSTEM_PROMPT

    lines = [TODO_SYSTEM_PROMPT, "", "## Current Todos"]

    for todo in todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} {todo.content}")

    return "\n".join(lines)
