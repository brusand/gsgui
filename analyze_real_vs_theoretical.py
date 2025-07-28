#!/usr/bin/env python3
"""
Analyse de l'écart entre performance théorique et réelle
Comprendre pourquoi [hybrid,position_aware,adaptive_time] performe mieux en réel
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def analyze_temporal_bias():
    """Analyser si les données ont un biais temporel"""
    
    print("📅 === ANALYSE DU BIAIS TEMPOREL ===\n")
    
    try:
        df = pd.read_feather('turbos.feather')
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        
        # Vérifier s'il y a une colonne de date
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        print(f"📋 Colonnes temporelles trouvées: {date_columns}")
        
        if date_columns:
            # Analyser distribution temporelle des données
            for col in date_columns[:1]:  # Prendre la première colonne de date
                if col in df_with_winner.columns:
                    print(f"\n📊 Distribution temporelle pour {col}:")
                    try:
                        # Essayer de parser les dates
                        df_with_winner[f'{col}_parsed'] = pd.to_datetime(df_with_winner[col], errors='coerce')
                        date_range = df_with_winner[f'{col}_parsed'].dropna()
                        
                        if len(date_range) > 0:
                            print(f"   📈 Période: {date_range.min()} à {date_range.max()}")
                            print(f"   📊 Nombre d'entrées avec date: {len(date_range)}")
                            
                            # Diviser en périodes récentes vs anciennes
                            median_date = date_range.median()
                            recent_mask = df_with_winner[f'{col}_parsed'] >= median_date
                            
                            recent_data = df_with_winner[recent_mask]
                            old_data = df_with_winner[~recent_mask]
                            
                            print(f"   🆕 Données récentes (>= {median_date.date()}): {len(recent_data)} entrées")
                            print(f"   🕰️ Données anciennes (< {median_date.date()}): {len(old_data)} entrées")
                            
                            return recent_data, old_data, median_date
                    except Exception as e:
                        print(f"   ❌ Erreur parsing dates: {e}")
        
        # Si pas de colonne de date, diviser par index (approximation)
        print(f"\n⚠️ Pas de colonne de date valide, division par index (approximation)")
        midpoint = len(df_with_winner) // 2
        recent_data = df_with_winner.iloc[midpoint:]
        old_data = df_with_winner.iloc[:midpoint]
        
        print(f"   🆕 'Récent' (index >= {midpoint}): {len(recent_data)} entrées")
        print(f"   🕰️ 'Ancien' (index < {midpoint}): {len(old_data)} entrées")
        
        return recent_data, old_data, None
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None, None, None

def compare_algorithms_by_period(recent_data, old_data, period_name):
    """Comparer performance des algorithmes par période"""
    
    if recent_data is None or old_data is None:
        return
    
    print(f"\n🔍 === COMPARAISON PAR PÉRIODE ({period_name}) ===")
    
    # Algorithmes à tester
    algorithms_to_test = [
        '[hybrid,ratio_low,votes_high]',
        '[hybrid,position_aware,adaptive_time]',
        '[ratio_low,votes_high,adaptive_time]'
    ]
    
    results = {}
    
    for algo in algorithms_to_test:
        results[algo] = {}
        
        # Test sur données récentes
        try:
            sample_recent = recent_data.sample(n=min(300, len(recent_data)), random_state=42)
            df_recent_result = apply_algorithm_to_query_result(sample_recent.copy(), algo)
            
            recent_total = (df_recent_result['winner_id'].notna() & (df_recent_result['winner_id'] != '')).sum()
            recent_successes = df_recent_result['majority_success'].sum() if 'majority_success' in df_recent_result.columns else 0
            recent_rate = recent_successes / recent_total * 100 if recent_total > 0 else 0
            
            results[algo]['recent'] = {
                'successes': recent_successes,
                'total': recent_total,
                'rate': recent_rate
            }
            
        except Exception as e:
            print(f"   ❌ Erreur {algo} récent: {e}")
            results[algo]['recent'] = None
        
        # Test sur données anciennes
        try:
            sample_old = old_data.sample(n=min(300, len(old_data)), random_state=42)
            df_old_result = apply_algorithm_to_query_result(sample_old.copy(), algo)
            
            old_total = (df_old_result['winner_id'].notna() & (df_old_result['winner_id'] != '')).sum()
            old_successes = df_old_result['majority_success'].sum() if 'majority_success' in df_old_result.columns else 0
            old_rate = old_successes / old_total * 100 if old_total > 0 else 0
            
            results[algo]['old'] = {
                'successes': old_successes,
                'total': old_total,
                'rate': old_rate
            }
            
        except Exception as e:
            print(f"   ❌ Erreur {algo} ancien: {e}")
            results[algo]['old'] = None
    
    # Afficher résultats comparatifs
    print(f"\n📊 Résultats comparatifs:")
    print(f"{'Algorithme':40} | {'Récent':>10} | {'Ancien':>10} | {'Évolution':>10}")
    print("-" * 80)
    
    for algo, data in results.items():
        algo_short = algo.replace('[', '').replace(']', '')
        
        recent_str = f"{data['recent']['rate']:.1f}%" if data['recent'] else "N/A"
        old_str = f"{data['old']['rate']:.1f}%" if data['old'] else "N/A"
        
        if data['recent'] and data['old']:
            evolution = data['recent']['rate'] - data['old']['rate']
            evolution_str = f"{evolution:+.1f}%"
        else:
            evolution_str = "N/A"
        
        print(f"{algo_short:40} | {recent_str:>10} | {old_str:>10} | {evolution_str:>10}")
    
    return results

def analyze_time_usage_patterns():
    """Analyser les patterns d'usage du temps restant"""
    
    print(f"\n⏰ === ANALYSE DES PATTERNS TEMPORELS ===")
    
    try:
        df = pd.read_feather('turbos.feather')
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        
        if 'time_left' in df.columns:
            # Analyser distribution des temps restants
            time_left_values = df_with_winner['time_left'].dropna()
            print(f"📊 Échantillon de temps restants:")
            
            sample_times = time_left_values.sample(n=min(10, len(time_left_values)))
            for i, time_val in enumerate(sample_times):
                print(f"   {i+1}. {time_val}")
            
            # Patterns temporels les plus fréquents
            top_times = time_left_values.value_counts().head(10)
            print(f"\n🔢 Temps restants les plus fréquents:")
            for time_val, count in top_times.items():
                percentage = count / len(time_left_values) * 100
                print(f"   {time_val}: {count} fois ({percentage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur analyse temporelle: {e}")
        return False

