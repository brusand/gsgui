#!/usr/bin/env python3
"""
Analyse spécifique des pairs avec une photo ratio ≥2.0 et une photo ratio <2.0
Détermine les facteurs décisifs dans cette zone de ratio très élevé
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_ratio_split_2():
    """Analyse les pairs avec une photo ≥2.0 et une <2.0"""
    print("🔍 === ANALYSE RATIO ≥2.0 vs <2.0 ===")
    print("🎯 Objectif: Qui gagne entre ratio très élevé vs normal?")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Chercher les pairs avec split à 2.0
    split_2_pairs = []
    
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
        
        # Vérifier si on a un split à 2.0
        split_2 = ((r1 >= 2.0 and r2 < 2.0) or (r2 >= 2.0 and r1 < 2.0))
        
        if split_2:
            winner_is_photo1 = winner_id == photo1.get('id', '')
            
            # Identifier qui a le ratio très élevé/normal
            if r1 >= 2.0:
                very_high_ratio_photo = {
                    'id': photo1.get('id', ''),
                    'ratio': r1,
                    'votes': v1,
                    'rank': rank1,
                    'is_photo1': True
                }
                normal_ratio_photo = {
                    'id': photo2.get('id', ''),
                    'ratio': r2,
                    'votes': v2,
                    'rank': rank2,
                    'is_photo1': False
                }
            else:
                very_high_ratio_photo = {
                    'id': photo2.get('id', ''),
                    'ratio': r2,
                    'votes': v2,
                    'rank': rank2,
                    'is_photo1': False
                }
                normal_ratio_photo = {
                    'id': photo1.get('id', ''),
                    'ratio': r1,
                    'votes': v1,
                    'rank': rank1,
                    'is_photo1': True
                }
            
            # Déterminer qui gagne
            very_high_ratio_wins = winner_id == very_high_ratio_photo['id']
            
            split_2_pairs.append({
                'key': key,
                'very_high_ratio_photo': very_high_ratio_photo,
                'normal_ratio_photo': normal_ratio_photo,
                'very_high_ratio_wins': very_high_ratio_wins,
                'winner_id': winner_id
            })
    
    print(f"📊 Trouvé {len(split_2_pairs)} pairs avec split ratio à 2.0")
    
    if len(split_2_pairs) < 5:
        print("❌ Pas assez de données pour une analyse significative")
        return
    
    # Statistiques principales
    very_high_ratio_victories = sum(1 for pair in split_2_pairs if pair['very_high_ratio_wins'])
    normal_ratio_victories = len(split_2_pairs) - very_high_ratio_victories
    
    print(f"\n🏆 === RÉSULTATS GLOBAUX ===")
    print(f"   Photo TRÈS HAUTE ratio (≥2.0) gagne: {very_high_ratio_victories}/{len(split_2_pairs)} ({very_high_ratio_victories/len(split_2_pairs)*100:.1f}%)")
    print(f"   Photo NORMALE ratio (<2.0) gagne: {normal_ratio_victories}/{len(split_2_pairs)} ({normal_ratio_victories/len(split_2_pairs)*100:.1f}%)")
    
    # Analyse détaillée des victoires
    print(f"\n📋 === ANALYSE DÉTAILLÉE ===")
    
    # Analyser les cas où très haute ratio gagne
    very_high_wins_cases = [pair for pair in split_2_pairs if pair['very_high_ratio_wins']]
    
    # Analyser les cas où ratio normal gagne  
    normal_wins_cases = [pair for pair in split_2_pairs if not pair['very_high_ratio_wins']]
    
    # Statistiques sur les différences
    if very_high_wins_cases:
        print(f"\n🚀 === QUAND TRÈS HAUTE RATIO GAGNE ({len(very_high_wins_cases)} cas) ===")
        
        votes_very_high_higher = 0
        votes_very_high_lower = 0  
        rank_very_high_better = 0
        rank_very_high_worse = 0
        
        vote_diffs = []
        rank_diffs = []
        ratio_diffs = []
        
        for case in very_high_wins_cases:
            very_high = case['very_high_ratio_photo'] 
            normal = case['normal_ratio_photo']
            
            # Votes
            if very_high['votes'] > normal['votes']:
                votes_very_high_higher += 1
            else:
                votes_very_high_lower += 1
            
            # Rangs (plus petit = meilleur)
            if very_high['rank'] < normal['rank']:
                rank_very_high_better += 1
            else:
                rank_very_high_worse += 1
            
            vote_diffs.append(very_high['votes'] - normal['votes'])
            rank_diffs.append(very_high['rank'] - normal['rank'])  # Positif = très haute ratio pire rang
            ratio_diffs.append(very_high['ratio'] - normal['ratio'])
        
        print(f"   Très haute ratio a PLUS de votes: {votes_very_high_higher}/{len(very_high_wins_cases)} ({votes_very_high_higher/len(very_high_wins_cases)*100:.1f}%)")
        print(f"   Très haute ratio a MEILLEUR rang: {rank_very_high_better}/{len(very_high_wins_cases)} ({rank_very_high_better/len(very_high_wins_cases)*100:.1f}%)")
        print(f"   Différence votes moyenne: {sum(vote_diffs)/len(vote_diffs):+.0f} (très haute - normale)")
        print(f"   Différence rang moyenne: {sum(rank_diffs)/len(rank_diffs):+.0f} (très haute - normale, positif = pire)")
        print(f"   Différence ratio moyenne: {sum(ratio_diffs)/len(ratio_diffs):.2f}")
    
    if normal_wins_cases:
        print(f"\n🎯 === QUAND RATIO NORMALE GAGNE ({len(normal_wins_cases)} cas) ===")
        
        votes_normal_higher = 0
        votes_normal_lower = 0
        rank_normal_better = 0  
        rank_normal_worse = 0
        
        vote_diffs = []
        rank_diffs = []
        ratio_diffs = []
        
        for case in normal_wins_cases:
            very_high = case['very_high_ratio_photo']
            normal = case['normal_ratio_photo']
            
            # Votes (du point de vue ratio normale)
            if normal['votes'] > very_high['votes']:
                votes_normal_higher += 1
            else:
                votes_normal_lower += 1
            
            # Rangs (du point de vue ratio normale)
            if normal['rank'] < very_high['rank']:
                rank_normal_better += 1
            else:
                rank_normal_worse += 1
            
            vote_diffs.append(normal['votes'] - very_high['votes'])
            rank_diffs.append(normal['rank'] - very_high['rank'])  # Positif = normale pire rang
            ratio_diffs.append(very_high['ratio'] - normal['ratio'])
        
        print(f"   Ratio normale a PLUS de votes: {votes_normal_higher}/{len(normal_wins_cases)} ({votes_normal_higher/len(normal_wins_cases)*100:.1f}%)")
        print(f"   Ratio normale a MEILLEUR rang: {rank_normal_better}/{len(normal_wins_cases)} ({rank_normal_better/len(normal_wins_cases)*100:.1f}%)")
        print(f"   Différence votes moyenne: {sum(vote_diffs)/len(vote_diffs):+.0f} (normale - très haute)")
        print(f"   Différence rang moyenne: {sum(rank_diffs)/len(rank_diffs):+.0f} (normale - très haute, positif = pire)")  
        print(f"   Différence ratio moyenne: {sum(ratio_diffs)/len(ratio_diffs):.2f}")
    
    # Exemples détaillés
    print(f"\n📋 === EXEMPLES DÉTAILLÉS ===")
    
    print(f"\n🚀 Top 5 victoires TRÈS HAUTE ratio:")
    very_high_wins_sorted = sorted(very_high_wins_cases, key=lambda x: x['very_high_ratio_photo']['ratio'], reverse=True)
    
    for i, case in enumerate(very_high_wins_sorted[:5]):
        very_high = case['very_high_ratio_photo']
        normal = case['normal_ratio_photo']
        
        print(f"   {i+1}. TRÈS HAUTE: ratio={very_high['ratio']:.2f}, votes={very_high['votes']:.0f}, rang={very_high['rank']:.0f}")
        print(f"      NORMALE: ratio={normal['ratio']:.2f}, votes={normal['votes']:.0f}, rang={normal['rank']:.0f}")
        print(f"      Écart ratio: {very_high['ratio'] - normal['ratio']:.2f}")
    
    if normal_wins_cases:
        print(f"\n🎯 Top 5 victoires RATIO NORMALE:")
        normal_wins_sorted = sorted(normal_wins_cases, key=lambda x: x['normal_ratio_photo']['votes'] - x['very_high_ratio_photo']['votes'], reverse=True)
        
        for i, case in enumerate(normal_wins_sorted[:5]):
            very_high = case['very_high_ratio_photo']
            normal = case['normal_ratio_photo']
            
            print(f"   {i+1}. NORMALE: ratio={normal['ratio']:.2f}, votes={normal['votes']:.0f}, rang={normal['rank']:.0f}")
            print(f"      TRÈS HAUTE: ratio={very_high['ratio']:.2f}, votes={very_high['votes']:.0f}, rang={very_high['rank']:.0f}")
            print(f"      Avantage votes normale: {normal['votes'] - very_high['votes']:+.0f}")
    
    # Analyse par tranches de ratios très élevés
    print(f"\n📊 === ANALYSE PAR TRANCHES TRÈS ÉLEVÉES ===")
    
    # Tranches de ratio très élevé
    extreme_high_wins = 0  # ≥3.0
    very_high_wins = 0     # 2.0-3.0
    extreme_high_total = 0
    very_high_total = 0
    
    for case in split_2_pairs:
        very_high_ratio = case['very_high_ratio_photo']['ratio']
        if very_high_ratio >= 3.0:
            extreme_high_total += 1
            if case['very_high_ratio_wins']:
                extreme_high_wins += 1
        else:  # 2.0-3.0
            very_high_total += 1
            if case['very_high_ratio_wins']:
                very_high_wins += 1
    
    if extreme_high_total > 0:
        print(f"   Ratio EXTRÊME (≥3.0): {extreme_high_wins}/{extreme_high_total} ({extreme_high_wins/extreme_high_total*100:.1f}%) gagnent")
    if very_high_total > 0:
        print(f"   Ratio TRÈS ÉLEVÉ (2.0-3.0): {very_high_wins}/{very_high_total} ({very_high_wins/very_high_total*100:.1f}%) gagnent")
    
    # Tranches de ratio normal
    low_normal_wins = 0    # <1.0
    good_normal_wins = 0   # 1.0-1.5
    high_normal_wins = 0   # 1.5-2.0
    low_normal_total = 0
    good_normal_total = 0
    high_normal_total = 0
    
    for case in split_2_pairs:
        normal_ratio = case['normal_ratio_photo']['ratio']
        if normal_ratio < 1.0:
            low_normal_total += 1
            if not case['very_high_ratio_wins']:
                low_normal_wins += 1
        elif normal_ratio < 1.5:
            good_normal_total += 1
            if not case['very_high_ratio_wins']:
                good_normal_wins += 1
        else:  # 1.5-2.0
            high_normal_total += 1
            if not case['very_high_ratio_wins']:
                high_normal_wins += 1
    
    if low_normal_total > 0:
        print(f"   Ratio FAIBLE (<1.0): {low_normal_wins}/{low_normal_total} ({low_normal_wins/low_normal_total*100:.1f}%) gagnent")
    if good_normal_total > 0:
        print(f"   Ratio BON (1.0-1.5): {good_normal_wins}/{good_normal_total} ({good_normal_wins/good_normal_total*100:.1f}%) gagnent")
    if high_normal_total > 0:
        print(f"   Ratio ÉLEVÉ (1.5-2.0): {high_normal_wins}/{high_normal_total} ({high_normal_wins/high_normal_total*100:.1f}%) gagnent")
    
    # Conclusions
    print(f"\n🎉 === CONCLUSIONS ===")
    
    very_high_ratio_win_rate = very_high_ratio_victories / len(split_2_pairs) * 100
    
    if very_high_ratio_win_rate > 65:
        print(f"✅ RATIO TRÈS ÉLEVÉ DOMINE: {very_high_ratio_win_rate:.1f}% de victoires")
        print("   → Ratio ≥2.0 = avantage majeur")
    elif very_high_ratio_win_rate < 35:
        print(f"⚠️ RATIO TRÈS ÉLEVÉ DÉSAVANTAGÉ: {100-very_high_ratio_win_rate:.1f}% de défaites")  
        print("   → Ratio ≥2.0 peut être contre-productif")
    else:
        print(f"❓ ÉQUILIBRÉ: {very_high_ratio_win_rate:.1f}% vs {100-very_high_ratio_win_rate:.1f}%")
        print("   → Autres facteurs décisifs (votes, rang)")
    
    # Analyse des facteurs compensatoires
    if normal_wins_cases:
        print(f"\n🔍 === FACTEURS COMPENSATION RATIO NORMALE ===")
        
        massive_votes_comp = 0
        massive_rank_comp = 0
        
        for case in normal_wins_cases:
            very_high = case['very_high_ratio_photo']
            normal = case['normal_ratio_photo']
            
            # Compensation massive par votes
            if normal['votes'] > very_high['votes'] * 2:
                massive_votes_comp += 1
            
            # Compensation massive par rang
            if normal['rank'] < very_high['rank'] * 0.5:
                massive_rank_comp += 1
        
        if len(normal_wins_cases) > 0:
            print(f"   Compensation massive votes (>2x): {massive_votes_comp}/{len(normal_wins_cases)} ({massive_votes_comp/len(normal_wins_cases)*100:.1f}%)")
            print(f"   Compensation massive rang (<0.5x): {massive_rank_comp}/{len(normal_wins_cases)} ({massive_rank_comp/len(normal_wins_cases)*100:.1f}%)")
    
    # Recommandations
    print(f"\n🚀 === RECOMMANDATIONS ALGORITHME ===")
    
    if very_high_ratio_win_rate > 60:
        print("💡 Face à ratio ≥2.0 vs <2.0: PRIVILÉGIER ratio très élevé")
        if very_high_wins_cases and votes_very_high_higher/len(very_high_wins_cases) > 0.6:
            print("💡 Bonus: ratio très élevé gagne souvent avec plus de votes aussi")
    elif very_high_ratio_win_rate < 40:
        print("💡 Face à ratio ≥2.0 vs <2.0: MÉFIANCE du ratio très élevé")
        print("💡 Priorité aux facteurs compensatoires (votes massifs, rang excellent)")
    else:
        print("💡 Face à ratio ≥2.0 vs <2.0: Utiliser facteurs secondaires")
        print("   → Analyser votes et rang avant de décider")
    
    # Seuils recommandés
    if normal_wins_cases and len(normal_wins_cases) > 0:
        avg_vote_compensation = sum(case['normal_ratio_photo']['votes'] - case['very_high_ratio_photo']['votes'] for case in normal_wins_cases) / len(normal_wins_cases)
        if avg_vote_compensation > 200:
            print(f"🔧 SEUIL VOTES: Si ratio normale a >{avg_vote_compensation:.0f} votes de plus, privilégier")
    
    return {
        'total_pairs': len(split_2_pairs),
        'very_high_ratio_wins': very_high_ratio_victories,
        'normal_ratio_wins': normal_ratio_victories,
        'very_high_ratio_win_rate': very_high_ratio_win_rate
    }

if __name__ == "__main__":
    analyze_ratio_split_2()