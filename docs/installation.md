# Installation

## Requirements

- Python 3.10 or higher
- [pydantic-ai](https://ai.pydantic.dev/) installed

## Install from PyPI

=== "pip"

    ```bash
    pip install pydantic-ai-todo
    ```

=== "uv"

    ```bash
    uv add pydantic-ai-todo
    ```

=== "poetry"

    ```bash
    poetry add pydantic-ai-todo
    ```

## Optional: PostgreSQL Support

For PostgreSQL storage, you need `asyncpg`:

=== "pip"

    ```bash
    pip install pydantic-ai-todo asyncpg
    ```

=== "uv"

    ```bash
    uv add pydantic-ai-todo asyncpg
    ```

## Verify Installation

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

# Create agent with todo capabilities
agent = Agent(
    "openai:gpt-4o",
    toolsets=[create_todo_toolset()],
)

# Test it works
result = await agent.run("Add a task: Test installation")
print(result.output)
```

## API Key Setup

You'll need an API key for your LLM provider. For OpenAI:

=== "Environment Variable"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```

=== ".env File"

    ```bash
    # .env
    OPENAI_API_KEY=your-api-key
    ```

    ```python
    from dotenv import load_dotenv
    load_dotenv()
    ```

## What's Included

The package provides:

- `create_todo_toolset()` — Factory function to create the toolset
- `TodoStorage` — Sync in-memory storage
- `AsyncMemoryStorage` — Async in-memory storage  
- `AsyncPostgresStorage` — PostgreSQL storage
- `TodoEventEmitter` — Event system for callbacks
- `Todo`, `TodoItem` — Pydantic models

## Next Steps

- [Quick Start](examples/basic-usage.md) — Build your first todo-enabled agent
- [Core Concepts](concepts/index.md) — Understand the architecture
- [Storage Backends](concepts/storage.md) — Choose the right storage
