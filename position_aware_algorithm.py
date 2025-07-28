#!/usr/bin/env python3
"""
Algorithme Position-Aware basé sur l'analyse complète des ratios par position
Utilise les patterns réels découverts dans l'analyse des données
"""

import json
import math
import sys
import os

def safe_float(val, default=0.0):
    """Conversion sécurisée en float"""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

class PositionAwareAlgorithm:
    """Algorithme basé sur les patterns de position et ratio découverts"""
    
    def __init__(self):
        self.load_ratio_patterns()
        
    def load_ratio_patterns(self):
        """Charge les patterns d'analyse des ratios"""
        try:
            with open('ratios_analysis_for_algorithm.json', 'r') as f:
                self.data = json.load(f)
            
            # Créer des maps rapides pour les lookups
            self.position_effects = {
                effect['ratio']: effect for effect in self.data['position_effects']
            }
            
            # Ratios sûrs par position
            self.safe_ratios_p1 = {r['ratio']: r['win_rate'] for r in self.data['safe_ratios']['photo1']}
            self.safe_ratios_p2 = {r['ratio']: r['win_rate'] for r in self.data['safe_ratios']['photo2']}
            
            # Ratios dangereux par position  
            self.risky_ratios_p1 = {r['ratio']: r['win_rate'] for r in self.data['risky_ratios']['photo1']}
            self.risky_ratios_p2 = {r['ratio']: r['win_rate'] for r in self.data['risky_ratios']['photo2']}
            
            # Analyse complète pour patterns fins
            self.complete_patterns = {}
            for entry in self.data['complete_analysis']:
                key = (entry['ratio'], entry['position'])
                self.complete_patterns[key] = entry
                
            print("✅ Patterns de ratios chargés avec succès")
            
        except FileNotFoundError:
            print("⚠️ Fichier d'analyse non trouvé, utilisation de patterns par défaut")
            self.use_default_patterns()
    
    def use_default_patterns(self):
        """Patterns par défaut si fichier non disponible"""
        self.position_effects = {}
        self.safe_ratios_p1 = {2.2: 0.6}
        self.safe_ratios_p2 = {1.6: 0.71, 1.1: 0.706, 0.9: 0.643, 0.7: 0.619, 1.4: 0.617}
        self.risky_ratios_p1 = {0.6: 0.0, 0.0: 0.053, 0.7: 0.238, 1.0: 0.385}
        self.risky_ratios_p2 = {0.0: 0.057, 1.8: 0.368, 2.1: 0.4}
        self.complete_patterns = {}
    
    def get_ratio_confidence(self, ratio, position):
        """Calcule la confiance basée sur les patterns historiques"""
        ratio_round = round(ratio, 1)
        
        if position == 'photo1':
            # Ratios sûrs Photo1
            if ratio_round in self.safe_ratios_p1:
                return self.safe_ratios_p1[ratio_round]
            # Ratios dangereux Photo1
            elif ratio_round in self.risky_ratios_p1:
                return self.risky_ratios_p1[ratio_round]
        else:  # photo2
            # Ratios sûrs Photo2
            if ratio_round in self.safe_ratios_p2:
                return self.safe_ratios_p2[ratio_round]
            # Ratios dangereux Photo2
            elif ratio_round in self.risky_ratios_p2:
                return self.risky_ratios_p2[ratio_round]
        
        # Pattern complet si disponible
        pattern_key = (ratio_round, 'Photo1' if position == 'photo1' else 'Photo2')
        if pattern_key in self.complete_patterns:
            return self.complete_patterns[pattern_key]['win_rate']
        
        # Fallback: estimation basée sur le ratio brut
        if ratio >= 1.5:
            return 0.52  # Légèrement favorable
        elif ratio >= 1.0:
            return 0.45  # Neutre-défavorable
        else:
            return 0.25  # Défavorable
    
    def get_position_effect(self, ratio):
        """Obtient l'effet de position pour un ratio donné"""
        ratio_round = round(ratio, 1)
        
        if ratio_round in self.position_effects:
            effect = self.position_effects[ratio_round]
            return effect['position_effect'] / 100, effect['better_position']
        
        # Effet par défaut: Photo2 légèrement avantagé
        return 0.096, 'Photo2'  # +9.6% pour Photo2 comme observé globalement
    
    def calculate_votes_factor(self, votes, position):
        """Facteur correctif basé sur les votes"""
        if votes == 0:
            return 0.1  # Très défavorable
        
        # Normalisation logarithmique des votes
        votes_log = math.log(max(votes, 1))
        
        # Seuils observés dans l'analyse
        if votes >= 1000:
            base_factor = 1.2  # Bonus votes élevés
        elif votes >= 500:
            base_factor = 1.1  # Léger bonus
        elif votes >= 200:
            base_factor = 1.0  # Neutre
        else:
            base_factor = 0.9  # Malus votes faibles
        
        # Ajustement position (Photo2 a tendance à avoir plus de votes dans les cas gagnants)
        if position == 'photo2':
            base_factor *= 1.05
        
        return base_factor
    
    def calculate_rank_factor(self, rank, position):
        """Facteur correctif basé sur le rang"""
        if rank >= 999:
            return 0.1  # Photo non trouvée/très mal classée
        
        # Conversion rang en facteur (meilleur rang = facteur plus élevé)
        if rank <= 50:
            base_factor = 1.3  # Excellent rang
        elif rank <= 100:
            base_factor = 1.2  # Très bon rang
        elif rank <= 200:
            base_factor = 1.1  # Bon rang
        elif rank <= 400:
            base_factor = 1.0  # Rang moyen
        elif rank <= 600:
            base_factor = 0.9  # Rang médiocre
        else:
            base_factor = 0.8  # Mauvais rang
        
        return base_factor
    
    def calculate_composite_score(self, photo_id, photo_data, position):
        """Calcule le score composite pour une photo"""
        ratio = safe_float(photo_data.get('ratio', 0))
        votes = safe_float(photo_data.get('votes', 0))
        rank = safe_float(photo_data.get('rank', 999))
        
        # 1. Score de base basé sur les patterns de ratio+position
        base_confidence = self.get_ratio_confidence(ratio, position)
        
        # 2. Effet de position
        position_effect, better_pos = self.get_position_effect(ratio)
        position_multiplier = 1.0
        if better_pos.lower() == position:
            position_multiplier = 1.0 + position_effect
        else:
            position_multiplier = 1.0 - position_effect
        
        # 3. Facteur votes
        votes_factor = self.calculate_votes_factor(votes, position)
        
        # 4. Facteur rang
        rank_factor = self.calculate_rank_factor(rank, position)
        
        # 5. Score composite avec pondération
        # Poids: patterns historiques 40%, position 25%, votes 20%, rang 15%
        composite_score = (
            base_confidence * 0.40 * position_multiplier +
            votes_factor * 0.20 +
            rank_factor * 0.15 +
            (ratio / 3.0) * 0.25  # Normalisation ratio brut
        )
        
        # Bonus spéciaux basés sur les découvertes
        # Photo2 a un avantage global de 9.6%
        if position == 'photo2':
            composite_score *= 1.096
        
        # Malus pour ratios < 1.0 (très défavorables)
        if ratio < 1.0:
            composite_score *= 0.7
        
        # Bonus pour ratios "magiques" observés
        ratio_round = round(ratio, 1)
        if position == 'photo1' and ratio_round == 2.2:
            composite_score *= 1.15  # Seul ratio vraiment sûr pour Photo1
        elif position == 'photo2' and ratio_round in [1.6, 1.1, 1.4]:
            composite_score *= 1.12  # Ratios très favorables pour Photo2
        
        return composite_score
    
    def decide(self, first_id, first_data, second_id, second_data):
        """Décision principale basée sur l'analyse position-aware"""
        
        # Calculer les scores composites
        first_score = self.calculate_composite_score(first_id, first_data, 'photo1')
        second_score = self.calculate_composite_score(second_id, second_data, 'photo2')
        
        # Décision
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
        ratio1 = round(safe_float(first_data.get('ratio', 0)), 1)
        ratio2 = round(safe_float(second_data.get('ratio', 0)), 1)
        
        strategy_desc = f"position_aware: scores({first_score:.3f} vs {second_score:.3f}) ratios({ratio1}vs{ratio2})"
        
        return winner_id, winner_ratio, loser_ratio, winner_votes, strategy_desc

