#!/usr/bin/env python3
"""
Analyse spécifique des pairs où les DEUX ratios sont < 1.0
Détermine les facteurs décisifs dans cette zone critique
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def analyze_both_ratios_under_1():
    """Analyse les pairs avec les deux ratios < 1.0"""
    print("🔍 === ANALYSE DEUX RATIOS < 1.0 ===")
    print("🎯 Objectif: Facteurs décisifs quand les deux ratios sont < 1.0")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Chercher les pairs avec les deux ratios < 1.0
    under_1_pairs = []
    
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
        
        # Vérifier si les deux ratios sont < 1.0
        if r1 < 1.0 and r2 < 1.0 and r1 > 0 and r2 > 0:  # Éviter les ratios invalides
            winner_is_photo1 = winner_id == photo1.get('id', '')
            
            under_1_pairs.append({
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
    
    print(f"📊 Trouvé {len(under_1_pairs)} pairs avec les deux ratios < 1.0")
    
    if len(under_1_pairs) < 5:
        print("❌ Pas assez de données pour une analyse significative")
        return
    
    # Analyser les tendances
    print(f"\n📋 === ANALYSE DÉTAILLÉE ===")
    
    # Statistiques sur les ratios (qui a le ratio le plus proche de 1.0)
    higher_ratio_wins = 0  # Ratio plus proche de 1.0 gagne
    lower_ratio_wins = 0   # Ratio plus éloigné de 1.0 gagne
    ratio_similar = 0      # Ratios très similaires
    
    # Statistiques sur les votes
    votes_winner_higher = 0
    votes_winner_lower = 0
    votes_similar = 0
    
    # Statistiques sur les rangs
    rank_winner_better = 0  # Rang plus petit = meilleur
    rank_winner_worse = 0   # Rang plus grand = pire
    rank_similar = 0
    
    detailed_cases = []
    
    for pair in under_1_pairs:
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
        
        # Analyser les ratios (plus proche de 1.0 = meilleur dans cette zone)
        ratio_diff = abs(winner['ratio'] - loser['ratio'])
        if ratio_diff < 0.05:  # Très similaires
            ratio_similar += 1
            ratio_status = "similaires"
        elif winner['ratio'] > loser['ratio']:  # Gagnant plus proche de 1.0
            higher_ratio_wins += 1
            ratio_status = "gagnant plus proche de 1.0"
        else:  # Gagnant plus éloigné de 1.0
            lower_ratio_wins += 1
            ratio_status = "gagnant plus éloigné de 1.0"
        
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
        
        detailed_cases.append({
            'winner': winner,
            'loser': loser,
            'ratio_status': ratio_status,
            'votes_status': votes_status,
            'rank_status': rank_status,
            'ratio_diff': ratio_diff,
            'votes_diff': votes_diff,
            'rank_diff': rank_diff
        })
    
    total = len(under_1_pairs)
    
    # Afficher les résultats
    print(f"\n📊 === ANALYSE RATIOS ===")
    print(f"   Gagnant a ratio PLUS PROCHE de 1.0: {higher_ratio_wins}/{total} ({higher_ratio_wins/total*100:.1f}%)")
    print(f"   Gagnant a ratio PLUS ÉLOIGNÉ de 1.0: {lower_ratio_wins}/{total} ({lower_ratio_wins/total*100:.1f}%)")
    print(f"   Ratios similaires: {ratio_similar}/{total} ({ratio_similar/total*100:.1f}%)")
    
    print(f"\n🗳️ === ANALYSE VOTES ===")
    print(f"   Gagnant a PLUS de votes: {votes_winner_higher}/{total} ({votes_winner_higher/total*100:.1f}%)")
    print(f"   Gagnant a MOINS de votes: {votes_winner_lower}/{total} ({votes_winner_lower/total*100:.1f}%)")
    print(f"   Votes similaires: {votes_similar}/{total} ({votes_similar/total*100:.1f}%)")
    
    print(f"\n🏆 === ANALYSE RANGS ===")
    print(f"   Gagnant a MEILLEUR rang: {rank_winner_better}/{total} ({rank_winner_better/total*100:.1f}%)")
    print(f"   Gagnant a PIRE rang: {rank_winner_worse}/{total} ({rank_winner_worse/total*100:.1f}%)")
    print(f"   Rangs similaires: {rank_similar}/{total} ({rank_similar/total*100:.1f}%)")
    
    # Identifier le facteur le plus décisif
    print(f"\n🎯 === FACTEURS DÉCISIFS ===")
    
    factors = [
        ("Ratio plus proche de 1.0", higher_ratio_wins, higher_ratio_wins/total*100),
        ("Plus de votes", votes_winner_higher, votes_winner_higher/total*100),
        ("Meilleur rang", rank_winner_better, rank_winner_better/total*100)
    ]
    
    factors.sort(key=lambda x: x[2], reverse=True)
    
    for i, (factor, count, percentage) in enumerate(factors):
        if i == 0:
            print(f"   🥇 FACTEUR #1: {factor} - {percentage:.1f}% ({count}/{total})")
        elif i == 1:
            print(f"   🥈 FACTEUR #2: {factor} - {percentage:.1f}% ({count}/{total})")
        else:
            print(f"   🥉 FACTEUR #3: {factor} - {percentage:.1f}% ({count}/{total})")
    
    # Analyser les tranches de ratios sous 1.0
    print(f"\n📈 === ANALYSE PAR TRANCHES ===")
    
    # Créer des tranches
    tranches = {
        'Très faible (0.0-0.3)': {'wins': 0, 'total': 0},
        'Faible (0.3-0.6)': {'wins': 0, 'total': 0},
        'Moyen (0.6-0.8)': {'wins': 0, 'total': 0},
        'Bon (0.8-1.0)': {'wins': 0, 'total': 0}
    }
    
    def get_tranche(ratio):
        if ratio < 0.3:
            return 'Très faible (0.0-0.3)'
        elif ratio < 0.6:
            return 'Faible (0.3-0.6)'
        elif ratio < 0.8:
            return 'Moyen (0.6-0.8)'
        else:
            return 'Bon (0.8-1.0)'
    
    for pair in under_1_pairs:
        p1 = pair['photo1']
        p2 = pair['photo2']
        
        # Pour photo1
        tranche1 = get_tranche(p1['ratio'])
        tranches[tranche1]['total'] += 1
        if pair['winner_is_photo1']:
            tranches[tranche1]['wins'] += 1
        
        # Pour photo2
        tranche2 = get_tranche(p2['ratio'])
        tranches[tranche2]['total'] += 1
        if not pair['winner_is_photo1']:
            tranches[tranche2]['wins'] += 1
    
    print("   Taux de victoire par tranche de ratio:")
    for tranche, stats in tranches.items():
        if stats['total'] >= 3:  # Seulement si assez d'échantillons
            win_rate = stats['wins'] / stats['total'] * 100
            print(f"      {tranche:20}: {win_rate:.1f}% ({stats['wins']}/{stats['total']})")
    
    # Exemples détaillés
    print(f"\n📋 === EXEMPLES DÉTAILLÉS (Top 10) ===")
    
    # Trier par différence de ratio pour montrer les cas intéressants
    detailed_cases.sort(key=lambda x: x['ratio_diff'], reverse=True)
    
    for i, case in enumerate(detailed_cases[:10]):
        winner = case['winner']
        loser = case['loser']
        
        print(f"\n   {i+1}. Gagnant: ratio={winner['ratio']:.3f}, votes={winner['votes']:.0f}, rang={winner['rank']:.0f}")
        print(f"      Perdant: ratio={loser['ratio']:.3f}, votes={loser['votes']:.0f}, rang={loser['rank']:.0f}")
        print(f"      Ratio: {case['ratio_status']} (diff: {case['ratio_diff']:.3f})")
        print(f"      Votes: {case['votes_status']} (diff: {case['votes_diff']:.0f})")
        print(f"      Rang: {case['rank_status']} (diff: {case['rank_diff']:.0f})")
    
    # Analyse de la logique actuelle de Bruno Custom
    print(f"\n🤖 === ANALYSE LOGIQUE BRUNO CUSTOM ACTUELLE ===")
    
    # Tester la logique actuelle: "prendre le ratio le plus proche de 1.0"
    current_logic_correct = 0
    
    for pair in under_1_pairs:
        p1 = pair['photo1']
        p2 = pair['photo2']
        
        # Logique actuelle: ratio le plus élevé (plus proche de 1.0)
        if p1['ratio'] >= p2['ratio']:
            predicted_winner = p1['id']
        else:
            predicted_winner = p2['id']
        
        if predicted_winner == pair['winner_id']:
            current_logic_correct += 1
    
    current_accuracy = current_logic_correct / total * 100
    print(f"Précision logique actuelle (ratio plus proche de 1.0): {current_accuracy:.1f}% ({current_logic_correct}/{total})")
    
    # Conclusions
    print(f"\n🎉 === CONCLUSIONS ===")
    
    main_factor = factors[0]
    if main_factor[2] > 60:
        if "Ratio plus proche" in main_factor[0]:
            print("✅ RATIO: Logique actuelle CORRECTE - Ratio plus proche de 1.0 = meilleur")
        elif "Plus de votes" in main_factor[0]:
            print("✅ VOTES: Facteur dominant - Plus de votes = victoire probable")
        elif "Meilleur rang" in main_factor[0]:
            print("✅ RANG: Facteur dominant - Meilleur rang = victoire probable")
    else:
        print("❓ AUCUN FACTEUR DOMINANT: Zone très imprévisible")
    
    # Recommandation algorithme
    print(f"\n🚀 === RECOMMANDATION ALGORITHME ===")
    
    if current_accuracy > 60:
        print(f"💡 MAINTENIR logique actuelle: Ratio plus proche de 1.0 ({current_accuracy:.1f}% précision)")
    else:
        print(f"💡 AMÉLIORER logique actuelle ({current_accuracy:.1f}% seulement):")
        
        if factors[0][2] > factors[1][2] + 10:  # Facteur dominant clair
            if "Plus de votes" in factors[0][0]:
                print("   → Priorité aux VOTES quand les deux ratios < 1.0")
            elif "Meilleur rang" in factors[0][0]:
                print("   → Priorité au RANG quand les deux ratios < 1.0")
        else:
            print("   → Logique hybride: votes + rang + ratio")
    
    # Suggestions d'amélioration
    if votes_winner_higher/total > 0.6:
        print("🔧 SUGGESTION: Ajouter seuil votes (>100 diff) avant ratio")
    if rank_winner_better/total > 0.6:
        print("🔧 SUGGESTION: Ajouter seuil rang (>200 diff) avant ratio")
    
    return {
        'total_pairs': total,
        'higher_ratio_wins': higher_ratio_wins,
        'votes_higher': votes_winner_higher,
        'rank_better': rank_winner_better,
        'current_logic_accuracy': current_accuracy,
        'main_factor': main_factor[0]
    }

if __name__ == "__main__":
    analyze_both_ratios_under_1()