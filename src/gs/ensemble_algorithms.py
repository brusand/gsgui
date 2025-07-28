#!/usr/bin/env python3
"""
Ensemble d'algorithmes pour la sélection de photos avec vote majoritaire
Implémente: bruno_custom, hybrid, votes_ratio + système de vote majoritaire
"""

import sys
import os
import random
import hashlib
from collections import Counter

# Importer l'algorithme bruno_custom existant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bruno_custom_refined import bruno_custom_refined

def safe_float(val, default=0.0):
    """Conversion sécurisée vers float"""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Conversion sécurisée vers int"""
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default

def hybrid_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme Hybrid - Approche équilibrée votes/ratio/rang
    Philosophie: Pondération équilibrée avec scoring normalisé
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # === RÈGLE 1: ÉVITER RATIO < 1.0 (priorité absolue) ===
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, f"hybrid: éviter <1.0 ({first_ratio} vs {second_ratio})"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, f"hybrid: éviter <1.0 ({second_ratio} vs {first_ratio})"
    elif first_ratio < 1.0 and second_ratio < 1.0:
        # Si les deux < 1.0, prendre le moins pire avec votes comme tie-breaker
        if first_ratio > second_ratio or (first_ratio == second_ratio and first_votes > second_votes):
            return first_id, f"hybrid: moins pire <1.0 ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"hybrid: moins pire <1.0 ({second_ratio} vs {first_ratio})"

    # === RÈGLE 2: SCORING PONDÉRÉ ===
    # Normaliser les métriques pour scoring équitable
    
    # Score ratio (30% du poids)
    ratio_score_1 = min(first_ratio / 2.0, 1.0)  # Normaliser sur 2.0 max
    ratio_score_2 = min(second_ratio / 2.0, 1.0)
    
    # Score votes (40% du poids) - normalisation relative
    total_votes = first_votes + second_votes
    if total_votes > 0:
        votes_score_1 = first_votes / total_votes
        votes_score_2 = second_votes / total_votes
    else:
        votes_score_1 = votes_score_2 = 0.5
    
    # Score rang (30% du poids) - inversé car rang faible = meilleur
    max_rank = max(first_rank, second_rank, 1)
    rank_score_1 = 1.0 - (first_rank / max_rank)
    rank_score_2 = 1.0 - (second_rank / max_rank)
    
    # Score final pondéré
    score_1 = (0.3 * ratio_score_1) + (0.4 * votes_score_1) + (0.3 * rank_score_1)
    score_2 = (0.3 * ratio_score_2) + (0.4 * votes_score_2) + (0.3 * rank_score_2)
    
    if score_1 > score_2:
        return first_id, f"hybrid: score pondéré ({score_1:.3f} vs {score_2:.3f})"
    else:
        return second_id, f"hybrid: score pondéré ({score_2:.3f} vs {score_1:.3f})"

def votes_ratio_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme Votes-Ratio - Priorité aux votes avec ratio comme arbitre
    Philosophie: Les votes reflètent la popularité réelle, ratio pour départager
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(first_data.get('rank', 999))

    # === RÈGLE 1: ÉVITER RATIO < 1.0 ===
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, f"votes_ratio: éviter <1.0 ({first_ratio} vs {second_ratio})"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, f"votes_ratio: éviter <1.0 ({second_ratio} vs {first_ratio})"

    # === RÈGLE 2: PRIORITÉ AUX VOTES ===
    votes_diff = abs(first_votes - second_votes)
    votes_threshold = 50  # Seuil de différence significative
    
    if votes_diff > votes_threshold:
        if first_votes > second_votes:
            return first_id, f"votes_ratio: votes prioritaires ({first_votes} vs {second_votes})"
        else:
            return second_id, f"votes_ratio: votes prioritaires ({second_votes} vs {first_votes})"
    
    # === RÈGLE 3: RATIO COMME TIE-BREAKER ===
    ratio_diff = abs(first_ratio - second_ratio)
    if ratio_diff > 0.1:
        if first_ratio > second_ratio:
            return first_id, f"votes_ratio: ratio tie-breaker ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"votes_ratio: ratio tie-breaker ({second_ratio} vs {first_ratio})"
    
    # === RÈGLE 4: RANG FINAL ===
    if first_rank < second_rank:
        return first_id, f"votes_ratio: rang final ({first_rank} vs {second_rank})"
    else:
        return second_id, f"votes_ratio: rang final ({second_rank} vs {first_rank})"

def ratio_low_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme Ratio-Low - Spécialisé sur les ratios faibles mais stables
    Philosophie: Préfère la stabilité et consistance plutôt que les pics
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # === RÈGLE 1: ÉVITER RATIO < 1.0 ===
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, f"ratio_low: éviter <1.0 ({first_ratio} vs {second_ratio})"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, f"ratio_low: éviter <1.0 ({second_ratio} vs {first_ratio})"

    # === RÈGLE 2: ZONE DE CONFORT 1.0-1.6 (ratios stables) ===
    # Préférer les ratios dans la zone stable plutôt que les pics élevés
    stable_zone_min, stable_zone_max = 1.0, 1.6
    
    first_in_stable = stable_zone_min <= first_ratio <= stable_zone_max
    second_in_stable = stable_zone_min <= second_ratio <= stable_zone_max
    
    if first_in_stable and not second_in_stable:
        return first_id, f"ratio_low: zone stable ({first_ratio} vs {second_ratio})"
    elif second_in_stable and not first_in_stable:
        return second_id, f"ratio_low: zone stable ({second_ratio} vs {first_ratio})"
    
    # === RÈGLE 3: DANS LA ZONE STABLE, PRIVILÉGIER VOTES + RANG ===
    if first_in_stable and second_in_stable:
        # Dans la zone stable, votes sont prioritaires
        votes_diff = abs(first_votes - second_votes)
        if votes_diff > 100:
            if first_votes > second_votes:
                return first_id, f"ratio_low: votes en zone stable ({first_votes} vs {second_votes})"
            else:
                return second_id, f"ratio_low: votes en zone stable ({second_votes} vs {first_votes})"
        
        # Si votes similaires, privilégier le meilleur rang
        if first_rank < second_rank:
            return first_id, f"ratio_low: rang en zone stable ({first_rank} vs {second_rank})"
        else:
            return second_id, f"ratio_low: rang en zone stable ({second_rank} vs {first_rank})"
    
    # === RÈGLE 4: HORS ZONE STABLE, ÉVITER LES RATIOS TROP ÉLEVÉS ===
    # Au-dessus de 1.6, préférer le ratio le plus modéré
    if first_ratio > stable_zone_max and second_ratio > stable_zone_max:
        # Les deux sont trop élevés, prendre le plus modéré
        if first_ratio < second_ratio:
            return first_id, f"ratio_low: plus modéré ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"ratio_low: plus modéré ({second_ratio} vs {first_ratio})"
    
    # === RÈGLE 5: FALLBACK CONSERVATEUR ===
    # En cas de doute, privilégier votes + rang
    vote_rank_score_1 = first_votes + (1000 - first_rank)
    vote_rank_score_2 = second_votes + (1000 - second_rank)
    
    if vote_rank_score_1 > vote_rank_score_2:
        return first_id, f"ratio_low: score conservateur ({vote_rank_score_1} vs {vote_rank_score_2})"
    else:
        return second_id, f"ratio_low: score conservateur ({vote_rank_score_2} vs {vote_rank_score_1})"

def votes_high_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme Votes-High - Priorité absolue aux votes élevés
    Philosophie: Les votes reflètent la vraie popularité, tout le reste est secondaire
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    first_rank = safe_float(first_data.get('rank', 999))
    second_rank = safe_float(second_data.get('rank', 999))

    # === RÈGLE 1: ÉVITER RATIO < 1.0 SEULEMENT SI TRÈS MAUVAIS ===
    # Plus tolérant que les autres algos si les votes compensent
    if first_ratio < 0.8 and second_ratio >= 1.0:
        return second_id, f"votes_high: éviter très mauvais ratio ({first_ratio} vs {second_ratio})"
    elif second_ratio < 0.8 and first_ratio >= 1.0:
        return first_id, f"votes_high: éviter très mauvais ratio ({second_ratio} vs {first_ratio})"

    # === RÈGLE 2: PRIORITÉ ABSOLUE AUX VOTES ===
    # Seuil très bas pour privilégier les votes
    votes_threshold = 20  # Beaucoup plus bas que les autres algos
    votes_diff = abs(first_votes - second_votes)
    
    if votes_diff > votes_threshold:
        if first_votes > second_votes:
            return first_id, f"votes_high: votes prioritaires ({first_votes} vs {second_votes})"
        else:
            return second_id, f"votes_high: votes prioritaires ({second_votes} vs {first_votes})"
    
    # === RÈGLE 3: BONUS POUR VOTES TRÈS ÉLEVÉS ===
    # Donner un bonus supplémentaire aux photos avec beaucoup de votes
    high_votes_threshold = 500
    
    first_high_votes = first_votes >= high_votes_threshold
    second_high_votes = second_votes >= high_votes_threshold
    
    if first_high_votes and not second_high_votes:
        return first_id, f"votes_high: votes très élevés ({first_votes} vs {second_votes})"
    elif second_high_votes and not first_high_votes:
        return second_id, f"votes_high: votes très élevés ({second_votes} vs {first_votes})"
    
    # === RÈGLE 4: RATIO COMME TIE-BREAKER MINEUR ===
    # Seulement pour départager si votes vraiment similaires
    ratio_diff = abs(first_ratio - second_ratio)
    if ratio_diff > 0.3:  # Seuil élevé
        if first_ratio > second_ratio:
            return first_id, f"votes_high: ratio tie-breaker ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"votes_high: ratio tie-breaker ({second_ratio} vs {first_ratio})"
    
    # === RÈGLE 5: VOTES ENCORE ET TOUJOURS ===
    # En dernier recours, toujours revenir aux votes
    if first_votes >= second_votes:
        return first_id, f"votes_high: votes fallback ({first_votes} vs {second_votes})"
    else:
        return second_id, f"votes_high: votes fallback ({second_votes} vs {first_votes})"

def random_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme Random - Choix aléatoire avec seed basé sur les IDs
    Philosophie: Baseline aléatoire pour tester la robustesse des autres algorithmes
    Utilise un seed déterministe basé sur les IDs pour la reproductibilité
    """
    first_ratio = safe_float(first_data.get('ratio', 0))
    second_ratio = safe_float(second_data.get('ratio', 0))
    first_votes = safe_float(first_data.get('votes', 0))
    second_votes = safe_float(second_data.get('votes', 0))
    
    # === RÈGLE 1: ÉVITER RATIO < 0.5 (minimum de bon sens) ===
    # Même l'aléatoire évite les cas vraiment catastrophiques
    if first_ratio < 0.5 and second_ratio >= 1.0:
        return second_id, f"random: éviter catastrophique ({first_ratio} vs {second_ratio})"
    elif second_ratio < 0.5 and first_ratio >= 1.0:
        return first_id, f"random: éviter catastrophique ({second_ratio} vs {first_ratio})"
    
    # === RÈGLE 2: CHOIX ALÉATOIRE AVEC SEED DÉTERMINISTE ===
    # Créer un seed reproductible basé sur les IDs des photos
    seed_string = f"{first_id}_{second_id}_{first_votes}_{second_votes}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
    seed_value = int(seed_hash[:8], 16)  # Prendre les 8 premiers caractères hex
    
    # Initialiser le générateur avec ce seed
    rng = random.Random(seed_value)
    
    # === RÈGLE 3: CHOIX ALÉATOIRE PONDÉRÉ (pas complètement uniforme) ===
    # Donner une légère pondération basée sur les données pour ne pas être complètement aveugle
    
    # Scores simples pour pondération
    score1 = first_votes + (first_ratio * 100)
    score2 = second_votes + (second_ratio * 100)
    total_score = score1 + score2
    
    if total_score > 0:
        # Probabilité proportionnelle au score
        prob1 = score1 / total_score
        choice_random = rng.random()
        
        if choice_random < prob1:
            return first_id, f"random: choix pondéré aléatoire (p={prob1:.3f}, r={choice_random:.3f})"
        else:
            return second_id, f"random: choix pondéré aléatoire (p={1-prob1:.3f}, r={choice_random:.3f})"
    else:
        # Fallback: choix 50/50 pur
        choice_random = rng.random()
        if choice_random < 0.5:
            return first_id, f"random: choix 50/50 (r={choice_random:.3f})"
        else:
            return second_id, f"random: choix 50/50 (r={choice_random:.3f})"

