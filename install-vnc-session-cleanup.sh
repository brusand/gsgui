#!/bin/bash
# Installation du service de nettoyage automatique des sessions VNC
# Nettoie les sessions zombies toutes les 5 minutes

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_PATH="/Library/LaunchDaemons/com.gsgui.vnc.session-cleanup.plist"
CLEANUP_SCRIPT="$SCRIPT_DIR/vnc-session-cleanup.sh"

echo "🔧 Installation du service de nettoyage VNC..."
echo ""

# Vérifier sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ce script nécessite sudo"
    echo "Relancez avec: sudo $0"
    exit 1
fi

# Vérifier que le script de nettoyage existe
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "❌ Script vnc-session-cleanup.sh introuvable dans $SCRIPT_DIR"
    exit 1
fi

# Rendre le script exécutable
chmod +x "$CLEANUP_SCRIPT"

# Créer le LaunchDaemon plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gsgui.vnc.session-cleanup</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$CLEANUP_SCRIPT</string>
    </array>

    <key>StartInterval</key>
    <integer>300</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/vnc-session-cleanup-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/vnc-session-cleanup-stderr.log</string>
</dict>
</plist>
EOF

# Charger le service
echo "📦 Chargement du service..."
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load -w "$PLIST_PATH"

# Vérifier que le service est chargé
sleep 2
if launchctl list | grep -q "com.gsgui.vnc.session-cleanup"; then
    echo "✅ Service installé avec succès !"
    echo ""
    echo "Le service va nettoyer les sessions VNC toutes les 5 minutes"
    echo ""
    echo "📊 Commandes utiles:"
    echo "   - Voir le statut:  sudo launchctl list | grep vnc.session-cleanup"
    echo "   - Voir les logs:   tail -f /tmp/vnc-session-cleanup.log"
    echo "   - Désinstaller:    sudo ./uninstall-vnc-session-cleanup.sh"
    echo ""
    echo "💡 Le service démarre immédiatement et à chaque démarrage du Mac"
else
    echo "❌ Erreur lors de l'installation du service"
    echo "Vérifiez les logs: cat /tmp/vnc-session-cleanup-stderr.log"
    exit 1
fi
