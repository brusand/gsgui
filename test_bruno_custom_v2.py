#!/usr/bin/env python3
"""
Test complet de Bruno Custom V2 affiné contre les données historiques
Compare performance avant/après amélioration
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def bruno_custom_v1_original(first_id, first_data, second_id, second_data):
    """Version originale de Bruno Custom pour comparaison"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # RÈGLE 1: Éviter ratio < 1.0
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, "v1: éviter <1.0"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, "v1: éviter <1.0"
    elif first_ratio < 1.0 and second_ratio < 1.0:
        if first_ratio >= second_ratio:
            return first_id, "v1: moins pire <1.0"
        else:
            return second_id, "v1: moins pire <1.0"

    # RÈGLE 2: Ratio supérieur si différence > 0.1
    ratio_diff = abs(first_ratio - second_ratio)
    if ratio_diff > 0.1:
        if first_ratio > second_ratio:
            return first_id, "v1: ratio supérieur"
        else:
            return second_id, "v1: ratio supérieur"

    # RÈGLE 3: Meilleur rang
    if first_rank < second_rank:
        return first_id, "v1: meilleur rang"
    elif second_rank < first_rank:
        return second_id, "v1: meilleur rang"

    # RÈGLE 4: Plus de votes
    if first_votes > second_votes:
        return first_id, "v1: plus de votes"
    else:
        return second_id, "v1: plus de votes"

