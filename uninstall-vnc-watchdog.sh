#!/bin/bash

# Script de désinstallation du watchdog VNC

echo "🗑️  Désinstallation du watchdog VNC"
echo ""

read -p "Utilisateur du Mac mini : " MAC_USER
read -p "IP du Mac mini : " MAC_IP

echo ""
echo "⚙️  Désinstallation..."

ssh ${MAC_USER}@${MAC_IP} << 'ENDSSH'
# Décharger le service
sudo launchctl unload /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist 2>/dev/null

# Supprimer les fichiers
sudo rm -f /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist
sudo rm -f /usr/local/bin/vnc-watchdog.sh
sudo rm -f /tmp/vnc-watchdog*.log

echo "✅ Watchdog VNC désinstallé"
ENDSSH

echo ""
echo "🎉 Désinstallation terminée"
