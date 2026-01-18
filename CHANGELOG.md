# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2025-01-18

### Added

- **Todo IDs**: Auto-generated 8-char hex IDs for todos (`uuid4().hex[:8]`)
- **Atomic CRUD Operations**:
  - `add_todo(content, active_form)` - Add single task
  - `update_todo_status(todo_id, status)` - Update task status by ID
  - `remove_todo(todo_id)` - Delete task by ID
- **Async Storage Protocol**:
  - `AsyncTodoStorageProtocol` - Interface for async storage backends
  - `AsyncMemoryStorage` - In-memory async implementation
  - `create_storage(backend)` - Factory function for storage backends
  - `get_todo_system_prompt_async()` - Async version of system prompt generator
- **Task Hierarchy** (opt-in via `enable_subtasks=True`):
  - `parent_id` and `depends_on` fields on Todo model
  - `add_subtask(parent_id, content, active_form)` - Create child tasks
  - `set_dependency(todo_id, depends_on_id)` - Link tasks with cycle detection
  - `get_available_tasks()` - List tasks ready to work on
  - `blocked` status for tasks with incomplete dependencies
  - Hierarchical tree view in `read_todos`
- **Event System**:
  - `TodoEventType` enum: CREATED, UPDATED, STATUS_CHANGED, DELETED, COMPLETED
  - `TodoEvent` model with event_type, todo, timestamp, previous_state
  - `TodoEventEmitter` class with `on/off/emit` methods
  - Convenience decorators: `on_created`, `on_completed`, `on_status_changed`, `on_updated`, `on_deleted`
  - Event integration with `AsyncMemoryStorage` and `AsyncPostgresStorage`
- **PostgreSQL Storage Backend**:
  - `AsyncPostgresStorage` - Full PostgreSQL implementation
  - Session-based multi-tenancy via `session_id` parameter
  - Support for connection string or existing `asyncpg.Pool`
  - Auto table creation on `initialize()`
  - `asyncpg>=0.29.0` as required dependency

### Changed

- `read_todos` output now includes todo IDs: `"1. [ ] [id] content"`
- `TODO_SYSTEM_PROMPT` updated to document all available tools
- `create_storage()` now supports `"postgres"` backend

## [0.1.2] - 2025-01-17

### Changed

- `__version__` now dynamically reads from package metadata (pyproject.toml) via `importlib.metadata`
