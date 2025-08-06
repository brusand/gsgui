# GSGUI Backend - Code Structure and Conventions

## Directory Structure
```
backend/
├── app/                     # Main application package
│   ├── api/v1/             # REST API endpoints
│   │   └── endpoints/      # Individual endpoint modules
│   ├── core/               # Core configuration
│   ├── models/             # Data models and file-based storage
│   ├── schemas/            # Pydantic schemas for validation
│   ├── services/           # Business logic services
│   ├── websockets/         # WebSocket handling
│   └── main.py            # FastAPI application entry point
├── data/                   # Configuration and data files (.ini files)
├── tests/                  # Test files (not currently populated)
└── requirements.txt        # Python dependencies
```

## Key Services Architecture

### GuruShotsAPI (`app/services/gurushots_api.py`)
- HTTP client for GuruShots API interactions
- Methods: `get_challenges()`, `submit_votes()`, `execute_simple_vote()`, `get_vote_panel()`
- Handles authentication headers and SSL context

### TurboExecutor (`app/services/turbo_executor.py`)  
- Complex turbo boost execution with timing algorithms
- Methods: `execute_turbo()`, `execute_turbo_challenge()`, `_submit_single_turbo_selection()`
- Manages turbo history and status tracking

### StrategyScheduler (`app/services/strategy_scheduler.py`)
- Automated scheduling of photography challenge strategies  
- Implements timing strategies like those described in the ANCA document

### ConfigManager (`app/services/config_manager.py`)
- Manages .ini file based configuration and persistence
- Maintains compatibility with original `gsui.py` data formats

## Coding Conventions

### Python Style
- **PEP 8 compliant** with Black formatting
- **Type hints required** for all public methods and classes
- **Async/await** for all I/O operations
- **Descriptive variable names** with snake_case

### Documentation Style  
- **Docstrings**: Triple quotes for all classes and public methods
- **Inline comments**: For complex business logic
- **Type annotations**: Required for method signatures

### Error Handling
- **Async exception handling** with proper logging
- **Structured error responses** with timestamps and error details
- **Global exception handler** in main.py

### Logging
- **Rotating file logs** in `../logs/backend.log`
- **Structured logging** with timestamp, logger name, level, message
- **Console output** for development

### API Design
- **RESTful endpoints** following OpenAPI standards
- **Pydantic schemas** for request/response validation
- **Consistent JSON responses** with standard fields
- **WebSocket endpoints** for real-time updates