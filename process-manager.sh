#!/bin/bash

# Script de gestion des processus GSGUI
# Lance, surveille et redémarre automatiquement le backend et frontend

set -e

# Configuration
BACKEND_CMD="python3 gs_backend.py"
FRONTEND_CMD="npm run dev"
BACKEND_DIR="backend"
FRONTEND_DIR="web-ui"
PID_DIR="./pids"
LOG_DIR="./logs"

# Fichiers PID
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
MANAGER_PID_FILE="$PID_DIR/manager.pid"

# Fichiers de log
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
MANAGER_LOG="$LOG_DIR/manager.log"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}" | tee -a "$MANAGER_LOG"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$MANAGER_LOG"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$MANAGER_LOG"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$MANAGER_LOG"
}

# Créer les répertoires nécessaires
setup_directories() {
    mkdir -p "$PID_DIR" "$LOG_DIR"
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

# Démarrer le backend
start_backend() {
    if is_running "$BACKEND_PID_FILE"; then
        log_warning "Backend déjà en cours d'exécution (PID: $(cat $BACKEND_PID_FILE))"
        return 0
    fi
    
    log_info "Démarrage du backend..."
    
    # S'assurer que les répertoires existent
    mkdir -p "$PID_DIR" "$LOG_DIR"
    
    cd "$BACKEND_DIR"
    
    # Démarrer le backend en arrière-plan
    nohup env PYTHONPATH=.. python3 gs_backend.py > "../$BACKEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "../$BACKEND_PID_FILE"
    
    # Retourner au répertoire racine
    cd ..
    
    # Attendre un peu et vérifier que le processus a démarré
    sleep 2
    if is_running "$BACKEND_PID_FILE"; then
        log_success "Backend démarré avec succès (PID: $pid)"
        return 0
    else
        log_error "Échec du démarrage du backend"
        return 1
    fi
}

# Démarrer le frontend
start_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        log_warning "Frontend déjà en cours d'exécution (PID: $(cat $FRONTEND_PID_FILE))"
        return 0
    fi
    
    log_info "Démarrage du frontend..."
    
    # S'assurer que les répertoires existent
    mkdir -p "$PID_DIR" "$LOG_DIR"
    
    cd "$FRONTEND_DIR"
    
    # Démarrer le frontend en arrière-plan
    nohup $FRONTEND_CMD > "../$FRONTEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "../$FRONTEND_PID_FILE"
    
    # Retourner au répertoire racine
    cd ..
    
    # Attendre un peu et vérifier que le processus a démarré
    sleep 3
    if is_running "$FRONTEND_PID_FILE"; then
        log_success "Frontend démarré avec succès (PID: $pid)"
        return 0
    else
        log_error "Échec du démarrage du frontend"
        return 1
    fi
}

# Arrêter un processus
stop_process() {
    local pid_file="$1"
    local name="$2"
    
    if is_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        log_info "Arrêt de $name (PID: $pid)..."
        
        # Essayer d'abord SIGTERM
        kill "$pid" 2>/dev/null || true
        
        # Attendre jusqu'à 10 secondes
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
            log_error "Impossible d'arrêter $name"
            return 1
        fi
    else
        log_info "$name n'est pas en cours d'exécution"
        return 0
    fi
}

# Surveiller les processus
monitor_processes() {
    log_info "Démarrage de la surveillance des processus..."
    echo $$ > "$MANAGER_PID_FILE"
    
    while true; do
        # Vérifier le backend
        if ! is_running "$BACKEND_PID_FILE"; then
            log_warning "Backend arrêté détecté, redémarrage..."
            start_backend
        fi
        
        # Vérifier le frontend
        if ! is_running "$FRONTEND_PID_FILE"; then
            log_warning "Frontend arrêté détecté, redémarrage..."
            start_frontend
        fi
        
        # Attendre avant la prochaine vérification
        sleep 5
    done
}

