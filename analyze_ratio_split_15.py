#!/usr/bin/env python3
"""
Analyse spécifique des pairs avec une photo ratio ≥1.5 et une photo ratio <1.5
Détermine qui gagne entre haute ratio vs basse ratio
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_ratio_split_15():
    """Analyse les pairs avec une photo ≥1.5 et une <1.5"""
    print("🔍 === ANALYSE RATIO ≥1.5 vs <1.5 ===")
    print("🎯 Objectif: Qui gagne entre haute ratio vs basse ratio?")
    print("=" * 55)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Chercher les pairs avec split à 1.5
    split_pairs = []
    
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
        v1 = safe_float(photo1.get('votes', 0))
        v2 = safe_float(photo2.get('votes', 0))
        rank1 = safe_float(photo1.get('rank', 999))
        rank2 = safe_float(photo2.get('rank', 999))
        
        # Éviter les ratios invalides
        if r1 <= 0 or r2 <= 0:
            continue
        
        # Vérifier si on a un split à 1.5
        split_15 = ((r1 >= 1.5 and r2 < 1.5) or (r2 >= 1.5 and r1 < 1.5))
        
        if split_15:
            winner_is_photo1 = winner_id == photo1.get('id', '')
            
            # Identifier qui a le ratio élevé/faible
            if r1 >= 1.5:
                high_ratio_photo = {
                    'id': photo1.get('id', ''),
                    'ratio': r1,
                    'votes': v1,
                    'rank': rank1,
                    'is_photo1': True
                }
                low_ratio_photo = {
                    'id': photo2.get('id', ''),
                    'ratio': r2,
                    'votes': v2,
                    'rank': rank2,
                    'is_photo1': False
                }
            else:
                high_ratio_photo = {
                    'id': photo2.get('id', ''),
                    'ratio': r2,
                    'votes': v2,
                    'rank': rank2,
                    'is_photo1': False
                }
                low_ratio_photo = {
                    'id': photo1.get('id', ''),
                    'ratio': r1,
                    'votes': v1,
                    'rank': rank1,
                    'is_photo1': True
                }
            
            # Déterminer qui gagne
            high_ratio_wins = winner_id == high_ratio_photo['id']
            
            split_pairs.append({
                'key': key,
                'high_ratio_photo': high_ratio_photo,
                'low_ratio_photo': low_ratio_photo,
                'high_ratio_wins': high_ratio_wins,
                'winner_id': winner_id
            })
    
    print(f"📊 Trouvé {len(split_pairs)} pairs avec split ratio à 1.5")
    
    if len(split_pairs) < 10:
        print("❌ Pas assez de données pour une analyse significative")
        return
    
    # Statistiques principales
    high_ratio_victories = sum(1 for pair in split_pairs if pair['high_ratio_wins'])
    low_ratio_victories = len(split_pairs) - high_ratio_victories
    
    print(f"\n🏆 === RÉSULTATS GLOBAUX ===")
    print(f"   Photo HAUTE ratio (≥1.5) gagne: {high_ratio_victories}/{len(split_pairs)} ({high_ratio_victories/len(split_pairs)*100:.1f}%)")
    print(f"   Photo BASSE ratio (<1.5) gagne: {low_ratio_victories}/{len(split_pairs)} ({low_ratio_victories/len(split_pairs)*100:.1f}%)")
    
    # Analyse détaillée des victoires
    print(f"\n📋 === ANALYSE DÉTAILLÉE ===")
    
    # Analyser les cas où haute ratio gagne
    high_wins_cases = [pair for pair in split_pairs if pair['high_ratio_wins']]
    
    # Analyser les cas où basse ratio gagne  
    low_wins_cases = [pair for pair in split_pairs if not pair['high_ratio_wins']]
    
    # Statistiques sur les différences
    if high_wins_cases:
        print(f"\n🔥 === QUAND HAUTE RATIO GAGNE ({len(high_wins_cases)} cas) ===")
        
        votes_high_higher = 0
        votes_high_lower = 0  
        rank_high_better = 0
        rank_high_worse = 0
        
        vote_diffs = []
        rank_diffs = []
        ratio_diffs = []
        
        for case in high_wins_cases:
            high = case['high_ratio_photo'] 
            low = case['low_ratio_photo']
            
            # Votes
            if high['votes'] > low['votes']:
                votes_high_higher += 1
            else:
                votes_high_lower += 1
            
            # Rangs (plus petit = meilleur)
            if high['rank'] < low['rank']:
                rank_high_better += 1
            else:
                rank_high_worse += 1
            
            vote_diffs.append(high['votes'] - low['votes'])
            rank_diffs.append(high['rank'] - low['rank'])  # Positif = haute ratio pire rang
            ratio_diffs.append(high['ratio'] - low['ratio'])
        
        print(f"   Haute ratio a PLUS de votes: {votes_high_higher}/{len(high_wins_cases)} ({votes_high_higher/len(high_wins_cases)*100:.1f}%)")
        print(f"   Haute ratio a MEILLEUR rang: {rank_high_better}/{len(high_wins_cases)} ({rank_high_better/len(high_wins_cases)*100:.1f}%)")
        print(f"   Différence votes moyenne: {sum(vote_diffs)/len(vote_diffs):+.0f} (haute - basse)")
        print(f"   Différence rang moyenne: {sum(rank_diffs)/len(rank_diffs):+.0f} (haute - basse, positif = pire)")
        print(f"   Différence ratio moyenne: {sum(ratio_diffs)/len(ratio_diffs):.2f}")
    
    if low_wins_cases:
        print(f"\n❄️ === QUAND BASSE RATIO GAGNE ({len(low_wins_cases)} cas) ===")
        
        votes_low_higher = 0
        votes_low_lower = 0
        rank_low_better = 0  
        rank_low_worse = 0
        
        vote_diffs = []
        rank_diffs = []
        ratio_diffs = []
        
        for case in low_wins_cases:
            high = case['high_ratio_photo']
            low = case['low_ratio_photo']
            
            # Votes (du point de vue basse ratio)
            if low['votes'] > high['votes']:
                votes_low_higher += 1
            else:
                votes_low_lower += 1
            
            # Rangs (du point de vue basse ratio)
            if low['rank'] < high['rank']:
                rank_low_better += 1
            else:
                rank_low_worse += 1
            
            vote_diffs.append(low['votes'] - high['votes'])
            rank_diffs.append(low['rank'] - high['rank'])  # Positif = basse ratio pire rang
            ratio_diffs.append(high['ratio'] - low['ratio'])
        
        print(f"   Basse ratio a PLUS de votes: {votes_low_higher}/{len(low_wins_cases)} ({votes_low_higher/len(low_wins_cases)*100:.1f}%)")
        print(f"   Basse ratio a MEILLEUR rang: {rank_low_better}/{len(low_wins_cases)} ({rank_low_better/len(low_wins_cases)*100:.1f}%)")
        print(f"   Différence votes moyenne: {sum(vote_diffs)/len(vote_diffs):+.0f} (basse - haute)")
        print(f"   Différence rang moyenne: {sum(rank_diffs)/len(rank_diffs):+.0f} (basse - haute, positif = pire)")  
        print(f"   Différence ratio moyenne: {sum(ratio_diffs)/len(ratio_diffs):.2f}")
    
    # Exemples détaillés
    print(f"\n📋 === EXEMPLES DÉTAILLÉS ===")
    
    print(f"\n🔥 Top 5 victoires HAUTE ratio:")
    high_wins_sorted = sorted(high_wins_cases, key=lambda x: x['high_ratio_photo']['ratio'] - x['low_ratio_photo']['ratio'], reverse=True)
    
    for i, case in enumerate(high_wins_sorted[:5]):
        high = case['high_ratio_photo']
        low = case['low_ratio_photo']
        
        print(f"   {i+1}. HAUTE: ratio={high['ratio']:.2f}, votes={high['votes']:.0f}, rang={high['rank']:.0f}")
        print(f"      BASSE: ratio={low['ratio']:.2f}, votes={low['votes']:.0f}, rang={low['rank']:.0f}")
        print(f"      Écart ratio: {high['ratio'] - low['ratio']:.2f}")
    
    print(f"\n❄️ Top 5 victoires BASSE ratio:")
    low_wins_sorted = sorted(low_wins_cases, key=lambda x: x['low_ratio_photo']['votes'] - x['high_ratio_photo']['votes'], reverse=True)
    
    for i, case in enumerate(low_wins_sorted[:5]):
        high = case['high_ratio_photo']
        low = case['low_ratio_photo']
        
        print(f"   {i+1}. BASSE: ratio={low['ratio']:.2f}, votes={low['votes']:.0f}, rang={low['rank']:.0f}")
        print(f"      HAUTE: ratio={high['ratio']:.2f}, votes={high['votes']:.0f}, rang={high['rank']:.0f}")
        print(f"      Avantage votes basse: {low['votes'] - high['votes']:+.0f}")
    
    # Analyse par tranches de ratios
    print(f"\n📊 === ANALYSE PAR TRANCHES ===")
    
    # Tranches de ratio élevé
    very_high_wins = 0  # ≥2.0
    high_wins = 0       # 1.5-2.0
    very_high_total = 0
    high_total = 0
    
    for case in split_pairs:
        high_ratio = case['high_ratio_photo']['ratio']
        if high_ratio >= 2.0:
            very_high_total += 1
            if case['high_ratio_wins']:
                very_high_wins += 1
        else:  # 1.5-2.0
            high_total += 1
            if case['high_ratio_wins']:
                high_wins += 1
    
    if very_high_total > 0:
        print(f"   Ratio TRÈS ÉLEVÉ (≥2.0): {very_high_wins}/{very_high_total} ({very_high_wins/very_high_total*100:.1f}%) gagnent")
    if high_total > 0:
        print(f"   Ratio ÉLEVÉ (1.5-2.0): {high_wins}/{high_total} ({high_wins/high_total*100:.1f}%) gagnent")
    
    # Tranches de ratio faible
    very_low_wins = 0   # <1.0
    medium_wins = 0     # 1.0-1.5
    very_low_total = 0
    medium_total = 0
    
    for case in split_pairs:
        low_ratio = case['low_ratio_photo']['ratio']
        if low_ratio < 1.0:
            very_low_total += 1
            if not case['high_ratio_wins']:
                very_low_wins += 1
        else:  # 1.0-1.5
            medium_total += 1
            if not case['high_ratio_wins']:
                medium_wins += 1
    
    if very_low_total > 0:
        print(f"   Ratio TRÈS FAIBLE (<1.0): {very_low_wins}/{very_low_total} ({very_low_wins/very_low_total*100:.1f}%) gagnent")
    if medium_total > 0:
        print(f"   Ratio MOYEN (1.0-1.5): {medium_wins}/{medium_total} ({medium_wins/medium_total*100:.1f}%) gagnent")
    
    # Conclusions
    print(f"\n🎉 === CONCLUSIONS ===")
    
    high_ratio_win_rate = high_ratio_victories / len(split_pairs) * 100
    
    if high_ratio_win_rate > 60:
        print(f"✅ RATIO ÉLEVÉ DOMINE: {high_ratio_win_rate:.1f}% de victoires")
        print("   → Confirme: ratio plus grand = meilleur")
    elif high_ratio_win_rate < 40:
        print(f"✅ RATIO FAIBLE DOMINE: {100-high_ratio_win_rate:.1f}% de victoires")  
        print("   → Contredit: ratio plus petit = meilleur")
    else:
        print(f"❓ ÉQUILIBRÉ: {high_ratio_win_rate:.1f}% vs {100-high_ratio_win_rate:.1f}%")
        print("   → Autres facteurs décisifs (votes, rang)")
    
    # Recommandations
    print(f"\n🚀 === RECOMMANDATIONS ALGORITHME ===")
    
    if high_ratio_win_rate > 55:
        print("💡 Face à ratio ≥1.5 vs <1.5: PRIVILÉGIER ratio plus élevé")
        if high_wins_cases and votes_high_higher/len(high_wins_cases) > 0.6:
            print("💡 Bonus: haute ratio gagne souvent avec plus de votes aussi")
    elif high_ratio_win_rate < 45:
        print("💡 Face à ratio ≥1.5 vs <1.5: PRIVILÉGIER ratio plus faible")
        if low_wins_cases and votes_low_higher/len(low_wins_cases) > 0.6:
            print("💡 Bonus: basse ratio gagne souvent avec plus de votes")
    else:
        print("💡 Face à ratio ≥1.5 vs <1.5: Utiliser facteurs secondaires")
        print("   → Priorité aux votes, puis rang")
    
    return {
        'total_pairs': len(split_pairs),
        'high_ratio_wins': high_ratio_victories,
        'low_ratio_wins': low_ratio_victories,
        'high_ratio_win_rate': high_ratio_win_rate
    }

if __name__ == "__main__":
    analyze_ratio_split_15()