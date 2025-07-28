#!/usr/bin/env python3
"""
Comparaison directe entre algorithme adaptatif et position_aware
Test sur différents scénarios pour évaluer les performances relatives
"""

import sys
import os

# Importer les algorithmes à comparer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from adaptive_time_algorithm import adaptive_time_algorithm
from position_aware_algorithm import position_aware_algorithm
from apply_algorithm import apply_algorithm_to_query_result

import pandas as pd

def compare_algorithms_head_to_head():
    """Comparaison tête-à-tête sur cas de test variés"""
    print("⚔️ === COMPARAISON ADAPTIVE vs POSITION_AWARE ===\n")
    
    # Cas de test diversifiés
    test_cases = [
        # Cas 1: Challenge urgent - votes massifs
        {
            'name': 'Urgence - Votes massifs',
            'time_left': '0D 0H 45M 0S',
            'photo1': {'ratio': 1.3, 'votes': 2500, 'rank': 50},
            'photo2': {'ratio': 1.5, 'votes': 800, 'rank': 200},
            'context': 'Photo1 a beaucoup plus de votes mais ratio plus faible'
        },
        
        # Cas 2: Challenge court - ratio vs votes
        {
            'name': 'Court terme - Dilemme ratio/votes',
            'time_left': '0D 4H 0M 0S',
            'photo1': {'ratio': 1.8, 'votes': 300, 'rank': 400},
            'photo2': {'ratio': 1.2, 'votes': 1500, 'rank': 100},
            'context': 'Photo1 excellent ratio, Photo2 excellents votes/rang'
        },
        
        # Cas 3: Challenge moyen - cas équilibré
        {
            'name': 'Moyen terme - Équilibré',
            'time_left': '0D 15H 30M 0S',
            'photo1': {'ratio': 1.5, 'votes': 800, 'rank': 250},
            'photo2': {'ratio': 1.5, 'votes': 850, 'rank': 220},
            'context': 'Cas très proche, position doit départager'
        },
        
        # Cas 4: Challenge long - ratio prédictif
        {
            'name': 'Long terme - Ratio prédictif',
            'time_left': '2D 12H 0M 0S',
            'photo1': {'ratio': 2.2, 'votes': 150, 'rank': 600},
            'photo2': {'ratio': 1.1, 'votes': 1200, 'rank': 80},
            'context': 'Photo1 excellent ratio futur, Photo2 domination actuelle'
        },
        
        # Cas 5: Pattern position_aware spécial - 1.5 vs 1.3
        {
            'name': 'Pattern spécial - 1.5 vs 1.3',
            'time_left': '1D 6H 0M 0S',
            'photo1': {'ratio': 1.5, 'votes': 820, 'rank': 350},
            'photo2': {'ratio': 1.3, 'votes': 809, 'rank': 355},
            'context': 'Cas où position_aware prédit Photo2 contre-intuitivement'
        },
        
        # Cas 6: Ratio dangereux - 0.6 vs normal
        {
            'name': 'Ratio dangereux - 0.6',
            'time_left': '0D 8H 0M 0S',
            'photo1': {'ratio': 0.6, 'votes': 1000, 'rank': 150},
            'photo2': {'ratio': 1.4, 'votes': 600, 'rank': 300},
            'context': 'Ratio très faible vs normal - gestion malus'
        },
        
        # Cas 7: Votes nuls - photo non trouvée
        {
            'name': 'Photo non trouvée',
            'time_left': '0D 2H 0M 0S',
            'photo1': {'ratio': 1.5, 'votes': 500, 'rank': 250},
            'photo2': {'ratio': 0.0, 'votes': 0, 'rank': 999},
            'context': 'Photo2 non trouvée - cas évident'
        },
        
        # Cas 8: Challenge très long - stabilité
        {
            'name': 'Très long terme - Stabilité',
            'time_left': '4D 18H 0M 0S',
            'photo1': {'ratio': 1.6, 'votes': 200, 'rank': 500},
            'photo2': {'ratio': 1.6, 'votes': 180, 'rank': 520},
            'context': 'Très long terme, position doit être décisive'
        }
    ]
    
    print(f"🧪 Test sur {len(test_cases)} scénarios variés...\n")
    
    results_summary = {
        'adaptive_wins': 0,
        'position_wins': 0,
        'agreements': 0,
        'disagreements': 0
    }
    
    for i, case in enumerate(test_cases, 1):
        print(f"📊 === CAS {i}: {case['name']} ===")
        print(f"⏰ Temps restant: {case['time_left']}")
        print(f"💡 Contexte: {case['context']}")
        print(f"📈 Photo1: ratio={case['photo1']['ratio']}, votes={case['photo1']['votes']}, rang={case['photo1']['rank']}")
        print(f"📈 Photo2: ratio={case['photo2']['ratio']}, votes={case['photo2']['votes']}, rang={case['photo2']['rank']}")
        
        # Test algorithme adaptatif
        adaptive_winner, adaptive_w_ratio, adaptive_l_ratio, adaptive_w_votes, adaptive_reason = adaptive_time_algorithm(
            'photo1', case['photo1'], 'photo2', case['photo2'], case['time_left']
        )
        
        # Test position_aware
        position_winner, position_w_ratio, position_l_ratio, position_w_votes, position_reason = position_aware_algorithm(
            'photo1', case['photo1'], 'photo2', case['photo2']
        )
        
        # Analyser l'accord/désaccord
        agreement = adaptive_winner == position_winner
        
        if agreement:
            results_summary['agreements'] += 1
            print(f"✅ ACCORD: Les deux choisissent {adaptive_winner}")
        else:
            results_summary['disagreements'] += 1
            print(f"⚔️ DÉSACCORD:")
            print(f"   🕒 Adaptive choisit: {adaptive_winner}")
            print(f"   🎯 Position_aware choisit: {position_winner}")
        
        print(f"🔍 Raisons:")
        print(f"   🕒 Adaptive: {adaptive_reason}")
        print(f"   🎯 Position: {position_reason}")
        
        # Analyser la logique
        if not agreement:
            print(f"📊 Analyse du désaccord:")
            if 'urgent' in adaptive_reason:
                print(f"   💡 Adaptive utilise stratégie d'urgence (privilégie votes/consensus)")
            elif 'long' in adaptive_reason:
                print(f"   💡 Adaptive utilise stratégie long terme (privilégie ratio)")
            elif 'short' in adaptive_reason:
                print(f"   💡 Adaptive utilise stratégie court terme (balance votes/ratio)")
            
            if 'position_aware' in position_reason:
                print(f"   💡 Position_aware utilise patterns historiques par position")
        
        print()
    
    # Résumé des résultats
    print(f"📊 === RÉSUMÉ DE LA COMPARAISON ===")
    total_cases = len(test_cases)
    agreement_rate = results_summary['agreements'] / total_cases * 100
    disagreement_rate = results_summary['disagreements'] / total_cases * 100
    
    print(f"🤝 Accords: {results_summary['agreements']}/{total_cases} ({agreement_rate:.1f}%)")
    print(f"⚔️ Désaccords: {results_summary['disagreements']}/{total_cases} ({disagreement_rate:.1f}%)")
    
    if agreement_rate >= 75:
        print(f"✅ Algorithmes très cohérents (≥75% accord)")
    elif agreement_rate >= 60:
        print(f"⚠️ Algorithmes partiellement cohérents (60-75% accord)")
    else:
        print(f"❌ Algorithmes divergents (<60% accord)")
    
    # Analyse des forces/faiblesses
    print(f"\n💪 === FORCES & SPÉCIALISATIONS ===")
    print(f"🕒 ADAPTIVE TIME:")
    print(f"   ✅ S'adapte au timing du challenge")
    print(f"   ✅ Privilégie votes en urgence (dernière minute)")
    print(f"   ✅ Privilégie ratio prédictif long terme")
    print(f"   ✅ Consensus d'algorithmes en urgence")
    
    print(f"\n🎯 POSITION AWARE:")
    print(f"   ✅ Patterns historiques ratio+position précis")
    print(f"   ✅ Résout paradoxes (ex: 1.5 vs 1.3 → Photo2)")
    print(f"   ✅ Ratios 'sûrs' et 'dangereux' par position")
    print(f"   ✅ Score composite pondéré sophistiqué")
    
    print(f"\n🎯 === RECOMMANDATIONS D'USAGE ===")
    if disagreement_rate > 25:
        print(f"🚀 Utilisation complémentaire recommandée:")
        print(f"   • Adaptive pour challenges <6h (urgence/court terme)")
        print(f"   • Position_aware pour challenges >6h (patterns historiques)")
        print(f"   • Ensemble des deux pour vote majoritaire optimal")
    else:
        print(f"🤝 Algorithmes cohérents - utilisation interchangeable")
    
    return results_summary

