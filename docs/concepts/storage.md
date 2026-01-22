# Storage Backends

pydantic-ai-todo supports multiple storage backends for different use cases.

## Overview

| Backend | Class | Persistence | Multi-Tenancy | Use Case |
|---------|-------|-------------|---------------|----------|
| Sync Memory | `TodoStorage` | No | No | Testing, simple agents |
| Async Memory | `AsyncMemoryStorage` | No | No | Async agents |
| PostgreSQL | `AsyncPostgresStorage` | Yes | Yes | Production apps |

## Sync In-Memory Storage

The simplest option. Data is lost when the process ends.

```python
from pydantic_ai_todo import TodoStorage, create_todo_toolset

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# After agent runs
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")

# Direct manipulation
storage.todos = []  # Clear all
```

### When to Use

- Testing
- Single-session agents
- Prototyping

## Async In-Memory Storage

For async operations with full CRUD support.

```python
from pydantic_ai_todo import AsyncMemoryStorage, create_todo_toolset

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# CRUD operations
todos = await storage.get_todos()
todo = await storage.get_todo("abc12345")
await storage.add_todo(Todo(content="Task", status="pending", active_form="Working"))
await storage.update_todo("abc12345", status="completed")
await storage.remove_todo("abc12345")
await storage.set_todos([])  # Replace all
```

### When to Use

- Async agents
- When you need CRUD operations
- Testing async code

## PostgreSQL Storage

Persistent storage with multi-tenancy support.

```python
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",
)
await storage.initialize()  # Creates table

toolset = create_todo_toolset(async_storage=storage)

# When done
await storage.close()
```

### Session-Based Multi-Tenancy

Each `session_id` isolates todos:

```python
# User A's todos
storage_a = create_storage("postgres", ..., session_id="user-a")

# User B's todos (completely separate)
storage_b = create_storage("postgres", ..., session_id="user-b")
```

### Database Schema

Auto-created table:

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

### When to Use

- Production applications
- Multi-user apps
- Persistent task storage

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
    event_emitter=emitter,  # optional
)
```

## Protocols

### TodoStorageProtocol

For sync storage:

```python
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> list[Todo]: ...
    
    @todos.setter
    def todos(self, value: list[Todo]) -> None: ...
```

### AsyncTodoStorageProtocol

For async storage:

```python
class AsyncTodoStorageProtocol(Protocol):
    async def get_todos(self) -> list[Todo]: ...
    async def set_todos(self, todos: list[Todo]) -> None: ...
    async def get_todo(self, id: str) -> Todo | None: ...
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def update_todo(self, id: str, **fields) -> Todo | None: ...
    async def remove_todo(self, id: str) -> bool: ...
```

## Custom Storage

Implement the protocol for custom backends:

```python
from pydantic_ai_todo import AsyncTodoStorageProtocol, Todo

class RedisStorage:
    """Redis-based storage."""
    
    def __init__(self, redis_client):
        self._redis = redis_client
    
    async def get_todos(self) -> list[Todo]:
        data = await self._redis.get("todos")
        return [Todo(**t) for t in json.loads(data)] if data else []
    
    async def set_todos(self, todos: list[Todo]) -> None:
        await self._redis.set("todos", json.dumps([t.model_dump() for t in todos]))
    
    # ... implement other methods
```
