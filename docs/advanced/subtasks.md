# Task Hierarchy (Subtasks & Dependencies)

Enable complex task management with parent-child relationships and dependencies.

## Enabling Subtasks

Subtask tools are opt-in:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()

# Without subtasks (default)
toolset = create_todo_toolset(async_storage=storage)

# With subtasks enabled
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Break down the API implementation into subtasks")
```

## Additional Tools

When `enable_subtasks=True`, these tools are added:

| Tool | Description |
|------|-------------|
| `add_subtask` | Create a child task under a parent |
| `set_dependency` | Link tasks with dependency relationship |
| `get_available_tasks` | List tasks ready to work on |

## Todo Model Extensions

With subtasks enabled, todos have additional fields:

```python
class Todo(BaseModel):
    id: str                    # Auto-generated 8-char hex
    content: str               # Task description
    status: Literal["pending", "in_progress", "completed", "blocked"]
    active_form: str           # Present continuous form
    parent_id: str | None      # Parent task ID (for subtasks)
    depends_on: list[str]      # List of dependency task IDs
```

## Creating Subtasks

### Via Tool (Agent)

The agent can use `add_subtask`:

```
Agent: I'll break this down into subtasks.
[calls add_subtask(parent_id="abc12345", content="Design database schema", active_form="Designing schema")]
```

### Via Storage (Programmatic)

```python
from pydantic_ai_todo import Todo, AsyncMemoryStorage

storage = AsyncMemoryStorage()

parent = Todo(content="Build API", status="pending", active_form="Building API")
await storage.add_todo(parent)

child = Todo(
    content="Design schema",
    status="pending",
    active_form="Designing schema",
    parent_id=parent.id
)
await storage.add_todo(child)
```

## Dependencies

### Setting Dependencies

```python
# Via tool (agent)
# set_dependency(todo_id="task2", depends_on_id="task1")

# Task 2 now depends on Task 1
# Task 2 is automatically blocked if Task 1 is not completed
```

### Automatic Blocking

When you set a dependency on an incomplete task:
- The dependent task's status becomes `"blocked"`
- The task shows as blocked in `read_todos`

```python
# Task 1: pending
# Task 2: depends on Task 1 -> automatically blocked
```

### Cycle Detection

Circular dependencies are prevented:

```
Task A depends on Task B
Task B depends on Task C
Task C depends on Task A  # ERROR: Would create cycle
```

Diamond-shaped dependencies are allowed:

```
     Task A
    /      \
Task B    Task C
    \      /
     Task D
```

## Hierarchical View

`read_todos` supports hierarchical display:

```python
# Flat view (default)
todos = await read_todos()
# 1. [ ] [abc123] Build API
# 2. [ ] [def456] Design schema
# 3. [ ] [ghi789] Implement endpoints

# Hierarchical view
todos = await read_todos(hierarchical=True)
# 1. [ ] [abc123] Build API
#    1.1. [ ] [def456] Design schema
#    1.2. [ ] [ghi789] Implement endpoints
```

## Available Tasks

Get tasks that can be worked on immediately:

```python
# Returns only tasks where:
# - status is "pending" or "in_progress"
# - all dependencies are completed
available = await get_available_tasks()
```

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task not started |
| `in_progress` | Task being worked on |
| `completed` | Task finished |
| `blocked` | Task has incomplete dependencies |

## Practical Example

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])

# Agent creates tasks with hierarchy
result = await agent.run("Build a REST API with user authentication. Break it down into subtasks with proper dependencies.")

# Agent might create:
# 1. [ ] Build REST API
#    1.1. [ ] Design database schema
#    1.2. [blocked] Implement models (depends on 1.1)
#    1.3. [blocked] Create endpoints (depends on 1.2)
# 2. [ ] Add authentication
#    2.1. [ ] Choose auth method
#    2.2. [blocked] Implement auth (depends on 2.1, 1.3)

# Check what's available to work on
todos = await storage.get_todos()
available = [t for t in todos if t.status in ("pending", "in_progress")]
# - Design database schema
# - Choose auth method
```

## Best Practices

1. **Use subtasks for breakdown** - Let the agent break complex tasks into subtasks
2. **Set dependencies explicitly** - Don't assume order from list position
3. **Check available tasks** - Use `get_available_tasks` to find what can be done next
4. **Handle blocked status** - Tasks automatically unblock when dependencies complete
