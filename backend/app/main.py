"""
GSGUI Backend - FastAPI Application
Main entry point for the GuruShots GUI backend server
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import logging
import logging.handlers
import os

from app.api.v1.api import api_router
from app.core.config import settings
from app.websockets.connection_manager import connection_manager

# Configure rotating logs
def setup_rotating_logs():
    # Créer le répertoire de logs s'il n'existe pas
    log_dir = "../logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Supprimer les handlers existants
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler rotatif pour backend.log
    backend_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "backend.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Garder 5 fichiers de backup
        encoding='utf-8'
    )
    backend_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Handler console (pour voir les logs en temps réel)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    # Ajouter les handlers
    root_logger.addHandler(backend_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

logger = setup_rotating_logs()

# Create FastAPI application
app = FastAPI(
    title="GSGUI Backend API",
    description="Backend API for GuruShots GUI application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager is imported as global instance

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "GSGUI Backend API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "database": "connected",  # TODO: vérifier vraiment la DB
            "redis": "connected"      # TODO: vérifier vraiment Redis
        }
    }

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await connection_manager.connect(websocket, user_id)
    logger.info(f"WebSocket connection established for user: {user_id}")
    
    try:
        while True:
            # Maintenir la connexion active
            data = await websocket.receive_text()
            
            # Echo pour test (à supprimer en production)
            await connection_manager.send_personal_message(
                user_id, 
                {"type": "echo", "message": f"Received: {data}"}
            )
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket connection closed for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        connection_manager.disconnect(websocket, user_id)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )