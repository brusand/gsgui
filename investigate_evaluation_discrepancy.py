#!/usr/bin/env python3
"""
Investigation des écarts entre notre test et l'évaluation officielle
Analyse pourquoi AI Optimized performe différemment
"""

from configobj import ConfigObj
import random

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def ai_optimized_algorithm(photo1, photo2):
    """Version exacte de notre algorithme IA"""
    first_ratio = safe_float(photo1.get('ratio', 0))
    second_ratio = safe_float(photo2.get('ratio', 0))
    first_votes = safe_float(photo1.get('votes', 0))
    second_votes = safe_float(photo2.get('votes', 0))
    first_rank = safe_float(photo1.get('rank', 999))
    second_rank = safe_float(photo1.get('rank', 999))
    
    first_id = photo1['id']
    second_id = photo2['id']
    
    # RÈGLE 1: Différence de rang > 300
    rank_diff = abs(first_rank - second_rank)
    if rank_diff > 300:
        winner = first_id if first_rank < second_rank else second_id
        return winner, f"AI-Rang: {first_rank} vs {second_rank}"
    
    # RÈGLE 2: Différence de votes > 500
    votes_diff = abs(first_votes - second_votes)
    if votes_diff > 500:
        winner = first_id if first_votes > second_votes else second_id
        return winner, f"AI-Votes: {first_votes} vs {second_votes}"
    
    # RÈGLE 3A: Pattern 1.3 vs 1.5
    if (1.25 <= first_ratio <= 1.35) and (1.45 <= second_ratio <= 1.55):
        return second_id, f"AI-Pattern 1.3vs1.5"
    elif (1.45 <= first_ratio <= 1.55) and (1.25 <= second_ratio <= 1.35):
        return first_id, f"AI-Pattern 1.5vs1.3"
    
    # RÈGLE 3B: Pattern 1.5 vs 1.8
    if (1.4 <= first_ratio <= 1.6) and (1.7 <= second_ratio <= 1.9):
        return second_id, f"AI-Pattern 1.5vs1.8"
    elif (1.7 <= first_ratio <= 1.9) and (1.4 <= second_ratio <= 1.6):
        return first_id, f"AI-Pattern 1.8vs1.5"
    
    # RÈGLE 4A: Deux ratios < 1.0
    if first_ratio < 1.0 and second_ratio < 1.0:
        if abs(first_votes - second_votes) > 50:
            winner = first_id if first_votes > second_votes else second_id
            return winner, f"AI-Sous1.0 votes"
        else:
            return second_id, f"AI-Sous1.0 pattern (85.7%)"
    
    # RÈGLE 4B: Un ratio < 1.0
    elif first_ratio < 1.0 and second_ratio >= 1.0:
        if first_votes > second_votes * 3:
            return first_id, f"AI-Sous1.0 exception"
        else:
            return second_id, f"AI-Éviter sous1.0"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        if second_votes > first_votes * 3:
            return second_id, f"AI-Sous1.0 exception"
        else:
            return first_id, f"AI-Éviter sous1.0"
    
    # RÈGLE 5: Zone danger 1.5
    first_danger = abs(first_ratio - 1.5) < 0.1
    second_danger = abs(second_ratio - 1.5) < 0.1
    if first_danger and not second_danger:
        return second_id, f"AI-Éviter danger 1.5"
    elif second_danger and not first_danger:
        return first_id, f"AI-Éviter danger 1.5"
    
    # Fallback
    winner = first_id if first_ratio <= second_ratio else second_id
    return winner, f"AI-Fallback ratio"

def bruno_custom_algorithm(photo1, photo2):
    """Version simplifiée Bruno Custom pour comparaison"""
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

