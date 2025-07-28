#!/usr/bin/env python3
"""
Extraction et analyse complète de tous les ratios à 0.1 près par position
Analyse exhaustive pour servir de base à un nouvel algorithme
"""

import pandas as pd
import numpy as np
import sys
import os
import json
from collections import defaultdict

def extract_all_ratios_comprehensive():
    """Extraction et analyse complète de tous les ratios"""
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        print(f"📊 Données chargées: {len(df)} entrées")
        
        # Filtrer les entrées avec gagnant connu
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        print(f"🏆 Avec gagnant: {len(df_with_winner)} entrées")
        
        # Arrondir les ratios à 0.1 près
        df_with_winner['p1_ratio'] = df_with_winner['photo1_ratio'].round(1)
        df_with_winner['p2_ratio'] = df_with_winner['photo2_ratio'].round(1)
        
        # Déterminer le gagnant
        df_with_winner['p1_wins'] = (df_with_winner['winner_id'] == df_with_winner['photo1_id'])
        
        print("\n🔍 === EXTRACTION DE TOUS LES RATIOS ===")
        
        # 1. ANALYSE PAR RATIO INDIVIDUEL ET POSITION
        print("\n📊 === ANALYSE PAR RATIO ET POSITION ===")
        
        # Photo1 ratios
        p1_analysis = df_with_winner.groupby('p1_ratio').agg({
            'p1_wins': ['count', 'sum', 'mean'],
            'photo1_votes': ['mean', 'median', 'std'],
            'photo1_rank': ['mean', 'median', 'std']
        }).round(3)
        
        p1_analysis.columns = [
            'cases', 'wins', 'win_rate', 
            'votes_mean', 'votes_median', 'votes_std',
            'rank_mean', 'rank_median', 'rank_std'
        ]
        
        # Photo2 ratios (inverser la logique pour les victoires)
        df_with_winner['p2_wins'] = ~df_with_winner['p1_wins']
        p2_analysis = df_with_winner.groupby('p2_ratio').agg({
            'p2_wins': ['count', 'sum', 'mean'],
            'photo2_votes': ['mean', 'median', 'std'],
            'photo2_rank': ['mean', 'median', 'std']
        }).round(3)
        
        p2_analysis.columns = [
            'cases', 'wins', 'win_rate',
            'votes_mean', 'votes_median', 'votes_std', 
            'rank_mean', 'rank_median', 'rank_std'
        ]
        
        # Obtenir tous les ratios uniques
        all_ratios = sorted(set(df_with_winner['p1_ratio'].unique()) | set(df_with_winner['p2_ratio'].unique()))
        all_ratios = [r for r in all_ratios if r >= 0.0]  # Garder tous les ratios >= 0
        
        print(f"📈 Ratios trouvés: {len(all_ratios)} ratios uniques de {min(all_ratios):.1f} à {max(all_ratios):.1f}")
        print(f"📈 Distribution: {all_ratios}")
        
        # 2. CRÉATION DU TABLEAU COMPLET
        print(f"\n📊 === TABLEAU COMPLET PAR RATIO ET POSITION ===")
        
        complete_analysis = []
        
        for ratio in all_ratios:
            # Données Photo1
            p1_data = {
                'ratio': ratio,
                'position': 'Photo1',
                'cases': p1_analysis.loc[ratio, 'cases'] if ratio in p1_analysis.index else 0,
                'wins': p1_analysis.loc[ratio, 'wins'] if ratio in p1_analysis.index else 0,
                'win_rate': p1_analysis.loc[ratio, 'win_rate'] if ratio in p1_analysis.index else 0,
                'votes_mean': p1_analysis.loc[ratio, 'votes_mean'] if ratio in p1_analysis.index else 0,
                'votes_median': p1_analysis.loc[ratio, 'votes_median'] if ratio in p1_analysis.index else 0,
                'votes_std': p1_analysis.loc[ratio, 'votes_std'] if ratio in p1_analysis.index else 0,
                'rank_mean': p1_analysis.loc[ratio, 'rank_mean'] if ratio in p1_analysis.index else 999,
                'rank_median': p1_analysis.loc[ratio, 'rank_median'] if ratio in p1_analysis.index else 999,
                'rank_std': p1_analysis.loc[ratio, 'rank_std'] if ratio in p1_analysis.index else 0
            }
            
            # Données Photo2 
            p2_data = {
                'ratio': ratio,
                'position': 'Photo2',
                'cases': p2_analysis.loc[ratio, 'cases'] if ratio in p2_analysis.index else 0,
                'wins': p2_analysis.loc[ratio, 'wins'] if ratio in p2_analysis.index else 0,
                'win_rate': p2_analysis.loc[ratio, 'win_rate'] if ratio in p2_analysis.index else 0,
                'votes_mean': p2_analysis.loc[ratio, 'votes_mean'] if ratio in p2_analysis.index else 0,
                'votes_median': p2_analysis.loc[ratio, 'votes_median'] if ratio in p2_analysis.index else 0,
                'votes_std': p2_analysis.loc[ratio, 'votes_std'] if ratio in p2_analysis.index else 0,
                'rank_mean': p2_analysis.loc[ratio, 'rank_mean'] if ratio in p2_analysis.index else 999,
                'rank_median': p2_analysis.loc[ratio, 'rank_median'] if ratio in p2_analysis.index else 999,
                'rank_std': p2_analysis.loc[ratio, 'rank_std'] if ratio in p2_analysis.index else 0
            }
            
            complete_analysis.extend([p1_data, p2_data])
        
        # Convertir en DataFrame pour analyse
        analysis_df = pd.DataFrame(complete_analysis)
        
        # Filtrer les ratios avec au moins quelques cas
        significant_analysis = analysis_df[analysis_df['cases'] >= 3].copy()
        
        print(f"📊 Ratios avec >= 3 cas: {len(significant_analysis)} entrées")
        
        # Afficher le tableau complet
        print("\nRatio | Pos    | Cases | Wins | Rate%  | VotesMean | VotesMedian | RankMean | RankMedian")
        print("-" * 90)
        
        for _, row in significant_analysis.sort_values(['ratio', 'position']).iterrows():
            print(f"{row['ratio']:5.1f} | {row['position']:6} | {row['cases']:5.0f} | {row['wins']:4.0f} | {row['win_rate']*100:5.1f}% | {row['votes_mean']:8.0f} | {row['votes_median']:10.0f} | {row['rank_mean']:7.0f} | {row['rank_median']:9.0f}")
        
        # 3. ANALYSE COMPARATIVE PAR POSITION
        print(f"\n🔍 === ANALYSE COMPARATIVE PAR POSITION ===")
        
        # Comparer les mêmes ratios en différentes positions
        position_comparison = []
        
        for ratio in all_ratios:
            p1_row = significant_analysis[(significant_analysis['ratio'] == ratio) & (significant_analysis['position'] == 'Photo1')]
            p2_row = significant_analysis[(significant_analysis['ratio'] == ratio) & (significant_analysis['position'] == 'Photo2')]
            
            if len(p1_row) > 0 and len(p2_row) > 0:
                p1_data = p1_row.iloc[0]
                p2_data = p2_row.iloc[0]
                
                # Calculer les différences
                if p1_data['cases'] >= 5 and p2_data['cases'] >= 5:  # Au moins 5 cas chacun
                    comparison = {
                        'ratio': ratio,
                        'p1_cases': p1_data['cases'],
                        'p2_cases': p2_data['cases'],
                        'p1_win_rate': p1_data['win_rate'] * 100,
                        'p2_win_rate': p2_data['win_rate'] * 100,
                        'position_effect': abs(p1_data['win_rate'] - p2_data['win_rate']) * 100,
                        'better_position': 'Photo1' if p1_data['win_rate'] > p2_data['win_rate'] else 'Photo2',
                        'votes_diff': p1_data['votes_mean'] - p2_data['votes_mean'],
                        'rank_diff': p1_data['rank_mean'] - p2_data['rank_mean']  # Photo1_rank - Photo2_rank
                    }
                    position_comparison.append(comparison)
        
        # Trier par effet de position le plus important
        position_comparison.sort(key=lambda x: x['position_effect'], reverse=True)
        
        print("Ratio | P1Cases | P2Cases | P1Rate | P2Rate | Effect | Better   | VotesDiff | RankDiff")
        print("-" * 85)
        
        for comp in position_comparison:
            print(f"{comp['ratio']:5.1f} | {comp['p1_cases']:7.0f} | {comp['p2_cases']:7.0f} | {comp['p1_win_rate']:6.1f}% | {comp['p2_win_rate']:6.1f}% | {comp['position_effect']:6.1f}% | {comp['better_position']:8} | {comp['votes_diff']:8.0f} | {comp['rank_diff']:7.0f}")
        
        # 4. ANALYSE DES TENDANCES GÉNÉRALES
        print(f"\n📈 === TENDANCES GÉNÉRALES ===")
        
        # Ratios les plus performants par position
        p1_best = significant_analysis[significant_analysis['position'] == 'Photo1'].nlargest(5, 'win_rate')
        p2_best = significant_analysis[significant_analysis['position'] == 'Photo2'].nlargest(5, 'win_rate')
        
        print(f"\n🏆 Top 5 ratios Photo1:")
        for _, row in p1_best.iterrows():
            print(f"   Ratio {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        print(f"\n🏆 Top 5 ratios Photo2:")
        for _, row in p2_best.iterrows():
            print(f"   Ratio {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        # Effet de position global
        overall_p1_rate = significant_analysis[significant_analysis['position'] == 'Photo1']['win_rate'].mean() * 100
        overall_p2_rate = significant_analysis[significant_analysis['position'] == 'Photo2']['win_rate'].mean() * 100
        
        print(f"\n📊 Performance globale:")
        print(f"   Photo1 moyenne: {overall_p1_rate:.1f}%")
        print(f"   Photo2 moyenne: {overall_p2_rate:.1f}%")
        print(f"   Avantage global: {'Photo2' if overall_p2_rate > overall_p1_rate else 'Photo1'} (+{abs(overall_p2_rate - overall_p1_rate):.1f}%)")
        
        # 5. MATRICE DE TRANSITION ET PATTERNS
        print(f"\n🔍 === PATTERNS POUR ALGORITHME ===")
        
        # Ratios "sûrs" (>60% de win rate avec suffisamment de cas)
        safe_ratios_p1 = significant_analysis[
            (significant_analysis['position'] == 'Photo1') & 
            (significant_analysis['win_rate'] >= 0.6) & 
            (significant_analysis['cases'] >= 10)
        ]
        
        safe_ratios_p2 = significant_analysis[
            (significant_analysis['position'] == 'Photo2') & 
            (significant_analysis['win_rate'] >= 0.6) & 
            (significant_analysis['cases'] >= 10)
        ]
        
        print(f"\n✅ Ratios 'sûrs' Photo1 (≥60%, ≥10 cas):")
        for _, row in safe_ratios_p1.sort_values('win_rate', ascending=False).iterrows():
            print(f"   {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        print(f"\n✅ Ratios 'sûrs' Photo2 (≥60%, ≥10 cas):")
        for _, row in safe_ratios_p2.sort_values('win_rate', ascending=False).iterrows():
            print(f"   {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        # Ratios "dangereux" (<40% de win rate)
        risky_ratios_p1 = significant_analysis[
            (significant_analysis['position'] == 'Photo1') & 
            (significant_analysis['win_rate'] <= 0.4) & 
            (significant_analysis['cases'] >= 10)
        ]
        
        risky_ratios_p2 = significant_analysis[
            (significant_analysis['position'] == 'Photo2') & 
            (significant_analysis['win_rate'] <= 0.4) & 
            (significant_analysis['cases'] >= 10)
        ]
        
        print(f"\n⚠️ Ratios 'dangereux' Photo1 (≤40%, ≥10 cas):")
        for _, row in risky_ratios_p1.sort_values('win_rate').iterrows():
            print(f"   {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        print(f"\n⚠️ Ratios 'dangereux' Photo2 (≤40%, ≥10 cas):")
        for _, row in risky_ratios_p2.sort_values('win_rate').iterrows():
            print(f"   {row['ratio']:4.1f}: {row['win_rate']*100:5.1f}% ({row['cases']:3.0f} cas)")
        
        # 6. SAUVEGARDER LES DONNÉES POUR ALGORITHME
        print(f"\n💾 === SAUVEGARDE POUR ALGORITHME ===")
        
        # Créer structure pour nouvel algorithme
        algorithm_data = {
            'metadata': {
                'total_entries': len(df_with_winner),
                'unique_ratios': len(all_ratios),
                'ratio_range': [float(min(all_ratios)), float(max(all_ratios))],
                'significant_entries': len(significant_analysis)
            },
            'position_effects': position_comparison,
            'safe_ratios': {
                'photo1': safe_ratios_p1[['ratio', 'win_rate', 'cases']].to_dict('records'),
                'photo2': safe_ratios_p2[['ratio', 'win_rate', 'cases']].to_dict('records')
            },
            'risky_ratios': {
                'photo1': risky_ratios_p1[['ratio', 'win_rate', 'cases']].to_dict('records'),
                'photo2': risky_ratios_p2[['ratio', 'win_rate', 'cases']].to_dict('records')
            },
            'complete_analysis': significant_analysis.to_dict('records')
        }
        
        # Sauvegarder en JSON pour utilisation par algorithme
        with open('ratios_analysis_for_algorithm.json', 'w') as f:
            json.dump(algorithm_data, f, indent=2, default=str)
        
        # Sauvegarder aussi en CSV pour analyse manuelle
        significant_analysis.to_csv('ratios_complete_analysis.csv', index=False)
        
        print(f"✅ Données sauvegardées:")
        print(f"   - ratios_analysis_for_algorithm.json (pour nouvel algorithme)")
        print(f"   - ratios_complete_analysis.csv (analyse complète)")
        
        # 7. RÉSUMÉ POUR ALGORITHME
        print(f"\n🎯 === RÉSUMÉ POUR NOUVEL ALGORITHME ===")
        
        strongest_position_effects = sorted(position_comparison, key=lambda x: x['position_effect'], reverse=True)[:5]
        
        print(f"📊 Statistiques clés:")
        print(f"   • {len(all_ratios)} ratios uniques analysés")
        print(f"   • {len(position_comparison)} ratios avec effet de position mesurable")
        print(f"   • {len(safe_ratios_p1) + len(safe_ratios_p2)} ratios 'sûrs' identifiés")
        print(f"   • Photo2 a un avantage global de {abs(overall_p2_rate - overall_p1_rate):.1f}%")
        
        print(f"\n🔥 Top 3 effets de position les plus forts:")
        for i, effect in enumerate(strongest_position_effects[:3], 1):
            print(f"   {i}. Ratio {effect['ratio']:.1f}: {effect['position_effect']:.1f}% d'avantage pour {effect['better_position']}")
        
        print(f"\n💡 Recommandations pour nouvel algorithme:")
        print(f"   1. Intégrer les effets de position spécifiques par ratio")
        print(f"   2. Appliquer des bonus/malus selon les ratios 'sûrs'/'dangereux'")
        print(f"   3. Considérer l'avantage général de Photo2")
        print(f"   4. Utiliser votes et rang comme facteurs correctifs")
        
        return algorithm_data
        
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
        return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔍 === EXTRACTION COMPLÈTE DES RATIOS POUR ALGORITHME ===\n")
    result = extract_all_ratios_comprehensive()
    
    if result:
        print(f"\n✅ Analyse terminée. Données prêtes pour développement du nouvel algorithme.")
    else:
        print(f"\n❌ Échec de l'analyse.")