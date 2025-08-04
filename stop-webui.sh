#!/bin/bash

# Script pour arrêter le serveur Web UI
echo "🛑 Arrêt du serveur Web UI..."

# Tuer tous les processus serve qui servent le port 3000
pkill -f "serve.*3000"
pkill -f "npx serve dist"

# Attendre un peu
sleep 1

# Vérifier que le serveur est arrêté
if ! curl -s -I http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Serveur Web UI arrêté avec succès"
else
    echo "⚠️ Le serveur semble encore actif, tentative d'arrêt forcé..."
    # Force kill si nécessaire
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
    if ! curl -s -I http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Serveur Web UI arrêté (forcé)"
    else
        echo "❌ Impossible d'arrêter le serveur"
    fi
fi