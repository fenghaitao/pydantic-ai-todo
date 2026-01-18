"""Tests for pydantic_ai_todo.events module."""

from datetime import datetime, timezone

from pydantic_ai_todo import (
    AsyncMemoryStorage,
    Todo,
    TodoEvent,
    TodoEventEmitter,
    TodoEventType,
    create_storage,
)


class TestTodoEventType:
    """Tests for TodoEventType enum."""

    def test_event_type_values(self) -> None:
        """Test that all event types have correct values."""
        assert TodoEventType.CREATED.value == "created"
        assert TodoEventType.UPDATED.value == "updated"
        assert TodoEventType.STATUS_CHANGED.value == "status_changed"
        assert TodoEventType.DELETED.value == "deleted"
        assert TodoEventType.COMPLETED.value == "completed"

    def test_event_type_is_string(self) -> None:
        """Test that event types are strings."""
        assert isinstance(TodoEventType.CREATED, str)
        assert TodoEventType.CREATED == "created"


class TestTodoEvent:
    """Tests for TodoEvent model."""

    def test_create_event(self) -> None:
        """Test creating a basic event."""
        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)

        assert event.event_type == TodoEventType.CREATED
        assert event.todo == todo
        assert event.previous_state is None
        assert isinstance(event.timestamp, datetime)

    def test_event_with_previous_state(self) -> None:
        """Test creating an event with previous state."""
        old_todo = Todo(id="abc", content="Test", status="pending", active_form="Testing")
        new_todo = Todo(id="abc", content="Test", status="completed", active_form="Testing")

        event = TodoEvent(
            event_type=TodoEventType.STATUS_CHANGED,
            todo=new_todo,
            previous_state=old_todo,
        )

        assert event.previous_state is not None
        assert event.previous_state.status == "pending"
        assert event.todo.status == "completed"

    def test_event_timestamp_is_utc(self) -> None:
        """Test that event timestamp is in UTC."""
        before = datetime.now(timezone.utc)
        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        after = datetime.now(timezone.utc)

        assert event.timestamp.tzinfo is not None
        assert before <= event.timestamp <= after


class TestTodoEventEmitter:
    """Tests for TodoEventEmitter class."""

    def test_create_emitter(self) -> None:
        """Test creating an emitter."""
        emitter = TodoEventEmitter()
        assert emitter is not None

    def test_on_registers_callback(self) -> None:
        """Test that on() registers a callback."""
        emitter = TodoEventEmitter()
        called: list[TodoEvent] = []

        def callback(event: TodoEvent) -> None:
            called.append(event)

        emitter.on(TodoEventType.CREATED, callback)

        # Verify callback is registered (internal check)
        assert callback in emitter._listeners[TodoEventType.CREATED]  # pyright: ignore[reportPrivateUsage]  # pyright: ignore[reportPrivateUsage]

    def test_on_returns_callback(self) -> None:
        """Test that on() returns the callback for decorator usage."""
        emitter = TodoEventEmitter()

        def callback(event: TodoEvent) -> None:
            pass

        result = emitter.on(TodoEventType.CREATED, callback)
        assert result is callback

    def test_off_unregisters_callback(self) -> None:
        """Test that off() removes a callback."""
        emitter = TodoEventEmitter()

        def callback(event: TodoEvent) -> None:
            pass

        emitter.on(TodoEventType.CREATED, callback)
        result = emitter.off(TodoEventType.CREATED, callback)

        assert result is True
        assert callback not in emitter._listeners[TodoEventType.CREATED]  # pyright: ignore[reportPrivateUsage]

    def test_off_returns_false_if_not_found(self) -> None:
        """Test that off() returns False if callback not found."""
        emitter = TodoEventEmitter()

        def callback(event: TodoEvent) -> None:
            pass

        result = emitter.off(TodoEventType.CREATED, callback)
        assert result is False

    async def test_emit_calls_sync_callback(self) -> None:
        """Test that emit() calls synchronous callbacks."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        def callback(event: TodoEvent) -> None:
            events.append(event)

        emitter.on(TodoEventType.CREATED, callback)

        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        await emitter.emit(event)

        assert len(events) == 1
        assert events[0] == event

    async def test_emit_calls_async_callback(self) -> None:
        """Test that emit() calls asynchronous callbacks."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        async def callback(event: TodoEvent) -> None:
            events.append(event)

        emitter.on(TodoEventType.CREATED, callback)

        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        await emitter.emit(event)

        assert len(events) == 1
        assert events[0] == event

    async def test_emit_calls_multiple_callbacks(self) -> None:
        """Test that emit() calls all registered callbacks."""
        emitter = TodoEventEmitter()
        results: list[str] = []

        def callback1(event: TodoEvent) -> None:
            results.append("sync")

        async def callback2(event: TodoEvent) -> None:
            results.append("async")

        emitter.on(TodoEventType.CREATED, callback1)
        emitter.on(TodoEventType.CREATED, callback2)

        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        await emitter.emit(event)

        assert len(results) == 2
        assert "sync" in results
        assert "async" in results

    async def test_emit_only_calls_matching_event_type(self) -> None:
        """Test that emit() only calls callbacks for matching event type."""
        emitter = TodoEventEmitter()
        created_events: list[TodoEvent] = []
        deleted_events: list[TodoEvent] = []

        def on_created(event: TodoEvent) -> None:
            created_events.append(event)

        def on_deleted(event: TodoEvent) -> None:
            deleted_events.append(event)

        emitter.on(TodoEventType.CREATED, on_created)
        emitter.on(TodoEventType.DELETED, on_deleted)

        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        await emitter.emit(event)

        assert len(created_events) == 1
        assert len(deleted_events) == 0


