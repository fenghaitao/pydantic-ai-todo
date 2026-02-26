# Toolset API

## create_todo_toolset

::: pydantic_ai_todo.create_todo_toolset
    options:
      show_root_heading: true
      show_source: true

---

## get_todo_system_prompt

::: pydantic_ai_todo.get_todo_system_prompt
    options:
      show_root_heading: true
      show_source: true

---

## get_todo_system_prompt_async

::: pydantic_ai_todo.get_todo_system_prompt_async
    options:
      show_root_heading: true
      show_source: true

---

## Usage Examples

### Basic Toolset

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

toolset = create_todo_toolset()
agent = Agent("openai:gpt-4o", toolsets=[toolset])
```

### With Storage Access

```python
from pydantic_ai_todo import create_todo_toolset, TodoStorage

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# After agent runs
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

### With Subtasks

```python
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(
    async_storage=storage,
    enable_subtasks=True,
)
```

### With Custom Tool Descriptions

Override default tool descriptions to steer LLM behavior for your use case:

```python
from pydantic_ai_todo import create_todo_toolset

toolset = create_todo_toolset(
    descriptions={
        "write_todos": "Plan and organize complex multi-step tasks only",
        "read_todos": "Check current task list and progress",
    }
)
```

Any tool name not present in the dict keeps its default description.
Available tool names: `read_todos`, `write_todos`, `add_todo`,
`update_todo_status`, `remove_todo`, `add_subtask`, `set_dependency`,
`get_available_tasks`.

### System Prompt Generation

```python
from pydantic_ai_todo import get_todo_system_prompt, TodoStorage

storage = TodoStorage()
# ... populate storage

prompt = get_todo_system_prompt(storage)
# Returns formatted prompt with current todos
```