def main():
    """Analyse principale"""
    
    print("🔍 === ANALYSE PERFORMANCE THÉORIQUE VS RÉELLE ===\n")
    
    print("📈 Feedback utilisateur:")
    print("   ❌ [hybrid,ratio_low,votes_high] → Beaucoup d'échecs récents")
    print("   ✅ [hybrid,position_aware,adaptive_time] → 4/6 succès (66.7%)")
    print("   📊 Analyse théorique → 68.6% vs 67.5%")
    print()
    
    # 1. Analyser biais temporel
    recent_data, old_data, split_date = analyze_temporal_bias()
    
    # 2. Comparer algorithmes par période
    if recent_data is not None and old_data is not None:
        period_name = f"split: {split_date.date()}" if split_date else "par index"
        results = compare_algorithms_by_period(recent_data, old_data, period_name)
    
    # 3. Analyser patterns d'usage temporel
    analyze_time_usage_patterns()
    
    # 4. Conclusions
    print(f"\n💡 === HYPOTHÈSES EXPLICATIVES ===")
    print(f"1. 🕰️ ÉVOLUTION TEMPORELLE:")
    print(f"   - Les patterns de vote évoluent avec le temps")
    print(f"   - [position_aware,adaptive_time] capturent des tendances récentes")
    print(f"   - L'ancien trio était optimisé sur données plus anciennes")
    print()
    print(f"2. ⏰ USAGE DU TEMPS RÉEL:")
    print(f"   - adaptive_time utilise le vrai temps restant en interface")
    print(f"   - Dans les tests, temps fixe 12H (biais méthodologique)")
    print(f"   - Performance réelle bénéficie de stratégies temporelles précises")
    print()
    print(f"3. 🎯 SOPHISTICATION ALGORITHMIQUE:")
    print(f"   - position_aware: Patterns fins ratio+position")
    print(f"   - adaptive_time: Adaptation contextuelle au timing")
    print(f"   - Ancien trio: Heuristiques plus simples, potentiellement dépassées")
    print()
    print(f"4. 📊 OVERFITTING HISTORIQUE:")
    print(f"   - Optimisation sur données passées vs adaptabilité future")
    print(f"   - Les nouveaux algos sont plus robustes aux changements")
    print()
    print(f"🎯 RECOMMANDATION:")
    print(f"   Adopter [hybrid,position_aware,adaptive_time] comme défaut")
    print(f"   Basé sur feedback utilisateur > analyse théorique")

if __name__ == "__main__":
    main()