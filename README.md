<h1 align="center">Todo Toolset for Pydantic AI</h1>

<p align="center">
  <em>Task Planning and Tracking for AI Agents</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/pydantic-ai-todo/"><img src="https://img.shields.io/pypi/v/pydantic-ai-todo.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/pydantic/pydantic-ai"><img src="https://img.shields.io/badge/Powered%20by-Pydantic%20AI-E92063?logo=pydantic&logoColor=white" alt="Pydantic AI"></a>
</p>

<p align="center">
  <b>Subtasks & Dependencies</b> — hierarchical task management
  &nbsp;&bull;&nbsp;
  <b>PostgreSQL Storage</b> — persistent multi-tenant tasks
  &nbsp;&bull;&nbsp;
  <b>Event System</b> — webhooks and callbacks
</p>

---

**Todo Toolset for Pydantic AI** adds task planning capabilities to any [Pydantic AI](https://ai.pydantic.dev/) agent. Your agent can create, track, and complete tasks with full support for subtasks, dependencies, and persistent storage.

> **Full framework?** Check out [Pydantic Deep Agents](https://github.com/vstorm-co/pydantic-deepagents) — complete agent framework with planning, filesystem, subagents, and skills.

## Use Cases

| What You Want to Build | How Todo Toolset Helps |
|------------------------|------------------------|
| **AI Coding Assistant** | Break down complex features into trackable tasks |
| **Project Manager Bot** | Create hierarchical task structures with dependencies |
| **Research Agent** | Track investigation progress across multiple topics |
| **Workflow Automation** | React to task completion with webhooks and callbacks |
| **Multi-User App** | Session-based PostgreSQL storage for each user |

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

agent = Agent(
    "openai:gpt-4o",
    toolsets=[create_todo_toolset()],
)

result = await agent.run("Create a todo list for building a REST API")
```

**That's it.** Your agent can now:

- ✅ **Create tasks** — `add_todo`, `write_todos`
- ✅ **Track progress** — `read_todos`, `update_todo_status`
- ✅ **Manage hierarchy** — subtasks and dependencies
- ✅ **Persist state** — PostgreSQL multi-tenant storage

## Available Tools

| Tool | Description |
|------|-------------|
| `read_todos` | List all tasks (supports hierarchical view) |
| `write_todos` | Bulk write/update tasks |
| `add_todo` | Add a single task |
| `update_todo_status` | Update task status by ID |
| `remove_todo` | Delete task by ID |
| `add_subtask`* | Create child task |
| `set_dependency`* | Link tasks with dependency |
| `get_available_tasks`* | List tasks ready to work on |

*Available when `enable_subtasks=True`

## Storage Backends

### In-Memory (Default)

```python
from pydantic_ai_todo import create_todo_toolset, TodoStorage

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# Access todos directly after agent runs
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

### Async Memory

```python
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# Async access
todos = await storage.get_todos()
```

### PostgreSQL

```python
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",  # Multi-tenancy
)
await storage.initialize()

toolset = create_todo_toolset(async_storage=storage)
```

## Task Hierarchy

Enable subtasks for complex task management:

```python
toolset = create_todo_toolset(
    async_storage=storage,
    enable_subtasks=True,
)

# Agent can now:
# - add_subtask(parent_id, content) — create child tasks
# - set_dependency(task_id, depends_on_id) — link tasks
# - get_available_tasks() — list tasks ready to work on
```

Dependencies include automatic cycle detection — no infinite loops possible.

## Event System

React to task changes:

```python
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify_completed(event):
    print(f"Task done: {event.todo.content}")
    # Send webhook, update UI, etc.

@emitter.on_created
async def notify_created(event):
    print(f"New task: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
toolset = create_todo_toolset(async_storage=storage)
```

## API Reference

### Factory Functions

| Function | Description |
|----------|-------------|
| `create_todo_toolset()` | Create toolset with todo tools |
| `create_storage(backend, **options)` | Factory for storage backends |
| `get_todo_system_prompt()` | Generate system prompt with current todos |

### Models

| Model | Description |
|-------|-------------|
| `Todo` | Task with id, content, status, parent_id, depends_on |
| `TodoItem` | Input model for write_todos |
| `TodoEvent` | Event data with type, todo, timestamp |
| `TodoEventType` | CREATED, UPDATED, STATUS_CHANGED, DELETED, COMPLETED |

### Storage Classes

| Class | Description |
|-------|-------------|
| `TodoStorage` | Sync in-memory storage |
| `AsyncMemoryStorage` | Async in-memory with CRUD |
| `AsyncPostgresStorage` | PostgreSQL with multi-tenancy |
| `TodoEventEmitter` | Event emitter for callbacks |

## Related Projects

| Package | Description |
|---------|-------------|
| [Pydantic Deep Agents](https://github.com/vstorm-co/pydantic-deepagents) | Full agent framework (uses this library) |
| [pydantic-ai-backend](https://github.com/vstorm-co/pydantic-ai-backend) | File storage and Docker sandbox |
| [subagents-pydantic-ai](https://github.com/vstorm-co/subagents-pydantic-ai) | Multi-agent orchestration |
| [summarization-pydantic-ai](https://github.com/vstorm-co/summarization-pydantic-ai) | Context management |
| [pydantic-ai](https://github.com/pydantic/pydantic-ai) | The foundation — agent framework by Pydantic |

## Contributing

```bash
git clone https://github.com/vstorm-co/pydantic-ai-todo.git
cd pydantic-ai-todo
make install
make test  # 100% coverage required
```

## License

MIT — see [LICENSE](LICENSE)

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/vstorm-co">vstorm-co</a></sub>
</p>
