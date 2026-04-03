#!/bin/bash

# Script d'installation du LaunchAgent pour GSGUI
# Ce script configure le démarrage automatique au boot

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Chemins
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.gsgui.manager.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.gsgui.manager.plist"
LABEL="com.gsgui.manager"

echo -e "${BLUE}=== Installation du LaunchAgent GSGUI ===${NC}"

# Vérifier que le fichier plist source existe
if [[ ! -f "$PLIST_SOURCE" ]]; then
    echo -e "${RED}Erreur: Fichier plist non trouvé: $PLIST_SOURCE${NC}"
    exit 1
fi

# Créer le répertoire LaunchAgents s'il n'existe pas
mkdir -p "$HOME/Library/LaunchAgents"
echo -e "${GREEN}Répertoire LaunchAgents créé/vérifié${NC}"

# Décharger le service s'il est déjà chargé
if launchctl list | grep -q "$LABEL"; then
    echo -e "${YELLOW}Service déjà chargé, déchargement...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 2
fi

# Copier le fichier plist
echo -e "${BLUE}Copie du fichier plist...${NC}"
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo -e "${GREEN}Fichier copié vers: $PLIST_DEST${NC}"

# Charger le service
echo -e "${BLUE}Chargement du service...${NC}"
launchctl load "$PLIST_DEST"

# Vérifier que le service est chargé
sleep 2
if launchctl list | grep -q "$LABEL"; then
    echo -e "${GREEN}Service chargé avec succès!${NC}"
    echo -e "${GREEN}Le service démarrera automatiquement à chaque démarrage de session${NC}"
else
    echo -e "${RED}Erreur: Le service n'a pas pu être chargé${NC}"
    exit 1
fi

# Afficher les informations
echo ""
echo -e "${BLUE}=== Informations utiles ===${NC}"
echo -e "${YELLOW}Fichier de configuration:${NC} $PLIST_DEST"
echo -e "${YELLOW}Logs standard:${NC} $SCRIPT_DIR/logs/launchd.out.log"
echo -e "${YELLOW}Logs d'erreur:${NC} $SCRIPT_DIR/logs/launchd.err.log"
echo ""
echo -e "${BLUE}=== Commandes utiles ===${NC}"
echo -e "${YELLOW}Vérifier l'état:${NC} launchctl list | grep $LABEL"
echo -e "${YELLOW}Voir les logs:${NC} tail -f $SCRIPT_DIR/logs/launchd.out.log"
echo -e "${YELLOW}Arrêter le service:${NC} launchctl unload $PLIST_DEST"
echo -e "${YELLOW}Redémarrer le service:${NC} launchctl unload $PLIST_DEST && launchctl load $PLIST_DEST"
echo -e "${YELLOW}Désinstaller:${NC} ./uninstall-launchd.sh"
echo ""
echo -e "${GREEN}Installation terminée!${NC}"