def simulate_official_evaluation():
    """Simule l'évaluation officielle pour comprendre l'écart"""
    print("🔍 === INVESTIGATION ÉVALUATION OFFICIELLE ===")
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    # Préparer toutes les données valides
    all_cases = []
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
            
        all_cases.append({
            'photo1': photo1,
            'photo2': photo2,
            'winner_id': winner_id,
            'key': key
        })
    
    print(f"📊 Total de cas valides: {len(all_cases)}")
    
    # Test sur différentes tailles d'échantillons
    sample_sizes = [50, 100, 106, 200, len(all_cases)]
    
    for sample_size in sample_sizes:
        if sample_size > len(all_cases):
            continue
            
        print(f"\\n🎯 === ÉCHANTILLON DE {sample_size} CAS ===")
        
        # Plusieurs échantillons aléatoires pour voir la variance
        ai_accuracies = []
        bruno_accuracies = []
        
        for trial in range(10):  # 10 tirages aléatoires
            # Échantillonner aléatoirement
            if sample_size == len(all_cases):
                sample = all_cases
            else:
                sample = random.sample(all_cases, sample_size)
            
            ai_correct = 0
            bruno_correct = 0
            
            for case in sample:
                # Test AI
                ai_pred, _ = ai_optimized_algorithm(case['photo1'], case['photo2'])
                if ai_pred == case['winner_id']:
                    ai_correct += 1
                
                # Test Bruno
                bruno_pred, _ = bruno_custom_algorithm(case['photo1'], case['photo2'])
                if bruno_pred == case['winner_id']:
                    bruno_correct += 1
            
            ai_acc = ai_correct / len(sample) * 100
            bruno_acc = bruno_correct / len(sample) * 100
            
            ai_accuracies.append(ai_acc)
            bruno_accuracies.append(bruno_acc)
        
        # Statistiques
        ai_mean = sum(ai_accuracies) / len(ai_accuracies)
        bruno_mean = sum(bruno_accuracies) / len(bruno_accuracies)
        ai_std = (sum((x - ai_mean) ** 2 for x in ai_accuracies) / len(ai_accuracies)) ** 0.5
        bruno_std = (sum((x - bruno_mean) ** 2 for x in bruno_accuracies) / len(bruno_accuracies)) ** 0.5
        
        print(f"   AI Optimized: {ai_mean:.1f}% ± {ai_std:.1f}% (range: {min(ai_accuracies):.1f}%-{max(ai_accuracies):.1f}%)")
        print(f"   Bruno Custom: {bruno_mean:.1f}% ± {bruno_std:.1f}% (range: {min(bruno_accuracies):.1f}%-{max(bruno_accuracies):.1f}%)")
        print(f"   Différence: {ai_mean - bruno_mean:+.1f}%")
        
        # Marquer si on retrouve les résultats officiels
        if sample_size == 106:
            print(f"   📊 Résultats officiels attendus: AI ~55.7%, Bruno ~66.0%")
            if abs(ai_mean - 55.7) < 5 and abs(bruno_mean - 66.0) < 5:
                print("   ✅ Cohérent avec évaluation officielle!")
            else:
                print("   ⚠️ Écart avec évaluation officielle")

def analyze_differences():
    """Analyse les cas où AI et Bruno diffèrent"""
    print("\\n🔍 === ANALYSE DES DIFFÉRENCES AI vs BRUNO ===")
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    # Cas où les algorithmes diffèrent
    differences = []
    
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
        
        ai_pred, ai_reason = ai_optimized_algorithm(photo1, photo2)
        bruno_pred, bruno_reason = bruno_custom_algorithm(photo1, photo2)
        
        if ai_pred != bruno_pred:
            ai_correct = ai_pred == winner_id
            bruno_correct = bruno_pred == winner_id
            
            differences.append({
                'photo1': photo1,
                'photo2': photo2,
                'winner_id': winner_id,
                'ai_pred': ai_pred,
                'bruno_pred': bruno_pred,
                'ai_reason': ai_reason,
                'bruno_reason': bruno_reason,
                'ai_correct': ai_correct,
                'bruno_correct': bruno_correct
            })
    
    print(f"📊 Cas où AI et Bruno diffèrent: {len(differences)}")
    
    # Analyser les patterns de différence
    ai_wins = sum(1 for d in differences if d['ai_correct'] and not d['bruno_correct'])
    bruno_wins = sum(1 for d in differences if d['bruno_correct'] and not d['ai_correct'])
    both_wrong = sum(1 for d in differences if not d['ai_correct'] and not d['bruno_correct'])
    both_right = sum(1 for d in differences if d['ai_correct'] and d['bruno_correct'])
    
    print(f"   🤖 AI gagne seul: {ai_wins}")
    print(f"   👑 Bruno gagne seul: {bruno_wins}")
    print(f"   ❌ Les deux se trompent: {both_wrong}")
    print(f"   ✅ Les deux ont raison: {both_right}")
    
    # Exemples de cas problématiques pour l'IA
    ai_fails = [d for d in differences if not d['ai_correct'] and d['bruno_correct']][:5]
    
    if ai_fails:
        print("\\n🚨 Exemples où Bruno bat AI:")
        for i, case in enumerate(ai_fails):
            p1 = case['photo1']
            p2 = case['photo2']
            print(f"   {i+1}. Photo1(r:{safe_float(p1.get('ratio')):.2f}, v:{safe_float(p1.get('votes')):.0f}) vs Photo2(r:{safe_float(p2.get('ratio')):.2f}, v:{safe_float(p2.get('votes')):.0f})")
            print(f"      Winner: {'Photo1' if case['winner_id'] == p1['id'] else 'Photo2'}")
            print(f"      AI: {'Photo1' if case['ai_pred'] == p1['id'] else 'Photo2'} ({case['ai_reason']})")
            print(f"      Bruno: {'Photo1' if case['bruno_pred'] == p1['id'] else 'Photo2'} ({case['bruno_reason']})")
            print()

if __name__ == "__main__":
    random.seed(42)  # Pour reproductibilité
    simulate_official_evaluation()
    analyze_differences()