#!/usr/bin/env python3
"""
Script de test pour reproduire le problème de changement de profil
"""
import sys
import os

# Ajouter le chemin vers le module gsui_enhanced
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'gs'))

def test_profile_switching():
    """Test du changement de profil avec logs de debug"""
    print("🧪 Test de changement de profil")
    print("=" * 50)
    
    try:
        from PySide6.QtWidgets import QApplication
        from gsui_enhanced import EnhancedGSGUI
        
        print("📱 Création de l'application Qt")
        app = QApplication(sys.argv)
        
        print("🖥️ Création de la fenêtre GSGUI")
        window = EnhancedGSGUI("bruno")  # Démarrer avec bruno
        window.show()
        
        print("✅ Application prête")
        print("📋 Instructions:")
        print("   1. Attendez que l'interface se charge")
        print("   2. Cliquez sur le bouton rouge '🚪 Déconnexion'")
        print("   3. Sélectionnez un autre profil (caloune)")
        print("   4. Observez les logs de debug dans le terminal")
        print("   5. Vérifiez s'il y a une sortie violente")
        print()
        print("🔍 Surveillez les messages [DEBUG] pour identifier le problème")
        print("=" * 50)
        
        # Lancer l'application
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    test_profile_switching()