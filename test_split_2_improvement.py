#!/usr/bin/env python3
"""
Test spécifique de l'amélioration pour les cas split ≥2.0 vs <2.0
Vérifie si la nouvelle logique améliore les prédictions
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def bruno_v2_original_split_2(first_data, second_data):
    """Logique originale V2 pour split ≥2.0 vs <2.0 (ratio supérieur)"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    
    # Logique classique: ratio supérieur
    if first_ratio > second_ratio:
        return first_data['id'], f"v2_original: ratio supérieur ({first_ratio} vs {second_ratio})"
    else:
        return second_data['id'], f"v2_original: ratio supérieur ({second_ratio} vs {first_ratio})"

def bruno_v2_improved_split_2(first_data, second_data):
    """Logique améliorée V2 pour split ≥2.0 vs <2.0"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))
    
    # Identifier qui a le ratio très élevé/normal
    if first_ratio >= 2.0:
        very_high_votes, normal_votes = first_votes, second_votes
        very_high_rank, normal_rank = first_rank, second_rank
        very_high_is_first = True
    else:
        very_high_votes, normal_votes = second_votes, first_votes
        very_high_rank, normal_rank = second_rank, first_rank
        very_high_is_first = False
    
    # Détecter compensation massive par ratio normal (33% succès)
    massive_votes_comp = normal_votes > very_high_votes * 2
    massive_rank_comp = normal_rank < very_high_rank * 0.5
    
    if massive_votes_comp or massive_rank_comp:
        # Ratio normal compense massivement
        if very_high_is_first:
            return second_data['id'], f"v2_improved: compensation massive vs ratio très élevé"
        else:
            return first_data['id'], f"v2_improved: compensation massive vs ratio très élevé"
    
    # Détecter double avantage ratio très élevé (77% ont meilleur rang)
    double_advantage = (very_high_votes >= normal_votes and very_high_rank < normal_rank)
    
    if double_advantage:
        # Ratio très élevé a double avantage
        if very_high_is_first:
            return first_data['id'], f"v2_improved: double avantage ratio très élevé"
        else:
            return second_data['id'], f"v2_improved: double avantage ratio très élevé"
    
    # Split équilibré: légère préférence ratio très élevé (52% vs 48%)
    if very_high_is_first:
        return first_data['id'], f"v2_improved: légère préférence ratio très élevé"
    else:
        return second_data['id'], f"v2_improved: légère préférence ratio très élevé"

def test_split_2_improvement():
    """Test l'amélioration sur les cas split ≥2.0 vs <2.0"""
    print("🧪 === TEST AMÉLIORATION SPLIT ≥2.0 vs <2.0 ===")
    print("📊 Compare logique originale vs améliorée sur cas réels")
    print("=" * 55)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    # Identifier les cas split ≥2.0 vs <2.0
    split_2_cases = []
    
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
        
        # Vérifier split ≥2.0 vs <2.0
        if (r1 >= 2.0 and r2 < 2.0) or (r2 >= 2.0 and r1 < 2.0):
            split_2_cases.append({
                'photo1': photo1,
                'photo2': photo2,
                'winner_id': winner_id,
                'key': key
            })
    
    print(f"📊 Test sur {len(split_2_cases)} cas split ≥2.0 vs <2.0")
    
    if len(split_2_cases) == 0:
        print("❌ Aucun cas trouvé")
        return
    
    # Tester les deux logiques
    original_correct = 0
    improved_correct = 0
    improvements = []
    regressions = []
    
    for case in split_2_cases:
        # Prédictions
        original_pred, original_reason = bruno_v2_original_split_2(case['photo1'], case['photo2'])
        improved_pred, improved_reason = bruno_v2_improved_split_2(case['photo1'], case['photo2'])
        
        # Vérifications
        original_correct_case = original_pred == case['winner_id']
        improved_correct_case = improved_pred == case['winner_id']
        
        if original_correct_case:
            original_correct += 1
        if improved_correct_case:
            improved_correct += 1
        
        # Identifier les changements
        if not original_correct_case and improved_correct_case:
            improvements.append({
                'case': case,
                'original_reason': original_reason,
                'improved_reason': improved_reason
            })
        elif original_correct_case and not improved_correct_case:
            regressions.append({
                'case': case,
                'original_reason': original_reason,
                'improved_reason': improved_reason
            })
    
    total = len(split_2_cases)
    original_accuracy = original_correct / total * 100
    improved_accuracy = improved_correct / total * 100
    improvement = improved_accuracy - original_accuracy
    
    # Résultats globaux
    print(f"\n📈 === RÉSULTATS GLOBAUX ===")
    print(f"Logique originale: {original_accuracy:.1f}% ({original_correct}/{total})")
    print(f"Logique améliorée: {improved_accuracy:.1f}% ({improved_correct}/{total})")
    print(f"Amélioration: {improvement:+.1f}%")
    
    print(f"\n🔢 === DÉTAILS ===")
    print(f"📈 Améliorations: {len(improvements)} cas")
    print(f"📉 Régressions: {len(regressions)} cas")
    print(f"Balance: {len(improvements) - len(regressions):+d} cas")
    
    # Exemples d'améliorations
    if improvements:
        print(f"\n🎉 === EXEMPLES D'AMÉLIORATIONS ===")
        for i, imp in enumerate(improvements[:3]):
            case = imp['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne")
            print(f"      Photo1: r={safe_float(p1.get('ratio')):.2f}, v={safe_float(p1.get('votes')):.0f}, rk={safe_float(p1.get('rank')):.0f}")
            print(f"      Photo2: r={safe_float(p2.get('ratio')):.2f}, v={safe_float(p2.get('votes')):.0f}, rk={safe_float(p2.get('rank')):.0f}")
            print(f"      Avant: {imp['original_reason']}")
            print(f"      Après: {imp['improved_reason']} ✅")
    
    # Conclusion
    print(f"\n🎯 === CONCLUSION ===")
    
    if improvement > 5:
        print(f"🎉 SUCCÈS! Amélioration significative de {improvement:.1f}%")
    elif improvement > 0:
        print(f"📈 AMÉLIORATION POSITIVE de {improvement:.1f}%")
    elif improvement >= -2:
        print(f"🤝 PERFORMANCE STABLE ({improvement:+.1f}%)")
    else:
        print(f"📉 RÉGRESSION de {improvement:.1f}%")
    
    return {
        'original_accuracy': original_accuracy,
        'improved_accuracy': improved_accuracy,
        'improvement': improvement,
        'improvements_count': len(improvements),
        'total_cases': total
    }

if __name__ == "__main__":
    test_split_2_improvement()