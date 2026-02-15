# Examples

Practical examples showing how to use Todo Toolset in different scenarios.

## Getting Started

- [Basic Usage](basic-usage.md) — Your first todo-enabled agent
- [Async Storage](async-storage.md) — Using async storage backends

## Storage

- [PostgreSQL](postgres.md) — Persistent multi-tenant storage
- [Multi-Tenancy](multi-tenancy.md) — Per-user isolation in web apps
- [Migration Guide](migration-guide.md) — Moving from memory to PostgreSQL

## Features

- [Subtasks](subtasks.md) — Hierarchical task management
- [Events](events.md) — Reacting to task changes

## Quick Reference

### Minimal Setup

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

agent = Agent("openai:gpt-4o", toolsets=[create_todo_toolset()])
result = await agent.run("Create a project plan")
```

### With Storage Access

```python
from pydantic_ai_todo import create_todo_toolset, TodoStorage

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)
agent = Agent("openai:gpt-4o", toolsets=[toolset])

result = await agent.run("Plan the API implementation")

for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

### With PostgreSQL

```python
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",
)
await storage.initialize()

toolset = create_todo_toolset(async_storage=storage)
agent = Agent("openai:gpt-4o", toolsets=[toolset])
```

### With Events

```python
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify(event):
    print(f"Done: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
toolset = create_todo_toolset(async_storage=storage)
```
