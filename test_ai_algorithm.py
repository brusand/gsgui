#!/usr/bin/env python3
"""
Test complet de l'algorithme IA optimisé
Évalue sur l'ensemble des données historiques
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def ai_optimized_algorithm(photo1, photo2):
    """Algorithme IA optimisé avec toutes les règles découvertes"""
    
    first_ratio = safe_float(photo1.get('ratio', 0))
    second_ratio = safe_float(photo2.get('ratio', 0))
    first_votes = safe_float(photo1.get('votes', 0))
    second_votes = safe_float(photo2.get('votes', 0))
    first_rank = safe_float(photo1.get('rank', 999))
    second_rank = safe_float(photo2.get('rank', 999))
    
    first_id = photo1['id']
    second_id = photo2['id']
    
    # RÈGLE 1: Différence de rang importante (17.2% importance)
    rank_diff = abs(first_rank - second_rank)
    if rank_diff > 300:
        winner = first_id if first_rank < second_rank else second_id
        return winner, f"AI-Rang: {first_rank} vs {second_rank}"
    
    # RÈGLE 2: Différence de votes importante (16.3% importance)
    votes_diff = abs(first_votes - second_votes)
    if votes_diff > 500:
        winner = first_id if first_votes > second_votes else second_id
        return winner, f"AI-Votes: {first_votes} vs {second_votes}"
    
    # RÈGLE 3A: Pattern 1.3 vs 1.5 (56.8% succès pour 1.5)
    if (1.25 <= first_ratio <= 1.35) and (1.45 <= second_ratio <= 1.55):
        return second_id, f"AI-Pattern 1.3vs1.5: favoriser {second_ratio}"
    elif (1.45 <= first_ratio <= 1.55) and (1.25 <= second_ratio <= 1.35):
        return first_id, f"AI-Pattern 1.5vs1.3: favoriser {first_ratio}"
    
    # RÈGLE 3B: Pattern 1.5 vs 1.8 (88.9% succès pour 1.8)
    if (1.4 <= first_ratio <= 1.6) and (1.7 <= second_ratio <= 1.9):
        return second_id, f"AI-Pattern 1.5vs1.8: favoriser {second_ratio}"
    elif (1.7 <= first_ratio <= 1.9) and (1.4 <= second_ratio <= 1.6):
        return first_id, f"AI-Pattern 1.8vs1.5: favoriser {first_ratio}"
    
    # RÈGLE 4A: Deux ratios sous 1.0 (Photo2 gagne 85.7%)
    if first_ratio < 1.0 and second_ratio < 1.0:
        if abs(first_votes - second_votes) > 50:
            winner = first_id if first_votes > second_votes else second_id
            return winner, f"AI-Sous1.0 votes: {first_votes} vs {second_votes}"
        else:
            return second_id, f"AI-Sous1.0 pattern: Photo2 défaut (85.7%)"
    
    # RÈGLE 4B: Un ratio sous 1.0
    elif first_ratio < 1.0 and second_ratio >= 1.0:
        if first_votes > second_votes * 3:
            return first_id, f"AI-Sous1.0 exception: votes {first_votes} vs {second_votes}"
        else:
            return second_id, f"AI-Éviter sous1.0: {first_ratio} vs {second_ratio}"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        if second_votes > first_votes * 3:
            return second_id, f"AI-Sous1.0 exception: votes {second_votes} vs {first_votes}"
        else:
            return first_id, f"AI-Éviter sous1.0: {second_ratio} vs {first_ratio}"
    
    # RÈGLE 5: Zone danger 1.5
    first_danger = abs(first_ratio - 1.5) < 0.1
    second_danger = abs(second_ratio - 1.5) < 0.1
    if first_danger and not second_danger:
        return second_id, f"AI-Éviter danger 1.5: {first_ratio}"
    elif second_danger and not first_danger:
        return first_id, f"AI-Éviter danger 1.5: {second_ratio}"
    
    # Fallback: ratio plus faible
    winner = first_id if first_ratio <= second_ratio else second_id
    return winner, f"AI-Fallback ratio: {first_ratio} vs {second_ratio}"

def bruno_custom_algorithm(photo1, photo2):
    """Algorithme Bruno Custom pour comparaison"""
    first_ratio = safe_float(photo1.get('ratio', 0))
    second_ratio = safe_float(photo2.get('ratio', 0))
    first_votes = safe_float(photo1.get('votes', 0))
    second_votes = safe_float(photo2.get('votes', 0))
    
    first_id = photo1['id']
    second_id = photo2['id']
    
    # RÈGLE 1: Éviter ratio < 1.0
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, "Bruno-Éviter <1.0"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, "Bruno-Éviter <1.0"
    
    # RÈGLE 2: Sweet spot 1.15-1.30
    first_sweet = 1.15 <= first_ratio <= 1.30
    second_sweet = 1.15 <= second_ratio <= 1.30
    
    if first_sweet and not second_sweet and first_votes >= 50:
        return first_id, "Bruno-Sweet spot"
    elif second_sweet and not first_sweet and second_votes >= 50:
        return second_id, "Bruno-Sweet spot"
    
    # RÈGLE 3: Zone danger 1.5
    first_danger = abs(first_ratio - 1.5) < 0.1
    second_danger = abs(second_ratio - 1.5) < 0.1
    
    if first_danger and not second_danger:
        return second_id, "Bruno-Éviter danger 1.5"
    elif second_danger and not first_danger:
        return first_id, "Bruno-Éviter danger 1.5"
    
    # Fallback
    return first_id if first_ratio <= second_ratio else second_id, "Bruno-Fallback"

def test_algorithms():
    """Test complet des algorithmes"""
    print("🚀 === TEST COMPLET ALGORITHMES ===")
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique trouvé")
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
            'winner_id': winner_id
        })
    
    print(f"📊 Test sur {len(test_cases)} comparaisons valides")
    
    # Test des algorithmes
    algorithms = {
        'AI Optimisé': ai_optimized_algorithm,
        'Bruno Custom': bruno_custom_algorithm
    }
    
    results = {}
    
    for algo_name, algo_func in algorithms.items():
        correct = 0
        total = len(test_cases)
        details = {'rules_used': {}}
        
        for test_case in test_cases:
            try:
                predicted_winner, reason = algo_func(test_case['photo1'], test_case['photo2'])
                
                if predicted_winner == test_case['winner_id']:
                    correct += 1
                
                # Compter l'utilisation des règles
                rule_type = reason.split(':')[0] if ':' in reason else reason
                details['rules_used'][rule_type] = details['rules_used'].get(rule_type, 0) + 1
                
            except Exception as e:
                print(f"⚠️ Erreur {algo_name}: {e}")
                continue
        
        accuracy = correct / total * 100 if total > 0 else 0
        results[algo_name] = {
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'details': details
        }
    
    # Afficher les résultats
    print("\\n📈 === RÉSULTATS ===")
    for algo_name, result in results.items():
        print(f"\\n🤖 {algo_name}:")
        print(f"   Précision: {result['accuracy']:.1f}% ({result['correct']}/{result['total']})")
        
        if 'rules_used' in result['details']:
            print("   Règles utilisées:")
            for rule, count in sorted(result['details']['rules_used'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {rule}: {count} fois")
    
    # Comparaison
    if 'AI Optimisé' in results and 'Bruno Custom' in results:
        ai_acc = results['AI Optimisé']['accuracy']
        bruno_acc = results['Bruno Custom']['accuracy']
        improvement = ai_acc - bruno_acc
        
        print(f"\\n🎯 === COMPARAISON ===")
        print(f"AI Optimisé: {ai_acc:.1f}%")
        print(f"Bruno Custom: {bruno_acc:.1f}%")
        print(f"Amélioration: {improvement:+.1f}%")
        
        if improvement > 0:
            print("🎉 L'IA bat Bruno Custom!")
        elif improvement == 0:
            print("🤝 Égalité parfaite")
        else:
            print("📊 Bruno Custom résiste")

if __name__ == "__main__":
    test_algorithms()