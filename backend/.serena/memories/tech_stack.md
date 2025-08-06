# GSGUI Backend - Tech Stack and Dependencies

## Core Framework
- **FastAPI 0.104.1**: Modern async web framework for the API
- **Uvicorn 0.24.0**: ASGI server for FastAPI
- **Python 3.11+**: Target Python version

## Key Libraries

### Async HTTP & Web
- **aiohttp 3.9.1**: Async HTTP client for GuruShots API calls
- **httpx 0.25.2**: Alternative async HTTP client  
- **websockets 12.0**: WebSocket support for real-time updates

### Data & Configuration
- **SQLAlchemy 2.0.23**: ORM (currently configured but using file-based storage)
- **Alembic 1.12.1**: Database migrations
- **configobj 5.0.8**: .ini file configuration management
- **pydantic 2.5.1**: Data validation and settings management
- **pydantic-settings 2.1.0**: Settings management

### Background Processing & Scheduling
- **APScheduler 3.10.4**: Advanced Python scheduler for strategy execution
- **Celery 5.3.4**: Distributed task queue (configured but not actively used)

### Caching & Session Management
- **Redis 5.0.1**: In-memory data structure store
- **python-redis-lock 4.0.0**: Distributed locking

### Security & Authentication
- **python-jose[cryptography] 3.3.0**: JWT token handling
- **passlib[bcrypt] 1.7.4**: Password hashing

### Development Tools
- **pytest 7.4.3**: Testing framework
- **pytest-asyncio 0.21.1**: Async testing support
- **black 23.11.0**: Code formatting
- **isort 5.12.0**: Import sorting

## Architecture Pattern
- **Hexagonal Architecture**: Clean separation between API, services, and external integrations
- **Async/Await**: Full async support for concurrent operations
- **Dependency Injection**: FastAPI's built-in DI system
- **Service Layer Pattern**: Business logic in dedicated service classes