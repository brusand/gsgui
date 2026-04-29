#!/bin/bash
# Fix VNC Blank Screen - Résout le problème d'écran vide après reconnexion VNC
# Ce script réinitialise le loginwindow et la session d'affichage

echo "🔧 Correction de l'écran VNC vide..."
echo ""

# Vérifier si on est root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ce script nécessite sudo"
    echo "Relancez avec: sudo $0"
    exit 1
fi

# 1. Forcer le logout de toutes les sessions utilisateur (sauf root)
echo "1️⃣  Logout de toutes les sessions utilisateur..."
WHO_OUTPUT=$(who)
if [ -n "$WHO_OUTPUT" ]; then
    echo "   Sessions actives détectées:"
    echo "$WHO_OUTPUT" | sed 's/^/   /'

    # Tuer gentiment les sessions console
    pkill -u $(who | grep console | awk '{print $1}' | head -1) 2>/dev/null
    sleep 2
fi

# 2. Réinitialiser le loginwindow (écran de connexion)
echo "2️⃣  Réinitialisation du loginwindow..."
pkill -HUP loginwindow
sleep 2

# Si ça ne suffit pas, tuer complètement
if pgrep loginwindow > /dev/null; then
    echo "   Force kill du loginwindow..."
    pkill -9 loginwindow
    sleep 2
fi

# 3. Réinitialiser WindowServer (gestion de l'affichage)
echo "3️⃣  Réinitialisation du WindowServer..."
pkill -HUP WindowServer 2>/dev/null
sleep 2

# 4. Nettoyer les connexions VNC zombies
echo "4️⃣  Nettoyage des connexions VNC zombies..."
ZOMBIES=$(netstat -an 2>/dev/null | grep 5900 | grep CLOSE_WAIT | wc -l | tr -d ' ')
echo "   Connexions zombies: $ZOMBIES"

if [ "$ZOMBIES" -gt 10 ]; then
    echo "   ⚠️  Trop de connexions zombies - redémarrage du service VNC..."
    launchctl stop system/com.apple.screensharing
    sleep 2
    pkill -9 screensharingd
    sleep 2
    launchctl start system/com.apple.screensharing
    sleep 3
fi

# 5. Vérification finale
echo ""
echo "5️⃣  Vérification finale..."

# Vérifier que VNC répond
if nc -z localhost 5900 2>/dev/null; then
    echo "   ✅ Service VNC actif (port 5900 ouvert)"
else
    echo "   ⚠️  Port 5900 fermé - redémarrage du VNC..."
    launchctl start system/com.apple.screensharing
    sleep 3
fi

# Vérifier que loginwindow tourne
if pgrep loginwindow > /dev/null; then
    echo "   ✅ Loginwindow actif"
else
    echo "   ⚠️  Loginwindow non trouvé (normal si utilisateur connecté)"
fi

echo ""
echo "✅ Réparation terminée !"
echo ""
echo "📱 Essayez maintenant de vous reconnecter avec VNC Viewer"
echo ""
echo "💡 Si le problème persiste:"
echo "   1. Vérifiez qu'aucun utilisateur n'est connecté physiquement au Mac mini"
echo "   2. Essayez: sudo ./force-restart-vnc.sh"
echo "   3. En dernier recours: redémarrage du Mac mini"
