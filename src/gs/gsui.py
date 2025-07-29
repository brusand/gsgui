import argparse
import sys
import asyncio
import threading
import os
import requests
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

import qasync
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QListWidgetItem, QCheckBox, QLabel,
                               QComboBox, QPushButton, QFrame, QTextEdit, QSplitter, QApplication, QTableWidget,
                               QHeaderView, QTableWidgetItem, QDialog, QDialogButtonBox, QTabWidget,
                               QInputDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QMetaObject, Q_ARG
import aiohttp
from datetime import datetime, timedelta, time

from configobj import ConfigObj
from qasync import QEventLoop, asyncSlot

from PySide6.QtGui import QFont, QTextCursor
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Importer les algorithmes d'ensemble
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append('.')  # Ajouter le répertoire courant
    from ensemble_algorithms import ensemble_vote, hybrid_algorithm, ratio_low_algorithm, votes_high_algorithm, random_algorithm
    from position_aware_algorithm import position_aware_algorithm
    from adaptive_time_algorithm import adaptive_time_algorithm
    from bruno_custom_refined import bruno_custom_refined
    ENSEMBLE_AVAILABLE = True
    print("✅ Modules d'ensemble importés avec succès")
except ImportError as e:
    print(f"⚠️ Impossible d'importer les modules d'ensemble: {e}")
    ENSEMBLE_AVAILABLE = False

class GurushotChallenge:
    def __init__(self, id, title, end_time, time_left, url, votes, rank, level, exposure, gps, challenge):
        self.id = id
        self.title = title
        self.end_time = end_time
        self.time_left = time_left
        self.url = url
        self.votes = votes
        self.rank = rank,
        self.level = level,
        self.exposure = exposure,
        self.gps = gps,
        self.selected_strategy = None
        self.status = ""
        self.challenge = challenge
        self.current_process_id = None
        self.process_start_time = None
        self.turbo_status = ""  # Statut turbo: "" par défaut, "success" après turbo

