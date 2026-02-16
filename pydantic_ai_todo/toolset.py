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

The `active_form` parameter is the present-continuous version of the task content,
used as a status label while the task is being worked on.
Generate it yourself from the content — e.g. "Fix the login bug" → "Fixing the login bug".
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

ADD_SUBTASK_DESCRIPTION = """
Add a subtask to an existing todo.

Use this tool to break down a task into smaller subtasks.
The subtask will be linked to its parent via parent_id.
Returns the ID of the newly created subtask.

The `active_form` parameter is the present-continuous version of the task content,
used as a status label while the task is being worked on.
Generate it yourself from the content — e.g. "Create login endpoint" → "Creating login endpoint".
"""

SET_DEPENDENCY_DESCRIPTION = """
Set a dependency between two todos.

Use this tool to specify that one task depends on another.
The dependent task will be blocked until its dependency is completed.
Returns confirmation or error if validation fails.
"""

GET_AVAILABLE_TASKS_DESCRIPTION = """
Get all tasks that can be worked on now.

Returns only tasks that have no incomplete dependencies.
Blocked tasks are excluded from the list.
Use this to decide what to work on next.
"""


def create_todo_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    async_storage: AsyncTodoStorageProtocol | None = None,
    id: str | None = None,
    enable_subtasks: bool = False,
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
        enable_subtasks: Enable subtask and dependency features. When True, adds:
            - add_subtask: Create subtasks linked to parent todos
            - set_dependency: Create dependencies between todos
            - get_available_tasks: Get tasks without blocking dependencies
            - Hierarchical view in read_todos
            - 'blocked' status for tasks with incomplete dependencies

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

    Example (with subtasks enabled):
        ```python
        from pydantic_ai_todo import create_todo_toolset

        toolset = create_todo_toolset(enable_subtasks=True)
        # Now includes add_subtask, set_dependency, get_available_tasks tools
        ```
    """
    # Use async storage if provided, otherwise fall back to sync storage
    if async_storage is not None:
        return _create_async_toolset(async_storage, id=id, enable_subtasks=enable_subtasks)
    else:
        return _create_sync_toolset(storage, id=id, enable_subtasks=enable_subtasks)


def _create_sync_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    id: str | None = None,
    enable_subtasks: bool = False,
) -> FunctionToolset[Any]:
    """Create toolset with sync storage (backwards compatible)."""
    _storage = storage if storage is not None else TodoStorage()

    toolset: FunctionToolset[Any] = FunctionToolset(id=id)

    def _get_status_icon(status: str, enable_subtasks: bool = False) -> str:
        """Get the icon for a todo status."""
        icons = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }
        if enable_subtasks:
            icons["blocked"] = "[!]"
        return icons.get(status, "[ ]")

    def _get_todo_by_id(todo_id: str) -> Todo | None:
        """Find a todo by its ID."""
        for todo in _storage.todos:
            if todo.id == todo_id:
                return todo
        return None

    def _has_cycle(todo_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        visited: set[str] = set()

        def visit(current_id: str) -> bool:
            if current_id == todo_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)
            todo = _get_todo_by_id(current_id)
            if todo:
                for dep_id in todo.depends_on:
                    if visit(dep_id):
                        return True
            return False

        return visit(depends_on_id)

    def _is_blocked(todo: Todo) -> bool:
        """Check if a todo is blocked by incomplete dependencies."""
        for dep_id in todo.depends_on:
            dep = _get_todo_by_id(dep_id)
            if dep and dep.status != "completed":
                return True
        return False

    def _format_hierarchical(todos: list[Todo]) -> str:
        """Format todos as a hierarchical tree."""
        # Build parent->children map
        children_map: dict[str | None, list[Todo]] = {None: []}
        for todo in todos:
            parent = todo.parent_id
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(todo)

        lines = ["Current todos (hierarchical view):"]

        def render_tree(parent_id: str | None, depth: int, counter: list[int]) -> None:
            for todo in children_map.get(parent_id, []):
                counter[0] += 1
                indent = "  " * depth
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{indent}{counter[0]}. {status_icon} [{todo.id}] {todo.content}")
                if todo.depends_on:
                    lines.append(f"{indent}   depends on: {', '.join(todo.depends_on)}")
                if todo.id in children_map:
                    render_tree(todo.id, depth + 1, counter)

        counter = [0]
        render_tree(None, 0, counter)

        return "\n".join(lines)

    if enable_subtasks:
        read_description = READ_TODO_DESCRIPTION + "\nSet hierarchical=True to view as tree."

        @toolset.tool(description=read_description)
        async def read_todos(hierarchical: bool = False) -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list.

            Args:
                hierarchical: If True, display todos as a tree with subtasks indented.
            """
            if not _storage.todos:
                return "No todos in the list. Use write_todos to create tasks."

            if hierarchical:
                result = _format_hierarchical(_storage.todos)
            else:
                lines = ["Current todos:"]
                for i, todo in enumerate(_storage.todos, 1):
                    status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                    lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")
                    if todo.parent_id:
                        lines.append(f"   (subtask of: {todo.parent_id})")
                    if todo.depends_on:
                        lines.append(f"   (depends on: {', '.join(todo.depends_on)})")
                result = "\n".join(lines)

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
            for todo in _storage.todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            summary_parts = [f"{counts['completed']} completed"]
            if counts["blocked"] > 0:
                summary_parts.append(f"{counts['blocked']} blocked")
            summary_parts.append(f"{counts['in_progress']} in progress")
            summary_parts.append(f"{counts['pending']} pending")

            return result + f"\n\nSummary: {', '.join(summary_parts)}"
    else:

        @toolset.tool(description=READ_TODO_DESCRIPTION)
        async def read_todos() -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list."""
            if not _storage.todos:
                return "No todos in the list. Use write_todos to create tasks."

            lines = ["Current todos:"]
            for i, todo in enumerate(_storage.todos, 1):
                status_icon = _get_status_icon(todo.status)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
            for todo in _storage.todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

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
            todo_kwargs: dict[str, Any] = {
                "content": t.content,
                "status": t.status,
                "active_form": t.active_form,
            }
            if t.id is not None:
                todo_kwargs["id"] = t.id
            if enable_subtasks:
                todo_kwargs["parent_id"] = t.parent_id
                todo_kwargs["depends_on"] = t.depends_on
            new_todos.append(Todo(**todo_kwargs))
        _storage.todos = new_todos

        # Count by status
        counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
        if enable_subtasks:
            counts["blocked"] = 0
        for todo in _storage.todos:
            counts[todo.status] = counts.get(todo.status, 0) + 1

        summary_parts = [f"{counts['completed']} completed"]
        if enable_subtasks and counts.get("blocked", 0) > 0:
            summary_parts.append(f"{counts['blocked']} blocked")
        summary_parts.append(f"{counts['in_progress']} in progress")
        summary_parts.append(f"{counts['pending']} pending")

        return f"Updated {len(todos)} todos: {', '.join(summary_parts)}"

    @toolset.tool(description=ADD_TODO_DESCRIPTION)
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form of the content, e.g. "Fix bug" → "Fixing bug".

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
            status: New status (pending, in_progress, completed, or blocked if subtasks enabled).

        Returns:
            Confirmation message or error if not found.
        """
        valid_statuses = {"pending", "in_progress", "completed"}
        if enable_subtasks:
            valid_statuses.add("blocked")
        if status not in valid_statuses:
            return f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"

        for todo in _storage.todos:
            if todo.id == todo_id:
                # Check if trying to start a blocked task
                if enable_subtasks and status == "in_progress" and _is_blocked(todo):
                    return f"Cannot start '{todo.content}' - it has incomplete dependencies"
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

    # Add subtask-related tools only when enabled
    if enable_subtasks:

        @toolset.tool(description=ADD_SUBTASK_DESCRIPTION)
        async def add_subtask(parent_id: str, content: str, active_form: str) -> str:
            """Add a subtask to an existing todo.

            Args:
                parent_id: The ID of the parent todo.
                content: The task description in imperative form.
                active_form: Present continuous form of the content, e.g. "Create endpoint" → "Creating endpoint".

            Returns:
                Confirmation message with the new subtask's ID or error.
            """
            parent = _get_todo_by_id(parent_id)
            if not parent:
                return f"Parent todo with ID '{parent_id}' not found"

            new_todo = Todo(
                content=content,
                status="pending",
                active_form=active_form,
                parent_id=parent_id,
            )
            _storage.todos = [*_storage.todos, new_todo]
            return f"Added subtask '{content}' with ID: {new_todo.id} (parent: {parent_id})"

        @toolset.tool(description=SET_DEPENDENCY_DESCRIPTION)
        async def set_dependency(todo_id: str, depends_on_id: str) -> str:
            """Set a dependency between two todos.

            Args:
                todo_id: The ID of the todo that depends on another.
                depends_on_id: The ID of the todo that must be completed first.

            Returns:
                Confirmation message or error if validation fails.
            """
            todo = _get_todo_by_id(todo_id)
            if not todo:
                return f"Todo with ID '{todo_id}' not found"

            dependency = _get_todo_by_id(depends_on_id)
            if not dependency:
                return f"Dependency todo with ID '{depends_on_id}' not found"

            if todo_id == depends_on_id:
                return "A todo cannot depend on itself"

            if _has_cycle(todo_id, depends_on_id):
                return "Cannot add dependency: would create a cycle"

            if depends_on_id in todo.depends_on:
                return "Dependency already exists"

            todo.depends_on = [*todo.depends_on, depends_on_id]

            # Auto-block if dependency is not completed
            if dependency.status != "completed" and todo.status not in ("completed", "blocked"):
                todo.status = "blocked"
                return (
                    f"Added dependency: '{todo.content}' now depends on '{dependency.content}'. "
                    f"Task automatically blocked."
                )

            return f"Added dependency: '{todo.content}' now depends on '{dependency.content}'"

        @toolset.tool(description=GET_AVAILABLE_TASKS_DESCRIPTION)
        async def get_available_tasks() -> str:
            """Get all tasks that can be worked on now.

            Returns:
                List of tasks without incomplete dependencies.
            """
            available: list[Todo] = []
            for todo in _storage.todos:
                if todo.status == "completed":
                    continue
                if todo.status == "blocked":
                    continue
                if not _is_blocked(todo):
                    available.append(todo)

            if not available:
                return "No available tasks. All tasks are either completed or blocked."

            lines: list[str] = ["Available tasks (no blocking dependencies):"]
            for i, todo in enumerate(available, 1):
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            return "\n".join(lines)

    return toolset


