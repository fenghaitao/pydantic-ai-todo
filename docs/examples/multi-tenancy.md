# Multi-Tenancy

Isolating todo lists per user in web applications using `session_id`.

## How session_id Works

[`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage] scopes every database
operation to a `session_id`. Two storage instances with different session IDs share the
same table but see completely separate data.

```python
from pydantic_ai_todo import AsyncPostgresStorage

# Alice and Bob share a database but have isolated todo lists
storage_alice = AsyncPostgresStorage(
    connection_string="postgresql://user:pass@localhost/mydb",
    session_id="user-alice",
)
storage_bob = AsyncPostgresStorage(
    connection_string="postgresql://user:pass@localhost/mydb",
    session_id="user-bob",
)

# Alice's tasks are invisible to Bob and vice versa
```

The underlying SQL adds a `WHERE session_id = $1` clause to every query, and the
database index on `session_id` keeps lookups fast.

## FastAPI: Per-User Todo Lists

A complete example showing per-user isolation in a FastAPI web app.

```python
import asyncpg
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic_ai import Agent
from pydantic_ai_todo import AsyncPostgresStorage, create_todo_toolset

app = FastAPI()
pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(
        "postgresql://user:pass@localhost/mydb",
        min_size=5,
        max_size=20,
    )
    # Ensure table exists (only needs to run once)
    storage = AsyncPostgresStorage(pool=pool, session_id="__setup__")
    await storage.initialize()


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


async def get_user_id(x_user_id: str = Header(...)) -> str:
    """Extract user ID from request header."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


async def get_storage(user_id: str = Depends(get_user_id)) -> AsyncPostgresStorage:
    """Create a storage instance scoped to the current user."""
    assert pool is not None
    storage = AsyncPostgresStorage(pool=pool, session_id=user_id)
    await storage.initialize()
    return storage


@app.post("/plan")
async def create_plan(prompt: str, storage: AsyncPostgresStorage = Depends(get_storage)):
    """Create a task plan for the current user."""
    toolset = create_todo_toolset(async_storage=storage)
    agent = Agent("openai:gpt-4o", toolsets=[toolset])

    result = await agent.run(prompt)
    todos = await storage.get_todos()

    return {
        "response": result.output,
        "tasks": [t.model_dump() for t in todos],
    }


@app.get("/todos")
async def list_todos(storage: AsyncPostgresStorage = Depends(get_storage)):
    """List all todos for the current user."""
    todos = await storage.get_todos()
    return {"tasks": [t.model_dump() for t in todos]}


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str, storage: AsyncPostgresStorage = Depends(get_storage)):
    """Delete a specific todo for the current user."""
    deleted = await storage.remove_todo(todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"deleted": True}
```

### Testing It

```bash
# Alice creates tasks
curl -X POST "http://localhost:8000/plan" \
  -H "X-User-Id: alice" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Plan a marketing campaign"}'

# Bob creates tasks
curl -X POST "http://localhost:8000/plan" \
  -H "X-User-Id: bob" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Plan the Q2 sprint"}'

# Alice only sees her own tasks
curl "http://localhost:8000/todos" -H "X-User-Id: alice"

# Bob only sees his own tasks
curl "http://localhost:8000/todos" -H "X-User-Id: bob"
```

## Using session_id with Events

Combine multi-tenancy with event notifications:

```python
from pydantic_ai_todo import AsyncPostgresStorage, TodoEventEmitter

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify_user(event):
    # The event contains the todo, which was scoped to a session.
    # You can look up the user from the session_id in your app logic.
    await send_push_notification(
        message=f"Task completed: {event.todo.content}",
    )

storage = AsyncPostgresStorage(
    pool=pool,
    session_id="user-alice",
    event_emitter=emitter,
)
await storage.initialize()
```

## Session ID Strategies

| Strategy | session_id Value | Use Case |
|----------|-----------------|----------|
| User ID | `"user-alice"` | Per-user todo lists |
| Conversation ID | `"conv-abc123"` | Per-chat-session tasks |
| Project ID | `"proj-backend"` | Shared project task boards |
| Composite | `"user-alice:proj-backend"` | User-scoped project tasks |

```python
# Per-user
storage = create_storage("postgres", ..., session_id=f"user-{user.id}")

# Per-conversation
storage = create_storage("postgres", ..., session_id=f"conv-{conversation_id}")

# Composite (user + project)
storage = create_storage("postgres", ..., session_id=f"{user.id}:{project.id}")
```

## Connection Pool Best Practices

In production, always share a single connection pool across all storage instances:

```python
import asyncpg

# Create ONE pool at startup
pool = await asyncpg.create_pool(
    "postgresql://user:pass@localhost/mydb",
    min_size=5,
    max_size=20,
)

# Create per-request storage instances using the shared pool
storage_a = AsyncPostgresStorage(pool=pool, session_id="user-alice")
storage_b = AsyncPostgresStorage(pool=pool, session_id="user-bob")

# The pool manages connections efficiently.
# Individual storage instances do NOT close the pool.
await storage_a.close()  # No-op (pool is external)
await storage_b.close()  # No-op (pool is external)

# Close the pool only at shutdown
await pool.close()
```

!!! warning
    Do **not** create a new pool per request. Use a shared pool and create
    lightweight `AsyncPostgresStorage` instances as needed.
