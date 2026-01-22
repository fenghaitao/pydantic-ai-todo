# Event System

React to task changes with sync or async callbacks.

## Overview

The event system allows you to:
- Get notified when tasks are created, updated, or deleted
- Integrate with external systems (Slack, email, webhooks)
- Build reactive UIs
- Implement audit logging

## Event Types

```python
from pydantic_ai_todo import TodoEventType

TodoEventType.CREATED        # New task created
TodoEventType.UPDATED        # Task modified (any field)
TodoEventType.STATUS_CHANGED # Task status changed
TodoEventType.DELETED        # Task removed
TodoEventType.COMPLETED      # Task marked as completed
```

## TodoEvent Model

```python
from pydantic_ai_todo import TodoEvent

# Event properties
event.event_type      # TodoEventType
event.todo            # The affected Todo
event.timestamp       # datetime (UTC)
event.previous_state  # Todo | None (for updates)
```

## Basic Usage

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage, create_todo_toolset

emitter = TodoEventEmitter()

# Register callback with decorator
@emitter.on_created
async def handle_created(event):
    print(f"New task: {event.todo.content}")

@emitter.on_completed
async def handle_completed(event):
    print(f"Completed: {event.todo.content}")

# Attach to storage
storage = AsyncMemoryStorage(event_emitter=emitter)
toolset = create_todo_toolset(async_storage=storage)

# Use with agent
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Create a task and mark it complete")
# Events fire automatically as agent manipulates tasks
```

## Callback Registration

### Decorator Syntax

```python
@emitter.on_created
async def on_created(event): ...

@emitter.on_updated
async def on_updated(event): ...

@emitter.on_status_changed
async def on_status_changed(event): ...

@emitter.on_deleted
async def on_deleted(event): ...

@emitter.on_completed
async def on_completed(event): ...
```

### Method Syntax

```python
def my_callback(event):
    print(event.todo.content)

emitter.on(TodoEventType.CREATED, my_callback)
```

### Unregistering Callbacks

```python
emitter.off(TodoEventType.CREATED, my_callback)
```

## Sync and Async Callbacks

Both sync and async callbacks are supported:

```python
# Sync callback
@emitter.on_created
def sync_callback(event):
    print(f"Created: {event.todo.content}")

# Async callback
@emitter.on_created
async def async_callback(event):
    await send_notification(event.todo)
```

## Event Details

### CREATED

Emitted when `add_todo()` is called.

```python
@emitter.on_created
def on_created(event):
    print(f"New task: {event.todo.id}")
    print(f"Content: {event.todo.content}")
    # event.previous_state is None
```

### UPDATED

Emitted on any field change via `update_todo()`.

```python
@emitter.on_updated
def on_updated(event):
    print(f"Updated: {event.todo.id}")
    if event.previous_state:
        print(f"Old content: {event.previous_state.content}")
        print(f"New content: {event.todo.content}")
```

### STATUS_CHANGED

Emitted when status changes (also triggers UPDATED).

```python
@emitter.on_status_changed
def on_status_changed(event):
    old = event.previous_state.status if event.previous_state else None
    new = event.todo.status
    print(f"Status: {old} -> {new}")
```

### COMPLETED

Emitted when status becomes "completed" (also triggers STATUS_CHANGED and UPDATED).

```python
@emitter.on_completed
async def on_completed(event):
    await send_celebration_email(event.todo)
```

### DELETED

Emitted when `remove_todo()` is called.

```python
@emitter.on_deleted
def on_deleted(event):
    print(f"Deleted: {event.todo.id}")
    # event.todo contains the deleted task data
```

## Event Order

When completing a task, events fire in this order:
1. `UPDATED`
2. `STATUS_CHANGED`
3. `COMPLETED`

## Integration with Storage

### AsyncMemoryStorage

```python
emitter = TodoEventEmitter()
storage = AsyncMemoryStorage(event_emitter=emitter)
```

### AsyncPostgresStorage

```python
emitter = TodoEventEmitter()
storage = AsyncPostgresStorage(
    connection_string="postgresql://...",
    session_id="user-123",
    event_emitter=emitter
)
```

### Factory Function

```python
storage = create_storage(
    "postgres",
    connection_string="postgresql://...",
    session_id="user-123",
    event_emitter=emitter
)
```

## Practical Examples

### Slack Notification

```python
@emitter.on_completed
async def notify_slack(event):
    await slack.post_message(
        channel="#tasks",
        text=f"Task completed: {event.todo.content}"
    )
```

### Audit Logging

```python
@emitter.on_updated
async def audit_log(event):
    await db.insert("audit_log", {
        "event": event.event_type.value,
        "todo_id": event.todo.id,
        "timestamp": event.timestamp,
        "previous": event.previous_state.model_dump() if event.previous_state else None,
        "current": event.todo.model_dump()
    })
```

### Real-time Updates

```python
@emitter.on_created
@emitter.on_updated
@emitter.on_deleted
async def broadcast_update(event):
    await websocket.broadcast({
        "type": event.event_type.value,
        "todo": event.todo.model_dump()
    })
```

## Manual Event Emission

For custom scenarios:

```python
from pydantic_ai_todo import TodoEvent, TodoEventType, Todo

event = TodoEvent(
    event_type=TodoEventType.CREATED,
    todo=Todo(content="Test", status="pending", active_form="Testing")
)

await emitter.emit(event)
```
