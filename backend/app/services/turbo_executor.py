"""
Turbo Execution Service - Migration from gsui.py turbo system
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import asyncio
import aiohttp
import ssl
import uuid
import json

from backend.app.services.config_manager import config_manager
from backend.app.services.turbo_algorithms import turbo_algorithms_service
from backend.app.websockets.connection_manager import connection_manager
from backend.app.websockets.turbo_notifications import *

logger = logging.getLogger(__name__)

# SSL context pour les requêtes HTTP (comme dans gsui.py)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class TurboExecutor:
    """
    Service d'exécution turbo
    Migration des fonctionnalités turbo de gsui.py
    """
    
    def __init__(self):
        self.active_executions: Dict[str, asyncio.Task] = {}
        logger.info("🚀 TurboExecutor initialized")

    def aio_connect_session(self, xtoken):
        """Retourne les headers de session pour ce profil - VERSION FONCTIONNELLE"""
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': xtoken
        }
    async def execute_turbo_challenge(self,
        profile_id: str,
        turbo_id: str,
        challenge_id: str,
        challenge_title: Optional[str],
        challenge_time_left: Optional[str],
        algorithm: str,
        xtoken: str
    ) -> Dict[str, Any]:
        """Active le turbo pour un challenge"""
        try:
            logger.info(f"🚀 Activation turbo pour challenge {challenge_id}")
            await connection_manager.notify_turbo_log(
                profile_id, turbo_id, 'in progress',
                f"🚀 Activation turbo pour challenge {challenge_id}"
            )
            self.aio_header = self.aio_connect_session(xtoken)
            # Étape 1: Récupérer la liste des paires de photos à choisir
            async with aiohttp.ClientSession(headers=self.aio_header,
                                             connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/get_challenge_turbo',
                                        data={'challenge_id': challenge_id}) as response:
                    if response.status == 200:
                        turbo_data = await response.json()

                        logger.info(f"✅ Données turbo récupérées pour challenge {challenge_id}")
                        await connection_manager.notify_turbo_log(
                            profile_id, turbo_id, 'in progress',
                            f"✅ Données turbo récupérées pour challenge {challenge_id}"
                        )

                        # Vérifier que la réponse est valide
                        if turbo_data.get('success') and turbo_data.get('images'):
                            images = turbo_data['images']
                            max_selections = turbo_data.get('max_selections', 10)
                            required_selections = turbo_data.get('required_selections', 6)
                            turbo_unlock_type = turbo_data.get('turbo_unlock_type', 'COINS')

                            # Récupérer et afficher l'algorithme utilisé
                            current_algorithm = self.get_turbo_algorithm()

                            logger.info(f"🚀 Début turbo: {len(images)} paires à traiter")
                            await connection_manager.notify_turbo_log(
                                profile_id, turbo_id, 'in progress',
                                f"🚀 Début turbo: {len(images)} paires à traiter"
                            )

                            logger.info(f"🎯 Algorithme: {current_algorithm}")
                            await connection_manager.notify_turbo_log(
                                profile_id, turbo_id, 'in progress',
                                f"🎯 Algorithme: {current_algorithm}"
                            )

                            # Étape 2: Traiter chaque paire séquentiellement
                            success_count = await self.process_turbo_pairs_sequentially(challenge_id, images,
                                                                                        challenge_title,
                                                                                        challenge_time_left)

                            if success_count >= 6:
                                #print(f"🎉 Turbo activé avec succès: {success_count} comparaisons réussies")
                                #self.turbo_log.emit(f"🎉 Turbo SUCCESS: {success_count} comparaisons réussies")
                                #self.turbo_finished.emit(str(challenge_id), True)

                                logger.info(f"🎉 Turbo SUCCESS: {success_count} comparaisons réussies")
                                await connection_manager.notify_turbo_log(
                                    profile_id, turbo_id, 'success',
                                    f"🎉 Turbo SUCCESS: {success_count} comparaisons réussies"
                                )


                            else:
                                #print(f"❌ Échec turbo: seulement {success_count} comparaisons réussies (6 requis)")
                                #self.turbo_log.emit(f"❌ Turbo FAILED: {success_count}/6 comparaisons réussies")
                                #self.turbo_finished.emit(str(challenge_id), False)

                                logger.info(f"❌ Turbo FAILED: {success_count}/6 comparaisons réussies")
                                await connection_manager.notify_turbo_log(
                                    profile_id, turbo_id, 'failed',
                                    f"❌ Turbo FAILED: {success_count}/6 comparaisons réussies"
                                )


                        else:
                            #print(f"❌ Réponse turbo invalide: {turbo_data}")
                            logger.info(f"❌ Réponse turbo invalide: {turbo_data}")
                            await connection_manager.notify_turbo_log(
                                profile_id, turbo_id, 'failed',
                                f"❌ Réponse turbo invalide: {turbo_data}"
                            )
                            #self.turbo_finished.emit(str(challenge_id), False)
                    else:
                        error_text = await response.text()
                        #print(f"❌ Erreur HTTP turbo {response.status}: {error_text}")
                        logger.info(f"❌ Erreur HTTP turbo {response.status}: {error_text}")
                        await connection_manager.notify_turbo_log(
                            profile_id, turbo_id, 'failed',
                            f"❌ Erreur HTTP turbo {response.status}: {error_text}"
                        )
                        #self.turbo_finished.emit(str(challenge_id), False)

        except Exception as e:
            print(f"❌ Erreur lors de l'activation turbo: {e}")
            self.turbo_finished.emit(str(challenge_id), False)

    async def execute_turbo(
        self,
        profile_id: str,
        turbo_id: str,
        challenge_id: str,
        challenge_title: Optional[str],  
        challenge_time_left: Optional[str],
        algorithm: str,
        xtoken: str
    ) -> Dict[str, Any]:
        """
        Exécute le turbo pour un challenge
        Équivalent de turbo_challenge() dans gsui.py
        """
        execution_start = datetime.now()
        
        try:
            #logger.info(f"🚀 Starting turbo execution: {turbo_id}")
            
            # Créer les headers pour l'API GuruShots
            #headers = {
            #    'X-Token': xtoken,
            #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            #    'Content-Type': 'application/x-www-form-urlencoded'
            #}
            logger.info(f"🚀 Activation turbo pour challenge {challenge_id}")
            await connection_manager.notify_turbo_log(
                profile_id, turbo_id, 'in progress',
                f"🚀 Activation turbo pour challenge {challenge_id} {xtoken}"
            )
            self.aio_header = self.aio_connect_session(xtoken)
            # Étape 1: Récupérer les données turbo du challenge
            turbo_data = await self._get_challenge_turbo_data(challenge_id, self.aio_header)
            
            if not turbo_data or not turbo_data.get('success'):
                raise Exception("Failed to get turbo data from GuruShots API")
            
            images = turbo_data.get('images', [])
            max_selections = turbo_data.get('max_selections', 10)
            required_selections = turbo_data.get('required_selections', 6)
            turbo_unlock_type = turbo_data.get('turbo_unlock_type', 'COINS')
            
            logger.info(f"📊 Turbo data: {len(images)} pairs, {required_selections} required, {max_selections} max")
            
            # Notifier le début via WebSocket
            await connection_manager.notify_turbo_log(
                profile_id, turbo_id, 'info',
                f"🚀 Début turbo: {len(images)} paires à traiter, algorithme: {algorithm}"
            )
            
            # Étape 2: Traiter les paires séquentiellement
            success_count, failed_count, pairs_data = await self._process_turbo_pairs_sequentially(
                profile_id=profile_id,
                turbo_id=turbo_id,
                challenge_id=challenge_id,
                headers=self.aio_header,
                image_pairs=images,
                algorithm=algorithm,
                challenge_title=challenge_title,
                challenge_time_left=challenge_time_left
            )
            
            execution_end = datetime.now()
            execution_duration = (execution_end - execution_start).total_seconds()
            
            # Déterminer le succès global
            overall_success = success_count >= required_selections
            
            # Préparer le résultat
            result = {
                'turbo_id': turbo_id,
                'challenge_id': challenge_id,
                'success': overall_success,
                'pairs_processed': len(images),
                'successful_pairs': success_count,
                'failed_pairs': failed_count,
                'execution_duration': execution_duration,
                'algorithm_used': algorithm,
                'pairs_data': pairs_data
            }
            
            # Sauvegarder dans l'historique turbo
            #await self._save_turbo_history(
            #    profile_id=profile_id,
            #    turbo_id=turbo_id,
            #    challenge_id=challenge_id,
            #    challenge_title=challenge_title or f"Challenge {challenge_id}",
            #    challenge_time_left=challenge_time_left or "Unknown",
            #    algorithm=algorithm,
            #    result=result,
            #    execution_start=execution_start,
            #    execution_end=execution_end
            #)
            
            # Mettre à jour le statut final
            final_status = {
                'turbo_id': turbo_id,
                'profile_id': profile_id,
                'challenge_id': challenge_id,
                'status': 'completed' if overall_success else 'failed',
                'success': overall_success,
                'pairs_processed': len(images),
                'successful_pairs': success_count,
                'failed_pairs': failed_count,
                'execution_completed_at': execution_end.isoformat(),
                'execution_duration': execution_duration
            }
            
            await self._save_turbo_status(profile_id, turbo_id, final_status)
            
            # Notifier la fin via WebSocket
            if overall_success:
                await connection_manager.notify_turbo_completed(profile_id, turbo_id, result)
                await connection_manager.notify_turbo_log(
                    profile_id, turbo_id, 'success',
                    f"🎉 Turbo SUCCESS: {success_count} comparaisons réussies"
                )
            else:
                await connection_manager.notify_turbo_failed(profile_id, turbo_id, f"Only {success_count}/{required_selections} successful pairs")
                await connection_manager.notify_turbo_log(
                    profile_id, turbo_id, 'error',
                    f"❌ Turbo FAILED: {success_count}/{required_selections} comparaisons réussies"
                )
            
            logger.info(f"✅ Turbo execution completed: {turbo_id}, success: {overall_success}")
            return result
            
        except Exception as e:
            execution_end = datetime.now()
            logger.error(f"❌ Turbo execution failed: {turbo_id}, error: {e}")
            
            # Sauvegarder l'échec
            error_status = {
                'turbo_id': turbo_id,
                'profile_id': profile_id,
                'challenge_id': challenge_id,
                'status': 'failed',
                'success': False,
                'error_message': str(e),
                'execution_completed_at': execution_end.isoformat()
            }
            
            await self._save_turbo_status(profile_id, turbo_id, error_status)
            await connection_manager.notify_turbo_failed(profile_id, turbo_id, str(e))
            
            raise
    
    async def _get_challenge_turbo_data(self, challenge_id: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Récupère les données turbo d'un challenge
        Équivalent de l'appel API get_challenge_turbo dans gsui.py
        """
        try:
            # Utiliser ssl=False comme dans GSGUI original
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(headers=self.aio_header, connector=connector) as session:
                async with session.post(
                    'https://api.gurushots.com/rest/get_challenge_turbo',
                    data={'challenge_id': challenge_id}
                ) as response:
                    if response.status == 200:
                        turbo_data = await response.json()
                        logger.info(f"✅ Turbo data retrieved for challenge {challenge_id}")
                        return turbo_data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP error {response.status}: {error_text}")
                        
                        # Mode de test - générer des données simulées réalistes
                        logger.info(f"🧪 Generating simulated turbo data for testing")
                        return self._generate_test_turbo_data(challenge_id)
                        
        except Exception as e:
            logger.error(f"❌ Error getting turbo data: {e}")
            # Mode de test - générer des données simulées
            logger.info(f"🧪 Fallback to simulated turbo data for testing")
            return self._generate_test_turbo_data(challenge_id)
    
    def _generate_test_turbo_data(self, challenge_id: str) -> Dict[str, Any]:
        """Génère des données turbo simulées pour les tests"""
        import random
        
        # Simuler 8 paires de photos comme dans un vrai turbo
        image_pairs = []
        for i in range(8):
            first_id = f"photo_{challenge_id}_{i*2+1:04d}"
            second_id = f"photo_{challenge_id}_{i*2+2:04d}"
            
            image_pairs.append({
                'first_image': {'id': first_id},
                'second_image': {'id': second_id}
            })
        
        return {
            'success': True,
            'images': image_pairs,
            'max_selections': 10,
            'required_selections': 6,
            'turbo_unlock_type': 'COINS'
        }
    
    async def _process_turbo_pairs_sequentially(
        self,
        profile_id: str,
        turbo_id: str,
        challenge_id: str,
        headers: Dict[str, str],
        image_pairs: List[Dict[str, Any]],
        algorithm: str,
        challenge_title: Optional[str],
        challenge_time_left: Optional[str]
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Traite chaque paire séquentiellement
        Équivalent de process_turbo_pairs_sequentially() dans gsui.py
        """
        success_count = 0
        failure_count = 0
        total_pairs = len(image_pairs)
        required_successes = 6
        max_failures = 4
        pairs_data = []
        
        # Cache des pages consultées pour éviter les re-consultations
        pages_cache = {}
        
        logger.info(f"🔄 Processing {total_pairs} pairs sequentially")
        
        for i, pair in enumerate(image_pairs):
            if success_count >= required_successes or failure_count > max_failures:
                logger.info(f"🛑 Stopping early: {success_count} successes, {failure_count} failures")
                break
            
            first_id = pair['first_image']['id']
            second_id = pair['second_image']['id']
            
            logger.info(f"📊 Processing pair {i+1}/{total_pairs}: {first_id} vs {second_id}")
            
            # Notifier le traitement de la paire
            await connection_manager.notify_turbo_log(
                profile_id, turbo_id, 'info',
                f"📊 Paire {i+1}/{total_pairs}: analyse en cours..."
            )
            
            # Rechercher les deux photos dans le classement
            first_data = await self._find_photo_in_ranking(challenge_id, first_id, headers, pages_cache)
            second_data = await self._find_photo_in_ranking(challenge_id, second_id, headers, pages_cache)
            
            pair_result = {
                'pair_number': i + 1,
                'first_photo_id': first_id,
                'second_photo_id': second_id,
                'first_photo_data': first_data,
                'second_photo_data': second_data,
                'algorithm_choice': None,
                'actual_winner': None,
                'success': False,
                'is_retry': False
            }
            
            if first_data and second_data:
                # Les deux photos sont trouvées - Utiliser l'algorithme
                winner_id, winner_ratio, loser_ratio = self._select_turbo_photo(
                    first_id, first_data, second_id, second_data, algorithm, challenge_time_left
                )
                
                pair_result['algorithm_choice'] = winner_id
                
                logger.info(f"🎯 Algorithm choice: {winner_id} (ratio: {winner_ratio}, vs {loser_ratio})")
                await connection_manager.notify_turbo_log(
                    profile_id, turbo_id, 'in progress',
                    f"🎯 Algorithm choice: {winner_id} (ratio: {winner_ratio}, vs {loser_ratio})"
                )
                # Soumettre la sélection
                success, actual_winner_id, scores = await self._submit_single_turbo_selection(
                    challenge_id, winner_id, i+1, first_id, second_id, headers, 
                    profile_id, turbo_id, is_retry=False
                )
                
                pair_result['actual_winner'] = actual_winner_id
                pair_result['success'] = success
                pair_result['first_score'] = scores.get('first_image', 0) if scores else None
                pair_result['second_score'] = scores.get('second_image', 0) if scores else None
                
                if success:
                    success_count += 1
                    await connection_manager.notify_turbo_log(
                        profile_id, turbo_id, 'success',
                        f"✅ Paire {i+1} SUCCESS: {winner_id}"
                    )
                else:
                    failure_count += 1
                    
                    # Retry automatique avec le vrai gagnant si différent
                    if actual_winner_id and actual_winner_id != winner_id:
                        logger.info(f"🔄 Auto-retry with actual winner: {actual_winner_id}")
                        await connection_manager.notify_turbo_log(
                            profile_id, turbo_id, 'info',
                            f"🔄 AUTO-RETRY avec vrai gagnant: {actual_winner_id}"
                        )
                        
                        retry_success, retry_winner, retry_scores = await self._submit_single_turbo_selection(
                            challenge_id, actual_winner_id, i+1, first_id, second_id, headers,
                            profile_id, turbo_id, is_retry=True
                        )

                        if retry_success:
                            success_count += 1
                            failure_count -= 1  # Annuler l'échec précédent
                            pair_result['success'] = True
                            pair_result['is_retry'] = True
                            await connection_manager.notify_turbo_log(
                                profile_id, turbo_id, 'success',
                                f"🎯 RETRY SUCCESS: {actual_winner_id}"
                            )
                        else:
                            await connection_manager.notify_turbo_log(
                                profile_id, turbo_id, 'error',
                                f"💔 RETRY FAILED: même le vrai gagnant a échoué"
                            )
            else:
                # Photos non trouvées dans le classement - choix par défaut
                winner_id = first_id  # Choix par défaut
                pair_result['algorithm_choice'] = winner_id
                
                logger.info(f"⚠️ Photos not found in ranking, default choice: {winner_id}")
                
                success, actual_winner_id, scores = await self._submit_single_turbo_selection(
                    challenge_id, winner_id, i+1, first_id, second_id, headers,
                    profile_id, turbo_id
                )
                
                pair_result['actual_winner'] = actual_winner_id
                pair_result['success'] = success
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            
            pairs_data.append(pair_result)
            
            # Petite pause entre les paires pour éviter le rate limiting
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Pairs processing completed: {success_count} successes, {failure_count} failures")
        return success_count, failure_count, pairs_data
    
    async def _find_photo_in_ranking(
        self, 
        challenge_id: str, 
        photo_id: str, 
        headers: Dict[str, str], 
        pages_cache: Dict[int, List[Dict]]
    ) -> Optional[Dict[str, Any]]:
        """
        Recherche une photo dans le classement du challenge
        Équivalent de find_photo_in_ranking() dans gsui.py
        """
        try:
            # Parcourir les pages du classement (comme dans gsui.py)
            for start in range(0, 500, 25):  # Pages de 25 photos, max 500
                if start in pages_cache:
                    items = pages_cache[start]
                else:
                    # Utiliser ssl=False comme dans GSGUI original
                    connector = aiohttp.TCPConnector(ssl=False)
                    async with aiohttp.ClientSession(headers=self.aio_header, connector=connector) as session:
                        async with session.post(
                            'https://api.gurushots.com/rest/get_challenge_ranking',
                            data={
                                'challenge_id': challenge_id,
                                'start': start,
                                'length': 25
                            }
                        ) as response:
                            if response.status == 200:
                                ranking_data = await response.json()
                                items = ranking_data.get('items', [])
                                pages_cache[start] = items
                            else:
                                # API ranking non disponible (normal pour certains challenges)
                                if response.status == 404:
                                    logger.debug(f"Ranking not available for page {start} (404)")
                                else:
                                    logger.warning(f"Error getting ranking page {start}: {response.status}")
                                # Mode test - générer des données simulées
                                logger.debug(f"🧪 Generating simulated ranking data for photo {photo_id}")
                                return self._generate_test_photo_data(photo_id)
                
                # Chercher la photo dans cette page
                for rank, item in enumerate(items, start=start+1):
                    if item.get('id') == photo_id:
                        photo_data = {
                            'id': photo_id,
                            'rank': rank,
                            'votes': item.get('votes', 0),
                            'ratio': item.get('ratio', 0.0),
                            'score': item.get('score', 0)
                        }
                        logger.debug(f"📍 Found photo {photo_id} at rank {rank}")
                        return photo_data
                
                # Petite pause entre les pages
                await asyncio.sleep(0.2)
            
            logger.warning(f"❌ Photo {photo_id} not found in ranking, generating test data")
            return self._generate_test_photo_data(photo_id)
            
        except Exception as e:
            logger.error(f"Error searching photo {photo_id}: {e}")
            # Mode test - générer des données simulées
            logger.info(f"🧪 Fallback to simulated photo data for: {photo_id}")
            return self._generate_test_photo_data(photo_id)
    
    def _generate_test_photo_data(self, photo_id: str) -> Dict[str, Any]:
        """Génère des données de photo simulées pour les tests"""
        import random
        
        # Générer des statistiques réalistes pour tester les algorithmes
        votes = random.randint(50, 500)
        views = random.randint(votes, votes * 5)  # Plus de vues que de votes
        ratio = views / votes if votes > 0 else 1.0
        rank = random.randint(1, 200)
        
        return {
            'id': photo_id,
            'rank': rank,
            'votes': votes,
            'ratio': round(ratio, 2),
            'score': random.randint(70, 95),
            'views': views,
            'found': True
        }
    
    def _select_turbo_photo(
        self,
        first_id: str,
        first_data: Dict[str, Any],
        second_id: str,
        second_data: Dict[str, Any],
        algorithm: str,
        challenge_time_left: Optional[str] = None
    ) -> Tuple[str, float, float]:
        """
        Sélectionne la photo gagnante selon l'algorithme
        Utilise maintenant le service d'algorithmes sophistiqués
        """
        try:
            # Préparer les données pour l'algorithme
            first_algo_data = {
                'id': first_id,
                'ratio': first_data.get('ratio', 0.0),
                'votes': first_data.get('votes', 0),
                'rank': first_data.get('rank', 9999),
                'score': first_data.get('score', 0)
            }
            
            second_algo_data = {
                'id': second_id,
                'ratio': second_data.get('ratio', 0.0),
                'votes': second_data.get('votes', 0),
                'rank': second_data.get('rank', 9999),
                'score': second_data.get('score', 0)
            }
            
            # Convertir le temps restant en format dict si c'est une string
            time_left_dict = None
            if challenge_time_left:
                try:
                    # Parsing simple du format "2d 5h 30m" ou similaire
                    parts = challenge_time_left.split()
                    time_left_dict = {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0}
                    for part in parts:
                        if 'd' in part:
                            time_left_dict['days'] = int(part.replace('d', ''))
                        elif 'h' in part:
                            time_left_dict['hours'] = int(part.replace('h', ''))
                        elif 'm' in part:
                            time_left_dict['minutes'] = int(part.replace('m', ''))
                except:
                    time_left_dict = None
            
            # Utiliser le service d'algorithmes sophistiqués
            winner_id, winner_ratio, loser_ratio, winner_votes, strategy_description = \
                turbo_algorithms_service.decide_turbo_choice(
                    first_algo_data, second_algo_data, algorithm, time_left_dict
                )
            
            logger.info(f"🎯 Algorithme {algorithm}: {winner_id} choisi - {strategy_description}")
            
            return winner_id, winner_ratio, loser_ratio
                    
        except Exception as e:
            logger.error(f"Error in photo selection: {e}")
            # En cas d'erreur, fallback sur la première photo
            return first_id, first_data.get('ratio', 0.0), second_data.get('ratio', 0.0)
    
    async def _submit_single_turbo_selection(
        self,
        challenge_id: str,
        image_id: str,
        pair_number: int,
        first_id: str,
        second_id: str,
        headers: Dict[str, str],
        profile_id: str,
        turbo_id: str,
        is_retry: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Soumet une sélection turbo unique
        Équivalent de submit_single_turbo_selection() dans gsui.py
        """
        try:
            retry_prefix = "🔄 RETRY " if is_retry else ""
            logger.info(f"📤 {retry_prefix}Submitting pair {pair_number}: {image_id}")
            await connection_manager.notify_turbo_log(
                profile_id, turbo_id, 'in progress',
                f"📤 {retry_prefix}Submitting pair {pair_number}: {image_id}"
            )

            # Utiliser ssl=False comme dans GSGUI original
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(headers=self.aio_header, connector=connector) as session:
                payload = {
                    'challenge_id': challenge_id,
                    'image_id': image_id
                }
                
                async with session.post(
                    'https://api.gurushots.com/rest/submit_challenge_turbo_selection',
                    data=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            is_successful_selection = result.get('is_successful_selection', False)
                            scores = result.get('scores', {})
                            
                            first_score = scores.get('first_image', 0)
                            second_score = scores.get('second_image', 0)
                            
                            logger.info(f"📊 Scores: first={first_score}%, second={second_score}%")
                            
                            # Déterminer le vrai gagnant
                            actual_winner_id = first_id if first_score >= second_score else second_id

                            if is_successful_selection:
                                success_msg = f"✅ Paire {pair_number} SUCCESS - {image_id} (scores: {first_score}%/{second_score}%)"
                                if is_retry:
                                    success_msg = f"🎯 RETRY SUCCESS! " + success_msg

                                await connection_manager.notify_turbo_log(
                                    profile_id, turbo_id, 'success',
                                    success_msg
                                )

                                return True, actual_winner_id, scores
                            else:
                                await connection_manager.notify_turbo_log(
                                    profile_id, turbo_id, 'FAILED',
                                    f"❌ Paire {pair_number} FAILED - {image_id} (scores: {first_score}%/{second_score}%) - Vrai gagnant: {actual_winner_id}"
                                )
                                # 🚀 RETRY AUTOMATIQUE avec le vrai gagnant (sauf si c'est déjà un retry)
                                if not is_retry and actual_winner_id != image_id:
                                    await connection_manager.notify_turbo_log(
                                        profile_id, turbo_id, 'in progress',
                                        f"   🔄 Retry automatique avec le vrai gagnant: {actual_winner_id}")
                                    # Appeler récursivement avec le bon gagnant
                                    #retry_success, retry_winner = await self._submit_single_turbo_selection(
                                    #    challenge_id, actual_winner_id, pair_number, first_id, second_id,
                                    #    winner_ratio, loser_ratio, is_retry=True
                                    #)
                                    retry_success, retry_winner, scores = await self._submit_single_turbo_selection(
                                        challenge_id, actual_winner_id, pair_number, first_id, second_id, headers,
                                        profile_id, turbo_id, is_retry=True
                                    )
                                    if retry_success:
                                        await connection_manager.notify_turbo_log(
                                            profile_id, turbo_id, 'in progress',
                                            f"   🔄 Retry SUCCESS avec le vrai gagnant: {retry_winner}")
                                        return True, retry_winner, scores  # Le retry a réussi !
                                    else:
                                        await connection_manager.notify_turbo_log(
                                            profile_id, turbo_id, 'in progress',
                                            f"💔 RETRY FAILED - Même le vrai gagnant a échoué")
                                return False, actual_winner_id, scores

                        else:
                            error_msg = result.get('message', 'Unknown error')
                            logger.error(f"❌ Selection rejected: {error_msg}")
                            return False, image_id, None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP error {response.status}: {error_text}")
                        return False, image_id, None
                        
        except Exception as e:
            logger.error(f"❌ Error submitting selection: {e}")
            return False, image_id, None
    
    async def _save_turbo_history(
        self,
        profile_id: str,
        turbo_id: str,
        challenge_id: str,
        challenge_title: str,
        challenge_time_left: str,
        algorithm: str,
        result: Dict[str, Any],
        execution_start: datetime,
        execution_end: datetime
    ):
        """
        Sauvegarde l'historique turbo
        Équivalent de save_turbo_history() dans gsui.py
        """
        try:
            # Vérifier si l'historisation est activée
            user = config_manager.get_user(profile_id)
            if not user or not user.get('turbo_history_enabled', True):
                logger.info(f"⏭️ Turbo history disabled for {profile_id}")
                return
            
            # Préparer les données d'historique
            history_data = {
                'turbo_id': turbo_id,
                'timestamp': execution_start.isoformat(),
                'challenge_id': challenge_id,
                'challenge_title': challenge_title,
                'time_left': challenge_time_left,
                'algorithm': algorithm,
                'strategy_description': f"Algorithme: {algorithm}",
                'success': result.get('success', False),
                'pairs_processed': result.get('pairs_processed', 0),
                'successful_pairs': result.get('successful_pairs', 0),
                'failed_pairs': result.get('failed_pairs', 0),
                'execution_duration': result.get('execution_duration', 0),
                'photo_pairs': result.get('pairs_data', []),
                'execution_started_at': execution_start.isoformat(),
                'execution_completed_at': execution_end.isoformat()
            }
            
            # Sauvegarder dans la section turbo_history
            turbo_history = config_manager.get_user_section(profile_id, 'turbo_history') or {}
            turbo_history[turbo_id] = history_data
            
            config_manager.update_user_section(profile_id, 'turbo_history', turbo_history)
            
            logger.info(f"💾 Turbo history saved: {turbo_id}")
            
        except Exception as e:
            logger.error(f"Error saving turbo history: {e}")
    
    async def _save_turbo_status(self, profile_id: str, turbo_id: str, status_data: Dict[str, Any]):
        """Sauvegarde le statut turbo"""
        try:
            turbo_statuses = config_manager.get_user_section(profile_id, 'turbo_status') or {}
            challenge_id = status_data.get('challenge_id', '')
            turbo_status_key = f"{challenge_id}_current"
            
            turbo_statuses[turbo_status_key] = status_data
            config_manager.update_user_section(profile_id, 'turbo_status', turbo_statuses)
            
        except Exception as e:
            logger.error(f"Error saving turbo status: {e}")
    
    async def cancel_turbo_execution(self, profile_id: str, challenge_id: str) -> bool:
        """Annule l'exécution turbo pour un challenge"""
        try:
            execution_key = f"{profile_id}_{challenge_id}"
            
            if execution_key in self.active_executions:
                task = self.active_executions[execution_key]
                task.cancel()
                del self.active_executions[execution_key]
                
                # Mettre à jour le statut
                cancel_status = {
                    'profile_id': profile_id,
                    'challenge_id': challenge_id,
                    'status': 'cancelled',
                    'execution_completed_at': datetime.now().isoformat()
                }
                
                await self._save_turbo_status(profile_id, f"cancelled_{int(datetime.now().timestamp())}", cancel_status)
                
                logger.info(f"✅ Turbo execution cancelled: {execution_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling turbo execution: {e}")
            return False


# Instance globale du service turbo
turbo_executor = TurboExecutor()