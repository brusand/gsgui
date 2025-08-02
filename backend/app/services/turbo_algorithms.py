"""
Turbo Algorithms Service - Refactorisé depuis gsui.py
Implémente tous les algorithmes de sélection turbo existants
"""

import logging
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import asyncio

logger = logging.getLogger(__name__)


class TurboAlgorithms:
    """
    Service contenant tous les algorithmes turbo existants de GSGUI
    Refactorisé depuis decide_turbo_choice() dans gsui.py
    """
    
    def __init__(self):
        self.algorithms = {
            'hybrid': self._algo_hybrid,
            'position_aware': self._algo_position_aware,
            'adaptive_time': self._algo_adaptive_time,
            'bruno_custom': self._algo_bruno_custom,
            'ratio_low': self._algo_ratio_low,
            'votes_high': self._algo_votes_high,
            'random': self._algo_random,
            'votes_ratio': self._algo_votes_ratio
        }
    
    def decide_turbo_choice(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        algorithm: str = "hybrid",
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Décide quel photo choisir entre deux options
        Refactorisé depuis decide_turbo_choice() dans gsui.py
        
        Returns: (winner_id, winner_ratio, loser_ratio, winner_votes, strategy_description)
        """
        try:
            # Gestion de l'ensemble d'algorithmes (format [algo1,algo2,algo3])
            if algorithm.startswith('[') and algorithm.endswith(']'):
                return self._ensemble_vote(first_data, second_data, algorithm, challenge_time_left)
            
            # Algorithme simple
            if algorithm in self.algorithms:
                return self.algorithms[algorithm](first_data, second_data, challenge_time_left)
            else:
                logger.warning(f"⚠️ Algorithme inconnu: {algorithm}, utilisation de hybrid")
                return self._algo_hybrid(first_data, second_data, challenge_time_left)
                
        except Exception as e:
            logger.error(f"❌ Erreur dans decide_turbo_choice: {e}")
            # Fallback sur bruno_custom en cas d'erreur
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def _ensemble_vote(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        algorithm_list: str,
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Vote d'ensemble - fait voter plusieurs algorithmes et prend la majorité
        """
        try:
            # Parser la liste d'algorithmes
            algorithm_list = algorithm_list.strip('[]')
            algorithms = [algo.strip() for algo in algorithm_list.split(',')]
            
            votes = {}
            descriptions = []
            
            # Faire voter chaque algorithme
            for algo in algorithms:
                if algo in self.algorithms:
                    try:
                        winner_id, winner_ratio, loser_ratio, winner_votes, desc = \
                            self.algorithms[algo](first_data, second_data, challenge_time_left)
                        
                        if winner_id not in votes:
                            votes[winner_id] = 0
                        votes[winner_id] += 1
                        descriptions.append(f"{algo}: {desc}")
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur algorithme {algo}: {e}")
                        continue
            
            if not votes:
                logger.warning("⚠️ Aucun vote d'ensemble valide, fallback sur bruno_custom")
                return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
            
            # Trouver le gagnant par majorité
            ensemble_winner = max(votes.keys(), key=lambda k: votes[k])
            vote_count = votes[ensemble_winner]
            
            # Déterminer les données du gagnant
            if ensemble_winner == first_data['id']:
                winner_ratio = first_data['ratio']
                loser_ratio = second_data['ratio']
                winner_votes = first_data['votes']
            else:
                winner_ratio = second_data['ratio']
                loser_ratio = first_data['ratio']
                winner_votes = second_data['votes']
            
            strategy_desc = f"Ensemble [{','.join(algorithms)}]: {vote_count}/{len(algorithms)} votes pour {ensemble_winner}"
            
            return ensemble_winner, winner_ratio, loser_ratio, winner_votes, strategy_desc
            
        except Exception as e:
            logger.error(f"❌ Erreur ensemble vote: {e}")
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def _algo_hybrid(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme hybride - équilibré (30% ratio, 40% votes, 30% rank)
        """
        try:
            first_ratio = first_data.get('ratio', 0.0)
            second_ratio = second_data.get('ratio', 0.0)
            first_votes = first_data.get('votes', 0)
            second_votes = second_data.get('votes', 0)
            first_rank = first_data.get('rank', 9999)
            second_rank = second_data.get('rank', 9999)
            
            # Score hybride pondéré
            def calculate_score(ratio, votes, rank):
                ratio_score = ratio * 0.3
                votes_score = (votes / max(first_votes + second_votes, 1)) * 0.4 * 100
                rank_score = (1.0 / max(rank, 1)) * 0.3 * 1000
                return ratio_score + votes_score + rank_score
            
            first_score = calculate_score(first_ratio, first_votes, first_rank)
            second_score = calculate_score(second_ratio, second_votes, second_rank)
            
            if first_score > second_score:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    f"Hybrid: Score {first_score:.2f} > {second_score:.2f}"
                )
            else:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    f"Hybrid: Score {second_score:.2f} > {first_score:.2f}"
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur algo hybrid: {e}")
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def _algo_position_aware(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme position-aware - utilise les patterns de position
        """
        try:
            first_ratio = first_data.get('ratio', 0.0)
            second_ratio = second_data.get('ratio', 0.0)
            first_votes = first_data.get('votes', 0)
            second_votes = second_data.get('votes', 0)
            
            # Position awareness - Photo1 vs Photo2 effects
            position_bonus_first = 0.1  # Léger avantage pour la première photo
            
            # Score composite avec bonus de position
            first_score = first_ratio * 0.6 + (first_votes / max(first_votes + second_votes, 1)) * 0.4 * 10 + position_bonus_first
            second_score = second_ratio * 0.6 + (second_votes / max(first_votes + second_votes, 1)) * 0.4 * 10
            
            if first_score > second_score:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    f"Position-aware: Score {first_score:.2f} > {second_score:.2f} (avec bonus position)"
                )
            else:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    f"Position-aware: Score {second_score:.2f} > {first_score:.2f}"
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur algo position_aware: {e}")
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def _algo_adaptive_time(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme adaptatif selon le temps restant
        """
        try:
            first_ratio = first_data.get('ratio', 0.0)
            second_ratio = second_data.get('ratio', 0.0)
            first_votes = first_data.get('votes', 0)
            second_votes = second_data.get('votes', 0)
            
            # Calculer le temps total restant en heures
            total_hours = 0
            if challenge_time_left:
                total_hours = (
                    challenge_time_left.get('days', 0) * 24 +
                    challenge_time_left.get('hours', 0) +
                    challenge_time_left.get('minutes', 0) / 60
                )
            
            # Stratégie adaptative selon le temps
            if total_hours <= 1:  # Urgent
                # Emphase sur les votes et le consensus
                first_score = first_ratio * 0.3 + (first_votes / max(first_votes + second_votes, 1)) * 0.7 * 10
                second_score = second_ratio * 0.3 + (second_votes / max(first_votes + second_votes, 1)) * 0.7 * 10
                strategy = "Urgent (≤1h): Emphase votes"
            elif total_hours <= 6:  # Court terme
                # Équilibré avec bonus votes
                first_score = first_ratio * 0.5 + (first_votes / max(first_votes + second_votes, 1)) * 0.5 * 10
                second_score = second_ratio * 0.5 + (second_votes / max(first_votes + second_votes, 1)) * 0.5 * 10
                strategy = "Court (1-6h): Équilibré avec bonus votes"
            elif total_hours <= 24:  # Moyen terme
                # Approche standard équilibrée
                first_score = first_ratio * 0.6 + (first_votes / max(first_votes + second_votes, 1)) * 0.4 * 10
                second_score = second_ratio * 0.6 + (second_votes / max(first_votes + second_votes, 1)) * 0.4 * 10
                strategy = "Moyen (6-24h): Standard équilibré"
            else:  # Long terme
                # Emphase sur les ratios prédictifs
                first_score = first_ratio * 0.8 + (first_votes / max(first_votes + second_votes, 1)) * 0.2 * 10
                second_score = second_ratio * 0.8 + (second_votes / max(first_votes + second_votes, 1)) * 0.2 * 10
                strategy = "Long (>24h): Emphase ratios prédictifs"
            
            if first_score > second_score:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    f"Adaptive-time: {strategy} - Score {first_score:.2f} > {second_score:.2f}"
                )
            else:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    f"Adaptive-time: {strategy} - Score {second_score:.2f} > {first_score:.2f}"
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur algo adaptive_time: {e}")
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def _algo_bruno_custom(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme Bruno Custom - logique sophistiquée avec règles spéciales
        Refactorisé depuis gsui.py
        """
        try:
            first_ratio = first_data.get('ratio', 0.0)
            second_ratio = second_data.get('ratio', 0.0)
            first_votes = first_data.get('votes', 0)
            second_votes = second_data.get('votes', 0)
            
            # Règle 1: Éviter les ratios < 1.0 (règle universelle)
            if first_ratio >= 1.0 and second_ratio < 1.0:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    "Bruno Custom: Règle 1 - Éviter ratio < 1.0"
                )
            elif second_ratio >= 1.0 and first_ratio < 1.0:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    "Bruno Custom: Règle 1 - Éviter ratio < 1.0"
                )
            
            # Règle 2: Zone spéciale ratio ~1.5 (priorité votes: 53.2% succès)
            if 1.4 <= first_ratio <= 1.6 or 1.4 <= second_ratio <= 1.6:
                if first_votes > second_votes:
                    return (
                        first_data['id'], first_ratio, second_ratio, first_votes,
                        "Bruno Custom: Règle 2 - Zone 1.5, priorité votes"
                    )
                else:
                    return (
                        second_data['id'], second_ratio, first_ratio, second_votes,
                        "Bruno Custom: Règle 2 - Zone 1.5, priorité votes"
                    )
            
            # Règle 3: Split ≥1.5 vs <1.5 (détection compensation massive)
            if first_ratio >= 1.5 and second_ratio < 1.5:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    "Bruno Custom: Règle 3 - Split ratio, choix ≥1.5"
                )
            elif second_ratio >= 1.5 and first_ratio < 1.5:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    "Bruno Custom: Règle 3 - Split ratio, choix ≥1.5"
                )
            
            # Règle 4: Logique classique fallback
            if first_ratio > second_ratio:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    "Bruno Custom: Règle 4 - Logique classique, ratio supérieur"
                )
            elif second_ratio > first_ratio:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    "Bruno Custom: Règle 4 - Logique classique, ratio supérieur"
                )
            else:
                # Ratios égaux, départager par votes
                if first_votes > second_votes:
                    return (
                        first_data['id'], first_ratio, second_ratio, first_votes,
                        "Bruno Custom: Règle 4 - Ratios égaux, plus de votes"
                    )
                else:
                    return (
                        second_data['id'], second_ratio, first_ratio, second_votes,
                        "Bruno Custom: Règle 4 - Ratios égaux, plus de votes"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Erreur algo bruno_custom: {e}")
            # Fallback ultime
            if first_data.get('ratio', 0) > second_data.get('ratio', 0):
                return (
                    first_data['id'], first_data.get('ratio', 0), second_data.get('ratio', 0), 
                    first_data.get('votes', 0), "Bruno Custom: Fallback - ratio supérieur"
                )
            else:
                return (
                    second_data['id'], second_data.get('ratio', 0), first_data.get('ratio', 0),
                    second_data.get('votes', 0), "Bruno Custom: Fallback - ratio supérieur"
                )
    
    def _algo_ratio_low(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme ratio low - choisit le ratio le plus bas (contre-intuitif)
        """
        first_ratio = first_data.get('ratio', 0.0)
        second_ratio = second_data.get('ratio', 0.0)
        
        if first_ratio < second_ratio:
            return (
                first_data['id'], first_ratio, second_ratio, first_data.get('votes', 0),
                f"Ratio Low: {first_ratio:.2f} < {second_ratio:.2f}"
            )
        else:
            return (
                second_data['id'], second_ratio, first_ratio, second_data.get('votes', 0),
                f"Ratio Low: {second_ratio:.2f} < {first_ratio:.2f}"
            )
    
    def _algo_votes_high(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme votes high - priorité aux photos avec plus de votes
        """
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        
        if first_votes > second_votes:
            return (
                first_data['id'], first_data.get('ratio', 0), second_data.get('ratio', 0), first_votes,
                f"Votes High: {first_votes} > {second_votes} votes"
            )
        else:
            return (
                second_data['id'], second_data.get('ratio', 0), first_data.get('ratio', 0), second_votes,
                f"Votes High: {second_votes} > {first_votes} votes"
            )
    
    def _algo_random(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme random - sélection aléatoire (pour tests)
        """
        if random.random() < 0.5:
            return (
                first_data['id'], first_data.get('ratio', 0), second_data.get('ratio', 0), 
                first_data.get('votes', 0), "Random: Première photo choisie aléatoirement"
            )
        else:
            return (
                second_data['id'], second_data.get('ratio', 0), first_data.get('ratio', 0),
                second_data.get('votes', 0), "Random: Seconde photo choisie aléatoirement"
            )
    
    def _algo_votes_ratio(
        self, 
        first_data: Dict[str, Any], 
        second_data: Dict[str, Any], 
        challenge_time_left: Optional[Dict[str, int]] = None
    ) -> Tuple[str, float, float, int, str]:
        """
        Algorithme votes_ratio - combine votes et ratio de façon équilibrée
        """
        try:
            first_ratio = first_data.get('ratio', 0.0)
            second_ratio = second_data.get('ratio', 0.0)
            first_votes = first_data.get('votes', 0)
            second_votes = second_data.get('votes', 0)
            
            # Score combiné votes + ratio (50/50)
            first_score = first_ratio * 0.5 + (first_votes / max(first_votes + second_votes, 1)) * 0.5 * 10
            second_score = second_ratio * 0.5 + (second_votes / max(first_votes + second_votes, 1)) * 0.5 * 10
            
            if first_score > second_score:
                return (
                    first_data['id'], first_ratio, second_ratio, first_votes,
                    f"Votes-Ratio: Score {first_score:.2f} > {second_score:.2f}"
                )
            else:
                return (
                    second_data['id'], second_ratio, first_ratio, second_votes,
                    f"Votes-Ratio: Score {second_score:.2f} > {first_score:.2f}"
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur algo votes_ratio: {e}")
            return self._algo_bruno_custom(first_data, second_data, challenge_time_left)
    
    def get_available_algorithms(self) -> List[Dict[str, str]]:
        """
        Retourne la liste des algorithmes disponibles avec leurs descriptions
        """
        return [
            {"name": "hybrid", "description": "Algorithme hybride équilibré (30% ratio, 40% votes, 30% rank)"},
            {"name": "position_aware", "description": "Algorithme tenant compte de la position des photos"},
            {"name": "adaptive_time", "description": "Algorithme adaptatif selon le temps restant"},
            {"name": "bruno_custom", "description": "Algorithme Bruno Custom avec règles sophistiquées"},
            {"name": "ratio_low", "description": "Choisit le ratio le plus bas (contre-intuitif)"},
            {"name": "votes_high", "description": "Priorité aux photos avec plus de votes"},
            {"name": "random", "description": "Sélection aléatoire (pour tests)"},
            {"name": "votes_ratio", "description": "Combine votes et ratio équitablement"}
        ]


# Instance globale du service
turbo_algorithms_service = TurboAlgorithms()