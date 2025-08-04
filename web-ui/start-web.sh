#!/bin/bash

echo "🚀 Démarrage de l'interface web GSGUI..."

# Vérifier que le build existe
if [ ! -d "dist" ]; then
    echo "📦 Build de l'application..."
    npm run build
fi

echo "🌐 Démarrage du serveur web sur http://localhost:3000"
echo "📝 L'interface GSGUI sera accessible dans votre navigateur"
echo ""
echo "⚡ Pour tester avec le backend :"
echo "   1. Démarrez le backend : ./start_backend.sh (dans le dossier parent)"
echo "   2. Ouvrez http://localhost:3000 dans votre navigateur"
echo ""

cd dist && python3 -m http.server 3000