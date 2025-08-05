#!/bin/bash

# Script pour arrêter tous les processus GSGUI
# Arrête le backend, frontend et le gestionnaire de processus

set -e

# Configuration
PID_DIR="./pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
MANAGER_PID_FILE="$PID_DIR/manager.pid"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions utilitaires
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

# Vérifier si un processus est en cours d'exécution
is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Arrêter un processus spécifique
stop_process() {
    local pid_file="$1"
    local name="$2"
    
    if is_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        log_info "Arrêt de $name (PID: $pid)..."
        
        # Essayer d'abord SIGTERM (arrêt propre)
        kill "$pid" 2>/dev/null || true
        
        # Attendre jusqu'à 10 secondes pour un arrêt propre
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                log_success "$name arrêté avec succès"
                rm -f "$pid_file"
                return 0
            fi
            sleep 1
        done
        
        # Si toujours en cours, forcer avec SIGKILL
        log_warning "Forçage de l'arrêt de $name..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 2
        
        if ! ps -p "$pid" > /dev/null 2>&1; then
            log_success "$name forcé à s'arrêter"
            rm -f "$pid_file"
            return 0
        else
            log_error "Impossible d'arrêter $name (PID: $pid)"
            return 1
        fi
    else
        log_info "$name n'était pas en cours d'exécution"
        return 0
    fi
}

# Arrêter tous les processus par nom (backup method)
stop_by_name() {
    log_info "Recherche des processus GSGUI restants..."
    
    # Arrêter les processus backend
    local backend_pids=$(pgrep -f "python.*gs_backend.py" 2>/dev/null || true)
    if [ -n "$backend_pids" ]; then
        log_warning "Processus backend trouvés: $backend_pids"
        echo "$backend_pids" | xargs kill -15 2>/dev/null || true
        sleep 2
        echo "$backend_pids" | xargs kill -9 2>/dev/null || true
        log_success "Processus backend nettoyés"
    fi
    
    # Arrêter les processus frontend (npm/vite)
    local frontend_pids=$(pgrep -f "vite" 2>/dev/null || true)
    if [ -n "$frontend_pids" ]; then
        log_warning "Processus frontend trouvés: $frontend_pids"
        echo "$frontend_pids" | xargs kill -15 2>/dev/null || true
        sleep 2
        echo "$frontend_pids" | xargs kill -9 2>/dev/null || true
        log_success "Processus frontend nettoyés"
    fi
    
    # Arrêter les processus npm restants dans le répertoire web-ui
    local npm_pids=$(pgrep -f "npm.*run.*dev" 2>/dev/null || true)
    if [ -n "$npm_pids" ]; then
        log_warning "Processus npm trouvés: $npm_pids"
        echo "$npm_pids" | xargs kill -15 2>/dev/null || true
        sleep 2
        echo "$npm_pids" | xargs kill -9 2>/dev/null || true
        log_success "Processus npm nettoyés"
    fi
}

# Nettoyer les fichiers PID
cleanup_pid_files() {
    log_info "Nettoyage des fichiers PID..."
    rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE" "$MANAGER_PID_FILE"
    log_success "Fichiers PID nettoyés"
}

# Fonction principale
main() {
    echo "🛑 Arrêt de tous les processus GSGUI"
    echo "====================================="
    
    # Créer le répertoire PID s'il n'existe pas
    mkdir -p "$PID_DIR"
    
    # Arrêter le gestionnaire de processus en premier
    stop_process "$MANAGER_PID_FILE" "Gestionnaire de processus"
    
    # Arrêter le backend
    stop_process "$BACKEND_PID_FILE" "Backend"
    
    # Arrêter le frontend
    stop_process "$FRONTEND_PID_FILE" "Frontend"
    
    # Méthode de backup pour s'assurer que tous les processus sont arrêtés
    stop_by_name
    
    # Nettoyer les fichiers PID
    cleanup_pid_files
    
    echo
    log_success "🎉 Tous les processus GSGUI ont été arrêtés avec succès!"
    echo
    echo "Les ports suivants sont maintenant libres:"
    echo "  - Port 8001 (Backend FastAPI)"
    echo "  - Port 3000 (Frontend Vite)"
}

# Vérifier si le script process-manager.sh existe et l'utiliser si possible
if [ -f "process-manager.sh" ]; then
    log_info "Utilisation du gestionnaire de processus pour l'arrêt..."
    chmod +x process-manager.sh
    ./process-manager.sh stop
else
    # Exécuter la fonction principale si process-manager.sh n'existe pas
    main
fi