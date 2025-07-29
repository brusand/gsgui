#!/usr/bin/env python3
"""
Test spécifique pour débugger le statut turbo de Coastline
"""

import requests
import json
from configobj import ConfigObj

def test_coastline_turbo():
    """Test le statut turbo de Coastline spécifiquement"""
    
    # Récupérer le vrai token
    try:
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
        real_token = config['players']['bruno']['xtoken']
        print(f"🔑 Using real token: {real_token[:20]}...")
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return
    
    # Appel API
    print("\n🌊 Testing Coastline turbo status...")
    print("=" * 50)
    
    try:
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges = data.get('challenges', [])
            
            # Chercher Coastline
            coastline = None
            for challenge in challenges:
                if 'Coastline' in challenge.get('title', ''):
                    coastline = challenge
                    break
            
            if coastline:
                print(f"✅ Found Coastline challenge:")
                print(f"  - ID: {coastline['id']}")
                print(f"  - Title: {coastline['title']}")
                print(f"  - Current turbo_status: {coastline['turbo_status']}")
                print(f"  - Votes: {coastline['votes']}")
                print(f"  - Time left: {coastline['time_left']}")
                
                # Comparer avec ce que GSGUI dit
                print(f"\n🤔 Expected: WON (selon GSGUI)")
                print(f"🔍 Actual: {coastline['turbo_status']}")
                
                if coastline['turbo_status'] != 'won':
                    print(f"❌ MISMATCH! Le statut devrait être 'won' mais est '{coastline['turbo_status']}'")
                else:
                    print(f"✅ CORRECT! Le statut est bien 'won'")
            else:
                print("❌ Coastline challenge not found!")
                print("Available challenges:")
                for ch in challenges[:5]:
                    print(f"  - {ch['id']}: {ch['title']}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coastline_turbo()