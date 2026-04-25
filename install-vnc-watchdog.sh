#!/bin/bash

# Script d'installation du watchdog VNC sur le Mac mini
# À lancer depuis votre ordinateur local

echo "🔧 Installation du watchdog VNC sur le Mac mini"
echo ""

# Demander les informations de connexion
read -p "Utilisateur du Mac mini : " MAC_USER
read -p "IP du Mac mini : " MAC_IP

echo ""
echo "📤 Copie des fichiers sur le Mac mini..."

# Copier le script watchdog
scp vnc-watchdog.sh ${MAC_USER}@${MAC_IP}:/tmp/vnc-watchdog.sh
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la copie du script"
    exit 1
fi

# Copier le fichier plist
scp com.gsgui.vnc-watchdog.plist ${MAC_USER}@${MAC_IP}:/tmp/com.gsgui.vnc-watchdog.plist
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la copie du plist"
    exit 1
fi

echo "✅ Fichiers copiés"
echo ""
echo "⚙️  Installation du watchdog..."

# Installer et activer le watchdog via SSH
ssh ${MAC_USER}@${MAC_IP} << 'ENDSSH'
# Déplacer le script dans /usr/local/bin
sudo mv /tmp/vnc-watchdog.sh /usr/local/bin/vnc-watchdog.sh
sudo chmod +x /usr/local/bin/vnc-watchdog.sh

# Déplacer le plist dans LaunchDaemons
sudo mv /tmp/com.gsgui.vnc-watchdog.plist /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist
sudo chown root:wheel /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist
sudo chmod 644 /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist

# Charger le service
sudo launchctl load /Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist

echo ""
echo "✅ Watchdog VNC installé et activé"
echo "   - Vérifie le service toutes les 5 minutes"
echo "   - Logs: /tmp/vnc-watchdog.log"
echo ""
echo "Pour vérifier le statut:"
echo "   sudo launchctl list | grep vnc-watchdog"
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation terminée avec succès !"
    echo ""
    echo "Le watchdog surveille maintenant le service VNC toutes les 5 minutes."
    echo "Si le service ne répond plus, il sera automatiquement relancé."
else
    echo "❌ Erreur lors de l'installation"
    exit 1
fi