# Instance globale pour éviter de recharger les patterns à chaque appel
_global_algorithm = None

def position_aware_algorithm(first_id, first_data, second_id, second_data):
    """Interface fonction pour compatibilité avec les autres algorithmes"""
    global _global_algorithm
    if _global_algorithm is None:
        _global_algorithm = PositionAwareAlgorithm()
    return _global_algorithm.decide(first_id, first_data, second_id, second_data)

# Test de l'algorithme
def test_position_aware_algorithm():
    """Test de l'algorithme avec quelques cas"""
    print("🧪 === TEST POSITION AWARE ALGORITHM ===")
    
    test_cases = [
        # Cas 1: 1.3 vs 1.5 (Photo2 devrait gagner selon analyse)
        {
            'name': '1.3 vs 1.5 - Photo2 favori',
            'photo1': {'ratio': 1.3, 'votes': 767, 'rank': 429},
            'photo2': {'ratio': 1.5, 'votes': 780, 'rank': 417},
            'expected': 'photo2'
        },
        
        # Cas 2: 1.5 vs 1.3 (Photo2 devrait quand même gagner - pattern surprenant)
        {
            'name': '1.5 vs 1.3 - Photo2 contre-intuitif',
            'photo1': {'ratio': 1.5, 'votes': 820, 'rank': 350},
            'photo2': {'ratio': 1.3, 'votes': 809, 'rank': 355},
            'expected': 'photo2'  # Basé sur l'analyse
        },
        
        # Cas 3: Ratio dangereux 0.6 vs 1.5
        {
            'name': '0.6 vs 1.5 - Ratio dangereux',
            'photo1': {'ratio': 0.6, 'votes': 690, 'rank': 458},
            'photo2': {'ratio': 1.5, 'votes': 800, 'rank': 300},
            'expected': 'photo2'
        },
        
        # Cas 4: Ratios égaux 1.5 vs 1.5
        {
            'name': '1.5 vs 1.5 - Position départage',
            'photo1': {'ratio': 1.5, 'votes': 879, 'rank': 390},
            'photo2': {'ratio': 1.5, 'votes': 913, 'rank': 361},
            'expected': 'photo2'  # Photo2 avantagé globalement
        },
        
        # Cas 5: Ratio sûr Photo2
        {
            'name': '1.2 vs 1.6 - Ratio sûr Photo2',
            'photo1': {'ratio': 1.2, 'votes': 500, 'rank': 400},
            'photo2': {'ratio': 1.6, 'votes': 884, 'rank': 323},
            'expected': 'photo2'  # 1.6 très fort pour Photo2
        }
    ]
    
    algorithm = PositionAwareAlgorithm()
    
    print(f"Testant {len(test_cases)} cas...")
    correct_predictions = 0
    
    for i, case in enumerate(test_cases):
        winner, winner_ratio, loser_ratio, winner_votes, reason = algorithm.decide(
            'photo1', case['photo1'], 'photo2', case['photo2']
        )
        
        success = winner == case['expected']
        if success:
            correct_predictions += 1
        
        print(f"\n{i+1}. {case['name']}")
        print(f"   Photo1: r={case['photo1']['ratio']}, v={case['photo1']['votes']}, rk={case['photo1']['rank']}")
        print(f"   Photo2: r={case['photo2']['ratio']}, v={case['photo2']['votes']}, rk={case['photo2']['rank']}")
        print(f"   Gagnant: {winner} {'✅' if success else '❌'}")
        print(f"   Raison: {reason}")
        print(f"   Attendu: {case['expected']}")
    
    accuracy = correct_predictions / len(test_cases) * 100
    print(f"\n🎯 Précision: {correct_predictions}/{len(test_cases)} ({accuracy:.1f}%)")
    
    if accuracy >= 80:
        print("✅ Algorithme performant!")
    elif accuracy >= 60:
        print("⚠️ Algorithme acceptable, peut être amélioré")
    else:
        print("❌ Algorithme nécessite des ajustements")

if __name__ == "__main__":
    print("🚀 === POSITION AWARE ALGORITHM ===\n")
    
    # Test de l'algorithme
    test_position_aware_algorithm()
    
    print(f"\n💡 Utilisation:")
    print(f"   from position_aware_algorithm import position_aware_algorithm")
    print(f"   winner, w_ratio, l_ratio, w_votes, desc = position_aware_algorithm(id1, data1, id2, data2)")