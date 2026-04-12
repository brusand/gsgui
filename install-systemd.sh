#!/bin/bash

# Script d'installation du service systemd pour GSGUI (Raspberry Pi / Linux)
# Équivalent de install-launchd.sh sur macOS

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_TEMPLATE="$SCRIPT_DIR/gsgui.service"
SERVICE_NAME="gsgui@$(whoami)"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_USER="$(whoami)"

echo -e "${BLUE}=== Installation du service systemd GSGUI ===${NC}"
echo -e "${BLUE}Utilisateur : $CURRENT_USER${NC}"
echo -e "${BLUE}Répertoire  : $SCRIPT_DIR${NC}"

# Vérifier que le fichier service source existe
if [[ ! -f "$SERVICE_TEMPLATE" ]]; then
    echo -e "${RED}Erreur: Fichier service non trouvé: $SERVICE_TEMPLATE${NC}"
    exit 1
fi

# Vérifier les droits sudo
if [[ $EUID -ne 0 ]]; then
    echo -e "${YELLOW}Ce script nécessite sudo pour installer le service système.${NC}"
    exec sudo "$0" "$@"
fi

# Vérifier que systemd est disponible
if ! command -v systemctl &>/dev/null; then
    echo -e "${RED}Erreur: systemd n'est pas disponible sur ce système.${NC}"
    exit 1
fi

# Vérifier que le repo est bien à l'emplacement attendu
EXPECTED_DIR="/home/$CURRENT_USER/gsgui"
if [[ "$SCRIPT_DIR" != "$EXPECTED_DIR" ]]; then
    echo -e "${YELLOW}Attention: le repo n'est pas dans $EXPECTED_DIR (trouvé: $SCRIPT_DIR)${NC}"
    echo -e "${YELLOW}Le fichier .service sera adapté au chemin réel.${NC}"
fi

# Rendre le process-manager exécutable
chmod +x "$SCRIPT_DIR/process-manager-portable.sh"

# Générer le fichier service en remplaçant %i par l'utilisateur réel
echo -e "${BLUE}Génération du fichier service pour l'utilisateur $CURRENT_USER...${NC}"
ACTUAL_HOME=$(eval echo "~$CURRENT_USER")
sed "s|/home/%i/gsgui|$SCRIPT_DIR|g; s|%i|$CURRENT_USER|g; s|HOME=/home/$CURRENT_USER|HOME=$ACTUAL_HOME|g" \
    "$SERVICE_TEMPLATE" > "$SERVICE_DEST"

echo -e "${GREEN}Fichier service copié vers: $SERVICE_DEST${NC}"

# Recharger systemd
echo -e "${BLUE}Rechargement de systemd...${NC}"
systemctl daemon-reload

# Arrêter le service s'il est déjà actif
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Service déjà actif, arrêt en cours...${NC}"
    systemctl stop "$SERVICE_NAME"
fi

# Activer le démarrage automatique au boot
echo -e "${BLUE}Activation du démarrage automatique...${NC}"
systemctl enable "$SERVICE_NAME"

# Démarrer le service maintenant
echo -e "${BLUE}Démarrage du service...${NC}"
systemctl start "$SERVICE_NAME"

# Vérification
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}Service démarré avec succès!${NC}"
    echo -e "${GREEN}Le service démarrera automatiquement à chaque boot.${NC}"
else
    echo -e "${RED}Erreur: le service n'a pas démarré correctement.${NC}"
    echo -e "${YELLOW}Diagnostic: journalctl -u $SERVICE_NAME -n 20${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=== Commandes utiles ===${NC}"
echo -e "${YELLOW}État :${NC}            systemctl status $SERVICE_NAME"
echo -e "${YELLOW}Logs :${NC}            journalctl -u $SERVICE_NAME -f"
echo -e "${YELLOW}Logs fichier :${NC}    tail -f $SCRIPT_DIR/logs/systemd.log"
echo -e "${YELLOW}Arrêter :${NC}         sudo systemctl stop $SERVICE_NAME"
echo -e "${YELLOW}Redémarrer :${NC}      sudo systemctl restart $SERVICE_NAME"
echo -e "${YELLOW}Désinstaller :${NC}    ./uninstall-systemd.sh"
echo ""
echo -e "${GREEN}Installation terminée!${NC}"
