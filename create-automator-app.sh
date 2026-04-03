#!/bin/bash

# Script pour créer une application Automator pour lancer GSGUI au démarrage
# Cette méthode contourne les restrictions nosuid des disques externes

APP_NAME="GSGUI Launcher"
APP_PATH="$HOME/Applications/$APP_NAME.app"
GSGUI_DIR="/Volumes/SSD/devs/gsgui"

echo "=== Création de l'application Automator ==="
echo ""
echo "Malheureusement, je ne peux pas créer l'application Automator via script."
echo "Voici les étapes à suivre MANUELLEMENT:"
echo ""
echo "1. Ouvrir 'Automator' (dans /Applications)"
echo ""
echo "2. Choisir 'Application' comme type de document"
echo ""
echo "3. Dans la barre de recherche, chercher 'Exécuter un script shell'"
echo ""
echo "4. Glisser 'Exécuter un script shell' dans la zone de droite"
echo ""
echo "5. Coller ce script:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << 'EOFSCRIPT'
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
/bin/bash ./process-manager-portable.sh monitor > /dev/null 2>&1 &

# Attendre 5 secondes et vérifier que les services démarrent
sleep 5

# Notification de succès
osascript -e 'display notification "GSGUI a démarré avec succès" with title "GSGUI Launcher" sound name "Glass"'
EOFSCRIPT
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "6. Enregistrer l'application:"
echo "   - Fichier > Enregistrer"
echo "   - Nom: $APP_NAME"
echo "   - Emplacement: ~/Applications"
echo "   - Format de fichier: Application"
echo ""
echo "7. Ajouter aux éléments de connexion:"
echo "   - Ouvrir Réglages Système"
echo "   - Aller dans 'Général' > 'Éléments de connexion'"
echo "   - Cliquer sur '+' sous 'Ouvrir à l'ouverture de session'"
echo "   - Sélectionner l'application '$ APP_NAME' dans ~/Applications"
echo "   - Cocher 'Masquer' pour qu'elle se lance en arrière-plan"
echo ""
echo "8. Facultatif - Icône personnalisée:"
echo "   - Faire un clic droit sur l'application"
echo "   - 'Lire les informations'"
echo "   - Glisser une icône sur la petite icône en haut à gauche"
echo ""
echo "=== Alternative: Script de démarrage simple ==="
echo ""
echo "Si vous préférez une solution plus simple, vous pouvez:"
echo "1. Créer un alias du script process-manager-portable.sh"
echo "2. L'ajouter aux éléments de connexion"
echo "3. Exécuter: ./process-manager-portable.sh monitor au démarrage"
echo ""
echo "Commande pour créer l'alias:"
echo "  ln -s '$GSGUI_DIR/process-manager-portable.sh' ~/Desktop/GSGUI-Start.command"
echo "  chmod +x ~/Desktop/GSGUI-Start.command"
echo ""
