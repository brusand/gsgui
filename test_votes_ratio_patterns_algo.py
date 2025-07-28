#!/usr/bin/env python3
"""
Test de l'algorithme votes_ratio_patterns sur l'historique réel
Compare sa performance avec les autres algorithmes
"""

from configobj import ConfigObj
import sys
import os

# Ajouter le chemin vers gsui.py
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'gs'))

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def algo_votes_ratio_patterns(first_id, first_data, second_id, second_data):
    """
    Réimplémentation de l'algorithme pour test autonome
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
            return first_id, "pattern: fallback ratio (données invalides)"
        else:
            return second_id, "pattern: fallback ratio (données invalides)"
    
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
    # Rapport votes < 0.2: MAX votes gagne 93.3% (14/15 dans l'analyse)
    if votes_ratio < 0.2:
        if first_has_votes_max:
            return first_id, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - 93.3% succès"
        else:
            return second_id, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - 93.3% succès"
    
    # =================== RÈGLE 2: DÉSÉQUILIBRE VOTES FORT ===================
    # Rapport votes < 0.3: MAX votes gagne 76.2% (32/42 dans l'analyse)
    if votes_ratio < 0.3:
        if first_has_votes_max:
            return first_id, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - 76.2% succès"
        else:
            return second_id, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - 76.2% succès"
    
    # =================== RÈGLE 3: DÉSÉQUILIBRE VOTES MODÉRÉ ===================
    # Rapport votes < 0.4: MAX votes gagne 76.4% (55/72 dans l'analyse)
    if votes_ratio < 0.4:
        if first_has_votes_max:
            return first_id, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - 76.4% succès"
        else:
            return second_id, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - 76.4% succès"
    
    # =================== RÈGLE 4: ZONE ÉQUILIBRÉE - DOMINANCE VOTES ===================
    # Zone équilibrée (0.6-0.8 votes): MAX votes gagne encore 75.6% (68/90)
    if votes_ratio >= 0.6 and votes_ratio <= 0.8:
        if first_has_votes_max:
            return first_id, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes dominant 75.6%"
        else:
            return second_id, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes dominant 75.6%"
    
    # =================== RÈGLE 5: TRÈS ÉQUILIBRÉ - DOUBLE DOMINATION ===================
    # Zone très équilibrée (0.8-1.0): MAX votes gagne 68.0% (100/147)
    # Pattern double domination prioritaire
    if votes_ratio >= 0.8:
        # Privilégier la double domination (MAX votes + MAX ratio)
        if first_has_votes_max and first_has_ratio_max:
            return first_id, f"pattern: double domination photo1 (v:{first_votes:.0f} r:{first_ratio:.3f})"
        elif (not first_has_votes_max) and (not first_has_ratio_max):
            return second_id, f"pattern: double domination photo2 (v:{second_votes:.0f} r:{second_ratio:.3f})"
        else:
            # Cas mixte - privilégier MAX votes (68% dans zone très équilibrée)
            if first_has_votes_max:
                return first_id, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes 68%"
            else:
                return second_id, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes 68%"
    
    # =================== RÈGLE 6: CAS INTERMÉDIAIRE ===================
    # Zone modérée (0.4-0.6): MAX votes gagne 60.9% (42/69) - moins dominant
    # Utiliser logique hybride avec ratios
    if votes_ratio >= 0.4 and votes_ratio < 0.6:
        # Analyser les ratios aussi pour les cas modérés
        if ratio_rapport < 0.5:
            # Déséquilibre ratio fort - privilégier MAX ratio
            if first_has_ratio_max:
                return first_id, f"pattern: zone modérée + déséq. ratio ({ratio_rapport:.3f}) - MAX ratio"
            else:
                return second_id, f"pattern: zone modérée + déséq. ratio ({ratio_rapport:.3f}) - MAX ratio"
        else:
            # Ratios équilibrés - privilégier MAX votes (60.9%)
            if first_has_votes_max:
                return first_id, f"pattern: zone modérée équilibrée - MAX votes 60.9%"
            else:
                return second_id, f"pattern: zone modérée équilibrée - MAX votes 60.9%"
    
    # =================== FALLBACK ===================
    # Si aucun pattern identifié clairement, utiliser double domination
    # (Pattern le plus fréquent: 38.9% des cas)
    if first_has_votes_max and first_has_ratio_max:
        return first_id, f"pattern: fallback double domination photo1"
    elif (not first_has_votes_max) and (not first_has_ratio_max):
        return second_id, f"pattern: fallback double domination photo2"
    elif first_has_votes_max:
        return first_id, f"pattern: fallback MAX votes"
    else:
        return second_id, f"pattern: fallback MAX votes"

def algo_bruno_custom(first_id, first_data, second_id, second_data):
    """Bruno Custom V2 pour comparaison"""
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # Logique simplifiée de Bruno Custom (cas principal: ratio supérieur)
    if abs(first_ratio - second_ratio) > 0.1:
        if first_ratio > second_ratio:
            return first_id, f"bruno_v2: ratio supérieur ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"bruno_v2: ratio supérieur ({second_ratio} vs {first_ratio})"
    
    # Ratios similaires: meilleur rang
    if abs(first_rank - second_rank) > 50:
        if first_rank < second_rank:
            return first_id, f"bruno_v2: meilleur rang ({first_rank} vs {second_rank})"
        else:
            return second_id, f"bruno_v2: meilleur rang ({second_rank} vs {first_rank})"
    
    # Fallback: plus de votes
    if first_votes > second_votes:
        return first_id, f"bruno_v2: plus de votes ({first_votes} vs {second_votes})"
    else:
        return second_id, f"bruno_v2: plus de votes ({second_votes} vs {first_votes})"

def test_votes_ratio_patterns_performance():
    """Test l'algorithme votes_ratio_patterns vs Bruno Custom"""
    print("🧪 === TEST PERFORMANCE VOTES/RATIO PATTERNS ===")
    print("📊 Compare nouvel algorithme vs Bruno Custom V2")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Tester les deux algorithmes
    patterns_correct = 0
    bruno_correct = 0
    total_cases = 0
    patterns_better = []
    bruno_better = []
    
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
        
        # Éviter données invalides
        v1 = safe_float(photo1.get('votes', 0))
        v2 = safe_float(photo2.get('votes', 0))
        r1 = safe_float(photo1.get('ratio', 0))
        r2 = safe_float(photo2.get('ratio', 0))
        
        if v1 <= 0 or v2 <= 0 or r1 <= 0 or r2 <= 0:
            continue
        
        # Test des deux algorithmes
        patterns_pred, patterns_reason = algo_votes_ratio_patterns('photo1', photo1, 'photo2', photo2)
        bruno_pred, bruno_reason = algo_bruno_custom('photo1', photo1, 'photo2', photo2)
        
        # Convertir les prédictions en vrais IDs
        patterns_winner_id = photo1.get('id') if patterns_pred == 'photo1' else photo2.get('id')
        bruno_winner_id = photo1.get('id') if bruno_pred == 'photo1' else photo2.get('id')
        
        patterns_correct_case = patterns_winner_id == winner_id
        bruno_correct_case = bruno_winner_id == winner_id
        
        if patterns_correct_case:
            patterns_correct += 1
        if bruno_correct_case:
            bruno_correct += 1
        
        # Identifier les améliorations
        if patterns_correct_case and not bruno_correct_case:
            patterns_better.append({
                'key': key,
                'reason': patterns_reason,
                'winner_id': winner_id,
                'photo1': photo1,
                'photo2': photo2
            })
        elif bruno_correct_case and not patterns_correct_case:
            bruno_better.append({
                'key': key,
                'reason': bruno_reason,
                'winner_id': winner_id,
                'photo1': photo1,
                'photo2': photo2
            })
        
        total_cases += 1
    
    # Résultats
    patterns_accuracy = patterns_correct / total_cases * 100
    bruno_accuracy = bruno_correct / total_cases * 100
    improvement = patterns_accuracy - bruno_accuracy
    
    print(f"\n📈 === RÉSULTATS SUR {total_cases} CAS ===")
    print(f"🆕 Votes/Ratio Patterns: {patterns_accuracy:.1f}% ({patterns_correct}/{total_cases})")
    print(f"🏆 Bruno Custom V2:      {bruno_accuracy:.1f}% ({bruno_correct}/{total_cases})")
    print(f"📊 Différence:           {improvement:+.1f}%")
    
    print(f"\n🔄 === COMPARAISON DÉTAILLÉE ===")
    print(f"📈 Cas où Patterns meilleur: {len(patterns_better)}")
    print(f"📉 Cas où Bruno meilleur:    {len(bruno_better)}")
    print(f"🤝 Balance:                  {len(patterns_better) - len(bruno_better):+d}")
    
    # Exemples d'améliorations
    if patterns_better:
        print(f"\n🎉 === EXEMPLES OÙ PATTERNS MEILLEUR ===")
        for i, case in enumerate(patterns_better[:5]):
            winner_name = "Photo1" if case['winner_id'] == case['photo1']['id'] else "Photo2"
            p1 = case['photo1']
            p2 = case['photo2']
            
            votes_min = min(safe_float(p1.get('votes')), safe_float(p2.get('votes')))
            votes_max = max(safe_float(p1.get('votes')), safe_float(p2.get('votes')))
            votes_ratio = votes_min / votes_max if votes_max > 0 else 0
            
            print(f"   {i+1}. {winner_name} gagne (rapport votes: {votes_ratio:.3f})")
            print(f"      Photo1: {safe_float(p1.get('votes')):.0f}v, {safe_float(p1.get('ratio')):.3f}r")
            print(f"      Photo2: {safe_float(p2.get('votes')):.0f}v, {safe_float(p2.get('ratio')):.3f}r")
            print(f"      Stratégie: {case['reason']}")
    
    # Conclusion
    print(f"\n🎯 === CONCLUSION ===")
    
    if improvement > 3:
        print(f"🎉 SUCCÈS! Patterns améliore de {improvement:.1f}% vs Bruno Custom")
        print("   → L'approche rapports votes/ratio est prometteuse!")
    elif improvement > 0:
        print(f"📈 Amélioration légère de {improvement:.1f}%")
        print("   → Patterns apporte une valeur ajoutée")
    elif improvement >= -1:
        print(f"🤝 Performance équivalente ({improvement:+.1f}%)")
        print("   → Patterns est une alternative viable")
    else:
        print(f"📉 Bruno Custom reste meilleur de {-improvement:.1f}%")
        print("   → Patterns nécessite des ajustements")
    
    return {
        'patterns_accuracy': patterns_accuracy,
        'bruno_accuracy': bruno_accuracy,
        'improvement': improvement,
        'total_cases': total_cases
    }

if __name__ == "__main__":
    test_votes_ratio_patterns_performance()