# Afficher le statut
show_status() {
    echo "=== Statut des processus GSGUI ==="
    
    if is_running "$BACKEND_PID_FILE"; then
        echo -e "${GREEN}✅ Backend: En cours d'exécution (PID: $(cat $BACKEND_PID_FILE))${NC}"
    else
        echo -e "${RED}❌ Backend: Arrêté${NC}"
    fi
    
    if is_running "$FRONTEND_PID_FILE"; then
        echo -e "${GREEN}✅ Frontend: En cours d'exécution (PID: $(cat $FRONTEND_PID_FILE))${NC}"
    else
        echo -e "${RED}❌ Frontend: Arrêté${NC}"
    fi
    
    if is_running "$MANAGER_PID_FILE"; then
        echo -e "${GREEN}✅ Manager: En cours d'exécution (PID: $(cat $MANAGER_PID_FILE))${NC}"
    else
        echo -e "${RED}❌ Manager: Arrêté${NC}"
    fi
    
    echo
    echo "Backend URL: http://localhost:8001"
    echo "Frontend URL: http://localhost:3000"
}

# Fonction d'arrêt propre
cleanup() {
    log_info "Arrêt demandé, nettoyage en cours..."
    stop_process "$BACKEND_PID_FILE" "Backend"
    stop_process "$FRONTEND_PID_FILE" "Frontend"
    rm -f "$MANAGER_PID_FILE"
    log_success "Tous les processus ont été arrêtés"
    exit 0
}

# Gérer les signaux
trap cleanup SIGTERM SIGINT

# Actions principales
case "${1:-start}" in
    "start")
        setup_directories
        log_info "Démarrage de GSGUI avec surveillance..."
        
        # Arrêter les processus existants s'ils existent
        stop_process "$BACKEND_PID_FILE" "Backend"
        stop_process "$FRONTEND_PID_FILE" "Frontend"
        
        # Démarrer les services
        start_backend
        start_frontend
        
        # Afficher le statut initial
        sleep 2
        show_status
        
        # Commencer la surveillance
        monitor_processes
        ;;
        
    "stop")
        setup_directories
        log_info "Arrêt de tous les processus GSGUI..."
        stop_process "$BACKEND_PID_FILE" "Backend"
        stop_process "$FRONTEND_PID_FILE" "Frontend"
        stop_process "$MANAGER_PID_FILE" "Manager"
        log_success "Tous les processus ont été arrêtés"
        ;;
        
    "restart")
        setup_directories
        log_info "Redémarrage de GSGUI..."
        stop_process "$BACKEND_PID_FILE" "Backend"
        stop_process "$FRONTEND_PID_FILE" "Frontend"
        sleep 2
        start_backend
        start_frontend
        show_status
        ;;
        
    "status")
        setup_directories
        show_status
        ;;
        
    "logs")
        echo "=== Logs Backend (10 dernières lignes) ==="
        tail -n 10 "$BACKEND_LOG" 2>/dev/null || echo "Aucun log backend trouvé"
        echo
        echo "=== Logs Frontend (10 dernières lignes) ==="
        tail -n 10 "$FRONTEND_LOG" 2>/dev/null || echo "Aucun log frontend trouvé"
        echo
        echo "=== Logs Manager (10 dernières lignes) ==="
        tail -n 10 "$MANAGER_LOG" 2>/dev/null || echo "Aucun log manager trouvé"
        ;;
        
    "tail")
        echo "Surveillance des logs en temps réel (Ctrl+C pour arrêter)..."
        tail -f "$BACKEND_LOG" "$FRONTEND_LOG" "$MANAGER_LOG" 2>/dev/null || {
            echo "Aucun fichier de log trouvé. Démarrez d'abord l'application."
            exit 1
        }
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|tail}"
        echo
        echo "Commands:"
        echo "  start     - Démarrer les serveurs avec surveillance automatique"
        echo "  stop      - Arrêter tous les processus"
        echo "  restart   - Redémarrer les serveurs"
        echo "  status    - Afficher le statut des processus"
        echo "  logs      - Afficher les derniers logs"
        echo "  tail      - Surveiller les logs en temps réel"
        exit 1
        ;;
esac