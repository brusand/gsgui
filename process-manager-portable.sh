#!/bin/bash

# Script de gestion des processus GSGUI - Version Portable
# Lance, surveille et redémarre automatiquement le backend et frontend
# Compatible: Linux, macOS, Windows (Git Bash/WSL)

set -e

# Détection de l'environnement
detect_environment() {
    # Répertoire du script (portable)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Détection OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        OS="windows"
        PYTHON_CMD="python"
        NPM_CMD="npm.cmd"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PYTHON_CMD="python3"
        NPM_CMD="npm"
    else
        OS="linux"
        PYTHON_CMD="python3"
        NPM_CMD="npm"
    fi
    
    # Le log sera fait après init_config
}

# Configuration (relative au répertoire du script)
init_config() {
    # Détecter si un environnement virtuel existe
    if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
        VENV_PATH="$SCRIPT_DIR/venv/bin/activate"
        PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
    elif [[ -f "$SCRIPT_DIR/venv/Scripts/activate" ]]; then
        VENV_PATH="$SCRIPT_DIR/venv/Scripts/activate"
        PYTHON_CMD="$SCRIPT_DIR/venv/Scripts/python"
    else
        VENV_PATH=""
        # Garder la détection Python originale
    fi
    
    BACKEND_DIR="$SCRIPT_DIR/backend"
    FRONTEND_DIR="$SCRIPT_DIR/web-ui"
    
    BACKEND_CMD="$PYTHON_CMD gs_backend.py"
    FRONTEND_CMD="$NPM_CMD run dev"
    PID_DIR="$SCRIPT_DIR/pids"
    LOG_DIR="$SCRIPT_DIR/logs"
    
    # Fichiers PID
    BACKEND_PID_FILE="$PID_DIR/backend.pid"
    FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
    MANAGER_PID_FILE="$PID_DIR/manager.pid"
    
    # Fichiers de log
    BACKEND_LOG="$LOG_DIR/backend.log"
    FRONTEND_LOG="$LOG_DIR/frontend.log"
    MANAGER_LOG="$LOG_DIR/manager.log"
}

# Couleurs pour les messages (avec détection de support)
init_colors() {
    if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        BLUE='\033[0;34m'
        NC='\033[0m'
    else
        RED=''
        GREEN=''
        YELLOW=''
        BLUE=''
        NC=''
    fi
}

# Fonctions utilitaires
log_info() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1"
    echo -e "${BLUE}${msg}${NC}"
    echo "$msg" >> "$MANAGER_LOG" 2>/dev/null || true
}

log_success() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1"
    echo -e "${GREEN}${msg}${NC}"
    echo "$msg" >> "$MANAGER_LOG" 2>/dev/null || true
}

log_warning() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1"
    echo -e "${YELLOW}${msg}${NC}"
    echo "$msg" >> "$MANAGER_LOG" 2>/dev/null || true
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1"
    echo -e "${RED}${msg}${NC}"
    echo "$msg" >> "$MANAGER_LOG" 2>/dev/null || true
}

