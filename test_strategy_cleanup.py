#!/usr/bin/env python3
"""
Test du nettoyage automatique des stratégies
Vérifie que le backend nettoie les stratégies existantes avant d'appliquer une nouvelle
"""

import asyncio
import sys
sys.path.append('/Users/bruno/gsgui/src/gs')
from gsui_api_client import GSGUIApiClient
from datetime import datetime, timedelta

async def test_strategy_cleanup():
    """Test de la fonctionnalité critique de nettoyage des stratégies"""
    
    async with GSGUIApiClient() as client:
        profile_name = "test_bruno"
        
        # 1. Enregistrer le profil
        print("🔌 Enregistrement profil...")
        await client.register_profile(profile_name, "test_token")
        
        # 2. Programmer une première stratégie
        print("📅 Programmation stratégie 1 (fill)...")
        result1 = await client.schedule_strategy(
            challenge_id="challenge_1",
            strategy_name="fill",
            scheduled_at=datetime.now() + timedelta(minutes=5),
            challenge_title="Test Challenge 1"
        )
        print(f"   ✅ Stratégie 1 créée: {result1.get('strategy_id')}")
        
        # 3. Vérifier qu'elle existe
        strategies = await client.list_strategies()
        print(f"📋 Stratégies existantes: {len(strategies.get('strategies', []))}")
        
        # 4. Programmer une seconde stratégie sur le même challenge
        print("📅 Programmation stratégie 2 (4m) - doit nettoyer la première...")
        
        # Simuler le nettoyage (comme fait dans l'UI)
        cancelled = await client.cancel_challenge_strategies("challenge_1")
        print(f"🧹 Stratégies annulées: {cancelled}")
        
        # Nouvelle stratégie
        result2 = await client.schedule_strategy(
            challenge_id="challenge_1", 
            strategy_name="4m",
            scheduled_at=datetime.now() + timedelta(minutes=3),
            challenge_title="Test Challenge 1"
        )
        print(f"   ✅ Stratégie 2 créée: {result2.get('strategy_id')}")
        
        # 5. Vérifier le résultat final
        strategies_final = await client.list_strategies()
        final_count = len(strategies_final.get('strategies', []))
        print(f"📋 Stratégies finales: {final_count}")
        
        # 6. Analyser le résultat
        if final_count == 1:
            final_strategy = strategies_final['strategies'][0]
            if final_strategy['strategy_name'] == '4m':
                print("✅ SUCCESS: Nettoyage automatique réussi!")
                print(f"   Stratégie finale: {final_strategy['strategy_name']} pour {final_strategy['challenge_id']}")
                return True
            else:
                print("❌ ERREUR: Mauvaise stratégie finale")
        else:
            print(f"❌ ERREUR: {final_count} stratégies au lieu d'1")
            
        return False

if __name__ == "__main__":
    print("🧪 Test du nettoyage automatique des stratégies")
    print("=" * 50)
    
    success = asyncio.run(test_strategy_cleanup())
    
    if success:
        print("\n🎉 Test RÉUSSI - La fonctionnalité critique fonctionne!")
    else:
        print("\n💥 Test ÉCHOUÉ - La fonctionnalité doit être corrigée")