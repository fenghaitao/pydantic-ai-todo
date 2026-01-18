"""Tests for pydantic_ai_todo.storage module."""

from pydantic_ai_todo import (
    AsyncMemoryStorage,
    Todo,
    TodoStorage,
    TodoStorageProtocol,
    create_storage,
)


class TestTodoStorage:
    """Tests for TodoStorage."""

    def test_default_empty(self) -> None:
        """Test that storage is empty by default."""
        storage = TodoStorage()
        assert storage.todos == []

    def test_set_and_get_todos(self) -> None:
        """Test setting and getting todos."""
        storage = TodoStorage()
        todos = [
            Todo(content="Task 1", status="pending", active_form="Working on Task 1"),
            Todo(content="Task 2", status="completed", active_form="Working on Task 2"),
        ]
        storage.todos = todos
        assert storage.todos == todos
        assert len(storage.todos) == 2

    def test_overwrite_todos(self) -> None:
        """Test that setting todos overwrites previous list."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Task 1", status="pending", active_form="Working"),
        ]
        storage.todos = [
            Todo(content="Task 2", status="completed", active_form="Working"),
        ]
        assert len(storage.todos) == 1
        assert storage.todos[0].content == "Task 2"

    def test_clear_todos(self) -> None:
        """Test clearing todos by setting empty list."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Task", status="pending", active_form="Working"),
        ]
        storage.todos = []
        assert storage.todos == []


class TestTodoStorageProtocol:
    """Tests for TodoStorageProtocol."""

    def test_todo_storage_implements_protocol(self) -> None:
        """Test that TodoStorage implements TodoStorageProtocol."""
        storage = TodoStorage()
        assert isinstance(storage, TodoStorageProtocol)

    def test_custom_storage_can_implement_protocol(self) -> None:
        """Test that custom storage can implement the protocol."""

        class CustomStorage:
            def __init__(self) -> None:
                self._data: list[Todo] = []

            @property
            def todos(self) -> list[Todo]:
                return self._data

            @todos.setter
            def todos(self, value: list[Todo]) -> None:
                self._data = value

        storage = CustomStorage()
        assert isinstance(storage, TodoStorageProtocol)

        # Test it works
        storage.todos = [
            Todo(content="Test", status="pending", active_form="Testing"),
        ]
        assert len(storage.todos) == 1


