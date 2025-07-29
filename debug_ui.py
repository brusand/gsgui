#!/usr/bin/env python3
"""
Debug interface - Diagnostic complet du problème d'affichage
"""

import sys
import asyncio
import requests
sys.path.append('/Users/bruno/gsgui/src/gs')
from PySide6.QtWidgets import QApplication
from gsui_simple import SimpleGSGUI
import qasync

def test_backend():
    """Test le backend directement"""
    print("🔍 Test backend...")
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        print(f"  ✅ Backend accessible: {response.status_code}")
        
        # Test avec le vrai token
        with open('/Users/bruno/gsgui/gsgui.ini', 'r') as f:
            content = f.read()
            # Extraire le token
            lines = content.split('\n')
            token = None
            for line in lines:
                if 'xtoken' in line and '=' in line:
                    token = line.split('=')[1].strip()
                    break
        
        if token:
            print(f"  🔑 Token trouvé: {token[:20]}...")
            
            # Test API challenges
            url = f"http://localhost:8001/api/v1/challenges/?user_token={token}"
            response = requests.get(url, timeout=5)
            print(f"  📡 API challenges: status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                challenges = data.get('challenges', [])
                print(f"  📋 Challenges reçus: {len(challenges)}")
                for i, ch in enumerate(challenges):
                    print(f"    {i+1}. {ch.get('title', 'No title')}")
            else:
                print(f"  ❌ Erreur API: {response.text}")
        else:
            print("  ❌ Token non trouvé")
            
    except Exception as e:
        print(f"  ❌ Erreur backend: {e}")

async def test_ui():
    """Test l'interface"""
    print("\n🎨 Test interface...")
    
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = SimpleGSGUI()
    
    print(f"  👤 Profil chargé: {window.player}")
    print(f"  🔑 Token présent: {'Oui' if window.user_token else 'Non'}")
    print(f"  📋 Challenges dict initial: {len(window.challenges)}")
    print(f"  📋 List widget count initial: {window.challenge_list.count()}")
    
    # Test refresh manuel
    print("\n🔄 Test refresh manuel...")
    try:
        await window.refresh_challenges()
        print(f"  📋 Challenges après refresh: {len(window.challenges)}")
        print(f"  📋 List widget après refresh: {window.challenge_list.count()}")
        
        # Afficher le contenu
        for i in range(window.challenge_list.count()):
            item = window.challenge_list.item(i)
            print(f"    {i+1}. {item.text()}")
            
    except Exception as e:
        print(f"  ❌ Erreur refresh: {e}")
    
    app.quit()

def main():
    """Main"""
    print("🧪 DIAGNOSTIC COMPLET - Interface GSGUI")
    print("=" * 50)
    
    # Test 1: Backend
    test_backend()
    
    # Test 2: Interface
    asyncio.run(test_ui())
    
    print("\n" + "=" * 50)
    print("🎯 Diagnostic terminé")

if __name__ == "__main__":
    main()