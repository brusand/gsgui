#!/bin/bash

# Script d'installation des dépendances pour GSGUI
# Install backend (Python) et frontend (Node.js) dependencies

set -e  # Arrêter en cas d'erreur

echo "🚀 Installation des dépendances GSGUI"
echo "====================================="

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages colorés
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "gs_backend.py" ] && [ ! -d "backend" ]; then
    log_error "Ce script doit être exécuté depuis la racine du projet GSGUI"
    exit 1
fi

# 1. Installation des dépendances Python (Backend)
echo
log_info "Installation des dépendances Python (Backend)..."

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérifier si pip est installé
if ! command -v pip3 &> /dev/null; then
    log_error "pip3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Installer les dépendances Python
if [ -f "backend/requirements.txt" ]; then
    log_info "Installation des dépendances depuis backend/requirements.txt..."
    pip3 install -r backend/requirements.txt
    log_success "Dépendances Python installées avec succès"
else
    log_warning "Fichier backend/requirements.txt non trouvé"
fi

# 2. Installation des dépendances Node.js (Frontend)
echo
log_info "Installation des dépendances Node.js (Frontend)..."

# Vérifier si Node.js est installé
if ! command -v node &> /dev/null; then
    log_error "Node.js n'est pas installé. Veuillez l'installer d'abord."
    log_info "Vous pouvez l'installer depuis https://nodejs.org/"
    exit 1
fi

# Vérifier si npm est installé
if ! command -v npm &> /dev/null; then
    log_error "npm n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Aller dans le répertoire web-ui et installer les dépendances
if [ -d "web-ui" ]; then
    cd web-ui
    log_info "Installation des dépendances depuis web-ui/package.json..."
    npm install
    log_success "Dépendances Node.js installées avec succès"
    cd ..
else
    log_warning "Répertoire web-ui non trouvé"
fi

# 3. Vérification des installations
echo
log_info "Vérification des installations..."

# Vérifier Python
python3 --version
log_success "Python installé et fonctionnel"

# Vérifier Node.js
node --version
npm --version
log_success "Node.js et npm installés et fonctionnels"

# 4. Création des répertoires nécessaires
log_info "Création des répertoires nécessaires..."

# Créer le répertoire data s'il n'existe pas
if [ ! -d "data" ]; then
    mkdir -p data
    log_success "Répertoire data créé"
fi

# Créer le répertoire logs s'il n'existe pas
if [ ! -d "logs" ]; then
    mkdir -p logs
    log_success "Répertoire logs créé"
fi

# 5. Rendre les scripts exécutables
log_info "Configuration des permissions des scripts..."

chmod +x start-webui.sh 2>/dev/null || true
chmod +x stop-webui.sh 2>/dev/null || true
chmod +x process-manager.sh 2>/dev/null || true

echo
log_success "🎉 Installation terminée avec succès!"
echo
echo "Pour démarrer l'application:"
echo "  ./process-manager.sh start    # Démarrer les serveurs avec surveillance"
echo "  ./start-webui.sh             # Démarrer manuellement"
echo
echo "Pour arrêter l'application:"
echo "  ./process-manager.sh stop     # Arrêter tous les processus"
echo "  ./stop-webui.sh              # Arrêter manuellement"
echo
echo "Backend sera disponible sur: http://localhost:8001"
echo "Frontend sera disponible sur: http://localhost:3000"