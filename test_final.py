#!/usr/bin/env python3
"""
Test de la version finale
"""

import sys
import time
import requests
from PySide6.QtWidgets import QApplication
from gsui_final import FinalGSGUI, FinalApiClient

def test_api():
    """Test direct de l'API"""
    print("🔍 Test API direct...")
    
    client = FinalApiClient()
    token = "a1cad95a6d480c14f51dd0eba4914c8337b893c789ec6278bb440c7c9a673b162f042470c62684e6da2bd342ffea7777"
    
    try:
        challenges = client.get_challenges(token)
        print(f"✅ Challenges reçus: {len(challenges)}")
        
        if challenges:
            print("📋 Premier challenge:")
            ch = challenges[0]
            print(f"  ID: {ch.get('id')}")
            print(f"  Titre: {ch.get('title')}")
            print(f"  Votes: {ch.get('votes')}")
            
        return len(challenges) > 0
    except Exception as e:
        print(f"❌ Erreur API: {e}")
        return False

def test_ui():
    """Test interface"""
    print("\n🎨 Test interface...")
    
    app = QApplication(sys.argv)
    window = FinalGSGUI()
    window.show()
    
    print("Interface créée, simulons refresh...")
    
    # Variables pour capturer le résultat
    result_received = False
    challenges_count = 0
    
    def on_result(challenges):
        nonlocal result_received, challenges_count
        result_received = True
        challenges_count = len(challenges)
        print(f"✅ Callback reçu: {challenges_count} challenges")
    
    def on_error(error):
        nonlocal result_received
        result_received = True
        print(f"❌ Erreur callback: {error}")
    
    # Connecter les callbacks
    window.api_thread = None
    
    # Refresh
    window.refresh_challenges()
    
    # Attendre le résultat
    max_wait = 10
    waited = 0
    while not result_received and waited < max_wait:
        app.processEvents()
        time.sleep(0.1)
        waited += 0.1
    
    if result_received:
        print(f"✅ Interface: {challenges_count} challenges")
        if challenges_count > 0:
            item = window.challenge_list.item(0)
            if item:
                print(f"  Premier: {item.text()}")
    else:
        print("❌ Timeout - pas de réponse")
    
    app.quit()
    return challenges_count > 0

def main():
    print("🧪 TEST FINAL - GSGUI Sans SSL")
    print("=" * 40)
    
    # Test 1: API direct
    api_ok = test_api()
    
    # Test 2: Interface
    ui_ok = test_ui()
    
    print("\n" + "=" * 40)
    print("🎯 RÉSULTATS:")
    print(f"  API direct: {'✅' if api_ok else '❌'}")
    print(f"  Interface:  {'✅' if ui_ok else '❌'}")
    
    if api_ok and ui_ok:
        print("\n🎉 TOUT FONCTIONNE !")
        print("Lance: python gsui_final.py")
        print("Puis clique Refresh pour voir les challenges")
    else:
        print("\n💥 Problème détecté")

if __name__ == "__main__":
    main()