class TestAsyncMemoryStorage:
    """Tests for AsyncMemoryStorage."""

    async def test_default_empty(self) -> None:
        """Test that storage is empty by default."""
        storage = AsyncMemoryStorage()
        todos = await storage.get_todos()
        assert todos == []

    async def test_set_and_get_todos(self) -> None:
        """Test setting and getting todos."""
        storage = AsyncMemoryStorage()
        todos = [
            Todo(content="Task 1", status="pending", active_form="Working on Task 1"),
            Todo(content="Task 2", status="completed", active_form="Working on Task 2"),
        ]
        await storage.set_todos(todos)
        result = await storage.get_todos()
        assert len(result) == 2
        assert result[0].content == "Task 1"
        assert result[1].content == "Task 2"

    async def test_get_todo_by_id(self) -> None:
        """Test getting a single todo by ID."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        result = await storage.get_todo("test123")
        assert result is not None
        assert result.id == "test123"
        assert result.content == "Task"

    async def test_get_todo_not_found(self) -> None:
        """Test getting a non-existent todo returns None."""
        storage = AsyncMemoryStorage()
        result = await storage.get_todo("nonexistent")
        assert result is None

    async def test_get_todo_from_multiple(self) -> None:
        """Test getting a todo that's not first in the list."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(id="id1", content="Task 1", status="pending", active_form="W1"))
        await storage.add_todo(Todo(id="id2", content="Task 2", status="pending", active_form="W2"))
        await storage.add_todo(Todo(id="id3", content="Task 3", status="pending", active_form="W3"))

        result = await storage.get_todo("id3")
        assert result is not None
        assert result.id == "id3"
        assert result.content == "Task 3"

    async def test_add_todo(self) -> None:
        """Test adding a todo."""
        storage = AsyncMemoryStorage()
        todo = Todo(content="New task", status="pending", active_form="Working")
        result = await storage.add_todo(todo)

        assert result.content == "New task"
        todos = await storage.get_todos()
        assert len(todos) == 1

    async def test_update_todo_status(self) -> None:
        """Test updating a todo's status."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        result = await storage.update_todo("test123", status="completed")
        assert result is not None
        assert result.status == "completed"

        # Verify persisted
        fetched = await storage.get_todo("test123")
        assert fetched is not None
        assert fetched.status == "completed"

    async def test_update_todo_content(self) -> None:
        """Test updating a todo's content."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Old content", status="pending", active_form="Working")
        await storage.add_todo(todo)

        result = await storage.update_todo("test123", content="New content")
        assert result is not None
        assert result.content == "New content"

    async def test_update_todo_active_form(self) -> None:
        """Test updating a todo's active_form."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Task", status="pending", active_form="Old form")
        await storage.add_todo(todo)

        result = await storage.update_todo("test123", active_form="New form")
        assert result is not None
        assert result.active_form == "New form"

    async def test_update_todo_not_found(self) -> None:
        """Test updating a non-existent todo returns None."""
        storage = AsyncMemoryStorage()
        result = await storage.update_todo("nonexistent", status="completed")
        assert result is None

    async def test_update_todo_no_changes(self) -> None:
        """Test updating a todo with no fields specified."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        # Update with no changes
        result = await storage.update_todo("test123")
        assert result is not None
        assert result.content == "Task"
        assert result.status == "pending"
        assert result.active_form == "Working"

    async def test_update_todo_multiple_fields(self) -> None:
        """Test updating multiple fields at once."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Old", status="pending", active_form="Old form")
        await storage.add_todo(todo)

        result = await storage.update_todo(
            "test123",
            content="New",
            status="completed",
            active_form="New form",
        )
        assert result is not None
        assert result.content == "New"
        assert result.status == "completed"
        assert result.active_form == "New form"

    async def test_update_todo_from_multiple(self) -> None:
        """Test updating a todo that's not first in the list."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(id="id1", content="Task 1", status="pending", active_form="W1"))
        await storage.add_todo(Todo(id="id2", content="Task 2", status="pending", active_form="W2"))
        await storage.add_todo(Todo(id="id3", content="Task 3", status="pending", active_form="W3"))

        result = await storage.update_todo("id3", status="completed")
        assert result is not None
        assert result.status == "completed"

        # Verify other todos unchanged
        todo1 = await storage.get_todo("id1")
        assert todo1 is not None
        assert todo1.status == "pending"

    async def test_remove_todo(self) -> None:
        """Test removing a todo."""
        storage = AsyncMemoryStorage()
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        result = await storage.remove_todo("test123")
        assert result is True

        todos = await storage.get_todos()
        assert len(todos) == 0

    async def test_remove_todo_not_found(self) -> None:
        """Test removing a non-existent todo returns False."""
        storage = AsyncMemoryStorage()
        result = await storage.remove_todo("nonexistent")
        assert result is False

    async def test_remove_todo_from_multiple(self) -> None:
        """Test removing a todo that's not first in the list."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(id="id1", content="Task 1", status="pending", active_form="W1"))
        await storage.add_todo(Todo(id="id2", content="Task 2", status="pending", active_form="W2"))
        await storage.add_todo(Todo(id="id3", content="Task 3", status="pending", active_form="W3"))

        result = await storage.remove_todo("id3")
        assert result is True

        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[0].id == "id1"
        assert todos[1].id == "id2"

    async def test_get_todos_returns_copy(self) -> None:
        """Test that get_todos returns a copy, not the original list."""
        storage = AsyncMemoryStorage()
        todo = Todo(content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        todos1 = await storage.get_todos()
        todos2 = await storage.get_todos()

        # Should be different list objects
        assert todos1 is not todos2


class TestCreateStorage:
    """Tests for create_storage factory function."""

    def test_create_memory_storage(self) -> None:
        """Test creating memory storage."""
        storage = create_storage("memory")
        assert isinstance(storage, AsyncMemoryStorage)

    def test_create_storage_default_is_memory(self) -> None:
        """Test that default backend is memory."""
        storage = create_storage()
        assert isinstance(storage, AsyncMemoryStorage)
