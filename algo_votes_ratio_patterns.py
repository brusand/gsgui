#!/usr/bin/env python3
"""
Algorithme basé sur l'analyse des rapports votes/ratio
Implémente les patterns découverts pour améliorer les prédictions turbo
"""

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def algo_votes_ratio_patterns(first_id, first_data, second_id, second_data):
    """
    Algorithme optimisé basé sur l'analyse des rapports votes/ratio
    
    Découvertes clés:
    - Rapport votes < 0.2: MAX votes gagne 93.3%
    - Rapport votes < 0.3: MAX votes gagne 76.2%  
    - Pattern dominant: Double domination (MAX votes + MAX ratio) = 38.9%
    """
    
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))
    
    # Éviter les données invalides
    if first_votes <= 0 or second_votes <= 0 or first_ratio <= 0 or second_ratio <= 0:
        # Fallback
        if first_ratio > second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, "pattern: fallback ratio"
        else:
            return second_id, second_ratio, first_ratio, second_votes, "pattern: fallback ratio"
    
    # Calculer les rapports
    votes_min = min(first_votes, second_votes)
    votes_max = max(first_votes, second_votes)
    votes_ratio = votes_min / votes_max  # Entre 0 et 1
    
    ratio_min = min(first_ratio, second_ratio)
    ratio_max = max(first_ratio, second_ratio)
    ratio_rapport = ratio_min / ratio_max  # Entre 0 et 1
    
    # Déterminer qui a les max
    first_has_votes_max = first_votes >= second_votes
    first_has_ratio_max = first_ratio >= second_ratio
    
    # =================== RÈGLE 1: DÉSÉQUILIBRE VOTES EXTRÊME ===================
    # Rapport votes < 0.2: MAX votes gagne 93.3% (15/15 dans l'analyse)
    if votes_ratio < 0.2:
        if first_has_votes_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - MAX votes prioritaire"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - MAX votes prioritaire"
    
    # =================== RÈGLE 2: DÉSÉQUILIBRE VOTES FORT ===================
    # Rapport votes < 0.3: MAX votes gagne 76.2% (32/42 dans l'analyse)
    if votes_ratio < 0.3:
        if first_has_votes_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - MAX votes très favorisé"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - MAX votes très favorisé"
    
    # =================== RÈGLE 3: DÉSÉQUILIBRE VOTES MODÉRÉ ===================
    # Rapport votes < 0.4: MAX votes gagne 76.4% (55/72 dans l'analyse)
    if votes_ratio < 0.4:
        if first_has_votes_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - MAX votes favorisé"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - MAX votes favorisé"
    
    # =================== RÈGLE 4: DOUBLE DOMINATION ===================
    # Pattern dominant: MAX votes + MAX ratio = 38.9% des cas
    # Dans zone équilibrée (0.6-0.8 votes), MAX votes gagne encore 75.6%
    if votes_ratio >= 0.6 and votes_ratio <= 0.8:
        # Zone équilibrée - MAX votes reste très favorisé (75.6%)
        if first_has_votes_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes reste dominant (75.6%)"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes reste dominant (75.6%)"
    
    # =================== RÈGLE 5: TRÈS ÉQUILIBRÉ - DOUBLE DOMINATION ===================
    # Zone très équilibrée (0.8-1.0): MAX votes gagne 68.0%
    # Pattern double domination prioritaire
    if votes_ratio >= 0.8:
        # Privilégier la double domination (MAX votes + MAX ratio)
        if first_has_votes_max and first_has_ratio_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: double domination photo1 (votes:{first_votes:.0f} ratio:{first_ratio:.3f})"
        elif (not first_has_votes_max) and (not first_has_ratio_max):
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: double domination photo2 (votes:{second_votes:.0f} ratio:{second_ratio:.3f})"
        else:
            # Cas mixte - privilégier MAX votes (68% dans zone très équilibrée)
            if first_has_votes_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes prioritaire (68%)"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes prioritaire (68%)"
    
    # =================== RÈGLE 6: CAS INTERMÉDIAIRE ===================
    # Zone modérée (0.4-0.6): MAX votes gagne 60.9% - moins dominant
    # Utiliser logique hybride
    if votes_ratio >= 0.4 and votes_ratio < 0.6:
        # Analyser les ratios aussi
        if ratio_rapport < 0.5:
            # Déséquilibre ratio - privilégier MAX ratio
            if first_has_ratio_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone modérée + déséquilibre ratio ({ratio_rapport:.3f}) - MAX ratio"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone modérée + déséquilibre ratio ({ratio_rapport:.3f}) - MAX ratio"
        else:
            # Ratios équilibrés - privilégier MAX votes (60.9%)
            if first_has_votes_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone modérée équilibrée - MAX votes (60.9%)"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone modérée équilibrée - MAX votes (60.9%)"
    
    # =================== FALLBACK ===================
    # Si aucun pattern identifié, utiliser double domination
    if first_has_votes_max and first_has_ratio_max:
        return first_id, first_ratio, second_ratio, first_votes, f"pattern: fallback double domination photo1"
    elif (not first_has_votes_max) and (not first_has_ratio_max):
        return second_id, second_ratio, first_ratio, second_votes, f"pattern: fallback double domination photo2"
    elif first_has_votes_max:
        return first_id, first_ratio, second_ratio, first_votes, f"pattern: fallback MAX votes"
    else:
        return second_id, second_ratio, first_ratio, second_votes, f"pattern: fallback MAX votes"

# Test de l'algorithme
if __name__ == "__main__":
    # Test cases basés sur les exemples découverts
    test_cases = [
        # Cas 1: Déséquilibre extrême (rapport 0.052)
        {
            'first_data': {'votes': 267, 'ratio': 1.330, 'rank': 300},
            'second_data': {'votes': 14, 'ratio': 1.500, 'rank': 400},
            'expected_winner': 'first',  # MAX votes gagne
            'case_name': 'Déséquilibre extrême (0.052)'
        },
        # Cas 2: Double domination
        {
            'first_data': {'votes': 642, 'ratio': 1.522, 'rank': 200},
            'second_data': {'votes': 55, 'ratio': 1.036, 'rank': 500},
            'expected_winner': 'first',  # Double domination
            'case_name': 'Double domination'
        },
        # Cas 3: Zone équilibrée
        {
            'first_data': {'votes': 500, 'ratio': 1.200, 'rank': 300},
            'second_data': {'votes': 400, 'ratio': 1.300, 'rank': 250},
            'expected_winner': 'first',  # MAX votes dans zone équilibrée
            'case_name': 'Zone équilibrée'
        }
    ]
    
    print("🧪 === TEST ALGORITHME VOTES/RATIO PATTERNS ===")
    
    for i, test in enumerate(test_cases):
        result = algo_votes_ratio_patterns(
            'first', test['first_data'],
            'second', test['second_data']
        )
        
        winner_id, winner_ratio, loser_ratio, winner_votes, strategy = result
        predicted_winner = 'first' if winner_id == 'first' else 'second'
        
        success = "✅" if predicted_winner == test['expected_winner'] else "❌"
        
        print(f"\n   {i+1}. {test['case_name']}")
        print(f"      Données: First({test['first_data']['votes']}v, {test['first_data']['ratio']}r) vs Second({test['second_data']['votes']}v, {test['second_data']['ratio']}r)")
        print(f"      Prédiction: {predicted_winner} {success}")
        print(f"      Stratégie: {strategy}")