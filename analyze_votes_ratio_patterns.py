#!/usr/bin/env python3
"""
Analyse des patterns de rapport votes/ratio pour optimiser les turbos
Étudie le rapport des votes (min/max) en fonction des photos gagnantes
"""

from configobj import ConfigObj
import matplotlib.pyplot as plt
import seaborn as sns

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_votes_ratio_patterns():
    """Analyse les rapports votes et ratios pour découvrir des patterns gagnants"""
    print("🔍 === ANALYSE RAPPORTS VOTES/RATIO ===" )
    print("🎯 Objectif: Découvrir patterns votes min/max vs gagnants")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Collecter tous les cas valides
    valid_cases = []
    
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
        
        v1 = safe_float(photo1.get('votes', 0))
        v2 = safe_float(photo2.get('votes', 0))
        r1 = safe_float(photo1.get('ratio', 0))
        r2 = safe_float(photo2.get('ratio', 0))
        rank1 = safe_float(photo1.get('rank', 999))
        rank2 = safe_float(photo2.get('rank', 999))
        
        # Éviter les données invalides
        if v1 <= 0 or v2 <= 0 or r1 <= 0 or r2 <= 0:
            continue
        
        # Calculer les rapports
        votes_min = min(v1, v2)
        votes_max = max(v1, v2)
        votes_ratio = votes_min / votes_max  # Toujours entre 0 et 1
        
        ratio_min = min(r1, r2)
        ratio_max = max(r1, r2)
        ratio_rapport = ratio_min / ratio_max  # Toujours entre 0 et 1
        
        # Déterminer quel côté gagne
        winner_is_photo1 = winner_id == photo1.get('id', '')
        
        # Déterminer qui a les votes min/max
        photo1_has_votes_max = v1 >= v2
        photo1_has_ratio_max = r1 >= r2
        
        # Déterminer les caractéristiques du gagnant
        if winner_is_photo1:
            winner_has_votes_max = photo1_has_votes_max
            winner_has_ratio_max = photo1_has_ratio_max
            winner_votes = v1
            winner_ratio = r1
            winner_rank = rank1
        else:
            winner_has_votes_max = not photo1_has_votes_max
            winner_has_ratio_max = not photo1_has_ratio_max
            winner_votes = v2
            winner_ratio = r2
            winner_rank = rank2
        
        valid_cases.append({
            'votes_ratio': votes_ratio,
            'ratio_rapport': ratio_rapport,
            'votes_min': votes_min,
            'votes_max': votes_max,
            'ratio_min': ratio_min,
            'ratio_max': ratio_max,
            'winner_has_votes_max': winner_has_votes_max,
            'winner_has_ratio_max': winner_has_ratio_max,
            'winner_votes': winner_votes,
            'winner_ratio': winner_ratio,
            'winner_rank': winner_rank,
            'v1': v1, 'v2': v2, 'r1': r1, 'r2': r2,
            'rank1': rank1, 'rank2': rank2,
            'winner_is_photo1': winner_is_photo1
        })
    
    print(f"📊 Analysé {len(valid_cases)} cas valides")
    
    if len(valid_cases) < 10:
        print("❌ Pas assez de données pour une analyse significative")
        return
    
    # =================== ANALYSE 1: RAPPORTS VOTES ===================
    print(f"\n📊 === ANALYSE RAPPORTS VOTES (min/max) ===")
    
    # Créer des tranches de rapport votes
    votes_tranches = {
        'Très déséquilibré (0.0-0.2)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Déséquilibré (0.2-0.4)': {'cases': [], 'max_wins': 0, 'min_wins': 0}, 
        'Modéré (0.4-0.6)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Équilibré (0.6-0.8)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Très équilibré (0.8-1.0)': {'cases': [], 'max_wins': 0, 'min_wins': 0}
    }
    
    def get_votes_tranche(ratio):
        if ratio < 0.2:
            return 'Très déséquilibré (0.0-0.2)'
        elif ratio < 0.4:
            return 'Déséquilibré (0.2-0.4)'
        elif ratio < 0.6:
            return 'Modéré (0.4-0.6)'
        elif ratio < 0.8:
            return 'Équilibré (0.6-0.8)'
        else:
            return 'Très équilibré (0.8-1.0)'
    
    # Classer les cas
    for case in valid_cases:
        tranche = get_votes_tranche(case['votes_ratio'])
        votes_tranches[tranche]['cases'].append(case)
        
        if case['winner_has_votes_max']:
            votes_tranches[tranche]['max_wins'] += 1
        else:
            votes_tranches[tranche]['min_wins'] += 1
    
    # Afficher les résultats
    print("   Qui gagne par tranche de rapport votes:")
    for tranche, data in votes_tranches.items():
        total = len(data['cases'])
        if total >= 3:  # Seulement si assez d'échantillons
            max_rate = data['max_wins'] / total * 100
            min_rate = data['min_wins'] / total * 100
            print(f"      {tranche:25}: MAX {max_rate:.1f}% ({data['max_wins']}/{total}) vs MIN {min_rate:.1f}% ({data['min_wins']}/{total})")
    
    # =================== ANALYSE 2: RAPPORTS RATIO ===================
    print(f"\n📊 === ANALYSE RAPPORTS RATIO (min/max) ===")
    
    # Créer des tranches de rapport ratio
    ratio_tranches = {
        'Très déséquilibré (0.0-0.3)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Déséquilibré (0.3-0.5)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Modéré (0.5-0.7)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Équilibré (0.7-0.9)': {'cases': [], 'max_wins': 0, 'min_wins': 0},
        'Très équilibré (0.9-1.0)': {'cases': [], 'max_wins': 0, 'min_wins': 0}
    }
    
    def get_ratio_tranche(ratio):
        if ratio < 0.3:
            return 'Très déséquilibré (0.0-0.3)'
        elif ratio < 0.5:
            return 'Déséquilibré (0.3-0.5)'
        elif ratio < 0.7:
            return 'Modéré (0.5-0.7)'
        elif ratio < 0.9:
            return 'Équilibré (0.7-0.9)'
        else:
            return 'Très équilibré (0.9-1.0)'
    
    # Classer les cas
    for case in valid_cases:
        tranche = get_ratio_tranche(case['ratio_rapport'])
        ratio_tranches[tranche]['cases'].append(case)
        
        if case['winner_has_ratio_max']:
            ratio_tranches[tranche]['max_wins'] += 1
        else:
            ratio_tranches[tranche]['min_wins'] += 1
    
    # Afficher les résultats
    print("   Qui gagne par tranche de rapport ratio:")
    for tranche, data in ratio_tranches.items():
        total = len(data['cases'])
        if total >= 3:  # Seulement si assez d'échantillons
            max_rate = data['max_wins'] / total * 100
            min_rate = data['min_wins'] / total * 100
            print(f"      {tranche:25}: MAX {max_rate:.1f}% ({data['max_wins']}/{total}) vs MIN {min_rate:.1f}% ({data['min_wins']}/{total})")
    
    # =================== ANALYSE 3: PATTERNS CROISÉS ===================
    print(f"\n🔍 === ANALYSE PATTERNS CROISÉS ===")
    
    # Chercher des patterns intéressants
    patterns = {
        'max_votes_max_ratio': 0,  # Gagnant a les deux max
        'max_votes_min_ratio': 0,  # Gagnant a max votes mais min ratio
        'min_votes_max_ratio': 0,  # Gagnant a min votes mais max ratio
        'min_votes_min_ratio': 0   # Gagnant a les deux min
    }
    
    for case in valid_cases:
        if case['winner_has_votes_max'] and case['winner_has_ratio_max']:
            patterns['max_votes_max_ratio'] += 1
        elif case['winner_has_votes_max'] and not case['winner_has_ratio_max']:
            patterns['max_votes_min_ratio'] += 1
        elif not case['winner_has_votes_max'] and case['winner_has_ratio_max']:
            patterns['min_votes_max_ratio'] += 1
        else:
            patterns['min_votes_min_ratio'] += 1
    
    total = len(valid_cases)
    print("   Patterns de victoire:")
    print(f"      MAX votes + MAX ratio: {patterns['max_votes_max_ratio']:3d} ({patterns['max_votes_max_ratio']/total*100:.1f}%) - Double domination")
    print(f"      MAX votes + MIN ratio: {patterns['max_votes_min_ratio']:3d} ({patterns['max_votes_min_ratio']/total*100:.1f}%) - Votes compensent ratio")
    print(f"      MIN votes + MAX ratio: {patterns['min_votes_max_ratio']:3d} ({patterns['min_votes_max_ratio']/total*100:.1f}%) - Ratio compense votes") 
    print(f"      MIN votes + MIN ratio: {patterns['min_votes_min_ratio']:3d} ({patterns['min_votes_min_ratio']/total*100:.1f}%) - Double faiblesse gagne")
    
    # =================== ANALYSE 4: SEUILS CRITIQUES ===================
    print(f"\n⚡ === SEUILS CRITIQUES DÉCOUVERTS ===")
    
    # Analyser les seuils où les patterns changent
    votes_ratios_sorted = sorted([case['votes_ratio'] for case in valid_cases])
    ratio_ratios_sorted = sorted([case['ratio_rapport'] for case in valid_cases])
    
    # Identifier les seuils où les victoires de MAX dépassent 70%
    high_success_votes_cases = [case for case in valid_cases if case['winner_has_votes_max']]
    high_success_ratio_cases = [case for case in valid_cases if case['winner_has_ratio_max']]
    
    print("   Seuils de domination (>70% de succès):")
    
    # Seuils votes
    votes_thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    for threshold in votes_thresholds:
        below_threshold = [case for case in valid_cases if case['votes_ratio'] < threshold]
        if len(below_threshold) >= 5:
            max_wins = sum(1 for case in below_threshold if case['winner_has_votes_max'])
            success_rate = max_wins / len(below_threshold) * 100
            if success_rate >= 70:
                print(f"      📈 Rapport votes < {threshold:.1f}: MAX gagne {success_rate:.1f}% ({max_wins}/{len(below_threshold)})")
    
    # Seuils ratio
    ratio_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    for threshold in ratio_thresholds:
        below_threshold = [case for case in valid_cases if case['ratio_rapport'] < threshold]
        if len(below_threshold) >= 5:
            max_wins = sum(1 for case in below_threshold if case['winner_has_ratio_max'])
            success_rate = max_wins / len(below_threshold) * 100
            if success_rate >= 70:
                print(f"      📈 Rapport ratio < {threshold:.1f}: MAX gagne {success_rate:.1f}% ({max_wins}/{len(below_threshold)})")
    
    # =================== ANALYSE 5: EXEMPLES DÉTAILLÉS ===================
    print(f"\n📋 === EXEMPLES DÉTAILLÉS ===")
    
    # Trier par rapport votes pour montrer les extrêmes
    extreme_votes_cases = sorted(valid_cases, key=lambda x: x['votes_ratio'])
    
    print("\n   🔥 TOP 10 cas VOTES très déséquilibrés (rapport le plus faible):")
    for i, case in enumerate(extreme_votes_cases[:10]):
        winner_profile = "MAX votes" if case['winner_has_votes_max'] else "MIN votes"
        ratio_profile = "MAX ratio" if case['winner_has_ratio_max'] else "MIN ratio"
        
        print(f"      {i+1}. Rapport votes: {case['votes_ratio']:.3f} ({case['votes_min']:.0f}/{case['votes_max']:.0f}) - Gagnant: {winner_profile} + {ratio_profile}")
        print(f"         Votes: {case['v1']:.0f} vs {case['v2']:.0f} | Ratios: {case['r1']:.3f} vs {case['r2']:.3f}")
    
    # Trier par rapport ratio pour montrer les extrêmes
    extreme_ratio_cases = sorted(valid_cases, key=lambda x: x['ratio_rapport'])
    
    print("\n   🎯 TOP 10 cas RATIO très déséquilibrés (rapport le plus faible):")
    for i, case in enumerate(extreme_ratio_cases[:10]):
        winner_profile = "MAX votes" if case['winner_has_votes_max'] else "MIN votes"
        ratio_profile = "MAX ratio" if case['winner_has_ratio_max'] else "MIN ratio"
        
        print(f"      {i+1}. Rapport ratio: {case['ratio_rapport']:.3f} ({case['ratio_min']:.3f}/{case['ratio_max']:.3f}) - Gagnant: {winner_profile} + {ratio_profile}")
        print(f"         Votes: {case['v1']:.0f} vs {case['v2']:.0f} | Ratios: {case['r1']:.3f} vs {case['r2']:.3f}")
    
    # =================== CONCLUSIONS ===================
    print(f"\n🎉 === CONCLUSIONS & RECOMMANDATIONS ===")
    
    # Identifier le pattern dominant
    dominant_pattern = max(patterns.items(), key=lambda x: x[1])
    print(f"   🏆 PATTERN DOMINANT: {dominant_pattern[0]} ({dominant_pattern[1]}/{total} = {dominant_pattern[1]/total*100:.1f}%)")
    
    # Identifier les meilleures stratégies par tranche
    print("\n   🎯 STRATÉGIES RECOMMANDÉES:")
    
    # Recommandations basées sur les rapports
    for tranche, data in votes_tranches.items():
        total_tranche = len(data['cases'])
        if total_tranche >= 5:
            if data['max_wins'] / total_tranche > 0.65:
                print(f"      📈 {tranche}: PRIVILÉGIER MAX votes ({data['max_wins']}/{total_tranche} = {data['max_wins']/total_tranche*100:.1f}%)")
            elif data['min_wins'] / total_tranche > 0.65:
                print(f"      📉 {tranche}: PRIVILÉGIER MIN votes ({data['min_wins']}/{total_tranche} = {data['min_wins']/total_tranche*100:.1f}%)")
    
    # Seuils critiques pour l'algorithme
    print(f"\n   🔧 SEUILS POUR ALGORITHME:")
    print(f"      💡 Si rapport votes < 0.3: Forte probabilité MAX votes gagne")
    print(f"      💡 Si rapport ratio < 0.5: Forte probabilité MAX ratio gagne")
    print(f"      💡 Pattern croisé le plus fréquent: {dominant_pattern[0]}")
    
    return {
        'total_cases': len(valid_cases),
        'patterns': patterns,
        'votes_tranches': votes_tranches,
        'ratio_tranches': ratio_tranches
    }

if __name__ == "__main__":
    analyze_votes_ratio_patterns()