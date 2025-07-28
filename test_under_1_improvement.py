#!/usr/bin/env python3
"""
Test spécifique de l'amélioration pour les cas où les deux ratios sont < 1.0
Compare la logique avant/après sur les 10 cas identifiés
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def bruno_v2_original_under_1(first_data, second_data):
    """Logique originale V2 pour les deux ratios < 1.0"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    
    # Si les deux < 1.0, prendre le moins pire (plus proche de 1.0)
    if first_ratio >= second_ratio:
        return first_data['id'], f"v2_original: ratio moins pire ({first_ratio} vs {second_ratio})"
    else:
        return second_data['id'], f"v2_original: ratio moins pire ({second_ratio} vs {first_ratio})"

def bruno_v2_improved_under_1(first_data, second_data):
    """Logique améliorée V2 pour les deux ratios < 1.0"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    
    # VOTES prioritaires (70% succès vs 40% ratio)
    votes_diff = abs(first_votes - second_votes)
    
    if votes_diff > 100:  # Différence significative de votes
        if first_votes > second_votes:
            return first_data['id'], f"v2_improved: votes prioritaires ({first_votes} vs {second_votes})"
        else:
            return second_data['id'], f"v2_improved: votes prioritaires ({second_votes} vs {first_votes})"
    
    # Si votes similaires, prendre le ratio moins pire (plus proche de 1.0)
    if first_ratio >= second_ratio:
        return first_data['id'], f"v2_improved: ratio moins pire ({first_ratio} vs {second_ratio})"
    else:
        return second_data['id'], f"v2_improved: ratio moins pire ({second_ratio} vs {first_ratio})"

def test_under_1_improvement():
    """Test l'amélioration sur les cas réels identifiés"""
    print("🧪 === TEST AMÉLIORATION DEUX RATIOS < 1.0 ===")
    print("📊 Compare logique originale vs améliorée sur 10 cas réels")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    # Identifier les cas avec deux ratios < 1.0
    under_1_cases = []
    
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
        
        if r1 < 1.0 and r2 < 1.0 and r1 > 0 and r2 > 0:
            under_1_cases.append({
                'photo1': photo1,
                'photo2': photo2,
                'winner_id': winner_id,
                'key': key
            })
    
    print(f"📊 Test sur {len(under_1_cases)} cas avec deux ratios < 1.0")
    
    if len(under_1_cases) == 0:
        print("❌ Aucun cas trouvé")
        return
    
    # Tester les deux logiques
    original_correct = 0
    improved_correct = 0
    improvements = []
    regressions = []
    
    print(f"\n📋 === ANALYSE CAS PAR CAS ===")
    
    for i, case in enumerate(under_1_cases):
        p1 = case['photo1']
        p2 = case['photo2']
        winner_name = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
        
        # Prédictions
        original_pred, original_reason = bruno_v2_original_under_1(p1, p2)
        improved_pred, improved_reason = bruno_v2_improved_under_1(p1, p2)
        
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
        
        # Affichage détaillé
        print(f"\n   {i+1}. Photo1: r={safe_float(p1.get('ratio')):.3f}, v={safe_float(p1.get('votes')):.0f}, rk={safe_float(p1.get('rank')):.0f}")
        print(f"      Photo2: r={safe_float(p2.get('ratio')):.3f}, v={safe_float(p2.get('votes')):.0f}, rk={safe_float(p2.get('rank')):.0f}")
        print(f"      Gagnant réel: {winner_name}")
        
        original_name = "Photo1" if original_pred == p1['id'] else "Photo2"
        improved_name = "Photo1" if improved_pred == p1['id'] else "Photo2"
        
        original_status = "✅" if original_correct_case else "❌"
        improved_status = "✅" if improved_correct_case else "❌"
        
        print(f"      Logique originale: {original_name} {original_status} - {original_reason}")
        print(f"      Logique améliorée: {improved_name} {improved_status} - {improved_reason}")
        
        if not original_correct_case and improved_correct_case:
            print(f"      📈 AMÉLIORATION!")
        elif original_correct_case and not improved_correct_case:
            print(f"      📉 RÉGRESSION!")
    
    # Résultats globaux
    total = len(under_1_cases)
    original_accuracy = original_correct / total * 100
    improved_accuracy = improved_correct / total * 100
    improvement = improved_accuracy - original_accuracy
    
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
        for i, imp in enumerate(improvements):
            case = imp['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne")
            print(f"      Votes: {safe_float(p1.get('votes')):.0f} vs {safe_float(p2.get('votes')):.0f}")
            print(f"      Ratios: {safe_float(p1.get('ratio')):.3f} vs {safe_float(p2.get('ratio')):.3f}")
            print(f"      Avant: {imp['original_reason']}")
            print(f"      Après: {imp['improved_reason']} ✅")
    
    # Exemples de régressions
    if regressions:
        print(f"\n⚠️ === EXEMPLES DE RÉGRESSIONS ===")
        for i, reg in enumerate(regressions):
            case = reg['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne")
            print(f"      Votes: {safe_float(p1.get('votes')):.0f} vs {safe_float(p2.get('votes')):.0f}")
            print(f"      Ratios: {safe_float(p1.get('ratio')):.3f} vs {safe_float(p2.get('ratio')):.3f}")
            print(f"      Avant: {reg['original_reason']} ✅")
            print(f"      Après: {reg['improved_reason']} ❌")
    
    # Conclusion
    print(f"\n🎯 === CONCLUSION ===")
    
    if improvement > 10:
        print(f"🎉 SUCCÈS MAJEUR! Amélioration de {improvement:.1f}%")
        print("   → L'amélioration est très bénéfique")
    elif improvement > 0:
        print(f"📈 AMÉLIORATION POSITIVE de {improvement:.1f}%")
        print("   → L'amélioration est bénéfique")
    elif improvement == 0:
        print("🤝 PERFORMANCE ÉQUIVALENTE")
        print("   → L'amélioration ne nuit pas")
    else:
        print(f"📉 RÉGRESSION de {improvement:.1f}%")
        print("   → Revoir l'amélioration")
    
    # Vérification de l'hypothèse
    votes_cases_improved = 0
    for imp in improvements:
        case = imp['case']
        p1 = case['photo1']
        p2 = case['photo2']
        votes_diff = abs(safe_float(p1.get('votes')) - safe_float(p2.get('votes')))
        if votes_diff > 100:
            votes_cases_improved += 1
    
    if len(improvements) > 0:
        print(f"\n📊 Validation hypothèse:")
        print(f"   Améliorations dues aux votes (>100 diff): {votes_cases_improved}/{len(improvements)}")
        if votes_cases_improved / len(improvements) > 0.7:
            print("   ✅ Hypothèse validée: les votes sont effectivement décisifs")
        else:
            print("   ❓ Hypothèse partielle: autres facteurs en jeu")
    
    return {
        'original_accuracy': original_accuracy,
        'improved_accuracy': improved_accuracy,
        'improvement': improvement,
        'improvements_count': len(improvements),
        'regressions_count': len(regressions)
    }

if __name__ == "__main__":
    test_under_1_improvement()