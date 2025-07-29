#!/usr/bin/env python3
"""
Test du backend avec vrais challenges GuruShots
"""

import requests
import time
import subprocess
import sys

def test_real_backend():
    """Test du backend avec vrais challenges"""
    print("🧪 Test Backend Vrais Challenges")
    print("=" * 40)
    
    # 1. Vérifier que le backend est accessible
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend accessible")
        else:
            print(f"❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend non accessible: {e}")
        return False
    
    # 2. Test avec le token de la config
    try:
        # Récupérer le token depuis la config
        from configobj import ConfigObj
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
        
        if 'players' not in config or not config['players']:
            print("❌ Aucun player dans la config")
            return False
            
        player = list(config['players'].keys())[0]
        token = config['players'][player].get('xtoken')
        
        if not token:
            print("❌ Token manquant dans la config")
            return False
            
        print(f"🔑 Token trouvé pour {player}: {token[:20]}...")
        
        # 3. Test de l'API challenges
        print("\n🔍 Test API challenges...")
        url = f"http://localhost:8001/api/v1/challenges/?user_token={token}"
        response = requests.get(url, timeout=15)  # Plus de temps pour l'API GuruShots
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            challenges = data.get('challenges', [])
            print(f"✅ Challenges reçus: {len(challenges)}")
            
            if challenges:
                print("\n📋 Premiers challenges:")
                for i, ch in enumerate(challenges[:3]):
                    print(f"  {i+1}. {ch.get('title', 'No title')}")
                    print(f"     Votes: {ch.get('votes', 0)}, Rang: {ch.get('rank', 999)}")
                
                return True
            else:
                print("⚠️ Aucun challenge retourné")
                return False
        else:
            print(f"❌ Erreur API: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🎯 GSGUI - Test Vrais Challenges GuruShots")
    print("=" * 50)
    
    success = test_real_backend()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Les vrais challenges GuruShots fonctionnent !")
        print("\n📋 Pour utiliser:")
        print("1. Arrêtez l'ancien backend (Ctrl+C)")
        print("2. Lancez: python backend_real.py")
        print("3. Lancez: python gsui_final.py")
        print("4. Cliquez Refresh pour voir VOS challenges !")
    else:
        print("💥 ERREUR: Problème avec les vrais challenges")
        print("Vérifiez que:")
        print("- Le token dans gsgui.ini est valide")
        print("- Vous êtes connecté à internet") 
        print("- L'API GuruShots est accessible")

if __name__ == "__main__":
    main()