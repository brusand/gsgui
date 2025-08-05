# Changelog - GSGUI

## [2.1.0] - 2025-08-05

### 🚀 Major Release: Complete Web Interface Migration

#### ✨ New Features
- **React/TypeScript Web Interface**: Complete migration from PyQt6 desktop to modern web interface
- **Mobile Access Support**: Responsive design accessible from any device via browser
- **Real-time WebSocket Communication**: Live log streaming and instant updates
- **Vite Development Server**: Hot reload, fast builds, and modern development experience
- **Proxy Configuration**: Mobile access via DynDNS with automatic API routing
- **Cross-platform Deployment**: Portable system supporting Linux, macOS, and Windows

#### 🔧 Technical Improvements
- **FastAPI Backend**: Async backend with WebSocket support for real-time updates
- **Virtual Environment Support**: Python 3.13+ compatibility with automated setup
- **Process Management**: Automated monitoring, restart, and PID-based tracking
- **Modern Toolchain**: TypeScript, ESLint, Vite build system
- **Error Recovery**: Comprehensive error handling and automatic service restart

#### 📱 Interface Features
- **Professional Dark Theme**: Modern UI with hover effects and animations
- **Interactive Components**: Drag-and-drop operations and responsive buttons
- **Real-time Logs**: Live log streaming with color-coded messages
- **Mobile Responsive**: Optimized for both desktop and mobile devices
- **Intuitive Navigation**: Streamlined workflow with clear visual feedback

#### 🌍 Deployment & DevOps
- **Portable Installation**: One-command setup across all major operating systems
- **Docker Ready**: Container-ready configuration with comprehensive documentation
- **Production Scripts**: Process management with monitoring and auto-restart
- **Dependency Management**: Automatic virtual environment and dependency resolution

#### 🔄 Migration & Compatibility
- **Configuration Preservation**: Existing profiles and settings automatically migrated
- **Backward Compatibility**: Legacy configurations supported during transition
- **Enhanced Multi-Profile**: Improved profile management with web interface
- **Port Configuration**: Frontend (3000), Backend (8001) with proxy routing

#### 🛠️ Infrastructure
- **OS Detection**: Automatic platform detection and adaptation
- **Requirements Management**: Multiple requirement files for different environments
- **Logging System**: Comprehensive logging with rotation and filtering
- **Health Monitoring**: Service health checks and automatic recovery

### 🔥 Breaking Changes
- Desktop PyQt6 interface deprecated in favor of web interface
- New port configuration requires router setup for external access
- Updated configuration file structure for enhanced multi-profile support

### 📋 Migration Guide
1. Run `./install-dependencies.sh` to setup new environment
2. Use `./process-manager-portable.sh monitor` for production deployment
3. Access interface at `http://localhost:3000` or via configured DynDNS
4. Existing profiles and strategies automatically preserved

---

## [2.0.0] - 2025-08-02

### ✨ Previous Features
- Multi-profile support with independent job scheduling
- FastAPI backend with APScheduler for persistent jobs
- Real-time WebSocket logging with profile-based filtering
- Enhanced vote execution with API validation
- Auto-refresh functionality after successful operations

---

*GSGUI Web Interface - Professional GuruShots automation platform*