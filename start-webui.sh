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

# Créer le répertoire de logs
mkdir -p ../logs

# Fonction pour rotation manuelle des logs
rotate_log() {
    local logfile="$1"
    local max_size="10485760"  # 10MB
    
    if [ -f "$logfile" ] && [ $(wc -c < "$logfile") -gt $max_size ]; then
        # Rotation des anciens logs
        for i in {4..1}; do
            [ -f "${logfile}.$i" ] && mv "${logfile}.$i" "${logfile}.$((i+1))"
        done
        [ -f "$logfile" ] && mv "$logfile" "${logfile}.1"
    fi
}

# Rotation du log frontend
rotate_log "../logs/frontend.log"

# Démarrer le serveur avec Vite dev (proxy support)
echo "🌐 Démarrage du serveur Vite sur http://localhost:3000"
npm run dev > ../logs/frontend.log 2>&1 &

# Attendre que le serveur démarre
sleep 2

# Vérifier que le serveur fonctionne
if curl -s -I http://localhost:3000 > /dev/null; then
    echo "✅ Serveur Web UI démarré avec succès sur http://localhost:3000"
    echo "📋 Logs: tail -f ../logs/frontend.log"
    echo "🔄 Rotation automatique: 10MB max, 5 backups"
else
    echo "❌ Erreur lors du démarrage du serveur"
    tail -20 ../logs/frontend.log
fi