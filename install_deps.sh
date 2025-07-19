#!/bin/bash

echo "Installation des dépendances pour GuruShots GUI Multi-Profile"
echo "=============================================================="

# Installer les dépendances Python
pip install apscheduler
pip install aiohttp  
pip install configobj
pip install qasync
pip install browser-cookie3

echo ""
echo "✅ Installation terminée!"
echo ""
echo "Pour lancer l'application:"
echo "cd src/gs && python gsui_tabs.py"