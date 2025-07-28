#!/usr/bin/env python3
"""
Analyse des ratios par position et performance
Objectifs:
1. Vérifier si un ratio 1.3 sur photo1 gagne plus souvent qu'un ratio 1.3 sur photo2
2. Identifier entre quels ratios et positions le vote est plus favorable que le ratio
"""

import pandas as pd
import numpy as np
import sys
import os

# Importer le module d'application d'algorithme
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def analyze_ratios_by_position():
    """Analyse les ratios par position avec une décimale"""
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
        
        print("\n🔍 === ANALYSE 1: PERFORMANCE PAR RATIO ET POSITION ===")
        
        # Analyser photo1
        print("\n📊 Photo1 - Performance par ratio:")
        photo1_analysis = df_with_winner.groupby('photo1_ratio_round').agg({
            'photo1_wins': ['count', 'sum', 'mean'],
            'photo1_votes': 'mean',
            'photo1_rank': 'mean'
        }).round(3)
        
        photo1_analysis.columns = ['total_cases', 'wins', 'win_rate', 'avg_votes', 'avg_rank']
        photo1_analysis = photo1_analysis[photo1_analysis['total_cases'] >= 10].sort_index()  # Au moins 10 cas
        
        print("Ratio | Cases | Wins | Win% | AvgVotes | AvgRank")
        print("-" * 50)
        for ratio, row in photo1_analysis.iterrows():
            print(f"{ratio:4.1f} | {row['total_cases']:5.0f} | {row['wins']:4.0f} | {row['win_rate']*100:4.1f}% | {row['avg_votes']:8.0f} | {row['avg_rank']:7.0f}")
        
        # Analyser photo2 (en inversant la logique)
        print("\n📊 Photo2 - Performance par ratio:")
        df_with_winner['photo2_wins'] = ~df_with_winner['photo1_wins']
        photo2_analysis = df_with_winner.groupby('photo2_ratio_round').agg({
            'photo2_wins': ['count', 'sum', 'mean'],
            'photo2_votes': 'mean',
            'photo2_rank': 'mean'
        }).round(3)
        
        photo2_analysis.columns = ['total_cases', 'wins', 'win_rate', 'avg_votes', 'avg_rank']
        photo2_analysis = photo2_analysis[photo2_analysis['total_cases'] >= 10].sort_index()  # Au moins 10 cas
        
        print("Ratio | Cases | Wins | Win% | AvgVotes | AvgRank")
        print("-" * 50)
        for ratio, row in photo2_analysis.iterrows():
            print(f"{ratio:4.1f} | {row['total_cases']:5.0f} | {row['wins']:4.0f} | {row['win_rate']*100:4.1f}% | {row['avg_votes']:8.0f} | {row['avg_rank']:7.0f}")
        
        print("\n🔍 === ANALYSE 2: COMPARAISON DIRECTE MÊME RATIO ===")
        
        # Comparer les performances pour les mêmes ratios
        common_ratios = set(photo1_analysis.index) & set(photo2_analysis.index)
        common_ratios = sorted([r for r in common_ratios if r >= 1.0])  # Ratios >= 1.0 seulement
        
        print("Ratio | Photo1_Win% | Photo2_Win% | Différence | Avantage")
        print("-" * 65)
        position_advantage = []
        
        for ratio in common_ratios:
            p1_rate = photo1_analysis.loc[ratio, 'win_rate'] * 100
            p2_rate = photo2_analysis.loc[ratio, 'win_rate'] * 100
            diff = p1_rate - p2_rate
            advantage = "Photo1" if diff > 2 else "Photo2" if diff < -2 else "Équilibré"
            
            position_advantage.append({
                'ratio': ratio,
                'photo1_rate': p1_rate,
                'photo2_rate': p2_rate,
                'difference': diff,
                'advantage': advantage
            })
            
            print(f"{ratio:4.1f} | {p1_rate:10.1f}% | {p2_rate:10.1f}% | {diff:9.1f}% | {advantage}")
        
        print("\n🔍 === ANALYSE 3: AVEC ALGORITHMES D'ENSEMBLE ===")
        
        # Appliquer l'ensemble d'algorithmes sur un échantillon
        sample_size = min(500, len(df_with_winner))
        df_sample = df_with_winner.sample(n=sample_size, random_state=42)
        
        print(f"🤖 Application ensemble sur échantillon de {sample_size} entrées...")
        df_with_algo = apply_algorithm_to_query_result(df_sample, '[votes_high,ratio_low,hybrid]')
        
        # Analyser où l'ensemble bat le simple ratio
        if 'majority_choice' in df_with_algo.columns:
            # Créer un algorithme "ratio simple" (toujours choisir le ratio le plus élevé)
            df_with_algo['simple_ratio_choice'] = df_with_algo.apply(
                lambda row: row['photo1_id'] if row['photo1_ratio'] > row['photo2_ratio'] 
                else row['photo2_id'] if row['photo2_ratio'] > row['photo1_ratio']
                else row['photo1_id'],  # En cas d'égalité, choisir photo1
                axis=1
            )
            
            # Calculer les succès
            df_with_algo['simple_ratio_success'] = (df_with_algo['simple_ratio_choice'] == df_with_algo['winner_id'])
            df_with_algo['ensemble_better'] = (
                (df_with_algo['majority_success'] == True) & 
                (df_with_algo['simple_ratio_success'] == False)
            )
            
            # Analyser par combinaisons de ratios
            df_with_algo['ratio_combo'] = df_with_algo.apply(
                lambda row: f"{row['photo1_ratio_round']:.1f}vs{row['photo2_ratio_round']:.1f}",
                axis=1
            )
            
            combo_analysis = df_with_algo.groupby('ratio_combo').agg({
                'simple_ratio_success': ['count', 'sum', 'mean'],
                'majority_success': ['sum', 'mean'],
                'ensemble_better': 'sum'
            }).round(3)
            
            combo_analysis.columns = ['total', 'ratio_wins', 'ratio_rate', 'ensemble_wins', 'ensemble_rate', 'ensemble_better_count']
            combo_analysis = combo_analysis[combo_analysis['total'] >= 5].sort_values('ensemble_better_count', ascending=False)
            
            print("\nCombinaisons où l'ensemble bat le ratio simple:")
            print("Combo      | Cases | Ratio% | Ensemble% | Ens>Ratio")
            print("-" * 55)
            for combo, row in combo_analysis.head(15).iterrows():
                if row['ensemble_better_count'] > 0:
                    print(f"{combo:10} | {row['total']:5.0f} | {row['ratio_rate']*100:5.1f}% | {row['ensemble_rate']*100:8.1f}% | {row['ensemble_better_count']:8.0f}")
        
        print("\n🔍 === RÉSUMÉ ===")
        
        # Calculer les tendances générales
        p1_overall = df_with_winner['photo1_wins'].mean() * 100
        print(f"📊 Photo1 gagne globalement: {p1_overall:.1f}%")
        print(f"📊 Photo2 gagne globalement: {100-p1_overall:.1f}%")
        
        # Avantage de position le plus marqué
        if position_advantage:
            max_advantage = max(position_advantage, key=lambda x: abs(x['difference']))
            print(f"🎯 Plus grand avantage de position: Ratio {max_advantage['ratio']:.1f}")
            print(f"   {max_advantage['advantage']} avec {abs(max_advantage['difference']):.1f}% d'avantage")
        
        # Conseil stratégique
        print("\n💡 INSIGHTS STRATÉGIQUES:")
        strong_photo1_ratios = [r for r in common_ratios if photo1_analysis.loc[r, 'win_rate'] > 0.6]
        strong_photo2_ratios = [r for r in common_ratios if photo2_analysis.loc[r, 'win_rate'] > 0.6]
        
        if strong_photo1_ratios:
            print(f"✅ Ratios favorables en Photo1: {strong_photo1_ratios}")
        if strong_photo2_ratios:
            print(f"✅ Ratios favorables en Photo2: {strong_photo2_ratios}")
            
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def sql_like_query_ratios():
    """Requête SQL-like pour analyser les ratios"""
    try:
        df = pd.read_feather('turbos.feather')
        
        # Équivalent SQL: SELECT ROUND(photo1_ratio,1) as p1_ratio, ROUND(photo2_ratio,1) as p2_ratio, 
        #                        COUNT(*) as cases, AVG(winner_id = photo1_id) as photo1_win_rate
        #                 FROM turbos WHERE winner_id IS NOT NULL 
        #                 GROUP BY p1_ratio, p2_ratio 
        #                 ORDER BY p1_ratio, p2_ratio
        
        query_result = df.query("winner_id.notna() and winner_id != ''").copy()
        query_result['p1_ratio'] = query_result['photo1_ratio'].round(1)
        query_result['p2_ratio'] = query_result['photo2_ratio'].round(1)
        query_result['photo1_wins'] = (query_result['winner_id'] == query_result['photo1_id'])
        
        sql_like_result = query_result.groupby(['p1_ratio', 'p2_ratio']).agg({
            'photo1_wins': ['count', 'mean'],
            'photo1_votes': 'mean',
            'photo2_votes': 'mean'
        }).round(3)
        
        sql_like_result.columns = ['cases', 'photo1_win_rate', 'avg_p1_votes', 'avg_p2_votes']
        sql_like_result = sql_like_result[sql_like_result['cases'] >= 5].sort_index()
        
        print("🗃️ === REQUÊTE SQL-LIKE: RATIOS PAR POSITION ===")
        print("P1_Ratio | P2_Ratio | Cases | P1_Win% | AvgP1_Votes | AvgP2_Votes")
        print("-" * 70)
        
        for (p1_r, p2_r), row in sql_like_result.iterrows():
            print(f"{p1_r:7.1f} | {p2_r:7.1f} | {row['cases']:5.0f} | {row['photo1_win_rate']*100:6.1f}% | {row['avg_p1_votes']:10.0f} | {row['avg_p2_votes']:10.0f}")
            
        return sql_like_result
        
    except Exception as e:
        print(f"❌ Erreur requête SQL-like: {e}")
        return None

if __name__ == "__main__":
    print("🔍 === ANALYSE DES RATIOS PAR POSITION ===\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "sql":
        # Mode requête SQL-like seulement
        sql_like_query_ratios()
    else:
        # Analyse complète
        analyze_ratios_by_position()
        print("\n" + "="*60)
        sql_like_query_ratios()
        
    print(f"\n💡 Usage: python {sys.argv[0]} [sql]")
    print("   python analyze_ratios_position.py     # Analyse complète")
    print("   python analyze_ratios_position.py sql # Requête SQL-like seulement")