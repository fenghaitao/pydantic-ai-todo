# Core Concepts

Todo Toolset for Pydantic AI is built around three main concepts:

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Your Agent                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Todo Toolset                         │  │
│  │  read_todos │ write_todos │ add_todo │ ...       │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Storage Backend                      │  │
│  │  TodoStorage │ AsyncMemoryStorage │ PostgreSQL   │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Event System (optional)              │  │
│  │  on_created │ on_completed │ on_updated │ ...    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### [Toolset](toolset.md)

The toolset provides tools for task management:

- `create_todo_toolset()` — Factory function
- Tools: `read_todos`, `write_todos`, `add_todo`, etc.
- Optional subtask tools with `enable_subtasks=True`

### [Storage](storage.md)

Multiple storage backends for different needs:

- `TodoStorage` — Simple sync in-memory
- `AsyncMemoryStorage` — Async with CRUD operations
- `AsyncPostgresStorage` — Persistent with multi-tenancy

### [Types](types.md)

Pydantic models for type safety:

- `Todo` — The task model
- `TodoItem` — Input model for LLM
- `TodoEvent` — Event data model

## How It Works

1. **Create toolset** with your preferred storage
2. **Add to agent** via `toolsets=[...]`
3. **Agent uses tools** to manage tasks
4. **Events fire** (optional) when tasks change

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, TodoStorage

# 1. Create storage and toolset
storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# 2. Add to agent
agent = Agent("openai:gpt-4o", toolsets=[toolset])

# 3. Agent manages tasks
result = await agent.run("Plan the project")

# 4. Access tasks
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

## Next Steps

- [Toolset](toolset.md) — Learn about available tools
- [Storage](storage.md) — Choose the right backend
- [Types](types.md) — Understand the data models
