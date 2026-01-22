# Subtasks Example

Building a project plan with hierarchical tasks and dependencies.

## Enable Subtasks

```python
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(
    async_storage=storage,
    enable_subtasks=True,  # Enables add_subtask, set_dependency, get_available_tasks
)
```

## Complete Example

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

async def main():
    storage = AsyncMemoryStorage()
    toolset = create_todo_toolset(
        async_storage=storage,
        enable_subtasks=True,
    )
    
    agent = Agent(
        "openai:gpt-4o",
        toolsets=[toolset],
        system_prompt="""You are a project planner.

When planning projects:
1. Create main tasks with add_todo
2. Break them into subtasks with add_subtask
3. Set dependencies where tasks must wait for others
4. Use get_available_tasks to see what can start now
""",
    )
    
    result = await agent.run("""
    Plan building a REST API with:
    - Database design (must be done first)
    - User model (needs database)
    - Auth system (needs user model)
    - API endpoints (needs auth)
    """)
    
    print("Plan:")
    print(result.output)
    print()
    
    # Show hierarchy
    todos = await storage.get_todos()
    
    # Find root tasks (no parent)
    roots = [t for t in todos if t.parent_id is None]
    
    def print_tree(todo, indent=0):
        status_map = {
            "pending": "○",
            "in_progress": "◐",
            "completed": "●",
            "blocked": "⊘",
        }
        icon = status_map.get(todo.status, "?")
        deps = f" (depends on: {', '.join(todo.depends_on)})" if todo.depends_on else ""
        print(f"{'  ' * indent}{icon} [{todo.id}] {todo.content}{deps}")
        
        # Find children
        children = [t for t in todos if t.parent_id == todo.id]
        for child in children:
            print_tree(child, indent + 1)
    
    print("Task hierarchy:")
    for root in roots:
        print_tree(root)

asyncio.run(main())
```

## Expected Output

```
Plan:
I've created a plan with proper dependencies...

Task hierarchy:
○ [a1b2c3d4] Build REST API
  ○ [e5f6g7h8] Design database schema
  ⊘ [i9j0k1l2] Implement user model (depends on: e5f6g7h8)
  ⊘ [m3n4o5p6] Build auth system (depends on: i9j0k1l2)
  ⊘ [q7r8s9t0] Create API endpoints (depends on: m3n4o5p6)
```

## Working Through the Plan

```python
async def work_through_plan():
    storage = AsyncMemoryStorage()
    toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)
    agent = Agent("openai:gpt-4o", toolsets=[toolset])
    
    # Create the plan
    await agent.run("Create a plan for building a blog with database, models, and API")
    
    # Work through available tasks
    while True:
        todos = await storage.get_todos()
        available = [t for t in todos if t.status == "pending"]
        
        if not available:
            print("All tasks completed or blocked!")
            break
        
        # Complete first available task
        task = available[0]
        print(f"Completing: {task.content}")
        await storage.update_todo(task.id, status="completed")
        
        # Check what's now available
        todos = await storage.get_todos()
        newly_available = [t for t in todos if t.status == "pending"]
        print(f"  → {len(newly_available)} tasks now available")
```

## Dependency Patterns

### Sequential

```
Task A → Task B → Task C
```

```python
# Create tasks
a = await storage.add_todo(Todo(content="Task A", ...))
b = await storage.add_todo(Todo(content="Task B", ...))
c = await storage.add_todo(Todo(content="Task C", ...))

# Set dependencies via agent tool
# set_dependency(todo_id=b.id, depends_on_id=a.id)
# set_dependency(todo_id=c.id, depends_on_id=b.id)
```

### Parallel then Merge

```
     Task A
    /      \
Task B    Task C
    \      /
     Task D
```

```python
# D depends on both B and C
# set_dependency(todo_id=d.id, depends_on_id=b.id)
# set_dependency(todo_id=d.id, depends_on_id=c.id)
```

### Cycle Prevention

The library automatically prevents cycles:

```python
# This would fail:
# A depends on B
# B depends on C
# C depends on A  ← ERROR: Would create cycle
```
