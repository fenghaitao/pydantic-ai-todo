# Toolset

The todo toolset provides task management tools for your Pydantic AI agent.

## Creating the Toolset

```python
from pydantic_ai_todo import create_todo_toolset

# Basic usage (in-memory storage)
toolset = create_todo_toolset()

# With custom storage
from pydantic_ai_todo import TodoStorage
storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# With async storage
from pydantic_ai_todo import AsyncMemoryStorage
storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# With subtasks enabled
toolset = create_todo_toolset(
    async_storage=storage,
    enable_subtasks=True,
)
```

## Available Tools

### Core Tools

| Tool | Description |
|------|-------------|
| `read_todos` | List all tasks with status and IDs |
| `write_todos` | Bulk write/replace tasks |
| `add_todo` | Add a single new task |
| `update_todo_status` | Update a task's status by ID |
| `remove_todo` | Delete a task by ID |

### Subtask Tools

When `enable_subtasks=True`:

| Tool | Description |
|------|-------------|
| `add_subtask` | Create a child task under a parent |
| `set_dependency` | Link two tasks with dependency |
| `get_available_tasks` | List tasks ready to work on |

## Tool Details

### read_todos

Lists all tasks in a formatted view.

```python
# Agent calls this internally
# Returns something like:
"""
Tasks:
- [pending] [abc12345] Set up project structure
- [in_progress] [def67890] Write documentation
- [completed] [ghi11111] Create README
"""
```

### write_todos

Bulk write tasks. Useful for initial planning.

```python
# The agent provides a list of TodoItem objects
# Each item has: content, status, active_form
```

### add_todo

Add a single task.

```python
# Agent provides: content, active_form (optional)
# Returns: task ID
```

### update_todo_status

Update a task's status.

```python
# Agent provides: task_id, new_status
# Statuses: "pending", "in_progress", "completed", "blocked"
```

### remove_todo

Delete a task by ID.

```python
# Agent provides: task_id
# Returns: success/failure message
```

## Adding to Your Agent

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

agent = Agent(
    "openai:gpt-4o",
    toolsets=[create_todo_toolset()],
    system_prompt="""You are a helpful assistant with task management.

Use the todo tools to:
- Break down complex requests into tasks
- Track progress on multi-step work
- Mark tasks complete as you finish them
""",
)
```

## Custom Tool Descriptions

The `descriptions` parameter lets you override default tool descriptions to better
guide LLM behavior for your specific use case. Pass a dict mapping tool names to
custom description strings:

```python
toolset = create_todo_toolset(
    descriptions={
        "write_todos": "Plan and organize complex multi-step tasks only",
        "read_todos": "Check current task list and progress",
    }
)
```

Any tool name not included in the dict keeps its default description. Available
tool names for the core tools: `read_todos`, `write_todos`, `add_todo`,
`update_todo_status`, `remove_todo`. When `enable_subtasks=True`, you can also
override: `add_subtask`, `set_dependency`, `get_available_tasks`.

## Factory Parameters

```python
def create_todo_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    async_storage: AsyncTodoStorageProtocol | None = None,
    id: str | None = None,
    enable_subtasks: bool = False,
    descriptions: dict[str, str] | None = None,
) -> FunctionToolset[Any]:
    """Create a todo toolset.

    Args:
        storage: Sync storage backend (e.g., TodoStorage)
        async_storage: Async storage backend (e.g., AsyncMemoryStorage)
        id: Optional toolset identifier
        enable_subtasks: Enable subtask and dependency tools
        descriptions: Optional dict mapping tool names to custom descriptions.
            Override any tool's description to steer LLM behavior.
            Tool names not present in the dict keep their defaults.

    Returns:
        A FunctionToolset with todo management tools
    """
```

## System Prompt Helper

Generate a system prompt with current todos:

```python
from pydantic_ai_todo import get_todo_system_prompt, TodoStorage

storage = TodoStorage()
storage.todos = [...]  # existing todos

prompt = get_todo_system_prompt(storage)
# Returns formatted prompt with current task list
```

Async version:

```python
from pydantic_ai_todo import get_todo_system_prompt_async

prompt = await get_todo_system_prompt_async(async_storage)
```
