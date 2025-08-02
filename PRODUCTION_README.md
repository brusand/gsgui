# GSGUI v2.0.0 - Production Guide

## 🚀 Quick Start

### 1. Launch Backend
```bash
./start_backend.sh
```

### 2. Launch UI
```bash
cd src/gs
python gs_backend_ui.py
```

## 📋 System Requirements

- Python 3.8+
- PySide6
- FastAPI
- APScheduler
- ConfigObj
- Requests

## 🔧 Production Configuration

### Backend Configuration
- **Port**: 8001 (configurable in gs_backend.py)
- **Data storage**: `backend/data/gsgui.ini`
- **Logs**: `backend.log`

### Profile Management
- Profiles stored in `backend/data/gsgui.ini`
- Token management per profile
- Independent job scheduling per profile

## 🔄 Multi-Profile Operations

### Adding New Profiles
1. Launch gs_backend_ui.py
2. Use profile selection dialog
3. Enter profile credentials
4. System automatically saves configuration

### Profile Switching
- Click "🚪 Déconnexion" button
- Select different profile
- Backend jobs continue running
- WebSocket logs filtered by active profile

## 📊 Job Management

### Strategy Scheduling
- Jobs persist across backend restarts
- Profile-based job isolation
- Automatic cleanup of expired strategies
- Real-time job status via WebSocket

### Backend Services
- **Strategy Scheduler**: APScheduler-based job management
- **GuruShots API**: Real challenge data integration
- **WebSocket Manager**: Real-time communication
- **Config Manager**: Profile and strategy persistence

## 🔍 Monitoring & Debugging

### Backend Logs
- Real-time logs via WebSocket in UI
- File logging in `backend.log`
- Profile-specific log filtering

### Health Checks
- Backend status: http://localhost:8001/api/v1/profiles
- WebSocket: ws://localhost:8001/ws/logs

## 🛠️ Troubleshooting

### Backend Won't Start
1. Check port 8001 availability
2. Verify Python dependencies
3. Check file permissions on data directory

### Profile Connection Issues
1. Verify GuruShots token validity
2. Check network connectivity
3. Review backend logs for API errors

### Job Scheduling Problems
1. Verify challenge exists in API
2. Check strategy configuration syntax
3. Review APScheduler logs in backend

## 📦 Production Deployment

### File Structure
```
gsgui/
├── gs_backend.py              # Main backend server
├── start_backend.sh           # Launcher script
├── backend/                   # FastAPI structure
│   ├── app/                   # Application code
│   └── data/                  # Configuration storage
└── src/gs/
    ├── gs_backend_ui.py       # Modern interface
    ├── gsui.py               # Original interface
    └── gsui_api_client.py    # API client
```

### Environment Variables
- `REAL_VOTE_AVAILABLE=true`: Enable real voting
- `DEBUG_MODE=false`: Production logging level

## 🔄 Backup & Recovery

### Configuration Backup
```bash
cp backend/data/gsgui.ini backup/gsgui_$(date +%Y%m%d).ini
```

### Strategy Backup
```bash
cp backend/data/strategies.ini backup/strategies_$(date +%Y%m%d).ini
```

## 📈 Performance

### Optimization
- WebSocket connection pooling
- Efficient API request batching
- Minimal UI update frequency
- Cached challenge data

### Scaling
- Supports multiple concurrent profiles
- Independent job scheduling per profile
- Async backend operations
- Real-time status updates

## 🔐 Security

### Token Management
- Secure token storage per profile
- No token exposure in logs
- Automatic token validation

### API Security
- Request rate limiting
- Input validation
- Error sanitization

## 📞 Support

For production issues:
1. Check backend logs
2. Verify configuration files
3. Test API connectivity
4. Review job scheduling status

Version: 2.0.0  
Release Date: 2025-08-02  
Status: Production Ready