#!/bin/bash
# VNC Session Cleanup - Nettoie automatiquement les sessions VNC après déconnexion
# À exécuter périodiquement via cron ou LaunchDaemon

LOG_FILE="/tmp/vnc-session-cleanup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

log_message() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

# Vérifier les connexions VNC actives
ACTIVE_VNC=$(netstat -an 2>/dev/null | grep 5900 | grep ESTABLISHED | wc -l | tr -d ' ')
ZOMBIE_VNC=$(netstat -an 2>/dev/null | grep 5900 | grep CLOSE_WAIT | wc -l | tr -d ' ')

log_message "Connexions VNC: $ACTIVE_VNC actives, $ZOMBIE_VNC zombies"

# Si aucune connexion active mais il y a des zombies, nettoyer
if [ "$ACTIVE_VNC" -eq 0 ] && [ "$ZOMBIE_VNC" -gt 0 ]; then
    log_message "🧹 Nettoyage des $ZOMBIE_VNC connexions zombies..."

    # Rafraîchir le loginwindow pour l'écran de connexion propre
    sudo pkill -HUP loginwindow 2>/dev/null

    # Si trop de zombies, redémarrer VNC
    if [ "$ZOMBIE_VNC" -gt 20 ]; then
        log_message "⚠️  Trop de zombies ($ZOMBIE_VNC) - redémarrage VNC"
        sudo launchctl stop system/com.apple.screensharing 2>/dev/null
        sleep 2
        sudo pkill -9 screensharingd 2>/dev/null
        sleep 2
        sudo launchctl start system/com.apple.screensharing 2>/dev/null
        sleep 3

        NEW_ZOMBIES=$(netstat -an 2>/dev/null | grep 5900 | grep CLOSE_WAIT | wc -l | tr -d ' ')
        log_message "✅ VNC redémarré - zombies restants: $NEW_ZOMBIES"
    fi

    log_message "✅ Nettoyage terminé"
fi

# Garder le log à une taille raisonnable (dernières 1000 lignes)
if [ -f "$LOG_FILE" ]; then
    tail -1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