def _create_async_toolset(
    storage: AsyncTodoStorageProtocol,
    *,
    id: str | None = None,
    enable_subtasks: bool = False,
) -> FunctionToolset[Any]:
    """Create toolset with async storage for true persistence."""
    toolset: FunctionToolset[Any] = FunctionToolset(id=id)

    def _get_status_icon(status: str, enable_subtasks: bool = False) -> str:
        """Get the icon for a todo status."""
        icons = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }
        if enable_subtasks:
            icons["blocked"] = "[!]"
        return icons.get(status, "[ ]")

    async def _get_todo_by_id(todo_id: str) -> Todo | None:
        """Find a todo by its ID."""
        return await storage.get_todo(todo_id)

    async def _has_cycle(todo_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        todos = await storage.get_todos()
        todos_map = {t.id: t for t in todos}
        visited: set[str] = set()

        def visit(current_id: str) -> bool:
            if current_id == todo_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)
            todo = todos_map.get(current_id)
            if todo:
                for dep_id in todo.depends_on:
                    if visit(dep_id):
                        return True
            return False

        return visit(depends_on_id)

    async def _is_blocked(todo: Todo) -> bool:
        """Check if a todo is blocked by incomplete dependencies."""
        for dep_id in todo.depends_on:
            dep = await _get_todo_by_id(dep_id)
            if dep and dep.status != "completed":
                return True
        return False

    def _format_hierarchical(todos: list[Todo]) -> str:
        """Format todos as a hierarchical tree."""
        children_map: dict[str | None, list[Todo]] = {None: []}
        for todo in todos:
            parent = todo.parent_id
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(todo)

        lines = ["Current todos (hierarchical view):"]

        def render_tree(parent_id: str | None, depth: int, counter: list[int]) -> None:
            for todo in children_map.get(parent_id, []):
                counter[0] += 1
                indent = "  " * depth
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{indent}{counter[0]}. {status_icon} [{todo.id}] {todo.content}")
                if todo.depends_on:
                    lines.append(f"{indent}   depends on: {', '.join(todo.depends_on)}")
                if todo.id in children_map:
                    render_tree(todo.id, depth + 1, counter)

        counter = [0]
        render_tree(None, 0, counter)

        return "\n".join(lines)

    if enable_subtasks:
        read_description = READ_TODO_DESCRIPTION + "\nSet hierarchical=True to view as tree."

        @toolset.tool(description=read_description)
        async def read_todos(hierarchical: bool = False) -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list.

            Args:
                hierarchical: If True, display todos as a tree with subtasks indented.
            """
            todos = await storage.get_todos()
            if not todos:
                return "No todos in the list. Use write_todos to create tasks."

            if hierarchical:
                result = _format_hierarchical(todos)
            else:
                lines = ["Current todos:"]
                for i, todo in enumerate(todos, 1):
                    status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                    lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")
                    if todo.parent_id:
                        lines.append(f"   (subtask of: {todo.parent_id})")
                    if todo.depends_on:
                        lines.append(f"   (depends on: {', '.join(todo.depends_on)})")
                result = "\n".join(lines)

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
            for todo in todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            summary_parts = [f"{counts['completed']} completed"]
            if counts["blocked"] > 0:
                summary_parts.append(f"{counts['blocked']} blocked")
            summary_parts.append(f"{counts['in_progress']} in progress")
            summary_parts.append(f"{counts['pending']} pending")

            return result + f"\n\nSummary: {', '.join(summary_parts)}"
    else:

        @toolset.tool(description=READ_TODO_DESCRIPTION)
        async def read_todos() -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list."""
            todos = await storage.get_todos()
            if not todos:
                return "No todos in the list. Use write_todos to create tasks."

            lines = ["Current todos:"]
            for i, todo in enumerate(todos, 1):
                status_icon = _get_status_icon(todo.status)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
            for todo in todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

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
            todo_kwargs: dict[str, Any] = {
                "content": t.content,
                "status": t.status,
                "active_form": t.active_form,
            }
            if t.id is not None:
                todo_kwargs["id"] = t.id
            if enable_subtasks:
                todo_kwargs["parent_id"] = t.parent_id
                todo_kwargs["depends_on"] = t.depends_on
            new_todos.append(Todo(**todo_kwargs))
        await storage.set_todos(new_todos)

        # Count by status
        counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
        if enable_subtasks:
            counts["blocked"] = 0
        for todo in new_todos:
            counts[todo.status] = counts.get(todo.status, 0) + 1

        summary_parts = [f"{counts['completed']} completed"]
        if enable_subtasks and counts.get("blocked", 0) > 0:
            summary_parts.append(f"{counts['blocked']} blocked")
        summary_parts.append(f"{counts['in_progress']} in progress")
        summary_parts.append(f"{counts['pending']} pending")

        return f"Updated {len(todos)} todos: {', '.join(summary_parts)}"

    @toolset.tool(description=ADD_TODO_DESCRIPTION)
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form of the content, e.g. "Fix bug" → "Fixing bug".

        Returns:
            Confirmation message with the new todo's ID.
        """
        new_todo = Todo(content=content, status="pending", active_form=active_form)
        await storage.add_todo(new_todo)
        return f"Added todo '{content}' with ID: {new_todo.id}"

    @toolset.tool(description=UPDATE_TODO_STATUS_DESCRIPTION)
    async def update_todo_status(
        todo_id: str, status: Literal["pending", "in_progress", "completed", "blocked"]
    ) -> str:
        """Update the status of an existing todo.

        Args:
            todo_id: The ID of the todo to update.
            status: New status (pending, in_progress, completed, or blocked if subtasks enabled).

        Returns:
            Confirmation message or error if not found.
        """
        valid_statuses: set[str] = {"pending", "in_progress", "completed"}
        if enable_subtasks:
            valid_statuses.add("blocked")
        if status not in valid_statuses:
            return f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"

        # Check if trying to start a blocked task
        if enable_subtasks and status == "in_progress":
            todo = await _get_todo_by_id(todo_id)
            if todo and await _is_blocked(todo):
                return f"Cannot start '{todo.content}' - it has incomplete dependencies"

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

    # Add subtask-related tools only when enabled
    if enable_subtasks:

        @toolset.tool(description=ADD_SUBTASK_DESCRIPTION)
        async def add_subtask(parent_id: str, content: str, active_form: str) -> str:
            """Add a subtask to an existing todo.

            Args:
                parent_id: The ID of the parent todo.
                content: The task description in imperative form.
                active_form: Present continuous form of the content, e.g. "Create endpoint" → "Creating endpoint".

            Returns:
                Confirmation message with the new subtask's ID or error.
            """
            parent = await _get_todo_by_id(parent_id)
            if not parent:
                return f"Parent todo with ID '{parent_id}' not found"

            new_todo = Todo(
                content=content,
                status="pending",
                active_form=active_form,
                parent_id=parent_id,
            )
            await storage.add_todo(new_todo)
            return f"Added subtask '{content}' with ID: {new_todo.id} (parent: {parent_id})"

        @toolset.tool(description=SET_DEPENDENCY_DESCRIPTION)
        async def set_dependency(todo_id: str, depends_on_id: str) -> str:
            """Set a dependency between two todos.

            Args:
                todo_id: The ID of the todo that depends on another.
                depends_on_id: The ID of the todo that must be completed first.

            Returns:
                Confirmation message or error if validation fails.
            """
            todo = await _get_todo_by_id(todo_id)
            if not todo:
                return f"Todo with ID '{todo_id}' not found"

            dependency = await _get_todo_by_id(depends_on_id)
            if not dependency:
                return f"Dependency todo with ID '{depends_on_id}' not found"

            if todo_id == depends_on_id:
                return "A todo cannot depend on itself"

            if await _has_cycle(todo_id, depends_on_id):
                return "Cannot add dependency: would create a cycle"

            if depends_on_id in todo.depends_on:
                return "Dependency already exists"

            new_depends_on = [*todo.depends_on, depends_on_id]

            # Auto-block if dependency is not completed
            original_status = todo.status
            new_status = todo.status
            if dependency.status != "completed" and todo.status not in ("completed", "blocked"):
                new_status = "blocked"  # type: ignore[assignment]

            await storage.update_todo(todo_id, depends_on=new_depends_on, status=new_status)

            if new_status == "blocked" and original_status != "blocked":
                return (
                    f"Added dependency: '{todo.content}' now depends on '{dependency.content}'. "
                    f"Task automatically blocked."
                )

            return f"Added dependency: '{todo.content}' now depends on '{dependency.content}'"

        @toolset.tool(description=GET_AVAILABLE_TASKS_DESCRIPTION)
        async def get_available_tasks() -> str:
            """Get all tasks that can be worked on now.

            Returns:
                List of tasks without incomplete dependencies.
            """
            todos = await storage.get_todos()
            available: list[Todo] = []
            for todo in todos:
                if todo.status == "completed":
                    continue
                if todo.status == "blocked":
                    continue
                if not await _is_blocked(todo):
                    available.append(todo)

            if not available:
                return "No available tasks. All tasks are either completed or blocked."

            lines: list[str] = ["Available tasks (no blocking dependencies):"]
            for i, todo in enumerate(available, 1):
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            return "\n".join(lines)

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
            "blocked": "[!]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} [{todo.id}] {todo.content}")

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
            "blocked": "[!]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} [{todo.id}] {todo.content}")

    return "\n".join(lines)
