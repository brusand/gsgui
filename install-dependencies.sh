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

# Installer les dépendances Python avec environnement virtuel
if [ -f "backend/requirements.txt" ]; then
    log_info "Installation des dépendances depuis backend/requirements.txt..."
    
    # Vérifier si on est dans un environnement virtuel
    if [[ -z "$VIRTUAL_ENV" ]]; then
        log_info "Création d'un environnement virtuel Python..."
        
        # Créer l'environnement virtuel
        if ! python3 -m venv venv 2>/dev/null; then
            # Fallback: essayer avec --user si venv échoue
            log_warning "Création d'environnement virtuel échoué, essai installation avec --user..."
            
            # Essayer d'abord les dépendances compatibles
            if [[ -f "backend/requirements-compatible.txt" ]]; then
                log_info "Tentative avec requirements-compatible.txt (versions flexibles)..."
                if pip3 install --user -r backend/requirements-compatible.txt; then
                    log_success "Dépendances Python compatibles installées avec --user"
                else
                    log_warning "Échec avec requirements-compatible.txt, essai avec minimal..."
                    if [[ -f "backend/requirements-minimal.txt" ]] && pip3 install --user -r backend/requirements-minimal.txt; then
                        log_success "Dépendances Python minimales installées avec --user"
                    else
                        log_error "Échec installation dépendances"
                        return 1
                    fi
                fi
            elif [[ -f "backend/requirements-minimal.txt" ]]; then
                log_info "Tentative avec requirements-minimal.txt (sans PostgreSQL)..."
                if pip3 install --user -r backend/requirements-minimal.txt; then
                    log_success "Dépendances Python minimales installées avec --user"
                else
                    log_error "Échec installation dépendances minimales"
                    return 1
                fi
            else
                pip3 install --user -r backend/requirements.txt
                log_success "Dépendances Python installées avec --user"
            fi
        else
            log_success "Environnement virtuel créé dans ./venv"
            
            # Activer l'environnement virtuel
            if [[ -f "venv/bin/activate" ]]; then
                source venv/bin/activate
                log_success "Environnement virtuel activé"
            elif [[ -f "venv/Scripts/activate" ]]; then
                # Windows Git Bash
                source venv/Scripts/activate
                log_success "Environnement virtuel activé (Windows)"
            else
                log_error "Impossible d'activer l'environnement virtuel"
                exit 1
            fi
            
            # Mettre à jour pip et installer
            python -m pip install --upgrade pip --quiet
            
            # Essayer d'abord requirements-compatible.txt si disponible
            if [[ -f "backend/requirements-compatible.txt" ]]; then
                log_info "Installation avec requirements-compatible.txt (versions flexibles)..."
                if python -m pip install -r backend/requirements-compatible.txt; then
                    log_success "Dépendances Python compatibles installées dans l'environnement virtuel"
                else
                    log_warning "Échec avec requirements-compatible.txt, essai avec minimal..."
                    if [[ -f "backend/requirements-minimal.txt" ]] && python -m pip install -r backend/requirements-minimal.txt; then
                        log_success "Dépendances Python minimales installées dans l'environnement virtuel"
                    else
                        log_warning "Échec avec versions allégées, essai avec requirements.txt complet..."
                        python -m pip install -r backend/requirements.txt
                        log_success "Dépendances Python complètes installées dans l'environnement virtuel"
                    fi
                fi
            elif [[ -f "backend/requirements-minimal.txt" ]]; then
                log_info "Installation avec requirements-minimal.txt (recommandé)..."
                if python -m pip install -r backend/requirements-minimal.txt; then
                    log_success "Dépendances Python minimales installées dans l'environnement virtuel"
                else
                    log_warning "Échec avec requirements-minimal.txt, essai avec requirements.txt complet..."
                    python -m pip install -r backend/requirements.txt
                    log_success "Dépendances Python complètes installées dans l'environnement virtuel"
                fi
            else
                python -m pip install -r backend/requirements.txt
                log_success "Dépendances Python installées dans l'environnement virtuel"
            fi
            
            # Créer un script d'activation
            cat > activate-env.sh << 'EOF'
#!/bin/bash
# Script d'activation de l'environnement virtuel GSGUI
echo "🐍 Activation de l'environnement virtuel GSGUI..."
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
    echo "✅ Environnement virtuel activé"
elif [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
    echo "✅ Environnement virtuel activé (Windows)"
else
    echo "❌ Environnement virtuel non trouvé"
    exit 1
fi
EOF
            chmod +x activate-env.sh
            log_info "Script d'activation créé: ./activate-env.sh"
        fi
    else
        log_info "Environnement virtuel déjà actif: $VIRTUAL_ENV"
        python -m pip install -r backend/requirements.txt
        log_success "Dépendances Python installées"
    fi
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