def bruno_custom_v2_refined(first_id, first_data, second_id, second_data):
    """Version V2 affinée (copie de l'implémentation gsui.py)"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # RÈGLE 1: Éviter ratio < 1.0 (inchangée)
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, "v2: éviter <1.0"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, "v2: éviter <1.0"
    elif first_ratio < 1.0 and second_ratio < 1.0:
        if first_ratio >= second_ratio:
            return first_id, "v2: moins pire <1.0"
        else:
            return second_id, "v2: moins pire <1.0"

    # RÈGLE 2: CAS SPÉCIAL RATIO ~1.5 - VOTES prioritaires
    both_near_15 = (abs(first_ratio - 1.5) <= 0.1 and abs(second_ratio - 1.5) <= 0.1)
    
    if both_near_15:
        votes_diff = abs(first_votes - second_votes)
        
        if votes_diff > 100:  # Différence significative
            if first_votes > second_votes:
                return first_id, "v2: zone1.5 - votes prioritaires"
            else:
                return second_id, "v2: zone1.5 - votes prioritaires"
        
        # Si votes similaires, ratio élevé
        ratio_diff = abs(first_ratio - second_ratio)
        if ratio_diff > 0.05:
            if first_ratio > second_ratio:
                return first_id, "v2: zone1.5 - ratio élevé"
            else:
                return second_id, "v2: zone1.5 - ratio élevé"
        
        # Fallback: rang
        if first_rank < second_rank:
            return first_id, "v2: zone1.5 - fallback rang"
        else:
            return second_id, "v2: zone1.5 - fallback rang"

    # RÈGLE 3: CAS SPÉCIAL SPLIT ≥1.5 vs <1.5
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
        
        # Détecter compensation massive
        massive_votes_compensation = low_ratio_votes > high_ratio_votes * 2
        massive_rank_compensation = low_ratio_rank < high_ratio_rank * 0.3
        
        if massive_votes_compensation or massive_rank_compensation:
            if high_is_first:
                return second_id, "v2: split1.5 - compensation massive"
            else:
                return first_id, "v2: split1.5 - compensation massive"
        
        # Triple avantage haute ratio
        triple_advantage = (high_ratio_votes > low_ratio_votes and high_ratio_rank < low_ratio_rank)
        
        if triple_advantage:
            if high_is_first:
                return first_id, "v2: split1.5 - triple avantage"
            else:
                return second_id, "v2: split1.5 - triple avantage"
        
        # Léger avantage ratio élevé
        if high_is_first:
            return first_id, "v2: split1.5 - léger avantage ratio élevé"
        else:
            return second_id, "v2: split1.5 - léger avantage ratio élevé"

    # RÈGLE 4: LOGIQUE CLASSIQUE (améliorée)
    ratio_diff = abs(first_ratio - second_ratio)
    if ratio_diff > 0.1:
        if first_ratio > second_ratio:
            return first_id, "v2: ratio supérieur classique"
        else:
            return second_id, "v2: ratio supérieur classique"

    # Rang avec seuil
    rank_diff = abs(first_rank - second_rank)
    if rank_diff > 50:
        if first_rank < second_rank:
            return first_id, "v2: meilleur rang classique"
        else:
            return second_id, "v2: meilleur rang classique"

    # Fallback votes
    if first_votes > second_votes:
        return first_id, "v2: plus de votes fallback"
    else:
        return second_id, "v2: plus de votes fallback"

def test_bruno_v1_vs_v2():
    """Compare les deux versions sur l'historique complet"""
    print("🚀 === COMPARAISON BRUNO CUSTOM V1 vs V2 ===")
    print("📊 Test sur historique complet de turbo")
    print("=" * 55)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Préparer les données de test
    test_cases = []
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
            
        test_cases.append({
            'photo1': photo1,
            'photo2': photo2, 
            'winner_id': winner_id,
            'key': key
        })
    
    print(f"📊 Test sur {len(test_cases)} comparaisons")
    
    # Tester les deux versions
    v1_correct = 0
    v2_correct = 0
    both_correct = 0
    both_wrong = 0
    v1_only = 0
    v2_only = 0
    
    # Analyser les améliorations par cas spéciaux
    zone_15_cases = 0
    zone_15_v2_better = 0
    split_15_cases = 0  
    split_15_v2_better = 0
    
    improvements = []
    regressions = []
    
    for case in test_cases:
        # Prédictions
        v1_pred, v1_reason = bruno_custom_v1_original(
            case['photo1']['id'], case['photo1'], 
            case['photo2']['id'], case['photo2']
        )
        v2_pred, v2_reason = bruno_custom_v2_refined(
            case['photo1']['id'], case['photo1'],
            case['photo2']['id'], case['photo2']
        )
        
        # Vérifications
        v1_correct_case = v1_pred == case['winner_id']
        v2_correct_case = v2_pred == case['winner_id']
        
        if v1_correct_case:
            v1_correct += 1
        if v2_correct_case:
            v2_correct += 1
        
        if v1_correct_case and v2_correct_case:
            both_correct += 1
        elif not v1_correct_case and not v2_correct_case:
            both_wrong += 1
        elif v1_correct_case and not v2_correct_case:
            v1_only += 1
            regressions.append({
                'case': case,
                'v1_reason': v1_reason,
                'v2_reason': v2_reason
            })
        elif not v1_correct_case and v2_correct_case:
            v2_only += 1
            improvements.append({
                'case': case,
                'v1_reason': v1_reason,
                'v2_reason': v2_reason
            })
        
        # Analyser cas spéciaux
        r1 = safe_float(case['photo1'].get('ratio', 0))
        r2 = safe_float(case['photo2'].get('ratio', 0))
        
        # Zone 1.5
        if abs(r1 - 1.5) <= 0.1 and abs(r2 - 1.5) <= 0.1:
            zone_15_cases += 1
            if v2_correct_case and not v1_correct_case:
                zone_15_v2_better += 1
        
        # Split 1.5
        if (r1 >= 1.5 and r2 < 1.5) or (r2 >= 1.5 and r1 < 1.5):
            split_15_cases += 1
            if v2_correct_case and not v1_correct_case:
                split_15_v2_better += 1
    
    total = len(test_cases)
    v1_accuracy = v1_correct / total * 100
    v2_accuracy = v2_correct / total * 100
    improvement = v2_accuracy - v1_accuracy
    
    # Résultats
    print(f"\n📈 === RÉSULTATS GLOBAUX ===")
    print(f"Bruno Custom V1: {v1_accuracy:.1f}% ({v1_correct}/{total})")
    print(f"Bruno Custom V2: {v2_accuracy:.1f}% ({v2_correct}/{total})")
    print(f"Amélioration: {improvement:+.1f}%")
    
    print(f"\n🔢 === RÉPARTITION DÉTAILLÉE ===")
    print(f"✅ Les deux corrects: {both_correct} ({both_correct/total*100:.1f}%)")
    print(f"❌ Les deux incorrects: {both_wrong} ({both_wrong/total*100:.1f}%)")
    print(f"🆕 V2 seul correct: {v2_only} ({v2_only/total*100:.1f}%)")
    print(f"🔙 V1 seul correct: {v1_only} ({v1_only/total*100:.1f}%)")
    
    # Analyse cas spéciaux
    print(f"\n🎯 === ANALYSE CAS SPÉCIAUX ===")
    if zone_15_cases > 0:
        print(f"Zone 1.5: {zone_15_v2_better}/{zone_15_cases} améliorations V2 ({zone_15_v2_better/zone_15_cases*100:.1f}%)")
    if split_15_cases > 0:
        print(f"Split 1.5: {split_15_v2_better}/{split_15_cases} améliorations V2 ({split_15_v2_better/split_15_cases*100:.1f}%)")
    
    # Exemples d'améliorations
    if improvements:
        print(f"\n🎉 === TOP 5 AMÉLIORATIONS V2 ===")
        for i, imp in enumerate(improvements[:5]):
            case = imp['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne")
            print(f"      Photo1: r={safe_float(p1.get('ratio')):.2f}, v={safe_float(p1.get('votes')):.0f}, rk={safe_float(p1.get('rank')):.0f}")
            print(f"      Photo2: r={safe_float(p2.get('ratio')):.2f}, v={safe_float(p2.get('votes')):.0f}, rk={safe_float(p2.get('rank')):.0f}")
            print(f"      V1: {imp['v1_reason']}")
            print(f"      V2: {imp['v2_reason']} ✅")
    
    # Exemples de régressions
    if regressions:
        print(f"\n⚠️ === TOP 3 RÉGRESSIONS V2 ===")
        for i, reg in enumerate(regressions[:3]):
            case = reg['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne")
            print(f"      Photo1: r={safe_float(p1.get('ratio')):.2f}, v={safe_float(p1.get('votes')):.0f}, rk={safe_float(p1.get('rank')):.0f}")
            print(f"      Photo2: r={safe_float(p2.get('ratio')):.2f}, v={safe_float(p2.get('votes')):.0f}, rk={safe_float(p2.get('rank')):.0f}")
            print(f"      V1: {reg['v1_reason']} ✅") 
            print(f"      V2: {reg['v2_reason']} ❌")
    
    # Conclusion
    print(f"\n🎯 === CONCLUSION ===")
    
    if improvement > 2:
        print(f"🎉 SUCCÈS! V2 améliore significativement (+{improvement:.1f}%)")
        print("   → Intégration recommandée")
    elif improvement > 0.5:
        print(f"📈 AMÉLIORATION MODÉRÉE (+{improvement:.1f}%)")
        print("   → Intégration bénéfique")
    elif improvement > -0.5:
        print(f"🤝 PERFORMANCE ÉQUIVALENTE ({improvement:+.1f}%)")
        print("   → V2 maintient la performance avec logique plus sophistiquée")
    else:
        print(f"📉 RÉGRESSION ({improvement:.1f}%)")
        print("   → Revoir les seuils ou maintenir V1")
    
    return {
        'v1_accuracy': v1_accuracy,
        'v2_accuracy': v2_accuracy,
        'improvement': improvement,
        'improvements_count': len(improvements),
        'regressions_count': len(regressions)
    }

if __name__ == "__main__":
    test_bruno_v1_vs_v2()