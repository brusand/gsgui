#!/bin/bash

#=============================================================================
# GuruShots Adaptive Collection Scheduler Launcher  
# Système adaptatif avec stratégies configurables et reprogrammation dynamique
#=============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_SCRIPT="$SCRIPT_DIR/adaptive_collector.py"
STRATEGIES_FILE="$SCRIPT_DIR/collection_strategies.ini"
PIDFILE="$SCRIPT_DIR/adaptive_collector.pid"
LOGFILE="$SCRIPT_DIR/adaptive_collector.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

is_running() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PIDFILE"
            return 1
        fi
    else
        return 1
    fi
}

start_collector() {
    if is_running; then
        local pid=$(cat "$PIDFILE")
        echo -e "${YELLOW}⚠️  Adaptive Collector déjà en marche (PID: $pid)${NC}"
        return 0
    fi

    if [ ! -f "$COLLECTOR_SCRIPT" ]; then
        error "Script collector non trouvé: $COLLECTOR_SCRIPT"
        return 1
    fi

    if [ ! -f "$STRATEGIES_FILE" ]; then
        error "Fichier de stratégies non trouvé: $STRATEGIES_FILE"
        return 1
    fi

    echo -e "${BLUE}🎯 DÉMARRAGE ADAPTIVE COLLECTION SCHEDULER${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    info "🔧 Configuration:"
    info "   • Script: $COLLECTOR_SCRIPT"
    info "   • Stratégies: $STRATEGIES_FILE"
    info "   • Base de données: /Volumes/SSD/Data/GuruShots/gurushots_adaptive.db"
    info "   • Logs: $LOGFILE"
    info "   • PID: $PIDFILE"
    echo ""
    
    info "⚙️  Fonctionnalités du système adaptatif:"
    info "   ✅ Reprogrammation dynamique après chaque collecte"
    info "   ✅ Stratégies configurables par fichier INI"
    info "   ✅ Une seule tâche programmée à la fois par challenge"
    info "   ✅ Adaptation au temps restant RÉEL du challenge"
    info "   ✅ Intégration des méthodes de parsing du backend"
    echo ""
    
    info "📋 Stratégies chargées:"
    if [ -f "$STRATEGIES_FILE" ]; then
        while IFS= read -r line; do
            if [[ $line =~ ^\[.*\]$ ]]; then
                strategy_name=$(echo "$line" | sed 's/\[//g' | sed 's/\]//g')
                info "   📊 $strategy_name"
            elif [[ $line =~ ^description= ]]; then
                description=$(echo "$line" | sed 's/description=//g' | sed 's/"//g')
                info "      → $description"
            elif [[ $line =~ ^0= ]]; then
                action_line=$(echo "$line" | sed 's/0=//g' | sed 's/"//g')
                info "      → $action_line"
            fi
        done < "$STRATEGIES_FILE"
    fi
    echo ""
    
    log "🚀 Démarrage du collector adaptatif..."

    # Activer le venv et démarrer en arrière-plan
    VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
    if [ ! -f "$VENV_PYTHON" ]; then
        error "Python venv non trouvé: $VENV_PYTHON"
        return 1
    fi

    nohup "$VENV_PYTHON" "$COLLECTOR_SCRIPT" > "$LOGFILE" 2>&1 &
    local pid=$!
    
    # Sauvegarder le PID
    echo "$pid" > "$PIDFILE"
    
    # Attendre pour vérifier le démarrage
    sleep 3
    
    if is_running; then
        log "✅ Adaptive Collector démarré avec succès (PID: $pid)"
        echo ""
        info "📊 Pour surveiller l'activité:"
        info "   tail -f $LOGFILE"
        echo ""
        info "🎯 Avantages du système adaptatif:"
        info "   ✅ EFFICACE: Une seule tâche par challenge"
        info "   ✅ RÉACTIF: S'adapte au temps restant réel"
        info "   ✅ FLEXIBLE: Stratégies configurables"
        info "   ✅ ROBUSTE: Résistant aux changements d'horaires"
        echo ""
        return 0
    else
        error "Échec du démarrage du collector"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_collector() {
    if ! is_running; then
        echo -e "${YELLOW}⚠️  Adaptive Collector n'est pas en marche${NC}"
        return 0
    fi

    local pid=$(cat "$PIDFILE")
    log "🛑 Arrêt du collector adaptatif (PID: $pid)..."
    
    # Arrêt gracieux
    kill -TERM "$pid" 2>/dev/null
    
    # Attendre l'arrêt gracieux
    local count=0
    while [ $count -lt 10 ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
    done
    
    # Forcer l'arrêt si nécessaire
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Arrêt forcé nécessaire${NC}"
        kill -KILL "$pid" 2>/dev/null
    fi
    
    # Nettoyer
    rm -f "$PIDFILE"
    log "✅ Adaptive Collector arrêté"
}

show_status() {
    echo ""
    echo -e "${BLUE}=== ADAPTIVE COLLECTION SCHEDULER STATUS ===${NC}"
    echo ""
    
    if is_running; then
        local pid=$(cat "$PIDFILE")
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | xargs)
        echo -e "📊 Status: ${GREEN}EN MARCHE${NC} (PID: $pid, Uptime: $uptime)"
    else
        echo -e "📊 Status: ${RED}ARRÊTÉ${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}=== FILES ===${NC}"
    echo "📝 Log: $LOGFILE"
    echo "📋 Stratégies: $STRATEGIES_FILE"
    echo "🗄️  Database: /Volumes/SSD/Data/GuruShots/gurushots_adaptive.db"
    echo "📋 PID: $PIDFILE"
    
    if [ -f "$LOGFILE" ]; then
        local log_size=$(du -h "$LOGFILE" | cut -f1)
        local last_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOGFILE" 2>/dev/null)
        echo "📊 Log: $log_size (modifié: $last_modified)"
    fi
    
    echo ""
    echo -e "${BLUE}=== STRATÉGIES CONFIGURÉES ===${NC}"
    if [ -f "$STRATEGIES_FILE" ]; then
        while IFS= read -r line; do
            if [[ $line =~ ^\[.*\]$ ]]; then
                strategy_name=$(echo "$line" | sed 's/\[//g' | sed 's/\]//g')
                echo -e "   📊 ${GREEN}$strategy_name${NC}"
            elif [[ $line =~ ^description= ]]; then
                description=$(echo "$line" | sed 's/description=//g' | sed 's/"//g')
                echo "      → $description"
            elif [[ $line =~ ^0= ]]; then
                action_line=$(echo "$line" | sed 's/0=//g' | sed 's/"//g')
                echo "      → $action_line"
            fi
        done < "$STRATEGIES_FILE"
    else
        echo "  ❌ Fichier de stratégies non trouvé"
    fi
    
    echo ""
    echo -e "${BLUE}=== ACTIVITÉ RÉCENTE ===${NC}"
    if [ -f "$LOGFILE" ]; then
        echo "📋 Dernières 8 lignes:"
        tail -8 "$LOGFILE" | while read line; do
            echo "  $line"
        done
    else
        echo "  Aucun log disponible"
    fi
    echo ""
}

edit_strategies() {
    echo -e "${BLUE}📋 ÉDITION DES STRATÉGIES${NC}"
    echo ""
    
    if [ ! -f "$STRATEGIES_FILE" ]; then
        error "Fichier de stratégies non trouvé: $STRATEGIES_FILE"
        return 1
    fi
    
    echo "Ouverture de $STRATEGIES_FILE..."
    
    # Détecter l'éditeur disponible
    if command -v nano >/dev/null 2>&1; then
        nano "$STRATEGIES_FILE"
    elif command -v vi >/dev/null 2>&1; then
        vi "$STRATEGIES_FILE"
    else
        echo "📝 Contenu actuel du fichier:"
        cat "$STRATEGIES_FILE"
        echo ""
        echo "❌ Aucun éditeur disponible (nano, vi)"
        return 1
    fi
    
    echo ""
    log "✅ Stratégies modifiées. Redémarrez le collector pour appliquer les changements."
}

show_comparison() {
    echo ""
    echo -e "${BLUE}=== COMPARAISON DES APPROCHES ===${NC}"
    echo ""
    echo -e "${RED}❌ APPROCHE ABSOLUE (précédente)${NC}:"
    echo "   • 8553 tâches programmées à l'avance"
    echo "   • Rigide, ne s'adapte pas aux changements"
    echo "   • Consommation mémoire élevée"
    echo "   • Difficile à modifier en cours de route"
    echo ""
    echo -e "${GREEN}✅ APPROCHE ADAPTATIVE (actuelle)${NC}:"
    echo "   • Une seule tâche par challenge à la fois"
    echo "   • Reprogrammation dynamique après chaque collecte"
    echo "   • S'adapte au temps restant RÉEL"
    echo "   • Stratégies configurables via fichier INI"
    echo ""
    echo -e "${BLUE}📊 LOGIQUE DE FONCTIONNEMENT:${NC}"
    echo "   1️⃣ Collecte → Récupère time_left réel du challenge"
    echo "   2️⃣ Évalue → Quelle stratégie correspond au temps restant?"
    echo "   3️⃣ Programme → Prochaine collecte selon la stratégie"
    echo "   4️⃣ Répète → À chaque collecte, réévalue et reprogramme"
    echo ""
    echo -e "${BLUE}🎯 PHASES ADAPTATIVES:${NC}"
    echo "   🟢 collecte-till-1h: every 15min (jusqu'à 1h de la fin)"
    echo "   🟡 collecte-last-hour: every 5min (1h → 10min avant fin)"
    echo "   🟠 collecte-last-10-minutes: every 1min (10min → 1min avant fin)"
    echo "   🔴 collecte-last-1-minute: every 10s (1min → fin)"
    echo ""
}

show_logs() {
    local lines=${1:-50}
    
    if [ ! -f "$LOGFILE" ]; then
        echo -e "${YELLOW}⚠️  Aucun log disponible${NC}"
        return
    fi
    
    echo -e "${BLUE}=== LOGS ADAPTIVE COLLECTOR (dernières $lines lignes) ===${NC}"
    tail -n "$lines" "$LOGFILE"
}

case "$1" in
    start)
        start_collector
        ;;
    stop)
        stop_collector
        ;;
    restart)
        log "🔄 Redémarrage du collector adaptatif..."
        stop_collector
        sleep 2
        start_collector
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    tail)
        if [ ! -f "$LOGFILE" ]; then
            echo -e "${YELLOW}⚠️  Aucun log disponible${NC}"
            exit 1
        fi
        echo "Following adaptive collector logs (Ctrl+C to stop)..."
        tail -f "$LOGFILE"
        ;;
    edit|strategies)
        edit_strategies
        ;;
    compare|comparison)
        show_comparison
        ;;
    test)
        echo -e "${BLUE}🧪 Test des stratégies${NC}"
        python3 -c "
