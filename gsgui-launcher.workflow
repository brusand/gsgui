# Script de lancement GSGUI
# Attendre que le disque SSD soit monté
MAX_WAIT=60
waited=0

while [[ ! -d "/Volumes/SSD/devs/gsgui" ]] && [[ $waited -lt $MAX_WAIT ]]; do
    sleep 5
    waited=$((waited + 5))
done

if [[ ! -d "/Volumes/SSD/devs/gsgui" ]]; then
    osascript -e 'display notification "Le disque SSD n'\''est pas monté" with title "GSGUI Launcher" sound name "Basso"'
    exit 1
fi

# Lancer le process-manager en mode monitor
cd "/Volumes/SSD/devs/gsgui"
nohup /bin/bash ./process-manager-portable.sh monitor > /dev/null 2>&1 &

# Attendre que les services démarrent
sleep 8

# Notification de succès
osascript -e 'display notification "GSGUI a démarré avec succès" with title "GSGUI Launcher" sound name "Glass"'