class TestConvenienceHooks:
    """Tests for convenience hook methods."""

    def test_on_created_decorator(self) -> None:
        """Test on_created convenience method."""
        emitter = TodoEventEmitter()

        @emitter.on_created
        def callback(event: TodoEvent) -> None:
            pass

        assert callback in emitter._listeners[TodoEventType.CREATED]  # pyright: ignore[reportPrivateUsage]

    def test_on_completed_decorator(self) -> None:
        """Test on_completed convenience method."""
        emitter = TodoEventEmitter()

        @emitter.on_completed
        def callback(event: TodoEvent) -> None:
            pass

        assert callback in emitter._listeners[TodoEventType.COMPLETED]  # pyright: ignore[reportPrivateUsage]

    def test_on_status_changed_decorator(self) -> None:
        """Test on_status_changed convenience method."""
        emitter = TodoEventEmitter()

        @emitter.on_status_changed
        def callback(event: TodoEvent) -> None:
            pass

        assert callback in emitter._listeners[TodoEventType.STATUS_CHANGED]  # pyright: ignore[reportPrivateUsage]

    def test_on_updated_decorator(self) -> None:
        """Test on_updated convenience method."""
        emitter = TodoEventEmitter()

        @emitter.on_updated
        def callback(event: TodoEvent) -> None:
            pass

        assert callback in emitter._listeners[TodoEventType.UPDATED]  # pyright: ignore[reportPrivateUsage]

    def test_on_deleted_decorator(self) -> None:
        """Test on_deleted convenience method."""
        emitter = TodoEventEmitter()

        @emitter.on_deleted
        def callback(event: TodoEvent) -> None:
            pass

        assert callback in emitter._listeners[TodoEventType.DELETED]  # pyright: ignore[reportPrivateUsage]

    async def test_on_created_receives_events(self) -> None:
        """Test that on_created decorator works with emit."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_created
        async def callback(event: TodoEvent) -> None:
            events.append(event)

        todo = Todo(content="Test", status="pending", active_form="Testing")
        event = TodoEvent(event_type=TodoEventType.CREATED, todo=todo)
        await emitter.emit(event)

        assert len(events) == 1


class TestStorageEventIntegration:
    """Tests for event integration with AsyncMemoryStorage."""

    async def test_storage_with_event_emitter(self) -> None:
        """Test creating storage with event emitter."""
        emitter = TodoEventEmitter()
        storage = AsyncMemoryStorage(event_emitter=emitter)
        assert storage._event_emitter is emitter  # pyright: ignore[reportPrivateUsage]

    async def test_add_todo_emits_created_event(self) -> None:
        """Test that add_todo emits CREATED event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_created
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        assert len(events) == 1
        assert events[0].event_type == TodoEventType.CREATED
        assert events[0].todo == todo

    async def test_update_todo_emits_updated_event(self) -> None:
        """Test that update_todo emits UPDATED event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_updated
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(id="test1", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        await storage.update_todo("test1", content="Updated")

        assert len(events) == 1
        assert events[0].event_type == TodoEventType.UPDATED
        assert events[0].todo.content == "Updated"
        assert events[0].previous_state is not None
        assert events[0].previous_state.content == "Test"

    async def test_update_status_emits_status_changed_event(self) -> None:
        """Test that status change emits STATUS_CHANGED event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_status_changed
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(id="test1", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        await storage.update_todo("test1", status="in_progress")

        assert len(events) == 1
        assert events[0].event_type == TodoEventType.STATUS_CHANGED
        assert events[0].todo.status == "in_progress"
        assert events[0].previous_state is not None
        assert events[0].previous_state.status == "pending"

    async def test_complete_todo_emits_completed_event(self) -> None:
        """Test that completing a todo emits COMPLETED event."""
        emitter = TodoEventEmitter()
        completed_events: list[TodoEvent] = []
        status_events: list[TodoEvent] = []

        @emitter.on_completed
        def on_completed(event: TodoEvent) -> None:
            completed_events.append(event)

        @emitter.on_status_changed
        def on_status(event: TodoEvent) -> None:
            status_events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(id="test1", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        await storage.update_todo("test1", status="completed")

        assert len(completed_events) == 1
        assert completed_events[0].event_type == TodoEventType.COMPLETED
        assert len(status_events) == 1  # Also emits STATUS_CHANGED

    async def test_remove_todo_emits_deleted_event(self) -> None:
        """Test that remove_todo emits DELETED event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_deleted
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(id="test1", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        await storage.remove_todo("test1")

        assert len(events) == 1
        assert events[0].event_type == TodoEventType.DELETED
        assert events[0].todo.id == "test1"

    async def test_storage_without_emitter_works(self) -> None:
        """Test that storage works without event emitter."""
        storage = AsyncMemoryStorage()
        todo = Todo(content="Test", status="pending", active_form="Testing")

        # Should not raise
        await storage.add_todo(todo)
        await storage.update_todo(todo.id, status="completed")
        await storage.remove_todo(todo.id)

    async def test_update_non_existent_todo_no_event(self) -> None:
        """Test that updating non-existent todo doesn't emit event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_updated
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        await storage.update_todo("nonexistent", content="Test")

        assert len(events) == 0

    async def test_remove_non_existent_todo_no_event(self) -> None:
        """Test that removing non-existent todo doesn't emit event."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_deleted
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        await storage.remove_todo("nonexistent")

        assert len(events) == 0

    async def test_status_same_value_no_status_changed_event(self) -> None:
        """Test that setting same status doesn't emit STATUS_CHANGED."""
        emitter = TodoEventEmitter()
        status_events: list[TodoEvent] = []

        @emitter.on_status_changed
        def callback(event: TodoEvent) -> None:
            status_events.append(event)

        storage = AsyncMemoryStorage(event_emitter=emitter)
        todo = Todo(id="test1", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        # Update with same status
        await storage.update_todo("test1", status="pending")

        assert len(status_events) == 0


class TestCreateStorageWithEvents:
    """Tests for create_storage with event emitter."""

    def test_create_storage_with_emitter(self) -> None:
        """Test creating storage with event emitter via factory."""
        emitter = TodoEventEmitter()
        storage = create_storage("memory", event_emitter=emitter)

        assert isinstance(storage, AsyncMemoryStorage)
        assert storage._event_emitter is emitter  # pyright: ignore[reportPrivateUsage]

    async def test_factory_storage_emits_events(self) -> None:
        """Test that storage from factory emits events."""
        emitter = TodoEventEmitter()
        events: list[TodoEvent] = []

        @emitter.on_created
        def callback(event: TodoEvent) -> None:
            events.append(event)

        storage = create_storage("memory", event_emitter=emitter)
        todo = Todo(content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        assert len(events) == 1