# Vérification des prérequis
check_requirements() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Python
    if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
        if [[ "$OS" == "windows" ]]; then
            # Essayer python3 sur Windows
            if command -v python3 >/dev/null 2>&1; then
                PYTHON_CMD="python3"
                log_warning "Python trouvé comme 'python3' au lieu de 'python'"
            else
                log_error "Python n'est pas installé ou pas dans le PATH"
                exit 1
            fi
        else
            # Essayer python sur Linux/macOS
            if command -v python >/dev/null 2>&1; then
                PYTHON_CMD="python"
                log_warning "Python trouvé comme 'python' au lieu de 'python3'"
            else
                log_error "Python n'est pas installé ou pas dans le PATH"
                exit 1
            fi
        fi
    fi
    
    # Vérifier npm
    local npm_test_cmd="$NPM_CMD"
    if [[ "$OS" == "windows" ]]; then
        # Sur Windows, essayer aussi npm sans .cmd
        if ! command -v "$NPM_CMD" >/dev/null 2>&1; then
            if command -v npm >/dev/null 2>&1; then
                NPM_CMD="npm"
                npm_test_cmd="npm"
            fi
        fi
    fi
    
    if ! command -v "$npm_test_cmd" >/dev/null 2>&1; then
        log_error "npm n'est pas installé ou pas dans le PATH"
        exit 1
    fi
    
    # Vérifier les répertoires
    if [[ ! -d "$BACKEND_DIR" ]]; then
        log_error "Répertoire backend non trouvé: $BACKEND_DIR"
        exit 1
    fi
    
    if [[ ! -d "$FRONTEND_DIR" ]]; then
        log_error "Répertoire frontend non trouvé: $FRONTEND_DIR"
        exit 1
    fi
    
    # Vérifier les fichiers principaux
    if [[ ! -f "$BACKEND_DIR/gs_backend.py" ]]; then
        log_error "Fichier backend non trouvé: $BACKEND_DIR/gs_backend.py"
        exit 1
    fi
    
    if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
        log_error "Fichier package.json non trouvé: $FRONTEND_DIR/package.json"
        exit 1
    fi
    
    log_success "Tous les prérequis sont satisfaits"
    log_info "Python: $PYTHON_CMD $(if [[ -n "$VENV_PATH" ]]; then echo "(environnement virtuel)"; else echo "($(command -v "$PYTHON_CMD"))"; fi)"
    log_info "npm: $NPM_CMD ($(command -v "$npm_test_cmd"))"
}

# Créer les répertoires nécessaires
create_directories() {
    mkdir -p "$PID_DIR" "$LOG_DIR"
    log_info "Répertoires créés: $PID_DIR, $LOG_DIR"
}


# Fonction pour tuer un processus de manière portable
kill_process() {
    local pid=$1
    local name=$2
    
    if [[ -z "$pid" ]]; then
        return 0
    fi
    
    # Vérifier si le processus existe
    if ! kill -0 "$pid" 2>/dev/null; then
        log_warning "Processus $name (PID: $pid) n'existe plus"
        return 0
    fi
    
    log_info "Arrêt du processus $name (PID: $pid)..."
    
    # Tentative d'arrêt propre
    if kill -TERM "$pid" 2>/dev/null; then
        # Attendre jusqu'à 10 secondes
        for i in {1..10}; do
            if ! kill -0 "$pid" 2>/dev/null; then
                log_success "Processus $name arrêté proprement"
                return 0
            fi
            sleep 1
        done
        
        # Force kill si toujours actif
        if kill -0 "$pid" 2>/dev/null; then
            log_warning "Arrêt forcé du processus $name"
            kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
}

# Démarrer le backend
start_backend() {
    if [[ -f "$BACKEND_PID_FILE" ]]; then
        local old_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            log_warning "Backend déjà en cours d'exécution (PID: $old_pid)"
            return 0
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    log_info "Démarrage du backend..."
    cd "$BACKEND_DIR"
    
    # Préparer la commande avec environnement virtuel si nécessaire
    local full_cmd
    if [[ -n "$VENV_PATH" ]]; then
        log_info "Utilisation de l'environnement virtuel: $VENV_PATH"
        full_cmd="source '$VENV_PATH' && $BACKEND_CMD"
    else
        full_cmd="$BACKEND_CMD"
    fi
    
    # Démarrer en arrière-plan avec redirection des logs
    nohup bash -c "$full_cmd" >> "$BACKEND_LOG" 2>&1 &
    local backend_pid=$!
    
    echo "$backend_pid" > "$BACKEND_PID_FILE"
    
    # Vérifier que le processus a bien démarré
    sleep 2
    if kill -0 "$backend_pid" 2>/dev/null; then
        log_success "Backend démarré (PID: $backend_pid)"
        cd - >/dev/null
        return 0
    else
        log_error "Échec du démarrage du backend"
        rm -f "$BACKEND_PID_FILE"
        cd - >/dev/null
        return 1
    fi
}

