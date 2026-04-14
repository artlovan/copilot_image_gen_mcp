# Copilot Instructions — Image Generation MCP Server

## SOLID Design Principles

This codebase follows the SOLID design principles. All contributions must adhere to them.

### S — Single Responsibility Principle (SRP)

Each module/class has exactly **one reason to change**:

| Module | Single Responsibility |
|--------|----------------------|
| `server.py` | MCP tool definitions and request routing |
| `session.py` | Conversation state and multi-turn orchestration |
| `auth.py` | Token acquisition, refresh, and caching |
| `storage.py` | Cross-platform file I/O and path management |
| `config.py` | Configuration defaults and environment overrides |
| `models.py` | Data structures (no behavior) |
| `transport/*.py` | Network protocol handling |
| `parsers/*.py` | Response parsing and data extraction |

**Rule**: If a change requires modifying two unrelated modules, one of them likely has too
many responsibilities.

### O — Open/Closed Principle (OCP)

Modules are **open for extension, closed for modification**:

- **Transport layer**: Add new transport implementations (e.g., SSE, gRPC) by creating a
  new class that extends `TransportBase` — no changes to `session.py` needed.
- **Parsers**: Add new response parsers by implementing the parser interface — no changes
  to existing parsers needed.
- **Configuration**: New settings are added via env vars without modifying existing config logic.

### L — Liskov Substitution Principle (LSP)

Subclasses must be **substitutable** for their base classes:

- Any `TransportBase` subclass must work with `ImageGenSession` without special handling.
- Any response parser must produce the same output types regardless of implementation.

### I — Interface Segregation Principle (ISP)

Clients should not depend on methods they don't use:

- Transport interface defines only transport concerns (connect, send, receive, close).
- Parser interface defines only parsing concerns (parse a message, extract results).
- No "god interfaces" — keep interfaces small and focused.

### D — Dependency Inversion Principle (DIP)

High-level modules depend on **abstractions**, not concrete implementations:

- `session.py` depends on `TransportBase` (abstract), not `SignalRTransport` (concrete).
- `server.py` depends on `ImageGenSession` interface, not transport details.
- Configuration is injected, not hardcoded.

## Code Style

- **Python 3.10+** with type hints on all public functions
- **`pathlib.Path`** for all file paths (cross-platform macOS + Windows)
- **Dataclasses** for data structures (no behavior in data classes)
- **Stderr for logging** (`print(..., file=sys.stderr)`) — never pollute MCP stdio
- **No comments on obvious code** — only comment _why_, not _what_
- **Descriptive names** over abbreviations (`conversation_id` not `conv_id`)
