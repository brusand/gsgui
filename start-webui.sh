#!/bin/bash

# Script pour démarrer le serveur Web UI
cd /Users/bruno/gsgui/web-ui

echo "🚀 Démarrage du serveur Web UI..."
echo "📁 Répertoire: $(pwd)"

# Build si nécessaire
if [ ! -d "dist" ] || [ "$(find src -name '*.ts' -o -name '*.tsx' -newer dist 2>/dev/null | head -1)" ]; then
    echo "🔨 Build nécessaire..."
    npm run build
fi

# Démarrer le serveur
echo "🌐 Démarrage du serveur sur http://localhost:3000"
npx serve dist -l 3000 > /tmp/serve.log 2>&1 &

# Attendre que le serveur démarre
sleep 2

# Vérifier que le serveur fonctionne
if curl -s -I http://localhost:3000 > /dev/null; then
    echo "✅ Serveur Web UI démarré avec succès sur http://localhost:3000"
    echo "📋 Logs: tail -f /tmp/serve.log"
else
    echo "❌ Erreur lors du démarrage du serveur"
    cat /tmp/serve.log
fi