# Démarrer le frontend
start_frontend() {
    if [[ -f "$FRONTEND_PID_FILE" ]]; then
        local old_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            log_warning "Frontend déjà en cours d'exécution (PID: $old_pid)"
            return 0
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    log_info "Démarrage du frontend..."
    cd "$FRONTEND_DIR"
    
    # Vérifier que node_modules existe
    if [[ ! -d "node_modules" ]]; then
        log_info "Installation des dépendances npm..."
        $NPM_CMD install
    fi
    
    # Démarrer en arrière-plan avec redirection des logs
    nohup $FRONTEND_CMD >> "$FRONTEND_LOG" 2>&1 &
    local frontend_pid=$!
    
    echo "$frontend_pid" > "$FRONTEND_PID_FILE"
    
    # Vérifier que le processus a bien démarré
    sleep 3
    if kill -0 "$frontend_pid" 2>/dev/null; then
        log_success "Frontend démarré (PID: $frontend_pid)"
        cd - >/dev/null
        return 0
    else
        log_error "Échec du démarrage du frontend"
        rm -f "$FRONTEND_PID_FILE"
        cd - >/dev/null
        return 1
    fi
}

# Arrêter les processus
stop_processes() {
    log_info "Arrêt des processus..."
    
    # Arrêter le frontend
    if [[ -f "$FRONTEND_PID_FILE" ]]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
        kill_process "$frontend_pid" "frontend"
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Arrêter le backend
    if [[ -f "$BACKEND_PID_FILE" ]]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        kill_process "$backend_pid" "backend"
        rm -f "$BACKEND_PID_FILE"
    fi
    
    log_success "Tous les processus ont été arrêtés"
}

# Vérifier l'état des processus
check_processes() {
    local backend_running=false
    local frontend_running=false
    
    # Vérifier le backend
    if [[ -f "$BACKEND_PID_FILE" ]]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
            backend_running=true
            log_success "Backend actif (PID: $backend_pid)"
        else
            log_warning "Backend arrêté (PID file existe mais processus mort)"
            rm -f "$BACKEND_PID_FILE"
        fi
    else
        log_warning "Backend arrêté (pas de PID file)"
    fi
    
    # Vérifier le frontend
    if [[ -f "$FRONTEND_PID_FILE" ]]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
        if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
            frontend_running=true
            log_success "Frontend actif (PID: $frontend_pid)"
        else
            log_warning "Frontend arrêté (PID file existe mais processus mort)"
            rm -f "$FRONTEND_PID_FILE"
        fi
    else
        log_warning "Frontend arrêté (pas de PID file)"
    fi
    
    # Retourner les états
    if $backend_running && $frontend_running; then
        return 0  # Tout va bien
    elif $backend_running || $frontend_running; then
        return 1  # Partiellement en cours
    else
        return 2  # Tout arrêté
    fi
}

# Surveillance et redémarrage automatique
monitor_processes() {
    log_info "Démarrage de la surveillance automatique..."
    echo $$ > "$MANAGER_PID_FILE"
    
    # Gestionnaire de signal pour arrêt propre
    trap 'log_info "Signal reçu, arrêt de la surveillance..."; stop_processes; rm -f "$MANAGER_PID_FILE"; exit 0' SIGTERM SIGINT
    
    while true; do
        check_processes
        local status=$?
        
        case $status in
            0)
                # Tout va bien, attendre
                sleep 10
                ;;
            1)
                # Partiellement en cours, redémarrer ce qui manque
                log_warning "Détection de processus manquant, redémarrage..."
                
                if [[ ! -f "$BACKEND_PID_FILE" ]] || ! kill -0 "$(cat "$BACKEND_PID_FILE" 2>/dev/null)" 2>/dev/null; then
                    start_backend
                fi
                
                if [[ ! -f "$FRONTEND_PID_FILE" ]] || ! kill -0 "$(cat "$FRONTEND_PID_FILE" 2>/dev/null)" 2>/dev/null; then
                    start_frontend
                fi
                
                sleep 5
                ;;
            2)
                # Tout arrêté, redémarrer tout
                log_error "Tous les processus sont arrêtés, redémarrage complet..."
                start_backend
                sleep 3
                start_frontend
                sleep 5
                ;;
        esac
    done
}

