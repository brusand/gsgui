# GSGUI Backend - Task Completion Checklist

## When a Coding Task is Completed

### Code Quality Checks
1. **Format Code**: Run `black app/` to ensure consistent formatting
2. **Sort Imports**: Run `isort app/ --profile black` to organize imports  
3. **Type Checking**: Ensure all new functions have proper type hints
4. **Documentation**: Add docstrings to new classes and public methods

### Testing (when test suite exists)
1. **Run Tests**: `pytest tests/` to ensure no regressions
2. **Test Coverage**: `pytest --cov=app tests/` to check coverage
3. **Integration Tests**: Test API endpoints with real or mock data

### API Documentation
1. **Update Schemas**: Ensure Pydantic schemas reflect new endpoints
2. **Test Swagger**: Verify endpoints appear correctly in `/docs`
3. **Validate Responses**: Check that API responses match documented schemas

### Configuration & Data
1. **Update .ini Files**: If new configuration options added, update examples
2. **Environment Variables**: Update `.env.example` if new settings added
3. **Data Migration**: Consider impact on existing `.ini` file formats

### Integration & Deployment
1. **Docker Build**: Ensure `docker-compose up -d` works correctly
2. **Health Checks**: Verify `/health` endpoint reports correctly  
3. **WebSocket**: Test real-time functionality if modified
4. **Logs**: Check that logging works properly for new features

### Documentation Updates
1. **README.md**: Update if new endpoints or features added
2. **API Documentation**: Ensure FastAPI auto-docs are accurate
3. **Comments**: Add inline comments for complex GuruShots strategy logic

### Manual Testing Checklist
1. **Start Application**: `uvicorn app.main:app --reload`
2. **Check Health**: Visit `http://localhost:8000/health`
3. **Test New Endpoints**: Use `/docs` interface or curl commands
4. **Monitor Logs**: `tail -f ../logs/backend.log` during testing
5. **WebSocket Connection**: Test `ws://localhost:8000/ws/test_user`

### Git Workflow  
1. **Commit Changes**: Clear commit messages describing strategy implementation
2. **Branch Management**: Create feature branches for new strategies
3. **Push to Remote**: Ensure changes are backed up

## Strategy-Specific Considerations

### When Adding New GuruShots Strategies
1. **Strategy Configuration**: Add to `strategies.ini` format
2. **Scheduler Integration**: Ensure proper APScheduler setup
3. **Error Handling**: Implement robust error handling for API failures
4. **Rate Limiting**: Respect GuruShots API rate limits
5. **Status Tracking**: Implement proper status updates via WebSocket

### When Modifying Turbo Algorithms
1. **History Preservation**: Ensure turbo history tracking still works
2. **Algorithm Testing**: Test with mock data before live deployment  
3. **Performance Metrics**: Verify algorithm performance tracking
4. **Cancellation**: Ensure turbo execution can be properly cancelled