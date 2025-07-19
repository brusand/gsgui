#!/usr/bin/env python3
"""
Test script pour vérifier que l'application multi-profil fonctionne
"""

import sys
import os
sys.path.append('src/gs')

# Importer l'application
from gsui_tabs import main

print("🚀 Lancement de l'application multi-profil GuruShots GUI")
print("=" * 60)
print()
print("Instructions de test:")
print("1. L'application devrait s'ouvrir avec les profils existants")
print("2. Chaque profil devrait avoir son propre onglet")
print("3. Cliquer sur 'Refresh' pour tester le fetch des challenges")
print("4. Cliquer sur 'Debug Fetch' pour voir les logs détaillés")
print("5. Si pas de token configuré, des challenges de test apparaîtront")
print()
print("Appuyez sur Ctrl+C pour fermer l'application")
print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Application fermée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()