#!/usr/bin/env python3
"""
Test du vrai vote avec délai pour attendre le traitement GuruShots
"""

import requests
import json
import time
from configobj import ConfigObj

def test_real_vote_with_delay():
    """Test le vrai vote avec délai d'attente"""
    
    # Récupérer le vrai token
    try:
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
        real_token = config['players']['bruno']['xtoken'] 
        print(f"🔑 Using real token: {real_token[:20]}...")
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return
    
    print("\n🧪 Test Vote RÉEL avec délai d'attente")
    print("=" * 60)
    
    # 1. État AVANT
    print("📋 1. État AVANT vote:")
    try:
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges_before = data.get('challenges', [])
            
            print(f"   Total challenges: {len(challenges_before)}")
            for challenge in challenges_before[:3]:
                print(f"   - {challenge['title'][:35]}: {challenge['votes']} votes, exposure: {challenge['exposure']}")
        else:
            print(f"❌ Erreur API: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # 2. VOTE RÉEL
    print(f"\n🗳️ 2. Exécution VOTE RÉEL (100 votes):")
    if challenges_before:
        test_challenge = challenges_before[0]
        challenge_url = test_challenge['url']
        
        print(f"   Challenge choisi: {test_challenge['title']}")
        print(f"   URL: {challenge_url}")
        
        try:
            vote_data = {
                "challenge_url": challenge_url,
                "vote_count": 100
            }
            
            start_time = time.time()
            response = requests.post(
                f"http://localhost:8001/api/v1/challenges/simple-vote?user_token={real_token}",
                json=vote_data,
                timeout=30  # Plus de temps pour le vrai vote
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Vote réussi en {end_time - start_time:.2f}s")
                print(f"   Message: {result.get('message', 'OK')}")
                print(f"   Détails: {result.get('result_data', {})}")
            else:
                print(f"   ❌ Vote échoué: {response.status_code}")
                print(f"   Response: {response.text}")
                return
                
        except Exception as e:
            print(f"   ❌ Erreur Vote: {e}")
            return
    
    # 3. ATTENDRE TRAITEMENT GURUSHOTS
    print(f"\n⏳ 3. Attente traitement GuruShots (30 secondes)...")
    for i in range(30, 0, -1):
        print(f"   Attente: {i}s restantes", end='\r')
        time.sleep(1)
    print("   ✅ Attente terminée                ")
    
    # 4. État APRÈS
    print(f"\n🔄 4. État APRÈS vote (refresh):")
    try:
        response = requests.get(
            f"http://localhost:8001/api/v1/challenges/?user_token={real_token}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            challenges_after = data.get('challenges', [])
            
            print(f"   Total challenges: {len(challenges_after)}")
            
            # Comparaison détaillée
            for i, challenge in enumerate(challenges_after[:3]):
                if i < len(challenges_before):
                    before = challenges_before[i]
                    after = challenge
                    
                    vote_diff = after['votes'] - before['votes']
                    exposure_diff = after['exposure'] - before['exposure']
                    
                    vote_status = "🟢 +" if vote_diff > 0 else "🔵 =" if vote_diff == 0 else "🔴 -"
                    exposure_status = "🟢 +" if exposure_diff > 0 else "🔵 =" if exposure_diff == 0 else "🔴 -"
                    
                    print(f"   - {after['title'][:35]}:")
                    print(f"     Votes: {after['votes']} ({vote_status}{vote_diff})")  
                    print(f"     Exposure: {after['exposure']} ({exposure_status}{exposure_diff})")
                    
                    if i == 0:  # Premier challenge (celui voté)
                        if vote_diff > 0 or exposure_diff > 0:
                            print(f"     🎉 SUCCÈS ! Le vote réel a fonctionné !")
                        else:
                            print(f"     ⚠️ Aucun changement détecté - possible délai ou problème")
        else:
            print(f"❌ Erreur API refresh: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur refresh: {e}")
    
    print(f"\n✅ Test terminé")
    print("Si votes/exposure ont augmenté, le système de vote réel fonctionne !")

if __name__ == "__main__":
    test_real_vote_with_delay()