# GSGUI Backend - Suggested Commands

## Development Commands

### Environment Setup
```bash
# Install dependencies  
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your specific settings
```

### Running the Application

#### Local Development
```bash
# Start FastAPI dev server with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative with explicit module
uvicorn app.main:app --reload
```

#### Docker Development  
```bash
# Build and start with Docker Compose
docker-compose up -d

# View logs  
docker-compose logs -f

# Stop services
docker-compose down
```

### Code Quality

#### Formatting
```bash
# Format code with Black
black app/ --line-length 88

# Sort imports with isort  
isort app/ --profile black
```

#### Testing
```bash
# Run tests with pytest
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc  
- **Health Check**: http://localhost:8000/health

### Debugging & Monitoring

#### Logs
```bash
# View rotating logs
tail -f ../logs/backend.log

# View Docker logs
docker-compose logs -f backend
```

#### API Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test challenges endpoint (requires user token)
curl -H "Authorization: Bearer your_token" http://localhost:8000/api/v1/challenges/
```

### System Commands (macOS/Darwin)

#### File Operations
```bash
# List files with details
ls -la

# Find files by pattern  
find . -name "*.py" -type f

# Search in files
grep -r "pattern" app/

# Change directory
cd app/services/
```

#### Process Management
```bash
# Find running processes
ps aux | grep python

# Kill process by PID
kill -9 <PID>

# View system resources  
top
```

#### Git Operations
```bash
# Common Git commands
git status
git add .
git commit -m "message"
git push origin main
git pull origin main
git log --oneline -10
```

### Development Workflow
1. Create feature branch: `git checkout -b feature/new-strategy`
2. Make changes with proper formatting: `black app/` and `isort app/`  
3. Test changes: `pytest tests/` (when tests exist)
4. Commit and push: `git add .`, `git commit -m "Add strategy"`, `git push`
5. Monitor logs: `tail -f ../logs/backend.log`