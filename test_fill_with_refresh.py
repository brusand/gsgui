#!/usr/bin/env python3
"""
Test Fill + Refresh automatique
"""

import requests
import json
from configobj import ConfigObj

def test_fill_and_refresh():
    """Test l'exécution de Fill et vérifie le refresh automatique"""
    
    # Récupérer le vrai token
    try:
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
        real_token = config['players']['bruno']['xtoken'] 
        print(f"🔑 Using real token: {real_token[:20]}...")
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return
    
    print("\n🧪 Test Fill + Refresh automatique")
    print("=" * 50)
    
    # 1. Récupérer les challenges avant Fill
    print("📋 1. État AVANT Fill:")
    try:
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges_before = data.get('challenges', [])
            
            # Afficher les votes de quelques challenges
            print(f"   Total challenges: {len(challenges_before)}")
            for challenge in challenges_before[:3]:
                print(f"   - {challenge['title'][:25]}: {challenge['votes']} votes")
        else:
            print(f"❌ Erreur API: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # 2. Simuler un Fill sur un challenge
    print(f"\n⚡ 2. Exécution Fill (50 votes):")
    if challenges_before:
        test_challenge = challenges_before[0]
        challenge_url = test_challenge['url']
        
        try:
            vote_data = {
                "challenge_url": challenge_url,
                "vote_count": 50
            }
            
            response = requests.post(
                f"http://localhost:8001/api/v1/challenges/simple-vote?user_token={real_token}",
                json=vote_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Fill réussi: {result.get('message', 'OK')}")
            else:
                print(f"   ❌ Fill échoué: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erreur Fill: {e}")
    
    # 3. Vérifier l'état après (simuler le refresh automatique)
    print(f"\n🔄 3. État APRÈS Fill (refresh automatique):")
    try:
        # Attendre un peu comme le fait le refresh automatique
        import time
        time.sleep(1)
        
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges_after = data.get('challenges', [])
            
            # Comparer les votes
            print(f"   Total challenges: {len(challenges_after)}")
            for i, challenge in enumerate(challenges_after[:3]):
                before_votes = challenges_before[i]['votes'] if i < len(challenges_before) else 0
                after_votes = challenge['votes']
                diff = after_votes - before_votes
                
                status = "🟢 +" if diff > 0 else "🔵 =" if diff == 0 else "🔴 -"
                print(f"   - {challenge['title'][:25]}: {after_votes} votes ({status}{diff})")
        else:
            print(f"❌ Erreur API refresh: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur refresh: {e}")
    
    print(f"\n✅ Test terminé - Le refresh automatique devrait être visible dans l'UI")

if __name__ == "__main__":
    test_fill_and_refresh()