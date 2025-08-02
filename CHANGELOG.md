# Changelog - GSGUI

## [2.0.0] - 2025-08-02

### ✨ New Features
- **Multi-profile support**: Switch between multiple GuruShots profiles seamlessly
- **Real-time WebSocket logging**: Live backend logs with profile-based filtering
- **Enhanced vote execution**: API validation before vote execution
- **Auto-refresh functionality**: Automatic challenge refresh after successful votes
- **Profile-based strategy scheduling**: Independent job management per profile
- **Logout/reconnection system**: Switch profiles while maintaining backend jobs

### 🔧 Technical Improvements
- **FastAPI backend**: Modern async backend with APScheduler for persistent jobs
- **Clean architecture**: Separation of backend/frontend with clear APIs
- **Thread-safe WebSocket**: Robust real-time communication
- **Comprehensive error handling**: Detailed logging and error recovery
- **Profile switching**: No interruption of scheduled backend jobs
- **API client architecture**: Enhanced client with profile management

### 🧹 Code Quality
- **Production cleanup**: Removed all temporary test files and experimental code
- **Consistent naming**: gs_ prefix for all main components
- **Clean codebase**: Only production-ready files maintained
- **Documentation**: Comprehensive guides and setup instructions

### 📦 Components
- `gs_backend.py`: Main FastAPI backend server
- `gs_backend_ui.py`: Modern PySide6 interface with profile switching
- `gsui.py`: Original interface (preserved for compatibility)
- `backend/`: Modern FastAPI structure with services and models
- `start_backend.sh`: Production launcher script

### 🚀 Production Ready
- Multi-profile job scheduling with persistence
- Real-time WebSocket communication
- Robust error handling and recovery
- Clean separation of concerns
- Ready for production deployment

### 🔄 Migration from v1.x
- All existing configurations are preserved
- Profile data automatically migrated
- Backend jobs continue running during upgrade
- No manual intervention required