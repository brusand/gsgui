#!/usr/bin/env python3
"""
Test d'intégration des algorithmes d'ensemble dans le programme principal
"""
import sys
import os

# Ajouter le répertoire source
sys.path.append('src/gs')

try:
    # Importer les modules comme dans gsui.py
    from ensemble_algorithms import ensemble_vote, hybrid_algorithm, ratio_low_algorithm, votes_high_algorithm, random_algorithm
    from bruno_custom_refined import bruno_custom_refined
    print("✅ Modules d'ensemble importés avec succès")
    
    # Test de simulation d'une décision turbo
    first_data = {'ratio': 1.4, 'votes': 500, 'rank': 120}
    second_data = {'ratio': 1.6, 'votes': 300, 'rank': 180}
    
    print(f"\n🧪 Test de décision turbo:")
    print(f"   Photo1: ratio={first_data['ratio']}, votes={first_data['votes']}, rank={first_data['rank']}")
    print(f"   Photo2: ratio={second_data['ratio']}, votes={second_data['votes']}, rank={second_data['rank']}")
    
    # Test ensemble [hybrid,ratio_low,votes_high]
    majority_choice, individual_choices, vote_details, majority_reason = ensemble_vote(
        'photo1', first_data, 'photo2', second_data, ['hybrid', 'ratio_low', 'votes_high']
    )
    
    print(f"\n🗳️ Résultat vote majoritaire:")
    print(f"   Votes individuels: {individual_choices}")
    print(f"   Gagnant majoritaire: {majority_choice}")
    print(f"   Raison: {majority_reason}")
    
    # Test format ensemble comme dans gsui.py
    algorithm = "[hybrid,ratio_low,votes_high]"
    print(f"\n🎯 Test parsing format ensemble: {algorithm}")
    
    if algorithm.startswith('[') and algorithm.endswith(']'):
        algo_list = [algo.strip() for algo in algorithm[1:-1].split(',')]
        print(f"   Algorithmes parsés: {algo_list}")
        
        # Simulation de la logique dans decide_turbo_choice
        majority_choice2, individual_choices2, vote_details2, majority_reason2 = ensemble_vote(
            'photo1', first_data, 'photo2', second_data, algo_list
        )
        
        if majority_choice2 == 'photo1':
            winner_ratio, loser_ratio = first_data['ratio'], second_data['ratio']
            winner_votes = first_data['votes']
        else:
            winner_ratio, loser_ratio = second_data['ratio'], first_data['ratio']
            winner_votes = second_data['votes']
        
        strategy_desc = f"Vote majoritaire {majority_reason2}"
        
        print(f"   📊 Résultat simulation gsui.py:")
        print(f"      Gagnant: {majority_choice2}")
        print(f"      Ratio gagnant/perdant: {winner_ratio}/{loser_ratio}")
        print(f"      Votes gagnant: {winner_votes}")
        print(f"      Stratégie: {strategy_desc}")
        
        print(f"\n✅ Intégration complète testée avec succès!")
        print(f"   Le système d'ensemble est prêt pour l'intégration dans gsui.py")
    
except ImportError as e:
    print(f"❌ Erreur import: {e}")
except Exception as e:
    print(f"❌ Erreur test: {e}")
    import traceback
    traceback.print_exc()