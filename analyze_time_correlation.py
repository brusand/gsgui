#!/usr/bin/env python3
"""
Analyse de la corrélation entre temps restant et performance des algorithmes
Hypothèse: Les algorithmes marchent mieux sur les challenges qui se terminent bientôt (<12h)
"""

import pandas as pd
import sys
import os
import re
from datetime import datetime, timedelta

# Importer le module d'application d'algorithme
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def parse_time_left(time_str):
    """Parse une chaîne 'XD YH ZM WS' en heures totales"""
    if pd.isna(time_str) or time_str == '':
        return None
    
    try:
        # Pattern pour capturer jours, heures, minutes, secondes
        pattern = r'(?:(\d+)D\s*)?(?:(\d+)H\s*)?(?:(\d+)M\s*)?(?:(\d+)S\s*)?'
        match = re.match(pattern, str(time_str).strip())
        
        if not match:
            return None
        
        days = int(match.group(1)) if match.group(1) else 0
        hours = int(match.group(2)) if match.group(2) else 0
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0
        
        total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
        return total_hours
        
    except Exception as e:
        print(f"Erreur parsing time_left '{time_str}': {e}")
        return None

def categorize_time_remaining(hours):
    """Catégorise le temps restant"""
    if hours is None:
        return "Unknown"
    elif hours <= 1:
        return "≤1h"
    elif hours <= 6:
        return "1-6h"
    elif hours <= 12:
        return "6-12h"
    elif hours <= 24:
        return "12-24h"
    elif hours <= 48:
        return "1-2d"
    else:
        return ">2d"

