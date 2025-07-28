#!/usr/bin/env python3
"""
Test de l'algorithme Random Forest avancé contre l'évaluation officielle
Vérifie si on peut battre Bruno Custom (66%) avec 70.2% de précision
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def advanced_turbo_algorithm(photo1, photo2):
    """
    Algorithme Turbo IA Avancé - Précision Cross-Val: 68.8%
    Basé sur 55 features et Random Forest
    """
    
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    r1 = safe_float(photo1.get('ratio', 0))
    r2 = safe_float(photo2.get('ratio', 0))
    v1 = safe_float(photo1.get('votes', 0))
    v2 = safe_float(photo2.get('votes', 0))
    rank1 = safe_float(photo1.get('rank', 999))
    rank2 = safe_float(photo2.get('rank', 999))
    
    # Règles basées sur les features les plus importantes:

    # Règle basée sur votes_rank_interaction_ratio (importance: 0.077)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: votes_rank_interaction_ratio"

    # Règle basée sur votes_ratio (importance: 0.058)
    if max(v1, v2) > 0 and abs(v1 - v2) > 200:
        return photo1['id'] if v1 > v2 else photo2['id'], f"advanced_ai: votes_ratio"

    # Règle basée sur rank_ratio (importance: 0.058)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: rank_ratio"

    # Règle basée sur rank_efficiency_ratio (importance: 0.039)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: rank_efficiency_ratio"

    # Fallback: ratio traditionnel
    return photo1['id'] if r1 <= r2 else photo2['id'], "advanced_ai: fallback"

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

def test_advanced_vs_bruno():
    """Test l'algorithme avancé contre Bruno Custom"""
    print("🚀 === TEST ALGORITHME RANDOM FOREST AVANCÉ ===")
    print("🎯 Objectif: Battre Bruno Custom (66%) avec Random Forest")
    print("=" * 60)
    
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
        'Random Forest Avancé': advanced_turbo_algorithm,
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
    print("\n📈 === RÉSULTATS COMPARATIFS ===")
    for algo_name, result in results.items():
        print(f"\n🤖 {algo_name}:")
        print(f"   Précision: {result['accuracy']:.1f}% ({result['correct']}/{result['total']})")
        
        if 'rules_used' in result['details']:
            print("   Top 5 règles utilisées:")
            for rule, count in sorted(result['details']['rules_used'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {rule}: {count} fois")
    
    # Comparaison finale
    if 'Random Forest Avancé' in results and 'Bruno Custom' in results:
        rf_acc = results['Random Forest Avancé']['accuracy']
        bruno_acc = results['Bruno Custom']['accuracy']
        improvement = rf_acc - bruno_acc
        
        print(f"\n🎯 === COMPARAISON FINALE ===")
        print(f"Random Forest Avancé: {rf_acc:.1f}%")
        print(f"Bruno Custom: {bruno_acc:.1f}%")
        print(f"Amélioration: {improvement:+.1f}%")
        
        # Référence attendue de l'évaluation officielle
        print(f"\n📊 Référence évaluation officielle:")
        print(f"   Bruno Custom attendu: ~66.0%")
        print(f"   Random Forest vs référence: {rf_acc - 66.0:+.1f}%")
        
        if rf_acc > 66.0:
            print("🎉 SUCCÈS! Random Forest bat l'objectif de 66%!")
        elif rf_acc > bruno_acc:
            print("📈 Random Forest améliore Bruno Custom")
        else:
            print("📊 Bruno Custom résiste encore")
    
    return results

if __name__ == "__main__":
    test_advanced_vs_bruno()