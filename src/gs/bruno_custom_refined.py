#!/usr/bin/env python3
"""
Version affinée de Bruno Custom basée sur les analyses statistiques
- Analyse ratio ~1.5: votes prioritaires (53.2%), puis ratio élevé (44.9%)
- Analyse split ≥1.5 vs <1.5: compensation massive par votes/rang
- Maintient la logique éprouvée tout en ajoutant des cas spéciaux
"""

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def bruno_custom_refined(first_id, first_data, second_id, second_data):
    """
    Algorithme Bruno Custom Affiné - Version 2.0
    Basé sur analyses statistiques: 
    - 265 pairs ratio ~1.5: votes (53.2%) > ratio élevé (44.9%) > rang (38.9%)
    - 194 pairs split 1.5: équilibré 52.1% vs 47.9%, compensation cruciale
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # =================== RÈGLE 1: ÉVITER RATIO < 1.0 ===================
    # (Règle universelle - maintenue inchangée)
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: éviter <1.0 ({first_ratio} vs {second_ratio})"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: éviter <1.0 ({second_ratio} vs {first_ratio})"
    elif first_ratio < 1.0 and second_ratio < 1.0:
        # Si les deux < 1.0, prendre le moins pire
        if first_ratio >= second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: moins pire <1.0 ({first_ratio} vs {second_ratio})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: moins pire <1.0 ({second_ratio} vs {first_ratio})"

    # =================== RÈGLE 2: CAS SPÉCIAL RATIO ~1.5 ===================
    # Analyse: 265 pairs avec ratio ~1.5 - VOTES prioritaires (53.2% succès)
    both_near_15 = (abs(first_ratio - 1.5) <= 0.1 and abs(second_ratio - 1.5) <= 0.1)
    
    if both_near_15:
        # Dans la zone 1.5, les VOTES sont le facteur #1 (53.2% vs 44.9% ratio)
        votes_diff = abs(first_votes - second_votes)
        
        if votes_diff > 100:  # Différence significative
            if first_votes > second_votes:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - votes prioritaires ({first_votes} vs {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - votes prioritaires ({second_votes} vs {first_votes})"
        
        # Si votes similaires dans zone 1.5, utiliser ratio élevé (facteur #2)
        ratio_diff = abs(first_ratio - second_ratio)
        if ratio_diff > 0.05:
            if first_ratio > second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - ratio élevé ({first_ratio} vs {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - ratio élevé ({second_ratio} vs {first_ratio})"
        
        # Fallback zone 1.5: rang (facteur #3 - 38.9%)
        if first_rank < second_rank:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - fallback rang ({first_rank} vs {second_rank})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - fallback rang ({second_rank} vs {first_rank})"

    # =================== RÈGLE 3: CAS SPÉCIAL SPLIT ≥1.5 vs <1.5 ===================
    # Analyse: 194 pairs split - Combat équilibré mais compensation massive efficace
    split_15 = ((first_ratio >= 1.5 and second_ratio < 1.5) or (second_ratio >= 1.5 and first_ratio < 1.5))
    
    if split_15:
        # Identifier qui a le ratio élevé/faible
        if first_ratio >= 1.5:
            high_ratio_votes, low_ratio_votes = first_votes, second_votes
            high_ratio_rank, low_ratio_rank = first_rank, second_rank
            high_is_first = True
        else:
            high_ratio_votes, low_ratio_votes = second_votes, first_votes
            high_ratio_rank, low_ratio_rank = second_rank, first_rank
            high_is_first = False
        
        # Détecter compensation massive par basse ratio (69.9% succès quand ça compense)
        massive_votes_compensation = low_ratio_votes > high_ratio_votes * 2
        massive_rank_compensation = low_ratio_rank < high_ratio_rank * 0.3  # Rang excellent
        
        if massive_votes_compensation or massive_rank_compensation:
            # Basse ratio compense massivement
            if high_is_first:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - compensation massive (votes:{low_ratio_votes} vs {high_ratio_votes}, rang:{low_ratio_rank} vs {high_ratio_rank})"
            else:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - compensation massive (votes:{low_ratio_votes} vs {high_ratio_votes}, rang:{low_ratio_rank} vs {high_ratio_rank})"
        
        # Détecter triple avantage haute ratio (79% succès)
        triple_advantage = (high_ratio_votes > low_ratio_votes and high_ratio_rank < low_ratio_rank)
        
        if triple_advantage:
            # Haute ratio a triple avantage
            if high_is_first:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - triple avantage ratio+votes+rang"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - triple avantage ratio+votes+rang"
        
        # Split équilibré: léger avantage au ratio élevé (52.1% vs 47.9%)
        if high_is_first:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - léger avantage ratio élevé"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - léger avantage ratio élevé"

    # =================== RÈGLE 4: LOGIQUE CLASSIQUE BRUNO ===================
    # (Pour tous les autres cas non couverts par les analyses spéciales)
    
    # Si différence de ratio significative (> 0.1), privilégier le plus élevé
    ratio_diff = abs(first_ratio - second_ratio)
    if ratio_diff > 0.1:
        if first_ratio > second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: ratio supérieur classique ({first_ratio} vs {second_ratio})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: ratio supérieur classique ({second_ratio} vs {first_ratio})"

    # Si ratios similaires, utiliser le meilleur rang
    rank_diff = abs(first_rank - second_rank)
    if rank_diff > 50:  # Seuil significatif
        if first_rank < second_rank:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: meilleur rang classique ({first_rank} vs {second_rank})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: meilleur rang classique ({second_rank} vs {first_rank})"

    # Fallback: plus de votes
    if first_votes > second_votes:
        return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: plus de votes fallback ({first_votes} vs {second_votes})"
    else:
        return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: plus de votes fallback ({second_votes} vs {first_votes})"

# Test de l'algorithme affiné
def test_refined_algorithm():
    """Test comparatif entre Bruno Custom original et affiné"""
    print("🧪 === TEST BRUNO CUSTOM AFFINÉ ===")
    
    # Cas de test basés sur les analyses
    test_cases = [
        # Cas 1: Zone 1.5 - votes doivent primer
        {
            'name': 'Zone 1.5 - votes prioritaires',
            'photo1': {'ratio': 1.48, 'votes': 300, 'rank': 200},
            'photo2': {'ratio': 1.52, 'votes': 150, 'rank': 180},
            'expected_winner': 'photo1',  # Plus de votes
            'reason': 'zone1.5 - votes prioritaires'
        },
        
        # Cas 2: Split 1.5 - compensation massive
        {
            'name': 'Split 1.5 - compensation votes',
            'photo1': {'ratio': 1.8, 'votes': 100, 'rank': 500},
            'photo2': {'ratio': 1.2, 'votes': 800, 'rank': 50},
            'expected_winner': 'photo2',  # Compensation massive
            'reason': 'split1.5 - compensation massive'
        },
        
        # Cas 3: Split 1.5 - triple avantage
        {
            'name': 'Split 1.5 - triple avantage',
            'photo1': {'ratio': 1.7, 'votes': 200, 'rank': 100},
            'photo2': {'ratio': 1.3, 'votes': 150, 'rank': 300},
            'expected_winner': 'photo1',  # Triple avantage
            'reason': 'split1.5 - triple avantage'
        },
        
        # Cas 4: Classique - éviter <1.0
        {
            'name': 'Classique - éviter <1.0',
            'photo1': {'ratio': 0.8, 'votes': 500, 'rank': 50},
            'photo2': {'ratio': 1.5, 'votes': 100, 'rank': 400},
            'expected_winner': 'photo2',  # Éviter <1.0
            'reason': 'éviter <1.0'
        }
    ]
    
    print(f"Testant {len(test_cases)} cas...")
    
    for i, case in enumerate(test_cases):
        winner, winner_ratio, loser_ratio, winner_votes, reason = bruno_custom_refined(
            'photo1', case['photo1'], 'photo2', case['photo2']
        )
        
        success = winner == case['expected_winner']
        expected_reason_found = case['reason'] in reason
        
        print(f"\n{i+1}. {case['name']}")
        print(f"   Photo1: r={case['photo1']['ratio']}, v={case['photo1']['votes']}, rk={case['photo1']['rank']}")
        print(f"   Photo2: r={case['photo2']['ratio']}, v={case['photo2']['votes']}, rk={case['photo2']['rank']}")
        print(f"   Gagnant: {winner} {'✅' if success else '❌'}")
        print(f"   Raison: {reason}")
        print(f"   Logique attendue: {'✅' if expected_reason_found else '❌'}")

if __name__ == "__main__":
    test_refined_algorithm()