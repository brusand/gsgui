#!/usr/bin/env python3
"""
Test exhaustif pour trouver la meilleure combinaison de 3 algorithmes
Analyse toutes les combinaisons possibles et évalue leur performance
"""

import pandas as pd
import sys
import os
from itertools import combinations

# Importer les modules nécessaires
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def test_all_3_algorithm_combinations():
    """Test toutes les combinaisons de 3 algorithmes pour trouver la meilleure"""
    
    print("🔍 === RECHERCHE DU MEILLEUR ENSEMBLE DE 3 ALGORITHMES ===\n")
    
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        print(f"📊 Données chargées: {len(df_with_winner)} entrées avec gagnant")
        
        # Échantillon pour tests plus rapides
        sample_size = min(800, len(df_with_winner))  # Plus grand échantillon pour plus de précision
        df_sample = df_with_winner.sample(n=sample_size, random_state=42)
        print(f"🧪 Test sur échantillon de {sample_size} entrées\n")
        
        # Algorithmes disponibles avec leurs performances individuelles connues
        algorithms = [
            'hybrid',         # 67.2%
            'ratio_low',      # 66.5% 
            'votes_high',     # 68.6%
            'position_aware', # 58.5%
            'adaptive_time',  # 59.0%
            'bruno_custom',   # 63.9%
            'votes_ratio',    # 64.6%
        ]
        
        print(f"🤖 Algorithmes testés: {', '.join(algorithms)}")
        print(f"📈 Performances individuelles connues:")
        individual_perfs = {
            'hybrid': 67.2,
            'ratio_low': 66.5,
            'votes_high': 68.6,
            'position_aware': 58.5,
            'adaptive_time': 59.0,
            'bruno_custom': 63.9,
            'votes_ratio': 64.6
        }
        
        for algo, perf in individual_perfs.items():
            print(f"   {algo:15}: {perf:5.1f}%")
        print()
        
        # Générer toutes les combinaisons de 3 algorithmes
        all_combinations = list(combinations(algorithms, 3))
        print(f"🔢 Nombre total de combinaisons à tester: {len(all_combinations)}")
        print()
        
        results = []
        
        for i, combo in enumerate(all_combinations, 1):
            combo_name = f"[{','.join(combo)}]"
            print(f"🧪 Test {i:2d}/{len(all_combinations)}: {combo_name}")
            
            try:
                # Appliquer l'ensemble d'algorithmes
                df_result = apply_algorithm_to_query_result(df_sample.copy(), combo_name)
                
                # Calculer les statistiques
                total_with_winner = (df_result['winner_id'].notna() & (df_result['winner_id'] != '')).sum()
                majority_successes = df_result['majority_success'].sum() if 'majority_success' in df_result.columns else 0
                
                if total_with_winner > 0:
                    success_rate = majority_successes / total_with_winner * 100
                    
                    # Calculer la performance théorique moyenne
                    theoretical_avg = sum(individual_perfs[algo] for algo in combo) / 3
                    
                    # Calculer le boost d'ensemble (différence vs moyenne individuelle)
                    ensemble_boost = success_rate - theoretical_avg
                    
                    result = {
                        'combination': combo,
                        'combo_name': combo_name,
                        'total_cases': total_with_winner,
                        'successes': majority_successes,
                        'success_rate': success_rate,
                        'theoretical_avg': theoretical_avg,
                        'ensemble_boost': ensemble_boost
                    }
                    
                    results.append(result)
                    
                    print(f"   ✅ Résultat: {majority_successes}/{total_with_winner} ({success_rate:.1f}%) | Théorique: {theoretical_avg:.1f}% | Boost: {ensemble_boost:+.1f}%")
                else:
                    print(f"   ❌ Aucun cas avec gagnant")
                    
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        # Analyser les résultats
        print(f"\n📊 === ANALYSE DES RÉSULTATS ===")
        
        if results:
            # Trier par taux de succès
            results_sorted = sorted(results, key=lambda x: x['success_rate'], reverse=True)
            
            print(f"\n🏆 TOP 10 des meilleures combinaisons:")
            print(f"{'Rang':>4} | {'Combinaison':35} | {'Succès':>7} | {'Taux':>6} | {'Théo':>6} | {'Boost':>7}")
            print("-" * 80)
            
            for i, result in enumerate(results_sorted[:10], 1):
                combo_display = f"[{','.join(result['combination'])}]"
                print(f"{i:4d} | {combo_display:35} | {result['successes']:3d}/{result['total_cases']:3d} | {result['success_rate']:5.1f}% | {result['theoretical_avg']:5.1f}% | {result['ensemble_boost']:+6.1f}%")
            
            # Analyser les patterns
            print(f"\n🔍 === ANALYSE DES PATTERNS ===")
            
            best_result = results_sorted[0]
            worst_result = results_sorted[-1]
            
            print(f"🥇 Meilleure combinaison: {best_result['combo_name']}")
            print(f"   Performance: {best_result['success_rate']:.1f}% ({best_result['successes']}/{best_result['total_cases']})")
            print(f"   Boost ensemble: {best_result['ensemble_boost']:+.1f}% vs moyenne théorique")
            
            print(f"\n🥉 Pire combinaison: {worst_result['combo_name']}")
            print(f"   Performance: {worst_result['success_rate']:.1f}% ({worst_result['successes']}/{worst_result['total_cases']})")
            print(f"   Boost ensemble: {worst_result['ensemble_boost']:+.1f}% vs moyenne théorique")
            
            # Analyser quels algorithmes apparaissent le plus dans le top
            print(f"\n📈 Fréquence des algorithmes dans le TOP 5:")
            top5_algorithms = {}
            for result in results_sorted[:5]:
                for algo in result['combination']:
                    top5_algorithms[algo] = top5_algorithms.get(algo, 0) + 1
            
            for algo, count in sorted(top5_algorithms.items(), key=lambda x: x[1], reverse=True):
                percentage = count / 5 * 100
                print(f"   {algo:15}: {count}/5 apparitions ({percentage:4.0f}%)")
            
            # Analyser les synergies
            print(f"\n🤝 === ANALYSE DES SYNERGIES ===")
            
            # Comparer avec les combinaisons actuelles
            current_default = "[hybrid,ratio_low,votes_high]"
            current_result = next((r for r in results if r['combo_name'] == current_default), None)
            
            if current_result:
                current_rank = results_sorted.index(current_result) + 1
                print(f"🎯 Combinaison actuelle par défaut: {current_default}")
                print(f"   Rang: {current_rank}/{len(results_sorted)}")
                print(f"   Performance: {current_result['success_rate']:.1f}%")
                print(f"   Amélioration possible: {best_result['success_rate'] - current_result['success_rate']:+.1f}%")
            
            # Vérifier si position_aware + adaptive_time apparaissent ensemble
            print(f"\n🎯 Combinaisons incluant position_aware + adaptive_time:")
            pa_at_combos = [r for r in results_sorted if 'position_aware' in r['combination'] and 'adaptive_time' in r['combination']]
            
            if pa_at_combos:
                print(f"   Nombre de combinaisons: {len(pa_at_combos)}")
                best_pa_at = pa_at_combos[0]
                best_pa_at_rank = results_sorted.index(best_pa_at) + 1
                print(f"   Meilleure avec PA+AT: {best_pa_at['combo_name']}")
                print(f"   Rang: {best_pa_at_rank}/{len(results_sorted)}")
                print(f"   Performance: {best_pa_at['success_rate']:.1f}%")
            
            # Recommandations finales
            print(f"\n💡 === RECOMMANDATIONS ===")
            
            if best_result['success_rate'] > 70:
                print(f"🚀 EXCELLENT: Meilleure combinaison dépasse 70%!")
            elif best_result['success_rate'] > 65:
                print(f"✅ BON: Meilleure combinaison dépasse 65%")
            else:
                print(f"⚠️ MOYEN: Meilleure combinaison sous 65%")
            
            print(f"\n🎯 Nouvelle combinaison recommandée: {best_result['combo_name']}")
            print(f"   Remplace: {current_default if current_result else 'N/A'}")
            print(f"   Gain estimé: {best_result['success_rate'] - (current_result['success_rate'] if current_result else 65):+.1f}%")
            
            # Alternatives intéressantes
            print(f"\n🔄 Alternatives intéressantes (TOP 3):")
            for i, result in enumerate(results_sorted[1:4], 2):
                print(f"   {i}. {result['combo_name']} → {result['success_rate']:.1f}%")
            
            return results_sorted
            
        else:
            print("❌ Aucun résultat valide obtenu")
            return []
            
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
        return []
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_results_to_csv(results):
    """Sauvegarder les résultats pour analyse ultérieure"""
    if results:
        results_data = []
        for result in results:
            results_data.append({
                'combination': ','.join(result['combination']),
                'success_rate': result['success_rate'],
                'successes': result['successes'],
                'total_cases': result['total_cases'],
                'theoretical_avg': result['theoretical_avg'],
                'ensemble_boost': result['ensemble_boost']
            })
        
        df_results = pd.DataFrame(results_data)
        df_results.to_csv('best_ensemble_3_analysis.csv', index=False)
        print(f"\n💾 Résultats sauvés: best_ensemble_3_analysis.csv")

if __name__ == "__main__":
    print("🔍 === RECHERCHE DU MEILLEUR ENSEMBLE DE 3 ALGORITHMES ===\n")
    
    results = test_all_3_algorithm_combinations()
    
    if results:
        save_results_to_csv(results)
        print(f"\n✅ Analyse terminée. {len(results)} combinaisons testées.")
        print(f"🏆 Meilleure performance: {results[0]['success_rate']:.1f}% avec {results[0]['combo_name']}")
    else:
        print(f"\n❌ Échec de l'analyse.")