import sys
sys.path.append('$SCRIPT_DIR')
from adaptive_collector import AdaptiveCollectionScheduler, CollectionConfig

config = CollectionConfig(
    database_path='./test_adaptive.db',
    bruno_token='test_token',
    strategies_file='$STRATEGIES_FILE'
)

scheduler = AdaptiveCollectionScheduler(config)
print(f'✅ {len(scheduler.strategies)} stratégies chargées')

# Test des temps
test_cases = [
    (7200, '2h restantes'),
    (3600, '1h restante'),  
    (1800, '30min restantes'),
    (300, '5min restantes'),
    (30, '30s restantes')
]

for seconds, description in test_cases:
    strategy = scheduler.find_active_strategy(seconds)
    if strategy:
        print(f'📊 {description}: {strategy.name} ({strategy.interval})')
    else:
        print(f'❌ {description}: Aucune stratégie')
"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [lines]|tail|edit|compare|test}"
        echo ""
        echo "Commands:"
        echo "  start          Démarrer l'adaptive collector"
        echo "  stop           Arrêter le collector"
        echo "  restart        Redémarrer le collector"
        echo "  status         Afficher le statut détaillé"
        echo "  logs [lines]   Afficher les logs (défaut: 50 lignes)"
        echo "  tail           Suivre les logs en temps réel"
        echo "  edit           Éditer les stratégies de collecte"
        echo "  compare        Comparaison absolue vs adaptative"
        echo "  test           Tester le parsing des stratégies"
        echo ""
        echo "Examples:"
        echo "  $0 start                 # Démarrer"
        echo "  $0 status                # Vérifier le statut"
        echo "  $0 edit                  # Modifier les stratégies"
        echo "  $0 compare               # Voir les différences"
        echo "  $0 test                  # Tester les stratégies"
        exit 1
        ;;
esac