#!/usr/bin/env python3
"""
Algorithme adaptatif basé sur le temps restant
S'adapte selon le temps restant du challenge pour optimiser les performances
"""

import re
import sys
import os

# Importer les algorithmes existants
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from position_aware_algorithm import position_aware_algorithm
from bruno_custom_refined import bruno_custom_refined

def safe_float(val, default=0.0):
    """Conversion sécurisée en float"""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def parse_time_left_hours(time_str):
    """Parse une chaîne 'XD YH ZM WS' en heures totales"""
    if not time_str:
        return 24.0  # Défaut si pas de temps
    
    try:
        # Pattern pour capturer jours, heures, minutes, secondes
        pattern = r'(?:(\d+)D\s*)?(?:(\d+)H\s*)?(?:(\d+)M\s*)?(?:(\d+)S\s*)?'
        match = re.match(pattern, str(time_str).strip())
        
        if not match:
            return 24.0
        
        days = int(match.group(1)) if match.group(1) else 0
        hours = int(match.group(2)) if match.group(2) else 0
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0
        
        total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
        return total_hours
        
    except Exception:
        return 24.0

class AdaptiveTimeAlgorithm:
    """Algorithme qui s'adapte selon le temps restant du challenge"""
    
    def __init__(self):
        # Seuils de temps pour différentes stratégies (en heures)
        self.time_thresholds = {
            'urgent': 1.0,      # ≤1h - Mode urgence
            'short': 6.0,       # 1-6h - Court terme
            'medium': 24.0,     # 6-24h - Moyen terme  
            'long': 48.0        # >24h - Long terme
        }
        
        # Facteurs d'ajustement par période
        self.time_factors = {
            'urgent': {
                'votes_weight': 1.3,    # Votes plus importants en fin
                'ratio_weight': 0.9,    # Ratio moins fiable
                'rank_weight': 1.2,     # Rang important (positions figées)
                'position_bonus': 1.1   # Léger bonus position
            },
            'short': {
                'votes_weight': 1.2,
                'ratio_weight': 1.0,
                'rank_weight': 1.1,
                'position_bonus': 1.05
            },
            'medium': {
                'votes_weight': 1.0,
                'ratio_weight': 1.1,
                'rank_weight': 1.0,
                'position_bonus': 1.0
            },
            'long': {
                'votes_weight': 0.9,    # Votes moins fiables à long terme
                'ratio_weight': 1.2,    # Ratio plus prédictif
                'rank_weight': 0.8,     # Rang peut encore bouger
                'position_bonus': 0.95
            }
        }
    
    def get_time_category(self, hours):
        """Détermine la catégorie temporelle"""
        if hours <= self.time_thresholds['urgent']:
            return 'urgent'
        elif hours <= self.time_thresholds['short']:
            return 'short'
        elif hours <= self.time_thresholds['medium']:
            return 'medium'
        else:
            return 'long'
    
    def calculate_time_adjusted_score(self, photo_id, photo_data, position, time_category):
        """Calcule un score ajusté selon le temps restant"""
        ratio = safe_float(photo_data.get('ratio', 0))
        votes = safe_float(photo_data.get('votes', 0))
        rank = safe_float(photo_data.get('rank', 999))
        
        factors = self.time_factors[time_category]
        
        # Score de base (normalisation)
        ratio_score = min(ratio / 3.0, 1.0)  # Normaliser sur 3.0 max
        
        # Score votes (logarithmique)
        votes_score = min(math.log(max(votes, 1)) / 10.0, 1.0) if votes > 0 else 0
        
        # Score rang (inversé)
        rank_score = max(0, (1000 - rank) / 1000) if rank < 999 else 0
        
        # Appliquer les poids selon le temps
        weighted_score = (
            ratio_score * factors['ratio_weight'] * 0.4 +
            votes_score * factors['votes_weight'] * 0.35 +
            rank_score * factors['rank_weight'] * 0.25
        )
        
        # Bonus de position selon le temps
        if position == 'photo2':
            weighted_score *= factors['position_bonus']
        
        # Bonus/malus spécifiques selon le temps
        if time_category == 'urgent':
            # En urgence, privilégier les évidences
            if ratio < 1.0:
                weighted_score *= 0.3  # Très mauvais ratio
            elif votes > 1000:
                weighted_score *= 1.2  # Beaucoup de votes
        
        elif time_category == 'long':
            # À long terme, plus conservateur sur ratio
            if ratio >= 1.5:
                weighted_score *= 1.1  # Bon ratio plus prédictif
        
        return weighted_score
    
    def decide(self, first_id, first_data, second_id, second_data, time_left=None):
        """Décision adaptative basée sur le temps restant"""
        
        # Parser le temps restant
        hours_left = parse_time_left_hours(time_left) if time_left else 24.0
        time_category = self.get_time_category(hours_left)
        
        # Calculer les scores adaptés au temps
        first_score = self.calculate_time_adjusted_score(first_id, first_data, 'photo1', time_category)
        second_score = self.calculate_time_adjusted_score(second_id, second_data, 'photo2', time_category)
        
        # Pour les cas très courts (≤1h), utiliser aussi l'expertise des autres algorithmes
        if time_category == 'urgent':
            try:
                # Consulter position_aware et bruno_custom
                pa_winner, _, _, _, _ = position_aware_algorithm(first_id, first_data, second_id, second_data)
                bc_winner, _, _, _, _ = bruno_custom_refined(first_id, first_data, second_id, second_data)
                
                # Si consensus, booster le gagnant
                if pa_winner == bc_winner:
                    if pa_winner == first_id:
                        first_score *= 1.15
                    else:
                        second_score *= 1.15
                        
            except Exception:
                pass  # Continuer sans le boost de consensus
        
        # Décision finale
        if first_score > second_score:
            winner_id = first_id
            winner_ratio = safe_float(first_data.get('ratio', 0))
            loser_ratio = safe_float(second_data.get('ratio', 0))
            winner_votes = safe_float(first_data.get('votes', 0))
        else:
            winner_id = second_id
            winner_ratio = safe_float(second_data.get('ratio', 0))
            loser_ratio = safe_float(first_data.get('ratio', 0))
            winner_votes = safe_float(second_data.get('votes', 0))
        
        # Description de la stratégie
        strategy_desc = f"adaptive_time: {time_category}({hours_left:.1f}h) scores({first_score:.3f}vs{second_score:.3f})"
        
        return winner_id, winner_ratio, loser_ratio, winner_votes, strategy_desc