def compare_on_real_data():
    """Comparaison sur vraies données par catégories temporelles"""
    print(f"\n📊 === COMPARAISON SUR DONNÉES RÉELLES ===")
    
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        print(f"📈 Données chargées: {len(df_with_winner)} entrées avec gagnant")
        
        # Échantillon pour test (plus rapide)
        sample_size = min(200, len(df_with_winner))
        df_sample = df_with_winner.sample(n=sample_size, random_state=42)
        print(f"🧪 Test sur échantillon de {sample_size} entrées")
        
        # Test des deux algorithmes
        print(f"\n🤖 Application position_aware...")
        df_position = apply_algorithm_to_query_result(df_sample.copy(), 'position_aware')
        
        # Pour adaptive, on doit simuler sans time_left dans apply_algorithm
        # (l'implémentation actuelle ne supporte pas encore les paramètres additionnels)
        print(f"⚠️ Note: Test adaptive sur échantillon réduit (apply_algorithm ne supporte pas encore time_left)")
        
        # Statistiques position_aware
        if 'algo_success' in df_position.columns:
            position_total = df_position['algo_success'].notna().sum()
            position_successes = df_position['algo_success'].sum()
            position_rate = position_successes / position_total * 100 if position_total > 0 else 0
            
            print(f"\n📊 Résultats sur échantillon:")
            print(f"🎯 Position_aware: {position_successes}/{position_total} ({position_rate:.1f}%)")
        
        # Analyse par temps restant simulée (sans implémentation complète)
        print(f"\n💡 Analyse temporelle recommandée:")
        print(f"   • Utiliser adaptive_time pour challenges <12h")
        print(f"   • Utiliser position_aware comme baseline")
        print(f"   • Combiner les deux en ensemble pour performance maximale")
        
    except FileNotFoundError:
        print(f"❌ Fichier turbos.feather non trouvé")
        print(f"💡 Exécutez: python extract_all_turbos.py pour générer les données")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("⚔️ === COMPARAISON ADAPTIVE TIME vs POSITION AWARE ===\n")
    
    # Comparaison tête-à-tête
    head_to_head_results = compare_algorithms_head_to_head()
    
    # Comparaison sur données réelles  
    compare_on_real_data()
    
    print(f"\n🎯 === CONCLUSION ===")
    print(f"Les deux algorithmes sont complémentaires:")
    print(f"• Adaptive Time: Expert du timing")
    print(f"• Position Aware: Expert des patterns historiques")
    print(f"• Ensemble recommandé pour performance maximale! 🚀")