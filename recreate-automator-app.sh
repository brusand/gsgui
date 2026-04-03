#!/bin/bash

# Script pour recréer l'application Automator GSGUI Launcher
# avec le bon PATH pour que npm soit trouvé au démarrage

set -e

APP_NAME="GSGUI Launcher"
APP_PATH="$HOME/Applications/$APP_NAME.app"
WORKFLOW_PATH="/tmp/gsgui-launcher-workflow.workflow"
SCRIPT_PATH="/Volumes/SSD/devs/gsgui/automator-launcher.sh"

echo "🔧 Création de l'application GSGUI Launcher..."

# Supprimer l'ancienne application si elle existe
if [[ -d "$APP_PATH" ]]; then
    echo "📦 Suppression de l'ancienne application..."
    rm -rf "$APP_PATH"
fi

# Créer un workflow Automator temporaire
echo "📝 Création du workflow Automator..."

cat > /tmp/create-workflow.applescript <<'EOF'
tell application "Automator"
    set newWorkflow to make new workflow
    tell newWorkflow
        -- Ajouter une action "Exécuter un script shell"
        set shellAction to make new action with properties {name:"Run Shell Script"}
        tell shellAction
            set value of setting "COMMAND_STRING" to "/bin/bash /Volumes/SSD/devs/gsgui/automator-launcher.sh"
            set value of setting "inputMethod" to 0
            set value of setting "shell" to "/bin/bash"
        end tell
    end tell
    save newWorkflow in POSIX file "/tmp/gsgui-launcher-temp.workflow"
    close newWorkflow
end tell
EOF

osascript /tmp/create-workflow.applescript

# Convertir le workflow en application
echo "🎯 Conversion en application..."
automator -i /tmp/gsgui-launcher-temp.workflow -o "$APP_PATH"

# Nettoyer
rm -f /tmp/create-workflow.applescript
rm -rf /tmp/gsgui-launcher-temp.workflow

echo "✅ Application créée : $APP_PATH"

# Vérifier si l'application est dans les éléments de connexion
echo "🔍 Vérification des éléments de connexion..."
LOGIN_ITEMS=$(osascript -e 'tell application "System Events" to get the name of every login item')

if [[ "$LOGIN_ITEMS" == *"$APP_NAME"* ]]; then
    echo "✅ '$APP_NAME' est déjà dans les éléments de connexion"
else
    echo "➕ Ajout de '$APP_NAME' aux éléments de connexion..."
    osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$APP_PATH\", hidden:true}"
    echo "✅ Ajouté aux éléments de connexion"
fi

echo ""
echo "🎉 Configuration terminée !"
echo ""
echo "Pour tester maintenant:"
echo "  1. Arrêter les services: ./process-manager-portable.sh stop"
echo "  2. Lancer l'application: open \"$APP_PATH\""
echo "  3. Vérifier les logs: cat /tmp/gsgui-launcher.log"
echo "  4. Vérifier les services: ./process-manager-portable.sh status"
echo ""
echo "L'application se lancera automatiquement au prochain démarrage de votre Mac."