# Afficher l'aide
show_help() {
    echo "Usage: $0 [COMMANDE]"
    echo ""
    echo "Commandes disponibles:"
    echo "  start     - Démarrer les services (défaut)"
    echo "  stop      - Arrêter tous les services"
    echo "  restart   - Redémarrer tous les services"
    echo "  status    - Afficher l'état des services"
    echo "  monitor   - Surveiller et redémarrer automatiquement"
    echo "  logs      - Afficher les logs en temps réel"
    echo "  help      - Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                # Démarre les services"
    echo "  $0 monitor        # Démarre avec surveillance"
    echo "  $0 status         # Vérifie l'état"
    echo "  $0 stop           # Arrête tout"
}

# Afficher les logs en temps réel
show_logs() {
    log_info "Affichage des logs en temps réel (Ctrl+C pour arrêter)..."
    
    if command -v tail >/dev/null 2>&1; then
        # Utiliser tail si disponible
        tail -f "$BACKEND_LOG" "$FRONTEND_LOG" "$MANAGER_LOG" 2>/dev/null || \
        tail -f "$MANAGER_LOG" 2>/dev/null || \
        echo "Aucun fichier de log disponible"
    else
        # Fallback simple
        echo "Commande 'tail' non disponible. Contenu actuel des logs:"
        echo "=== Backend Log ==="
        cat "$BACKEND_LOG" 2>/dev/null || echo "Pas de log backend"
        echo "=== Frontend Log ==="
        cat "$FRONTEND_LOG" 2>/dev/null || echo "Pas de log frontend"
        echo "=== Manager Log ==="
        cat "$MANAGER_LOG" 2>/dev/null || echo "Pas de log manager"
    fi
}

# Point d'entrée principal
main() {
    # Initialisation
    init_colors
    detect_environment
    init_config
    log_info "Détection: OS=$OS, Script dir=$SCRIPT_DIR"
    create_directories
    
    # Traitement des arguments
    local command="${1:-start}"
    
    case "$command" in
        "start")
            check_requirements
            log_info "=== Démarrage des services GSGUI ==="
            start_backend
            sleep 3
            start_frontend
            log_success "=== Tous les services sont démarrés ==="
            log_info "Utilisez '$0 status' pour vérifier l'état"
            log_info "Utilisez '$0 monitor' pour surveillance automatique"
            ;;
        "stop")
            log_info "=== Arrêt des services GSGUI ==="
            stop_processes
            rm -f "$MANAGER_PID_FILE"
            ;;
        "restart")
            log_info "=== Redémarrage des services GSGUI ==="
            stop_processes
            sleep 2
            check_requirements
            start_backend
            sleep 3
            start_frontend
            log_success "=== Redémarrage terminé ==="
            ;;
        "status")
            log_info "=== État des services GSGUI ==="
            check_processes
            local status=$?
            case $status in
                0) log_success "Tous les services sont actifs" ;;
                1) log_warning "Certains services sont arrêtés" ;;
                2) log_error "Tous les services sont arrêtés" ;;
            esac
            ;;
        "monitor")
            check_requirements
            log_info "=== Démarrage avec surveillance automatique ==="
            
            # Démarrer les services si nécessaire
            check_processes
            if [[ $? -ne 0 ]]; then
                start_backend
                sleep 3
                start_frontend
                sleep 2
            fi
            
            # Démarrer la surveillance
            monitor_processes
            ;;
        "logs")
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Commande inconnue: $command"
            show_help
            exit 1
            ;;
    esac
}

# Lancer le script
main "$@"
