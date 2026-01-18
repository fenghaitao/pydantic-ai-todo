"""Tests for AsyncPostgresStorage."""

# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pydantic_ai_todo import (
    AsyncPostgresStorage,
    Todo,
    TodoEvent,
    TodoEventEmitter,
    TodoEventType,
    create_storage,
)

if TYPE_CHECKING:
    pass


class TestAsyncPostgresStorageInit:
    """Tests for AsyncPostgresStorage initialization."""

    def test_init_with_connection_string(self) -> None:
        """Test initialization with connection string."""
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )
        assert storage._session_id == "test-session"
        assert storage._connection_string == "postgresql://localhost/test"
        assert storage._external_pool is None
        assert not storage._initialized

    def test_init_with_pool(self) -> None:
        """Test initialization with existing pool."""
        mock_pool = MagicMock()
        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        assert storage._session_id == "test-session"
        assert storage._external_pool is mock_pool
        assert storage._pool is mock_pool

    def test_init_requires_connection_string_or_pool(self) -> None:
        """Test that either connection_string or pool is required."""
        with pytest.raises(ValueError, match="Either connection_string or pool"):
            AsyncPostgresStorage(session_id="test-session")

    def test_init_with_custom_table_name(self) -> None:
        """Test initialization with custom table name."""
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
            table_name="custom_todos",
        )
        assert storage._table_name == "custom_todos"

    def test_init_with_event_emitter(self) -> None:
        """Test initialization with event emitter."""
        emitter = TodoEventEmitter()
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
            event_emitter=emitter,
        )
        assert storage._event_emitter is emitter


class TestAsyncPostgresStorageNotInitialized:
    """Tests for operations before initialization."""

    def test_ensure_initialized_raises_without_init(self) -> None:
        """Test that operations fail before initialize() is called."""
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )
        with pytest.raises(RuntimeError, match="not initialized"):
            storage._ensure_initialized()


