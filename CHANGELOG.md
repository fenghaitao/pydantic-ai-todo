# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.10] - 2026-02-26

### Added

- **Custom tool descriptions** — `create_todo_toolset()` now accepts `descriptions: dict[str, str] | None` parameter to override any tool's built-in description. Enables customizing agent behavior without forking the library ([#11](https://github.com/vstorm-co/pydantic-ai-todo/issues/11))

## [0.1.9] - 2026-02-24

### Changed

- **Enriched all tool description constants** — All 9 description constants (`TODO_TOOL_DESCRIPTION`, `TODO_SYSTEM_PROMPT`, `READ_TODO_DESCRIPTION`, `ADD_TODO_DESCRIPTION`, `UPDATE_TODO_STATUS_DESCRIPTION`, `REMOVE_TODO_DESCRIPTION`, `ADD_SUBTASK_DESCRIPTION`, `SET_DEPENDENCY_DESCRIPTION`, `GET_AVAILABLE_TASKS_DESCRIPTION`) rewritten with detailed "When to Use" / "When NOT to Use" sections, status workflow documentation, parameter explanations, and practical tips. Follows the Claude Code / deepagents pattern of putting comprehensive guidance directly in tool descriptions.
- **Expanded `TODO_SYSTEM_PROMPT`** — Tool listing now includes brief usage guidance for each tool. Added "Task Workflow" section with numbered steps.

## [0.1.8] - 2026-02-16

### Fixed

- **System prompt now includes todo IDs**: `get_todo_system_prompt()` and `get_todo_system_prompt_async()` now render todos as `- [x] [abc123ef] Task content` instead of `- [x] Task content`. Previously, agents could see their todos in the system prompt but had no way to know the IDs needed by `update_todo_status` and `remove_todo` without first calling `read_todos`. ([#9](https://github.com/vstorm-co/pydantic-ai-todo/pull/9) by [@pedro-at-noxus](https://github.com/pedro-at-noxus))

- **Improved `active_form` parameter descriptions**: Added concrete transformation examples (e.g., "Fix the login bug" → "Fixing the login bug") to `add_todo` and `add_subtask` tool descriptions and docstrings. Some models previously asked the user for this value instead of generating it from the task content. ([#9](https://github.com/vstorm-co/pydantic-ai-todo/pull/9) by [@pedro-at-noxus](https://github.com/pedro-at-noxus))

## [0.1.7] - 2026-02-15

### Added

- **Event Subscription Patterns**: New documentation section covering:
  - Single event, multiple subscribers
  - Single subscriber, multiple events via stacked decorators
  - Conditional event handling
  - Dynamic registration/unregistration at runtime
  - Class-based event handlers for organizing related logic
- **Cycle Detection Deep Dive**: Expanded documentation explaining:
  - DFS algorithm for cycle detection
  - Self-dependency, direct cycle, and transitive cycle cases
  - Diamond dependencies (allowed)
  - Practical examples for each case
- **Multi-Tenancy Example**: New guide for per-user task isolation in web applications
- **Migration Guide**: New guide for transitioning from memory to PostgreSQL storage

### Changed

- **Navigation**: Updated docs nav to include multi-tenancy and migration guide

## [0.1.6] - 2026-02-03

### Changed

- **Lightweight dependency**: Replaced `pydantic-ai` with `pydantic-ai-slim` to reduce install footprint — pulls in only the core modules needed by the toolset
- **Removed CLI**: Dropped the CLI entry point to keep the package focused as a library-only toolset

## [0.1.5] - 2025-01-23

### Added

- **Missing Exports**: Added `UPDATE_TODO_STATUS_DESCRIPTION` and `REMOVE_TODO_DESCRIPTION` constants to public API

### Fixed

- **Documentation**: Fixed `create_todo_toolset` signature - added missing `id` parameter and corrected return type to `FunctionToolset[Any]`

## [0.1.4] - 2025-01-22

### Added

- **Full Documentation Site**: MkDocs Material documentation matching pydantic-deep style
  - Concepts: Toolset, Storage, Types
  - Advanced: Subtasks & Dependencies, Event System
  - Examples: Basic Usage, Async Storage, PostgreSQL, Subtasks, Events
  - API Reference: Auto-generated from docstrings
- **GitHub Actions Workflow**: Auto-deploy docs to GitHub Pages on push to main
- **Custom Styling**: Pink theme with Inter/JetBrains Mono fonts

### Changed

- **README**: Complete rewrite with centered header, badges, Use Cases table, and vstorm-co branding

### Fixed

- Documentation accuracy: Added missing "blocked" status to all status lists
- Documentation accuracy: Fixed `previous_state` type from `str | None` to `Todo | None`

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
