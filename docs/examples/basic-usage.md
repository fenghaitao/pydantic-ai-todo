# Basic Usage

A complete example of creating your first todo-enabled agent.

## The Simplest Agent

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

async def main():
    # Create agent with todo tools
    agent = Agent(
        "openai:gpt-4o",
        toolsets=[create_todo_toolset()],
    )
    
    # Ask it to plan something
    result = await agent.run(
        "Create a todo list for building a REST API with user authentication"
    )
    
    print(result.output)

asyncio.run(main())
```

## Accessing Tasks After Run

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, TodoStorage

async def main():
    # Create storage we can access
    storage = TodoStorage()
    toolset = create_todo_toolset(storage=storage)
    
    agent = Agent(
        "openai:gpt-4o",
        toolsets=[toolset],
        system_prompt="""You are a project planner.
        
When asked to plan something:
1. Break it down into specific tasks
2. Use add_todo to create each task
3. Summarize the plan
""",
    )
    
    result = await agent.run("Plan the implementation of a blog application")
    
    # Print the plan
    print("Agent's response:")
    print(result.output)
    print()
    
    # Access tasks directly
    print("Tasks created:")
    for todo in storage.todos:
        status_icon = "✓" if todo.status == "completed" else "○"
        print(f"  {status_icon} [{todo.id}] {todo.content}")

asyncio.run(main())
```

## Task Progress Tracking

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, TodoStorage

async def main():
    storage = TodoStorage()
    toolset = create_todo_toolset(storage=storage)
    
    agent = Agent(
        "openai:gpt-4o",
        toolsets=[toolset],
        system_prompt="""You are a task executor.

When given tasks:
1. Read current todos with read_todos
2. Work on pending tasks
3. Mark them complete with update_todo_status
4. Report what you did
""",
    )
    
    # First run: create tasks
    result1 = await agent.run("Create 3 simple coding tasks")
    print("Created tasks:")
    for todo in storage.todos:
        print(f"  [{todo.status}] {todo.content}")
    
    # Second run: complete tasks
    result2 = await agent.run(
        "Complete all the tasks you created",
        message_history=result1.all_messages(),
    )
    print("\nAfter completion:")
    for todo in storage.todos:
        print(f"  [{todo.status}] {todo.content}")

asyncio.run(main())
```

## With Custom System Prompt

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, get_todo_system_prompt, TodoStorage

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# Generate system prompt with current todos
base_prompt = """You are a development assistant.

Help the user with coding tasks. Track your work using the todo tools.
"""

dynamic_prompt = get_todo_system_prompt(storage)

agent = Agent(
    "openai:gpt-4o",
    toolsets=[toolset],
    system_prompt=base_prompt + "\n\n" + dynamic_prompt,
)
```

## Output Example

```
Agent's response:
I've created a plan for the blog application. Here are the tasks:

1. Set up project structure
2. Design database schema
3. Implement user model
4. Create post model
5. Build authentication
6. Implement CRUD for posts
7. Add frontend templates
8. Write tests

Tasks created:
  ○ [a1b2c3d4] Set up project structure
  ○ [e5f6g7h8] Design database schema
  ○ [i9j0k1l2] Implement user model
  ○ [m3n4o5p6] Create post model
  ○ [q7r8s9t0] Build authentication
  ○ [u1v2w3x4] Implement CRUD for posts
  ○ [y5z6a7b8] Add frontend templates
  ○ [c9d0e1f2] Write tests
```

## Next Steps

- [Async Storage](async-storage.md) — Use async storage backends
- [PostgreSQL](postgres.md) — Persistent storage
- [Subtasks](subtasks.md) — Hierarchical tasks