class TestAsyncPostgresStorageMocked:
    """Tests for AsyncPostgresStorage with mocked asyncpg."""

    @pytest.fixture
    def mock_pool(self) -> MagicMock:
        """Create a mock asyncpg pool."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        pool.close = AsyncMock()
        return pool

    @pytest.fixture
    def storage(self, mock_pool: MagicMock) -> AsyncPostgresStorage:
        """Create storage with mocked pool."""
        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        storage._initialized = True
        return storage

    async def test_initialize_creates_table(self, mock_pool: MagicMock) -> None:
        """Test that initialize creates the todos table."""
        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        await storage.initialize()

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.execute.assert_called_once()
        call_args = conn.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS todos" in call_args

    async def test_initialize_with_connection_string(self) -> None:
        """Test that initialize creates pool from connection string."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool

            storage = AsyncPostgresStorage(
                connection_string="postgresql://localhost/test",
                session_id="test-session",
            )
            await storage.initialize()

            mock_create.assert_called_once_with("postgresql://localhost/test")
            assert storage._pool is mock_pool

    async def test_close_closes_own_pool(self) -> None:
        """Test that close() closes pool created from connection string."""
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()

        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )
        storage._pool = mock_pool
        storage._external_pool = None

        await storage.close()

        mock_pool.close.assert_called_once()
        assert storage._pool is None

    async def test_close_does_not_close_external_pool(self, mock_pool: MagicMock) -> None:
        """Test that close() doesn't close externally provided pool."""
        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        storage._initialized = True

        await storage.close()

        mock_pool.close.assert_not_called()

    async def test_get_todos(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test getting all todos."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetch = AsyncMock(
            return_value=[
                {
                    "id": "abc12345",
                    "content": "Test task",
                    "status": "pending",
                    "active_form": "Testing",
                    "parent_id": None,
                    "depends_on": [],
                }
            ]
        )

        todos = await storage.get_todos()

        assert len(todos) == 1
        assert todos[0].id == "abc12345"
        assert todos[0].content == "Test task"

    async def test_get_todo(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test getting a single todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow = AsyncMock(
            return_value={
                "id": "abc12345",
                "content": "Test task",
                "status": "pending",
                "active_form": "Testing",
                "parent_id": None,
                "depends_on": [],
            }
        )

        todo = await storage.get_todo("abc12345")

        assert todo is not None
        assert todo.id == "abc12345"

    async def test_get_todo_not_found(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test getting a non-existent todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow = AsyncMock(return_value=None)

        todo = await storage.get_todo("nonexistent")

        assert todo is None

    async def test_add_todo(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test adding a todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.execute = AsyncMock()

        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        result = await storage.add_todo(todo)

        assert result == todo
        conn.execute.assert_called_once()

    async def test_add_todo_emits_event(self, mock_pool: MagicMock) -> None:
        """Test that add_todo emits CREATED event."""
        emitter = TodoEventEmitter()
        events: list[tuple[TodoEventType, Todo]] = []

        @emitter.on_created
        def callback(event: TodoEvent) -> None:
            events.append((event.event_type, event.todo))

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.execute = AsyncMock()

        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        assert len(events) == 1
        assert events[0][0] == TodoEventType.CREATED
        assert events[0][1] == todo

    async def test_update_todo(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test updating a todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value

        # Mock get_todo to return the todo
        original_record = {
            "id": "abc12345",
            "content": "Original",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated_record = {
            "id": "abc12345",
            "content": "Updated",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        conn.fetchrow = AsyncMock(side_effect=[original_record, updated_record])
        conn.execute = AsyncMock()

        result = await storage.update_todo("abc12345", content="Updated")

        assert result is not None
        assert result.content == "Updated"

    async def test_update_todo_not_found(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test updating a non-existent todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow = AsyncMock(return_value=None)

        result = await storage.update_todo("nonexistent", content="Updated")

        assert result is None

    async def test_remove_todo(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test removing a todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.execute = AsyncMock(return_value="DELETE 1")

        result = await storage.remove_todo("abc12345")

        assert result is True

    async def test_remove_todo_not_found(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test removing a non-existent todo."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.execute = AsyncMock(return_value="DELETE 0")

        result = await storage.remove_todo("nonexistent")

        assert result is False

    async def test_remove_todo_emits_event(self, mock_pool: MagicMock) -> None:
        """Test that remove_todo emits DELETED event."""
        emitter = TodoEventEmitter()
        events: list[tuple[TodoEventType, Todo]] = []

        @emitter.on_deleted
        def callback(event: TodoEvent) -> None:
            events.append((event.event_type, event.todo))

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow = AsyncMock(
            return_value={
                "id": "abc12345",
                "content": "Test",
                "status": "pending",
                "active_form": "Testing",
                "parent_id": None,
                "depends_on": [],
            }
        )
        conn.execute = AsyncMock(return_value="DELETE 1")

        await storage.remove_todo("abc12345")

        assert len(events) == 1
        assert events[0][0] == TodoEventType.DELETED

    async def test_set_todos(self, mock_pool: MagicMock) -> None:
        """Test setting all todos."""
        # Create conn as MagicMock (not AsyncMock) so transaction() isn't async
        conn = MagicMock()
        conn.execute = AsyncMock()

        # Create a proper async context manager mock for transaction
        transaction_cm = MagicMock()
        transaction_cm.__aenter__ = AsyncMock(return_value=None)
        transaction_cm.__aexit__ = AsyncMock(return_value=None)
        conn.transaction.return_value = transaction_cm

        # Override the pool's acquire to return our custom conn
        mock_pool.acquire.return_value.__aenter__.return_value = conn

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        storage._initialized = True

        todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="T1"),
            Todo(id="id2", content="Task 2", status="pending", active_form="T2"),
        ]

        await storage.set_todos(todos)

        # Should call execute for DELETE + 2 INSERTs
        assert conn.execute.call_count == 3


class TestAsyncPostgresStorageUpdateFields:
    """Tests for update_todo with different field combinations."""

    @pytest.fixture
    def mock_pool(self) -> MagicMock:
        """Create a mock asyncpg pool."""
        pool = MagicMock()
        conn = MagicMock()
        conn.execute = AsyncMock()
        conn.fetchrow = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        return pool

    @pytest.fixture
    def storage(self, mock_pool: MagicMock) -> AsyncPostgresStorage:
        """Create storage with mocked pool."""
        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
        )
        storage._initialized = True
        return storage

    async def test_update_status(self, storage: AsyncPostgresStorage, mock_pool: MagicMock) -> None:
        """Test updating status field."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "status": "in_progress"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        result = await storage.update_todo("abc12345", status="in_progress")

        assert result is not None
        assert result.status == "in_progress"

    async def test_update_active_form(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test updating active_form field."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "active_form": "New form"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        result = await storage.update_todo("abc12345", active_form="New form")

        assert result is not None
        assert result.active_form == "New form"

    async def test_update_parent_id(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test updating parent_id field."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "parent_id": "parent1"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        result = await storage.update_todo("abc12345", parent_id="parent1")

        assert result is not None
        assert result.parent_id == "parent1"

    async def test_update_depends_on(
        self, storage: AsyncPostgresStorage, mock_pool: MagicMock
    ) -> None:
        """Test updating depends_on field."""
        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "depends_on": ["dep1", "dep2"]}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        result = await storage.update_todo("abc12345", depends_on=["dep1", "dep2"])

        assert result is not None
        assert result.depends_on == ["dep1", "dep2"]

    async def test_update_emits_status_changed_event(self, mock_pool: MagicMock) -> None:
        """Test that updating status emits STATUS_CHANGED event."""
        emitter = TodoEventEmitter()
        status_events: list[TodoEventType] = []

        @emitter.on_status_changed
        def callback(event: TodoEvent) -> None:
            status_events.append(event.event_type)

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "status": "in_progress"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        await storage.update_todo("abc12345", status="in_progress")

        assert TodoEventType.STATUS_CHANGED in status_events

    async def test_update_emits_completed_event(self, mock_pool: MagicMock) -> None:
        """Test that completing a todo emits COMPLETED event."""
        emitter = TodoEventEmitter()
        completed_events: list[TodoEventType] = []

        @emitter.on_completed
        def callback(event: TodoEvent) -> None:
            completed_events.append(event.event_type)

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        conn = mock_pool.acquire.return_value.__aenter__.return_value
        original = {
            "id": "abc12345",
            "content": "Test",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "status": "completed"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        await storage.update_todo("abc12345", status="completed")

        assert TodoEventType.COMPLETED in completed_events


class TestAsyncPostgresStorageEventEdgeCases:
    """Tests for event emission edge cases."""

    async def test_update_without_status_change_no_status_event(self) -> None:
        """Test that updating without status change doesn't emit STATUS_CHANGED."""
        mock_pool = MagicMock()
        conn = MagicMock()
        conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        emitter = TodoEventEmitter()
        status_events: list[TodoEventType] = []
        updated_events: list[TodoEventType] = []

        @emitter.on_status_changed
        def on_status(event: TodoEvent) -> None:
            status_events.append(event.event_type)

        @emitter.on_updated
        def on_updated(event: TodoEvent) -> None:
            updated_events.append(event.event_type)

        storage = AsyncPostgresStorage(
            pool=mock_pool,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        original = {
            "id": "abc12345",
            "content": "Original",
            "status": "pending",
            "active_form": "Testing",
            "parent_id": None,
            "depends_on": [],
        }
        updated = {**original, "content": "Updated"}
        conn.fetchrow = AsyncMock(side_effect=[original, updated])

        # Update content only, not status
        await storage.update_todo("abc12345", content="Updated")

        # UPDATED should be emitted, but not STATUS_CHANGED
        assert TodoEventType.UPDATED in updated_events
        assert len(status_events) == 0


class TestAsyncPostgresStorageInitializeEdgeCases:
    """Tests for initialize edge cases."""

    async def test_initialize_when_create_pool_returns_none(self) -> None:
        """Test initialize behavior when create_pool returns None (edge case)."""
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = None

            storage = AsyncPostgresStorage(
                connection_string="postgresql://localhost/test",
                session_id="test-session",
            )
            await storage.initialize()

            # Storage should not be initialized if pool is None
            assert not storage._initialized


class TestAsyncPostgresStorageClose:
    """Tests for close method edge cases."""

    async def test_close_when_pool_is_none(self) -> None:
        """Test close when pool was never created."""
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )
        # Pool is None because initialize() was never called
        await storage.close()  # Should not raise


class TestCreateStoragePostgres:
    """Tests for create_storage with postgres backend."""

    def test_create_postgres_storage(self) -> None:
        """Test creating postgres storage via factory."""
        storage = create_storage(
            "postgres",
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )

        assert isinstance(storage, AsyncPostgresStorage)
        assert storage._session_id == "test-session"

    def test_create_postgres_requires_session_id(self) -> None:
        """Test that postgres backend requires session_id."""
        with pytest.raises(ValueError, match="session_id is required"):
            create_storage(  # pyright: ignore[reportCallIssue]
                "postgres",
                connection_string="postgresql://localhost/test",
            )

    def test_create_postgres_with_event_emitter(self) -> None:
        """Test creating postgres storage with event emitter."""
        emitter = TodoEventEmitter()
        storage = create_storage(
            "postgres",
            connection_string="postgresql://localhost/test",
            session_id="test-session",
            event_emitter=emitter,
        )

        assert storage._event_emitter is emitter


# Integration tests - only run if POSTGRES_URL is set
POSTGRES_URL = os.environ.get("POSTGRES_TEST_URL")


@pytest.mark.skipif(POSTGRES_URL is None, reason="POSTGRES_TEST_URL not set")
class TestAsyncPostgresStorageIntegration:
    """Integration tests for AsyncPostgresStorage with real database."""

    @pytest.fixture
    async def storage(self) -> AsyncGenerator[AsyncPostgresStorage, None]:
        """Create and initialize storage for integration tests."""
        assert POSTGRES_URL is not None
        storage = AsyncPostgresStorage(
            connection_string=POSTGRES_URL,
            session_id=f"test-{os.urandom(4).hex()}",
            table_name="todos_test",
        )
        await storage.initialize()
        yield storage
        # Cleanup
        pool = storage._ensure_initialized()
        async with pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {storage._table_name} WHERE session_id = $1",
                storage._session_id,
            )
        await storage.close()

    async def test_full_crud_cycle(self, storage: AsyncPostgresStorage) -> None:
        """Test complete CRUD cycle with real database."""
        # Create
        todo = Todo(content="Integration test", status="pending", active_form="Testing")
        created = await storage.add_todo(todo)
        assert created.id == todo.id

        # Read
        fetched = await storage.get_todo(todo.id)
        assert fetched is not None
        assert fetched.content == "Integration test"

        # Update
        updated = await storage.update_todo(todo.id, status="completed")
        assert updated is not None
        assert updated.status == "completed"

        # Delete
        deleted = await storage.remove_todo(todo.id)
        assert deleted is True

        # Verify deleted
        gone = await storage.get_todo(todo.id)
        assert gone is None
