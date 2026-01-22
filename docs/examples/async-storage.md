# Async Storage

Using async storage backends for full async operations.

## Why Async Storage?

- **Full async support** — All operations are non-blocking
- **CRUD operations** — Get, add, update, remove individual todos
- **Event integration** — Works with TodoEventEmitter
- **Preparation for persistence** — Same interface as PostgreSQL

## Basic Example

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

async def main():
    # Create async storage
    storage = AsyncMemoryStorage()
    toolset = create_todo_toolset(async_storage=storage)
    
    agent = Agent(
        "openai:gpt-4o",
        toolsets=[toolset],
    )
    
    result = await agent.run("Create a project plan for a mobile app")
    
    # Async access to todos
    todos = await storage.get_todos()
    for todo in todos:
        print(f"[{todo.status}] {todo.content}")

asyncio.run(main())
```

## CRUD Operations

```python
from pydantic_ai_todo import AsyncMemoryStorage, Todo

storage = AsyncMemoryStorage()

# Create
todo = await storage.add_todo(
    Todo(content="New task", status="pending", active_form="Working on task")
)
print(f"Created: {todo.id}")

# Read all
todos = await storage.get_todos()

# Read one
todo = await storage.get_todo("abc12345")

# Update
updated = await storage.update_todo(
    "abc12345",
    status="completed",
    content="Updated content",
)

# Delete
deleted = await storage.remove_todo("abc12345")

# Replace all
await storage.set_todos([])
```

## With Event Emitter

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import (
    create_todo_toolset,
    AsyncMemoryStorage,
    TodoEventEmitter,
)

async def main():
    # Set up event handling
    emitter = TodoEventEmitter()
    
    @emitter.on_created
    async def on_created(event):
        print(f"Created: {event.todo.content}")
    
    @emitter.on_completed
    async def on_completed(event):
        print(f"Completed: {event.todo.content}")
    
    # Create storage with emitter
    storage = AsyncMemoryStorage(event_emitter=emitter)
    toolset = create_todo_toolset(async_storage=storage)
    
    agent = Agent("openai:gpt-4o", toolsets=[toolset])
    
    # Events fire as agent works
    await agent.run("Create two tasks and complete one")

asyncio.run(main())
```

## Programmatic Task Management

```python
import asyncio
from pydantic_ai_todo import AsyncMemoryStorage, Todo

async def main():
    storage = AsyncMemoryStorage()
    
    # Pre-populate tasks
    tasks = [
        Todo(content="Review PR #123", status="pending", active_form="Reviewing PR"),
        Todo(content="Fix bug #456", status="in_progress", active_form="Fixing bug"),
        Todo(content="Deploy v2.0", status="pending", active_form="Deploying"),
    ]
    
    for task in tasks:
        await storage.add_todo(task)
    
    # Find in-progress tasks
    all_todos = await storage.get_todos()
    in_progress = [t for t in all_todos if t.status == "in_progress"]
    
    print("In progress:")
    for todo in in_progress:
        print(f"  - {todo.content}")
    
    # Complete them
    for todo in in_progress:
        await storage.update_todo(todo.id, status="completed")
    
    # Verify
    all_todos = await storage.get_todos()
    completed = [t for t in all_todos if t.status == "completed"]
    print(f"\nCompleted {len(completed)} tasks")

asyncio.run(main())
```

## Sync vs Async Comparison

### Sync (TodoStorage)

```python
storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# Direct property access
todos = storage.todos
storage.todos = []
```

### Async (AsyncMemoryStorage)

```python
storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# Async method calls
todos = await storage.get_todos()
await storage.set_todos([])
await storage.add_todo(todo)
await storage.update_todo(id, status="completed")
await storage.remove_todo(id)
```

## Next Steps

- [PostgreSQL](postgres.md) — Persistent async storage
- [Events](events.md) — React to task changes
