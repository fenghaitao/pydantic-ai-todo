# Types API

## Todo

::: pydantic_ai_todo.Todo
    options:
      show_root_heading: true
      show_source: true

---

## TodoItem

::: pydantic_ai_todo.TodoItem
    options:
      show_root_heading: true
      show_source: true

---

## TodoEvent

::: pydantic_ai_todo.TodoEvent
    options:
      show_root_heading: true
      show_source: true

---

## TodoEventType

::: pydantic_ai_todo.TodoEventType
    options:
      show_root_heading: true
      show_source: true

---

## TodoEventEmitter

::: pydantic_ai_todo.TodoEventEmitter
    options:
      show_root_heading: true
      show_source: true

---

## Usage Examples

### Creating Todos

```python
from pydantic_ai_todo import Todo

todo = Todo(
    content="Implement authentication",
    status="pending",
    active_form="Implementing authentication",
)

# With subtask fields
todo = Todo(
    content="Design schema",
    status="pending",
    active_form="Designing schema",
    parent_id="abc12345",
    depends_on=["def67890"],
)
```

### Working with Events

```python
from pydantic_ai_todo import TodoEventEmitter, TodoEventType

emitter = TodoEventEmitter()

@emitter.on_created
async def handle_created(event):
    print(f"Type: {event.event_type}")  # TodoEventType.CREATED
    print(f"Todo: {event.todo.content}")
    print(f"Time: {event.timestamp}")

@emitter.on_status_changed
async def handle_status(event):
    old = event.previous_state.status if event.previous_state else None
    new = event.todo.status
    print(f"Status: {old} → {new}")
```

### Converting to Dict

```python
from pydantic_ai_todo import Todo

todo = Todo(content="Task", status="pending", active_form="Working")

# To dict
data = todo.model_dump()

# From dict
todo = Todo(**data)

# To JSON
json_str = todo.model_dump_json()
```
