#!/bin/bash

# Script de désinstallation du LaunchAgent pour GSGUI

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Chemins
PLIST_DEST="$HOME/Library/LaunchAgents/com.gsgui.manager.plist"
LABEL="com.gsgui.manager"

echo -e "${BLUE}=== Désinstallation du LaunchAgent GSGUI ===${NC}"

# Vérifier si le service est chargé
if launchctl list | grep -q "$LABEL"; then
    echo -e "${YELLOW}Déchargement du service...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}Service déchargé${NC}"
else
    echo -e "${YELLOW}Le service n'est pas actuellement chargé${NC}"
fi

# Supprimer le fichier plist
if [[ -f "$PLIST_DEST" ]]; then
    echo -e "${BLUE}Suppression du fichier plist...${NC}"
    rm -f "$PLIST_DEST"
    echo -e "${GREEN}Fichier plist supprimé${NC}"
else
    echo -e "${YELLOW}Le fichier plist n'existe pas${NC}"
fi

# Vérifier que le service n'est plus listé
if launchctl list | grep -q "$LABEL"; then
    echo -e "${RED}Attention: Le service est toujours listé${NC}"
    echo -e "${YELLOW}Essayez de redémarrer votre session${NC}"
else
    echo -e "${GREEN}Service complètement désinstallé!${NC}"
fi

echo ""
echo -e "${BLUE}Désinstallation terminée${NC}"
echo -e "${YELLOW}Note: Les processus backend et frontend peuvent encore être en cours d'exécution${NC}"
echo -e "${YELLOW}Pour les arrêter: ./process-manager-portable.sh stop${NC}"
