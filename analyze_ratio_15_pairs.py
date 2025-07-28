#!/usr/bin/env python3
"""
Analyse spécifique des pairs avec ratio 1.5 dans l'historique turbo
Détermine les facteurs décisifs quand les deux photos ont un ratio similaire à 1.5
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_ratio_15_pairs():
    """Analyse les pairs avec ratio ~1.5"""
    print("🔍 === ANALYSE PAIRS RATIO ~1.5 ===")
    print("🎯 Objectif: Identifier les facteurs décisifs quand ratio ≈ 1.5")
    print("=" * 55)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Chercher les pairs avec ratio ~1.5 (tolérance ±0.1)
    ratio_15_pairs = []
    
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
        
        # Vérifier si les deux ratios sont proches de 1.5 (±0.1)
        ratio_15_threshold = 0.1
        both_near_15 = (abs(r1 - 1.5) <= ratio_15_threshold and 
                       abs(r2 - 1.5) <= ratio_15_threshold)
        
        # Ou l'un des deux exactement à 1.5
        one_exactly_15 = (abs(r1 - 1.5) < 0.05 or abs(r2 - 1.5) < 0.05)
        
        if both_near_15 or one_exactly_15:
            winner_is_photo1 = winner_id == photo1.get('id', '')
            
            ratio_15_pairs.append({
                'key': key,
                'photo1': {
                    'id': photo1.get('id', ''),
                    'ratio': r1,
                    'votes': v1,
                    'rank': rank1
                },
                'photo2': {
                    'id': photo2.get('id', ''),
                    'ratio': r2,
                    'votes': v2,
                    'rank': rank2
                },
                'winner_is_photo1': winner_is_photo1,
                'winner_id': winner_id
            })
    
    print(f"📊 Trouvé {len(ratio_15_pairs)} pairs avec ratio proche de 1.5")
    
    if len(ratio_15_pairs) < 5:
        print("❌ Pas assez de données pour une analyse significative")
        return
    
    # Analyser les tendances
    print(f"\n📋 === ANALYSE DÉTAILLÉE ===")
    
    # Statistiques sur les votes
    votes_winner_higher = 0
    votes_winner_lower = 0
    votes_similar = 0
    
    # Statistiques sur les rangs
    rank_winner_better = 0  # Rang plus petit = meilleur
    rank_winner_worse = 0   # Rang plus grand = pire
    rank_similar = 0
    
    # Statistiques sur les ratios
    ratio_winner_higher = 0
    ratio_winner_lower = 0  
    ratio_similar = 0
    
    detailed_cases = []
    
    for pair in ratio_15_pairs:
        p1 = pair['photo1']
        p2 = pair['photo2']
        winner_is_p1 = pair['winner_is_photo1']
        
        # Identifier le gagnant et le perdant
        if winner_is_p1:
            winner = p1
            loser = p2
        else:
            winner = p2
            loser = p1
        
        # Analyser les votes
        votes_diff = abs(winner['votes'] - loser['votes'])
        if votes_diff < 50:  # Seuil de similarité
            votes_similar += 1
            votes_status = "similaires"
        elif winner['votes'] > loser['votes']:
            votes_winner_higher += 1
            votes_status = "gagnant plus"
        else:
            votes_winner_lower += 1
            votes_status = "gagnant moins"
        
        # Analyser les rangs (plus petit = meilleur)
        rank_diff = abs(winner['rank'] - loser['rank'])
        if rank_diff < 100:  # Seuil de similarité
            rank_similar += 1
            rank_status = "similaires"
        elif winner['rank'] < loser['rank']:  # Gagnant a meilleur rang
            rank_winner_better += 1
            rank_status = "gagnant meilleur"
        else:
            rank_winner_worse += 1
            rank_status = "gagnant pire"
        
        # Analyser les ratios
        ratio_diff = abs(winner['ratio'] - loser['ratio'])
        if ratio_diff < 0.05:
            ratio_similar += 1
            ratio_status = "similaires"
        elif winner['ratio'] > loser['ratio']:
            ratio_winner_higher += 1
            ratio_status = "gagnant plus élevé"
        else:
            ratio_winner_lower += 1
            ratio_status = "gagnant plus faible"
        
        detailed_cases.append({
            'winner': winner,
            'loser': loser,
            'votes_status': votes_status,
            'rank_status': rank_status,
            'ratio_status': ratio_status,
            'votes_diff': votes_diff,
            'rank_diff': rank_diff,
            'ratio_diff': ratio_diff
        })
    
    total = len(ratio_15_pairs)
    
    # Afficher les résultats
    print(f"\n🗳️ === ANALYSE VOTES ===")
    print(f"   Gagnant a PLUS de votes: {votes_winner_higher}/{total} ({votes_winner_higher/total*100:.1f}%)")
    print(f"   Gagnant a MOINS de votes: {votes_winner_lower}/{total} ({votes_winner_lower/total*100:.1f}%)")
    print(f"   Votes similaires: {votes_similar}/{total} ({votes_similar/total*100:.1f}%)")
    
    print(f"\n🏆 === ANALYSE RANGS ===")
    print(f"   Gagnant a MEILLEUR rang: {rank_winner_better}/{total} ({rank_winner_better/total*100:.1f}%)")
    print(f"   Gagnant a PIRE rang: {rank_winner_worse}/{total} ({rank_winner_worse/total*100:.1f}%)")
    print(f"   Rangs similaires: {rank_similar}/{total} ({rank_similar/total*100:.1f}%)")
    
    print(f"\n📊 === ANALYSE RATIOS ===")
    print(f"   Gagnant a ratio PLUS ÉLEVÉ: {ratio_winner_higher}/{total} ({ratio_winner_higher/total*100:.1f}%)")
    print(f"   Gagnant a ratio PLUS FAIBLE: {ratio_winner_lower}/{total} ({ratio_winner_lower/total*100:.1f}%)")
    print(f"   Ratios similaires: {ratio_similar}/{total} ({ratio_similar/total*100:.1f}%)")
    
    # Identifier le facteur le plus décisif
    print(f"\n🎯 === FACTEURS DÉCISIFS ===")
    
    factors = [
        ("Votes supérieurs", votes_winner_higher, votes_winner_higher/total*100),
        ("Meilleur rang", rank_winner_better, rank_winner_better/total*100),
        ("Ratio plus élevé", ratio_winner_higher, ratio_winner_higher/total*100)
    ]
    
    factors.sort(key=lambda x: x[2], reverse=True)
    
    for i, (factor, count, percentage) in enumerate(factors):
        if i == 0:
            print(f"   🥇 FACTEUR #1: {factor} - {percentage:.1f}% ({count}/{total})")
        elif i == 1:
            print(f"   🥈 FACTEUR #2: {factor} - {percentage:.1f}% ({count}/{total})")
        else:
            print(f"   🥉 FACTEUR #3: {factor} - {percentage:.1f}% ({count}/{total})")
    
    # Exemples détaillés
    print(f"\n📋 === EXEMPLES DÉTAILLÉS (Top 10) ===")
    
    # Trier par différence de votes pour montrer les cas intéressants
    detailed_cases.sort(key=lambda x: x['votes_diff'], reverse=True)
    
    for i, case in enumerate(detailed_cases[:10]):
        winner = case['winner']
        loser = case['loser']
        
        print(f"\n   {i+1}. Gagnant: ratio={winner['ratio']:.2f}, votes={winner['votes']:.0f}, rang={winner['rank']:.0f}")
        print(f"      Perdant: ratio={loser['ratio']:.2f}, votes={loser['votes']:.0f}, rang={loser['rank']:.0f}")
        print(f"      Votes: {case['votes_status']} (diff: {case['votes_diff']:.0f})")
        print(f"      Rang: {case['rank_status']} (diff: {case['rank_diff']:.0f})")
        print(f"      Ratio: {case['ratio_status']} (diff: {case['ratio_diff']:.3f})")
    
    # Conclusions
    print(f"\n🎉 === CONCLUSIONS ===")
    
    if votes_winner_higher > total * 0.6:
        print("✅ VOTES: Facteur dominant - Plus de votes = victoire probable")
    elif votes_winner_lower > total * 0.6:
        print("⚠️ VOTES: Contre-intuitif - Moins de votes = victoire probable")
    else:
        print("❓ VOTES: Facteur non décisif")
    
    if rank_winner_better > total * 0.6:
        print("✅ RANG: Facteur dominant - Meilleur rang = victoire probable")
    elif rank_winner_worse > total * 0.6:
        print("⚠️ RANG: Contre-intuitif - Pire rang = victoire probable")
    else:
        print("❓ RANG: Facteur non décisif")
    
    if ratio_winner_higher > total * 0.6:
        print("✅ RATIO: Facteur dominant - Ratio plus élevé = victoire probable")
    elif ratio_winner_lower > total * 0.6:
        print("⚠️ RATIO: Contre-intuitif - Ratio plus faible = victoire probable")
    else:
        print("❓ RATIO: Facteur non décisif")
    
    # Recommandation algorithme
    print(f"\n🚀 === RECOMMANDATION ALGORITHME ===")
    
    main_factor = factors[0]
    if main_factor[2] > 60:
        if "Votes supérieurs" in main_factor[0]:
            print("💡 Quand ratio ~1.5: Privilégier la photo avec PLUS de votes")
        elif "Meilleur rang" in main_factor[0]:
            print("💡 Quand ratio ~1.5: Privilégier la photo avec MEILLEUR rang")
        elif "Ratio plus élevé" in main_factor[0]:
            print("💡 Quand ratio ~1.5: Privilégier la photo avec ratio PLUS ÉLEVÉ")
    else:
        print("💡 Quand ratio ~1.5: Aucun facteur dominant clair, utiliser logique hybride")
    
    return {
        'total_pairs': total,
        'votes_higher': votes_winner_higher,
        'rank_better': rank_winner_better,
        'ratio_higher': ratio_winner_higher,
        'main_factor': main_factor[0]
    }

if __name__ == "__main__":
    analyze_ratio_15_pairs()