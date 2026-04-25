#!/bin/bash

# VNC Watchdog - Vérifie et relance le service screensharing si nécessaire
LOG_FILE="/tmp/vnc-watchdog.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Fonction de log
log_message() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

# Vérifier si le service screensharing est actif
if launchctl list | grep -q "com.apple.screensharing"; then
    # Le service est listé, vérifier s'il répond vraiment
    # On vérifie si le port VNC (5900) est ouvert
    if nc -z localhost 5900 2>/dev/null; then
        log_message "✅ Service VNC répond correctement"
        exit 0
    else
        log_message "⚠️  Service VNC listé mais port 5900 ne répond pas"
    fi
else
    log_message "⚠️  Service VNC n'est pas listé"
fi

# Si on arrive ici, il y a un problème - redémarrer le service
log_message "🔄 Redémarrage du service VNC..."

# Arrêter puis redémarrer le service
sudo launchctl stop com.apple.screensharing
sleep 2
sudo launchctl start com.apple.screensharing
sleep 2

# Vérifier que le redémarrage a fonctionné
if nc -z localhost 5900 2>/dev/null; then
    log_message "✅ Service VNC redémarré avec succès"
else
    log_message "❌ ERREUR : Le service VNC ne répond toujours pas après redémarrage"
fi
