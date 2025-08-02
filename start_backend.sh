#!/bin/bash

echo "🚀 Démarrage Backend GSGUI"
echo "=========================="

# Tuer ancien backend
pkill -f "backend_real.py" 2>/dev/null
sleep 1

# Démarrer le backend
echo "🚀 Lancement backend API sur port 8001..."
cd /Users/bruno/gsgui
python gs_backend.py

echo "👋 Backend arrêté"