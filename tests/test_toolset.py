"""Tests for pydantic_ai_todo.toolset module."""

from typing import Any

import pytest
from pydantic_ai.toolsets import FunctionToolset

from pydantic_ai_todo import (
    AsyncMemoryStorage,
    Todo,
    TodoItem,
    TodoStorage,
    create_todo_toolset,
    get_todo_system_prompt,
    get_todo_system_prompt_async,
)


class TestCreateTodoToolset:
    """Tests for create_todo_toolset factory."""

    def test_returns_function_toolset(self) -> None:
        """Test that factory returns a FunctionToolset."""
        toolset = create_todo_toolset()
        assert isinstance(toolset, FunctionToolset)

    def test_toolset_has_read_todos_tool(self) -> None:
        """Test that toolset has read_todos tool."""
        toolset = create_todo_toolset()
        assert "read_todos" in toolset.tools

    def test_toolset_has_write_todos_tool(self) -> None:
        """Test that toolset has write_todos tool."""
        toolset = create_todo_toolset()
        assert "write_todos" in toolset.tools

    def test_toolset_has_add_todo_tool(self) -> None:
        """Test that toolset has add_todo tool."""
        toolset = create_todo_toolset()
        assert "add_todo" in toolset.tools

    def test_toolset_has_update_todo_status_tool(self) -> None:
        """Test that toolset has update_todo_status tool."""
        toolset = create_todo_toolset()
        assert "update_todo_status" in toolset.tools

    def test_toolset_has_remove_todo_tool(self) -> None:
        """Test that toolset has remove_todo tool."""
        toolset = create_todo_toolset()
        assert "remove_todo" in toolset.tools

    def test_toolset_with_custom_id(self) -> None:
        """Test creating toolset with custom ID."""
        toolset = create_todo_toolset(id="my-todos")
        assert toolset.id == "my-todos"

    def test_toolset_with_custom_storage(self) -> None:
        """Test creating toolset with custom storage."""
        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)
        assert toolset is not None

    def test_default_storage_isolation(self) -> None:
        """Test that each toolset has isolated storage by default."""
        toolset1 = create_todo_toolset()
        toolset2 = create_todo_toolset()
        # They should be different instances
        assert toolset1 is not toolset2


