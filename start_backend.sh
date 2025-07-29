#!/bin/bash

echo "🚀 Démarrage Backend GSGUI Simple"
echo "================================"

# Tuer ancien backend
pkill -f "backend_simple.py" 2>/dev/null
sleep 1

# Démarrer le backend
echo "🚀 Lancement backend API sur port 8001..."
cd /Users/bruno/gsgui
python backend_simple.py

echo "👋 Backend arrêté"