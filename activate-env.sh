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