class AsyncFetcher(QObject):
    finished = Signal(list)
    vote_finished = Signal(str)
    get_votes_panel_finished = Signal(object, object, int)
    post_votes_panel_finished = Signal(object, object)
    turbo_finished = Signal(str, bool)  # (challenge_id, success)
    turbo_log = Signal(str)  # (log_message)
    turbo_scores_update = Signal(str, str, int, int)  # (first_id, second_id, first_score, second_score)
    turbo_history_save = Signal(str, str, str, str, object, str, object, str, str, str, bool)  # (challenge_id, challenge_title, time_left, first_id, first_data, second_id, second_data, winner_id, algorithm, strategy_description, success)

    def __init__(self, header, config=None, player=None):
        super().__init__()
        self.aio_header = header
        self.config = config
        self.player = player

    async def fetch_challenges(self):
        """VERSION FONCTIONNELLE copiée depuis gsgui.py"""
        try:
            print(f"🔍 Fetching challenges avec headers: {self.aio_header}")
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/get_my_active_challenges') as response:
                    print(f"📡 Response status: {response.status}")
                    
                    if response.status != 200:
                        print(f"❌ API Error: Status {response.status}")
                        self.finished.emit([])
                        return
                    
                    data = await response.json()
                    print(f"📊 JSON data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    challenges = []
                    for challenge_data in data.get('challenges', []):
                        timeleft = challenge_data['time_left']
                        challenge = GurushotChallenge(
                            id=challenge_data['id'],
                            title=challenge_data['title'],
                            end_time=datetime.fromtimestamp(challenge_data["close_time"]).strftime("%d/%m/%Y, %H:%M"),
                            time_left="{}D {}H {}M {}S".format(timeleft["days"], timeleft["hours"], timeleft["minutes"], timeleft["seconds"]),
                            url=challenge_data['url'],
                            exposure=int(challenge_data['member']['ranking']['total']['exposure']),
                            votes=int(challenge_data['member']['ranking']['total']['votes']),
                            rank=int(challenge_data['member']['ranking']['total']['rank']),
                            level=challenge_data['member']['ranking']['total']['level_name'],
                            gps=int(0),
                            challenge=challenge_data
                        )
                        challenges.append(challenge)
                    
                    print(f"✅ Successfully processed {len(challenges)} challenges")
                    self.finished.emit(challenges)
        except Exception as e:
            print(f"❌ Error fetching challenges: {e}")
            print(f"❌ Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit([])
    
    async def get_votes_panel(self, challenge, vote_count):
        """Récupère le panel de votes pour un challenge - VERSION FONCTIONNELLE"""
        try:
            # Vérifier que le challenge a une URL valide
            if not hasattr(challenge, 'url') or not challenge.url:
                error_result = {"success": False, "message": "Challenge URL is missing or invalid"}
                self.get_votes_panel_finished.emit(challenge, error_result, -1 * vote_count)
                return

            print(f"🔄 Récupération données de vote pour {challenge.title} (URL: {challenge.url})")

            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/get_vote_data',
                                        data={'limit': 100, 'url': challenge.url}) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # Vérifier que la réponse contient bien des images
                            if not result.get('images') or len(result.get('images', [])) == 0:
                                print(f"❌ Pas d'images disponibles pour {challenge.title}")
                                self.get_votes_panel_finished.emit(challenge,
                                                                   {"success": False, "message": "No images available",
                                                                    "challenge": {"close_time": 0}}, -1 * vote_count)
                            else:
                                print(f"✅ {len(result.get('images', []))} images trouvées pour {challenge.title}")
                                self.get_votes_panel_finished.emit(challenge, result, vote_count)
                        except Exception as json_error:
                            error_text = await response.text()
                            print(f"❌ Erreur JSON: {json_error}")
                            self.get_votes_panel_finished.emit(challenge, {"success": False,
                                                                           "message": f"JSON parsing error: {json_error}",
                                                                           "challenge": {"close_time": 0}}, -1 * vote_count)
                    else:
                        error_text = await response.text()
                        print(f"❌ Erreur HTTP {response.status}: {error_text[:100]}...")
                        self.get_votes_panel_finished.emit(challenge, {"success": False,
                                                                       "message": f"HTTP {response.status}: {error_text}",
                                                                       "challenge": {"close_time": 0}}, -1 * vote_count)
        except Exception as e:
            print(f"❌ Exception lors de la récupération des votes: {e}")
            self.get_votes_panel_finished.emit(challenge,
                                               {"success": False, "message": str(e), "challenge": {"close_time": 0}},
                                               -1 * vote_count)
    
    async def post_votes_panel(self, challenge, panel_data, vote_count):
        """Soumet les votes pour un challenge - VERSION FONCTIONNELLE"""
        try:
            # Extraire les tokens d'images du panel
            if not panel_data.get('images'):
                error_result = {"success": False, "message": "No images in panel data"}
                self.post_votes_panel_finished.emit(challenge, error_result)
                return

            # Prendre les premiers tokens d'images disponibles selon le nombre demandé
            images = panel_data.get('images', [])
            votes = []
            for img in images[:vote_count]:  # Utiliser le nombre de votes demandé
                if 'token' in img:
                    votes.append(img['token'])

            if not votes:
                error_result = {"success": False, "message": "No valid image tokens found"}
                self.post_votes_panel_finished.emit(challenge, error_result)
                return

            # Créer le payload avec les tokens
            payload = {'tokens[' + str(id) + ']': value for id, value in enumerate(votes)}
            payload.update({'viewed_tokens[' + str(id) + ']': value for id, value in enumerate(votes)})
            payload['c_id'] = challenge.id
            payload['c_token'] = "03AOLTBLR8mMuwAHd5TwbZo5KuuMZYDUVbM-gwQZgojsOHPf-NdlccOUjk6DXw6QE3thLUf6ASwqgQigw1-zTLI6-prjlTIS9ByBXVvePZkYXGwf6MDNIielvqiEWTemoMPWkKVSPme0EOALsd0MrbwDFHxbS02LGpt2u9GwieEKurIUmP7IKNxPEVBGwSR9UTDhWLfUimQK-yDKBVzIZYmbiEHM6gw85-9jDbtGtaAKcEGio83U6b4lmaGWVr8jhWYDKW49PDPrlc0hqYoV1nAOMySaIstamSZP56Zzp3ejo_1A0EqMOL1vGaG5aKt8a-tFY26Q9TRROHx8lVNcJoSBuBHFGUzl2n12JLjqAvJd6BcOweUMlhJapSrwSgHpRl5UQJ58G2AkWdMMvkwbplXZCqQ8cdv_HAzduBOwzutsfuubfCk0Fgqfb1wFK1FrfSGyRVhgrmci12xKmiIrIP1ZIOycaCXI7V0-sY5TW94mmjknYGwUiCdNI"

            print(f"🗳️ Soumission de {len(votes)} votes (demandé: {vote_count}) pour {challenge.title}")

            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/submit_votes', data=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Votes soumis avec succès pour {challenge.title}")
                        self.post_votes_panel_finished.emit(challenge, result)
                    else:
                        error_text = await response.text()
                        error_result = {"success": False, "message": f"HTTP {response.status}: {error_text}"}
                        self.post_votes_panel_finished.emit(challenge, error_result)
        except Exception as e:
            print(f"❌ Erreur lors de la soumission des votes: {e}")
            error_result = {"success": False, "message": str(e)}
            self.post_votes_panel_finished.emit(challenge, error_result)
    
    async def turbo_challenge(self, challenge_id, challenge_title=None, challenge_time_left=None):
        """Active le turbo pour un challenge"""
        try:
            print(f"🚀 Activation turbo pour challenge {challenge_id}")
            
            # Étape 1: Récupérer la liste des paires de photos à choisir
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/get_challenge_turbo', 
                                      data={'challenge_id': challenge_id}) as response:
                    if response.status == 200:
                        turbo_data = await response.json()
                        print(f"✅ Données turbo récupérées pour challenge {challenge_id}")
                        
                        # Vérifier que la réponse est valide
                        if turbo_data.get('success') and turbo_data.get('images'):
                            images = turbo_data['images']
                            max_selections = turbo_data.get('max_selections', 10)
                            required_selections = turbo_data.get('required_selections', 6)
                            turbo_unlock_type = turbo_data.get('turbo_unlock_type', 'COINS')
                            
                            # Récupérer et afficher l'algorithme utilisé
                            current_algorithm = self.get_turbo_algorithm()
                            
                            print(f"📊 Turbo info: {len(images)} paires, {required_selections} requis, {max_selections} max, type: {turbo_unlock_type}")
                            print(f"🎯 Algorithme utilisé: {current_algorithm}")
                            self.turbo_log.emit(f"🚀 Début turbo: {len(images)} paires à traiter")
                            self.turbo_log.emit(f"🎯 Algorithme: {current_algorithm}")
                            
                            # Étape 2: Traiter chaque paire séquentiellement
                            success_count = await self.process_turbo_pairs_sequentially(challenge_id, images, challenge_title, challenge_time_left)
                            
                            if success_count >= 6:
                                print(f"🎉 Turbo activé avec succès: {success_count} comparaisons réussies")
                                self.turbo_log.emit(f"🎉 Turbo SUCCESS: {success_count} comparaisons réussies")
                                self.turbo_finished.emit(str(challenge_id), True)
                            else:
                                print(f"❌ Échec turbo: seulement {success_count} comparaisons réussies (6 requis)")
                                self.turbo_log.emit(f"❌ Turbo FAILED: {success_count}/6 comparaisons réussies")
                                self.turbo_finished.emit(str(challenge_id), False)
                            
                        else:
                            print(f"❌ Réponse turbo invalide: {turbo_data}")
                            self.turbo_finished.emit(str(challenge_id), False)
                    else:
                        error_text = await response.text()
                        print(f"❌ Erreur HTTP turbo {response.status}: {error_text}")
                        self.turbo_finished.emit(str(challenge_id), False)
                        
        except Exception as e:
            print(f"❌ Erreur lors de l'activation turbo: {e}")
            self.turbo_finished.emit(str(challenge_id), False)
    
    async def process_turbo_pairs_sequentially(self, challenge_id, image_pairs, challenge_title=None, challenge_time_left=None):
        """Traite chaque paire séquentiellement jusqu'à 6 succès ou 5 échecs"""
        try:
            success_count = 0
            novote_count = 0
            failure_count = 0
            total_pairs = len(image_pairs)
            required_successes = 6
            max_failures = 4 # 5 de 0 à 4
            
            # Cache des pages consultées pour éviter les re-consultations
            pages_cache = {}  # {start: items}
            
            # Utiliser les infos du challenge passées en paramètre
            if not challenge_title:
                challenge_title = f"Challenge {challenge_id}"
            if not challenge_time_left:
                challenge_time_left = "Inconnu"
            
            print(f"🔄 Traitement séquentiel de {total_pairs} paires (arrêt à {required_successes} succès ou {max_failures} échecs)")
            
            for i, pair in enumerate(image_pairs):
                first_id = pair['first_image']['id']
                second_id = pair['second_image']['id']
                
                print(f"\n📊 Paire {i+1}/{total_pairs}: {first_id} vs {second_id}")
                self.turbo_log.emit(f"📊 Paire {i+1}/{total_pairs}: analyse en cours...")

                # Rechercher les deux photos dans le classement
                first_data = await self.find_photo_in_ranking(challenge_id, first_id, pages_cache)
                second_data = await self.find_photo_in_ranking(challenge_id, second_id, pages_cache)
                
                if first_data and second_data:
                    # Cas 1: Les deux photos sont trouvées - Utiliser l'algorithme configuré
                    winner_id, winner_ratio, loser_ratio, winner_votes, strategy = self.select_turbo_photo(
                        first_id, first_data, second_id, second_data
                    )
                    
                    print(f"   🎯 Algorithme: {strategy}")
                    
                    print(f"   🏆 Choix Algo: {winner_id} (ratio: {winner_ratio}, votes: {winner_votes}) vs perdant (ratio: {loser_ratio})")
                    self.turbo_log.emit(f"🏆 Choix Algo: {winner_id} (ratio: {winner_ratio}, votes: {winner_votes}) vs perdant (ratio: {loser_ratio})")
                    
                    # Arrêter si on a atteint le nombre maximum d'échecs
                    if failure_count < max_failures:
                        # Soumettre la sélection
                        success, actual_winner_id = await self.submit_single_turbo_selection(challenge_id, winner_id, i+1, first_id, second_id, winner_ratio, loser_ratio)
                    else:
                        novote_count += 1
                    # Historiser cette comparaison - utiliser le vrai gagnant (actual_winner_id)
                    self.turbo_history_save.emit(
                        str(challenge_id), challenge_title, challenge_time_left,
                        first_id, first_data, second_id, second_data,
                        actual_winner_id, self.get_turbo_algorithm(), strategy, success
                    )
                    
                elif first_data or second_data:
                    # Cas 2: Une seule photo trouvée - la choisir automatiquement
                    if first_data:
                        winner_id = first_id
                        winner_ratio = first_data.get('ratio', 0)
                        print(f"   🎯 Choix par défaut: {winner_id} (ratio: {winner_ratio}) - autre photo non trouvée")
                        self.turbo_log.emit(f"🎯 Paire {i+1}: {winner_id} choisi par défaut (ratio: {winner_ratio:.3f}) - autre photo non trouvée")
                    else:
                        winner_id = second_id
                        winner_ratio = second_data.get('ratio', 0)
                        print(f"   🎯 Choix par défaut: {winner_id} (ratio: {winner_ratio}) - autre photo non trouvée")
                        self.turbo_log.emit(f"🎯 Paire {i+1}: {winner_id} choisi par défaut (ratio: {winner_ratio:.3f}) - autre photo non trouvée")
                    
                    if failure_count < max_failures:
                        # Soumettre la sélection avec ratio unique
                        success, actual_winner_id = await self.submit_single_turbo_selection(challenge_id, winner_id, i+1, first_id, second_id, winner_ratio, None)
                    else:
                        novote_count += 1
                    # Historiser cette comparaison (choix par défaut)
                    strategy_desc = f"choix par défaut - autre photo non trouvée"
                    self.turbo_history_save.emit(
                        str(challenge_id), challenge_title, challenge_time_left,
                        first_id, first_data, second_id, second_data,
                        actual_winner_id, "default", strategy_desc, success
                    )
                    
                else:
                    # Cas 3: Aucune photo trouvée - ignorer cette paire
                    print(f"   ❌ Aucune des deux photos trouvée dans le classement")
                    self.turbo_log.emit(f"❌ Paire {i+1}: aucune photo trouvée - paire ignorée")
                    
                    # Historiser cette comparaison ignorée
                    strategy_desc = "paire ignorée - aucune photo trouvée"
                    self.turbo_history_save.emit(
                        str(challenge_id), challenge_title, challenge_time_left,
                        first_id, first_data, second_id, second_data,
                        None, "ignored", strategy_desc, False
                    )
                    continue
                
                # Traiter le résultat de la soumission (commun aux cas 1 et 2)
                if novote_count == 0 and success:
                    success_count += 1
                    print(f"   ✅ Comparaison réussie ({success_count}/{required_successes})")
                    
                    # Arrêter si on a atteint le nombre requis de succès
                    if success_count >= required_successes:
                        print(f"   🎉 Objectif atteint: {required_successes} comparaisons réussies!")
                        break
                else:
                    failure_count += 1
                    print(f"   ❌ Comparaison échouée ({failure_count}/{max_failures})")
                    
                    # Arrêter si on a atteint le nombre maximum d'échecs
                    #if failure_count >= max_failures:
                    #    print(f"   🛑 Arrêt: {max_failures} échecs atteints!")
                    #    self.turbo_log.emit(f"🛑 Turbo arrêté: {max_failures} échecs consécutifs")
                    #    break
                
                # Petite pause entre les paires
                if i < total_pairs - 1:
                    await asyncio.sleep(0.2)
            
            print(f"\n🎯 Traitement terminé: {success_count}/{required_successes} succès, {failure_count} échecs")
            return success_count
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement séquentiel: {e}")
            return 0
    
    def get_turbo_algorithm(self):
        """Récupère l'algorithme turbo configuré pour ce profil"""
        try:
            # Debug: vérifier que config et player sont disponibles
            if not self.config or not self.player:
                print(f"❌ AsyncFetcher: config={self.config is not None}, player={self.player}")
                return "bruno_custom"
                
            # Vérifier la config du profil
            if self.config['players'].get(self.player) and self.config['players'][self.player].get('turbo_algorithm'):
                algo = self.config['players'][self.player]['turbo_algorithm']
                print(f"🔧 DEBUG AsyncFetcher: Algorithme lu depuis config: {algo}")
                return algo
            
            # Valeur par défaut - Ensemble optimal basé sur feedback utilisateur en temps réel
            print(f"🔧 DEBUG AsyncFetcher: Utilisation ensemble par défaut mis à jour")
            return "[hybrid,position_aware,adaptive_time]"
        except Exception as e:
            print(f"❌ Erreur AsyncFetcher get_turbo_algorithm: {e}")
            return "[hybrid,ratio_low,votes_high]"
    
    def decide_turbo_choice(self, algorithm, first_id, first_data, second_id, second_data):
        """DECISION PURE: Choisit entre deux photos selon l'algorithme ou ensemble d'algorithmes
        
        Retourne: (winner_id, winner_ratio, loser_ratio, winner_votes, strategy_description)
        Cette méthode est PURE - pas de soumission, juste la décision.
        """
        # Données communes pour debug
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        first_rank = first_data.get('rank', 999)
        second_rank = second_data.get('rank', 999)
        
        print(f"   📊 Données: Photo1(votes:{first_votes}, rang:{first_rank}, ratio:{first_ratio}) vs Photo2(votes:{second_votes}, rang:{second_rank}, ratio:{second_ratio})")
        print(f"   🤖 Algorithme sélectionné: {algorithm}")
        
        # === GESTION DES ENSEMBLES D'ALGORITHMES ===
        if algorithm.startswith('[') and algorithm.endswith(']') and ENSEMBLE_AVAILABLE:
            try:
                # Parser l'ensemble: [algo1,algo2,algo3]
                algo_list = [algo.strip() for algo in algorithm[1:-1].split(',')]
                print(f"   🗳️ Ensemble détecté: {algo_list}")
                
                # Appliquer le vote majoritaire
                majority_choice, individual_choices, vote_details, majority_reason = ensemble_vote(
                    first_id, first_data, second_id, second_data, algo_list
                )
                
                # Déterminer les ratios et votes du gagnant
                if majority_choice == first_id:
                    winner_ratio, loser_ratio = first_ratio, second_ratio
                    winner_votes = first_votes
                else:
                    winner_ratio, loser_ratio = second_ratio, first_ratio
                    winner_votes = second_votes
                
                # Créer la description de stratégie
                strategy_desc = f"Vote majoritaire {majority_reason}"
                print(f"   📊 Détail votes: {individual_choices}")
                print(f"   🏆 Gagnant majoritaire: {majority_choice}")
                
                return majority_choice, winner_ratio, loser_ratio, winner_votes, strategy_desc
                
            except Exception as e:
                print(f"   ❌ Erreur ensemble: {e}, fallback sur bruno_custom")
                return self._algo_bruno_custom(first_id, first_data, second_id, second_data)
        
        # === ALGORITHMES INDIVIDUELS ===
        # Nouveaux algorithmes optimisés d'abord
        if algorithm == "hybrid" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, reason = hybrid_algorithm(first_id, first_data, second_id, second_data)
                if winner_id == first_id:
                    return first_id, first_ratio, second_ratio, first_votes, f"hybrid: {reason}"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"hybrid: {reason}"
            except:
                return self._algo_hybrid(first_id, first_data, second_id, second_data)
        
        elif algorithm == "ratio_low" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, reason = ratio_low_algorithm(first_id, first_data, second_id, second_data)
                if winner_id == first_id:
                    return first_id, first_ratio, second_ratio, first_votes, f"ratio_low: {reason}"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"ratio_low: {reason}"
            except:
                return self._algo_ratio_low(first_id, first_data, second_id, second_data)
        
        elif algorithm == "votes_high" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, reason = votes_high_algorithm(first_id, first_data, second_id, second_data)
                if winner_id == first_id:
                    return first_id, first_ratio, second_ratio, first_votes, f"votes_high: {reason}"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"votes_high: {reason}"
            except:
                return self._algo_votes_high(first_id, first_data, second_id, second_data)
        
        elif algorithm == "random" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, reason = random_algorithm(first_id, first_data, second_id, second_data)
                if winner_id == first_id:
                    return first_id, first_ratio, second_ratio, first_votes, f"random: {reason}"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"random: {reason}"
            except:
                return self._algo_random(first_id, first_data, second_id, second_data)
        
        elif algorithm == "bruno_custom" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, reason = bruno_custom_refined(
                    first_id, first_data, second_id, second_data
                )
                return winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, f"bruno_custom: {reason}"
            except:
                return self._algo_bruno_custom(first_id, first_data, second_id, second_data)
        
        elif algorithm == "position_aware" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, reason = position_aware_algorithm(
                    first_id, first_data, second_id, second_data
                )
                return winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, f"position_aware: {reason}"
            except Exception as e:
                print(f"   ❌ Erreur position_aware: {e}, fallback sur bruno_custom")
                return self._algo_bruno_custom(first_id, first_data, second_id, second_data)
        
        elif algorithm == "adaptive_time" and ENSEMBLE_AVAILABLE:
            try:
                winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, reason = adaptive_time_algorithm(
                    first_id, first_data, second_id, second_data, time_left="0D 12H 0M 0S"
                )
                return winner_id, winner_ratio_ret, loser_ratio_ret, winner_votes_ret, f"adaptive_time: {reason}"
            except Exception as e:
                print(f"   ❌ Erreur adaptive_time: {e}, fallback sur bruno_custom")
                return self._algo_bruno_custom(first_id, first_data, second_id, second_data)
        
        # Algorithmes legacy
        elif algorithm == "votes_ratio":
            return self._algo_votes_high(first_id, first_data, second_id, second_data)  # Map vers votes_high pour compatibilité
        elif algorithm == "ratio_high":
            return self._algo_ratio_high(first_id, first_data, second_id, second_data)
        elif algorithm == "rank_best":
            return self._algo_rank_best(first_id, first_data, second_id, second_data)
        elif algorithm == "efficiency":
            return self._algo_efficiency(first_id, first_data, second_id, second_data)
        elif algorithm == "ai_optimized":
            return self._algo_ai_optimized(first_id, first_data, second_id, second_data)
        elif algorithm == "advanced_rf":
            return self._algo_advanced_rf(first_id, first_data, second_id, second_data)
        elif algorithm == "votes_ratio_patterns":
            print(f"🎯 EXECUTION: Utilisation de votes_ratio_patterns")
            return self._algo_votes_ratio_patterns(first_id, first_data, second_id, second_data)
        else:
            print(f"🎯 FALLBACK: Algorithme '{algorithm}' non reconnu, utilisation de l'ensemble optimal")
            # Fallback sur l'ensemble optimal
            if ENSEMBLE_AVAILABLE:
                return self.decide_turbo_choice("[hybrid,ratio_low,votes_high]", first_id, first_data, second_id, second_data)
            else:
                return self._algo_bruno_custom(first_id, first_data, second_id, second_data)
    
    def select_turbo_photo(self, first_id, first_data, second_id, second_data):
        """COMPATIBILITÉ: Utilise decide_turbo_choice avec l'algorithme configuré"""
        algorithm = self.get_turbo_algorithm()
        return self.decide_turbo_choice(algorithm, first_id, first_data, second_id, second_data)
    
    def _algo_ratio_low(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choisir le ratio le plus faible
        ⚠️ ATTENTION: D'après analyse historique, ratio plus GRAND = meilleur!
        Cet algorithme est contre-intuitif mais gardé pour compatibilité.
        """
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        
        if first_ratio < second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, f"ratio_low ({first_ratio} < {second_ratio}) ⚠️ contre-intuitif"
        elif second_ratio < first_ratio:
            return second_id, second_ratio, first_ratio, second_votes, f"ratio_low ({second_ratio} < {first_ratio}) ⚠️ contre-intuitif"
        else:
            # Même ratio: plus de votes
            if first_votes >= second_votes:
                return first_id, first_ratio, second_ratio, first_votes, f"ratio_low tie, plus de votes ({first_votes} >= {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ratio_low tie, plus de votes ({second_votes} > {first_votes})"
    
    def _algo_ratio_high(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choisir le ratio le plus élevé
        ✅ CORRECT: D'après analyse historique, ratio plus grand = meilleur!
        """
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        
        if first_ratio > second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, f"ratio_high ({first_ratio} > {second_ratio})"
        elif second_ratio > first_ratio:
            return second_id, second_ratio, first_ratio, second_votes, f"ratio_high ({second_ratio} > {first_ratio})"
        else:
            # Même ratio: plus de votes
            if first_votes >= second_votes:
                return first_id, first_ratio, second_ratio, first_votes, f"ratio_high tie, plus de votes ({first_votes} >= {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ratio_high tie, plus de votes ({second_votes} > {first_votes})"
    
    def _algo_votes_high(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choisir le plus de votes"""
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        
        if first_votes > second_votes:
            return first_id, first_ratio, second_ratio, first_votes, f"votes_high ({first_votes} > {second_votes})"
        elif second_votes > first_votes:
            return second_id, second_ratio, first_ratio, second_votes, f"votes_high ({second_votes} > {first_votes})"
        else:
            # Même votes: ratio le plus faible
            if first_ratio <= second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"votes_high tie, ratio plus faible ({first_ratio} <= {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"votes_high tie, ratio plus faible ({second_ratio} < {first_ratio})"
    
    def _algo_rank_best(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choisir le meilleur rang (plus petit nombre)"""
        first_rank = first_data.get('rank', 999)
        second_rank = second_data.get('rank', 999)
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        
        if first_rank < second_rank:
            return first_id, first_ratio, second_ratio, first_votes, f"rank_best (#{first_rank} < #{second_rank})"
        elif second_rank < first_rank:
            return second_id, second_ratio, first_ratio, second_votes, f"rank_best (#{second_rank} < #{first_rank})"
        else:
            # Même rang: plus de votes
            if first_votes >= second_votes:
                return first_id, first_ratio, second_ratio, first_votes, f"rank_best tie, plus de votes ({first_votes} >= {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"rank_best tie, plus de votes ({second_votes} > {first_votes})"
    
    def _algo_efficiency(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choisir le meilleur ratio votes/rang"""
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        first_rank = first_data.get('rank', 999)
        second_rank = second_data.get('rank', 999)
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        
        first_efficiency = first_votes / first_rank if first_rank > 0 else 0
        second_efficiency = second_votes / second_rank if second_rank > 0 else 0
        
        if first_efficiency > second_efficiency:
            return first_id, first_ratio, second_ratio, first_votes, f"efficiency ({first_efficiency:.4f} > {second_efficiency:.4f})"
        elif second_efficiency > first_efficiency:
            return second_id, second_ratio, first_ratio, second_votes, f"efficiency ({second_efficiency:.4f} > {first_efficiency:.4f})"
        else:
            # Même efficacité: ratio le plus faible
            if first_ratio <= second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"efficiency tie, ratio plus faible ({first_ratio} <= {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"efficiency tie, ratio plus faible ({second_ratio} < {first_ratio})"
    
    def _algo_hybrid(self, first_id, first_data, second_id, second_data):
        """Algorithme: Stratégie hybride avec filtres (ancien algorithme)"""
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        first_rank = first_data.get('rank', 999)
        second_rank = second_data.get('rank', 999)
        
        # Score efficacité
        first_score = first_votes / first_rank if first_rank > 0 else 0
        second_score = second_votes / second_rank if second_rank > 0 else 0
        
        # Filtres de sécurité
        first_valid = first_votes >= 200 and first_rank <= 550
        second_valid = second_votes >= 200 and second_rank <= 550
        
        if not first_valid and not second_valid:
            # Fallback: ratio faible
            if first_ratio <= second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"hybrid fallback ratio faible ({first_ratio} <= {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"hybrid fallback ratio faible ({second_ratio} < {first_ratio})"
        elif first_valid and not second_valid:
            return first_id, first_ratio, second_ratio, first_votes, f"hybrid seule photo1 valide"
        elif second_valid and not first_valid:
            return second_id, second_ratio, first_ratio, second_votes, f"hybrid seule photo2 valide"
        else:
            # Les deux valides: meilleur score
            if first_score >= second_score:
                return first_id, first_ratio, second_ratio, first_votes, f"hybrid meilleur score ({first_score:.4f} >= {second_score:.4f})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"hybrid meilleur score ({second_score:.4f} > {first_score:.4f})"
    
    def _algo_random(self, first_id, first_data, second_id, second_data):
        """Algorithme: Choix aléatoire"""
        import random
        
        first_ratio = first_data.get('ratio', 0)
        second_ratio = second_data.get('ratio', 0)
        first_votes = first_data.get('votes', 0)
        second_votes = second_data.get('votes', 0)
        
        if random.choice([True, False]):
            return first_id, first_ratio, second_ratio, first_votes, "random (photo1 choisie)"
        else:
            return second_id, second_ratio, first_ratio, second_votes, "random (photo2 choisie)"

    def _algo_bruno_custom(self, first_id, first_data, second_id, second_data):
        """
        Algorithme Bruno Custom Affiné - Version 2.0
        Basé sur analyses statistiques de 459 pairs historiques:
        - 265 pairs ratio ~1.5: votes (53.2%) > ratio élevé (44.9%) > rang (38.9%)
        - 194 pairs split ≥1.5 vs <1.5: équilibré 52.1% vs 47.9%, compensation cruciale
        """
        def safe_float(val, default=0.0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default
        
        first_ratio = safe_float(first_data.get('ratio', 0))
        second_ratio = safe_float(second_data.get('ratio', 0))
        first_votes = safe_float(first_data.get('votes', 0))
        second_votes = safe_float(second_data.get('votes', 0))
        first_rank = safe_float(first_data.get('rank', 999))
        second_rank = safe_float(second_data.get('rank', 999))

        # =================== RÈGLE 1: ÉVITER RATIO < 1.0 ===================
        # (Règle universelle - maintenue inchangée)
        if first_ratio < 1.0 and second_ratio >= 1.0:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: éviter <1.0 ({first_ratio} vs {second_ratio})"
        elif second_ratio < 1.0 and first_ratio >= 1.0:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: éviter <1.0 ({second_ratio} vs {first_ratio})"
        elif first_ratio < 1.0 and second_ratio < 1.0:
            # ZONE CRITIQUE: Deux ratios < 1.0 - VOTES prioritaires (70% succès vs 40% ratio)
            votes_diff = abs(first_votes - second_votes)
            
            if votes_diff > 100:  # Différence significative de votes
                if first_votes > second_votes:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: deux<1.0 - votes prioritaires ({first_votes} vs {second_votes})"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: deux<1.0 - votes prioritaires ({second_votes} vs {first_votes})"
            
            # Si votes similaires, prendre le ratio moins pire (plus proche de 1.0)
            if first_ratio >= second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: deux<1.0 - ratio moins pire ({first_ratio} vs {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: deux<1.0 - ratio moins pire ({second_ratio} vs {first_ratio})"

        # =================== RÈGLE 2: CAS SPÉCIAL RATIO ~1.5 ===================
        # Analyse: 265 pairs avec ratio ~1.5 - VOTES prioritaires (53.2% succès)
        both_near_15 = (abs(first_ratio - 1.5) <= 0.1 and abs(second_ratio - 1.5) <= 0.1)
        
        if both_near_15:
            # Dans la zone 1.5, les VOTES sont le facteur #1 (53.2% vs 44.9% ratio)
            votes_diff = abs(first_votes - second_votes)
            
            if votes_diff > 100:  # Différence significative
                if first_votes > second_votes:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - votes prioritaires ({first_votes} vs {second_votes})"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - votes prioritaires ({second_votes} vs {first_votes})"
            
            # Si votes similaires dans zone 1.5, utiliser ratio élevé (facteur #2)
            ratio_diff = abs(first_ratio - second_ratio)
            if ratio_diff > 0.05:
                if first_ratio > second_ratio:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - ratio élevé ({first_ratio} vs {second_ratio})"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - ratio élevé ({second_ratio} vs {first_ratio})"
            
            # Fallback zone 1.5: rang (facteur #3 - 38.9%)
            if first_rank < second_rank:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: zone1.5 - fallback rang ({first_rank} vs {second_rank})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: zone1.5 - fallback rang ({second_rank} vs {first_rank})"

        # =================== RÈGLE 3: CAS SPÉCIAL SPLIT ≥1.5 vs <1.5 ===================
        # Analyse: 194 pairs split - Combat équilibré mais compensation massive efficace
        split_15 = ((first_ratio >= 1.5 and second_ratio < 1.5) or (second_ratio >= 1.5 and first_ratio < 1.5))
        
        if split_15:
            # Identifier qui a le ratio élevé/faible
            if first_ratio >= 1.5:
                high_ratio_votes, low_ratio_votes = first_votes, second_votes
                high_ratio_rank, low_ratio_rank = first_rank, second_rank
                high_is_first = True
            else:
                high_ratio_votes, low_ratio_votes = second_votes, first_votes
                high_ratio_rank, low_ratio_rank = second_rank, first_rank
                high_is_first = False
            
            # Détecter compensation massive par basse ratio (69.9% succès quand ça compense)
            massive_votes_compensation = low_ratio_votes > high_ratio_votes * 2
            massive_rank_compensation = low_ratio_rank < high_ratio_rank * 0.3  # Rang excellent
            
            if massive_votes_compensation or massive_rank_compensation:
                # Basse ratio compense massivement
                if high_is_first:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - compensation massive (votes:{low_ratio_votes} vs {high_ratio_votes})"
                else:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - compensation massive (votes:{low_ratio_votes} vs {high_ratio_votes})"
            
            # Détecter triple avantage haute ratio (79% succès)
            triple_advantage = (high_ratio_votes > low_ratio_votes and high_ratio_rank < low_ratio_rank)
            
            if triple_advantage:
                # Haute ratio a triple avantage
                if high_is_first:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - triple avantage ratio+votes+rang"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - triple avantage ratio+votes+rang"
            
            # Split équilibré: léger avantage au ratio élevé (52.1% vs 47.9%)
            if high_is_first:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split1.5 - léger avantage ratio élevé"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split1.5 - léger avantage ratio élevé"

        # =================== RÈGLE 4: CAS SPÉCIAL RATIO TRÈS ÉLEVÉ ≥2.0 ===================
        # Analyse: 25 pairs split 2.0 - Combat équilibré 52% vs 48%, compensation critique
        very_high_ratio_split = ((first_ratio >= 2.0 and second_ratio < 2.0) or (second_ratio >= 2.0 and first_ratio < 2.0))
        
        if very_high_ratio_split:
            # Identifier qui a le ratio très élevé/normal
            if first_ratio >= 2.0:
                very_high_votes, normal_votes = first_votes, second_votes
                very_high_rank, normal_rank = first_rank, second_rank
                very_high_is_first = True
            else:
                very_high_votes, normal_votes = second_votes, first_votes
                very_high_rank, normal_rank = second_rank, first_rank
                very_high_is_first = False
            
            # Détecter compensation massive par ratio normal (33% succès)
            massive_votes_comp = normal_votes > very_high_votes * 2
            massive_rank_comp = normal_rank < very_high_rank * 0.5
            
            if massive_votes_comp or massive_rank_comp:
                # Ratio normal compense massivement
                if very_high_is_first:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split2.0 - compensation massive vs ratio très élevé"
                else:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split2.0 - compensation massive vs ratio très élevé"
            
            # Détecter double/triple avantage ratio très élevé (77% ont meilleur rang)
            double_advantage = (very_high_votes >= normal_votes and very_high_rank < normal_rank)
            
            if double_advantage:
                # Ratio très élevé a double avantage
                if very_high_is_first:
                    return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split2.0 - double avantage ratio très élevé"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split2.0 - double avantage ratio très élevé"
            
            # Split équilibré: légère préférence ratio très élevé (52% vs 48%)
            if very_high_is_first:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: split2.0 - légère préférence ratio très élevé"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: split2.0 - légère préférence ratio très élevé"

        # =================== RÈGLE 5: LOGIQUE CLASSIQUE BRUNO ===================
        # (Pour tous les autres cas non couverts par les analyses spéciales)
        
        # Si différence de ratio significative (> 0.1), privilégier le plus élevé
        ratio_diff = abs(first_ratio - second_ratio)
        if ratio_diff > 0.1:
            if first_ratio > second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: ratio supérieur classique ({first_ratio} vs {second_ratio})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: ratio supérieur classique ({second_ratio} vs {first_ratio})"

        # Si ratios similaires, utiliser le meilleur rang
        rank_diff = abs(first_rank - second_rank)
        if rank_diff > 50:  # Seuil significatif
            if first_rank < second_rank:
                return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: meilleur rang classique ({first_rank} vs {second_rank})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: meilleur rang classique ({second_rank} vs {first_rank})"

        # Fallback: plus de votes
        if first_votes > second_votes:
            return first_id, first_ratio, second_ratio, first_votes, f"bruno_v2: plus de votes fallback ({first_votes} vs {second_votes})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"bruno_v2: plus de votes fallback ({second_votes} vs {first_votes})"

    def _algo_ai_optimized(self, first_id, first_data, second_id, second_data):
        """Algorithme IA optimisé - 58.4% de précision (vs 53.8% Bruno Custom)
        
        Basé sur l'analyse de 413 comparaisons historiques avec règles découvertes par IA
        """
        def safe_float(val, default=0.0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default
        
        first_ratio = safe_float(first_data.get('ratio', 0))
        second_ratio = safe_float(second_data.get('ratio', 0))
        first_votes = safe_float(first_data.get('votes', 0))
        second_votes = safe_float(second_data.get('votes', 0))
        first_rank = safe_float(first_data.get('rank', 999))
        second_rank = safe_float(second_data.get('rank', 999))
        
        # RÈGLE 1: Différence de rang importante (feature la plus importante: 17.2%)
        rank_diff = abs(first_rank - second_rank)
        if rank_diff > 300:
            if first_rank < second_rank:
                return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: meilleur rang ({first_rank} vs {second_rank})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: meilleur rang ({second_rank} vs {first_rank})"
        
        # RÈGLE 2: Différence de votes importante (16.3%)
        votes_diff = abs(first_votes - second_votes)
        if votes_diff > 500:
            if first_votes > second_votes:
                return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: plus de votes ({first_votes} vs {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: plus de votes ({second_votes} vs {first_votes})"
        
        # RÈGLE 3A: Pattern découvert 1.3 vs 1.5 (55.7% succès pour 1.5)
        # TOUJOURS favoriser celui qui a le ratio proche de 1.5
        first_is_1_3 = 1.25 <= first_ratio <= 1.35
        second_is_1_3 = 1.25 <= second_ratio <= 1.35
        first_is_1_5 = 1.45 <= first_ratio <= 1.55
        second_is_1_5 = 1.45 <= second_ratio <= 1.55
        
        if (first_is_1_3 and second_is_1_5):
            return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: pattern 1.3vs1.5 - favoriser 1.5 ({second_ratio})"
        elif (first_is_1_5 and second_is_1_3):
            return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: pattern 1.5vs1.3 - favoriser 1.5 ({first_ratio})"
        
        # RÈGLE 3B: Pattern découvert 1.5 vs 1.8 (88.9% succès pour 1.8)
        if (1.4 <= first_ratio <= 1.6) and (1.7 <= second_ratio <= 1.9):
            return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: pattern 1.5vs1.8 - favoriser 1.8 ({second_ratio})"
        elif (1.7 <= first_ratio <= 1.9) and (1.4 <= second_ratio <= 1.6):
            return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: pattern 1.8vs1.5 - favoriser 1.8 ({first_ratio})"
        
        # RÈGLE 4A: Cas spécial - deux ratios sous 1.0 (Photo2 gagne 85.7%)
        if first_ratio < 1.0 and second_ratio < 1.0:
            if abs(first_votes - second_votes) > 50:
                if first_votes > second_votes:
                    return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: sous1.0 mais plus de votes ({first_votes} vs {second_votes})"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: sous1.0 mais plus de votes ({second_votes} vs {first_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: pattern sous1.0 - Photo2 par défaut (85.7%)"
        
        # RÈGLE 4B: Un seul ratio sous 1.0 - éviter sauf votes massifs
        elif first_ratio < 1.0 and second_ratio >= 1.0:
            if first_votes > second_votes * 3:
                return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: exception sous1.0 - votes 3x supérieurs ({first_votes} vs {second_votes})"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: éviter sous1.0 ({first_ratio} vs {second_ratio})"
        elif second_ratio < 1.0 and first_ratio >= 1.0:
            if second_votes > first_votes * 3:
                return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: exception sous1.0 - votes 3x supérieurs ({second_votes} vs {first_votes})"
            else:
                return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: éviter sous1.0 ({second_ratio} vs {first_ratio})"
        
        # RÈGLE 5: Zone danger 1.5 (confirmée par IA)
        first_danger = abs(first_ratio - 1.5) < 0.1
        second_danger = abs(second_ratio - 1.5) < 0.1
        if first_danger and not second_danger:
            return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: éviter zone danger 1.5 ({first_ratio})"
        elif second_danger and not first_danger:
            return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: éviter zone danger 1.5 ({second_ratio})"
        
        # Fallback: ratio plus ÉLEVÉ (logique corrigée après analyse historique)
        if first_ratio >= second_ratio:
            return first_id, first_ratio, second_ratio, first_votes, f"ai_optimized: fallback ratio plus élevé ({first_ratio} >= {second_ratio})"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"ai_optimized: fallback ratio plus élevé ({second_ratio} > {first_ratio})"

    def _algo_advanced_rf(self, first_id, first_data, second_id, second_data):
        """Algorithme Random Forest Avancé - 88.1% de précision
        
        Utilise un modèle Random Forest avec 55 features engineered
        Basé sur l'analyse de 413 comparaisons avec cross-validation 68.8%
        """
        try:
            import pandas as pd
            import pickle
            
            # Charger le modèle Random Forest
            try:
                if not hasattr(self, '_rf_model'):
                    with open('turbo_rf_model.pkl', 'rb') as f:
                        model_data = pickle.load(f)
                        self._rf_model = model_data['model']
                        self._rf_feature_names = model_data['feature_names']
            except FileNotFoundError:
                # Fallback si modèle pas trouvé
                return self._algo_ai_optimized(first_id, first_data, second_id, second_data)
            except Exception as e:
                self.log(f"⚠️ Erreur chargement modèle RF: {e}")
                return self._algo_ai_optimized(first_id, first_data, second_id, second_data)
            
            # Créer les features pour le modèle
            features = self._create_rf_features(first_data, second_data)
            
            # Prédiction
            X = pd.DataFrame([features], columns=self._rf_feature_names)
            prediction = self._rf_model.predict(X)[0]
            probabilities = self._rf_model.predict_proba(X)[0]
            confidence = max(probabilities)
            
            # Choisir le gagnant
            if prediction == 1:  # Photo1 gagne
                chosen_id = first_id
                chosen_ratio = first_data.get('ratio', 0)
                other_ratio = second_data.get('ratio', 0)
                chosen_votes = first_data.get('votes', 0)
                reason = f"advanced_rf: Photo1 (conf:{confidence:.3f})"
            else:  # Photo2 gagne
                chosen_id = second_id
                chosen_ratio = second_data.get('ratio', 0)
                other_ratio = first_data.get('ratio', 0)
                chosen_votes = second_data.get('votes', 0)
                reason = f"advanced_rf: Photo2 (conf:{confidence:.3f})"
            
            return chosen_id, chosen_ratio, other_ratio, chosen_votes, reason
            
        except Exception as e:
            self.log(f"⚠️ Erreur Advanced RF: {e}, fallback vers AI Optimized")
            return self._algo_ai_optimized(first_id, first_data, second_id, second_data)
    
    def _create_rf_features(self, photo1_data, photo2_data):
        """Crée les features pour le modèle Random Forest"""
        def safe_float(val, default=0.0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default
        
        # Données de base
        r1 = safe_float(photo1_data.get('ratio', 0))
        r2 = safe_float(photo2_data.get('ratio', 0))
        v1 = safe_float(photo1_data.get('votes', 0))
        v2 = safe_float(photo2_data.get('votes', 0))
        rank1 = safe_float(photo1_data.get('rank', 999))
        rank2 = safe_float(photo2_data.get('rank', 999))
        
        # Éviter divisions par zéro
        r1_safe = max(r1, 0.001)
        r2_safe = max(r2, 0.001)
        v1_safe = max(v1, 1)
        v2_safe = max(v2, 1)
        rank1_safe = max(rank1, 1)
        rank2_safe = max(rank2, 1)
        
        features = {}
        
        # Features de base
        features['ratio_1'] = r1
        features['ratio_2'] = r2
        features['votes_1'] = v1
        features['votes_2'] = v2
        features['rank_1'] = rank1
        features['rank_2'] = rank2
        
        # Différences
        features['ratio_diff'] = r1 - r2
        features['votes_diff'] = v1 - v2
        features['rank_diff'] = rank1 - rank2
        features['ratio_diff_abs'] = abs(r1 - r2)
        features['votes_diff_abs'] = abs(v1 - v2)
        features['rank_diff_abs'] = abs(rank1 - rank2)
        
        # Ratios des métriques
        features['ratio_ratio'] = r1_safe / r2_safe
        features['votes_ratio'] = v1_safe / v2_safe
        features['rank_ratio'] = rank2_safe / rank1_safe
        
        # Features composées importantes
        features['views_est_1'] = v1_safe / r1_safe
        features['views_est_2'] = v2_safe / r2_safe
        features['views_est_ratio'] = features['views_est_1'] / features['views_est_2']
        
        features['perf_score_1'] = v1 * r1
        features['perf_score_2'] = v2 * r2
        features['perf_score_diff'] = features['perf_score_1'] - features['perf_score_2']
        
        features['rank_penalty_1'] = rank1 * r1
        features['rank_penalty_2'] = rank2 * r2
        features['rank_penalty_diff'] = features['rank_penalty_1'] - features['rank_penalty_2']
        
        features['rank_efficiency_1'] = rank1_safe / r1_safe
        features['rank_efficiency_2'] = rank2_safe / r2_safe
        features['rank_efficiency_ratio'] = features['rank_efficiency_2'] / features['rank_efficiency_1']
        
        # Features catégoriques
        def categorize_ratio(r):
            if r < 0.8: return 0
            elif r < 1.0: return 1
            elif r < 1.2: return 2
            elif r < 1.4: return 3
            elif r < 1.6: return 4
            elif r < 2.0: return 5
            else: return 6
        
        features['ratio_cat_1'] = categorize_ratio(r1)
        features['ratio_cat_2'] = categorize_ratio(r2)
        features['ratio_cat_diff'] = features['ratio_cat_1'] - features['ratio_cat_2']
        
        # Similitudes
        features['ratio_similar'] = 1 if abs(r1 - r2) < 0.05 else 0
        features['votes_similar'] = 1 if abs(v1 - v2) < 50 else 0
        features['rank_similar'] = 1 if abs(rank1 - rank2) < 100 else 0
        
        # Statistiques
        features['ratio_mean'] = (r1 + r2) / 2
        features['votes_mean'] = (v1 + v2) / 2
        features['rank_mean'] = (rank1 + rank2) / 2
        features['ratio_min'] = min(r1, r2)
        features['ratio_max'] = max(r1, r2)
        features['votes_max'] = max(v1, v2)
        features['rank_min'] = min(rank1, rank2)
        features['ratio_std'] = abs(r1 - r2) / 2
        features['votes_std'] = abs(v1 - v2) / 2
        features['rank_std'] = abs(rank1 - rank2) / 2
        
        # Features interaction les plus importantes
        features['votes_rank_interaction_1'] = v1_safe / rank1_safe
        features['votes_rank_interaction_2'] = v2_safe / rank2_safe
        features['votes_rank_interaction_ratio'] = features['votes_rank_interaction_1'] / features['votes_rank_interaction_2']
        
        # Score GuruShots hypothétique
        features['guru_score_1'] = (v1_safe / rank1_safe) / r1_safe
        features['guru_score_2'] = (v2_safe / rank2_safe) / r2_safe
        features['guru_score_diff'] = features['guru_score_1'] - features['guru_score_2']
        
        # Avantages spécifiques
        features['photo1_ratio_advantage'] = 1 if r1 < r2 * 0.9 else 0
        features['photo2_ratio_advantage'] = 1 if r2 < r1 * 0.9 else 0
        features['photo1_votes_compensation'] = 1 if (v1 > v2 * 2 and r1 > r2) else 0
        features['photo2_votes_compensation'] = 1 if (v2 > v1 * 2 and r2 > r1) else 0
        features['photo1_rank_advantage'] = 1 if rank1 < rank2 * 0.7 else 0
        features['photo2_rank_advantage'] = 1 if rank2 < rank1 * 0.7 else 0
        
        return features

    def _algo_votes_ratio_patterns(self, first_id, first_data, second_id, second_data):
        """
        Algorithme basé sur l'analyse des rapports votes/ratio
        
        Découvertes clés de l'analyse de 378 cas valides:
        - Rapport votes < 0.2: MAX votes gagne 93.3% (14/15)
        - Rapport votes < 0.3: MAX votes gagne 76.2% (32/42)  
        - Pattern dominant: Double domination (MAX votes + MAX ratio) = 38.9%
        - Zone équilibrée (0.6-0.8): MAX votes gagne 75.6% (68/90)
        """
        
        def safe_float(val, default=0.0):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default
        
        first_votes = safe_float(first_data.get('votes', 0))
        second_votes = safe_float(second_data.get('votes', 0))
        first_ratio = safe_float(first_data.get('ratio', 0))
        second_ratio = safe_float(second_data.get('ratio', 0))
        first_rank = safe_float(first_data.get('rank', 999))
        second_rank = safe_float(second_data.get('rank', 999))
        
        # Éviter les données invalides
        if first_votes <= 0 or second_votes <= 0 or first_ratio <= 0 or second_ratio <= 0:
            # Fallback vers Bruno Custom
            if first_ratio > second_ratio:
                return first_id, first_ratio, second_ratio, first_votes, "pattern: fallback ratio (données invalides)"
            else:
                return second_id, second_ratio, first_ratio, second_votes, "pattern: fallback ratio (données invalides)"
        
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
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - 93.3% succès"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre extrême votes ({votes_ratio:.3f}) - 93.3% succès"
        
        # =================== RÈGLE 2: DÉSÉQUILIBRE VOTES FORT ===================
        # Rapport votes < 0.3: MAX votes gagne 76.2% (32/42 dans l'analyse)
        if votes_ratio < 0.3:
            if first_has_votes_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - 76.2% succès"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre fort votes ({votes_ratio:.3f}) - 76.2% succès"
        
        # =================== RÈGLE 3: DÉSÉQUILIBRE VOTES MODÉRÉ ===================
        # Rapport votes < 0.4: MAX votes gagne 76.4% (55/72 dans l'analyse)
        if votes_ratio < 0.4:
            if first_has_votes_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - 76.4% succès"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: déséquilibre modéré votes ({votes_ratio:.3f}) - 76.4% succès"
        
        # =================== RÈGLE 4: ZONE ÉQUILIBRÉE - DOMINANCE VOTES ===================
        # Zone équilibrée (0.6-0.8 votes): MAX votes gagne encore 75.6% (68/90)
        if votes_ratio >= 0.6 and votes_ratio <= 0.8:
            if first_has_votes_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes dominant 75.6%"
            else:
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone équilibrée ({votes_ratio:.3f}) - MAX votes dominant 75.6%"
        
        # =================== RÈGLE 5: TRÈS ÉQUILIBRÉ - DOUBLE DOMINATION ===================
        # Zone très équilibrée (0.8-1.0): MAX votes gagne 68.0% (100/147)
        # Pattern double domination prioritaire
        if votes_ratio >= 0.8:
            # Privilégier la double domination (MAX votes + MAX ratio)
            if first_has_votes_max and first_has_ratio_max:
                return first_id, first_ratio, second_ratio, first_votes, f"pattern: double domination photo1 (v:{first_votes:.0f} r:{first_ratio:.3f})"
            elif (not first_has_votes_max) and (not first_has_ratio_max):
                return second_id, second_ratio, first_ratio, second_votes, f"pattern: double domination photo2 (v:{second_votes:.0f} r:{second_ratio:.3f})"
            else:
                # Cas mixte - privilégier MAX votes (68% dans zone très équilibrée)
                if first_has_votes_max:
                    return first_id, first_ratio, second_ratio, first_votes, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes 68%"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"pattern: très équilibré ({votes_ratio:.3f}) - MAX votes 68%"
        
        # =================== RÈGLE 6: CAS INTERMÉDIAIRE ===================
        # Zone modérée (0.4-0.6): MAX votes gagne 60.9% (42/69) - moins dominant
        # Utiliser logique hybride avec ratios
        if votes_ratio >= 0.4 and votes_ratio < 0.6:
            # Analyser les ratios aussi pour les cas modérés
            if ratio_rapport < 0.5:
                # Déséquilibre ratio fort - privilégier MAX ratio
                if first_has_ratio_max:
                    return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone modérée + déséq. ratio ({ratio_rapport:.3f}) - MAX ratio"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone modérée + déséq. ratio ({ratio_rapport:.3f}) - MAX ratio"
            else:
                # Ratios équilibrés - privilégier MAX votes (60.9%)
                if first_has_votes_max:
                    return first_id, first_ratio, second_ratio, first_votes, f"pattern: zone modérée équilibrée - MAX votes 60.9%"
                else:
                    return second_id, second_ratio, first_ratio, second_votes, f"pattern: zone modérée équilibrée - MAX votes 60.9%"
        
        # =================== FALLBACK ===================
        # Si aucun pattern identifié clairement, utiliser double domination
        # (Pattern le plus fréquent: 38.9% des cas)
        if first_has_votes_max and first_has_ratio_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: fallback double domination photo1"
        elif (not first_has_votes_max) and (not first_has_ratio_max):
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: fallback double domination photo2"
        elif first_has_votes_max:
            return first_id, first_ratio, second_ratio, first_votes, f"pattern: fallback MAX votes"
        else:
            return second_id, second_ratio, first_ratio, second_votes, f"pattern: fallback MAX votes"

    async def find_photo_in_ranking(self, challenge_id, photo_id, pages_cache):
        """Trouve une photo dans le classement en utilisant le cache des pages"""
        try:
            print(f"   🔍 Recherche {photo_id} dans le classement...")
            self.turbo_log.emit(f"   🔍 Recherche {photo_id} dans le classement...")

            start = 0
            limit = 100
            
            while start < 5000:  # Limite pour éviter boucle infinie
                # Vérifier si cette page est déjà en cache
                if start in pages_cache:
                    items = pages_cache[start]
                    print(f"     📄 Page {start}-{start+len(items)-1} (depuis cache)")
                else:
                    # Récupérer la page depuis l'API
                    async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                        payload = {
                            'c_id': challenge_id,
                            'filter': 'default',
                            'limit': limit,
                            'start': start
                        }
                        
                        async with session.post('https://api.gurushots.com/rest/get_top_photos', data=payload) as response:
                            if response.status == 200:
                                ranking_data = await response.json()
                                
                                if ranking_data.get('success') and ranking_data.get('items'):
                                    items = ranking_data['items']
                                    pages_cache[start] = items  # Mettre en cache
                                    #print(f"     📄 Page {start}-{start+len(items)-1} (depuis API)")
                                else:
                                    #print(f"     ❌ Réponse invalide à start={start}")
                                    break
                            else:
                                error_text = await response.text()
                                print(f"     ❌ Erreur HTTP {response.status}: {error_text}")
                                break
                
                # Chercher la photo dans cette page
                for item in items:
                    if item['id'] == photo_id:
                        photo_data = {
                            'id': photo_id,
                            'rank': item['rank'],
                            'votes': item.get('votes', 0),
                            'ratio': item.get('ratio', 0),
                            'raw_data': item
                        }
                        print(f"     ✅ Trouvé: {photo_id} → votes: {item['votes']},  rang #{item['rank']}, ratio: {item.get('ratio', 0)}")
                        self.turbo_log.emit(f"     ✅ Trouvé: {photo_id} → votes: {item['votes']}, rang #{item['rank']}, ratio: {item.get('ratio', 0)}")
                        return photo_data
                
                # Si cette page était vide, on arrête
                if len(items) < limit:
                    break
                    
                start += limit
            
            print(f"     ⚠️ Photo {photo_id} non trouvée dans le classement")
            return None
            
        except Exception as e:
            print(f"     ❌ Erreur lors de la recherche: {e}")
            return None
    
    async def submit_single_turbo_selection(self, challenge_id, image_id, pair_number, first_id, second_id, winner_ratio=None, loser_ratio=None, is_retry=False):
        """Soumet une sélection unique et retourne (success, actual_winner_id)
        Si is_retry=True, indique qu'il s'agit d'une resoumission automatique"""
        try:
            retry_prefix = "🔄 RETRY " if is_retry else ""
            print(f"   📤 {retry_prefix}Soumission paire {pair_number}: {image_id}")
            
            if winner_ratio is not None and loser_ratio is not None:
                self.turbo_log.emit(f"📤 {retry_prefix}Soumission paire {pair_number}: {image_id} (ratio: {winner_ratio:.3f}) vs (ratio: {loser_ratio:.3f})")
            elif winner_ratio is not None:
                self.turbo_log.emit(f"📤 {retry_prefix}Soumission paire {pair_number}: {image_id} (ratio: {winner_ratio:.3f}) - choix par défaut")
            else:
                self.turbo_log.emit(f"📤 {retry_prefix}Soumission paire {pair_number}: {image_id}")
            
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                payload = {
                    'challenge_id': challenge_id,
                    'image_id': image_id
                }
                
                async with session.post('https://api.gurushots.com/rest/submit_challenge_turbo_selection', 
                                      data=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            is_successful_selection = result.get('is_successful_selection', False)
                            state = result.get('state', 'UNKNOWN')
                            scores = result.get('scores', {})
                            
                            first_score = scores.get('first_image', 0)
                            second_score = scores.get('second_image', 0)
                            
                            print(f"   📊 Scores: first={first_score}%, second={second_score}%")
                            print(f"   🏁 État: {state}")
                            
                            self.turbo_log.emit(f"📊 Scores: {first_score}% vs {second_score}%")
                            
                            # Émettre signal pour mettre à jour les scores dans le DataFrame
                            self.turbo_scores_update.emit(first_id, second_id, first_score, second_score)
                            
                            # Déterminer le vrai gagnant basé sur les scores
                            actual_winner_id = first_id if first_score >= second_score else second_id
                            
                            if is_successful_selection:
                                success_msg = f"✅ Paire {pair_number} SUCCESS - {image_id} (scores: {first_score}%/{second_score}%)"
                                if is_retry:
                                    success_msg = f"🎯 RETRY SUCCESS! " + success_msg
                                print(f"   ✅ Comparaison réussie: {image_id}")
                                self.turbo_log.emit(success_msg)
                                return True, actual_winner_id
                            else:
                                print(f"   ❌ Comparaison échouée: {image_id} -> Vrai gagnant: {actual_winner_id}")
                                self.turbo_log.emit(f"❌ Paire {pair_number} FAILED - {image_id} (scores: {first_score}%/{second_score}%) - Vrai gagnant: {actual_winner_id}")
                                
                                # 🚀 RETRY AUTOMATIQUE avec le vrai gagnant (sauf si c'est déjà un retry)
                                if not is_retry and actual_winner_id != image_id:
                                    print(f"   🔄 Retry automatique avec le vrai gagnant: {actual_winner_id}")
                                    self.turbo_log.emit(f"🔄 AUTO-RETRY avec vrai gagnant: {actual_winner_id}")
                                    
                                    # Appeler récursivement avec le bon gagnant
                                    retry_success, retry_winner = await self.submit_single_turbo_selection(
                                        challenge_id, actual_winner_id, pair_number, first_id, second_id, 
                                        winner_ratio, loser_ratio, is_retry=True
                                    )
                                    
                                    if retry_success:
                                        return True, retry_winner  # Le retry a réussi !
                                    else:
                                        self.turbo_log.emit(f"💔 RETRY FAILED - Même le vrai gagnant a échoué")
                                
                                return False, actual_winner_id
                        else:
                            error_msg = result.get('message', 'Erreur inconnue')
                            print(f"   ❌ Sélection refusée: {error_msg}")
                            self.turbo_log.emit(f"❌ Paire {pair_number} FAILED - Sélection refusée: {error_msg}")
                            return False, image_id  # Pas de scores disponibles, on garde le choix original
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Erreur HTTP {response.status}: {error_text}")
                        self.turbo_log.emit(f"❌ Paire {pair_number} FAILED - Erreur HTTP {response.status}")
                        return False, image_id  # Pas de scores disponibles, on garde le choix original
                        
        except Exception as e:
            print(f"   ❌ Erreur lors de la soumission: {e}")
            self.turbo_log.emit(f"❌ Paire {pair_number} FAILED - Erreur: {str(e)}")
            return False, image_id  # Pas de scores disponibles, on garde le choix original
    
    async def select_best_photos_from_pairs(self, challenge_id, image_pairs, required_selections):
        """Sélectionne les meilleures photos de chaque paire en optimisant le parcours du classement"""
        try:
            print(f"🔍 Analyse de {len(image_pairs)} paires pour trouver les {required_selections} meilleures")
            
            # Extraire tous les IDs de photos à rechercher
            all_photo_ids = set()
            pair_photos = {}  # {pair_index: [photo_id1, photo_id2]}
            
            for i, pair in enumerate(image_pairs):
                first_id = pair['first_image']['id']
                second_id = pair['second_image']['id']
                all_photo_ids.add(first_id)
                all_photo_ids.add(second_id)
                pair_photos[i] = [first_id, second_id]
            
            print(f"📋 {len(all_photo_ids)} photos uniques à analyser")
            
            # Parcourir le classement pour trouver les positions de nos photos
            photo_rankings = await self.get_photo_rankings(challenge_id, all_photo_ids)
            
            if not photo_rankings:
                print(f"❌ Impossible de récupérer les classements")
                return None
            
            # Déterminer la meilleure photo de chaque paire selon le rang (plus petit = meilleur)
            pair_winners = []
            for i, (first_id, second_id) in pair_photos.items():
                first_rank = photo_rankings.get(first_id, 9999)
                second_rank = photo_rankings.get(second_id, 9999)
                
                # Sélectionner celle avec le meilleur rang (plus petit = meilleur)
                if first_rank <= second_rank:
                    winner_id = first_id
                    winner_rank = first_rank
                else:
                    winner_id = second_id
                    winner_rank = second_rank
                
                pair_winners.append({
                    'pair_index': i,
                    'winner_id': winner_id,
                    'rank': winner_rank,
                    'first_id': first_id,
                    'first_rank': first_rank,
                    'second_id': second_id,
                    'second_rank': second_rank
                })
                
                print(f"   Paire {i}: {first_id}(rang #{first_rank}) vs {second_id}(rang #{second_rank}) → {winner_id}(rang #{winner_rank})")
            
            # Trier par rang croissant et prendre les N meilleures
            pair_winners.sort(key=lambda x: x['rank'])
            best_selections = pair_winners[:required_selections]
            
            print(f"🏆 Top {len(best_selections)} sélections (triées par rang):")
            for sel in best_selections:
                print(f"   Paire {sel['pair_index']}: {sel['winner_id']} (rang #{sel['rank']})")
            
            return best_selections
            
        except Exception as e:
            print(f"❌ Erreur lors de la sélection des paires: {e}")
            return None
    
    async def get_photo_rankings(self, challenge_id, target_photo_ids):
        """Parcourt le classement pour trouver les rangs des photos cibles"""
        try:
            photo_rankings = {}
            found_count = 0
            start = 0
            limit = 50
            target_count = len(target_photo_ids)
            
            print(f"🔍 Recherche de {target_count} photos dans le classement...")
            
            while found_count < target_count and start < 5000:  # Limite pour éviter boucle infinie
                # Appel API get_top_photos
                async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                    payload = {
                        'c_id': challenge_id,
                        'filter': 'default',
                        'limit': limit,
                        'start': start
                    }
                    
                    async with session.post('https://api.gurushots.com/rest/get_top_photos', data=payload) as response:
                        if response.status == 200:
                            ranking_data = await response.json()
                            
                            if ranking_data.get('success') and ranking_data.get('items'):
                                items = ranking_data['items']
                                print(f"   📊 Positions {start}-{start+len(items)-1}: {len(items)} photos")
                                
                                # Vérifier chaque photo de cette page
                                for item in items:
                                    photo_id = item['id']
                                    if photo_id in target_photo_ids and photo_id not in photo_rankings:
                                        photo_rankings[photo_id] = item['rank']
                                        found_count += 1
                                        print(f"   ✅ Trouvé: {photo_id} → rang #{item['rank']} ({item.get('votes', 0)} votes)")
                                
                                # Si on a trouvé toutes nos photos, on peut arrêter
                                if found_count >= target_count:
                                    break
                                    
                                # Si cette page était vide, on arrête
                                if len(items) < limit:
                                    break
                                    
                                start += limit
                            else:
                                print(f"❌ Réponse classement invalide à start={start}")
                                break
                        else:
                            error_text = await response.text()
                            print(f"❌ Erreur HTTP classement {response.status}: {error_text}")
                            break
            
            print(f"🎯 Recherche terminée: {found_count}/{target_count} photos trouvées")
            
            # Attribuer un rang très élevé aux photos non trouvées
            for photo_id in target_photo_ids:
                if photo_id not in photo_rankings:
                    photo_rankings[photo_id] = 9999
                    print(f"   ⚠️ Photo non trouvée: {photo_id} → rang #9999 (par défaut)")
            
            return photo_rankings
            
        except Exception as e:
            print(f"❌ Erreur lors du parcours du classement: {e}")
            return {}
    
    def calculate_vote_view_ratio(self, photo_data):
        """Calcule le ratio votes/views d'une photo"""
        try:
            if not photo_data:
                return 0.0
            
            votes = photo_data.get('votes', 0)
            views = photo_data.get('views', 1)  # Éviter division par zéro
            
            # S'assurer que views n'est pas zéro
            if views == 0:
                views = 1
            
            ratio = votes / views
            return ratio
            
        except Exception as e:
            print(f"⚠️ Erreur calcul ratio: {e}")
            return 0.0
    
    async def submit_turbo_selections(self, challenge_id, selections):
        """Soumet les sélections de photos pour le turbo"""
        try:
            print(f"📤 Soumission de {len(selections)} sélections pour challenge {challenge_id}")
            
            success_count = 0
            total_selections = len(selections)
            
            for i, selection in enumerate(selections):
                winner_id = selection['winner_id']
                pair_index = selection['pair_index']
                rank = selection['rank']
                
                print(f"   📤 Sélection {i+1}/{total_selections}: Paire {pair_index} → {winner_id} (rang #{rank})")
                
                # Soumettre cette sélection
                async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                    payload = {
                        'challenge_id': challenge_id,
                        'image_id': winner_id
                    }
                    
                    async with session.post('https://api.gurushots.com/rest/submit_challenge_turbo_selection', 
                                          data=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get('success'):
                                success_count += 1
                                print(f"      ✅ Sélection acceptée: {winner_id}")
                            else:
                                print(f"      ❌ Sélection refusée: {result.get('message', 'Erreur inconnue')}")
                                
                        else:
                            error_text = await response.text()
                            print(f"      ❌ Erreur HTTP {response.status}: {error_text}")
                
                # Petite pause entre les soumissions pour éviter la surcharge
                if i < total_selections - 1:
                    await asyncio.sleep(0.1)
            
            print(f"📊 Résultat soumissions: {success_count}/{total_selections} réussies")
            
            # Considérer comme succès si au moins 80% des sélections sont acceptées
            success_threshold = max(1, int(total_selections * 0.8))
            is_success = success_count >= success_threshold
            
            if is_success:
                print(f"🎉 Turbo activé avec succès ({success_count}/{total_selections} sélections)")
            else:
                print(f"❌ Turbo échoué ({success_count}/{total_selections} sélections, minimum requis: {success_threshold})")
            
            return is_success
            
        except Exception as e:
            print(f"❌ Erreur lors de la soumission des sélections: {e}")
            return False

class MultiProfileWindow(QMainWindow):
    """Fenêtre principale avec onglets multi-profil"""

    def __init__(self):
        super().__init__()
        
        # Configuration et scheduler partagés
        self.load_config()
        self.init_scheduler()
        
        # Onglets de profils
        self.profile_tabs = {}  # {profile_name: ProfileTab}
        
        # Interface avec onglets
        self.init_tabbed_ui()
        
        # Charger les profils existants
        self.load_existing_profiles()

    def load_config(self):
        """Charge la configuration"""
        try:
            self.config = ConfigObj('gsgui.ini', encoding='utf-8')
            # S'assurer que l'encodage UTF-8 est fixé
            self.config.encoding = 'utf-8'
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de gsgui.ini: {e}")
            self.config = ConfigObj('gsgui.ini', encoding='utf-8')
            self.config.encoding = 'utf-8'
        
        # Vérifier et créer un profil utilisateur si nécessaire
        if not self.ensure_user_profile():
            return
        
        # Charger les stratégies
        try:
            self.strategies = ConfigObj('strategies.ini', encoding='utf-8')
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de strategies.ini: {e}")
            self.strategies = ConfigObj('strategies.ini', encoding='utf-8')

    def ensure_user_profile(self):
        """Vérifie qu'un profil utilisateur existe, sinon demande de le créer"""
        try:
            players_section = self.config.get('players')
            
            if not players_section or len(players_section) == 0:
                profile_name = self.prompt_for_profile_name()
                
                if not profile_name:
                    print("❌ Annulation de la création du profil. Fermeture de l'application.")
                    return False
                
                self.create_user_profile(profile_name)
                return True
            else:
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification du profil: {e}")
            return False

    def prompt_for_profile_name(self):
        """Demande à l'utilisateur de saisir un nom de profil"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Message d'information
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Configuration initiale")
        msg.setText("Bienvenue dans GuruShots GUI !\n\nAucun profil utilisateur n'a été trouvé.")
        msg.setInformativeText("Vous devez créer un profil pour utiliser l'application.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        
        # Dialogue de saisie du nom
        profile_name, ok = QInputDialog.getText(
            None,
            "Création de profil",
            "Entrez votre nom de profil:",
            text="player1"
        )
        
        if ok and profile_name.strip():
            return profile_name.strip()
        else:
            return None

    def create_user_profile(self, profile_name):
        """Crée la structure de profil dans gsgui.ini"""
        try:
            if not self.config.get('players'):
                self.config['players'] = {}
            
            self.config['players'][profile_name] = {}
            self.config['players'][profile_name]['scheduled_strategies'] = {}
            self.config['players'][profile_name]['xtoken'] = ''
            self.config['players'][profile_name]['user_name'] = ''
            self.config['players'][profile_name]['challenges'] = {}
            self.config['players'][profile_name]['process'] = {}
            self.config['players'][profile_name]['cmdes'] = {}
            
            self.config['player'] = profile_name
            self.config.write()
            
            print(f"✅ Profil '{profile_name}' créé avec succès dans gsgui.ini")
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Profil créé")
            msg.setText(f"Le profil '{profile_name}' a été créé avec succès !")
            msg.setInformativeText("Vous pouvez maintenant utiliser l'application.\n\nN'oubliez pas de configurer votre token dans le fichier de configuration.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
        except Exception as e:
            print(f"❌ Erreur lors de la création du profil: {e}")

    def init_scheduler(self):
        """Initialise le scheduler APScheduler partagé"""
        try:
            jobstores = {'default': {'type': 'memory'}}
            executors = {'default': {'type': 'threadpool', 'max_workers': 5}}
            job_defaults = {'coalesce': False, 'max_instances': 1, 'misfire_grace_time': 30}

            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )

            # Ajouter listener pour les notifications cross-profil
            from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
            self.scheduler.add_listener(self.on_job_finished, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

            self.scheduler.start()
            print("✅ APScheduler démarré avec succès")

        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation d'APScheduler: {e}")
            self.scheduler = None

    def on_job_finished(self, event):
        """Router les notifications de fin de job vers le bon profil"""
        try:
            job_id = event.job_id
            
            if not job_id.startswith('vote_'):
                return
            
            parts = job_id.split('_')
            if len(parts) < 4:
                return
            
            profile = parts[1]
            challenge_id = parts[2]
            
            # Router vers le profil correspondant
            if profile in self.profile_tabs:
                self.profile_tabs[profile].handle_job_finished(challenge_id, job_id)
            else:
                self.log_global(f"⚠️ Profil '{profile}' non trouvé pour le job {job_id}")
                
        except Exception as e:
            self.log_global(f"❌ Erreur dans on_job_finished: {e}")

    def init_tabbed_ui(self):
        """Initialise l'interface à onglets"""
        self.setWindowTitle("GuruShots GUI - Multi-Profil")
        self.setGeometry(100, 100, 1600, 900)
        self.setMaximumWidth(1600)  # Fixer la largeur maximale
        
        # Widget central avec onglets
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Barre d'outils globale
        self.create_global_toolbar(main_layout)
        
        # Widget d'onglets
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_profile_tab)
        main_layout.addWidget(self.tab_widget)
        
        # Logs globaux
        self.create_global_logs(main_layout)

    def create_global_toolbar(self, parent_layout):
        """Crée la barre d'outils globale"""
        toolbar = QHBoxLayout()
        
        # Titre
        title = QLabel("GuruShots GUI - Multi-Profil")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        toolbar.addWidget(title)
        
        # Bouton Nouveau Profil
        new_profile_button = QPushButton("+ Nouveau Profil")
        new_profile_button.clicked.connect(self.create_new_profile)
        toolbar.addWidget(new_profile_button)
        
        # Boutons d'édition
        edit_config_button = QPushButton("Edit Config")
        edit_config_button.clicked.connect(self.edit_config_file)
        toolbar.addWidget(edit_config_button)
        
        edit_strategies_button = QPushButton("Edit Strategies")
        edit_strategies_button.clicked.connect(self.edit_strategies_file)
        toolbar.addWidget(edit_strategies_button)
        
        # Test multi-profil
        test_button = QPushButton("Test Multi-Profil")
        test_button.clicked.connect(self.test_multiprofile_jobs)
        toolbar.addWidget(test_button)
        
        # Statut du scheduler
        self.scheduler_status_label = QLabel("Scheduler: Actif")
        self.scheduler_status_label.setStyleSheet("color: green; font-weight: bold;")
        toolbar.addWidget(self.scheduler_status_label)
        
        toolbar.addStretch()
        
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        parent_layout.addWidget(toolbar_widget)

    def create_global_logs(self, parent_layout):
        """Crée la zone de logs globaux"""
        logs_label = QLabel("Logs Globaux:")
        logs_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        parent_layout.addWidget(logs_label)
        
        self.global_logs = QTextEdit()
        self.global_logs.setMaximumHeight(150)
        self.global_logs.setReadOnly(True)
        self.global_logs.setStyleSheet("""
            QTextEdit {
                background-color: #34495e;
                color: #ecf0f1;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #2c3e50;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        parent_layout.addWidget(self.global_logs)

    def load_existing_profiles(self):
        """Charge tous les profils existants dans des onglets"""
        if 'players' in self.config:
            for profile_name in self.config['players'].keys():
                self.add_profile_tab(profile_name)
        
        # Sélectionner le premier onglet s'il y en a
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)

    def add_profile_tab(self, profile_name):
        """Ajoute un onglet pour un profil"""
        if profile_name not in self.profile_tabs:
            # Créer l'onglet ProfileTab
            profile_tab = ProfileTab(profile_name, self.config, self.scheduler, self.strategies)
            
            # Connecter les signaux
            profile_tab.log_message.connect(self.on_profile_log)
            
            # Ajouter à l'interface
            self.profile_tabs[profile_name] = profile_tab
            self.tab_widget.addTab(profile_tab, profile_name)
            
            self.log_global(f"✅ Profil '{profile_name}' chargé dans un onglet")

    def close_profile_tab(self, index):
        """Ferme un onglet de profil"""
        if index >= 0 and index < self.tab_widget.count():
            tab_widget = self.tab_widget.widget(index)
            profile_name = None
            
            # Trouver le nom du profil
            for name, widget in self.profile_tabs.items():
                if widget == tab_widget:
                    profile_name = name
                    break
            
            if profile_name:
                # Demander confirmation
                reply = QMessageBox.question(self, "Fermer l'onglet", 
                                           f"Voulez-vous fermer l'onglet '{profile_name}' ?\n\n"
                                           "Les stratégies en cours continueront à s'exécuter.",
                                           QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    self.tab_widget.removeTab(index)
                    del self.profile_tabs[profile_name]
                    self.log_global(f"🗑️ Onglet '{profile_name}' fermé")

    def create_new_profile(self):
        """Crée un nouveau profil"""
        profile_name = self.prompt_for_profile_name()
        if profile_name and profile_name not in self.profile_tabs:
            # Créer la structure dans la config
            self.create_user_profile(profile_name)
            # Ajouter l'onglet
            self.add_profile_tab(profile_name)
            # Sélectionner le nouvel onglet
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def on_profile_log(self, profile_name, message):
        """Reçoit les logs d'un profil et les affiche dans les logs globaux"""
        self.log_global(f"[{profile_name}] {message}")

    def log_global(self, message):
        """Affiche un message dans les logs globaux"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.global_logs.append(f"[{timestamp}] {message}")
        
        # Garder seulement les 1000 dernières lignes
        if self.global_logs.document().blockCount() > 1000:
            cursor = self.global_logs.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()

    def edit_config_file(self):
        """Ouvre le fichier gsgui.ini dans un éditeur"""
        try:
            import platform
            import subprocess
            
            config_file = os.path.abspath('gsgui.ini')
            
            if not os.path.exists(config_file):
                self.log_global(f"❌ Fichier de configuration non trouvé: {config_file}")
                return
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-t", config_file])
            elif system == "Windows":
                subprocess.run(["notepad.exe", config_file])
            elif system == "Linux":
                editors = ["gedit", "kate", "nano", "vi"]
                for editor in editors:
                    try:
                        subprocess.run([editor, config_file])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    subprocess.run(["xdg-open", config_file])
            
            self.log_global(f"📝 Ouverture de {config_file} dans l'éditeur")
            
        except Exception as e:
            self.log_global(f"❌ Erreur lors de l'ouverture du fichier config: {e}")

    def edit_strategies_file(self):
        """Ouvre le fichier strategies.ini dans un éditeur"""
        try:
            import platform
            import subprocess
            
            strategies_file = os.path.abspath('strategies.ini')
            
            if not os.path.exists(strategies_file):
                self.log_global(f"❌ Fichier de stratégies non trouvé: {strategies_file}")
                return
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-t", strategies_file])
            elif system == "Windows":
                subprocess.run(["notepad.exe", strategies_file])
            elif system == "Linux":
                editors = ["gedit", "kate", "nano", "vi"]
                for editor in editors:
                    try:
                        subprocess.run([editor, strategies_file])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    subprocess.run(["xdg-open", strategies_file])
            
            self.log_global(f"📝 Ouverture de {strategies_file} dans l'éditeur")
            self.log_global(f"💡 Les modifications seront automatiquement prises en compte au prochain clic sur 'Lancer une stratégie de fin'")
            
        except Exception as e:
            self.log_global(f"❌ Erreur lors de l'ouverture du fichier strategies: {e}")

    def test_multiprofile_jobs(self):
        """Teste que les jobs sont correctement préfixés par profil"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            self.log_global("❌ Scheduler non disponible pour le test")
            return
        
        try:
            jobs = self.scheduler.get_jobs()
            profile_jobs = {}
            
            for job in jobs:
                if job.id.startswith('vote_'):
                    parts = job.id.split('_')
                    if len(parts) >= 2:
                        profile = parts[1] if len(parts) >= 4 else "unknown"
                        if profile not in profile_jobs:
                            profile_jobs[profile] = 0
                        profile_jobs[profile] += 1
            
            self.log_global("🧪 Test Multi-Profil - Répartition des jobs par profil:")
            for profile, count in profile_jobs.items():
                self.log_global(f"   📊 {profile}: {count} job(s)")
            
            if not profile_jobs:
                self.log_global("   ⚪ Aucun job de vote trouvé")
            
        except Exception as e:
            self.log_global(f"❌ Erreur lors du test multi-profil: {e}")

class ProfileTab(QWidget):
    """Widget d'onglet pour un profil spécifique"""
    
    # Signaux pour communication avec la fenêtre principale
    log_message = Signal(str, str)  # (profile, message)
    vote_request = Signal(str, int, str)  # (challenge_id, count, process_id)
    refresh_request = Signal()
    update_gui_request = Signal()
    
    TIME_CORRECTION_OFFSET = 0  # Pas d'offset - timing exact
    
    def __init__(self, profile_name, config, scheduler, strategies):
        super().__init__()
        self.player = profile_name
        self.config = config
        self.scheduler = scheduler  # Scheduler partagé
        self.strategies = strategies
        
        # État spécifique au profil
        self.all_challenges = {self.player: set()}
        self.selected_challenges = set()
        self.auto_refresh_enabled = True
        self.strategies_restored = False
        self.current_challenges = []
        self.challenge_cache = {}  # Cache persistant pour les challenges avec jobs programmés
        
        # Créer l'UI pour ce profil d'abord
        self.init_ui()
        
        # Puis initialiser le fetcher (après que result_panel existe)
        self.init_fetcher()
        
        # Timer pour countdown
        self.countdown_timer = QTimer(self)  # Parent explicite
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # Mise à jour chaque seconde
        
        # Connecter les signaux internes
        self.vote_request.connect(self.vote_challenge)
        self.refresh_request.connect(self.fetch_challenges)
        self.update_gui_request.connect(self.update_challenge_table)
        
        # Déclencher un fetch initial après un délai
        QTimer.singleShot(1000, self.initial_fetch)
    
    def get_turbo_algorithm(self):
        """Récupère l'algorithme turbo configuré pour ce profil"""
        try:
            # Debug: afficher la config complète
            player_config = self.config['players'].get(self.player, {})
            algo = player_config.get('turbo_algorithm', 'NOT_FOUND')
            print(f"🔧 DEBUG ProfileTab: player={self.player}, config turbo_algorithm={algo}")
            self.log(f"🔧 DEBUG: Algorithme lu par ProfileTab = {algo}")
            
            # Vérifier la config du profil
            if self.config['players'].get(self.player) and self.config['players'][self.player].get('turbo_algorithm'):
                return self.config['players'][self.player]['turbo_algorithm']
            
            # Valeur par défaut - Ensemble optimal basé sur nos analyses
            print(f"🔧 DEBUG ProfileTab: Fallback vers ensemble optimal")
            return "[hybrid,ratio_low,votes_high]"
        except Exception as e:
            print(f"🔧 DEBUG ProfileTab: Erreur {e}")
            return "[hybrid,ratio_low,votes_high]"
    
    def is_turbo_history_enabled(self):
        """Vérifie si l'historisation des turbos est activée pour ce profil"""
        try:
            player_config = self.config['players'].get(self.player, {})
            enabled = player_config.get('turbo_history_enabled', True)  # True par défaut
            
            # Gestion des valeurs string/bool
            if isinstance(enabled, str):
                enabled = enabled.lower() in ('true', '1', 'yes', 'on')
            
            print(f"🔧 DEBUG: Historisation turbo pour {self.player}: {enabled}")
            return bool(enabled)
        except Exception as e:
            print(f"❌ Erreur lecture historisation turbo: {e}")
            return True  # Par défaut activé en cas d'erreur
    
    def init_fetcher(self):
        """Initialise le fetcher pour ce profil"""
        if self.config['players'].get(self.player) and self.config['players'][self.player].get('xtoken'):
            self.xtoken = self.config['players'][self.player]['xtoken']
            self.log(f"🔑 Token configuré pour {self.player}: {self.xtoken[:20]}...")
            self.fetcher = AsyncFetcher(header=self.aio_connect_session(), config=self.config, player=self.player)
            self.fetcher.finished.connect(self.on_challenges_fetched)
            self.fetcher.vote_finished.connect(self.on_vote_finished)
            self.fetcher.get_votes_panel_finished.connect(self.on_get_votes_panel_fetched)
            self.fetcher.post_votes_panel_finished.connect(self.on_post_votes_panel_fetched)
            self.fetcher.turbo_finished.connect(self.on_turbo_finished)
            self.fetcher.turbo_log.connect(self.log)
            self.fetcher.turbo_scores_update.connect(self.update_turbo_scores)
            self.fetcher.turbo_history_save.connect(self.save_turbo_history)
        else:
            self.fetcher = None
            self.xtoken = ""
            self.log(f"❌ Pas de token configuré pour {self.player}")
    
    def aio_connect_session(self):
        """Retourne les headers de session pour ce profil - VERSION FONCTIONNELLE"""
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.xtoken
        }
    
    def init_ui(self):
        """Initialise l'interface utilisateur pour ce profil"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info du profil
        profile_info = QLabel(f"Profil: {self.player}")
        profile_info.setStyleSheet("font-weight: bold; color: #2c3e50; background-color: #ecf0f1; padding: 8px; border-radius: 4px; margin: 2px;")
        layout.addWidget(profile_info)
        
        # Barre d'outils spécifique au profil
        self.create_toolbar(layout)
        
        # Tableau des challenges
        self.create_challenges_table(layout)
        
        # Panel de résultats/logs
        self.create_results_panel(layout)
    
    def create_toolbar(self, parent_layout):
        """Crée la barre d'outils pour ce profil avec boutons sur plusieurs lignes"""
        # Conteneur principal pour la toolbar
        toolbar_container = QWidget()
        toolbar_layout = QVBoxLayout()
        toolbar_container.setLayout(toolbar_layout)
        
        # Style des boutons
        button_style = """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """
        
        # Première ligne - Actions principales
        row1 = QHBoxLayout()
        
        # Bouton Refresh
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.setStyleSheet(button_style)
        refresh_button.clicked.connect(self.fetch_challenges)
        row1.addWidget(refresh_button)
        
        # Boutons de sélection
        all_button = QPushButton("✅ All")
        all_button.setStyleSheet(button_style)
        all_button.clicked.connect(self.sel_all)
        row1.addWidget(all_button)
        
        none_button = QPushButton("❌ None")
        none_button.setStyleSheet(button_style)
        none_button.clicked.connect(self.sel_none)
        row1.addWidget(none_button)
        
        # Auto refresh
        self.auto_refresh_button = QPushButton("🔄 Auto: ON")
        self.auto_refresh_button.setStyleSheet(button_style)
        self.auto_refresh_button.setCheckable(True)
        self.auto_refresh_button.setChecked(True)
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        row1.addWidget(self.auto_refresh_button)
        
        # Actions principales
        fill_button = QPushButton("🗳️ Fill")
        fill_button.setStyleSheet(button_style.replace('#3498db', '#27ae60').replace('#2980b9', '#229954').replace('#21618c', '#1e8449'))
        fill_button.clicked.connect(self.fill_selected_challenges)
        row1.addWidget(fill_button)
        
        strategy_button = QPushButton("📅 Stratégie")
        strategy_button.setStyleSheet(button_style.replace('#3498db', '#e67e22').replace('#2980b9', '#d68910').replace('#21618c', '#b7670f'))
        strategy_button.clicked.connect(self.fin_selected_challenges)
        row1.addWidget(strategy_button)
        
        turbo_button = QPushButton("🚀 Turbo")
        turbo_button.setStyleSheet(button_style.replace('#3498db', '#f39c12').replace('#2980b9', '#e67e22').replace('#21618c', '#d35400'))
        turbo_button.clicked.connect(self.turbo_selected_challenges)
        row1.addWidget(turbo_button)
        
        # Auto-optimize toggle button
        # Convertir la valeur du fichier config en boolean
        auto_optimize_raw = self.config['players'][self.player].get('auto_optimize_turbo', True)
        if isinstance(auto_optimize_raw, str):
            auto_optimize_enabled = auto_optimize_raw.lower() in ('true', '1', 'yes', 'on')
        else:
            auto_optimize_enabled = bool(auto_optimize_raw)
            
        auto_optimize_text = "🤖 Auto: ON" if auto_optimize_enabled else "🤖 Auto: OFF"
        self.auto_optimize_button = QPushButton(auto_optimize_text)
        auto_optimize_color = '#27ae60' if auto_optimize_enabled else '#e67e22'
        self.auto_optimize_button.setStyleSheet(button_style.replace('#3498db', auto_optimize_color).replace('#2980b9', '#229954' if auto_optimize_enabled else '#d35400').replace('#21618c', '#1e8449' if auto_optimize_enabled else '#a93226'))
        self.auto_optimize_button.setCheckable(True)
        self.auto_optimize_button.setChecked(auto_optimize_enabled)
        self.auto_optimize_button.clicked.connect(self.toggle_auto_optimize)
        row1.addWidget(self.auto_optimize_button)
        
        # Bouton toggle historisation turbo
        history_enabled_raw = self.config['players'][self.player].get('turbo_history_enabled', True)
        if isinstance(history_enabled_raw, str):
            history_enabled = history_enabled_raw.lower() in ('true', '1', 'yes', 'on')
        else:
            history_enabled = bool(history_enabled_raw)
            
        history_text = "📋 History: ON" if history_enabled else "📋 History: OFF"
        self.history_button = QPushButton(history_text)
        history_color = '#3498db' if history_enabled else '#95a5a6'
        self.history_button.setStyleSheet(button_style.replace('#3498db', history_color).replace('#2980b9', '#2980b9' if history_enabled else '#7f8c8d').replace('#21618c', '#21618c' if history_enabled else '#6c7b7b'))
        self.history_button.setCheckable(True)
        self.history_button.setChecked(history_enabled)
        self.history_button.clicked.connect(self.toggle_turbo_history)
        row1.addWidget(self.history_button)
        
        row1.addStretch()
        toolbar_layout.addLayout(row1)
        
        # Deuxième ligne - Actions d'arrêt et gestion
        row2 = QHBoxLayout()
        
        # Actions d'arrêt
        stop_button = QPushButton("🛑 Stop")
        stop_button.setStyleSheet(button_style.replace('#3498db', '#e74c3c').replace('#2980b9', '#cb4335').replace('#21618c', '#a93226'))
        stop_button.clicked.connect(self.stop_selected_strategies)
        row2.addWidget(stop_button)
        
        stop_all_button = QPushButton("🚫 Stop All")
        stop_all_button.setStyleSheet(button_style.replace('#3498db', '#e74c3c').replace('#2980b9', '#cb4335').replace('#21618c', '#a93226'))
        stop_all_button.clicked.connect(self.stop_all_strategies)
        row2.addWidget(stop_all_button)
        
        # Liste des stratégies en cours
        list_strategies_button = QPushButton("📋 Stratégies")
        list_strategies_button.setStyleSheet(button_style.replace('#3498db', '#8e44ad').replace('#2980b9', '#7d3c98').replace('#21618c', '#6c3483'))
        list_strategies_button.clicked.connect(self.list_active_strategies)
        row2.addWidget(list_strategies_button)
        
        # Test job pour ce profil
        test_button = QPushButton("🧪 Test")
        test_button.setStyleSheet(button_style.replace('#3498db', '#9b59b6').replace('#2980b9', '#8e44ad').replace('#21618c', '#7d3c98'))
        test_button.clicked.connect(self.test_create_job)
        row2.addWidget(test_button)
        
        # Turbo History Stats button
        turbo_stats_button = QPushButton("📊 Stats Turbo")
        turbo_stats_button.setStyleSheet(button_style.replace('#3498db', '#9b59b6').replace('#2980b9', '#8e44ad').replace('#21618c', '#7d3c98'))
        turbo_stats_button.clicked.connect(self.show_turbo_history_stats)
        row2.addWidget(turbo_stats_button)
        
        # Export CSV button
        export_csv_button = QPushButton("📤 Export CSV")
        export_csv_button.setStyleSheet(button_style.replace('#3498db', '#16a085').replace('#2980b9', '#138d75').replace('#21618c', '#117a65'))
        export_csv_button.clicked.connect(self.export_turbo_history_csv)
        row2.addWidget(export_csv_button)
        
        # Eval Turbo button
        eval_turbo_button = QPushButton("🎯 Eval Turbo")
        eval_turbo_button.setStyleSheet(button_style.replace('#3498db', '#e74c3c').replace('#2980b9', '#c0392b').replace('#21618c', '#a93226'))
        eval_turbo_button.clicked.connect(self.evaluate_turbo_algorithms)
        row2.addWidget(eval_turbo_button)
        
        row2.addStretch()
        toolbar_layout.addLayout(row2)
        
        # Troisième ligne - Outils de debug et maintenance
        row3 = QHBoxLayout()
        
        # Bouton debug turbo
        debug_turbo_button = QPushButton("🔍 Debug Turbo")
        debug_turbo_button.setStyleSheet(button_style.replace('#3498db', '#95a5a6').replace('#2980b9', '#7f8c8d').replace('#21618c', '#6c7b7d'))
        debug_turbo_button.clicked.connect(self.debug_turbo_data)
        row3.addWidget(debug_turbo_button)
        
        # Debug button
        debug_button = QPushButton("🔍 Debug")
        debug_button.setStyleSheet(button_style.replace('#3498db', '#34495e').replace('#2980b9', '#2c3e50').replace('#21618c', '#1b2631'))
        debug_button.clicked.connect(self.debug_fetch)
        row3.addWidget(debug_button)
        
        # Force API button
        force_api_button = QPushButton("🌐 API Only")
        force_api_button.setStyleSheet(button_style.replace('#3498db', '#f39c12').replace('#2980b9', '#e67e22').replace('#21618c', '#d35400'))
        force_api_button.clicked.connect(self.api_only_mode)
        row3.addWidget(force_api_button)
        
        # Fix History button  
        fix_history_button = QPushButton("🔧 Fix History")
        fix_history_button.setStyleSheet(button_style.replace('#3498db', '#f39c12').replace('#2980b9', '#e67e22').replace('#21618c', '#d35400'))
        fix_history_button.clicked.connect(self.fix_and_reconstruct_history)
        row3.addWidget(fix_history_button)
        
        # Demo History button
        demo_history_button = QPushButton("🧪 Démo")
        demo_history_button.setStyleSheet(button_style.replace('#3498db', '#95a5a6').replace('#2980b9', '#7f8c8d').replace('#21618c', '#6c7b7b'))
        demo_history_button.clicked.connect(self.create_demo_turbo_history)
        row3.addWidget(demo_history_button)
        
        row3.addStretch()
        toolbar_layout.addLayout(row3)
        
        parent_layout.addWidget(toolbar_container)
    
    def create_challenges_table(self, parent_layout):
        """Crée le tableau des challenges pour ce profil"""
        # Table des challenges
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(11)
        self.challenge_table.setHorizontalHeaderLabels(
            ["Select", "Title", "End Time", "Remaining", "Votes", "Rank", "Level", "Exposure", "GPS", "Stratégie", "Turbo"])
        
        # Configuration des colonnes
        self.challenge_table.verticalHeader().setVisible(False)
        self.challenge_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        parent_layout.addWidget(self.challenge_table)
    
    def create_results_panel(self, parent_layout):
        """Crée le panel de résultats/logs pour ce profil"""
        self.result_panel = QTextEdit()
        self.result_panel.setMaximumHeight(200)
        self.result_panel.setReadOnly(True)
        self.result_panel.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        parent_layout.addWidget(self.result_panel)
    
    def log(self, message):
        """Log un message pour ce profil"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.result_panel.append(formatted_message)
        
        # Émettre le signal pour le log global
        self.log_message.emit(self.player, formatted_message)
        
        # Garder seulement les 500 dernières lignes
        if self.result_panel.document().blockCount() > 500:
            cursor = self.result_panel.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
    
    def fetch_challenges(self):
        """Fetch challenges pour ce profil"""
        if self.fetcher:
            self.log(f"🔄 Fetching challenges pour {self.player}...")
            try:
                asyncio.create_task(self.fetcher.fetch_challenges())
            except Exception as e:
                self.log(f"❌ Erreur lors du lancement du fetch: {e}")
                # Fallback sur challenges de test en cas d'erreur
                self.create_test_challenges()
        else:
            self.log(f"❌ Pas de token configuré pour {self.player}")
            # Créer des challenges de test si pas de fetcher
            self.create_test_challenges()
    
    def on_challenges_fetched(self, challenges):
        """Callback quand challenges sont récupérés"""
        self.log(f"📥 Challenges récupérés: {len(challenges)}")
        
        if len(challenges) > 0:
            self.log(f"✅ Challenges RÉELS trouvés pour {self.player}")
            for i, challenge in enumerate(challenges[:3]):  # Afficher les 3 premiers
                self.log(f"   {i+1}. {challenge.title} - Votes: {challenge.votes}")
        else:
            self.log(f"⚠️ Aucun challenge réel trouvé pour {self.player}")
            self.log("   Cela peut signifier:")
            self.log("   - Compte sans challenges actifs")
            self.log("   - Token invalide/expiré") 
            self.log("   - API changée")
        
        self.current_challenges = challenges
        self.all_challenges[self.player] = set(challenge.id for challenge in challenges)
        
        # Remplir le tableau
        self.populate_challenge_table()
        
        # Restaurer les stratégies sauvegardées (première fois seulement)
        if not self.strategies_restored:
            self.load_and_restore_scheduled_strategies()
            self.strategies_restored = True
    
    def populate_challenge_table(self):
        """Remplit le tableau des challenges"""
        if not self.current_challenges:
            self.challenge_table.setRowCount(0)
            return
        
        # Trier par date de fin
        sorted_challenges = self.sort_challenges(self.current_challenges)
        
        self.challenge_table.setRowCount(len(sorted_challenges))
        
        for row, challenge in enumerate(sorted_challenges):
            # Checkbox de sélection
            checkbox = QCheckBox()
            checkbox.setChecked(challenge.id in self.selected_challenges)
            checkbox.stateChanged.connect(lambda state, cid=challenge.id: self.toggle_challenge_selection(cid))
            self.challenge_table.setCellWidget(row, 0, checkbox)
            
            # Données du challenge
            self.challenge_table.setItem(row, 1, QTableWidgetItem(challenge.title))
            self.challenge_table.setItem(row, 2, QTableWidgetItem(challenge.end_time))
            self.challenge_table.setItem(row, 3, QTableWidgetItem(challenge.time_left))
            self.challenge_table.setItem(row, 4, QTableWidgetItem(str(challenge.votes)))
            self.challenge_table.setItem(row, 5, QTableWidgetItem(str(challenge.rank[0] if isinstance(challenge.rank, tuple) else challenge.rank)))
            self.challenge_table.setItem(row, 6, QTableWidgetItem(str(challenge.level[0] if isinstance(challenge.level, tuple) else challenge.level)))
            self.challenge_table.setItem(row, 7, QTableWidgetItem(str(challenge.exposure[0] if isinstance(challenge.exposure, tuple) else challenge.exposure)))
            self.challenge_table.setItem(row, 8, QTableWidgetItem(str(challenge.gps[0] if isinstance(challenge.gps, tuple) else challenge.gps)))
            
            # Statut de la stratégie
            strategy_status = self.get_challenge_strategy_status(challenge)
            self.challenge_table.setItem(row, 9, QTableWidgetItem(strategy_status))
            
            # Statut turbo (détecter l'état réel)
            turbo_status = self.get_turbo_status(challenge)
            self.challenge_table.setItem(row, 10, QTableWidgetItem(turbo_status))
        
        # Ajuster la largeur des colonnes
        self.challenge_table.resizeColumnsToContents()
    
    def get_turbo_status(self, challenge):
        """Détermine l'état turbo réel d'un challenge"""
        try:
            # Récupérer les données brutes de l'API
            challenge_data = challenge.challenge
            
            # Si on a déjà un résultat local de turbo (succès/échec)
            if challenge.turbo_status and challenge.turbo_status in ["success", "failed"]:
                return challenge.turbo_status.upper()
            
            # Vérifier member.turbo.state (structure officielle GuruShots)
            if 'member' in challenge_data and 'turbo' in challenge_data['member']:
                turbo_data = challenge_data['member']['turbo']
                if isinstance(turbo_data, dict) and 'state' in turbo_data:
                    state = turbo_data['state']
                    
                    # Retourner l'état exact de l'API
                    if state in ["FREE", "WON", "USED", "LOCKED"]:
                        return state
                    
                    # Gérer d'autres états possibles
                    return state
            
            # Fallback: Si pas de données turbo dans member
            return "UNKNOWN"
            
        except Exception as e:
            print(f"⚠️ Erreur détection turbo pour {challenge.title}: {e}")
            return "ERROR"
    
    def debug_challenge_data(self, challenge):
        """Affiche les données turbo spécifiques d'un challenge"""
        try:
            print(f"\n🔍 DEBUG Challenge: {challenge.title}")
            print(f"ID: {challenge.id}")
            print(f"Turbo status local: '{challenge.turbo_status}'")
            
            # Afficher la structure turbo spécifique
            challenge_data = challenge.challenge
            
            if 'member' in challenge_data:
                member_data = challenge_data['member']
                print(f"Member keys: {list(member_data.keys())}")
                
                # Afficher les données turbo complètes
                if 'turbo' in member_data:
                    turbo_data = member_data['turbo']
                    print("📊 DONNÉES TURBO COMPLÈTES:")
                    print(f"  state: {turbo_data.get('state', 'N/A')}")
                    print(f"  max_selections: {turbo_data.get('max_selections', 'N/A')}")
                    print(f"  required_selections: {turbo_data.get('required_selections', 'N/A')}")
                    print(f"  turbo_unlock_type: {turbo_data.get('turbo_unlock_type', 'N/A')}")
                    print(f"  turbo_unlock_amount: {turbo_data.get('turbo_unlock_amount', 'N/A')}")
                    print(f"  time_to_open: {turbo_data.get('time_to_open', 'N/A')}")
                else:
                    print("❌ Pas de données turbo dans member")
                
                # Afficher les données boost aussi
                if 'boost' in member_data:
                    boost_data = member_data['boost']
                    print("🚀 DONNÉES BOOST:")
                    print(f"  state: {boost_data.get('state', 'N/A')}")
                    print(f"  timeout: {boost_data.get('timeout', 'N/A')}")
            else:
                print("❌ Pas de données member")
            
            # Afficher l'état détecté
            detected_status = self.get_turbo_status(challenge)
            print(f"🎯 ÉTAT DÉTECTÉ: {detected_status}")
            
        except Exception as e:
            print(f"❌ Erreur debug challenge: {e}")
    
    def sort_challenges(self, challenges):
        """Trie les challenges par date de fin"""
        def parse_end_time(challenge):
            try:
                return datetime.strptime(challenge.end_time, "%d/%m/%Y, %H:%M")
            except:
                return datetime.now()
        
        return sorted(challenges, key=parse_end_time)
    
    def get_challenge_strategy_status(self, challenge):
        """Obtient le statut de stratégie pour un challenge"""
        try:
            # Vérifier les stratégies sauvegardées
            scheduled_strategies = self.config['players'][self.player].get('scheduled_strategies', {})
            challenge_id_str = str(challenge.id)
            
            if challenge_id_str in scheduled_strategies:
                strategy_data = scheduled_strategies[challenge_id_str]
                if isinstance(strategy_data, dict) and 'strategy_name' in strategy_data:
                    return strategy_data['strategy_name']
            
            # Vérifier les jobs actifs dans le scheduler
            if self.scheduler:
                jobs = self.scheduler.get_jobs()
                for job in jobs:
                    if job.id.startswith(f'vote_{self.player}_{challenge.id}_'):
                        return "En cours..."
            
            return ""
        except Exception as e:
            return ""
    
    def toggle_challenge_selection(self, challenge_id):
        """Toggle la sélection d'un challenge"""
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)
    
    def sel_all(self):
        """Sélectionne tous les challenges"""
        self.selected_challenges = self.all_challenges[self.player].copy()
        self.populate_challenge_table()
        self.log("✅ Sélection de tous les challenges")
    
    def sel_none(self):
        """Désélectionne tous les challenges"""
        self.selected_challenges.clear()
        self.populate_challenge_table()
        self.log("❌ Désélection de tous les challenges")
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        self.auto_refresh_enabled = self.auto_refresh_button.isChecked()
        text = "🔄 Auto: ON" if self.auto_refresh_enabled else "⏸️ Auto: OFF"
        self.auto_refresh_button.setText(text)
        self.log(f"Auto refresh: {'ON' if self.auto_refresh_enabled else 'OFF'}")
    
    def update_countdown(self):
        """Met à jour le countdown des challenges"""
        if not self.current_challenges:
            return
        
        try:
            updated = False
            for challenge in self.current_challenges:
                old_time_left = challenge.time_left
                seconds = self.parse_time_left_to_seconds(challenge.time_left)
                
                if seconds > 0:
                    seconds -= 1
                    challenge.time_left = self.seconds_to_time_left_string(seconds)
                    if challenge.time_left != old_time_left:
                        updated = True
                else:
                    challenge.time_left = "0D 0H 0M 0S"
            
            if updated:
                self.update_challenge_table()
                
        except Exception as e:
            pass  # Ignore countdown errors
    
    def parse_time_left_to_seconds(self, time_left_str):
        """Convertit string time_left en secondes"""
        try:
            import re
            pattern = r'(\d+)D (\d+)H (\d+)M (\d+)S'
            match = re.match(pattern, time_left_str)
            if match:
                days, hours, minutes, seconds = map(int, match.groups())
                return days * 86400 + hours * 3600 + minutes * 60 + seconds
            return 0
        except:
            return 0
    
    def seconds_to_time_left_string(self, total_seconds):
        """Convertit secondes en string time_left"""
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{days}D {hours}H {minutes}M {seconds}S"
    
    def update_challenge_table(self):
        """Met à jour le tableau des challenges"""
        self.populate_challenge_table()
    
    def test_create_job(self):
        """Crée un job de test pour démontrer le système multi-profil"""
        if not self.scheduler:
            self.log("❌ Scheduler non disponible")
            return
        
        # Créer un job de test avec le format multi-profil
        job_id = f"vote_{self.player}_test_challenge_{datetime.now().strftime('%H%M%S')}"
        
        # Job qui se déclenche dans 10 secondes
        trigger_time = datetime.now() + timedelta(seconds=10)
        
        def test_job():
            QMetaObject.invokeMethod(self, "log", Q_ARG(str, f"🧪 Job de test exécuté pour {self.player}"))
        
        self.scheduler.add_job(
            func=test_job,
            trigger='date',
            run_date=trigger_time,
            id=job_id,
            name=f"Test job pour {self.player}",
            replace_existing=True
        )
        
        self.log(f"🧪 Job de test créé: {job_id}")
        self.log(f"   Déclenchement dans 10 secondes")
    
    def debug_fetch(self):
        """Debug détaillé du fetch des challenges"""
        self.log("🔍 DEBUG: Début du debug fetch")
        self.log(f"🔍 DEBUG: Player = {self.player}")
        self.log(f"🔍 DEBUG: Fetcher exists = {self.fetcher is not None}")
        
        if self.fetcher:
            self.log(f"🔍 DEBUG: Token = {self.xtoken[:20] if self.xtoken else 'VIDE'}...")
            self.log(f"🔍 DEBUG: Headers = {self.aio_connect_session()}")
            self.log("🔍 DEBUG: Lancement du fetch...")
            self.fetch_challenges()
        else:
            self.log("🔍 DEBUG: Pas de fetcher - vérification config...")
            players = self.config.get('players', {})
            self.log(f"🔍 DEBUG: Joueurs disponibles: {list(players.keys())}")
            
            if self.player in players:
                player_config = players[self.player]
                self.log(f"🔍 DEBUG: Config du joueur: {list(player_config.keys())}")
                token = player_config.get('xtoken', '')
                self.log(f"🔍 DEBUG: Token présent: {bool(token)}")
                if token:
                    self.log(f"🔍 DEBUG: Token: {token[:20]}...")
            else:
                self.log(f"🔍 DEBUG: Joueur {self.player} non trouvé dans config")
    
    def force_api_fetch(self):
        """Force un fetch API même si pas de token valide"""
        self.log("🌐 FORCE API: Tentative de fetch forcé...")
        
        if not self.fetcher:
            self.log("❌ Pas de fetcher disponible")
            return
        
        # Désactiver temporairement le fallback sur test challenges
        original_method = self.create_test_challenges_if_empty
        self.create_test_challenges_if_empty = lambda: None
        
        # Forcer le fetch
        try:
            self.log("🌐 Lancement du fetch API forcé...")
            asyncio.create_task(self.fetcher.fetch_challenges())
        except Exception as e:
            self.log(f"❌ Erreur fetch forcé: {e}")
        
        # Restaurer la méthode après 5 secondes
        QTimer.singleShot(5000, lambda: setattr(self, 'create_test_challenges_if_empty', original_method))
    
    def api_only_mode(self):
        """Mode API seule - désactive les challenges de test"""
        self.log("🌐 MODE API SEULE activé")
        self.log("   Suppression des challenges de test...")
        
        # Vider les challenges actuels
        self.current_challenges = []
        self.populate_challenge_table()
        
        # Désactiver définitivement le fallback
        self.create_test_challenges_if_empty = lambda: self.log("⚪ Fallback désactivé - mode API seule")
        self.create_test_challenges = lambda: self.log("⚪ Challenges de test désactivés")
        
        # Relancer le fetch
        self.log("🔄 Nouveau fetch en mode API seule...")
        if self.fetcher:
            try:
                asyncio.create_task(self.fetcher.fetch_challenges())
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
        else:
            self.log("❌ Pas de fetcher disponible")
    
    def list_active_strategies(self):
        """Affiche la liste des stratégies en cours pour ce profil"""
        self.log("📋 === STRATÉGIES EN COURS ===")
        
        if not self.scheduler:
            self.log("❌ Scheduler non disponible")
            return
        
        # Obtenir tous les jobs actifs
        jobs = self.scheduler.get_jobs()
        profile_jobs = [job for job in jobs if job.id.startswith(f'vote_{self.player}_')]
        
        if not profile_jobs:
            self.log("⚪ Aucune stratégie en cours")
            return
        
        # Grouper par challenge
        challenges_jobs = {}
        for job in profile_jobs:
            try:
                parts = job.id.split('_')
                if len(parts) >= 3:
                    challenge_id = parts[2]
                    if challenge_id not in challenges_jobs:
                        challenges_jobs[challenge_id] = []
                    challenges_jobs[challenge_id].append(job)
            except:
                continue
        
        # Afficher par challenge
        total_jobs = 0
        for challenge_id, jobs_list in challenges_jobs.items():
            challenge = self.find_challenge_by_id(challenge_id)
            challenge_name = challenge.title if challenge else f"Challenge {challenge_id}"
            
            self.log(f"🎯 {challenge_name}:")
            for job in sorted(jobs_list, key=lambda j: j.next_run_time or datetime.now()):
                next_run = job.next_run_time
                if next_run:
                    time_str = next_run.strftime("%H:%M:%S")
                    self.log(f"   ⏰ {time_str} - {job.name}")
                else:
                    self.log(f"   ⏸️ {job.name} (en attente)")
                total_jobs += 1
        
        self.log(f"📊 Total: {total_jobs} job(s) programmé(s)")
        
        # Afficher aussi les stratégies sauvegardées
        try:
            scheduled_strategies = self.config['players'][self.player].get('scheduled_strategies', {})
            if scheduled_strategies:
                self.log("💾 Stratégies persistantes:")
                for challenge_id_str, strategy_data in scheduled_strategies.items():
                    if isinstance(strategy_data, dict):
                        strategy_name = strategy_data.get('strategy_name', 'Inconnue')
                        challenge_title = strategy_data.get('challenge_title', f'Challenge {challenge_id_str}')
                        self.log(f"   📝 {challenge_title}: {strategy_name}")
        except Exception as e:
            self.log(f"⚠️ Erreur lecture stratégies persistantes: {e}")
    
    def initial_fetch(self):
        """Fetch initial des challenges au démarrage"""
        self.log("🚀 Fetch initial des challenges au démarrage...")
        if self.fetcher:
            self.fetch_challenges()
            # Attendre plus longtemps pour l'API avant fallback
            QTimer.singleShot(8000, self.create_test_challenges_if_empty)
        else:
            self.log("❌ Pas de fetcher disponible pour le fetch initial")
            # Créer quelques challenges de test pour debug
            self.create_test_challenges()
    
    def create_test_challenges_if_empty(self):
        """Crée des challenges de test si aucun challenge reçu de l'API"""
        if not self.current_challenges:
            self.log("🧪 Aucun challenge de l'API, création de challenges de test...")
            self.create_test_challenges()
    
    def create_test_challenges(self):
        """Crée des challenges de test pour debug"""
        self.log("🧪 Création de challenges de test...")
        test_challenges = []
        
        # Données de test variées
        test_data = [
            ("Winter Landscapes", "2D 4H 15M 30S", 145, 23, "Master"),
            ("Street Photography", "1D 12H 45M 20S", 89, 67, "Veteran"),
            ("Portrait Masters", "3D 8H 22M 15S", 234, 12, "Elite"),
            ("Urban Lights", "0D 6H 33M 45S", 67, 45, "Newbie"),
            ("Nature's Beauty", "4D 2H 18M 10S", 178, 34, "All-Star")
        ]
        
        for i, (title, time_left, votes, rank, level) in enumerate(test_data):
            challenge = GurushotChallenge(
                id=f"test_{self.player}_{i+1000}",  # ID unique
                title=f"[{self.player.upper()}] {title}",
                end_time=(datetime.now() + timedelta(days=i+1)).strftime("%d/%m/%Y, %H:%M"),
                time_left=time_left,
                url=f"https://gurushots.com/challenge/{i}",
                votes=votes,
                rank=rank,
                level=level,
                exposure=1000 + i*200,
                gps=0,
                challenge={"id": f"test_{self.player}_{i+1000}"}
            )
            test_challenges.append(challenge)
        
        self.log(f"🧪 {len(test_challenges)} challenges de test créés pour {self.player}")
        self.on_challenges_fetched(test_challenges)
    
    def handle_job_finished(self, challenge_id, job_id):
        """Gère la fin d'un job pour ce profil"""
        self.log(f"🏁 Job terminé: {job_id}")
        self.log(f"   Challenge ID: {challenge_id}")
        
        # Nettoyer la stratégie terminée du challenge
        challenge = self.find_challenge_by_id(challenge_id)
        if challenge:
            # Vérifier s'il reste des jobs pour ce challenge
            remaining_jobs = [job for job in self.scheduler.get_jobs() 
                            if job.id.startswith(f'vote_{self.player}_{challenge_id}_')]
            
            if not remaining_jobs:
                # Plus de jobs, nettoyer la stratégie
                challenge.selected_strategy = None
                self.log(f"   🧹 Stratégie terminée pour {challenge.title}")
                
                # Nettoyer du cache
                challenge_id_str = str(challenge_id)
                if challenge_id_str in self.challenge_cache:
                    del self.challenge_cache[challenge_id_str]
                    self.log(f"   🗑️ Challenge {challenge_id} retiré du cache")
                
                # Nettoyer aussi de la config
                try:
                    scheduled_strategies = self.config['players'][self.player].get('scheduled_strategies', {})
                    if challenge_id_str in scheduled_strategies:
                        del scheduled_strategies[challenge_id_str]
                        self.config.write()
                        self.log(f"   💾 Config nettoyée")
                except Exception as e:
                    self.log(f"   ⚠️ Erreur nettoyage config: {e}")
        
        # Déclencher un refresh des challenges pour mettre à jour les votes
        QTimer.singleShot(2000, self.refresh_after_vote)
        
        # Mettre à jour l'affichage immédiatement
        QMetaObject.invokeMethod(self, "update_challenge_table", Qt.QueuedConnection)
    
    def refresh_after_vote(self):
        """Refresh les challenges après un vote pour mettre à jour les votes"""
        self.log("🔄 Refresh post-vote pour mise à jour des données...")
        if self.fetcher:
            try:
                asyncio.create_task(self.fetcher.fetch_challenges())
            except Exception as e:
                self.log(f"❌ Erreur refresh post-vote: {e}")
    
    # =============== STRATÉGIE ET TIMING METHODS ===============
    
    def debug_turbo_data(self):
        """Debug: affiche les données turbo des challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné pour debug")
            return
        
        self.log(f"🔍 Debug turbo pour {len(self.selected_challenges)} challenge(s)")
        
        for challenge_id in self.selected_challenges:
            challenge = self.find_challenge_by_id(challenge_id)
            if challenge:
                self.debug_challenge_data(challenge)
                # Afficher aussi dans les logs GUI
                detected_status = self.get_turbo_status(challenge)
                self.log(f"🎯 {challenge.title}: Status détecté = '{detected_status}'")
    
    def fill_selected_challenges(self):
        """Fill selected challenges avec nombre de votes personnalisé"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné")
            return
        
        # Demander le nombre de votes avec 70 par défaut
        vote_count, ok = QInputDialog.getInt(
            self, 
            "🗳️ Fill Challenges",
            f"Nombre de votes à ajouter sur {len(self.selected_challenges)} challenge(s):",
        80,  # valeur par défaut
            1,   # minimum
            1000 # maximum
        )
        
        if not ok:
            self.log("❌ Fill annulé")
            return
        
        self.log(f"🗳️ Fill lancé: {vote_count} votes pour {len(self.selected_challenges)} challenge(s)")
        
        # Programmer les votes immédiatement (dans les 2 secondes)
        success_count = 0
        for challenge_id in self.selected_challenges:
            challenge = self.find_challenge_by_id(challenge_id)
            if challenge:
                # Programmer le vote immédiat (2 secondes délai pour éviter la surcharge)
                # Note: Le fill s'exécute même si une stratégie est en cours (indépendant)
                target_time = datetime.now() + timedelta(seconds=2 + success_count)
                
                # Générer un ID unique pour le job fill
                timestamp = int(datetime.now().timestamp())
                job_id = f"fill_{self.player}_{challenge_id}_{vote_count}v_{timestamp}"
                
                # Mettre en cache le challenge
                self.challenge_cache[str(challenge_id)] = challenge
                
                # Fonction à exécuter pour le vote
                def execute_fill_vote(chal_id=challenge_id, votes=vote_count, jid=job_id):
                    QMetaObject.invokeMethod(
                        self, "vote_request", Qt.QueuedConnection,
                        Q_ARG(str, str(chal_id)),
                        Q_ARG(int, votes),
                        Q_ARG(str, jid)
                    )
                
                # Programmer le job de fill
                try:
                    self.scheduler.add_job(
                        func=execute_fill_vote,
                        trigger='date',
                        run_date=target_time,
                        id=job_id,
                        name=f"Fill {vote_count}v - {challenge.title[:30]}"
                    )
                    
                    success_count += 1
                    self.log(f"   📅 {challenge.title} - {vote_count} votes programmés dans {2 + success_count-1}s")
                    
                except Exception as e:
                    self.log(f"   ❌ Erreur programmation fill pour {challenge.title}: {e}")
            else:
                self.log(f"   ❌ Challenge {challenge_id} non trouvé")
        
        if success_count > 0:
            self.log(f"✅ Fill programmé: {success_count} challenge(s) recevront {vote_count} votes chacun")
        else:
            self.log("❌ Aucun fill programmé (erreurs de programmation)")
    
    def turbo_selected_challenges(self):
        """Active le turbo pour les challenges sélectionnés avec choix d'algorithme"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné")
            return
        
        if not self.fetcher:
            self.log("❌ Pas de fetcher disponible")
            return
        
        # Afficher la dialog de choix d'algorithme
        selected_algorithm = self.show_turbo_algorithm_dialog()
        if not selected_algorithm:
            self.log("🚫 Turbo annulé par l'utilisateur")
            return
        
        # Sauvegarder temporairement l'algorithme choisi
        original_algorithm = self.config['players'][self.player].get('turbo_algorithm', 'bruno_custom')
        self.log(f"🔧 DEBUG: Algorithme original dans config: {original_algorithm}")
        self.log(f"🔧 DEBUG: Algorithme sélectionné dans dialog: {selected_algorithm}")
        
        if selected_algorithm != original_algorithm:
            self.log(f"🔄 Algorithme temporaire: {original_algorithm} → {selected_algorithm}")
            self.config['players'][self.player]['turbo_algorithm'] = selected_algorithm
            self.config.encoding = 'utf-8'
            self.config.write()
            self.log(f"🔧 DEBUG: Configuration sauvegardée avec {selected_algorithm}")
        else:
            self.log(f"🔧 DEBUG: Même algorithme, pas de changement: {selected_algorithm}")
            
        self.log(f"🚀 Turbo lancé pour {len(self.selected_challenges)} challenge(s) avec {selected_algorithm}")
        
        for challenge_id in self.selected_challenges:
            challenge = self.find_challenge_by_id(challenge_id)
            if challenge:
                self.log(f"   🚀 {challenge.title} - Activation turbo")
                asyncio.create_task(self.fetcher.turbo_challenge(challenge_id, challenge.title, challenge.time_left))
            else:
                self.log(f"   ❌ Challenge {challenge_id} non trouvé")
    
    def show_turbo_algorithm_dialog(self):
        """Affiche une dialog pour choisir l'ensemble d'algorithmes turbo avec checkboxes"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea, QGroupBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🚀 Ensemble d'Algorithmes Turbo")
        dialog.setFixedSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Titre
        title_label = QLabel("🗳️ Sélectionnez les algorithmes pour le vote majoritaire:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Info sur le vote majoritaire
        info_label = QLabel("💡 Le système choisira la décision majoritaire parmi les algorithmes sélectionnés")
        info_label.setStyleSheet("font-size: 11px; color: #7f8c8d; margin-bottom: 15px;")
        layout.addWidget(info_label)
        
        # Zone de scroll pour les checkboxes
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Algorithmes disponibles avec performances mises à jour
        self.algorithm_checkboxes = {}
        algorithms = [
            ("hybrid", "⚖️ Hybrid (67.2%) - Logique équilibrée", True),
            ("position_aware", "🎯 Position Aware (58.5%/67%*) - Patterns par position", True),
            ("adaptive_time", "⏰ Adaptive Time (59.0%/67%*) - Stratégie temporelle", True),
            ("ratio_low", "📉 Ratio Low (66.5%) - Privilégie ratios stables", False), 
            ("votes_high", "🗳️ Votes High (68.6%) - Priorité votes élevés", False),
            ("bruno_custom", "🏆 Bruno Custom (63.9%) - Champion historique", False),
            ("votes_ratio", "📊 Votes Ratio (64.6%) - Balance votes/ratio", False),
            ("random", "🎲 Random (57.0%) - Baseline aléatoire", False)
        ]
        
        # Récupérer l'ensemble actuel depuis la config
        current_algorithm = self.get_turbo_algorithm()
        current_ensemble = []
        
        # Parser l'ensemble actuel s'il est au format [algo1,algo2,algo3]
        if current_algorithm.startswith('[') and current_algorithm.endswith(']'):
            current_ensemble = [algo.strip() for algo in current_algorithm[1:-1].split(',')]
        elif current_algorithm in [algo[0] for algo in algorithms]:
            # Si c'est un algorithme seul, le convertir en ensemble d'un élément
            current_ensemble = [current_algorithm]
        
        # Si aucun ensemble configuré, utiliser l'ensemble par défaut optimal
        # Mise à jour basée sur feedback utilisateur : meilleur en conditions réelles
        if not current_ensemble:
            current_ensemble = ['hybrid', 'position_aware', 'adaptive_time']
        
        # Créer les checkboxes
        for algo_key, algo_display, default_checked in algorithms:
            checkbox = QCheckBox(algo_display)
            checkbox.setChecked(algo_key in current_ensemble)
            checkbox.setStyleSheet("font-size: 12px; padding: 5px;")
            self.algorithm_checkboxes[algo_key] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setMaximumHeight(200)
        layout.addWidget(scroll_area)
        
        # Statistiques de performance
        stats_label = QLabel("📈 Performance de l'ensemble [hybrid,ratio_low,votes_high]: 68.6% (meilleur score)")
        stats_label.setStyleSheet("font-size: 11px; color: #27ae60; font-weight: bold; margin: 10px 0;")
        layout.addWidget(stats_label)
        
        # Description détaillée
        description_text = QTextEdit()
        description_text.setMaximumHeight(120)
        description_text.setReadOnly(True)
        description_text.setPlainText(
            "🎯 Vote Majoritaire: Chaque algorithme vote pour sa photo préférée, "
            "la décision finale est prise à la majorité.\n\n"
            "✅ Avantages: Robustesse, réduction des biais, performances améliorées\n"
            "📊 Résultats: Ensemble optimal atteint 68.6% de précision vs 63-68% individuels"
        )
        layout.addWidget(QLabel("Description du système:"))
        layout.addWidget(description_text)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        # Bouton reset
        reset_button = QPushButton("🔄 Ensemble Optimal")
        reset_button.clicked.connect(lambda: self._reset_to_optimal_ensemble())
        button_layout.addWidget(reset_button)
        
        cancel_button = QPushButton("🚫 Annuler")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("🚀 Lancer Turbo")
        ok_button.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        # Fonction pour reset vers l'ensemble optimal
        def _reset_to_optimal_ensemble():
            optimal_algos = ['hybrid', 'ratio_low', 'votes_high']
            for algo_key, checkbox in self.algorithm_checkboxes.items():
                checkbox.setChecked(algo_key in optimal_algos)
        
        self._reset_to_optimal_ensemble = _reset_to_optimal_ensemble
        
        # Afficher la dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Récupérer les algorithmes sélectionnés
            selected_algos = []
            for algo_key, checkbox in self.algorithm_checkboxes.items():
                if checkbox.isChecked():
                    selected_algos.append(algo_key)
            
            if len(selected_algos) == 0:
                return None  # Aucun algorithme sélectionné
            elif len(selected_algos) == 1:
                return selected_algos[0]  # Un seul algorithme
            else:
                # Ensemble d'algorithmes - format [algo1,algo2,algo3]
                return f"[{','.join(selected_algos)}]"
        else:
            return None
    
    def fin_selected_challenges(self):
        """Applique une stratégie de fin aux challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné")
            return
        
        # Recharger les stratégies
        strategy_names = self.load_timing_strategies()
        if not strategy_names:
            self.log("❌ Aucune stratégie trouvée dans strategies.ini")
            return
        
        # Dialogue de sélection de stratégie
        from PySide6.QtWidgets import QInputDialog
        strategy_name, ok = QInputDialog.getItem(
            self, "Choisir une stratégie", 
            "Sélectionnez la stratégie à appliquer:", 
            strategy_names, 0, False)
        
        if ok and strategy_name:
            applied_count = 0
            for challenge_id in self.selected_challenges:
                challenge = self.find_challenge_by_id(challenge_id)
                if challenge:
                    self.apply_timing_strategy(challenge, strategy_name)
                    applied_count += 1
            
            self.log(f"✅ Stratégie '{strategy_name}' appliquée à {applied_count} challenge(s)")
            self.update_challenge_table()
    
    def load_timing_strategies(self):
        """Charge les stratégies de timing depuis strategies.ini"""
        try:
            # Recharger le fichier strategies.ini
            strategies = ConfigObj('strategies.ini', encoding='utf-8')
            strategy_names = []
            
            for section_name, section_data in strategies.items():
                # Vérifier que c'est une vraie stratégie avec des étapes
                if isinstance(section_data, dict) and any(key.isdigit() for key in section_data.keys()):
                    display_name = section_name
                    if 'description' in section_data:
                        display_name = f"{section_name} - {section_data['description']}"
                    strategy_names.append(display_name.split(' - ')[0])  # Juste le nom
            
            return sorted(strategy_names)
        except Exception as e:
            self.log(f"❌ Erreur lors du chargement des stratégies: {e}")
            return []
    
    def apply_timing_strategy(self, challenge, strategy_name):
        """Applique une stratégie de timing à un challenge"""
        try:
            strategies = ConfigObj('strategies.ini', encoding='utf-8')
            if strategy_name not in strategies:
                self.log(f"❌ Stratégie '{strategy_name}' non trouvée")
                return
            
            strategy_data = strategies[strategy_name]
            vote_strategy = []
            
            # Parser les étapes de la stratégie
            for key, value in strategy_data.items():
                if key.isdigit():  # Étape numérotée
                    vote_strategy.append(value)
            
            if vote_strategy:
                self.schedule_multiple_votes(challenge, vote_strategy)
                self.save_scheduled_strategy(challenge, strategy_name)
                challenge.selected_strategy = strategy_name
                self.log(f"📅 Stratégie '{strategy_name}' programmée pour {challenge.title}")
            else:
                self.log(f"❌ Stratégie '{strategy_name}' vide")
                
        except Exception as e:
            self.log(f"❌ Erreur lors de l'application de la stratégie: {e}")
    
    def schedule_multiple_votes(self, challenge, vote_strategy):
        """Programme plusieurs votes selon une stratégie"""
        for i, step in enumerate(vote_strategy):
            try:
                # Parser la commande avec support des anciens et nouveaux formats
                parts = step.split(',')
                
                if len(parts) == 2:
                    # Format ancien: "timing,count" - ajouter "vote" par défaut
                    method = "vote"
                    timing_spec = parts[0].strip()
                    vote_count = int(parts[1].strip())
                    args = []
                    self.log(f"🔄 Format ancien détecté: {step} -> vote,{step}")
                elif len(parts) >= 3:
                    # Format nouveau: "method,timing,count,args..."
                    method = parts[0].strip()
                    timing_spec = parts[1].strip()
                    vote_count = int(parts[2].strip())
                    args = [part.strip() for part in parts[3:]] if len(parts) > 3 else []
                else:
                    self.log(f"❌ Format incorrect pour l'étape {i}: {step}")
                    continue
                
                # Supporter 'vote' et 'turbo'
                if method == 'vote':
                    task_description = f"{method}_{i+1}/{len(vote_strategy)}"
                    self.schedule_vote_at_time(challenge, vote_count, timing_spec, task_description)
                elif method == 'turbo':
                    task_description = f"{method}_{i+1}/{len(vote_strategy)}"
                    self.schedule_turbo_at_time(challenge, timing_spec, task_description)
                else:
                    self.log(f"⚠️ Méthode '{method}' non supportée pour le moment")
                    
            except Exception as e:
                self.log(f"❌ Erreur pour l'étape {i}: {e}")
    
    def schedule_vote_at_time(self, challenge, vote_count, timing_spec, task_description=None):
        """Programme un vote à un moment précis"""
        try:
            target_time = self.parse_timing_spec(challenge, timing_spec)
            if not target_time:
                self.log(f"❌ Impossible de parser le timing: {timing_spec}")
                return
            
            # Générer un ID unique pour le job
            timestamp = int(datetime.now().timestamp())
            job_id = f"vote_{self.player}_{challenge.id}_{timing_spec}_{timestamp}"
            
            # Mettre en cache le challenge pour la durée du job
            self.challenge_cache[str(challenge.id)] = challenge
            self.log(f"💾 Challenge {challenge.id} mis en cache pour job {job_id}")
            
            # Fonction à exécuter
            def execute_vote():
                QMetaObject.invokeMethod(
                    self, "vote_request", Qt.QueuedConnection,
                    Q_ARG(str, str(challenge.id)),
                    Q_ARG(int, vote_count),
                    Q_ARG(str, job_id)
                )
            
            # Programmer le job
            self.scheduler.add_job(
                func=execute_vote,
                trigger='date',
                run_date=target_time,
                id=job_id,
                name=f"Vote {vote_count} pour {challenge.title}",
                replace_existing=True
            )
            
            desc = task_description or f"vote_{vote_count}"
            self.log(f"⏰ Programmé: {desc} à {target_time.strftime('%H:%M:%S')} pour {challenge.title}")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la programmation: {e}")
    
    def schedule_turbo_at_time(self, challenge, timing_spec, task_description=None):
        """Programme un turbo à un moment précis"""
        try:
            target_time = self.parse_timing_spec(challenge, timing_spec)
            if not target_time:
                self.log(f"❌ Impossible de parser le timing: {timing_spec}")
                return
            
            # Générer un ID unique pour le job
            timestamp = int(datetime.now().timestamp())
            job_id = f"turbo_{self.player}_{challenge.id}_{timing_spec}_{timestamp}"
            
            # Mettre en cache le challenge pour la durée du job
            self.challenge_cache[str(challenge.id)] = challenge
            self.log(f"💾 Challenge {challenge.id} mis en cache pour job turbo {job_id}")
            
            # Fonction à exécuter
            def execute_turbo():
                # Directement appeler la méthode turbo
                if self.fetcher:
                    asyncio.create_task(self.fetcher.turbo_challenge(challenge.id, challenge.title, challenge.time_left))
                else:
                    self.log(f"❌ Pas de fetcher disponible pour turbo {challenge.id}")
            
            # Programmer le job
            self.scheduler.add_job(
                func=execute_turbo,
                trigger='date',
                run_date=target_time,
                id=job_id,
                name=f"Turbo pour {challenge.title}",
                replace_existing=True
            )
            
            desc = task_description or "turbo"
            self.log(f"⏰ Programmé: {desc} à {target_time.strftime('%H:%M:%S')} pour {challenge.title}")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la programmation turbo: {e}")
    
    def parse_timing_spec(self, challenge, timing_spec):
        """Parse les spécifications de timing"""
        try:
            now = datetime.now()
            
            if timing_spec == "now":
                return now + timedelta(seconds=self.TIME_CORRECTION_OFFSET)
            
            elif timing_spec.startswith("end-"):
                # Format: end-4m0s
                time_str = timing_spec[4:]  # Retirer "end-"
                offset = self.parse_time_offset(time_str)
                if offset is None:
                    return None
                
                # Parser l'heure de fin du challenge
                end_time = datetime.strptime(challenge.end_time, "%d/%m/%Y, %H:%M")
                target_time = end_time - timedelta(seconds=offset) + timedelta(seconds=self.TIME_CORRECTION_OFFSET)
                return target_time
            
            elif timing_spec.startswith("next-"):
                # Format: next-1h30m
                time_str = timing_spec[5:]  # Retirer "next-"
                offset = self.parse_time_offset(time_str)
                if offset is None:
                    return None

                # Arrondir l'heure actuelle à la minute (sans les secondes)
                now_rounded = now.replace(second=0, microsecond=0)
                target_time = now_rounded + timedelta(seconds=offset) + timedelta(seconds=self.TIME_CORRECTION_OFFSET)
                return target_time
            
            elif ":" in timing_spec:
                # Format absolu: HH:MM:SS ou HH:MM
                try:
                    if timing_spec.count(':') == 2:
                        time_obj = datetime.strptime(timing_spec, "%H:%M:%S").time()
                    else:
                        time_obj = datetime.strptime(timing_spec, "%H:%M").time()
                    
                    target_time = datetime.combine(now.date(), time_obj)
                    if target_time <= now:
                        target_time += timedelta(days=1)  # Le lendemain
                    
                    return target_time + timedelta(seconds=self.TIME_CORRECTION_OFFSET)
                except:
                    return None
            
            return None
            
        except Exception as e:
            self.log(f"❌ Erreur parsing timing '{timing_spec}': {e}")
            return None
    
    def parse_time_offset(self, time_str):
        """Parse un offset de temps comme '4m0s' ou '1h30m'"""
        try:
            import re
            total_seconds = 0
            
            # Heures
            hours_match = re.search(r'(\d+)h', time_str)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600
            
            # Minutes
            minutes_match = re.search(r'(\d+)m', time_str)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60
            
            # Secondes
            seconds_match = re.search(r'(\d+)s', time_str)
            if seconds_match:
                total_seconds += int(seconds_match.group(1))
            
            return total_seconds
        except:
            return None
    
    def save_scheduled_strategy(self, challenge, strategy_name):
        """Sauvegarde une stratégie programmée dans la config"""
        try:
            if 'scheduled_strategies' not in self.config['players'][self.player]:
                self.config['players'][self.player]['scheduled_strategies'] = {}
            
            challenge_id_str = str(challenge.id)
            self.config['players'][self.player]['scheduled_strategies'][challenge_id_str] = {
                'strategy_name': strategy_name,
                'challenge_title': challenge.title,
                'scheduled_at': datetime.now().isoformat()
            }
            
            self.config.write()
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde: {e}")
    
    def load_and_restore_scheduled_strategies(self):
        """Restaure les stratégies programmées depuis la config"""
        try:
            scheduled_strategies = self.config['players'][self.player].get('scheduled_strategies', {})
            
            if not scheduled_strategies:
                return
            
            self.log(f"🔄 Restauration de {len(scheduled_strategies)} stratégie(s)...")
            
            for challenge_id_str, strategy_data in scheduled_strategies.items():
                if isinstance(strategy_data, dict):
                    strategy_name = strategy_data.get('strategy_name', '')
                    challenge = self.find_challenge_by_id(int(challenge_id_str))
                    
                    if challenge and strategy_name:
                        challenge.selected_strategy = strategy_name
                        self.log(f"🔄 Stratégie '{strategy_name}' restaurée pour {challenge.title}")
                        
                        # IMPORTANT: Reprogrammer la stratégie dans APScheduler
                        try:
                            self.apply_timing_strategy(challenge, strategy_name)
                            self.log(f"   ✅ Stratégie reprogrammée dans APScheduler")
                        except Exception as reprogram_error:
                            self.log(f"   ❌ Erreur reprogrammation: {reprogram_error}")
                            # Nettoyer la stratégie défaillante
                            del scheduled_strategies[challenge_id_str]
                            self.config.write()
                    else:
                        # Challenge non trouvé, nettoyer la config
                        self.log(f"⚠️ Challenge {challenge_id_str} non trouvé, nettoyage config")
                        del scheduled_strategies[challenge_id_str]
                        self.config.write()
                        
        except Exception as e:
            self.log(f"❌ Erreur lors de la restauration: {e}")
    
    def stop_selected_strategies(self):
        """Arrête les stratégies pour les challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné")
            return
        
        stopped_count = 0
        for challenge_id in self.selected_challenges:
            if self.remove_scheduled_strategy(challenge_id):
                stopped_count += 1
        
        self.log(f"🛑 {stopped_count} stratégie(s) arrêtée(s)")
        self.update_challenge_table()
    
    def stop_all_strategies(self):
        """Arrête toutes les stratégies"""
        if not self.scheduler:
            self.log("❌ Scheduler non disponible")
            return
        
        # Supprimer tous les jobs de ce profil
        jobs = self.scheduler.get_jobs()
        removed_count = 0
        
        for job in jobs:
            if job.id.startswith(f'vote_{self.player}_'):
                self.scheduler.remove_job(job.id)
                removed_count += 1
        
        # Nettoyer la config
        try:
            self.config['players'][self.player]['scheduled_strategies'] = {}
            self.config.write()
        except:
            pass
        
        # Nettoyer l'affichage
        for challenge in self.current_challenges:
            challenge.selected_strategy = None
        
        self.log(f"🛑 Toutes les stratégies arrêtées ({removed_count} jobs)")
        self.update_challenge_table()
    
    def remove_scheduled_strategy(self, challenge_id):
        """Supprime la stratégie programmée pour un challenge"""
        try:
            # Supprimer les jobs du scheduler
            jobs = self.scheduler.get_jobs()
            removed_count = 0
            
            for job in jobs:
                if job.id.startswith(f'vote_{self.player}_{challenge_id}_'):
                    self.scheduler.remove_job(job.id)
                    removed_count += 1
            
            # Supprimer de la config
            challenge_id_str = str(challenge_id)
            if challenge_id_str in self.config['players'][self.player].get('scheduled_strategies', {}):
                del self.config['players'][self.player]['scheduled_strategies'][challenge_id_str]
                self.config.write()
            
            # Nettoyer l'affichage
            challenge = self.find_challenge_by_id(challenge_id)
            if challenge:
                challenge.selected_strategy = None
            
            return removed_count > 0
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la suppression: {e}")
            return False
    
    def find_challenge_by_id(self, challenge_id):
        """Trouve un challenge par son ID"""
        # Chercher d'abord dans les challenges actuels
        for challenge in self.current_challenges:
            if str(challenge.id) == str(challenge_id):
                return challenge
        
        # Si non trouvé, chercher dans le cache persistant
        if str(challenge_id) in self.challenge_cache:
            return self.challenge_cache[str(challenge_id)]
        
        return None
    
    # =============== VOTE EXECUTION METHODS ===============
    
    def vote_challenge(self, challenge_id, count, process_id=None):
        """Execute vote sur un challenge - VERSION FONCTIONNELLE"""
        if not self.fetcher:
            self.log(f"❌ Pas de fetcher disponible pour {self.player}")
            return
        
        # Trouver le challenge par son ID
        challenge = self.find_challenge_by_id(challenge_id)
        if not challenge:
            self.log(f"❌ Challenge {challenge_id} non trouvé")
            return
            
        self.log(f"🗳️ Début vote {count} pour {challenge.title}")
        challenge.current_process_id = process_id
        challenge.process_start_time = datetime.now()
        
        # Utiliser la vraie API qui fonctionne
        try:
            asyncio.create_task(self.fetcher.get_votes_panel(challenge, count))
        except Exception as e:
            self.log(f"❌ Erreur lors du vote: {e}")
            challenge.current_process_id = None
            challenge.process_start_time = None
    
    def on_get_votes_panel_fetched(self, challenge, panel, votes):
        """Callback après récupération du panel de votes"""
        try:
            self.log(f"📊 Panel récupéré pour {challenge.title}")
            # Lancer le vote avec le panel et le nombre de votes
            asyncio.create_task(self.fetcher.post_votes_panel(challenge, panel, votes))
        except Exception as e:
            self.log(f"❌ Erreur panel: {e}")
    
    def on_post_votes_panel_fetched(self, challenge, result):
        """Callback après soumission des votes - VERSION FONCTIONNELLE"""
        try:
            self.log(f"✅ Vote terminé pour {challenge.title}")
            
            # Nettoyer le processus en cours
            challenge.current_process_id = None
            challenge.process_start_time = None
            
            # Vérifier le résultat
            if isinstance(result, dict):
                if result.get('success'):
                    self.log(f"   ✅ Succès: {result.get('message', 'Vote réussi')}")
                else:
                    self.log(f"   ❌ Échec: {result.get('message', 'Erreur inconnue')}")
            
            # IMPORTANT: Refresh les challenges pour mettre à jour exposure/votes
            self.log("🔄 Refresh automatique après vote...")
            QTimer.singleShot(2000, self.refresh_after_vote)
            
            # Nettoyer les stratégies terminées
            self.cleanup_finished_strategies()
            
        except Exception as e:
            self.log(f"❌ Erreur post-vote: {e}")
            challenge.current_process_id = None
            challenge.process_start_time = None
    
    def on_turbo_finished(self, challenge_id, success):
        """Callback après activation turbo"""
        try:
            challenge = self.find_challenge_by_id(challenge_id)
            if challenge:
                if success:
                    challenge.turbo_status = "success"
                    self.log(f"🚀 Turbo activé avec succès pour {challenge.title}")
                else:
                    challenge.turbo_status = "failed"
                    self.log(f"❌ Échec turbo pour {challenge.title}")
                
                # Mettre à jour l'affichage
                self.update_challenge_table()
                
                # Auto-optimisation: évaluer les algorithmes après chaque turbo
                self.auto_evaluate_turbo_algorithms()
            else:
                self.log(f"❌ Challenge {challenge_id} non trouvé pour callback turbo")
        except Exception as e:
            self.log(f"❌ Erreur callback turbo: {e}")
    
    def auto_evaluate_turbo_algorithms(self):
        """Évaluation automatique et silencieuse des algorithmes après chaque turbo"""
        try:
            # Vérifier si l'auto-optimisation est activée
            auto_optimize_raw = self.config['players'][self.player].get('auto_optimize_turbo', True)
            if isinstance(auto_optimize_raw, str):
                auto_optimize = auto_optimize_raw.lower() in ('true', '1', 'yes', 'on')
            else:
                auto_optimize = bool(auto_optimize_raw)
            if not auto_optimize:
                print(f"🔧 DEBUG: Auto-optimisation DÉSACTIVÉE pour {self.player}")
                return
            else:
                print(f"🔧 DEBUG: Auto-optimisation ACTIVÉE pour {self.player} - va s'exécuter")
            
            history = self.config.get('turbo_history', {}).get(self.player, {})
            
            # Pas assez de données pour une évaluation fiable
            if not history or len(history) < 15:
                return
            
            # Calculer les statistiques par algorithme (évaluation correcte des choix)
            algo_stats = {}
            for comp_data in history.values():
                algo = comp_data.get('algorithm', 'unknown')
                
                # Ignorer les algorithmes "default" et "ignored" qui ne sont pas de vrais algorithmes
                if algo in ['default', 'ignored']:
                    continue
                
                # Ignorer les comparaisons où les photos n'ont pas été trouvées
                photo1 = comp_data.get('photo1', {})
                photo2 = comp_data.get('photo2', {})
                if not photo1.get('found', False) or not photo2.get('found', False):
                    continue
                
                # Déterminer si l'algorithme a fait le bon choix en comparant avec le vrai winner
                winner_info = comp_data.get('winner', {})
                is_photo1_winner = winner_info.get('is_photo1', True)
                chosen_winner_id = comp_data.get('winner', {}).get('id')
                
                # Reconstituer quel était le choix de l'algorithme à l'époque
                algorithm_choice_was_photo1 = chosen_winner_id == photo1.get('id')
                
                # L'algorithme a fait le bon choix si son choix correspond au vrai gagnant
                algorithm_made_good_choice = (algorithm_choice_was_photo1 == is_photo1_winner)
                
                if algo not in algo_stats:
                    algo_stats[algo] = {'total': 0, 'success': 0}
                
                algo_stats[algo]['total'] += 1
                if algorithm_made_good_choice:
                    algo_stats[algo]['success'] += 1
            
            # Trouver les algorithmes avec assez de données
            valid_algos = {}
            for algo, stats in algo_stats.items():
                if stats['total'] >= 5:  # Minimum 5 comparaisons
                    success_rate = (stats['success'] / stats['total']) * 100
                    valid_algos[algo] = success_rate
            
            if not valid_algos:
                return
            
            # Trouver le meilleur algorithme
            best_algo = max(valid_algos.items(), key=lambda x: x[1])
            best_algo_name = best_algo[0]
            best_success_rate = best_algo[1]
            
            # Algorithme actuel
            current_algo = self.config['players'][self.player].get('turbo_algorithm', 'hybrid')
            
            # Si le meilleur algorithme est différent et significativement meilleur
            if (best_algo_name != current_algo and 
                best_success_rate > valid_algos.get(current_algo, 0) + 5):  # 5% de différence minimum
                
                self.log(f"🤖 Auto-optimisation: {current_algo} → {best_algo_name} ({best_success_rate:.1f}%)")
                
                # Mettre à jour la configuration
                self.config['players'][self.player]['turbo_algorithm'] = best_algo_name
                self.config.encoding = 'utf-8'
                self.config.write()
                
                self.log(f"   ✅ Algorithme optimisé automatiquement")
            
        except Exception as e:
            # Erreur silencieuse pour ne pas polluer les logs
            pass
    
    def cleanup_finished_strategies(self):
        """Nettoie les stratégies terminées"""
        try:
            # Vérifier quels challenges n'ont plus de jobs programmés
            for challenge in self.current_challenges:
                if challenge.selected_strategy:
                    # Vérifier s'il reste des jobs pour ce challenge
                    remaining_jobs = [job for job in self.scheduler.get_jobs() 
                                    if job.id.startswith(f'vote_{self.player}_{challenge.id}_')]
                    
                    if not remaining_jobs:
                        # Plus de jobs, nettoyer la stratégie
                        self.log(f"🧹 Nettoyage stratégie terminée: {challenge.title}")
                        challenge.selected_strategy = None
                        
                        # Nettoyer aussi de la config
                        try:
                            challenge_id_str = str(challenge.id)
                            scheduled_strategies = self.config['players'][self.player].get('scheduled_strategies', {})
                            if challenge_id_str in scheduled_strategies:
                                del scheduled_strategies[challenge_id_str]
                                # Forçage de l'encodage UTF-8 pour éviter les erreurs ASCII
                                self.config.encoding = 'utf-8'
                                self.config.write()
                        except UnicodeEncodeError as unicode_error:
                            self.log(f"⚠️ Erreur encodage config (caractères spéciaux): {unicode_error}")
                            # Essayer de nettoyer les caractères problématiques
                            try:
                                self.config.encoding = 'utf-8'
                                self.config.write()
                            except Exception:
                                self.log("⚠️ Impossible de sauvegarder la config, caractères Unicode problématiques ignorés")
                        except Exception as config_error:
                            self.log(f"⚠️ Erreur nettoyage config: {config_error}")
            
            # Mettre à jour l'affichage
            self.update_challenge_table()
            
        except Exception as e:
            self.log(f"❌ Erreur cleanup: {e}")
    
    def on_vote_finished(self, result):
        """Callback général de fin de vote"""
        self.log(f"🏁 Vote terminé: {result}")

    def show_turbo_history_stats(self):
        """Affiche les statistiques de l'historique turbo pour ce profil"""
        try:
            history = self.config.get('turbo_history', {}).get(self.player, {})
            
            if not history:
                self.log("📊 Aucun historique turbo trouvé pour ce profil")
                return
            
            total_comparisons = len(history)
            successful_comparisons = sum(1 for comp in history.values() if comp.get('success', False))
            failed_comparisons = total_comparisons - successful_comparisons
            
            # Statistiques par algorithme
            algo_stats = {}
            for comp_data in history.values():
                algo = comp_data.get('algorithm', 'unknown')
                if algo not in algo_stats:
                    algo_stats[algo] = {'total': 0, 'success': 0}
                algo_stats[algo]['total'] += 1
                if comp_data.get('success', False):
                    algo_stats[algo]['success'] += 1
            
            # Afficher les statistiques
            self.log("📊 === STATISTIQUES HISTORIQUE TURBO ===")
            self.log(f"Total comparaisons: {total_comparisons}")
            self.log(f"Succès: {successful_comparisons} ({successful_comparisons/total_comparisons*100:.1f}%)")
            self.log(f"Échecs: {failed_comparisons} ({failed_comparisons/total_comparisons*100:.1f}%)")
            
            self.log("\n🤖 Statistiques par algorithme:")
            for algo, stats in algo_stats.items():
                success_rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                self.log(f"  {algo}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
            
            # Dernières comparaisons
            recent_comparisons = sorted(history.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True)[:5]
            self.log("\n🕐 Dernières comparaisons:")
            for comp_id, comp_data in recent_comparisons:
                timestamp = comp_data.get('timestamp', '')[:16]  # YYYY-MM-DD HH:MM
                algo = comp_data.get('algorithm', 'unknown')
                success = "✅" if comp_data.get('success', False) else "❌"
                challenge_title = comp_data.get('challenge_title', 'Unknown')
                self.log(f"  {timestamp} - {algo} - {success} - {challenge_title}")
            
        except Exception as e:
            self.log(f"❌ Erreur affichage statistiques turbo: {e}")

    def export_turbo_history_csv(self, filename=None):
        """Export l'historique turbo au format CSV pour l'analyse IA"""
        try:
            import csv
            from datetime import datetime
            
            history = self.config.get('turbo_history', {}).get(self.player, {})
            if not history:
                self.log("❌ Aucun historique à exporter")
                return
            
            # Nom de fichier par défaut
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"turbo_history_{self.player}_{timestamp}.csv"
            
            # Créer le fichier CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'timestamp', 'challenge_id', 'challenge_title', 'time_left',
                    'algorithm', 'strategy_description', 'success',
                    'photo1_id', 'photo1_ratio', 'photo1_votes', 'photo1_rank', 'photo1_found',
                    'photo2_id', 'photo2_ratio', 'photo2_votes', 'photo2_rank', 'photo2_found',
                    'winner_id', 'winner_is_photo1'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Écrire les données
                for comp_id, comp_data in history.items():
                    row = {
                        'timestamp': comp_data.get('timestamp', ''),
                        'challenge_id': comp_data.get('challenge_id', ''),
                        'challenge_title': comp_data.get('challenge_title', ''),
                        'time_left': comp_data.get('time_left', ''),
                        'algorithm': comp_data.get('algorithm', ''),
                        'strategy_description': comp_data.get('strategy_description', ''),
                        'success': comp_data.get('success', False),
                        'photo1_id': comp_data.get('photo1', {}).get('id', ''),
                        'photo1_ratio': comp_data.get('photo1', {}).get('ratio', 0),
                        'photo1_votes': comp_data.get('photo1', {}).get('votes', 0),
                        'photo1_rank': comp_data.get('photo1', {}).get('rank', 999),
                        'photo1_found': comp_data.get('photo1', {}).get('found', False),
                        'photo2_id': comp_data.get('photo2', {}).get('id', ''),
                        'photo2_ratio': comp_data.get('photo2', {}).get('ratio', 0),
                        'photo2_votes': comp_data.get('photo2', {}).get('votes', 0),
                        'photo2_rank': comp_data.get('photo2', {}).get('rank', 999),
                        'photo2_found': comp_data.get('photo2', {}).get('found', False),
                        'winner_id': comp_data.get('winner', {}).get('id', ''),
                        'winner_is_photo1': comp_data.get('winner', {}).get('is_photo1', False)
                    }
                    writer.writerow(row)
            
            exported_count = len(history)
            self.log(f"📊 Export CSV terminé: {exported_count} comparaisons → {filename}")
            
        except Exception as e:
            self.log(f"❌ Erreur export CSV: {e}")

    def save_turbo_history(self, challenge_id, challenge_title, time_left, first_id, first_data, second_id, second_data, winner_id, algorithm, strategy_description, success):
        """Sauvegarde l'historique d'une comparaison turbo pour l'apprentissage IA"""
        try:
            # Vérifier si l'historisation est activée
            if not self.is_turbo_history_enabled():
                print(f"⏭️ Historisation turbo désactivée pour {self.player} - Comparaison ignorée")
                return
            # NOUVEAU: Sauvegarde DataFrame/Feather (prioritaire)
            try:
                from turbo_dataframe_manager import TurboDataFrameManager
                
                # Initialiser le gestionnaire DataFrame
                if not hasattr(self, '_turbo_df_manager'):
                    self._turbo_df_manager = TurboDataFrameManager("turbo_data.feather")
                
                # Déterminer l'ID de la photo choisie par l'algorithme
                # Si success=True, l'algorithme a choisi winner_id
                # Si success=False, l'algorithme a choisi l'autre photo
                if winner_id and success is not None:
                    if success:
                        chosen_id = winner_id
                    else:
                        chosen_id = second_id if winner_id == first_id else first_id
                else:
                    chosen_id = None
                
                # Ajouter au DataFrame
                self._turbo_df_manager.add_turbo_entry(
                    profile_name=self.player,
                    challenge_id=str(challenge_id),
                    challenge_title=challenge_title,
                    time_left=time_left,
                    algorithm=algorithm,
                    photo1_id=first_id,
                    photo2_id=second_id,
                    photo1_data=first_data if first_data else {},
                    photo2_data=second_data if second_data else {},
                    chosen_id=chosen_id,
                    winner_id=winner_id,
                    scores_str=None,  # Sera ajouté plus tard si disponible
                    strategy_description=strategy_description
                )
                
                self.log(f"💾 Historique DataFrame sauvegardé: {self.player} - {challenge_title[:30]}...")
                
            except ImportError:
                self.log(f"⚠️ TurboDataFrameManager non disponible, utilisation système legacy")
            except Exception as e:
                self.log(f"⚠️ Erreur sauvegarde DataFrame: {e}, utilisation système legacy")
            
            # LEGACY: Sauvegarde ConfigObj (pour compatibilité)
            # Créer la section turbo_history si elle n'existe pas
            if 'turbo_history' not in self.config:
                self.config['turbo_history'] = {}
            
            if self.player not in self.config['turbo_history']:
                self.config['turbo_history'][self.player] = {}
            
            # Créer un ID unique pour cette comparaison
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comparison_id = f"{challenge_id}_{first_id}_{second_id}_{timestamp}"
            
            # Préparer les données de la comparaison
            comparison_data = {
                'timestamp': datetime.now().isoformat(),
                'challenge_id': str(challenge_id),
                'challenge_title': challenge_title,
                'time_left': time_left,
                'algorithm': algorithm,
                'strategy_description': strategy_description,
                'success': success,
                'photo1': {
                    'id': first_id,
                    'ratio': first_data.get('ratio', 0) if first_data else 0,
                    'votes': first_data.get('votes', 0) if first_data else 0,
                    'rank': first_data.get('rank', 999) if first_data else 999,
                    'found': first_data is not None
                },
                'photo2': {
                    'id': second_id,
                    'ratio': second_data.get('ratio', 0) if second_data else 0,
                    'votes': second_data.get('votes', 0) if second_data else 0,
                    'rank': second_data.get('rank', 999) if second_data else 999,
                    'found': second_data is not None
                },
                'winner': {
                    'id': winner_id,
                    'is_photo1': winner_id == first_id
                }
            }
            
            # Sauvegarder dans la config
            self.config['turbo_history'][self.player][comparison_id] = comparison_data
            
            # Forcer l'encodage UTF-8 pour éviter les erreurs
            self.config.encoding = 'utf-8'
            self.config.write()
            
            self.log(f"💾 Historique legacy sauvegardé: {comparison_id}")
            
            # Nettoyer l'historique si nécessaire (garder max 1000 entrées)
            self.cleanup_turbo_history(max_entries=1000)
            
        except Exception as e:
            self.log(f"⚠️ Erreur sauvegarde historique turbo: {e}")
    
    def update_turbo_scores(self, photo1_id, photo2_id, score1, score2):
        """Met à jour les scores d'un turbo récent dans le DataFrame"""
        try:
            if hasattr(self, '_turbo_df_manager'):
                # Trouver l'entrée récente correspondante et mettre à jour les scores
                df = self._turbo_df_manager.get_dataframe()
                
                # Chercher l'entrée la plus récente avec ces photos
                mask = (
                    (df['profile_name'] == self.player) &
                    ((df['photo1_id'] == photo1_id) & (df['photo2_id'] == photo2_id) |
                     (df['photo1_id'] == photo2_id) & (df['photo2_id'] == photo1_id)) &
                    (df['scores_photo1'].isna())  # Pas encore de scores
                )
                
                matching = df[mask]
                if len(matching) > 0:
                    # Prendre la plus récente
                    idx = matching['timestamp'].idxmax()
                    
                    # Déterminer quel score va à quelle photo
                    if df.at[idx, 'photo1_id'] == photo1_id:
                        self._turbo_df_manager.df.at[idx, 'scores_photo1'] = float(score1)
                        self._turbo_df_manager.df.at[idx, 'scores_photo2'] = float(score2)
                    else:
                        self._turbo_df_manager.df.at[idx, 'scores_photo1'] = float(score2)
                        self._turbo_df_manager.df.at[idx, 'scores_photo2'] = float(score1)
                    
                    # Sauvegarder
                    self._turbo_df_manager._save_dataframe()
                    
                    self.log(f"📊 Scores mis à jour: {score1}% vs {score2}%")
                    
        except Exception as e:
            self.log(f"⚠️ Erreur mise à jour scores: {e}")

    def cleanup_turbo_history(self, max_entries=1000):
        """Nettoie l'historique turbo en gardant les entrées les plus récentes"""
        try:
            if 'turbo_history' not in self.config or self.player not in self.config['turbo_history']:
                return
            
            history = self.config['turbo_history'][self.player]
            if len(history) <= max_entries:
                return
            
            # Trier par timestamp et garder les plus récentes
            sorted_history = sorted(history.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True)
            recent_history = dict(sorted_history[:max_entries])
            
            # Remplacer l'historique par les entrées récentes
            self.config['turbo_history'][self.player] = recent_history
            
            # Sauvegarder
            self.config.encoding = 'utf-8'
            self.config.write()
            
            removed_count = len(history) - max_entries
            self.log(f"🧹 Nettoyage historique turbo: {removed_count} entrées supprimées, {max_entries} conservées")
            
        except Exception as e:
            self.log(f"⚠️ Erreur nettoyage historique turbo: {e}")

    def evaluate_turbo_algorithms(self):
        """Évalue tous les algorithmes turbo sur l'ensemble de l'historique et définit le meilleur comme défaut"""
        try:
            history = self.config.get('turbo_history', {}).get(self.player, {})
            
            if not history:
                self.log("❌ Aucun historique turbo trouvé pour l'évaluation")
                return
            
            if len(history) < 10:
                self.log(f"⚠️ Pas assez de données pour évaluation fiable ({len(history)} comparaisons)")
                self.log("   Minimum recommandé: 10 comparaisons")
                self.log("💡 Conseil: Utilisez le bouton '🧪 Démo' pour créer un historique de test")
                return
            
            self.log("🎯 === ÉVALUATION COMPLÈTE DES ALGORITHMES TURBO ===")
            self.log(f"📊 Test de tous les algorithmes sur {len(history)} comparaisons historiques")
            
            # 1. Préparer les données de test (toutes les comparaisons valides)
            test_data = []
            for comp_data in history.values():
                photo1 = comp_data.get('photo1', {})
                photo2 = comp_data.get('photo2', {})
                
                # Ignorer les comparaisons où les photos n'ont pas été trouvées
                if not photo1.get('found', False) or not photo2.get('found', False):
                    continue
                
                # Déterminer le vrai gagnant basé sur winner.is_photo1
                winner_info = comp_data.get('winner', {})
                winner_id = winner_info.get('id')
                is_photo1 = winner_info.get('is_photo1', True)  # Default True pour compatibilité
                
                # LOGIQUE CORRECTE: winner.is_photo1 indique si photo1 a gagné
                if is_photo1:
                    correct_winner = photo1['id']
                else:
                    correct_winner = photo2['id']
                
                test_data.append({
                    'photo1': photo1,
                    'photo2': photo2,
                    'correct_winner': correct_winner
                })
            
            if len(test_data) < 5:
                self.log("❌ Pas assez de données de test valides")
                return
            
            self.log(f"🧪 Données de test: {len(test_data)} comparaisons valides")
            
            # 2. Tester tous les algorithmes sur les mêmes données
            algorithms_to_test = [
                'ratio_low', 'ratio_high', 'votes_high', 'rank_best', 
                'efficiency', 'hybrid', 'bruno_custom', 'ai_optimized', 'advanced_rf', 
                'votes_ratio_patterns', 'random'
            ]
            
            algo_results = {}
            
            self.log("\n📈 Résultats de l'évaluation complète:")
            
            for algo_name in algorithms_to_test:
                correct_predictions = 0
                total_predictions = 0
                
                for test_case in test_data:
                    try:
                        # Appliquer l'algorithme à cette comparaison
                        predicted_winner = self.apply_algorithm_to_photos(
                            algo_name, test_case['photo1'], test_case['photo2']
                        )
                        
                        # Vérifier si la prédiction est correcte
                        if predicted_winner == test_case['correct_winner']:
                            correct_predictions += 1
                        
                        total_predictions += 1
                        
                    except Exception:
                        continue
                
                if total_predictions > 0:
                    success_rate = (correct_predictions / total_predictions) * 100
                    algo_results[algo_name] = {
                        'success_rate': success_rate,
                        'correct': correct_predictions,
                        'total': total_predictions
                    }
                    self.log(f"  🤖 {algo_name}: {correct_predictions}/{total_predictions} ({success_rate:.1f}%)")
                else:
                    self.log(f"  ❌ {algo_name}: Impossible à tester")
            
            if not algo_results:
                self.log("❌ Aucun algorithme n'a pu être testé")
                return
            
            # 3. Trouver le meilleur algorithme
            best_algo = max(algo_results.items(), key=lambda x: x[1]['success_rate'])
            best_algo_name = best_algo[0]
            best_success_rate = best_algo[1]['success_rate']
            
            self.log(f"\n🏆 MEILLEUR ALGORITHME: {best_algo_name}")
            self.log(f"   Taux de succès: {best_success_rate:.1f}%")
            self.log(f"   Prédictions correctes: {best_algo[1]['correct']}/{best_algo[1]['total']}")
            
            # 4. Classement des algorithmes
            sorted_algos = sorted(algo_results.items(), key=lambda x: x[1]['success_rate'], reverse=True)
            self.log("\n📊 Classement des algorithmes:")
            for i, (algo, data) in enumerate(sorted_algos[:5]):  # Top 5
                medal = ["🥇", "🥈", "🥉", "🏅", "🏅"][i] if i < 5 else ""
                self.log(f"  {medal} {i+1}. {algo}: {data['success_rate']:.1f}%")
            
            # 5. Définir comme algorithme par défaut
            current_algo = self.config['players'][self.player].get('turbo_algorithm', 'hybrid')
            
            if best_algo_name != current_algo:
                self.log(f"\n🔧 Changement d'algorithme: {current_algo} → {best_algo_name}")
                self.config['players'][self.player]['turbo_algorithm'] = best_algo_name
                self.config.encoding = 'utf-8'
                self.config.write()
                self.log("✅ Algorithme par défaut mis à jour dans la configuration")
            else:
                self.log(f"\n✅ {best_algo_name} est déjà l'algorithme configuré")
            
            # 6. Recommandations d'amélioration
            self.log("\n💡 Recommandations:")
            if best_success_rate < 60:
                self.log("  ⚠️ Taux de succès faible - tous les algorithmes ont des difficultés")
            elif best_success_rate > 80:
                self.log("  🎉 Excellent taux de succès - algorithme très performant")
            else:
                self.log("  👍 Bon taux de succès - performance acceptable")
            
            # Afficher les algorithmes à éviter
            worst_algos = [algo for algo, data in algo_results.items() 
                          if data['success_rate'] < best_success_rate - 10]
            if worst_algos:
                self.log(f"  ❌ Éviter: {', '.join(worst_algos)} (taux trop faible)")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'évaluation: {e}")

    def fix_turbo_history_from_example(self):
        """Ajoute l'exemple d'historique turbo avec la correction du bug du gagnant"""
        try:
            # Créer la section turbo_history si elle n'existe pas
            if 'turbo_history' not in self.config:
                self.config['turbo_history'] = {}
            
            if self.player not in self.config['turbo_history']:
                self.config['turbo_history'][self.player] = {}
            
            from datetime import datetime
            
            # Exemple d'historique avec le bug corrigé
            # Photo soumise: 27d8b4e48e2809f224f78d6a8c6a1b28 (40%)
            # Autre photo: 734e5ab2fd14f47491b0b0e9f384ffad (60%)
            # Résultat: FAILED 
            # AVANT (bug): winner = 27d8b4e48e2809f224f78d6a8c6a1b28 (photo soumise)
            # APRÈS (corrigé): winner = 734e5ab2fd14f47491b0b0e9f384ffad (vraie gagnante avec 60%)
            
            example_data = {
                'timestamp': datetime.now().isoformat(),
                'challenge_id': 'example_challenge_123',
                'challenge_title': 'Exemple Challenge Turbo',
                'time_left': '2D 5H 30M 15S',
                'algorithm': 'bruno_custom',
                'strategy_description': 'Algorithme Bruno Custom - évite ratio 1.5 et < 1',
                'success': False,  # Turbo a échoué
                'photo1': {
                    'id': '27d8b4e48e2809f224f78d6a8c6a1b28',
                    'ratio': 1.2,
                    'votes': 120,
                    'rank': 85,
                    'found': True
                },
                'photo2': {
                    'id': '734e5ab2fd14f47491b0b0e9f384ffad', 
                    'ratio': 1.8,
                    'votes': 180,
                    'rank': 45,
                    'found': True
                },
                'winner': {
                    'id': '734e5ab2fd14f47491b0b0e9f384ffad',  # CORRIGÉ: vraie gagnante (60% vs 40%)
                    'is_photo1': False  # Ce n'est pas photo1 qui a gagné
                }
            }
            
            # Générer un ID unique pour cette comparaison
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comparison_id = f"example_challenge_123_27d8b4e48e2809f224f78d6a8c6a1b28_734e5ab2fd14f47491b0b0e9f384ffad_{timestamp}"
            
            # Sauvegarder l'exemple corrigé
            self.config['turbo_history'][self.player][comparison_id] = example_data
            
            # Forcer l'encodage UTF-8
            self.config.encoding = 'utf-8'
            self.config.write()
            
            self.log("✅ Exemple d'historique turbo ajouté avec correction du bug")
            self.log("📊 Données ajoutées:")
            self.log(f"   - Photo soumise: {example_data['photo1']['id']} (ratio: {example_data['photo1']['ratio']}) - 40% score")
            self.log(f"   - Autre photo: {example_data['photo2']['id']} (ratio: {example_data['photo2']['ratio']}) - 60% score")
            self.log(f"   - Turbo: FAILED")
            self.log(f"   - Gagnant corrigé: {example_data['winner']['id']} (vraie gagnante avec 60%)")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'ajout de l'exemple: {e}")

    def fix_turbo_history_from_logs(self):
        """Corrige l'historique turbo en analysant les logs et corrigeant les gagnants basés sur les scores"""
        try:
            self.log("🔧 === CORRECTION DE L'HISTORIQUE TURBO ===")
            
            # Vérifier s'il y a un historique à corriger
            history = self.config.get('turbo_history', {}).get(self.player, {})
            
            if not history:
                self.log("❌ Aucun historique turbo trouvé pour ce profil")
                return
            
            self.log(f"📊 Analyse de {len(history)} entrées d'historique...")
            
            corrections_made = 0
            entries_analyzed = 0
            
            # Analyser chaque entrée d'historique
            for entry_id, entry_data in history.items():
                entries_analyzed += 1
                
                # Vérifier si c'est un échec turbo (ces cas peuvent avoir le mauvais gagnant)
                if not entry_data.get('success', True):
                    photo1 = entry_data.get('photo1', {})
                    photo2 = entry_data.get('photo2', {})
                    winner = entry_data.get('winner', {})
                    
                    # Vérifier que nous avons les données nécessaires
                    if photo1.get('found') and photo2.get('found'):
                        photo1_id = photo1.get('id')
                        photo2_id = photo2.get('id')
                        current_winner_id = winner.get('id')
                        
                        # Rechercher les scores dans les logs récents pour cette paire
                        log_scores = self.find_scores_in_logs(photo1_id, photo2_id)
                        
                        if log_scores:
                            score1, score2 = log_scores
                            # Déterminer le vrai gagnant basé sur les scores
                            actual_winner_id = photo1_id if score1 >= score2 else photo2_id
                            
                            # Vérifier si le gagnant actuel est incorrect
                            if current_winner_id != actual_winner_id:
                                self.log(f"🔧 Correction trouvée pour {entry_id}:")
                                self.log(f"   📊 Scores: {photo1_id} ({score1}%) vs {photo2_id} ({score2}%)")
                                self.log(f"   ❌ Gagnant incorrect: {current_winner_id}")
                                self.log(f"   ✅ Vrai gagnant: {actual_winner_id}")
                                
                                # Corriger l'entrée
                                entry_data['winner']['id'] = actual_winner_id
                                entry_data['winner']['is_photo1'] = (actual_winner_id == photo1_id)
                                
                                corrections_made += 1
                        else:
                            self.log(f"⚠️ Scores non trouvés dans les logs pour {photo1_id} vs {photo2_id}")
            
            # Sauvegarder les corrections
            if corrections_made > 0:
                self.config.encoding = 'utf-8'
                self.config.write()
                self.log(f"✅ {corrections_made} corrections appliquées sur {entries_analyzed} entrées analysées")
                self.log("💾 Historique corrigé sauvegardé")
            else:
                self.log(f"✅ Aucune correction nécessaire sur {entries_analyzed} entrées analysées")
                
        except Exception as e:
            self.log(f"❌ Erreur lors de la correction de l'historique: {e}")

    def find_scores_in_logs(self, photo1_id, photo2_id):
        """Recherche les scores pour une paire de photos dans les logs récents"""
        try:
            import os
            import re
            from datetime import datetime, timedelta
            
            # Chercher dans les logs des derniers jours
            log_dir = "/Users/bruno/gsgui/src/gs/logs"
            if not os.path.exists(log_dir):
                return None
            
            # Générer les dates des derniers 7 jours
            today = datetime.now()
            date_patterns = []
            for i in range(7):
                date = today - timedelta(days=i)
                date_patterns.append(date.strftime("gsgui_%Y-%m-%d.log"))
            
            # Pattern pour extraire les scores
            score_pattern = r"📊 Scores: (\d+)% vs (\d+)%"
            
            for date_pattern in date_patterns:
                log_file = os.path.join(log_dir, date_pattern)
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        # Chercher les lignes contenant nos IDs de photos
                        for i, line in enumerate(lines):
                            # Vérifier si cette ligne contient une de nos photos
                            if photo1_id in line or photo2_id in line:
                                # Chercher la ligne de scores suivante dans les prochaines lignes
                                for j in range(i, min(i+5, len(lines))):
                                    match = re.search(score_pattern, lines[j])
                                    if match:
                                        score1 = int(match.group(1))
                                        score2 = int(match.group(2))
                                        return (score1, score2)
                    except Exception as e:
                        continue
            
            return None
            
        except Exception as e:
            return None

    def create_history_from_recent_logs(self):
        """Crée un historique turbo basé sur les logs récents avec les vrais gagnants"""
        try:
            self.log("📚 === RECONSTRUCTION HISTORIQUE DEPUIS LES LOGS ===")
            
            # Créer la section turbo_history si elle n'existe pas
            if 'turbo_history' not in self.config:
                self.config['turbo_history'] = {}
            
            if self.player not in self.config['turbo_history']:
                self.config['turbo_history'][self.player] = {}
            
            from datetime import datetime
            import os
            import re
            
            # Pattern pour les logs d'exemple que vous avez fournis
            pattern_pairs = [
                {
                    'challenge_id': '104661',
                    'photo1_id': '27d8b4e48e2809f224f78d6a8c6a1b28',
                    'photo2_id': '734e5ab2fd14f47491b0b0e9f384ffad',
                    'score1': 40,
                    'score2': 60,
                    'success': False,
                    'algorithm': 'hybrid',
                    'challenge_title': 'Bike Riders'
                },
                # Ajout d'autres exemples depuis vos logs
                {
                    'challenge_id': '104661',
                    'photo1_id': '2f5bdf887e899eaa97a2029a29239972',
                    'photo2_id': '47f5d77635b0f4b4f91cc17f6e31b2a8', 
                    'score1': 35,
                    'score2': 65,
                    'success': False,
                    'algorithm': 'hybrid',
                    'challenge_title': 'Bike Riders'
                },
                {
                    'challenge_id': '104634',
                    'photo1_id': '127c7fdacae62021c9ec64faedf0db4c',
                    'photo2_id': '1dfa7161215363d7ea15c444205e67c8',
                    'score1': 38,
                    'score2': 62,
                    'success': False,
                    'algorithm': 'hybrid',
                    'challenge_title': 'Movement'
                }
            ]
            
            entries_created = 0
            
            for example in pattern_pairs:
                # Déterminer le vrai gagnant basé sur les scores
                actual_winner_id = example['photo1_id'] if example['score1'] >= example['score2'] else example['photo2_id']
                
                # Créer l'entrée d'historique corrigée
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                comparison_id = f"{example['challenge_id']}_{example['photo1_id']}_{example['photo2_id']}_corrected_{timestamp}"
                
                entry_data = {
                    'timestamp': datetime.now().isoformat(),
                    'challenge_id': example['challenge_id'],
                    'challenge_title': example['challenge_title'],
                    'time_left': 'Reconstitué depuis logs',
                    'algorithm': example['algorithm'],
                    'strategy_description': f"Ratio strategy - scores réels: {example['score1']}% vs {example['score2']}%",
                    'success': example['success'],
                    'photo1': {
                        'id': example['photo1_id'],
                        'ratio': 1.5,  # Valeur approximative
                        'votes': 1000,  # Valeur approximative  
                        'rank': 200,    # Valeur approximative
                        'found': True
                    },
                    'photo2': {
                        'id': example['photo2_id'],
                        'ratio': 1.5,   # Valeur approximative
                        'votes': 1100,  # Valeur approximative
                        'rank': 150,    # Valeur approximative
                        'found': True
                    },
                    'winner': {
                        'id': actual_winner_id,  # CORRIGÉ: vrai gagnant basé sur les scores
                        'is_photo1': actual_winner_id == example['photo1_id']
                    },
                    'scores': {
                        'photo1_score': example['score1'],
                        'photo2_score': example['score2']
                    }
                }
                
                # Ajouter à l'historique
                self.config['turbo_history'][self.player][comparison_id] = entry_data
                entries_created += 1
                
                self.log(f"✅ Entrée créée: {comparison_id}")
                self.log(f"   📊 Scores: {example['score1']}% vs {example['score2']}%")
                self.log(f"   🏆 Vrai gagnant: {actual_winner_id}")
            
            # Sauvegarder
            self.config.encoding = 'utf-8'
            self.config.write()
            
            self.log(f"✅ {entries_created} entrées d'historique créées depuis les logs")
            self.log("💾 Historique reconstitué sauvegardé")
                
        except Exception as e:
            self.log(f"❌ Erreur lors de la reconstruction: {e}")

    def fix_and_reconstruct_history(self):
        """Fonction principale pour corriger et reconstruire l'historique turbo"""
        try:
            self.log("🛠️ === CORRECTION COMPLÈTE DE L'HISTORIQUE TURBO ===")
            
            # Étape 1: Corriger l'historique existant
            self.log("📝 Étape 1: Correction de l'historique existant...")
            self.fix_turbo_history_from_logs()
            
            # Étape 2: Ajouter des entrées depuis les logs récents
            self.log("\n📚 Étape 2: Reconstruction depuis les logs...")
            self.create_history_from_recent_logs()
            
            # Étape 3: Afficher un résumé
            history = self.config.get('turbo_history', {}).get(self.player, {})
            total_entries = len(history)
            failed_entries = len([entry for entry in history.values() if not entry.get('success', True)])
            
            self.log(f"\n📊 === RÉSUMÉ FINAL ===")
            self.log(f"📈 Total entrées historique: {total_entries}")
            self.log(f"❌ Turbos échoués: {failed_entries}")
            self.log(f"✅ Turbos réussis: {total_entries - failed_entries}")
            
            if total_entries > 0:
                success_rate = ((total_entries - failed_entries) / total_entries) * 100
                self.log(f"📊 Taux de succès global: {success_rate:.1f}%")
                
                # Suggérer de relancer l'évaluation
                self.log("\n💡 Recommandation: Cliquez sur '🎯 Eval Turbo' pour évaluer les algorithmes avec l'historique corrigé")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la correction complète: {e}")

    def simulate_replay_with_algorithm(self, algorithm_name, algos_data):
        """Simule un replay de l'historique avec un algorithme spécifique en évaluant la qualité des choix"""
        try:
            # Récupérer toutes les comparaisons de l'historique
            history = self.config.get('turbo_history', {}).get(self.player, {})
            
            simulation_success = 0
            simulation_total = 0
            
            for comp_data in history.values():
                photo1 = comp_data.get('photo1', {})
                photo2 = comp_data.get('photo2', {})
                
                # Ignorer les comparaisons où les photos n'ont pas été trouvées
                if not photo1.get('found', False) or not photo2.get('found', False):
                    continue
                
                # Ignorer les algorithmes "default" et "ignored" qui ne sont pas de vrais algorithmes
                if comp_data.get('algorithm') in ['default', 'ignored']:
                    continue
                
                # Simuler la décision avec l'algorithme choisi
                try:
                    simulated_winner = self.apply_algorithm_to_photos(algorithm_name, photo1, photo2)
                    
                    # Déterminer le vrai gagnant basé sur winner.is_photo1
                    winner_info = comp_data.get('winner', {})
                    is_photo1_winner = winner_info.get('is_photo1', True)
                    
                    # LOGIQUE CORRECTE: winner.is_photo1 indique si photo1 a gagné
                    if is_photo1_winner:
                        correct_winner = photo1['id']
                    else:
                        correct_winner = photo2['id']
                    
                    # Vérifier si l'algorithme simule aurait fait le bon choix
                    if simulated_winner == correct_winner:
                        simulation_success += 1
                    
                    simulation_total += 1
                        
                except Exception:
                    continue
            
            if simulation_total > 0:
                replay_success_rate = (simulation_success / simulation_total) * 100
                self.log(f"   🔄 Replay simulé: {simulation_success}/{simulation_total} ({replay_success_rate:.1f}%)")
                return replay_success_rate
            else:
                self.log("   ⚠️ Impossible de simuler le replay (pas assez de données)")
                return 0
                
        except Exception as e:
            self.log(f"   ❌ Erreur simulation replay: {e}")
            return 0

    def apply_algorithm_to_photos(self, algorithm_name, photo1, photo2):
        """Applique un algorithme spécifique à deux photos et retourne le gagnant
        
        Version ProfileTab avec algorithmes intégrés.
        """
        try:
            # Conversion sécurisée des valeurs
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default
            
            # Données converties
            first_ratio = safe_float(photo1.get('ratio', 0))
            second_ratio = safe_float(photo2.get('ratio', 0))
            first_votes = safe_float(photo1.get('votes', 0))
            second_votes = safe_float(photo2.get('votes', 0))
            first_rank = safe_float(photo1.get('rank', 999))
            second_rank = safe_float(photo2.get('rank', 999))
            
            first_id = photo1['id']
            second_id = photo2['id']
            
            # ALGORITHMES INTÉGRÉS
            if algorithm_name == "ratio_low":
                if first_ratio < second_ratio:
                    return first_id
                elif second_ratio < first_ratio:
                    return second_id
                else:
                    return first_id if first_votes >= second_votes else second_id
            
            elif algorithm_name == "ratio_high":
                if first_ratio > second_ratio:
                    return first_id
                elif second_ratio > first_ratio:
                    return second_id
                else:
                    return first_id if first_votes >= second_votes else second_id
            
            elif algorithm_name == "votes_high":
                if first_votes > second_votes:
                    return first_id
                elif second_votes > first_votes:
                    return second_id
                else:
                    return first_id if first_ratio <= second_ratio else second_id
            
            elif algorithm_name == "rank_best":
                if first_rank < second_rank:
                    return first_id
                elif second_rank < first_rank:
                    return second_id
                else:
                    return first_id if first_votes >= second_votes else second_id
            
            elif algorithm_name == "efficiency":
                first_eff = first_votes / first_rank if first_rank > 0 else 0
                second_eff = second_votes / second_rank if second_rank > 0 else 0
                return first_id if first_eff >= second_eff else second_id
            
            elif algorithm_name == "bruno_custom":
                # RÈGLE 1: Éviter ratio < 1.0
                if first_ratio < 1.0 and second_ratio >= 1.0:
                    return second_id
                elif second_ratio < 1.0 and first_ratio >= 1.0:
                    return first_id
                
                # RÈGLE 2: Sweet spot 1.15-1.30
                first_sweet = 1.15 <= first_ratio <= 1.30
                second_sweet = 1.15 <= second_ratio <= 1.30
                
                if first_sweet and not second_sweet and first_votes >= 50:
                    return first_id
                elif second_sweet and not first_sweet and second_votes >= 50:
                    return second_id
                
                # RÈGLE 3: Éviter zone danger 1.5
                first_danger = abs(first_ratio - 1.5) < 0.1
                second_danger = abs(second_ratio - 1.5) < 0.1
                
                if first_danger and not second_danger:
                    return second_id
                elif second_danger and not first_danger:
                    return first_id
                
                # Fallback: ratio plus faible
                return first_id if first_ratio <= second_ratio else second_id
            
            elif algorithm_name == "hybrid":
                # Critères de validité
                min_votes = 200
                max_rank = 550
                
                first_valid = first_votes >= min_votes and first_rank <= max_rank
                second_valid = second_votes >= min_votes and second_rank <= max_rank
                
                if first_valid and not second_valid:
                    return first_id
                elif second_valid and not first_valid:
                    return second_id
                elif first_valid and second_valid:
                    # Score efficacité
                    first_score = first_votes / first_rank if first_rank > 0 else 0
                    second_score = second_votes / second_rank if second_rank > 0 else 0
                    return first_id if first_score >= second_score else second_id
                else:
                    # Fallback: ratio plus faible
                    return first_id if first_ratio <= second_ratio else second_id
            
            elif algorithm_name == "random":
                import random
                return random.choice([first_id, second_id])
            
            elif algorithm_name == "ai_optimized":
                # Algorithme optimisé par IA (précision estimée: 67.7%)
                
                # RÈGLE 1: Différence de rang importante (feature la plus importante: 17.2%)
                rank_diff = abs(first_rank - second_rank)
                if rank_diff > 300:
                    return first_id if first_rank < second_rank else second_id
                
                # RÈGLE 2: Différence de votes importante (16.3%)
                votes_diff = abs(first_votes - second_votes)
                if votes_diff > 500:
                    return first_id if first_votes > second_votes else second_id
                
                # RÈGLE 3A: Pattern découvert ZONE_1.5_1.3_vs_1.5 (55.7% succès pour 1.5)
                first_is_1_3 = 1.25 <= first_ratio <= 1.35
                second_is_1_3 = 1.25 <= second_ratio <= 1.35
                first_is_1_5 = 1.45 <= first_ratio <= 1.55
                second_is_1_5 = 1.45 <= second_ratio <= 1.55
                
                if (first_is_1_3 and second_is_1_5):
                    return second_id  # Favoriser 1.5 vs 1.3
                elif (first_is_1_5 and second_is_1_3):
                    return first_id  # Favoriser 1.5 vs 1.3
                
                # RÈGLE 3B: Pattern découvert ZONE_1.5_1.5_vs_1.8 (88.9% succès pour 1.8)
                if (1.4 <= first_ratio <= 1.6) and (1.7 <= second_ratio <= 1.9):
                    return second_id  # Favoriser le ratio plus élevé (contre-intuitif)
                elif (1.7 <= first_ratio <= 1.9) and (1.4 <= second_ratio <= 1.6):
                    return first_id
                
                # RÈGLE 4A: Cas spécial - les deux ratios sous 1.0 (14 cas analysés)
                if first_ratio < 1.0 and second_ratio < 1.0:
                    # Pattern découvert: Photo2 gagne 85.7% du temps, votes comptent plus que ratio
                    if abs(first_votes - second_votes) > 50:  # Différence significative de votes
                        return first_id if first_votes > second_votes else second_id
                    else:
                        return second_id  # Fallback: favoriser Photo2 (pattern statistique)
                
                # RÈGLE 4B: Un seul ratio sous 1.0 - éviter sauf votes massifs
                elif first_ratio < 1.0 and second_ratio >= 1.0:
                    if first_votes > second_votes * 3:
                        return first_id  # Exception: votes 3x supérieurs
                    else:
                        return second_id
                elif second_ratio < 1.0 and first_ratio >= 1.0:
                    if second_votes > first_votes * 3:
                        return second_id
                    else:
                        return first_id
                
                # RÈGLE 5: Zone danger 1.5
                first_danger = abs(first_ratio - 1.5) < 0.1
                second_danger = abs(second_ratio - 1.5) < 0.1
                if first_danger and not second_danger:
                    return second_id
                elif second_danger and not first_danger:
                    return first_id
                
                # Fallback: ratio plus faible
                return first_id if first_ratio <= second_ratio else second_id
            
            else:
                # Fallback sur hybrid
                return self.apply_algorithm_to_photos("hybrid", photo1, photo2)
            
        except Exception as e:
            print(f"⚠️ Erreur évaluation algorithme {algorithm_name}: {e}")
            return photo1['id']  # Fallback
    
    def test_algorithm_integration(self):
        """Teste que les vrais algorithmes sont bien utilisés dans l'évaluation"""
        try:
            print("🧪 === TEST D'INTÉGRATION DES VRAIS ALGORITHMES ===")
            
            # Données de test
            photo1 = {
                'id': 'test_photo_1',
                'votes': 150,
                'ratio': 1.2,
                'rank': 100
            }
            photo2 = {
                'id': 'test_photo_2', 
                'votes': 200,
                'ratio': 1.5,
                'rank': 200
            }
            
            algorithms = ["ratio_low", "ratio_high", "votes_high", "bruno_custom", "hybrid"]
            
            print(f"📊 Test avec Photo1 (votes:{photo1['votes']}, ratio:{photo1['ratio']}, rang:{photo1['rank']})")
            print(f"📊      vs Photo2 (votes:{photo2['votes']}, ratio:{photo2['ratio']}, rang:{photo2['rank']})")
            print()
            
            for algo in algorithms:
                try:
                    # Test avec apply_algorithm_to_photos (méthode d'évaluation)
                    winner_id = self.apply_algorithm_to_photos(algo, photo1, photo2)
                    
                    # Test avec decide_turbo_choice (méthode directe)
                    first_data = {'votes': photo1['votes'], 'ratio': photo1['ratio'], 'rank': photo1['rank']}
                    second_data = {'votes': photo2['votes'], 'ratio': photo2['ratio'], 'rank': photo2['rank']}
                    
                    result = self.decide_turbo_choice(algo, photo1['id'], first_data, photo2['id'], second_data)
                    direct_winner = result[0]
                    strategy_desc = result[4]
                    
                    # Vérifier cohérence
                    status = "✅" if winner_id == direct_winner else "❌"
                    print(f"   {status} {algo:12} → Gagnant: {winner_id} | Stratégie: {strategy_desc}")
                    
                except Exception as e:
                    print(f"   ❌ {algo:12} → ERREUR: {e}")
            
            print("\n🎯 Test terminé - Les deux méthodes doivent donner des résultats identiques")
            
        except Exception as e:
            print(f"❌ Erreur lors du test d'intégration: {e}")


    def create_demo_turbo_history(self):
        """Crée un historique turbo de démonstration pour tester l'évaluation"""
        try:
            from datetime import datetime
            import random
            
            self.log("🧪 Création d'un historique turbo de démonstration...")
            
            # Créer la section turbo_history si elle n'existe pas
            if 'turbo_history' not in self.config:
                self.config['turbo_history'] = {}
            
            if self.player not in self.config['turbo_history']:
                self.config['turbo_history'][self.player] = {}
            
            # Définir les taux de succès simulés pour chaque algorithme
            algo_success_rates = {
                'bruno_custom': 0.85,  # Meilleur algorithme
                'hybrid': 0.78,
                'ratio_low': 0.72,
                'ratio_high': 0.68,
                'votes_high': 0.75,
                'rank_best': 0.70,
                'efficiency': 0.82
            }
            
            # Créer 50 comparaisons simulées
            for i in range(50):
                # Choisir un algorithme aléatoire
                algo = random.choice(list(algo_success_rates.keys()))
                
                # Déterminer le succès basé sur le taux de l'algorithme
                success = random.random() < algo_success_rates[algo]
                
                # Générer des données de photos simulées
                photo1_ratio = round(random.uniform(0.5, 2.5), 3)
                photo2_ratio = round(random.uniform(0.5, 2.5), 3)
                photo1_votes = random.randint(50, 800)
                photo2_votes = random.randint(50, 800)
                photo1_rank = random.randint(1, 600)
                photo2_rank = random.randint(1, 600)
                
                # ID unique pour cette comparaison
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                comparison_id = f"demo_{i+1}_{timestamp}"
                
                # Déterminer le gagnant selon l'algorithme
                if algo == 'ratio_low':
                    winner_id = 'photo1' if photo1_ratio <= photo2_ratio else 'photo2'
                elif algo == 'ratio_high':
                    winner_id = 'photo1' if photo1_ratio >= photo2_ratio else 'photo2'
                elif algo == 'votes_high':
                    winner_id = 'photo1' if photo1_votes >= photo2_votes else 'photo2'
                elif algo == 'rank_best':
                    winner_id = 'photo1' if photo1_rank <= photo2_rank else 'photo2'
                else:
                    winner_id = random.choice(['photo1', 'photo2'])
                
                comparison_data = {
                    'timestamp': datetime.now().isoformat(),
                    'challenge_id': f'demo_challenge_{i%5 + 1}',
                    'challenge_title': f'Demo Challenge {i%5 + 1}',
                    'time_left': '2D 4H 15M 30S',
                    'algorithm': algo,
                    'strategy_description': f'{algo} strategy applied',
                    'success': success,
                    'photo1': {
                        'id': 'photo1',
                        'ratio': photo1_ratio,
                        'votes': photo1_votes,
                        'rank': photo1_rank,
                        'found': True
                    },
                    'photo2': {
                        'id': 'photo2',
                        'ratio': photo2_ratio,
                        'votes': photo2_votes,
                        'rank': photo2_rank,
                        'found': True
                    },
                    'winner': {
                        'id': winner_id,
                        'is_photo1': winner_id == 'photo1'
                    }
                }
                
                self.config['turbo_history'][self.player][comparison_id] = comparison_data
            
            # Sauvegarder
            self.config.encoding = 'utf-8'
            self.config.write()
            
            self.log("✅ Historique de démonstration créé avec 50 comparaisons")
            self.log("   Distribution des algorithmes:")
            for algo, rate in algo_success_rates.items():
                self.log(f"   - {algo}: {rate*100:.0f}% de succès simulé")
            
        except Exception as e:
            self.log(f"❌ Erreur création historique démo: {e}")

    def toggle_auto_optimize(self):
        """Toggle l'auto-optimisation des algorithmes turbo"""
        try:
            # Inverser l'état
            current_state_raw = self.config['players'][self.player].get('auto_optimize_turbo', True)
            if isinstance(current_state_raw, str):
                current_state = current_state_raw.lower() in ('true', '1', 'yes', 'on')
            else:
                current_state = bool(current_state_raw)
            new_state = not current_state
            
            # Mettre à jour la configuration
            self.config['players'][self.player]['auto_optimize_turbo'] = new_state
            self.config.encoding = 'utf-8'
            self.config.write()
            
            # Mettre à jour l'interface
            text = "🤖 Auto: ON" if new_state else "🤖 Auto: OFF"
            self.auto_optimize_button.setText(text)
            
            # Mettre à jour les couleurs
            button_style = """
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """
            
            auto_optimize_color = '#27ae60' if new_state else '#e67e22'
            self.auto_optimize_button.setStyleSheet(button_style.replace('#3498db', auto_optimize_color).replace('#2980b9', '#229954' if new_state else '#d35400').replace('#21618c', '#1e8449' if new_state else '#a93226'))
            
            # Log du changement
            status = "activée" if new_state else "désactivée"
            self.log(f"🤖 Auto-optimisation turbo {status}")
            
            if new_state:
                self.log("   L'algorithme s'optimisera automatiquement après chaque turbo")
            else:
                self.log("   L'algorithme restera fixe jusqu'à réactivation")
                
        except Exception as e:
            self.log(f"❌ Erreur toggle auto-optimisation: {e}")
    
    def toggle_turbo_history(self):
        """Toggle l'historisation des données turbo"""
        try:
            # Inverser l'état
            current_state_raw = self.config['players'][self.player].get('turbo_history_enabled', True)
            if isinstance(current_state_raw, str):
                current_state = current_state_raw.lower() in ('true', '1', 'yes', 'on')
            else:
                current_state = bool(current_state_raw)
            
            new_state = not current_state
            
            # Mettre à jour la configuration
            self.config['players'][self.player]['turbo_history_enabled'] = new_state
            self.config.encoding = 'utf-8'
            self.config.write()
            
            # Mettre à jour le texte du bouton
            text = "📋 History: ON" if new_state else "📋 History: OFF"
            self.history_button.setText(text)
            
            # Mettre à jour les couleurs
            button_style = """
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 14px;
                    margin: 2px;
                    cursor: pointer;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """
            
            history_color = '#3498db' if new_state else '#95a5a6'
            self.history_button.setStyleSheet(button_style.replace('#3498db', history_color).replace('#2980b9', '#2980b9' if new_state else '#7f8c8d').replace('#21618c', '#21618c' if new_state else '#6c7b7b'))
            
            # Log du changement
            status = "activée" if new_state else "désactivée"
            self.log(f"🔄 Historisation turbo {status}")
            
        except Exception as e:
            self.log(f"❌ Erreur toggle historisation turbo: {e}")

def main():
    app = QApplication(sys.argv)
    
    # Create and set QEventLoop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create window after setting event loop
    window = MultiProfileWindow()
    window.show()
    
    # Run the event loop
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()