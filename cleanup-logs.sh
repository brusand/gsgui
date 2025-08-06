#!/bin/bash

# Script pour nettoyer les anciens logs et faire de la place
cd /Users/bruno/gsgui

echo "🧹 Nettoyage des anciens logs..."

# Créer le répertoire logs s'il n'existe pas
mkdir -p logs

# Fonction pour afficher la taille d'un fichier
show_size() {
    if [ -f "$1" ]; then
        ls -lh "$1" | awk '{print $5}'
    else
        echo "0B"
    fi
}

# Fonction pour nettoyer les logs rotatifs anciens (>30 jours)
cleanup_old_rotated() {
    echo "📋 Suppression des logs rotatifs anciens (>30 jours)..."
    find logs/ -name "*.log.[6-9]" -mtime +30 -delete 2>/dev/null || true
    find logs/ -name "*.log.1[0-9]" -mtime +30 -delete 2>/dev/null || true
}

# Afficher les tailles actuelles
echo ""
echo "📊 Taille actuelle des logs:"
echo "   backend.log:  $(show_size logs/backend.log)"
echo "   frontend.log: $(show_size logs/frontend.log)"
echo "   manager.log:  $(show_size logs/manager.log)"

# Nettoyer les anciens logs rotatifs
cleanup_old_rotated

# Compresser les logs anciens de plus de 7 jours
echo ""
echo "🗜️ Compression des logs anciens (>7 jours)..."
find logs/ -name "*.log.[2-5]" -mtime +7 ! -name "*.gz" -exec gzip {} \; 2>/dev/null || true

# Afficher l'espace disque utilisé par les logs
echo ""
echo "💾 Espace disque utilisé par les logs:"
du -sh logs/ 2>/dev/null || echo "   logs/: 0B"

# Afficher les fichiers de logs existants
echo ""
echo "📁 Fichiers de logs actuels:"
ls -lah logs/ | grep -E '\.(log|gz)' | awk '{print "   " $9 " (" $5 ")"}' || echo "   Aucun fichier de log trouvé"

echo ""
echo "✅ Nettoyage terminé"