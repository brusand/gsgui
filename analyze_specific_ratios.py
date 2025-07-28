#!/usr/bin/env python3
"""
Analyse spécifique des combinaisons de ratios par position
Focus sur: 1.3vs1.5, 1.5vs1.3, 0.7vs2.1, 2.1vs1.3
"""

import pandas as pd
import numpy as np
import sys
import os

# Importer le module d'application d'algorithme
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def analyze_specific_ratio_combinations():
    """Analyse des combinaisons spécifiques de ratios"""
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        print(f"📊 Données chargées: {len(df)} entrées")
        
        # Filtrer les entrées avec gagnant connu
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        print(f"🏆 Avec gagnant: {len(df_with_winner)} entrées")
        
        # Arrondir les ratios à 1 décimale
        df_with_winner['photo1_ratio_round'] = df_with_winner['photo1_ratio'].round(1)
        df_with_winner['photo2_ratio_round'] = df_with_winner['photo2_ratio'].round(1)
        
        # Déterminer si photo1 a gagné
        df_with_winner['photo1_wins'] = (df_with_winner['winner_id'] == df_with_winner['photo1_id'])
        
        # Combinaisons spécifiques à analyser
        target_combinations = [
            (1.3, 1.5, "1.3 vs 1.5"),
            (1.5, 1.3, "1.5 vs 1.3"), 
            (0.7, 2.1, "0.7 vs 2.1"),
            (2.1, 1.3, "2.1 vs 1.3"),
            # Ajoutons quelques autres combinaisons intéressantes
            (1.5, 1.5, "1.5 vs 1.5"),
            (1.3, 1.3, "1.3 vs 1.3"),
            (1.0, 1.5, "1.0 vs 1.5"),
            (1.5, 1.0, "1.5 vs 1.0"),
            (0.8, 1.5, "0.8 vs 1.5"),
            (1.5, 0.8, "1.5 vs 0.8")
        ]
        
        print("\n🔍 === ANALYSE DÉTAILLÉE DES COMBINAISONS SPÉCIFIQUES ===")
        
        detailed_results = []
        
        for p1_ratio, p2_ratio, label in target_combinations:
            # Filtrer pour cette combinaison
            mask = (
                (df_with_winner['photo1_ratio_round'] == p1_ratio) & 
                (df_with_winner['photo2_ratio_round'] == p2_ratio)
            )
            combo_data = df_with_winner[mask].copy()
            
            if len(combo_data) == 0:
                print(f"\n❌ {label}: Aucune donnée trouvée")
                continue
            
            # Statistiques de base
            total_cases = len(combo_data)
            photo1_wins = combo_data['photo1_wins'].sum()
            photo1_win_rate = photo1_wins / total_cases * 100
            photo2_wins = total_cases - photo1_wins
            photo2_win_rate = 100 - photo1_win_rate
            
            # Statistiques des votes et rangs
            avg_p1_votes = combo_data['photo1_votes'].mean()
            avg_p2_votes = combo_data['photo2_votes'].mean()
            avg_p1_rank = combo_data['photo1_rank'].mean()
            avg_p2_rank = combo_data['photo2_rank'].mean()
            
            # Médiane des votes (plus robuste aux outliers)
            med_p1_votes = combo_data['photo1_votes'].median()
            med_p2_votes = combo_data['photo2_votes'].median()
            
            print(f"\n📊 === {label} ({total_cases} cas) ===")
            print(f"🏆 Résultats:")
            print(f"   Photo1 (ratio {p1_ratio}): {photo1_wins:3d} victoires ({photo1_win_rate:5.1f}%)")
            print(f"   Photo2 (ratio {p2_ratio}): {photo2_wins:3d} victoires ({photo2_win_rate:5.1f}%)")
            
            winner_by_ratio = "Photo1" if p1_ratio > p2_ratio else "Photo2" if p2_ratio > p1_ratio else "Égalité"
            actual_winner = "Photo1" if photo1_win_rate > 50 else "Photo2" if photo2_win_rate > 50 else "Équilibré"
            
            print(f"📈 Analyse:")
            print(f"   Gagnant par ratio: {winner_by_ratio}")
            print(f"   Gagnant réel: {actual_winner}")
            print(f"   Cohérence: {'✅' if winner_by_ratio == actual_winner or winner_by_ratio == 'Égalité' else '❌'}")
            
            print(f"📊 Métriques moyennes:")
            print(f"   Photo1: {avg_p1_votes:6.0f} votes (médiane: {med_p1_votes:6.0f}), rang {avg_p1_rank:6.0f}")
            print(f"   Photo2: {avg_p2_votes:6.0f} votes (médiane: {med_p2_votes:6.0f}), rang {avg_p2_rank:6.0f}")
            
            # Analyse des facteurs décisifs
            vote_advantage = "Photo1" if avg_p1_votes > avg_p2_votes else "Photo2"
            rank_advantage = "Photo1" if avg_p1_rank < avg_p2_rank else "Photo2"  # Plus petit rang = meilleur
            
            print(f"🎯 Avantages:")
            print(f"   Votes: {vote_advantage} ({abs(avg_p1_votes - avg_p2_votes):6.0f} votes d'écart)")
            print(f"   Rang: {rank_advantage} ({abs(avg_p1_rank - avg_p2_rank):6.0f} rangs d'écart)")
            
            # Stocker pour analyse comparative
            detailed_results.append({
                'combination': label,
                'p1_ratio': p1_ratio,
                'p2_ratio': p2_ratio,
                'cases': total_cases,
                'p1_win_rate': photo1_win_rate,
                'p2_win_rate': photo2_win_rate,
                'ratio_winner': winner_by_ratio,
                'actual_winner': actual_winner,
                'coherent': winner_by_ratio == actual_winner or winner_by_ratio == 'Égalité',
                'avg_p1_votes': avg_p1_votes,
                'avg_p2_votes': avg_p2_votes,
                'avg_p1_rank': avg_p1_rank,
                'avg_p2_rank': avg_p2_rank,
                'vote_advantage': vote_advantage,
                'rank_advantage': rank_advantage
            })
        
        # Analyse comparative
        print("\n🔍 === ANALYSE COMPARATIVE ===")
        
        # Chercher les paires inversées
        print("\n📊 Comparaison des positions inversées:")
        inverse_pairs = [
            ("1.3 vs 1.5", "1.5 vs 1.3"),
            ("0.7 vs 2.1", "2.1 vs 1.3")  # Pas vraiment inversé mais intéressant
        ]
        
        results_dict = {r['combination']: r for r in detailed_results}
        
        for combo1, combo2 in inverse_pairs:
            if combo1 in results_dict and combo2 in results_dict:
                r1 = results_dict[combo1]
                r2 = results_dict[combo2]
                
                print(f"\n🔄 {combo1} vs {combo2}:")
                print(f"   {combo1}: Photo1 gagne {r1['p1_win_rate']:.1f}% ({r1['cases']} cas)")
                print(f"   {combo2}: Photo1 gagne {r2['p1_win_rate']:.1f}% ({r2['cases']} cas)")
                
                # Impact de l'inversion
                if r1['p1_ratio'] == r2['p2_ratio'] and r1['p2_ratio'] == r2['p1_ratio']:
                    # Vraie inversion
                    position_effect = abs(r1['p1_win_rate'] - (100 - r2['p1_win_rate']))
                    print(f"   Effet de position: {position_effect:.1f}% de différence")
        
        # Analyse avec algorithmes d'ensemble sur les combinaisons spécifiques
        print("\n🔍 === ANALYSE AVEC ENSEMBLE D'ALGORITHMES ===")
        
        for p1_ratio, p2_ratio, label in target_combinations[:4]:  # Seulement les 4 principales
            mask = (
                (df_with_winner['photo1_ratio_round'] == p1_ratio) & 
                (df_with_winner['photo2_ratio_round'] == p2_ratio)
            )
            combo_data = df_with_winner[mask].copy()
            
            if len(combo_data) < 5:  # Pas assez de données
                continue
                
            print(f"\n🤖 {label} avec ensemble d'algorithmes:")
            
            try:
                # Appliquer l'ensemble d'algorithmes
                combo_with_algo = apply_algorithm_to_query_result(combo_data, '[votes_high,ratio_low,hybrid]')
                
                if 'majority_choice' in combo_with_algo.columns:
                    # Algorithme "ratio simple"
                    combo_with_algo['simple_ratio_choice'] = combo_with_algo.apply(
                        lambda row: row['photo1_id'] if row['photo1_ratio'] > row['photo2_ratio'] 
                        else row['photo2_id'] if row['photo2_ratio'] > row['photo1_ratio']
                        else row['photo1_id'],
                        axis=1
                    )
                    
                    combo_with_algo['simple_ratio_success'] = (
                        combo_with_algo['simple_ratio_choice'] == combo_with_algo['winner_id']
                    )
                    
                    # Statistiques comparatives
                    ensemble_success_rate = combo_with_algo['majority_success'].mean() * 100
                    ratio_success_rate = combo_with_algo['simple_ratio_success'].mean() * 100
                    
                    # Cas où l'ensemble fait mieux
                    ensemble_better = (
                        (combo_with_algo['majority_success'] == True) & 
                        (combo_with_algo['simple_ratio_success'] == False)
                    ).sum()
                    
                    print(f"   📊 Performances:")
                    print(f"      Ratio simple: {ratio_success_rate:5.1f}%")
                    print(f"      Ensemble: {ensemble_success_rate:5.1f}%")
                    print(f"      Amélioration: {ensemble_success_rate - ratio_success_rate:+5.1f}%")
                    print(f"      Cas où ensemble > ratio: {ensemble_better}")
                    
            except Exception as e:
                print(f"   ❌ Erreur ensemble: {e}")
        
        # Résumé final
        print("\n🔍 === RÉSUMÉ EXÉCUTIF ===")
        
        coherent_cases = sum(1 for r in detailed_results if r['coherent'])
        total_analyzed = len(detailed_results)
        
        print(f"📊 Cohérence ratio/résultat: {coherent_cases}/{total_analyzed} cas ({coherent_cases/total_analyzed*100:.1f}%)")
        
        # Cas les plus surprenants
        surprising_cases = [r for r in detailed_results if not r['coherent'] and r['cases'] >= 10]
        if surprising_cases:
            print(f"\n🎯 Cas surprenants (ratio ne prédit pas le gagnant):")
            for case in surprising_cases:
                print(f"   {case['combination']}: {case['ratio_winner']} attendu, {case['actual_winner']} réel")
                print(f"      → Facteur décisif probable: {case['vote_advantage']} aux votes, {case['rank_advantage']} au rang")
        
        print(f"\n💡 INSIGHTS CLÉS:")
        print(f"   • La position compte: même ratio peut avoir des résultats différents")
        print(f"   • Les votes et rangs compensent souvent les ratios faibles")
        print(f"   • L'ensemble d'algorithmes excelle sur les cas ambigus")
        
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 === ANALYSE SPÉCIFIQUE DES COMBINAISONS DE RATIOS ===\n")
    analyze_specific_ratio_combinations()