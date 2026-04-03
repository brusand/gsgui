#!/bin/bash

# Script de lancement GSGUI pour Automator
# Configure le PATH complet avant de lancer le process-manager

# Définir le PATH complet (important pour Automator au démarrage)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Log de démarrage
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage de GSGUI Launcher" > /tmp/gsgui-launcher.log 2>&1

# Afficher notification de démarrage
osascript -e 'display notification "Démarrage en cours..." with title "GSGUI Launcher"' >> /tmp/gsgui-launcher.log 2>&1

# Attendre que le disque SSD soit monté
MAX_WAIT=60
waited=0

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attente du montage du disque SSD..." >> /tmp/gsgui-launcher.log 2>&1

while [[ ! -d "/Volumes/SSD/devs/gsgui" ]] && [[ $waited -lt $MAX_WAIT ]]; do
    sleep 5
    waited=$((waited + 5))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attente... ($waited/$MAX_WAIT secondes)" >> /tmp/gsgui-launcher.log 2>&1
done

if [[ ! -d "/Volumes/SSD/devs/gsgui" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR: Le disque SSD n'est pas monté" >> /tmp/gsgui-launcher.log 2>&1
    osascript -e 'display notification "Le disque SSD n'\''est pas monté" with title "GSGUI Launcher" sound name "Basso"' >> /tmp/gsgui-launcher.log 2>&1
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Disque SSD monté avec succès" >> /tmp/gsgui-launcher.log 2>&1

# Vérifier que npm est accessible
if ! command -v npm >/dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR: npm n'est pas trouvé dans le PATH: $PATH" >> /tmp/gsgui-launcher.log 2>&1
    osascript -e 'display notification "npm non trouvé dans le PATH" with title "GSGUI Launcher" sound name "Basso"' >> /tmp/gsgui-launcher.log 2>&1
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] npm trouvé: $(which npm)" >> /tmp/gsgui-launcher.log 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] python3 trouvé: $(which python3)" >> /tmp/gsgui-launcher.log 2>&1

# Lancer le process-manager en mode start
cd "/Volumes/SSD/devs/gsgui"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Lancement du process-manager..." >> /tmp/gsgui-launcher.log 2>&1
/bin/bash ./process-manager-portable.sh start >> /tmp/gsgui-launcher.log 2>&1

# Vérifier le résultat
if [[ $? -eq 0 ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] GSGUI démarré avec succès" >> /tmp/gsgui-launcher.log 2>&1
    osascript -e 'display notification "GSGUI a démarré avec succès" with title "GSGUI Launcher" sound name "Glass"' >> /tmp/gsgui-launcher.log 2>&1
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR: Échec du démarrage" >> /tmp/gsgui-launcher.log 2>&1
    osascript -e 'display notification "Échec du démarrage de GSGUI" with title "GSGUI Launcher" sound name "Basso"' >> /tmp/gsgui-launcher.log 2>&1
    exit 1
fi
