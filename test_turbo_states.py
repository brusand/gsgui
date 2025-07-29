#!/usr/bin/env python3
"""
Test des différents états turbo
"""

import requests
import json

def test_turbo_states():
    """Test tous les états turbo"""
    print("🧪 Test des états turbo GSGUI")
    print("=" * 40)
    
    base_url = "http://localhost:8001/api/v1"
    
    try:
        # 1. Récupérer les challenges pour voir les états automatiques
        print("📋 1. États automatiques selon les règles:")
        response = requests.get(f"{base_url}/challenges/?user_token=test", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            challenges = data.get('challenges', [])
            
            # Analyser les différents états
            states = {}
            for challenge in challenges:
                status = challenge.get('turbo_status', 'none')
                if status not in states:
                    states[status] = []
                states[status].append({
                    'id': challenge.get('id'),
                    'title': challenge.get('title'),
                    'days': challenge.get('time_left', {}).get('days', 0),
                    'hours': challenge.get('time_left', {}).get('hours', 0)
                })
            
            for state, challenges_list in states.items():
                print(f"\n🔸 État '{state}': {len(challenges_list)} challenges")
                for ch in challenges_list[:3]:  # Afficher les 3 premiers
                    print(f"  - {ch['title']}: {ch['days']}D {ch['hours']}H")
        
        # 2. Tester l'exécution turbo (crée l'état "completed")
        print(f"\n📋 2. Test exécution turbo:")
        turbo_data = {
            "challenge_id": "105519",
            "challenge_title": "Test Turbo States",
            "challenge_time_left": "1j"
        }
        
        response = requests.post(
            f"{base_url}/profiles/bruno/turbo/execute", 
            json=turbo_data, 
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Turbo exécuté: {result['challenge_id']} → {result['status']}")
        
        print("\n🎯 Testez maintenant l'UI pour voir tous les états!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_turbo_states()