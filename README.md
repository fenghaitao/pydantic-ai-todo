# pydantic-ai-todo

> **Looking for a complete agent framework?** Check out [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) - a full-featured deep agent framework with planning, subagents, and skills system built on pydantic-ai.

[![PyPI version](https://img.shields.io/pypi/v/pydantic-ai-todo.svg)](https://pypi.org/project/pydantic-ai-todo/)
[![CI](https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml/badge.svg)](https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/vstorm-co/pydantic-ai-todo)
[![Python](https://img.shields.io/pypi/pyversions/pydantic-ai-todo.svg)](https://pypi.org/project/pydantic-ai-todo/)
[![License](https://img.shields.io/github/license/vstorm-co/pydantic-ai-todo)](https://github.com/vstorm-co/pydantic-ai-todo/blob/main/LICENSE)

Todo/task planning toolset for [pydantic-ai](https://ai.pydantic.dev/) agents.

**This library was extracted from [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents)** to provide standalone task planning for any pydantic-ai agent without requiring the full framework.

## Features

- **Task Management** - `read_todos`, `write_todos`, `add_todo`, `update_todo_status`, `remove_todo`
- **Unique IDs** - Auto-generated 8-char hex IDs for each task
- **Task Hierarchy** - Optional subtasks and dependencies with cycle detection
- **Multiple Storage Backends** - In-memory, async, and PostgreSQL
- **Event System** - React to task changes with sync/async callbacks
- **100% Test Coverage** - Production-ready with strict type checking

## Installation

```bash
pip install pydantic-ai-todo
```

Or with uv:

```bash
uv add pydantic-ai-todo
```

## Quick Start

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

# Create an agent with todo capabilities
agent = Agent(
    "openai:gpt-4.1",
    toolsets=[create_todo_toolset()],
)

# Run the agent
result = await agent.run("Create a todo list for building a website")
```

## Usage with Storage Access

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, TodoStorage

# Create storage and toolset
storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Plan the implementation of a REST API")

# Access todos directly
for todo in storage.todos:
    print(f"[{todo.status}] [{todo.id}] {todo.content}")
```

## Async Storage

For async operations and future persistence support:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Plan a feature implementation")

# After agent runs - access todos via async methods
todos = await storage.get_todos()
todo = await storage.get_todo("abc12345")
await storage.update_todo("abc12345", status="completed")
```

## PostgreSQL Storage

For persistent storage with PostgreSQL:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset

# Create storage with connection string
storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123"  # Multi-tenancy support
)
await storage.initialize()  # Creates table if not exists

toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Plan the project milestones")

# Todos are now persisted in PostgreSQL
# Clean up when done
await storage.close()
```

See [Storage Documentation](docs/storage.md) for more details.

## Task Hierarchy (Subtasks & Dependencies)

Enable subtask support for complex task management:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Break down the API implementation into subtasks with dependencies")
```

This adds tools for:
- `add_subtask` - Create child tasks
- `set_dependency` - Link tasks (with cycle detection)
- `get_available_tasks` - List tasks ready to work on
- Hierarchical view in `read_todos`

See [Subtasks Documentation](docs/subtasks.md) for more details.

## Event System

React to task changes:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify_completed(event):
    print(f"Task completed: {event.todo.content}")

@emitter.on_created
async def notify_created(event):
    print(f"Task created: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Create and complete a simple task")
# Events will fire as agent creates/completes tasks
```

See [Events Documentation](docs/events.md) for more details.

## API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `create_todo_toolset(storage?, async_storage?, enable_subtasks?)` | Create toolset with todo tools |
| `get_todo_system_prompt(storage?)` | Generate system prompt with current todos |
| `get_todo_system_prompt_async(storage?)` | Async version of system prompt generator |
| `create_storage(backend, **options)` | Factory for storage backends |

### Models

| Model | Description |
|-------|-------------|
| `Todo` | Task model with id, content, status, active_form, parent_id, depends_on |
| `TodoItem` | Input model for write_todos with Field descriptions for LLM |
| `TodoEvent` | Event data with event_type, todo, timestamp, previous_state |
| `TodoEventType` | Enum: CREATED, UPDATED, STATUS_CHANGED, DELETED, COMPLETED |

### Storage Classes

| Class | Description |
|-------|-------------|
| `TodoStorage` | Simple sync in-memory storage |
| `AsyncMemoryStorage` | Async in-memory storage with CRUD methods |
| `AsyncPostgresStorage` | PostgreSQL storage with session-based multi-tenancy |
| `TodoEventEmitter` | Event emitter for task change notifications |

### Tools (registered with toolset)

| Tool | Description |
|------|-------------|
| `read_todos` | List all tasks (supports hierarchical view) |
| `write_todos` | Bulk write/update tasks |
| `add_todo` | Add single task |
| `update_todo_status` | Update task status by ID |
| `remove_todo` | Delete task by ID |
| `add_subtask`* | Create child task |
| `set_dependency`* | Link tasks with dependency |
| `get_available_tasks`* | List tasks ready to work on |

*Only available when `enable_subtasks=True`

## Documentation

- [Storage Backends](docs/storage.md) - In-memory, async, PostgreSQL
- [Event System](docs/events.md) - Callbacks and event handling
- [Task Hierarchy](docs/subtasks.md) - Subtasks and dependencies

## Related Projects

- **[pydantic-ai](https://github.com/pydantic/pydantic-ai)** - The foundation: Agent framework by Pydantic
- **[pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents)** - Full agent framework (uses this library)
- **[pydantic-ai-backend](https://github.com/vstorm-co/pydantic-ai-backend)** - File storage and sandbox backends
- **[fastapi-fullstack](https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template)** - Full-stack AI app template

## License

[MIT](LICENSE)