def analyze_time_correlation():
    """Analyse principale de la corrélation temps vs performance"""
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        print(f"📊 Données chargées: {len(df)} entrées")
        
        # Vérifier si on a une colonne time_left
        if 'time_left' not in df.columns:
            print("❌ Colonne 'time_left' non trouvée dans les données")
            print(f"📋 Colonnes disponibles: {list(df.columns)}")
            return
        
        # Filtrer les entrées avec gagnant connu
        df_with_winner = df[(df['winner_id'].notna()) & (df['winner_id'] != '')].copy()
        print(f"🏆 Avec gagnant: {len(df_with_winner)} entrées")
        
        # Parser le temps restant
        print("⏱️ Parsing des temps restants...")
        df_with_winner['time_left_hours'] = df_with_winner['time_left'].apply(parse_time_left)
        df_with_winner['time_category'] = df_with_winner['time_left_hours'].apply(categorize_time_remaining)
        
        # Statistiques des catégories temporelles
        print(f"\n📊 === DISTRIBUTION DES TEMPS RESTANTS ===")
        time_distribution = df_with_winner['time_category'].value_counts().sort_index()
        
        for category, count in time_distribution.items():
            percentage = count / len(df_with_winner) * 100
            print(f"   {category:8}: {count:4d} entrées ({percentage:5.1f}%)")
        
        # Analyser performance par catégorie temporelle
        print(f"\n🔍 === ANALYSE PAR ALGORITHME ET TEMPS RESTANT ===")
        
        algorithms_to_test = ['bruno_custom', 'position_aware', 'hybrid', 'votes_high']
        results_by_algo = {}
        
        for algo in algorithms_to_test:
            print(f"\n🤖 Test algorithme: {algo}")
            
            try:
                # Appliquer l'algorithme sur toutes les données
                df_with_algo = apply_algorithm_to_query_result(df_with_winner.copy(), algo)
                
                # Analyser par catégorie temporelle
                category_results = []
                
                for category in ['≤1h', '1-6h', '6-12h', '12-24h', '1-2d', '>2d']:
                    category_mask = df_with_algo['time_category'] == category
                    category_data = df_with_algo[category_mask]
                    
                    if len(category_data) == 0:
                        continue
                    
                    # Calculer taux de succès
                    total_cases = len(category_data)
                    successful_cases = category_data['algo_success'].sum() if 'algo_success' in category_data.columns else 0
                    success_rate = successful_cases / total_cases * 100 if total_cases > 0 else 0
                    
                    # Temps moyen
                    avg_time = category_data['time_left_hours'].mean()
                    
                    category_results.append({
                        'category': category,
                        'cases': total_cases,
                        'successes': successful_cases,
                        'success_rate': success_rate,
                        'avg_time_hours': avg_time
                    })
                    
                    print(f"   {category:8}: {successful_cases:3d}/{total_cases:3d} ({success_rate:5.1f}%) - avg: {avg_time:5.1f}h")
                
                results_by_algo[algo] = category_results
                
            except Exception as e:
                print(f"   ❌ Erreur avec {algo}: {e}")
                continue
        
        # Analyse comparative
        print(f"\n📈 === ANALYSE COMPARATIVE ===")
        
        # Trouver les tendances
        print(f"\n🔥 Performance par tranche temporelle:")
        
        time_categories = ['≤1h', '1-6h', '6-12h', '12-24h', '1-2d', '>2d']
        
        # Tableau comparatif
        print(f"\n{'Catégorie':>8} | {'Cases':>5} | " + " | ".join([f"{algo[:8]:>8}" for algo in algorithms_to_test]))
        print("-" * (8 + 5 + 3 + len(algorithms_to_test) * 11))
        
        for category in time_categories:
            line = f"{category:>8} | "
            
            # Nombre de cas pour cette catégorie
            category_cases = df_with_winner[df_with_winner['time_category'] == category]
            if len(category_cases) == 0:
                continue
                
            line += f"{len(category_cases):5d} | "
            
            # Performance de chaque algorithme
            for algo in algorithms_to_test:
                if algo in results_by_algo:
                    algo_result = next((r for r in results_by_algo[algo] if r['category'] == category), None)
                    if algo_result:
                        rate = algo_result['success_rate']
                        line += f"{rate:8.1f} | "
                    else:
                        line += f"{'N/A':>8} | "
                else:
                    line += f"{'ERR':>8} | "
            
            print(line)
        
        # Hypothèse validation
        print(f"\n🎯 === VALIDATION DE L'HYPOTHÈSE ===")
        
        # Performance générale dans les différentes tranches
        short_term_categories = ['≤1h', '1-6h', '6-12h']  # ≤12h
        long_term_categories = ['12-24h', '1-2d', '>2d']    # >12h
        
        for algo in algorithms_to_test:
            if algo not in results_by_algo:
                continue
                
            # Calculer performance moyenne court terme vs long terme
            short_term_total = sum(r['cases'] for r in results_by_algo[algo] if r['category'] in short_term_categories)
            short_term_successes = sum(r['successes'] for r in results_by_algo[algo] if r['category'] in short_term_categories)
            short_term_rate = short_term_successes / short_term_total * 100 if short_term_total > 0 else 0
            
            long_term_total = sum(r['cases'] for r in results_by_algo[algo] if r['category'] in long_term_categories)
            long_term_successes = sum(r['successes'] for r in results_by_algo[algo] if r['category'] in long_term_categories)
            long_term_rate = long_term_successes / long_term_total * 100 if long_term_total > 0 else 0
            
            difference = short_term_rate - long_term_rate
            
            print(f"\n📊 {algo}:")
            print(f"   Court terme (≤12h): {short_term_successes:3d}/{short_term_total:3d} ({short_term_rate:5.1f}%)")
            print(f"   Long terme (>12h):  {long_term_successes:3d}/{long_term_total:3d} ({long_term_rate:5.1f}%)")
            print(f"   Différence: {difference:+5.1f}% {'✅' if difference > 2 else '❌' if difference < -2 else '➖'}")
        
        # Recommandations
        print(f"\n💡 === RECOMMANDATIONS ===")
        
        best_short_term = None
        best_short_term_rate = 0
        best_long_term = None
        best_long_term_rate = 0
        
        for algo in algorithms_to_test:
            if algo not in results_by_algo:
                continue
                
            # Performance court terme
            short_total = sum(r['cases'] for r in results_by_algo[algo] if r['category'] in short_term_categories)
            short_successes = sum(r['successes'] for r in results_by_algo[algo] if r['category'] in short_term_categories)
            short_rate = short_successes / short_total * 100 if short_total > 0 else 0
            
            if short_rate > best_short_term_rate:
                best_short_term_rate = short_rate
                best_short_term = algo
            
            # Performance long terme
            long_total = sum(r['cases'] for r in results_by_algo[algo] if r['category'] in long_term_categories)
            long_successes = sum(r['successes'] for r in results_by_algo[algo] if r['category'] in long_term_categories)
            long_rate = long_successes / long_total * 100 if long_total > 0 else 0
            
            if long_rate > best_long_term_rate:
                best_long_term_rate = long_rate
                best_long_term = algo
        
        if best_short_term:
            print(f"🚀 Meilleur pour court terme (≤12h): {best_short_term} ({best_short_term_rate:.1f}%)")
        if best_long_term:
            print(f"⏳ Meilleur pour long terme (>12h): {best_long_term} ({best_long_term_rate:.1f}%)")
        
        if best_short_term != best_long_term:
            print(f"⚠️ Algorithmes différents recommandés selon le timing!")
            print(f"💡 Considérer un algorithme adaptatif basé sur le temps restant")
        
        # Sauvegarde des résultats
        print(f"\n💾 === SAUVEGARDE ===")
        
        # Créer DataFrame des résultats pour analyse ultérieure
        analysis_results = []
        for algo, results in results_by_algo.items():
            for result in results:
                analysis_results.append({
                    'algorithm': algo,
                    'time_category': result['category'],
                    'cases': result['cases'],
                    'successes': result['successes'],
                    'success_rate': result['success_rate'],
                    'avg_time_hours': result['avg_time_hours']
                })
        
        if analysis_results:
            results_df = pd.DataFrame(analysis_results)
            results_df.to_csv('time_correlation_analysis.csv', index=False)
            print(f"✅ Résultats sauvés: time_correlation_analysis.csv")
        
        return results_by_algo
        
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
    print("⏱️ === ANALYSE CORRÉLATION TEMPS RESTANT VS PERFORMANCE ===\n")
    result = analyze_time_correlation()
    
    if result:
        print(f"\n✅ Analyse terminée. Vérifiez time_correlation_analysis.csv pour plus de détails.")
    else:
        print(f"\n❌ Échec de l'analyse.")