# Import math pour log
import math

def adaptive_time_algorithm(first_id, first_data, second_id, second_data, time_left=None):
    """Interface fonction pour compatibilité avec les autres algorithmes"""
    algorithm = AdaptiveTimeAlgorithm()
    return algorithm.decide(first_id, first_data, second_id, second_data, time_left)

# Test de l'algorithme
def test_adaptive_time_algorithm():
    """Test de l'algorithme avec différents temps restants"""
    print("🧪 === TEST ADAPTIVE TIME ALGORITHM ===")
    
    # Cas de test avec différents temps
    test_cases = [
        {
            'name': 'Urgence - 30 minutes',
            'time_left': '0D 0H 30M 0S',
            'photo1': {'ratio': 1.3, 'votes': 800, 'rank': 200},
            'photo2': {'ratio': 1.5, 'votes': 1200, 'rank': 150},
            'expected_strategy': 'urgent'
        },
        {
            'name': 'Court terme - 3 heures',
            'time_left': '0D 3H 15M 0S',
            'photo1': {'ratio': 1.5, 'votes': 600, 'rank': 300},
            'photo2': {'ratio': 1.3, 'votes': 800, 'rank': 250},
            'expected_strategy': 'short'
        },
        {
            'name': 'Moyen terme - 18 heures',
            'time_left': '0D 18H 30M 0S',
            'photo1': {'ratio': 1.8, 'votes': 400, 'rank': 400},
            'photo2': {'ratio': 1.2, 'votes': 900, 'rank': 100},
            'expected_strategy': 'medium'
        },
        {
            'name': 'Long terme - 3 jours',
            'time_left': '3D 12H 0M 0S',
            'photo1': {'ratio': 2.0, 'votes': 200, 'rank': 500},
            'photo2': {'ratio': 1.1, 'votes': 150, 'rank': 600},
            'expected_strategy': 'long'
        }
    ]
    
    algorithm = AdaptiveTimeAlgorithm()
    
    print(f"Testant {len(test_cases)} scénarios temporels...")
    
    for i, case in enumerate(test_cases):
        winner, winner_ratio, loser_ratio, winner_votes, reason = algorithm.decide(
            'photo1', case['photo1'], 'photo2', case['photo2'], case['time_left']
        )
        
        strategy_used = reason.split(':')[1].split('(')[0]
        correct_strategy = strategy_used.strip() == case['expected_strategy']
        
        print(f"\n{i+1}. {case['name']}")
        print(f"   Time left: {case['time_left']}")
        print(f"   Photo1: r={case['photo1']['ratio']}, v={case['photo1']['votes']}, rk={case['photo1']['rank']}")
        print(f"   Photo2: r={case['photo2']['ratio']}, v={case['photo2']['votes']}, rk={case['photo2']['rank']}")
        print(f"   Gagnant: {winner}")
        print(f"   Stratégie: {strategy_used} {'✅' if correct_strategy else '❌'}")
        print(f"   Raison: {reason}")
    
    print(f"\n💡 L'algorithme adapte sa stratégie selon le temps restant:")
    print(f"   🚨 Urgence (≤1h): Privilégie votes et consensus")
    print(f"   ⏰ Court (1-6h): Balance votes/ratio avec léger bonus votes")
    print(f"   📊 Moyen (6-24h): Approche équilibrée standard")  
    print(f"   📈 Long (>24h): Privilégie ratio prédictif")

if __name__ == "__main__":
    print("⏱️ === ADAPTIVE TIME ALGORITHM ===\n")
    
    # Test de l'algorithme
    test_adaptive_time_algorithm()
    
    print(f"\n💡 Utilisation:")
    print(f"   from adaptive_time_algorithm import adaptive_time_algorithm")
    print(f"   winner, w_ratio, l_ratio, w_votes, desc = adaptive_time_algorithm(id1, data1, id2, data2, time_left)")