class TestReadTodos:
    """Tests for read_todos tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_read_empty_todos(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading when no todos exist."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function()  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_read_todos_with_items(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test reading todos with items."""
        storage.todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="Working on Task 1"),
            Todo(id="id2", content="Task 2", status="in_progress", active_form="Working on Task 2"),
            Todo(id="id3", content="Task 3", status="completed", active_form="Working on Task 3"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function()  # type: ignore[call-arg]

        assert "Task 1" in result
        assert "Task 2" in result
        assert "Task 3" in result
        assert "[ ]" in result  # pending icon
        assert "[*]" in result  # in_progress icon
        assert "[x]" in result  # completed icon
        # Verify IDs are shown
        assert "[id1]" in result
        assert "[id2]" in result
        assert "[id3]" in result

    async def test_read_todos_summary(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that read_todos includes summary."""
        storage.todos = [
            Todo(content="Task 1", status="pending", active_form="Working"),
            Todo(content="Task 2", status="pending", active_form="Working"),
            Todo(content="Task 3", status="completed", active_form="Working"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function()  # type: ignore[call-arg]

        assert "1 completed" in result
        assert "2 pending" in result


class TestWriteTodos:
    """Tests for write_todos tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_write_todos(self, storage: TodoStorage, toolset: FunctionToolset[Any]) -> None:
        """Test writing todos."""
        write_todos = toolset.tools["write_todos"]

        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working on Task 1"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working on Task 2"),
        ]

        result = await write_todos.function(todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].content == "Task 1"
        assert storage.todos[1].status == "in_progress"
        assert "Updated 2 todos" in result

    async def test_write_todos_overwrites(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that write_todos overwrites existing todos."""
        storage.todos = [
            Todo(content="Old task", status="pending", active_form="Working"),
        ]

        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="New task", status="completed", active_form="Working"),
        ]
        await write_todos.function(todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 1
        assert storage.todos[0].content == "New task"

    async def test_write_todos_returns_summary(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that write_todos returns status summary."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working"),
            TodoItem(content="Task 3", status="completed", active_form="Working"),
        ]
        result = await write_todos.function(todos=items)  # type: ignore[call-arg]

        assert "3 todos" in result
        assert "1 completed" in result
        assert "1 in progress" in result
        assert "1 pending" in result

    async def test_write_todos_with_custom_id(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with custom IDs preserves them."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="custom1", content="Task 1", status="pending", active_form="Working"),
            TodoItem(id="custom2", content="Task 2", status="pending", active_form="Working"),
        ]
        await write_todos.function(todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].id == "custom1"
        assert storage.todos[1].id == "custom2"


class TestGetTodoSystemPrompt:
    """Tests for get_todo_system_prompt function."""

    def test_prompt_without_storage(self) -> None:
        """Test system prompt without storage."""
        prompt = get_todo_system_prompt()
        assert "Task Management" in prompt
        assert "write_todos" in prompt

    def test_prompt_with_empty_storage(self) -> None:
        """Test system prompt with empty storage."""
        storage = TodoStorage()
        prompt = get_todo_system_prompt(storage)
        assert "Task Management" in prompt
        # Should not include "Current Todos" section
        assert "Current Todos" not in prompt

    def test_prompt_with_todos(self) -> None:
        """Test system prompt includes current todos."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Task 1", status="pending", active_form="Working"),
            Todo(content="Task 2", status="in_progress", active_form="Working"),
        ]

        prompt = get_todo_system_prompt(storage)

        assert "Current Todos" in prompt
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "[ ]" in prompt  # pending
        assert "[*]" in prompt  # in_progress

    def test_prompt_todos_status_icons(self) -> None:
        """Test that prompt shows correct status icons."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Pending", status="pending", active_form="Working"),
            Todo(content="In Progress", status="in_progress", active_form="Working"),
            Todo(content="Completed", status="completed", active_form="Working"),
        ]

        prompt = get_todo_system_prompt(storage)

        assert "[ ] Pending" in prompt
        assert "[*] In Progress" in prompt
        assert "[x] Completed" in prompt


class TestAddTodo:
    """Tests for add_todo tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_add_todo_to_empty_list(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo to an empty list."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(content="New task", active_form="Working on new task")  # type: ignore[call-arg]

        assert len(storage.todos) == 1
        assert storage.todos[0].content == "New task"
        assert storage.todos[0].active_form == "Working on new task"
        assert storage.todos[0].status == "pending"
        assert "Added todo" in result
        assert storage.todos[0].id in result

    async def test_add_todo_to_existing_list(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo to an existing list."""
        storage.todos = [
            Todo(content="Existing task", status="pending", active_form="Working"),
        ]

        add_todo = toolset.tools["add_todo"]
        await add_todo.function(content="New task", active_form="Working on new task")  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].content == "Existing task"
        assert storage.todos[1].content == "New task"

    async def test_add_todo_returns_id(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that add_todo returns the new todo's ID."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(content="Task", active_form="Working")  # type: ignore[call-arg]

        assert "ID:" in result
        assert storage.todos[0].id in result


class TestUpdateTodoStatus:
    """Tests for update_todo_status tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_update_status_to_in_progress(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status to in_progress."""
        todo = Todo(id="abc123", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="abc123", status="in_progress")  # type: ignore[call-arg]

        assert storage.todos[0].status == "in_progress"
        assert "Updated todo" in result
        assert "in_progress" in result

    async def test_update_status_to_completed(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status to completed."""
        todo = Todo(id="abc123", content="Task", status="in_progress", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="abc123", status="completed")  # type: ignore[call-arg]

        assert storage.todos[0].status == "completed"
        assert "completed" in result

    async def test_update_status_to_pending(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status back to pending."""
        todo = Todo(id="abc123", content="Task", status="in_progress", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="abc123", status="pending")  # type: ignore[call-arg]

        assert storage.todos[0].status == "pending"
        assert "pending" in result

    async def test_update_status_not_found_empty(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status for non-existent todo in empty list."""
        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_update_status_not_found_with_items(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status for non-existent todo when other todos exist."""
        storage.todos = [
            Todo(id="other1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="other2", content="Task 2", status="pending", active_form="Working"),
        ]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result
        # Verify other todos unchanged
        assert len(storage.todos) == 2
        assert all(t.status == "pending" for t in storage.todos)

    async def test_update_status_invalid_status(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating with invalid status."""
        todo = Todo(id="abc123", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="abc123", status="invalid")  # type: ignore[call-arg]

        assert "Invalid status" in result
        assert storage.todos[0].status == "pending"  # unchanged


class TestRemoveTodo:
    """Tests for remove_todo tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_remove_existing_todo(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing an existing todo."""
        todo = Todo(id="abc123", content="Task to remove", status="pending", active_form="Working")
        storage.todos = [todo]

        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(todo_id="abc123")  # type: ignore[call-arg]

        assert len(storage.todos) == 0
        assert "Removed todo" in result
        assert "abc123" in result

    async def test_remove_todo_from_multiple(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing one todo from multiple."""
        storage.todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="id2", content="Task 2", status="pending", active_form="Working"),
            Todo(id="id3", content="Task 3", status="pending", active_form="Working"),
        ]

        remove_todo = toolset.tools["remove_todo"]
        await remove_todo.function(todo_id="id2")  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].id == "id1"
        assert storage.todos[1].id == "id3"

    async def test_remove_nonexistent_todo(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing a non-existent todo."""
        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(todo_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result


class TestAsyncStorageToolset:
    """Tests for toolset with async storage."""

    @pytest.fixture
    def storage(self) -> AsyncMemoryStorage:
        """Create an async storage instance."""
        return AsyncMemoryStorage()

    @pytest.fixture
    def toolset(self, storage: AsyncMemoryStorage) -> FunctionToolset[Any]:
        """Create a toolset with async storage."""
        return create_todo_toolset(async_storage=storage)

    def test_returns_function_toolset(self, toolset: FunctionToolset[Any]) -> None:
        """Test that factory returns a FunctionToolset."""
        assert isinstance(toolset, FunctionToolset)

    def test_toolset_has_all_tools(self, toolset: FunctionToolset[Any]) -> None:
        """Test that toolset has all expected tools."""
        assert "read_todos" in toolset.tools
        assert "write_todos" in toolset.tools
        assert "add_todo" in toolset.tools
        assert "update_todo_status" in toolset.tools
        assert "remove_todo" in toolset.tools

    async def test_read_empty_todos(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading when no todos exist."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function()  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_write_and_read_todos(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing and reading todos with async storage."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working on Task 1"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working on Task 2"),
        ]
        await write_todos.function(todos=items)  # type: ignore[call-arg]

        # Verify in storage
        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[0].content == "Task 1"
        assert todos[1].status == "in_progress"

        # Verify via read
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function()  # type: ignore[call-arg]
        assert "Task 1" in result
        assert "Task 2" in result

    async def test_add_todo(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo with async storage."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(content="New task", active_form="Working")  # type: ignore[call-arg]

        assert "Added todo" in result
        todos = await storage.get_todos()
        assert len(todos) == 1
        assert todos[0].content == "New task"

    async def test_update_todo_status(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating todo status with async storage."""
        # Add a todo first
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="test123", status="completed")  # type: ignore[call-arg]

        assert "Updated todo" in result
        updated = await storage.get_todo("test123")
        assert updated is not None
        assert updated.status == "completed"

    async def test_update_todo_status_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test updating non-existent todo."""
        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_remove_todo(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing a todo with async storage."""
        # Add a todo first
        todo = Todo(id="test123", content="Task to remove", status="pending", active_form="Working")
        await storage.add_todo(todo)

        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(todo_id="test123")  # type: ignore[call-arg]

        assert "Removed todo" in result
        assert "test123" in result

        todos = await storage.get_todos()
        assert len(todos) == 0

    async def test_remove_todo_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test removing non-existent todo."""
        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(todo_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_write_todos_with_custom_id(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with custom IDs preserves them (async)."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="custom1", content="Task 1", status="pending", active_form="Working"),
            TodoItem(id="custom2", content="Task 2", status="pending", active_form="Working"),
        ]
        await write_todos.function(todos=items)  # type: ignore[call-arg]

        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[0].id == "custom1"
        assert todos[1].id == "custom2"


class TestGetTodoSystemPromptAsync:
    """Tests for get_todo_system_prompt_async function."""

    async def test_prompt_without_storage(self) -> None:
        """Test system prompt without storage."""
        prompt = await get_todo_system_prompt_async()
        assert "Task Management" in prompt
        assert "write_todos" in prompt

    async def test_prompt_with_empty_storage(self) -> None:
        """Test system prompt with empty storage."""
        storage = AsyncMemoryStorage()
        prompt = await get_todo_system_prompt_async(storage)
        assert "Task Management" in prompt
        assert "Current Todos" not in prompt

    async def test_prompt_with_todos(self) -> None:
        """Test system prompt includes current todos."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(content="Task 1", status="pending", active_form="Working"))
        await storage.add_todo(Todo(content="Task 2", status="in_progress", active_form="Working"))

        prompt = await get_todo_system_prompt_async(storage)

        assert "Current Todos" in prompt
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "[ ]" in prompt  # pending
        assert "[*]" in prompt  # in_progress

    async def test_prompt_todos_status_icons(self) -> None:
        """Test that prompt shows correct status icons."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(content="Pending", status="pending", active_form="Working"))
        await storage.add_todo(
            Todo(content="In Progress", status="in_progress", active_form="Working")
        )
        await storage.add_todo(Todo(content="Completed", status="completed", active_form="Working"))

        prompt = await get_todo_system_prompt_async(storage)

        assert "[ ] Pending" in prompt
        assert "[*] In Progress" in prompt
        assert "[x] Completed" in prompt
