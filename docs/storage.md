# Storage Backends

pydantic-ai-todo supports multiple storage backends for different use cases.

## Overview

| Backend | Class | Use Case |
|---------|-------|----------|
| Sync In-Memory | `TodoStorage` | Simple agents, testing |
| Async In-Memory | `AsyncMemoryStorage` | Async agents, no persistence |
| PostgreSQL | `AsyncPostgresStorage` | Production, persistence, multi-tenancy |

## Sync In-Memory Storage

The simplest storage option. Data is lost when the process ends.

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoStorage, create_todo_toolset

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Create a todo list for the project")

# After agent runs
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")

# Direct manipulation
storage.todos = []  # Clear all
```

### Custom Sync Storage

Implement `TodoStorageProtocol` for custom storage:

```python
from pydantic_ai_todo import TodoStorageProtocol, Todo

class RedisTodoStorage:
    def __init__(self, redis_client):
        self._redis = redis_client

    @property
    def todos(self) -> list[Todo]:
        data = self._redis.get("todos")
        return [Todo(**t) for t in json.loads(data)] if data else []

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        self._redis.set("todos", json.dumps([t.model_dump() for t in value]))
```

## Async In-Memory Storage

For async operations with full CRUD support.

```python
from pydantic_ai import Agent
from pydantic_ai_todo import AsyncMemoryStorage, Todo, create_todo_toolset

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Plan the sprint tasks")

# CRUD operations after agent runs
todos = await storage.get_todos()
todo = await storage.get_todo("abc12345")
await storage.add_todo(Todo(content="Task", status="pending", active_form="Working"))
await storage.update_todo("abc12345", status="completed")
await storage.remove_todo("abc12345")
await storage.set_todos([])  # Replace all
```

### AsyncTodoStorageProtocol

Interface for async storage backends:

```python
class AsyncTodoStorageProtocol(Protocol):
    async def get_todos(self) -> list[Todo]: ...
    async def set_todos(self, todos: list[Todo]) -> None: ...
    async def get_todo(self, id: str) -> Todo | None: ...
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def update_todo(self, id: str, **fields) -> Todo | None: ...
    async def remove_todo(self, id: str) -> bool: ...
```

## PostgreSQL Storage

Persistent storage with PostgreSQL and multi-tenancy support.

### Basic Usage

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/mydb",
    session_id="user-123"
)
await storage.initialize()  # Creates table if not exists

toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Create project milestones")

# Todos are persisted in PostgreSQL
# When done
await storage.close()
```

### With Existing Pool

```python
import asyncpg
from pydantic_ai import Agent
from pydantic_ai_todo import AsyncPostgresStorage, create_todo_toolset

pool = await asyncpg.create_pool("postgresql://user:pass@localhost/mydb")

storage = AsyncPostgresStorage(
    pool=pool,
    session_id="user-123"
)
await storage.initialize()

toolset = create_todo_toolset(async_storage=storage)
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Plan the deployment")

# Pool is NOT closed when storage.close() is called
# You manage the pool lifecycle
```

### Session-Based Multi-Tenancy

Each `session_id` isolates todos:

```python
# User A's todos
storage_a = create_storage("postgres", connection_string=url, session_id="user-a")
await storage_a.initialize()

# User B's todos (completely separate)
storage_b = create_storage("postgres", connection_string=url, session_id="user-b")
await storage_b.initialize()

# User A cannot see User B's todos
```

### Custom Table Name

```python
storage = AsyncPostgresStorage(
    connection_string="postgresql://...",
    session_id="user-123",
    table_name="my_custom_todos"  # Default: "todos"
)
```

### Database Schema

The table is auto-created with this schema:

```sql
CREATE TABLE IF NOT EXISTS todos (
    id VARCHAR(8) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    active_form TEXT NOT NULL,
    parent_id VARCHAR(8),
    depends_on TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_todos_session_id ON todos(session_id);
```

## Factory Function

Use `create_storage()` for consistent backend creation:

```python
from pydantic_ai_todo import create_storage

# Memory (default)
storage = create_storage("memory")

# PostgreSQL
storage = create_storage(
    "postgres",
    connection_string="postgresql://...",
    session_id="user-123",
    table_name="todos",  # optional
    event_emitter=emitter  # optional
)
```

## Event Integration

All async storage backends support event emitters:

```python
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_created
async def on_created(event):
    print(f"Created: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
# or
storage = create_storage("postgres", ..., event_emitter=emitter)
```

See [Event System](events.md) for more details.