def ensemble_vote(first_id, first_data, second_id, second_data, algorithms=['bruno_custom', 'hybrid', 'votes_ratio']):
    """
    Système de vote majoritaire sur un ensemble d'algorithmes
    Retourne: (majority_choice, individual_choices, vote_details)
    """
    
    individual_choices = {}
    vote_details = {}
    
    # Appliquer chaque algorithme
    for algo in algorithms:
        try:
            if algo == 'bruno_custom':
                choice, ratio1, ratio2, votes, reason = bruno_custom_refined(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            elif algo == 'hybrid':
                choice, reason = hybrid_algorithm(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            elif algo == 'votes_ratio':
                choice, reason = votes_ratio_algorithm(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            elif algo == 'ratio_low':
                choice, reason = ratio_low_algorithm(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            elif algo == 'votes_high':
                choice, reason = votes_high_algorithm(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            elif algo == 'random':
                choice, reason = random_algorithm(first_id, first_data, second_id, second_data)
                individual_choices[algo] = choice
                vote_details[algo] = reason
                
            else:
                # Algorithme non supporté
                individual_choices[algo] = None
                vote_details[algo] = f"Algorithme non supporté: {algo}"
                
        except Exception as e:
            individual_choices[algo] = None
            vote_details[algo] = f"Erreur: {e}"
    
    # Vote majoritaire
    valid_choices = [choice for choice in individual_choices.values() if choice is not None]
    
    if len(valid_choices) == 0:
        majority_choice = None
        majority_reason = "Aucun algorithme valide"
    else:
        vote_count = Counter(valid_choices)
        majority_choice = vote_count.most_common(1)[0][0]
        majority_count = vote_count[majority_choice]
        majority_reason = f"Vote majoritaire: {majority_count}/{len(valid_choices)} ({', '.join([f'{algo}={choice}' for algo, choice in individual_choices.items() if choice is not None])})"
    
    return majority_choice, individual_choices, vote_details, majority_reason

def test_ensemble_algorithms():
    """Test des algorithmes d'ensemble"""
    print("🧪 === TEST NOUVEAUX ALGORITHMES ===")
    
    # Cas de test pour les nouveaux algorithmes
    test_cases = [
        {
            'name': 'Cas votes très élevés vs ratio élevé',
            'photo1': {'ratio': 1.2, 'votes': 800, 'rank': 100},
            'photo2': {'ratio': 1.8, 'votes': 200, 'rank': 300},
        },
        {
            'name': 'Cas zone stable vs pic ratio',
            'photo1': {'ratio': 1.4, 'votes': 400, 'rank': 150},
            'photo2': {'ratio': 2.0, 'votes': 350, 'rank': 180},
        },
        {
            'name': 'Cas ratio modéré vs votes massifs',
            'photo1': {'ratio': 0.9, 'votes': 1000, 'rank': 50},
            'photo2': {'ratio': 1.6, 'votes': 150, 'rank': 200},
        },
        {
            'name': 'Cas équilibré dans zone stable',
            'photo1': {'ratio': 1.3, 'votes': 300, 'rank': 120},
            'photo2': {'ratio': 1.5, 'votes': 280, 'rank': 140},
        },
        {
            'name': 'Test algorithme random',
            'photo1': {'ratio': 1.4, 'votes': 350, 'rank': 100},
            'photo2': {'ratio': 1.6, 'votes': 400, 'rank': 150},
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   Photo1: r={case['photo1']['ratio']}, v={case['photo1']['votes']}, rk={case['photo1']['rank']}")
        print(f"   Photo2: r={case['photo2']['ratio']}, v={case['photo2']['votes']}, rk={case['photo2']['rank']}")
        
        # Tester les nouveaux algorithmes individuellement
        print(f"   🔍 Choix individuels:")
        
        # Tester chaque nouvel algorithme
        choice1, reason1 = hybrid_algorithm('photo1', case['photo1'], 'photo2', case['photo2'])
        print(f"      hybrid: {choice1} - {reason1}")
        
        choice2, reason2 = ratio_low_algorithm('photo1', case['photo1'], 'photo2', case['photo2'])
        print(f"      ratio_low: {choice2} - {reason2}")
        
        choice3, reason3 = votes_high_algorithm('photo1', case['photo1'], 'photo2', case['photo2'])
        print(f"      votes_high: {choice3} - {reason3}")
        
        choice4, reason4 = random_algorithm('photo1', case['photo1'], 'photo2', case['photo2'])
        print(f"      random: {choice4} - {reason4}")
        
        # Tester l'ensemble hybrid, votes_high, random
        majority_choice, individual_choices, vote_details, majority_reason = ensemble_vote(
            'photo1', case['photo1'], 'photo2', case['photo2'], ['hybrid', 'votes_high', 'random']
        )
        
        print(f"   📊 Choix individuels:")
        for algo, choice in individual_choices.items():
            print(f"      {algo}: {choice}")
        
        print(f"   🗳️ Choix majoritaire: {majority_choice}")
        print(f"   📝 Raison: {majority_reason}")

if __name__ == "__main__":
    test_ensemble_algorithms()