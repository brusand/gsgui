#!/bin/bash

# Wrapper pour launchd
# Ce script est appelé par launchd et lance le process-manager en mode monitor

# Log de démarrage
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Wrapper launchd démarré"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] PATH: $PATH"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] PWD: $(pwd)"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] User: $(whoami)"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Lancement du process-manager..."

# Se placer dans le bon répertoire
cd /Volumes/SSD/devs/gsgui || exit 1

# Lancer le script avec bash explicitement (sans exec pour garder le wrapper actif)
/bin/bash /Volumes/SSD/devs/gsgui/process-manager-portable.sh monitor
