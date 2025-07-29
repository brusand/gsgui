#!/bin/bash

echo "🎯 GSGUI Desktop Simple - Démarrage"
echo "=================================="

# Fonction de nettoyage
cleanup() {
    echo "🔴 Arrêt du backend..."
    kill $BACKEND_PID 2>/dev/null
    pkill -f "backend_simple.py" 2>/dev/null
    echo "👋 Au revoir!"
    exit 0
}

# Capturer Ctrl+C pour nettoyage
trap cleanup SIGINT SIGTERM

# Tuer les anciens processus
pkill -f "backend_simple.py" 2>/dev/null
pkill -f "gsui_simple.py" 2>/dev/null
sleep 1

# Démarrer le backend en arrière-plan
echo "🚀 Démarrage backend API..."
cd /Users/bruno/gsgui
python backend_simple.py > backend.log 2>&1 &
BACKEND_PID=$!

# Attendre que le backend soit prêt
echo "⏳ Attente du backend..."
sleep 5

# Vérifier que le backend fonctionne
if curl -s http://localhost:8001/ > /dev/null; then
    echo "✅ Backend prêt sur port 8001"
else
    echo "❌ Erreur: Backend non accessible"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Démarrer l'interface
echo "🎨 Démarrage interface..."
echo "📋 Les challenges vont se charger automatiquement..."
cd /Users/bruno/gsgui/src/gs
python gsui_simple.py

# Nettoyage à la fermeture
cleanup