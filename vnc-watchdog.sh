#!/bin/bash

# VNC Watchdog - Vérifie et relance le service screensharing si nécessaire
LOG_FILE="/tmp/vnc-watchdog.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Fonction de log
log_message() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

# Vérifier le nombre de connexions zombies
ZOMBIE_COUNT=$(netstat -an 2>/dev/null | grep 5900 | grep CLOSE_WAIT | wc -l | tr -d ' ')

# Si plus de 50 connexions zombies, redémarrer le service
if [ "$ZOMBIE_COUNT" -gt 50 ]; then
    log_message "⚠️  $ZOMBIE_COUNT connexions zombies détectées - redémarrage nécessaire"
    # Forcer le redémarrage même si le service semble actif
fi

# Vérifier si le service screensharing est actif
if launchctl list | grep -q "com.apple.screensharing"; then
    # Le service est listé, vérifier s'il répond vraiment
    # On vérifie si le port VNC (5900) est ouvert
    if nc -z localhost 5900 2>/dev/null && [ "$ZOMBIE_COUNT" -le 50 ]; then
        log_message "✅ Service VNC répond correctement ($ZOMBIE_COUNT connexions zombies)"
        exit 0
    else
        if [ "$ZOMBIE_COUNT" -gt 50 ]; then
            log_message "⚠️  Service VNC saturé par $ZOMBIE_COUNT connexions zombies"
        else
            log_message "⚠️  Service VNC listé mais port 5900 ne répond pas"
        fi
    fi
else
    log_message "⚠️  Service VNC n'est pas listé"
fi

# Si on arrive ici, il y a un problème - redémarrer le service
log_message "🔄 Redémarrage du service VNC..."

# Arrêter le service
sudo launchctl stop system/com.apple.screensharing 2>/dev/null
sleep 2

# Tuer les processus screensharingd bloqués
sudo pkill -9 screensharingd 2>/dev/null
sleep 2

# Redémarrer le service
sudo launchctl start system/com.apple.screensharing 2>/dev/null
sleep 3

# Vérifier que le redémarrage a fonctionné
if nc -z localhost 5900 2>/dev/null; then
    NEW_ZOMBIE_COUNT=$(netstat -an 2>/dev/null | grep 5900 | grep CLOSE_WAIT | wc -l | tr -d ' ')
    log_message "✅ Service VNC redémarré avec succès ($NEW_ZOMBIE_COUNT connexions zombies)"
else
    log_message "❌ ERREUR : Le service VNC ne répond toujours pas après redémarrage"
    log_message "    Vérifiez que sudo est configuré correctement (exécutez setup-vnc-sudo.sh)"
fi
