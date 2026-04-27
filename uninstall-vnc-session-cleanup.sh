#!/bin/bash
# Désinstallation du service de nettoyage automatique des sessions VNC

PLIST_PATH="/Library/LaunchDaemons/com.gsgui.vnc.session-cleanup.plist"

echo "🗑️  Désinstallation du service de nettoyage VNC..."

# Vérifier sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ce script nécessite sudo"
    echo "Relancez avec: sudo $0"
    exit 1
fi

# Décharger le service
if [ -f "$PLIST_PATH" ]; then
    launchctl unload -w "$PLIST_PATH" 2>/dev/null
    rm -f "$PLIST_PATH"
    echo "✅ Service désinstallé avec succès"
else
    echo "⚠️  Service déjà désinstallé"
fi

# Nettoyer les logs
rm -f /tmp/vnc-session-cleanup*.log

echo "✅ Désinstallation terminée"
