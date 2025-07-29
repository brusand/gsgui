#!/usr/bin/env python3
"""
Debug spécifique pour les challenges avec incohérences turbo
"""

import requests
import json
from configobj import ConfigObj

def debug_specific_challenges():
    """Debug les challenges problématiques"""
    
    # Récupérer le vrai token
    try:
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
        real_token = config['players']['bruno']['xtoken'] 
        print(f"🔑 Using real token: {real_token[:20]}...")
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return
    
    print("\n🔍 Debug des challenges problématiques...")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges = data.get('challenges', [])
            
            # Challenges problématiques identifiés
            problematic = {
                'The Bluest Skies': {'expected': 'WON', 'current': 'OK'},
                'Humorous Shots': {'expected': 'LOCKED', 'current': 'OK'}, 
                'Smoke': {'expected': 'TIMER ou autre', 'current': 'vide'}
            }
            
            print(f"📋 Analyse des {len(challenges)} challenges...")
            print()
            
            for challenge in challenges:
                title = challenge.get('title', '')
                if any(name in title for name in problematic.keys()):
                    print(f"🎯 CHALLENGE PROBLÉMATIQUE: {title}")
                    print(f"   ID: {challenge['id']}")
                    print(f"   Turbo Status: '{challenge['turbo_status']}'")
                    print(f"   Expected: {problematic.get(title, {}).get('expected', 'Unknown')}")
                    print(f"   Time left: {challenge['time_left']}")
                    print(f"   Votes: {challenge['votes']}")
                    
                    # Identifier pourquoi il a ce statut
                    if challenge['turbo_status'] == 'completed':
                        print(f"   ⚠️  RAISON: Challenge marqué 'completed' localement")
                        print(f"   🔍 Turbo ID: {challenge.get('turbo_id', 'None')}")
                    elif challenge['turbo_status'] == 'none':
                        print(f"   ⚠️  RAISON: Aucun statut turbo détecté")
                    
                    print()
            
            # Statistiques générales
            status_count = {}
            for challenge in challenges:
                status = challenge['turbo_status']
                status_count[status] = status_count.get(status, 0) + 1
            
            print("📊 DISTRIBUTION DES STATUTS TURBO:")
            for status, count in sorted(status_count.items()):
                print(f"   {status}: {count} challenges")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_specific_challenges()