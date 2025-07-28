#!/usr/bin/env python3
"""
Analyse de la relation entre ratio et victoire
Détermine si ratio plus petit = meilleur ou l'inverse
"""

from configobj import ConfigObj
import pandas as pd

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_ratio_victory_relationship():
    """Analyse la relation entre ratio et victoire"""
    print("🔍 === ANALYSE RELATION RATIO <-> VICTOIRE ===")
    print("📋 Question: Ratio plus petit = meilleur ou l'inverse?")
    print("=" * 55)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique trouvé")
        return
    
    # Collecter les données
    comparisons = []
    
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
        
        r1 = safe_float(photo1.get('ratio', 0))
        r2 = safe_float(photo2.get('ratio', 0))
        
        # Éviter les cas avec ratios invalides
        if r1 <= 0 or r2 <= 0:
            continue
        
        photo1_wins = winner_id == photo1.get('id', '')
        
        comparisons.append({
            'ratio1': r1,
            'ratio2': r2,
            'photo1_wins': photo1_wins,
            'votes1': safe_float(photo1.get('votes', 0)),
            'votes2': safe_float(photo2.get('votes', 0)),
            'rank1': safe_float(photo1.get('rank', 999)),
            'rank2': safe_float(photo2.get('rank', 999))
        })
    
    print(f"📊 Analysing {len(comparisons)} comparaisons valides")
    
    # 1. ANALYSE DIRECTE: Qui gagne quand il y a une différence de ratio claire?
    print("\n🎯 === ANALYSE 1: DIFFÉRENCES DE RATIO CLAIRES ===")
    
    ratio_advantage_cases = []
    for comp in comparisons:
        ratio_diff = abs(comp['ratio1'] - comp['ratio2'])
        if ratio_diff > 0.1:  # Différence significative
            if comp['ratio1'] < comp['ratio2']:  # Photo1 a ratio plus petit
                ratio_advantage_cases.append({
                    'smaller_ratio_wins': comp['photo1_wins'],
                    'ratio_diff': ratio_diff,
                    'smaller_ratio': comp['ratio1'],
                    'bigger_ratio': comp['ratio2']
                })
            else:  # Photo2 a ratio plus petit
                ratio_advantage_cases.append({
                    'smaller_ratio_wins': not comp['photo1_wins'],
                    'ratio_diff': ratio_diff,
                    'smaller_ratio': comp['ratio2'],
                    'bigger_ratio': comp['ratio1']
                })
    
    if ratio_advantage_cases:
        smaller_wins = sum(1 for case in ratio_advantage_cases if case['smaller_ratio_wins'])
        total_clear = len(ratio_advantage_cases)
        smaller_win_rate = smaller_wins / total_clear * 100
        
        print(f"   Cas avec différence > 0.1: {total_clear}")
        print(f"   Ratio plus petit gagne: {smaller_wins}/{total_clear} = {smaller_win_rate:.1f}%")
        
        if smaller_win_rate > 60:
            print("   ✅ CONCLUSION: Ratio plus petit = MEILLEUR (plus de votes/vue)")
        elif smaller_win_rate < 40:
            print("   ✅ CONCLUSION: Ratio plus grand = MEILLEUR (moins de votes/vue)")
        else:
            print("   ❓ CONCLUSION: Relation pas claire")
    
    # 2. ANALYSE PAR TRANCHES DE RATIO
    print("\n📊 === ANALYSE 2: PAR TRANCHES DE RATIO ===")
    
    def get_ratio_category(ratio):
        if ratio < 0.8: return "Très faible (<0.8)"
        elif ratio < 1.0: return "Faible (0.8-1.0)"
        elif ratio < 1.2: return "Bon (1.0-1.2)"
        elif ratio < 1.4: return "Moyen (1.2-1.4)"
        elif ratio < 1.6: return "Élevé (1.4-1.6)"
        elif ratio < 2.0: return "Très élevé (1.6-2.0)"
        else: return "Extrême (>2.0)"
    
    # Statistiques par catégorie de ratio
    ratio_stats = {}
    
    for comp in comparisons:
        cat1 = get_ratio_category(comp['ratio1'])
        cat2 = get_ratio_category(comp['ratio2'])
        
        # Pour photo1
        if cat1 not in ratio_stats:
            ratio_stats[cat1] = {'wins': 0, 'total': 0}
        ratio_stats[cat1]['total'] += 1
        if comp['photo1_wins']:
            ratio_stats[cat1]['wins'] += 1
        
        # Pour photo2
        if cat2 not in ratio_stats:
            ratio_stats[cat2] = {'wins': 0, 'total': 0}
        ratio_stats[cat2]['total'] += 1
        if not comp['photo1_wins']:
            ratio_stats[cat2]['wins'] += 1
    
    print("   Taux de victoire par catégorie de ratio:")
    # Ordre logique des catégories
    category_order = {
        "Très faible (<0.8)": 1,
        "Faible (0.8-1.0)": 2, 
        "Bon (1.0-1.2)": 3,
        "Moyen (1.2-1.4)": 4,
        "Élevé (1.4-1.6)": 5,
        "Très élevé (1.6-2.0)": 6,
        "Extrême (>2.0)": 7
    }
    
    for category, stats in sorted(ratio_stats.items(), key=lambda x: category_order.get(x[0], 999)):
        if stats['total'] >= 10:  # Seulement si assez d'échantillons
            win_rate = stats['wins'] / stats['total'] * 100
            print(f"      {category:20}: {win_rate:.1f}% ({stats['wins']}/{stats['total']})")
    
    # 3. ANALYSE DES PATTERNS SPÉCIFIQUES
    print("\n🔍 === ANALYSE 3: PATTERNS SPÉCIFIQUES ===")
    
    # Pattern 1: Très faible vs Normal
    very_low_vs_normal = [comp for comp in comparisons 
                         if (comp['ratio1'] < 0.8 and 1.0 <= comp['ratio2'] <= 1.5) or 
                            (comp['ratio2'] < 0.8 and 1.0 <= comp['ratio1'] <= 1.5)]
    
    if very_low_vs_normal:
        very_low_wins = 0
        for comp in very_low_vs_normal:
            if comp['ratio1'] < 0.8 and comp['photo1_wins']:
                very_low_wins += 1
            elif comp['ratio2'] < 0.8 and not comp['photo1_wins']:
                very_low_wins += 1
        
        very_low_rate = very_low_wins / len(very_low_vs_normal) * 100
        print(f"   Ratio très faible vs normal: {very_low_rate:.1f}% ({very_low_wins}/{len(very_low_vs_normal)})")
    
    # Pattern 2: Autour de 1.0 vs Au-dessus de 1.5
    low_vs_high = [comp for comp in comparisons 
                   if (0.8 <= comp['ratio1'] <= 1.1 and comp['ratio2'] >= 1.5) or 
                      (0.8 <= comp['ratio2'] <= 1.1 and comp['ratio1'] >= 1.5)]
    
    if low_vs_high:
        low_wins = 0
        for comp in low_vs_high:
            if 0.8 <= comp['ratio1'] <= 1.1 and comp['photo1_wins']:
                low_wins += 1
            elif 0.8 <= comp['ratio2'] <= 1.1 and not comp['photo1_wins']:
                low_wins += 1
        
        low_rate = low_wins / len(low_vs_high) * 100
        print(f"   Ratio ~1.0 vs >1.5: {low_rate:.1f}% ({low_wins}/{len(low_vs_high)})")
    
    # 4. ANALYSE CORRÉLATION AVEC VOTES
    print("\n📈 === ANALYSE 4: RATIO vs VOTES ===")
    
    # Cas où un ratio plus petit a plus de votes (cohérent avec view-to-vote)
    coherent_cases = 0
    total_cases = 0
    
    for comp in comparisons:
        if comp['ratio1'] != comp['ratio2'] and comp['votes1'] != comp['votes2']:
            total_cases += 1
            
            # Cohérent si: ratio plus petit ET plus de votes
            if ((comp['ratio1'] < comp['ratio2'] and comp['votes1'] >= comp['votes2']) or 
                (comp['ratio2'] < comp['ratio1'] and comp['votes2'] >= comp['votes1'])):
                coherent_cases += 1
    
    if total_cases > 0:
        coherence_rate = coherent_cases / total_cases * 100
        print(f"   Cohérence ratio<->votes: {coherence_rate:.1f}% ({coherent_cases}/{total_cases})")
        print("   (ratio plus petit = plus de votes)")

    # 5. CONCLUSION FINALE
    print("\n🎯 === CONCLUSION FINALE ===")
    
    if ratio_advantage_cases:
        if smaller_win_rate > 55:
            print("✅ RATIO PLUS PETIT = MEILLEUR")
            print("   → Plus de votes par vue = meilleure performance")
            print("   → Logique GuruShots: view-to-vote ratio plus efficace")
        else:
            print("✅ RATIO PLUS GRAND = MEILLEUR") 
            print("   → Moins de votes par vue = plus sélectif/qualitatif")
    
    return smaller_win_rate if ratio_advantage_cases else None

if __name__ == "__main__":
    analyze_ratio_victory_relationship()