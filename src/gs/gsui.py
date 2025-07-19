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
                               QHeaderView, QTableWidgetItem, QDialog, QDialogButtonBox, QTabWidget)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QMetaObject, Q_ARG
import aiohttp
from datetime import datetime, timedelta, time

from configobj import ConfigObj
from qasync import QEventLoop, asyncSlot
import browser_cookie3
from src.gs.gsprompt import GuruBatch
from PySide6.QtGui import QFont
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

class ProfileTab(QWidget):
    """Widget d'onglet pour un profil spécifique"""
    
    # Signaux pour communication avec la fenêtre principale
    log_message = Signal(str, str)  # (profile, message)
    job_finished = Signal(str, str)  # (profile, challenge_id)
    
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
        
        # Initialiser le fetcher pour ce profil
        self.init_fetcher()
        
        # Créer l'UI pour ce profil
        self.init_ui()
        
    def init_fetcher(self):
        """Initialise le fetcher pour ce profil"""
        if self.config['players'].get(self.player) and self.config['players'][self.player].get('xtoken'):
            self.xtoken = self.config['players'][self.player]['xtoken']
            self.fetcher = AsyncFetcher(header=self.aio_connect_session())
            self.fetcher.finished.connect(self.on_challenges_fetched)
            self.fetcher.vote_finished.connect(self.on_vote_finished)
            self.fetcher.get_votes_panel_finished.connect(self.on_get_votes_panel_fetched)
            self.fetcher.post_votes_panel_finished.connect(self.on_post_votes_panel_fetched)
        else:
            self.fetcher = None
            self.xtoken = ""
    
    def aio_connect_session(self):
        """Retourne les headers de session pour ce profil"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-token': self.xtoken
        }
    
    def init_ui(self):
        """Initialise l'interface utilisateur pour ce profil"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info du profil
        profile_info = QLabel(f"Profil: {self.player}")
        profile_info.setStyleSheet("font-weight: bold; color: blue; padding: 5px;")
        layout.addWidget(profile_info)
        
        # Barre d'outils spécifique au profil
        self.create_toolbar(layout)
        
        # Tableau des challenges
        self.create_challenges_table(layout)
        
        # Panel de résultats/logs
        self.create_results_panel(layout)
    
    def create_toolbar(self, parent_layout):
        """Crée la barre d'outils pour ce profil"""
        toolbar = QHBoxLayout()
        
        # Bouton Refresh
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.fetch_challenges)
        toolbar.addWidget(refresh_button)
        
        # Boutons de sélection
        all_button = QPushButton("All")
        all_button.clicked.connect(self.sel_all)
        toolbar.addWidget(all_button)
        
        none_button = QPushButton("None")
        none_button.clicked.connect(self.sel_none)
        toolbar.addWidget(none_button)
        
        # Auto refresh
        self.auto_refresh_button = QPushButton("Auto Refresh: ON")
        self.auto_refresh_button.setCheckable(True)
        self.auto_refresh_button.setChecked(True)
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        toolbar.addWidget(self.auto_refresh_button)
        
        # Boutons d'action
        fill_button = QPushButton("Fill")
        fill_button.clicked.connect(self.fill_selected_challenges)
        toolbar.addWidget(fill_button)
        
        fin_button = QPushButton("Lancer Stratégie Fin")
        fin_button.clicked.connect(self.fin_selected_challenges)
        toolbar.addWidget(fin_button)
        
        # Boutons de gestion
        strategies_button = QPushButton("Stratégies en cours")
        strategies_button.clicked.connect(self.show_in_progress_challenges)
        toolbar.addWidget(strategies_button)
        
        stop_button = QPushButton("Stop Stratégie")
        stop_button.clicked.connect(self.stop_selected_strategies)
        toolbar.addWidget(stop_button)
        
        stop_all_button = QPushButton("Stop Tous")
        stop_all_button.clicked.connect(self.stop_all_strategies)
        toolbar.addWidget(stop_all_button)
        
        toolbar.addStretch()
        
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        parent_layout.addWidget(toolbar_widget)
    
    def create_challenges_table(self, parent_layout):
        """Crée le tableau des challenges pour ce profil"""
        # Table des challenges
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(10)
        self.challenge_table.setHorizontalHeaderLabels(
            ["Select", "Title", "End Time", "Remaining", "Votes", "Rank", "Level", "Exposure", "GPS", "Stratégie"])
        
        # Configuration des colonnes
        self.challenge_table.verticalHeader().setVisible(False)
        self.challenge_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.challenge_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select
        self.challenge_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # End Time
        self.challenge_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Remaining
        self.challenge_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Stratégie
        
        parent_layout.addWidget(self.challenge_table)
    
    def create_results_panel(self, parent_layout):
        """Crée le panel de résultats/logs pour ce profil"""
        self.result_panel = QTextEdit()
        self.result_panel.setMaximumHeight(200)
        self.result_panel.setReadOnly(True)
        parent_layout.addWidget(self.result_panel)
    
    def log(self, message):
        """Log un message pour ce profil"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.result_panel.append(formatted_message)
        
        # Émettre le signal pour le log global
        self.log_message.emit(self.player, formatted_message)
    
    # Placeholder pour les méthodes principales (à compléter)
    def fetch_challenges(self):
        """Fetch challenges pour ce profil"""
        if self.fetcher:
            self.log(f"Fetching challenges pour {self.player}...")
            # TODO: Implémenter le fetch
        else:
            self.log(f"Pas de token configuré pour {self.player}")
    
    def sel_all(self):
        """Sélectionne tous les challenges"""
        self.log("Sélection de tous les challenges")
    
    def sel_none(self):
        """Désélectionne tous les challenges"""
        self.log("Désélection de tous les challenges")
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        self.auto_refresh_enabled = self.auto_refresh_button.isChecked()
        text = "Auto Refresh: ON" if self.auto_refresh_enabled else "Auto Refresh: OFF"
        self.auto_refresh_button.setText(text)
    
    def fill_selected_challenges(self):
        """Fill challenges sélectionnés"""
        self.log("Fill des challenges sélectionnés")
    
    def fin_selected_challenges(self):
        """Lance stratégie de fin"""
        self.log("Lancement stratégie de fin")
    
    def show_in_progress_challenges(self):
        """Affiche les stratégies en cours"""
        self.log("Affichage des stratégies en cours")
    
    def stop_selected_strategies(self):
        """Arrête les stratégies sélectionnées"""
        self.log("Arrêt des stratégies sélectionnées")
    
    def stop_all_strategies(self):
        """Arrête toutes les stratégies"""
        self.log("Arrêt de toutes les stratégies")
    
    def on_challenges_fetched(self, challenges):
        """Callback quand challenges sont récupérés"""
        self.log(f"Challenges récupérés: {len(challenges)}")
    
    def on_vote_finished(self, result):
        """Callback quand vote terminé"""
        self.log(f"Vote terminé: {result}")
    
    def on_get_votes_panel_fetched(self, challenge, panel, count):
        """Callback vote panel fetched"""
        pass
    
    def on_post_votes_panel_fetched(self, challenge, result):
        """Callback post vote panel"""
        pass
class GurushotChallenge:

    def __init__(self, id, title, end_time, time_left, url, votes, rank, level, exposure, gps, challenge):
        self.id = id
        self.title = title
        self.end_time = end_time
        self.time_left = time_left
        self.url = url
        self.votes= votes

        self.rank = rank,
        self.level = level,
        self.exposure = exposure,
        self.gps = gps,
        self.selected_strategy = None
        self.status = ""  # Statut initial vide
        self.challenge=challenge
        self.current_process_id = None  # Pour stocker l'ID du processus en cours
        self.process_start_time = None  # Pour suivre quand un processus a commencé


class AsyncFetcher(QObject):
    finished = Signal(list)
    vote_finished = Signal(str)
    get_votes_panel_finished = Signal(object, object, int)
    post_votes_panel_finished = Signal(object, object)

    def __init__(self, header):
        super().__init__()
        self.aio_header = header

    async def fetch_challenges(self):
        try:
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/get_my_active_challenges') as response:
                    data = await response.json()
                    challenges = []
                    for challenge_data in data.get('challenges', []):
                        timeleft = challenge_data['time_left']

                        challenge = GurushotChallenge(
                            id=challenge_data['id'],
                            title=challenge_data['title'],
                            end_time=datetime.fromtimestamp(challenge_data["close_time"]).strftime(
                            "%d/%m/%Y, %H:%M"),
                            time_left = "{}D {}H {}M {}S".format(timeleft["days"], timeleft["hours"],
                                                                                timeleft["minutes"], timeleft["seconds"]),
                            url=challenge_data['url'],
                            exposure=int(challenge_data['member']['ranking']['total']['exposure']),
                            votes=int(challenge_data['member']['ranking']['total']['votes']),
                            rank=int(challenge_data['member']['ranking']['total']['rank']),
                            level=challenge_data['member']['ranking']['total']['level_name'],
                            #if challenge_data['member']['ranking']['total'].get('gps') is not None:
                            gps = int(0),#gps=challenge_data['member']['ranking']['total']['gps'],
                            challenge=challenge_data

                        )
                        challenges.append(challenge)
                    self.finished.emit(challenges)
        except Exception as e:
            print(f"Error fetching challenges: {e}")
            self.finished.emit([])

    async def votes(self, url, count):
        try:
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(url, data={'count': count}) as response:
                    if response.status == 200:
                        result = await response.text()
                        #self.vote_finished.emit(f"Voted successfully: {result}")
                        return await response.read()
                    else:
                        return await response.read() #self.vote_finished.emit(f"Vote failed with status: {response.status}")
        except Exception as e:
            self.vote_finished.emit(f"Error during voting: {str(e)}")

    async def fetch_get_votes_panel(self, challenge, count):
        try:
            # Vérifier que le challenge a une URL valide
            if not hasattr(challenge, 'url') or not challenge.url:
                error_result = {"success": False, "message": "Challenge URL is missing or invalid"}
                self.get_votes_panel_finished.emit(challenge, error_result, -1*count)
                return
                
            # Log pour le débogage
            self.loggs(f"Récupération des données de vote pour {challenge.title} (URL: {challenge.url}, HEADER:{self.aio_header})")
                
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                    async with session.post('https://api.gurushots.com/rest/get_vote_data', data={'limit': 100, 'url': challenge.url}) as response:
                        if response.status == 200:
                            try:
                                result = await response.json()
                                # Vérifier que la réponse contient bien des images
                                if not result.get('images') or len(result.get('images', [])) == 0:
                                    self.loggs(f"Pas d'images disponibles pour {challenge.title}, {result}")
                                    self.get_votes_panel_finished.emit(challenge, {"success": False, "message": "No images available", "challenge": {"close_time": 0}}, -1*count)
                                else:
                                    self.loggs(f"Récupération réussie: {len(result.get('images', []))} images pour {challenge.title}")
                                    if count > 0:
                                        self.get_votes_panel_finished.emit(challenge, result, count)
                                    else:
                                        self.loggs(len(result.get('images', [])))
                                        for image in result.get('images', []):
                                            #récupérer les photos
                                            async with session.get(f'''https://photos.gurushots.com/unsafe/0x840/{image.get('token')}''') as response_image:
                                                data = response_image
                                        self.post_votes_panel_finished.emit(challenge,  {"success": True, "message": 'no vote panel', "challenge": {"close_time": 0}})


                            except Exception as json_error:
                                error_text = await response.text()
                                self.loggs(f"Erreur de parsing JSON: {json_error}, Réponse: {error_text[:100]}...")
                                self.get_votes_panel_finished.emit(challenge, {"success": False, "message": f"JSON parsing error: {json_error}", "challenge": {"close_time": 0}}, -1*count)
                        else:
                            error_text = await response.text()
                            self.loggs(f"Erreur HTTP {response.status}: {error_text[:100]}...")
                            self.get_votes_panel_finished.emit(challenge, {"success": False, "message": f"HTTP {response.status}: {error_text}", "challenge": {"close_time": 0}}, -1*count)
        except Exception as e:
            #(f"Exception générale lors de la récupération des votes: {e}")
            self.get_votes_panel_finished.emit(challenge, {"success": False, "message": str(e), "challenge": {"close_time": 0}}, -1*count)

    async def fetch_post_votes_panel(self, challenge, votes):
        try:
            # Vérifier que nous avons des tokens à envoyer
            if not votes or len(votes) == 0:
                error_result = {"success": False, "message": "No valid image tokens to vote on"}
                self.post_votes_panel_finished.emit(challenge, error_result)
                return

            # Vérifier que tous les tokens sont valides (non vides)
            valid_votes = [v for v in votes if v and v.strip()]
            if len(valid_votes) == 0:
                error_result = {"success": False, "message": "All image tokens were empty or invalid"}
                self.post_votes_panel_finished.emit(challenge, error_result)
                return
                
            # Créer le payload avec seulement les tokens valides
            payload = {'tokens[' + str(id) + ']': value for id, value in enumerate(valid_votes)}
            payload.update({'viewed_tokens[' + str(id) + ']': value for id, value in enumerate(valid_votes)})
            
            # Vérifier que nous avons un ID de challenge valide
            if not hasattr(challenge, 'id') or not challenge.id:
                error_result = {"success": False, "message": "Invalid challenge ID"}
                self.post_votes_panel_finished.emit(challenge, error_result)
                return
                
            payload['c_id'] = challenge.id
            payload['c_token'] = "03AOLTBLR8mMuwAHd5TwbZo5KuuMZYDUVbM-gwQZgojsOHPf-NdlccOUjk6DXw6QE3thLUf6ASwqgQigw1-zTLI6-prjlTIS9ByBXVvePZkYXGwf6MDNIielvqiEWTemoMPWkKVSPme0EOALsd0MrbwDFHxbS02LGpt2u9GwieEKurIUmP7IKNxPEVBGwSR9UTDhWLfUimQK-yDKBVzIZYmbiEHM6gw85-9jDbtGtaAKcEGio83U6b4lmaGWVr8jhWYDKW49PDPrlc0hqYoV1nAOMySaIstamSZP56Zzp3ejo_1A0EqMOL1vGaG5aKt8a-tFY26Q9TRROHx8lVNcJoSBuBHFGUzl2n12JLjqAvJd6BcOweUMlhJapSrwSgHpRl5UQJ58G2AkWdMMvkwbplXZCqQ8cdv_HAzduBOwzutsfuubfCk0Fgqfb1wFK1FrfSGyRVhgrmci12xKmiIrIP1ZIOycaCXI7V0-sY5TW94mmjknYGwUiCdNI"

            # Envoyer la requête avec les tokens valides
            async with aiohttp.ClientSession(headers=self.aio_header, connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post('https://api.gurushots.com/rest/submit_votes', data=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.post_votes_panel_finished.emit(challenge, result)
                    else:
                        error_text = await response.text()
                        error_result = {"success": False, "message": f"HTTP {response.status}: {error_text}"}
                        self.post_votes_panel_finished.emit(challenge, error_result)
        except Exception as e:
            error_result = {"success": False, "message": str(e)}
            self.post_votes_panel_finished.emit(challenge, error_result)

    def set_log(self, logger):
        self.logger = logger

    def loggs(self, *args):
        # Créer le texte à ajouter
        text = "".join([str(e) for e in args])

        # Ajouter un timestamp au message de log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {text}"

        # Écrire dans le fichier de logs
        try:
            # Créer le répertoire logs s'il n'existe pas
            log_dir = os.path.join(os.path.dirname(os.path.abspath('gsgui.ini')), 'logs')
            os.makedirs(log_dir, exist_ok=True)

            # Définir le chemin du fichier de log (un fichier par jour)
            log_file = os.path.join(log_dir, f"gsgui_{datetime.now().strftime('%Y-%m-%d')}.log")

            # Écrire dans le fichier en mode append
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            # En cas d'erreur, on continue sans bloquer l'affichage dans l'UI
            print(f"Erreur lors de l'écriture dans le fichier de logs: {e}")

    def start_fetch(self):
        # Utiliser create_task au lieu de ensure_future et capturer l'erreur
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Create task in the current loop
            asyncio.ensure_future(self.fetch_challenges(), loop=loop)
        except Exception as e:
            print(f"Error starting fetch_challenges: {e}")

    def start_get_votes_panel(self, url, count):
        # Utiliser create_task au lieu de ensure_future et capturer l'erreur
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Create task in the current loop
            asyncio.ensure_future(self.fetch_get_votes_panel(url, count), loop=loop)
        except Exception as e:
            print(f"Error starting fetch_get_votes_panel: {e}")

    def start_post_votes_panel(self, challenge, votes_panel):
        # Utiliser create_task au lieu de ensure_future et capturer l'erreur
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Create task in the current loop
            asyncio.ensure_future(self.fetch_post_votes_panel(challenge, votes_panel), loop=loop)
        except Exception as e:
            print(f"Error starting fetch_post_votes_panel: {e}")
            
    def _handle_task_exception(self, task, task_name):
        # Fonction helper pour gérer les exceptions de tâches asyncio
        try:
            task.result()  # Récupérer le résultat ou lever l'exception
        except asyncio.CancelledError:
            print(f"Task {task_name} was cancelled")
        except Exception as e:
            print(f"Task {task_name} raised exception: {e}")

class ChallengeWindow(QMainWindow):
    # Définir un signal pour les votes à déclencher depuis les workers
    vote_request = Signal(object, int, str)  # Signal avec challenge, count et process_id
    # Signal pour déclencher le refresh depuis les threads APScheduler
    refresh_request = Signal()
    # Signal pour déclencher la mise à jour de l'interface depuis les threads
    update_gui_request = Signal()
    
    # Correction de temps pour compenser le décalage serveur (en secondes)
    TIME_CORRECTION_OFFSET = 30
    
    def __init__(self, player=None):
        super().__init__()

        self.setWindowTitle("Gurushot Challenges")
        self.setGeometry(100, 100, 1200, 1200)

        self.parser = argparse.ArgumentParser(description='challenge')
        self.parser.add_argument('--cha', nargs='?', action="store", default='')
        self.parser.add_argument('--player', nargs='?', help='Player', default='')
        self.parser.add_argument('--user', nargs='?', help='User', required=False)
        self.parser.add_argument('--xtoken', help='xtoken', required=False)
        self.parser.add_argument('--cmde', nargs='?', help='Cmde', default='')
        self.parser.add_argument('--shell ', action="store_true", default=False)
        self.subparsers = self.parser.add_subparsers(dest='cmdla', help='sub-command help')

        #self.parser_ps = self.subparsers.add_parser('ps')
        #self.parser_ps.add_argument('ps', nargs='?', action="store", default='')
        #self.parser_ps.add_argument('--list', action="store_true", default=False)
        #self.parser_ps.add_argument('--pop', nargs='?', action="store", default='')
        #self.parser_ps.set_defaults(func=self.ps)

        self.parser_vote = self.subparsers.add_parser('vote')
        self.parser_vote.add_argument('vote', nargs='?', action="store", default='1')
        self.parser_vote.add_argument('--list', action="store_true", default=False)
        self.parser_vote.add_argument('--novote', nargs='?', type=int, action="store", default=0)

        self.parser_vote.add_argument('--player', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--all', action="store_true", default=False)
        self.parser_vote.add_argument('--at', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--left', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--when', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--now', action="store_true", default=False)
        self.parser_vote.add_argument('--next', nargs='?', help='time left', default='')
        self.parser_vote.add_argument('--photo', nargs='?', action="store", default='')
        self.parser_vote.set_defaults(func=self.vote)

        self.parser_strategie = self.subparsers.add_parser('st')
        self.parser_strategie.add_argument('st', nargs='?', action="store", default='end4')
        self.parser_strategie.add_argument('--player', nargs='?', action="store", default='')
        self.parser_strategie.add_argument('--list', action="store_true", default=False)
        self.parser_strategie.add_argument('--start', action="store_true", default=True)
        self.parser_strategie.add_argument('--stop', action="store_true", default=False)
        self.parser_strategie.add_argument('--step', nargs='?', action="store", default='1')
        self.parser_strategie.add_argument('--at', nargs='?', action="store", default='')
        self.parser_strategie.add_argument('--left', nargs='?', action="store", default='')
        self.parser_strategie.set_defaults(func=self.strategie)



        self.parser_ps = self.subparsers.add_parser('ps')
        self.parser_ps.add_argument('ps', nargs='?', action="store", default='')
        self.parser_ps.add_argument('--list', action="store_true", default=False)
        self.parser_ps.add_argument('--restart', action="store_true", default=False)
        self.parser_ps.add_argument('--stop', action="store_true", default=False)
        self.parser_ps.add_argument('--pop', nargs='?', action="store", default='')
        self.parser_ps.add_argument('--purge', action="store_true", default=False)
        self.parser_ps.add_argument('--at', nargs='?', action="store", default='')
        self.parser_ps.set_defaults(func=self.ps)


        # Charger ou créer le fichier de configuration
        try:
            self.config = ConfigObj('gsgui.ini')
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de gsgui.ini: {e}")
            print("🔧 Création d'un nouveau fichier de configuration...")
            self.config = ConfigObj('gsgui.ini')
        
        # Vérifier et créer un profil utilisateur si nécessaire
        if not self.ensure_user_profile():
            return  # Arrêter l'initialisation si l'utilisateur a annulé
        
        args = self.parser.parse_args()
        if args.player == '':
             self.player = self.config.get('player')
        else:
            self.player = args.player
        self.init_player(self.player)
        self.init_scheduler()

    def ensure_user_profile(self):
        """Vérifie qu'un profil utilisateur existe, sinon demande de le créer"""
        try:
            # Vérifier si la section players existe et n'est pas vide
            players_section = self.config.get('players')
            
            if not players_section or len(players_section) == 0:
                # Pas de profil existant, demander à l'utilisateur
                profile_name = self.prompt_for_profile_name()
                
                if not profile_name:
                    print("❌ Annulation de la création du profil. Fermeture de l'application.")
                    return False
                
                # Créer la structure du profil
                self.create_user_profile(profile_name)
                return True
            else:
                # Au moins un profil existe
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification du profil: {e}")
            return False

    def prompt_for_profile_name(self):
        """Demande à l'utilisateur de saisir un nom de profil"""
        from PySide6.QtWidgets import QInputDialog, QMessageBox, QApplication
        
        # Créer une QApplication temporaire si nécessaire
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
            # Créer la section players si elle n'existe pas
            if not self.config.get('players'):
                self.config['players'] = {}
            
            # Créer le profil utilisateur avec la structure complète
            self.config['players'][profile_name] = {}
            self.config['players'][profile_name]['scheduled_strategies'] = {}
            self.config['players'][profile_name]['xtoken'] = ''
            
            # Définir ce profil comme profil par défaut
            self.config['player'] = profile_name
            
            # Sauvegarder la configuration
            self.config.write()
            
            print(f"✅ Profil '{profile_name}' créé avec succès dans gsgui.ini")
            
            # Afficher un message de confirmation
            from PySide6.QtWidgets import QMessageBox
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
        """Initialise et configure APScheduler pour les tâches automatiques"""
        try:
            # Utiliser BlockingScheduler au lieu de QtScheduler pour éviter les problèmes de QTimer
            from apscheduler.schedulers.background import BackgroundScheduler
            
            """Configuration avancée du scheduler"""
            jobstores = {
                'default': {'type': 'memory'}
            }
            executors = {
                'default': {'type': 'threadpool', 'max_workers': 5}
            }
            job_defaults = {
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 30
            }

            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )

            # Ajouter un listener pour nettoyer automatiquement les stratégies terminées
            from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
            self.scheduler.add_listener(self.on_job_finished, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

            # 1. Fetch initial des challenges pour récupérer le temps restant
            self.log("Fetch initial des challenges pour initialiser le décompte...")
            self.refresh_request.emit()
            
            # Programmer le premier déclenchement au prochain changement de minute
            from datetime import datetime, timedelta
            now = datetime.now()
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            
            # 2. Première exécution au prochain changement de minute
            self.scheduler.add_job(
                func=self.start_countdown_refresh,
                trigger='date',
                run_date=next_minute,
                id='initial_countdown',
                name='Démarrage du décompte au changement de minute',
                replace_existing=True
            )
            
            self.log(f"Décompte programmé à {next_minute.strftime('%H:%M:%S')}")

            # Ajouter une tâche de nettoyage des processus bloqués toutes les minutes
            self.scheduler.add_job(
                func=self.check_stalled_processes,
                trigger=IntervalTrigger(minutes=1),
                id='check_stalled_processes',
                name='Vérification des processus bloqués',
                replace_existing=True,
                max_instances=1
            )

            # Optionnel: Ajouter une tâche de nettoyage des challenges fermés toutes les 5 minutes
            self.scheduler.add_job(
                func=self.purge_closed_challenges,
                trigger=IntervalTrigger(minutes=5),
                id='purge_closed_challenges',
                name='Suppression des challenges fermés',
                replace_existing=True,
                max_instances=1
            )
            
            # Resynchronisation avec le serveur toutes les 5 minutes pour corriger la dérive
            self.scheduler.add_job(
                func=self.sync_with_server,
                trigger=IntervalTrigger(minutes=5),
                id='server_sync',
                name='Synchronisation avec le serveur',
                replace_existing=True,
                max_instances=1
            )

            # Nettoyage périodique des stratégies terminées (toutes les 2 minutes)
            self.scheduler.add_job(
                func=self.cleanup_finished_strategies,
                trigger=IntervalTrigger(minutes=2),
                id='cleanup_strategies',
                name='Nettoyage des stratégies terminées',
                replace_existing=True,
                max_instances=1
            )

            # Démarrer le scheduler
            self.scheduler.start()
            self.log("APScheduler démarré avec succès")

            # Variable pour contrôler l'état du refresh automatique
            self.auto_refresh_enabled = True

        except Exception as e:
            self.log(f"Erreur lors de l'initialisation d'APScheduler: {e}")
            self.scheduler = None

    def start_countdown_refresh(self):
        """Démarre le décompte local après le premier déclenchement"""
        try:
            # Initialiser le timestamp de référence
            #self.last_countdown_update = datetime.now()
            
            # Première mise à jour du décompte
            self.update_countdown()
            
            # 3. Programmer les mises à jour du décompte toutes les 10 secondes
            self.scheduler.add_job(
                func=self.update_countdown,
                trigger=IntervalTrigger(seconds=10),
                id='countdown_refresh',
                name='Mise à jour du décompte local',
                replace_existing=True,
                max_instances=1
            )
            
            self.log("Décompte local démarré - mise à jour toutes les 10 secondes")
            
        except Exception as e:
            self.log(f"Erreur lors du démarrage du décompte: {e}")

    def parse_time_left_to_seconds(self, time_left_str):
        """Convertit le format 'XD YH ZM XS' en secondes"""
        try:
            # Format: "6D 7H 42M 50S"
            parts = time_left_str.strip().split()
            days = hours = minutes = seconds = 0
            
            for part in parts:
                if part.endswith('D'):
                    days = int(part[:-1])
                elif part.endswith('H'):
                    hours = int(part[:-1])
                elif part.endswith('M'):
                    minutes = int(part[:-1])
                elif part.endswith('S'):
                    seconds = int(part[:-1])
            
            total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
            return total_seconds
            
        except Exception as e:
            self.log(f"Erreur parsing time_left '{time_left_str}': {e}")
            return 0

    def update_countdown(self):
        """Met à jour le temps restant par décompte local"""
        try:
            if not self.auto_refresh_enabled:
                return

            current_time = datetime.now()
            
            # Calculer le temps écoulé depuis la dernière mise à jour
            if hasattr(self, 'last_countdown_update'):
                elapsed_seconds = (current_time - self.last_countdown_update).total_seconds()
            else:
                elapsed_seconds = 10  # Première exécution

            # Mettre à jour le temps restant pour chaque challenge
            if hasattr(self, 'all_challenges') and self.player in self.all_challenges:
                for challenge in self.all_challenges[self.player]:
                    if hasattr(challenge, 'remaining_seconds'):
                        # Décompter le temps écoulé depuis la dernière mise à jour
                        challenge.remaining_seconds -= elapsed_seconds
                        
                        # Recalculer le format d'affichage avec les secondes
                        if challenge.remaining_seconds > 0:
                            days = int(challenge.remaining_seconds // 86400)
                            hours = int((challenge.remaining_seconds % 86400) // 3600)
                            minutes = int((challenge.remaining_seconds % 3600) // 60)
                            seconds = int(challenge.remaining_seconds % 60)
                            challenge.time_left = f"{days}D {hours}H {minutes}M {seconds}S"
                        else:
                            challenge.time_left = "0D 0H 0M 0S"
                            challenge.remaining_seconds = 0

            # 4. Mettre à jour l'interface via signal
            self.update_gui_request.emit()
            
            # Mettre à jour le timestamp APRÈS avoir fait les calculs
            self.last_countdown_update = current_time

            
        except Exception as e:
            self.log(f"Erreur lors de la mise à jour du décompte: {e}")

    def sync_with_server(self):
        """Resynchronisation périodique avec le serveur pour corriger la dérive"""
        try:
            self.log("Resynchronisation avec le serveur...")
            # Déclencher un fetch complet pour recalibrer les temps
            self.refresh_request.emit()
            
        except Exception as e:
            self.log(f"Erreur lors de la synchronisation: {e}")

    def auto_refresh_challenges(self):
        """Fonction appelée automatiquement pour rafraîchir les challenges (ancien système)"""
        try:
            if not self.auto_refresh_enabled:
                return

            self.log("Refresh automatique des challenges...")
            # Émettre le signal pour déclencher le refresh dans le thread principal
            self.refresh_request.emit()

        except Exception as e:
            self.log(f"Erreur lors du refresh automatique: {e}")

    def toggle_auto_refresh(self, enabled):
        """Activer/désactiver le refresh automatique"""
        self.auto_refresh_enabled = enabled
        if self.scheduler:
            if enabled:
                self.log("Refresh automatique activé")
            else:
                self.log("Refresh automatique désactivé")

    def purge_closed_challenges(self):
            """Supprime les challenges fermés de la liste"""
            try:
                if not hasattr(self, 'all_challenges'):
                    return

                now = datetime.now()
                challenges_removed = 0

                for player in list(self.all_challenges.keys()):
                    challenges_to_remove = []

                    for challenge in list(self.all_challenges[player]):
                        try:
                            # Convertir end_time en datetime
                            end_time = datetime.strptime(challenge.end_time.strip(), "%d/%m/%Y, %H:%M")
                            if now > end_time:
                                challenges_to_remove.append(challenge)
                        except Exception as e:
                            self.log(f"Erreur lors de la vérification de fin pour {challenge.title}: {e}")

                    # Supprimer les challenges fermés
                    for challenge in challenges_to_remove:
                        self.all_challenges[player].discard(challenge)
                        challenges_removed += 1
                        self.log(f"Challenge fermé supprimé pour {player}: {challenge.title}")

                if challenges_removed > 0:
                    self.log(f"Suppression automatique de {challenges_removed} challenge(s) fermé(s)")
                    # Mettre à jour l'interface seulement si on a supprimé des challenges
                    self.schedule_update()

            except Exception as e:
                self.log(f"Erreur lors de la suppression des challenges fermés: {e}")

    def closeEvent(self, event):
            """Gestionnaire de fermeture de la fenêtre - arrêter le scheduler"""
            try:
                if hasattr(self, 'scheduler') and self.scheduler:
                    self.scheduler.shutdown()
                    self.log("APScheduler arrêté")
            except Exception as e:
                self.log(f"Erreur lors de l'arrêt d'APScheduler: {e}")

            # Arrêter les autres threads/workers si nécessaire
            if hasattr(self, 'bye'):
                self.bye = True

            event.accept()

    # 3. Modifier init_ui pour ajouter des contrôles du scheduler
    def init_ui_refresh(self):
        # ... code existant jusqu'aux boutons du haut ...

        # Top bar avec les boutons existants + contrôles scheduler
        top_bar = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_challenges)

        all_button = QPushButton("All")
        all_button.clicked.connect(self.sel_all)

        none_button = QPushButton("None")
        none_button.clicked.connect(self.sel_none)

        # Nouveau: Bouton pour activer/désactiver le refresh automatique
        self.auto_refresh_button = QPushButton("Auto Refresh: ON")
        self.auto_refresh_button.setCheckable(True)
        self.auto_refresh_button.setChecked(True)
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh_ui)

        # Nouveau: Label pour afficher le statut du scheduler
        self.scheduler_status_label = QLabel("Scheduler: Actif")
        self.scheduler_status_label.setStyleSheet("color: green; font-weight: bold;")

        top_bar.addWidget(refresh_button)
        top_bar.addWidget(all_button)
        top_bar.addWidget(none_button)
        top_bar.addWidget(self.auto_refresh_button)  # Nouveau
        top_bar.addWidget(self.scheduler_status_label)  # Nouveau
        top_bar.addStretch()

        # ... reste du code existant pour profile_label, etc. ...

    def toggle_auto_refresh_ui(self):
        """Gestionnaire pour le bouton de toggle du refresh automatique"""
        enabled = self.auto_refresh_button.isChecked()
        self.toggle_auto_refresh(enabled)

        if enabled:
            self.auto_refresh_button.setText("Auto Refresh: ON")
            self.scheduler_status_label.setText("Scheduler: Actif")
            self.scheduler_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.auto_refresh_button.setText("Auto Refresh: OFF")
            self.scheduler_status_label.setText("Scheduler: Inactif")
            self.scheduler_status_label.setStyleSheet("color: red; font-weight: bold;")

    # 4. Méthodes pour programmer des votes à des heures précises
    def schedule_vote_at_time(self, challenge, vote_count, timing_spec, task_description=None, *args):
        """
        Programme un vote à une heure précise
        
        Args:
            challenge: L'objet challenge
            vote_count: Nombre de votes à effectuer
            timing_spec: Spécification du timing:
                - "now" : maintenant
                - "end-4m0s" : 4 minutes avant la fin
                - "end-0m30s" : 30 secondes avant la fin
                - "14:30:00" : heure absolue (HH:MM:SS)
            task_description: Description optionnelle de la tâche
        """
        try:
            if not self.scheduler:
                self.log("Scheduler non disponible")
                return False

            # Calculer l'heure de déclenchement
            trigger_time = self.parse_timing_spec(challenge, timing_spec)
            if not trigger_time:
                return False

            # Générer un ID unique pour la tâche avec le profil
            task_id = f"vote_{self.player}_{challenge.id}_{timing_spec}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Description par défaut
            if not task_description:
                task_description = f"Vote sur {challenge.title} à {timing_spec}"

            # Programmer la tâche
            self.scheduler.add_job(
                func=lambda: self.execute_scheduled_vote(challenge, vote_count, task_id),
                trigger='date',
                run_date=trigger_time,
                id=task_id,
                name=task_description,
                replace_existing=True
            )

            self.log(f"Vote programmé: {task_description}")
            self.log(f"  - Challenge: {challenge.title}")
            self.log(f"  - Heure de déclenchement: {trigger_time.strftime('%d/%m/%Y %H:%M:%S')}")
            self.log(f"  - Votes: {vote_count}")
            self.log(f"  - ID tâche: {task_id}")
            
            return True

        except Exception as e:
            self.log(f"Erreur lors de la programmation du vote: {e}")
            return False

    def parse_timing_spec(self, challenge, timing_spec):
        """Parse les spécifications de timing et retourne un datetime"""
        try:
            current_time = datetime.now()
            
            # Cas 1: "now" - maintenant
            if timing_spec.lower() == "now":
                return current_time
            
            # Cas 2: Format absolu "HH:MM:SS"
            if ":" in timing_spec and not timing_spec.startswith(("end-", "next-")):
                try:
                    time_parts = timing_spec.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2]) if len(time_parts) > 2 else 0
                    
                    # Créer le datetime pour aujourd'hui à cette heure
                    target_time = current_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
                    
                    # Si l'heure est déjà passée aujourd'hui, programmer pour demain
                    if target_time <= current_time:
                        target_time += timedelta(days=1)
                    
                    return target_time
                except ValueError:
                    self.log(f"Format d'heure invalide: {timing_spec}")
                    return None
            
            # Cas 3: Format relatif "end-XmYs"
            if timing_spec.startswith("end-"):
                # Parser le format "end-4m30s" ou "end-0m30s"
                offset_str = timing_spec[4:]  # Enlever "end-"
                
                # Extraire minutes et secondes
                minutes = 0
                seconds = 0
                
                # Chercher les minutes
                if "m" in offset_str:
                    m_pos = offset_str.find("m")
                    minutes = int(offset_str[:m_pos])
                    offset_str = offset_str[m_pos+1:]
                
                # Chercher les secondes
                if "s" in offset_str:
                    s_pos = offset_str.find("s")
                    seconds = int(offset_str[:s_pos])
                
                # Calculer l'offset total en secondes
                total_offset = (minutes * 60) + seconds
                
                # Calculer l'heure de fin du challenge
                end_datetime = datetime.strptime(challenge.end_time.strip(), "%d/%m/%Y, %H:%M")
                
                # Calculer l'heure de déclenchement
                trigger_time = end_datetime - timedelta(seconds=total_offset)
                
                self.log(f"Calcul timing relatif end:")
                self.log(f"  - Fin du challenge: {end_datetime.strftime('%d/%m/%Y %H:%M:%S')}")
                self.log(f"  - Offset: -{minutes}m{seconds}s ({total_offset}s)")
                self.log(f"  - Déclenchement: {trigger_time.strftime('%d/%m/%Y %H:%M:%S')}")
                
                return trigger_time
            
            # Cas 4: Format relatif "next-XmYs" - NOUVEAU
            if timing_spec.startswith("next-"):
                # Parser le format "next-1m30s" ou "next-0m30s"
                offset_str = timing_spec[5:]  # Enlever "next-"
                
                # Extraire minutes et secondes
                minutes = 0
                seconds = 0
                
                # Chercher les minutes
                if "m" in offset_str:
                    m_pos = offset_str.find("m")
                    minutes = int(offset_str[:m_pos])
                    offset_str = offset_str[m_pos+1:]
                
                # Chercher les secondes
                if "s" in offset_str:
                    s_pos = offset_str.find("s")
                    seconds = int(offset_str[:s_pos])
                
                # Calculer l'heure de déclenchement : prochaine minute pleine + offset
                # Exemple: now=11:31:18, next-1m0s → 11:32:00, next-1m30s → 11:32:30
                next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
                trigger_time = next_minute + timedelta(minutes=minutes-1, seconds=seconds)
                
                self.log(f"Calcul timing relatif next:")
                self.log(f"  - Heure actuelle: {current_time.strftime('%d/%m/%Y %H:%M:%S')}")
                self.log(f"  - Prochaine minute: {next_minute.strftime('%d/%m/%Y %H:%M:%S')}")
                self.log(f"  - Offset: +{minutes-1}m{seconds}s depuis la prochaine minute")
                self.log(f"  - Déclenchement: {trigger_time.strftime('%d/%m/%Y %H:%M:%S')}")
                
                return trigger_time
            
            self.log(f"Format de timing non reconnu: {timing_spec}")
            return None
            
        except Exception as e:
            self.log(f"Erreur lors du parsing du timing '{timing_spec}': {e}")
            return None

    def execute_scheduled_vote(self, challenge, vote_count, task_id):
        """Exécute un vote programmé"""
        try:
            self.log(f"Exécution du vote programmé: {task_id}")
            self.log(f"Challenge: {challenge.title}, Votes: {vote_count}")
            
            # Émettre le signal de vote (thread-safe)
            self.vote_request.emit(challenge, vote_count, task_id)
            
        except Exception as e:
            self.log(f"Erreur lors de l'exécution du vote programmé {task_id}: {e}")

    def schedule_swap_at_time(self, challenge, count, timing_spec, *args):
        """Programme un swap à une heure spécifique (à implémenter)"""
        # TODO: Implémenter la logique de swap
        args_str = f" avec args: {args}" if args else ""
        self.log(f"🚧 schedule_swap_at_time pas encore implémenté: {count} swaps à {timing_spec}{args_str}")
        return False

    def schedule_turbo_at_time(self, challenge, count, timing_spec, *args):
        """Programme un turbo à une heure spécifique (à implémenter)"""
        # TODO: Implémenter la logique de turbo
        args_str = f" avec args: {args}" if args else ""
        self.log(f"🚧 schedule_turbo_at_time pas encore implémenté: {count} turbos à {timing_spec}{args_str}")
        return False

    def schedule_multiple_votes(self, challenge, vote_strategy):
        """
        Programme plusieurs actions selon une stratégie
        
        Args:
            challenge: L'objet challenge
            vote_strategy: Liste de tuples (method, timing_spec, count)
                Exemple: [("vote", "end-4m0s", 10), ("swap", "end-0m30s", 25)]
        """
        scheduled_count = 0
        for strategy_step in vote_strategy:
            if len(strategy_step) >= 3:
                # Nouveau format avec arguments variables: method,timing_spec,count[,*args]
                method = strategy_step[0]
                timing_spec = strategy_step[1]
                count = strategy_step[2]
                args = strategy_step[3:] if len(strategy_step) > 3 else []
                
                if method == "vote":
                    if self.schedule_vote_at_time(challenge, count, timing_spec, None, *args):
                        scheduled_count += 1
                elif method == "swap":
                    if self.schedule_swap_at_time(challenge, count, timing_spec, *args):
                        scheduled_count += 1
                elif method == "turbo":
                    if self.schedule_turbo_at_time(challenge, count, timing_spec, *args):
                        scheduled_count += 1
                else:
                    self.log(f"❌ Méthode inconnue: {method}")
            elif len(strategy_step) == 2:
                # Ancien format pour compatibilité: timing_spec,count
                timing_spec, count = strategy_step
                if self.schedule_vote_at_time(challenge, count, timing_spec):
                    scheduled_count += 1
        
        self.log(f"Stratégie programmée: {scheduled_count}/{len(vote_strategy)} votes pour {challenge.title}")
        return scheduled_count == len(vote_strategy)

    def load_timing_strategies(self):
        """Charge les stratégies de timing depuis strategies.ini (recharge le fichier à chaque appel)"""
        timing_strategies = {}
        try:
            # Recharger le fichier strategies.ini depuis le disque
            from configobj import ConfigObj
            strategies_config = ConfigObj('strategies.ini')
            
            self.log("🔄 Rechargement des stratégies depuis strategies.ini")
            
            # Charger toutes les sections sauf 'timing_strategies' et les legacy
            #legacy_sections = {'end4', 'end3', 'end2', 'fills', 'timing_strategies'}
            
            for section_name in strategies_config.sections:
                strategy_data = []
                description = strategies_config[section_name].get('description', f'Stratégie {section_name}')

                # Charger les étapes de la stratégie
                step_keys = [key for key in strategies_config[section_name].keys() if key.isdigit()]
                step_keys.sort(key=int)  # Trier par ordre numérique

                for step_key in step_keys:
                    step_value = strategies_config[section_name][step_key]
                    # Nouveau format étendu: "vote,end-4m0s,10,arg1,arg2" ou "end-4m0s,10"
                    parts = [p.strip() for p in step_value.split(',')]
                    
                    if len(parts) >= 3:
                        # Nouveau format: method,timing_spec,count[,*args]
                        method = parts[0].strip()
                        timing_spec = parts[1].strip()
                        count = int(parts[2].strip())
                        args = parts[3:] if len(parts) > 3 else []  # Arguments supplémentaires
                        strategy_data.append((method, timing_spec, count, *args))
                    elif len(parts) == 2:
                        # Ancien format: timing_spec,count (compatibilité)
                        timing_spec = parts[0].strip()
                        count = int(parts[1].strip())
                        strategy_data.append(("vote", timing_spec, count))  # Méthode par défaut
                    else:
                        self.log(f"⚠️ Format invalide pour {section_name}.{step_key}: {step_value}")

                if strategy_data:
                    timing_strategies[section_name] = {
                        'description': description,
                        'steps': strategy_data
                    }
                    self.log(f"✅ Stratégie chargée: {section_name} - {description}")
            
            self.log(f"🎯 Total: {len(timing_strategies)} stratégies de timing rechargées depuis le fichier")
            return timing_strategies
            
        except Exception as e:
            self.log(f"Erreur lors du chargement des stratégies de timing: {e}")
            return {}

    def apply_timing_strategy(self, challenge, strategy_name):
        """Applique une stratégie de timing à un challenge"""
        try:
            timing_strategies = self.load_timing_strategies()
            
            if strategy_name not in timing_strategies:
                self.log(f"Stratégie '{strategy_name}' non trouvée")
                return False
            
            strategy = timing_strategies[strategy_name]
            self.log(f"Application de la stratégie '{strategy_name}': {strategy['description']}")
            
            # Programmer tous les votes de la stratégie
            success = self.schedule_multiple_votes(challenge, strategy['steps'])
            
            if success:
                self.log(f"Stratégie '{strategy_name}' appliquée avec succès à {challenge.title}")
                
                # Mettre à jour la colonne "Stratégie" avec le nom de la stratégie
                for row in range(self.challenge_table.rowCount()):
                    if self.challenge_table.item(row, 1).text() == challenge.title:
                        self.challenge_table.setItem(row, 9, self.create_centered_item(strategy_name))
                        break
                
                # Sauvegarder la stratégie dans la configuration au même moment
                self.save_scheduled_strategy(challenge, strategy_name)
            else:
                self.log(f"Erreur lors de l'application de la stratégie '{strategy_name}'")
            
            return success
            
        except Exception as e:
            self.log(f"Erreur lors de l'application de la stratégie '{strategy_name}': {e}")
            return False

    def save_scheduled_strategy(self, challenge, strategy_name):
        """Sauvegarde une stratégie programmée dans la configuration"""
        try:
            self.log(f"🔧 DEBUG: Début sauvegarde stratégie '{strategy_name}' pour challenge ID: {challenge.id}")
            
            # S'assurer que la section scheduled_strategies existe
            if not self.config['players'][self.player].get('scheduled_strategies'):
                self.config['players'][self.player]['scheduled_strategies'] = {}
                self.log(f"🔧 DEBUG: Section scheduled_strategies créée")
            
            # Convertir end_time en string pour ConfigObj
            end_time_str = challenge.end_time
            if hasattr(challenge.end_time, 'strftime'):
                end_time_str = challenge.end_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Sauvegarder la stratégie avec un timestamp
            strategy_info = {
                'strategy_name': strategy_name,
                'scheduled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'challenge_title': challenge.title,
                'challenge_end_time': str(end_time_str)
            }
            
            self.log(f"🔧 DEBUG: Strategy info à sauvegarder: {strategy_info}")
            
            # Sauvegarder chaque clé individuellement pour ConfigObj
            # Convertir l'ID en string car ConfigObj exige des clés string
            challenge_id_str = str(challenge.id)
            challenge_section = self.config['players'][self.player]['scheduled_strategies']
            challenge_section[challenge_id_str] = {}
            challenge_section[challenge_id_str]['strategy_name'] = strategy_name
            challenge_section[challenge_id_str]['scheduled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            challenge_section[challenge_id_str]['challenge_title'] = challenge.title
            challenge_section[challenge_id_str]['challenge_end_time'] = str(end_time_str)
            
            self.config.write()
            
            self.log(f"💾 Stratégie '{strategy_name}' sauvegardée pour {challenge.title}")
            self.log(f"🔧 DEBUG: Fichier config écrit avec succès")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde de la stratégie: {e}")
            import traceback
            self.log(f"🔧 DEBUG: Traceback complet: {traceback.format_exc()}")

    def remove_scheduled_strategy(self, challenge_id):
        """Supprime une stratégie programmée de la configuration"""
        try:
            # Convertir l'ID en string car ConfigObj utilise des clés string
            challenge_id_str = str(challenge_id)
            if (self.config['players'][self.player].get('scheduled_strategies') and 
                challenge_id_str in self.config['players'][self.player]['scheduled_strategies']):
                
                strategy_info = self.config['players'][self.player]['scheduled_strategies'][challenge_id_str]
                del self.config['players'][self.player]['scheduled_strategies'][challenge_id_str]
                self.config.write()
                
                self.log(f"🗑️ Stratégie supprimée de la config: {strategy_info.get('strategy_name', 'Unknown')}")
                
        except Exception as e:
            self.log(f"Erreur lors de la suppression de la stratégie: {e}")

    def load_and_restore_scheduled_strategies(self):
        """Charge et restaure les stratégies programmées au démarrage"""
        try:
            if not self.config['players'][self.player].get('scheduled_strategies'):
                self.log("Aucune stratégie programmée à restaurer")
                return 0
            
            # Debug : vérifier que les challenges sont disponibles
            available_challenges = self.all_challenges.get(self.player, [])
            self.log(f"🔧 DEBUG: {len(available_challenges)} challenges disponibles pour restauration")
            
            scheduled_strategies = self.config['players'][self.player]['scheduled_strategies']
            restored_count = 0
            invalid_strategies = []
            
            self.log("🔄 Restauration des stratégies programmées...")
            
            for challenge_id_str, strategy_info in scheduled_strategies.items():
                # Convertir l'ID string en int pour la comparaison
                challenge_id = int(challenge_id_str)
                # Trouver le challenge correspondant
                challenge = next((c for c in self.all_challenges.get(self.player, []) if c.id == challenge_id), None)
                
                if challenge:
                    strategy_name = strategy_info.get('strategy_name')
                    if strategy_name:
                        # Vérifier si la stratégie existe encore
                        timing_strategies = self.load_timing_strategies()
                        if strategy_name in timing_strategies:
                            success = self.apply_timing_strategy(challenge, strategy_name)
                            if success:
                                restored_count += 1
                                self.log(f"✅ Stratégie '{strategy_name}' restaurée pour {challenge.title}")
                            else:
                                self.log(f"❌ Échec restauration stratégie '{strategy_name}' pour {challenge.title}")
                                invalid_strategies.append(challenge_id_str)
                        else:
                            self.log(f"⚠️ Stratégie '{strategy_name}' n'existe plus")
                            invalid_strategies.append(challenge_id_str)
                else:
                    challenge_title = strategy_info.get('challenge_title', 'Inconnu')
                    self.log(f"⚠️ Challenge non trouvé: {challenge_title} (ID: {challenge_id})")
                    invalid_strategies.append(challenge_id_str)
            
            # Nettoyer les stratégies invalides
            for challenge_id in invalid_strategies:
                self.remove_scheduled_strategy(challenge_id)
            
            if restored_count > 0:
                self.log(f"🎯 {restored_count} stratégie(s) restaurée(s) avec succès")
            
            return restored_count
            
        except Exception as e:
            self.log(f"Erreur lors de la restauration des stratégies: {e}")
            return 0

    def on_job_finished(self, event):
        """Callback appelé quand un job APScheduler se termine (succès ou erreur)"""
        try:
            job_id = event.job_id
            
            # Ne traiter que les jobs de vote
            if not job_id.startswith('vote_'):
                return
            
            # Extraire les infos depuis le job_id (format: vote_PROFILE_CHALLENGE_ID_timing_timestamp)
            parts = job_id.split('_')
            if len(parts) < 4:
                return
            
            profile = parts[1]
            challenge_id = parts[2]
            
            # Router vers le bon profil
            self.route_job_notification_to_profile(profile, challenge_id, job_id)
                
        except Exception as e:
            self.log(f"❌ Erreur dans on_job_finished: {e}")

    def route_job_notification_to_profile(self, target_profile, challenge_id, job_id):
        """Route une notification de fin de job vers le bon profil"""
        try:
            # Vérifier s'il reste d'autres jobs pour ce challenge/profil
            remaining_jobs = self.count_scheduled_votes_for_challenge_and_profile(challenge_id, target_profile)
            
            self.log(f"🔍 Job terminé: {job_id} - Jobs restants pour {target_profile}/challenge {challenge_id}: {remaining_jobs}")
            
            # S'il n'y a plus de jobs pour ce challenge/profil, nettoyer
            if remaining_jobs == 0:
                self.log(f"🧹 Nettoyage automatique: stratégie terminée pour {target_profile}/challenge {challenge_id}")
                
                # Si c'est le profil actuel, faire le nettoyage complet
                if target_profile == self.player:
                    # Supprimer de la configuration
                    self.remove_scheduled_strategy(challenge_id)
                    
                    # Mettre à jour l'UI (thread-safe)
                    QMetaObject.invokeMethod(self, "clear_strategy_display_for_challenge", 
                                           Qt.QueuedConnection, 
                                           Q_ARG(str, challenge_id))
                else:
                    # Pour un autre profil, nettoyer seulement la config (pas l'UI actuelle)
                    self.remove_scheduled_strategy_for_profile(challenge_id, target_profile)
                
        except Exception as e:
            self.log(f"❌ Erreur dans route_job_notification_to_profile: {e}")

    def count_scheduled_votes_for_challenge_and_profile(self, challenge_id, profile):
        """Compte le nombre de votes programmés pour un challenge et un profil spécifique"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        try:
            jobs = self.scheduler.get_jobs()
            count = 0
            for job in jobs:
                # Format: vote_PROFILE_CHALLENGE_ID_timing_timestamp
                if job.id.startswith(f'vote_{profile}_{challenge_id}_'):
                    count += 1
            return count
        except:
            return 0

    def remove_scheduled_strategy_for_profile(self, challenge_id, profile):
        """Supprime une stratégie programmée de la configuration pour un profil spécifique"""
        try:
            # Convertir l'ID en string car ConfigObj utilise des clés string
            challenge_id_str = str(challenge_id)
            if (self.config['players'].get(profile) and
                self.config['players'][profile].get('scheduled_strategies') and 
                challenge_id_str in self.config['players'][profile]['scheduled_strategies']):
                
                strategy_info = self.config['players'][profile]['scheduled_strategies'][challenge_id_str]
                del self.config['players'][profile]['scheduled_strategies'][challenge_id_str]
                self.config.write()
                
                self.log(f"🗑️ Stratégie supprimée de la config pour {profile}: {strategy_info.get('strategy_name', 'Unknown')}")
                
        except Exception as e:
            self.log(f"Erreur lors de la suppression de la stratégie pour {profile}: {e}")

    @Slot(str)
    def clear_strategy_display_for_challenge(self, challenge_id):
        """Met à jour l'affichage pour vider la colonne stratégie d'un challenge spécifique"""
        try:
            # Trouver le challenge par ID
            challenge = next((c for c in self.all_challenges.get(self.player, []) if str(c.id) == str(challenge_id)), None)
            
            if challenge:
                # Trouver la ligne dans le tableau et vider la colonne stratégie
                for row in range(self.challenge_table.rowCount()):
                    if self.challenge_table.item(row, 1).text() == challenge.title:
                        self.challenge_table.setItem(row, 9, self.create_centered_item(""))
                        self.log(f"🎯 Colonne stratégie vidée pour {challenge.title}")
                        break
                        
        except Exception as e:
            self.log(f"❌ Erreur lors de la mise à jour de l'affichage: {e}")

    def cleanup_finished_strategies(self):
        """Nettoyage périodique des stratégies dont tous les jobs sont terminés"""
        try:
            if not self.config['players'][self.player].get('scheduled_strategies'):
                return
            
            scheduled_strategies = self.config['players'][self.player]['scheduled_strategies']
            to_cleanup = []
            
            for challenge_id_str, strategy_info in scheduled_strategies.items():
                # Compter les jobs restants pour ce challenge
                remaining_jobs = self.count_scheduled_votes_for_challenge(challenge_id_str)
                
                if remaining_jobs == 0:
                    strategy_name = strategy_info.get('strategy_name', 'Unknown')
                    challenge_title = strategy_info.get('challenge_title', 'Unknown')
                    
                    self.log(f"🧹 Nettoyage différé: stratégie '{strategy_name}' terminée pour {challenge_title}")
                    to_cleanup.append(challenge_id_str)
            
            # Nettoyer les stratégies terminées
            for challenge_id_str in to_cleanup:
                self.remove_scheduled_strategy(challenge_id_str)
                
                # Mettre à jour l'UI
                QMetaObject.invokeMethod(self, "clear_strategy_display_for_challenge", 
                                       Qt.QueuedConnection, 
                                       Q_ARG(str, challenge_id_str))
            
            if to_cleanup:
                self.log(f"🧹 Nettoyage périodique terminé: {len(to_cleanup)} stratégie(s) supprimée(s)")
                
        except Exception as e:
            self.log(f"❌ Erreur lors du nettoyage périodique: {e}")

    def test_multiprofile_jobs(self):
        """Teste que les jobs sont correctement préfixés par profil"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            self.log("❌ Scheduler non disponible pour le test")
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
            
            self.log("🧪 Test Multi-Profil - Répartition des jobs par profil:")
            for profile, count in profile_jobs.items():
                self.log(f"   📊 {profile}: {count} job(s)")
            
            if not profile_jobs:
                self.log("   ⚪ Aucun job de vote trouvé")
            
        except Exception as e:
            self.log(f"❌ Erreur lors du test multi-profil: {e}")

    def edit_config_file(self):
        """Ouvre le fichier gsgui.ini dans un éditeur"""
        try:
            import platform
            import subprocess
            import os
            
            config_file = os.path.abspath('gsgui.ini')
            
            if not os.path.exists(config_file):
                self.log(f"❌ Fichier de configuration non trouvé: {config_file}")
                return
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-t", config_file])
            elif system == "Windows":
                subprocess.run(["notepad.exe", config_file])
            elif system == "Linux":
                # Essayer différents éditeurs
                editors = ["gedit", "kate", "nano", "vi"]
                for editor in editors:
                    try:
                        subprocess.run([editor, config_file])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    subprocess.run(["xdg-open", config_file])
            
            self.log(f"📝 Ouverture de {config_file} dans l'éditeur")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'ouverture du fichier config: {e}")

    def edit_strategies_file(self):
        """Ouvre le fichier strategies.ini dans un éditeur"""
        try:
            import platform
            import subprocess
            import os
            
            strategies_file = os.path.abspath('strategies.ini')
            
            if not os.path.exists(strategies_file):
                self.log(f"❌ Fichier de stratégies non trouvé: {strategies_file}")
                return
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-t", strategies_file])
            elif system == "Windows":
                subprocess.run(["notepad.exe", strategies_file])
            elif system == "Linux":
                # Essayer différents éditeurs
                editors = ["gedit", "kate", "nano", "vi"]
                for editor in editors:
                    try:
                        subprocess.run([editor, strategies_file])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    subprocess.run(["xdg-open", strategies_file])
            
            self.log(f"📝 Ouverture de {strategies_file} dans l'éditeur")
            self.log(f"💡 Les modifications seront automatiquement prises en compte au prochain clic sur 'Lancer une stratégie de fin'")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'ouverture du fichier strategies: {e}")

    def clear_all_scheduled_strategies(self):
        """Supprime toutes les stratégies programmées de la configuration"""
        try:
            if not self.config['players'][self.player].get('scheduled_strategies'):
                return 0
            
            count = len(self.config['players'][self.player]['scheduled_strategies'])
            self.config['players'][self.player]['scheduled_strategies'] = {}
            self.config.write()
            
            self.log(f"🗑️ Toutes les stratégies programmées ont été supprimées de la configuration")
            return count
            
        except Exception as e:
            self.log(f"Erreur lors de la suppression des stratégies: {e}")
            return 0

    def get_available_timing_strategies(self):
        """Retourne la liste des stratégies de timing disponibles"""
        timing_strategies = self.load_timing_strategies()
        return [(name, data['description']) for name, data in timing_strategies.items()]

    def save_timing_strategy(self, strategy_name, strategy_steps, description=""):
        """Sauvegarde une nouvelle stratégie de timing"""
        try:
            # Ajouter la nouvelle stratégie
            if strategy_name not in self.strategies.sections:
                self.strategies[strategy_name] = {}
            
            # Effacer les anciens steps
            for key in list(self.strategies[strategy_name].keys()):
                if key.isdigit():
                    del self.strategies[strategy_name][key]
            
            # Ajouter la description
            if description:
                self.strategies[strategy_name]['description'] = description
            
            # Ajouter les nouveaux steps
            for i, (timing_spec, vote_count) in enumerate(strategy_steps):
                self.strategies[strategy_name][str(i)] = f"{timing_spec},{vote_count}"
            
            # Sauvegarder le fichier
            self.strategies.write()
            self.log(f"Stratégie '{strategy_name}' sauvegardée avec succès")
            return True
            
        except Exception as e:
            self.log(f"Erreur lors de la sauvegarde de la stratégie '{strategy_name}': {e}")
            return False

    # 5. Optionnel: Méthodes pour gérer des tâches programmées spécifiques
    def schedule_custom_task(self, func, trigger_time, task_id, description="Tâche personnalisée"):
        """Ajoute une tâche programmée personnalisée"""
        try:
            if not self.scheduler:
                self.log("Scheduler non disponible")
                return False

            self.scheduler.add_job(
                func=func,
                trigger='date',
                run_date=trigger_time,
                id=task_id,
                name=description,
                replace_existing=True
            )

            self.log(f"Tâche programmée: {description} à {trigger_time}")
            return True

        except Exception as e:
            self.log(f"Erreur lors de la programmation de la tâche: {e}")
            return False

    def remove_scheduled_task(self, task_id):
        """Supprime une tâche programmée"""
        try:
            if self.scheduler and self.scheduler.get_job(task_id):
                self.scheduler.remove_job(task_id)
                self.log(f"Tâche supprimée: {task_id}")
                return True
        except Exception as e:
            self.log(f"Erreur lors de la suppression de la tâche {task_id}: {e}")
        return False

    def list_scheduled_jobs(self):
        """Liste toutes les tâches programmées"""
        try:
            if not self.scheduler:
                self.log("Scheduler non disponible")
                return

            jobs = self.scheduler.get_jobs()
            if jobs:
                self.log("Tâches programmées:")
                for job in jobs:
                    next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
                    self.log(f"  - {job.name} (ID: {job.id}) - Prochaine exécution: {next_run}")
            else:
                self.log("Aucune tâche programmée")

        except Exception as e:
            self.log(f"Erreur lors de la liste des tâches: {e}")
    def set_player(self, player):
        self.config['player'] = player
        self.config.write()

    def init_player(self, player):

        self.strategies = ConfigObj('strategies.ini')

        self.sem = asyncio.Semaphore(100)
        
        # Verrou pour protéger l'accès concurrent à la configuration
        if not hasattr(self, 'config_lock'):
            self.config_lock = threading.Lock()

        self.player = player
        self.set_player(self.player)

        args = self.parser.parse_args()
        args.player = self.player

        # S'assurer que la structure de configuration existe pour ce joueur
        if not self.config['players'].get(args.player):
            self.log(f"Configuration manquante pour le joueur {args.player}. Initialisation...")
            self.config['players'][args.player] = {'xtoken': ''}
            self.config.write()
            
        if self.config['players'][args.player].get('xtoken') == '':
                self.config['players'][args.player]['xtoken'] = self.get_xtoken_from_browser()
                self.config.write()

        self.xtoken = self.config['players'][args.player]['xtoken']

        self.threads={}
        self.bye = False  # Réinitialiser le drapeau d'arrêt des threads

        self.fetcher = AsyncFetcher(header=self.aio_connect_session())
        self.fetcher.finished.connect(self.on_challenges_fetched)
        self.fetcher.vote_finished.connect(self.on_vote_finished)  # Connect new signal
        self.fetcher.get_votes_panel_finished.connect(self.on_get_votes_panel_fetched)  # Connect new signal
        self.fetcher.post_votes_panel_finished.connect(self.on_post_votes_panel_fetched)  # Connect new signal

        # Initialiser un dictionnaire de challenges par profil
        if not hasattr(self, 'all_challenges'):
            self.all_challenges = {}
        
        # Initialiser le set de challenges pour ce profil
        if self.player not in self.all_challenges:
            self.all_challenges[self.player] = set()
            
        # Pour la compatibilité avec le code existant
        #self.challenges = self.all_challenges[self.player]
        self.selected_challenges = set()

        self.profiles = []
        #for player in self.config['players'].keys():
        #    self.profiles.append(player)
        self.profiles.append(self.player)
        # Connecter le signal de vote à la méthode de vote
        self.vote_request.connect(self.vote_challenge)
        # Connecter le signal de refresh à la méthode de refresh
        self.refresh_request.connect(self.fetch_challenges)
        # Connecter le signal de mise à jour GUI
        self.update_gui_request.connect(self.update_challenge_table)
        
        # Timer pour nettoyer les processus bloqués
        self.process_monitor_timer = QTimer(self)
        self.process_monitor_timer.timeout.connect(self.check_stalled_processes)
        self.process_monitor_timer.start(60000)  # Vérifier toutes les minutes
        
        self.init_ui()
        self.fetcher.set_log(self.result_panel)
        
        # Flag pour éviter de restaurer plusieurs fois
        self.strategies_restored = False



    def log(self, *args):
        # Créer le texte à ajouter
        text = "".join([str(e) for e in args])
        
        # Ajouter un timestamp au message de log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {text}"
        
        # Écrire dans le fichier de logs
        try:
            # Créer le répertoire logs s'il n'existe pas
            log_dir = os.path.join(os.path.dirname(os.path.abspath('gsgui.ini')), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Définir le chemin du fichier de log (un fichier par jour)
            log_file = os.path.join(log_dir, f"gsgui_{datetime.now().strftime('%Y-%m-%d')}.log")
            
            # Écrire dans le fichier en mode append
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            # En cas d'erreur, on continue sans bloquer l'affichage dans l'UI
            print(f"Erreur lors de l'écriture dans le fichier de logs: {e}")
        
        # Utiliser QTimer.singleShot pour ajouter le texte de manière thread-safe
        try:
            # Vérifier si nous sommes dans le thread principal
            from PySide6.QtCore import QThread
            if QThread.currentThread() == self.thread():
                # Thread principal - mise à jour directe
                self.result_panel.append(text)
            else:
                # Thread secondaire - utiliser QTimer.singleShot
                QTimer.singleShot(0, lambda: self.result_panel.append(text))
        except Exception as e:
            # En cas d'erreur, juste print sans bloquer
            print(f"Log UI error: {e} - Message: {text}")


    def strategie(self, args):
        if args.start:
            sel = self.challenge
            if args.cha:
                for section in self.all_challenges[self.player].keys():
                    if args.cha in section:
                        sel = section
            for _strategie in self.strategies.keys():
                if args.st in _strategie:
                    for step in self.strategies[_strategie].keys():
                        cmd = ' --cha ' + str(sel) + ' ' + self.strategies[_strategie][step]
                        cmd_args = self.parser.parse_args(cmd.split())
                        cmd_args.cmde = cmd
                        cmd_args.func(cmd_args)

        if args.list:
            for strategie in self.strategies.keys():
                self.log(f'strategie :  {{strategie}}')
                for step in self.strategies[strategie].keys():
                    self.log(f'(step :  {{step}} {{self.strategies[strategie][step]}}')
        else:
            self.log(args.st)

    def get_xtoken_from_browser(self):
        """Récupère le xtoken directement depuis les cookies du navigateur"""
        try:
            # Essaie différents navigateurs
            for browser_func in [browser_cookie3.chrome, browser_cookie3.firefox, browser_cookie3.safari]:
                try:
                    cookies = browser_func(domain_name='gurushots.com')
                    for cookie in cookies:
                        if cookie.name.lower() in ['gs_t', 'xtoken', 'x-token']:
                            return cookie.value
                except:
                    continue
        except Exception as e:
            print(f"Erreur: {e}")
        return None
    def aio_connect_session(self):
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.xtoken
        }
    # Méthode pour planifier des mises à jour d'interface depuis des threads secondaires
    def schedule_update(self):
        try:
            # Vérifier si nous sommes dans le thread principal
            from PySide6.QtCore import QThread
            if QThread.currentThread() == self.thread():
                # Thread principal - mise à jour directe
                self.update_challenge_table()
            else:
                # Thread secondaire - utiliser QTimer.singleShot
                QTimer.singleShot(0, self.update_challenge_table)
        except Exception as e:
            print(f"Schedule update error: {e}")
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Top bar with refresh button and profile selector
        top_bar = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_challenges)

        all_button = QPushButton("All")
        all_button.clicked.connect(self.sel_all)

        none_button = QPushButton("None")
        none_button.clicked.connect(self.sel_none)

        # Nouveau: Bouton pour activer/désactiver le refresh automatique
        self.auto_refresh_button = QPushButton("Auto Refresh: ON")
        self.auto_refresh_button.setCheckable(True)
        self.auto_refresh_button.setChecked(True)
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh_ui)

        # Nouveau: Label pour afficher le statut du scheduler
        self.scheduler_status_label = QLabel("Scheduler: Actif")
        self.scheduler_status_label.setStyleSheet("color: green; font-weight: bold;")

        top_bar.addWidget(refresh_button)
        top_bar.addWidget(all_button)
        top_bar.addWidget(none_button)
        top_bar.addWidget(self.auto_refresh_button)  # Nouveau
        
        # Bouton Edit Config
        edit_config_button = QPushButton("Edit Config")
        edit_config_button.clicked.connect(self.edit_config_file)
        top_bar.addWidget(edit_config_button)
        
        # Bouton Edit Strategies  
        edit_strategies_button = QPushButton("Edit Strategies")
        edit_strategies_button.clicked.connect(self.edit_strategies_file)
        top_bar.addWidget(edit_strategies_button)
        
        # Bouton Test Multi-Profil
        test_multiprofile_button = QPushButton("Test Multi-Profil")
        test_multiprofile_button.clicked.connect(self.test_multiprofile_jobs)
        top_bar.addWidget(test_multiprofile_button)
        
        top_bar.addWidget(self.scheduler_status_label)
        top_bar.addStretch()

        profile_label = QLabel("Profile:")
        top_bar.addWidget(profile_label)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profiles)
        index = self.profile_combo.findText(self.player)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        top_bar.addWidget(self.profile_combo)

        main_layout.addLayout(top_bar)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Splitter for challenge list and result panel
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # Challenge list
        #self.challenge_list = QListWidget()
        #self.challenge_list.setSelectionMode(QListWidget.NoSelection)
        #splitter.addWidget(self.challenge_list)
        #title, end_time, time_left, url, votes, rank, level, exposure, gps

        # Challenge table
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(10)
        self.challenge_table.setHorizontalHeaderLabels(
            ["Select", "Title", "End Time", "Remaining", "Votes", "Rank", "Level", "Exposure", "GPS", "Stratégie"])
        # Masquer la numérotation des lignes (row headers)
        self.challenge_table.verticalHeader().setVisible(False)
        # Définir Stretch pour toutes les colonnes par défaut
        self.challenge_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Définir ResizeToContents pour les colonnes qui doivent s'ajuster au contenu
        self.challenge_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Title
        self.challenge_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # End Time
        self.challenge_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Remaining
        self.challenge_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Votes
        self.challenge_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Rank
        self.challenge_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents) # Stratégie

        # Center align and bold the header
        font = QFont()
        font.setBold(True)
        for i in range(self.challenge_table.columnCount()):
            self.challenge_table.horizontalHeaderItem(i).setTextAlignment(Qt.AlignCenter)
            self.challenge_table.horizontalHeaderItem(i).setFont(font)

        splitter.addWidget(self.challenge_table)


        # Result panel
        self.result_panel = QTextEdit()  # Initialize result_panel here
        self.result_panel.setReadOnly(True)
        splitter.addWidget(self.result_panel)

        # Set initial sizes for splitter
        splitter.setSizes([400, 200])

        # Bottom buttons
        button_layout = QHBoxLayout()
        fill_button = QPushButton("FILL")
        fin_button = QPushButton("Lancer une stratégie de fin")
        in_progress_button = QPushButton("Stratégies en cours")
        stop_strategy_button = QPushButton("Stop Stratégie")
        stop_all_button = QPushButton("Stop Tous")

        fill_button.clicked.connect(self.fill_selected_challenges)
        fin_button.clicked.connect(self.fin_selected_challenges)
        in_progress_button.clicked.connect(self.show_in_progress_challenges)
        stop_strategy_button.clicked.connect(self.stop_selected_strategies)
        stop_all_button.clicked.connect(self.stop_all_strategies)

        button_layout.addWidget(fill_button)
        button_layout.addWidget(fin_button)
        button_layout.addWidget(in_progress_button)
        button_layout.addWidget(stop_strategy_button)
        button_layout.addWidget(stop_all_button)
        main_layout.addLayout(button_layout)

        # Timer pour mettre à jour l'affichage toutes les secondes
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_challenge_list)
        # self.timer.start(1000)

        # Start fetching challenges
        self.fetch_challenges()

    def fetch_challenges(self):
        self.log("Fetching challenges...")
        self.fetcher.start_fetch()

    @Slot(list)
    def on_challenges_fetched(self, challenges):
        # Ces méthodes sont appelées depuis le thread principal via les signaux,
        # donc pas besoin de QTimer.singleShot ici
        #self.log("Challenges fetching ...")
        
        # S'assurer que le dictionnaire all_challenges existe
        if not hasattr(self, 'all_challenges'):
            self.all_challenges = {}
        
        # S'assurer que le set de challenges existe pour ce profil
        if self.player not in self.all_challenges:
            self.all_challenges[self.player] = set()
            
        # Mettre à jour la référence pour être sûr
        #self.challenges = self.all_challenges[self.player]
            
        # Identifier les nouveaux challenges avant de mettre à jour
        previous_challenges = {c.id for c in self.all_challenges[self.player]} if self.all_challenges[self.player] else set()
        
        # Mettre à jour la liste complète des challenges pour le profil actuel
        sorted_challenges = self.sort_challenges(challenges)
        
        # Initialiser remaining_seconds pour chaque challenge (nouveaux et resync)
        for challenge in sorted_challenges:
            # Toujours recalculer lors d'un fetch (pour la resync)
            if not hasattr(challenge, 'remaining_seconds') or True:
                # Calculer remaining_seconds à partir de end_time ET time_left du serveur
                try:
                    # Méthode 1: Calcul à partir de end_time (peut avoir du décalage)
                    end_datetime = datetime.strptime(challenge.end_time.strip(), "%d/%m/%Y, %H:%M")
                    current_time = datetime.now()
                    remaining_from_end = max(0, (end_datetime - current_time).total_seconds())
                    
                    # Méthode 2: Calcul à partir de time_left du serveur (plus précis)
                    remaining_from_server = self.parse_time_left_to_seconds(challenge.time_left)
                    
                    # Détecter et compenser le décalage
                    time_offset = remaining_from_end - remaining_from_server
                    
                    # Appliquer une correction pour compenser le décalage observé
                    remaining_from_server = max(0, remaining_from_server + self.TIME_CORRECTION_OFFSET)
                    
                    # Utiliser le temps du serveur corrigé
                    challenge.remaining_seconds = remaining_from_server
                    
                    #self.log(f"Challenge {challenge.title}:")
                    #self.log(f"  - Temps calculé: {remaining_from_end}s")
                    #self.log(f"  - Temps serveur brut: {self.parse_time_left_to_seconds(challenge.time_left)}s")
                    #self.log(f"  - Temps serveur corrigé (-{self.TIME_CORRECTION_OFFSET}s): {remaining_from_server}s")
                    #self.log(f"  - Décalage détecté: {time_offset:.1f}s")
                    challenge.time_offset = time_offset
                    
                except Exception as e:
                    self.log(f"Erreur calcul temps restant pour {challenge.title}: {e}")
                    challenge.remaining_seconds = 0
        
        # Réinitialiser le set de challenges pour ce profil
        self.all_challenges[self.player] = set(sorted_challenges)
        
        # Mettre à jour la référence
        #self.challenges = self.all_challenges[self.player]
        
        # Lancer la stratégie de fin par défaut pour chaque nouveau challenge
        new_challenges = []
        for challenge in self.all_challenges[self.player]:
            if challenge.id not in previous_challenges:
                new_challenges.append(challenge)
        
        # Peupler le tableau des challenges
        self.populate_challenge_table()
        
        # Restaurer les stratégies programmées après le premier chargement des challenges
        if not self.strategies_restored:
            self.strategies_restored = True
            QTimer.singleShot(500, self.load_and_restore_scheduled_strategies)
        
        # Lancer les stratégies de fin automatiquement pour les nouveaux challenges
        if new_challenges:
            self.log(f"Lancement automatique des stratégies de fin pour {len(new_challenges)} nouveaux challenges...")
            for challenge in new_challenges:
                self.log(f"Nouveau challenge détecté pour {self.player}: {challenge.title}")
                #self.strategy(challenge)
                
        #self.log(f"Challenges fetched successfully for {self.player}!")
        
        # Rafraîchir l'interface une dernière fois après tout traitement
        self.schedule_update()


    @Slot(list)
    def on_get_votes_panel_fetched(self, challenge, panel, count):
        self.log("Voting fetching ...")
        if count > 0:
            self.voting_challenge(challenge, panel, count)
        else:
            self.post_votes_panel_finished.emit(challenge, {"success": True, "message": 'no vote panel', "challenge": {"close_time": 0}}, 0)
        #sleep(3)
        #self.voting_challenge(challenge, panel, count)

    def on_post_votes_panel_fetched(self, challenge, result):
        success = result.get("success", False) if isinstance(result, dict) else False
        
        # Afficher le résultat du vote
        if success:
            #self.result_panel.append(f'{challenge.title} voted successfully')
            self.log(f'{challenge.title} voted successfully')
        else:
            error_msg = str(result) if not isinstance(result, dict) else f"Vote failed: {result.get('message', 'Unknown error')}"
            self.log(f'{challenge.title} vote failed: {error_msg}')
        
        # Mettre à jour le statut du processus si l'ID est disponible
        if hasattr(challenge, 'current_process_id') and challenge.current_process_id:
            if success:
                # Rechercher le profil propriétaire du processus
                process_owner = self.find_process_owner(challenge.current_process_id)
                if process_owner:
                    self.ps_update(challenge.current_process_id, 'success', process_owner)
                    self.log(f"Processus {challenge.current_process_id} terminé avec succès (profil: {process_owner})")
                else:
                    self.ps_update(challenge.current_process_id, 'success')
                    self.log(f"Processus {challenge.current_process_id} terminé avec succès")
            else:
                # Rechercher le profil propriétaire du processus
                process_owner = self.find_process_owner(challenge.current_process_id)
                if process_owner:
                    self.ps_update(challenge.current_process_id, 'error', process_owner)
                    self.log(f"Processus {challenge.current_process_id} terminé avec erreur (profil: {process_owner})")
                else:
                    self.ps_update(challenge.current_process_id, 'error')
                    self.log(f"Processus {challenge.current_process_id} terminé avec erreur")
            
            # Réinitialiser l'ID du processus et l'heure de début
            challenge.current_process_id = None
            challenge.process_start_time = None
        
        # Rafraîchir les challenges après un délai
        sleep(2)
        self.fetcher.start_fetch()

    @Slot(object, int, str)
    def vote_challenge(self, challenge, count, process_id=None):
        # Challenge details
        self.log(f'{challenge.title} get vote panel')
        
        # Stocker l'ID du processus dans l'objet challenge
        if process_id:
            challenge.current_process_id = process_id
            challenge.process_start_time = datetime.now()  # Enregistrer l'heure de début
            self.log(f"Processus associé: {process_id}")
            
        # Assurer que l'appel à start_get_votes_panel est sécurisé
        try:
            #votes = 0
            #while votes < count:
            self.fetcher.start_get_votes_panel(challenge, count)
            #    sleep(3)
            #    votes += 10
        except Exception as e:
            # En cas d'erreur, mettre à jour le statut du processus
            if challenge.current_process_id and process_id in self.config['players'][self.player]['process']:
                self.ps_update(challenge.current_process_id, 'error')
            challenge.current_process_id = None
            challenge.process_start_time = None
            self.log(f"Erreur lors de l'appel à vote_challenge: {str(e)}")
            


    def voting_challenge(self, challenge, panel, votes):
        if votes < 0:
            #erreur
            self.log(f"Erreur lors de la récupération des données de vote: {str(panel)}")
            return
            
        if not panel.get('challenge') or not panel.get('images'):
            self.log(f"Données de vote incomplètes pour {challenge.title}: {str(panel)}")
            # Rechercher le profil propriétaire du processus
            if hasattr(challenge, 'current_process_id') and challenge.current_process_id:
                process_owner = self.find_process_owner(challenge.current_process_id)
                if process_owner:
                    self.ps_update(challenge.current_process_id, 'error', process_owner)
            return
            
        if panel['challenge']["close_time"] != 0:
            vote_count_max = int(votes)
            vote_count = 0
            vote_index = 0
            votes_panel = []
            vote_data = panel
            
            # Vérifier que nous avons des images à voter
            if len(vote_data.get("images", [])) == 0:
                self.log(f"Aucune image disponible pour voter dans {challenge.title}")
                # Terminer le processus avec erreur
                if hasattr(challenge, 'current_process_id') and challenge.current_process_id:
                    process_owner = self.find_process_owner(challenge.current_process_id)
                    if process_owner:
                        self.ps_update(challenge.current_process_id, 'error', process_owner)
                return
                
            # Collecter les tokens des images à voter
            while vote_count < vote_count_max and vote_index < len(vote_data["images"]):
                vote_image = vote_data["images"][vote_index]
                
                # Vérifier que l'image a un token valide
                if vote_image.get("token"):
                    votes_panel.append(vote_image["token"])
                    vote_count = vote_count + 1
                
                vote_index = vote_index + 1
                
                # Si nous avons parcouru toutes les images disponibles
                if vote_index == len(vote_data["images"]):
                    # Si nous n'avons pas pu collecter suffisamment d'images, terminer le processus
                    if vote_count == 0:
                        self.log(f"Aucune image valide trouvée pour {challenge.title}")
                        return
                    break

            # Vérifier que nous avons au moins une image à voter
            if not votes_panel:
                self.log(f"Aucun token d'image valide pour voter dans {challenge.title}")
                return
                
            self.log_action(challenge.title, "voting", f"{len(votes_panel)} images")
            self.fetcher.start_post_votes_panel(challenge, votes_panel)


    def sort_challenges(self, challenges):
        # Fonction helper pour convertir l'end_time en datetime pour le tri
        def end_time_to_datetime(end_time_str):
            try:
                # Format: "dd/mm/yyyy, HH:MM"
                return datetime.strptime(end_time_str.strip(), "%d/%m/%Y, %H:%M")
            except Exception as e:
                # En cas d'erreur, retourner une date très éloignée pour mettre à la fin
                print(f"Erreur de parsing de date: {end_time_str} - {e}")
                return datetime.max

        # Trier les challenges par end_time (ordre croissant)
        sorted_challenges = sorted(challenges, key=lambda x: end_time_to_datetime(x.end_time))
        return sorted_challenges

    def create_centered_item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def populate_challenge_table(self):
        # Trier les challenges avant de les afficher
        sorted_challenges = self.sort_challenges(list(self.all_challenges[self.player]))
        self.challenge_table.setRowCount(len(sorted_challenges))
        for row, challenge in enumerate(sorted_challenges):
            # Select checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(challenge.id in self.selected_challenges)
            checkbox.stateChanged.connect(lambda state, cid=challenge.id: self.toggle_challenge_selection(cid))
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.challenge_table.setCellWidget(row, 0, checkbox_widget)

            # Title
            self.challenge_table.setItem(row, 1, self.create_centered_item(challenge.title))

            # End Time
            self.challenge_table.setItem(row, 2, self.create_centered_item(challenge.end_time))

            # Remaining Time (will be updated by timer)
            self.challenge_table.setItem(row, 3, self.create_centered_item(challenge.time_left))

            # Remaining Time (will be updated by timer)
            self.challenge_table.setItem(row, 4, self.create_centered_item(challenge.votes))
            self.challenge_table.setItem(row, 5, self.create_centered_item(challenge.rank))
            self.challenge_table.setItem(row, 6, self.create_centered_item(challenge.level))
            self.challenge_table.setItem(row, 7, self.create_centered_item(challenge.exposure))
            self.challenge_table.setItem(row, 8, self.create_centered_item(challenge.gps))

            # Stratégie (colonne 9) - Affiche le nom de la stratégie active pour ce challenge
            status = self.get_challenge_strategy_status(challenge)
            self.challenge_table.setItem(row, 9, self.create_centered_item(status))

    def get_challenge_strategy_status(self, challenge):
        """Retourne le nom de la stratégie active pour ce challenge, ou vide si aucune"""
        
        # 1. Vérifier d'abord dans la configuration des stratégies programmées
        if self.config['players'][self.player].get('scheduled_strategies'):
            challenge_id_str = str(challenge.id)
            if challenge_id_str in self.config['players'][self.player]['scheduled_strategies']:
                strategy_info = self.config['players'][self.player]['scheduled_strategies'][challenge_id_str]
                return strategy_info.get('strategy_name', '')
        
        # 2. Vérifier les jobs APScheduler programmés (fallback)
        apscheduler_jobs = self.count_scheduled_votes_for_challenge(challenge.id)
        if apscheduler_jobs > 0:
            return "Programmé"  # Si pas dans config mais jobs existent
        
        # 3. Vérifier les processus legacy actifs (fallback)
        if self.config['players'][self.player].get('process'):
            for process_id in self.config['players'][self.player]['process'].keys():
                if (challenge.url in process_id and 
                    self.config['players'][self.player]['process'][process_id] in ('init', 'waiting', 'executing')):
                    return "Legacy"  # Processus legacy actif
        
        # 4. Aucune stratégie active trouvée
        return ""

    def toggle_challenge_selection(self, challenge_id):
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)

    def update_challenge_strategy(self, challenge, strategy):
        challenge.selected_strategy = strategy
        self.log(f"Stratégie de {challenge.title} mise à jour: {strategy}")
        
        # Sauvegarder la stratégie dans la section appropriée du fichier de configuration
        if not self.config['players'][self.player].get('challenges'):
            self.config['players'][self.player]['challenges'] = {}
        
        # Utiliser l'URL du challenge comme clé unique
        challenge_key = challenge.url.split('/')[-1]  # Extrait la dernière partie de l'URL
        self.config['players'][self.player]['challenges'][challenge_key] = strategy
        self.config.write()
        self.log(f"Stratégie enregistrée pour {self.player}: {challenge_key} = {strategy}")


    def _create_challenge_widget(self, challenge):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        checkbox = QCheckBox()
        checkbox.setChecked(challenge.id in self.selected_challenges)
        checkbox.stateChanged.connect(lambda state, cid=challenge.id: self.toggle_challenge_selection(cid))
        layout.addWidget(checkbox)

        #info_layout = QVBoxLayout()

        layout.addWidget(QLabel(f"{challenge.title}"))
        layout.addWidget(QLabel(f"End {challenge.end_time}"))
        layout.addWidget(QLabel(f"Left {challenge.time_left}"))

        layout.addWidget(QLabel(f"Votes {challenge.votes}"))
        layout.addWidget(QLabel(f"Rank {challenge.rank}"))
        layout.addWidget(QLabel(f"level {challenge.level}"))
        layout.addWidget(QLabel(f"exposure {challenge.exposure}"))

        #if challenge.gps > 0:
        #    layout.addWidget(QLabel(f"GURU PICK {challenge.gps}"))


        #layout.addLayout(info_layout)

        strategy_combo = QComboBox()
        strategy_combo.addItems(self.strategies.keys())
        
        # Vérifier si une stratégie est sauvegardée dans le fichier ini
        challenge_key = challenge.url.split('/')[-1]  # Extrait la dernière partie de l'URL
        saved_strategy = None
        if self.config['players'][self.player].get('challenges') and challenge_key in self.config['players'][self.player]['challenges']:
            saved_strategy = self.config['players'][self.player]['challenges'][challenge_key]
        
        # Priorité: 1) Stratégie sauvegardée, 2) Stratégie déjà définie
        if saved_strategy and saved_strategy in self.strategies.keys():
            challenge.selected_strategy = saved_strategy
        
        strategy_combo.setCurrentText(challenge.selected_strategy)
        strategy_combo.currentTextChanged.connect(lambda text, c=challenge: self.update_challenge_strategy(c, text))
        layout.addWidget(strategy_combo)


        #status_label = QLabel(f"Status: {challenge.status}")
        #status_label.setObjectName(f"status_label_{challenge.id}")
        #layout.addWidget(status_label)

        return widget

    def toggle_challenge_selection(self, challenge_id):
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)

    def fill_selected_challenges(self):
        result = f"Filling challenges: {self.selected_challenges}\n"
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                # Appel direct car nous sommes déjà sur le thread principal
                self.vote_challenge(challenge, 35)
                result += f"Filling {challenge.title} with strategy {challenge.selected_strategy}\n"
                self.filled_selected_challenges(challenge, True)
                sleep(3)

        self.log(result)

    def sel_all(self):
        # Ajouter tous les IDs de challenges à l'ensemble des challenges sélectionnés
        for challenge in self.all_challenges[self.player]:
            self.selected_challenges.add(challenge.id)
        # Mettre à jour l'état des checkboxes
        self.populate_challenge_table()
        result = f"Sélection de tous les challenges\n"
        self.log(result)
    def sel_none(self):
        # Vider l'ensemble des challenges sélectionnés
        self.selected_challenges.clear()
        # Mettre à jour l'état des checkboxes
        self.populate_challenge_table()
        result = f"Désélection de tous les challenges\n"
        self.log(result)

    def filled_selected_challenges(self, challenge, result):
        if result == True:
            result = f"Filled {challenge.title} with strategy {challenge.selected_strategy}\n"
        else:
            result = f"NOT Filled {challenge.title} with strategy {challenge.selected_strategy}\n"
        self.log(result)


    def test_timing_strategies(self):
        """Méthode de test pour afficher et tester les stratégies"""
        self.log("=== Test des stratégies de timing ===")
        
        # Lister les stratégies disponibles
        strategies = self.get_available_timing_strategies()
        self.log(f"Stratégies disponibles ({len(strategies)}):")
        for name, description in strategies:
            self.log(f"  - {name}: {description}")
        
        # Exemple d'application sur le premier challenge
        if hasattr(self, 'all_challenges') and self.player in self.all_challenges:
            challenges = list(self.all_challenges[self.player])
            if challenges:
                test_challenge = challenges[0]
                self.log(f"\nTest sur le challenge: {test_challenge.title}")
                
                # Appliquer la stratégie 'aggressive' par exemple
                if strategies:
                    strategy_name = strategies[0][0]  # Première stratégie
                    self.log(f"Application de la stratégie: {strategy_name}")
                    success = self.apply_timing_strategy(test_challenge, strategy_name)
                    if success:
                        self.log("✅ Stratégie appliquée avec succès!")
                    else:
                        self.log("❌ Échec de l'application de la stratégie")

    def show_in_progress_challenges(self):
        """Affiche les stratégies et jobs APScheduler en cours"""
        result = "=== STRATÉGIES ET JOBS EN COURS ===\n\n"
        
        # 1. Afficher les jobs APScheduler programmés
        result += "📅 JOBS APSCHEDULER PROGRAMMÉS:\n"
        result += "-" * 50 + "\n"
        
        if hasattr(self, 'scheduler') and self.scheduler:
            try:
                jobs = self.scheduler.get_jobs()
                if jobs:
                    for job in jobs:
                        next_run = job.next_run_time.strftime("%d/%m/%Y %H:%M:%S") if job.next_run_time else "N/A"
                        
                        # Identifier le type de job
                        job_type = "📊 Système"
                        if job.id.startswith('vote_'):
                            job_type = "🗳️ Vote"
                        elif job.id == 'countdown_refresh':
                            job_type = "⏱️ Décompte"
                        elif job.id == 'check_stalled_processes':
                            job_type = "🔍 Nettoyage"
                        elif job.id == 'server_sync':
                            job_type = "🔄 Sync"
                        elif job.id == 'purge_closed_challenges':
                            job_type = "🗑️ Purge"
                        
                        result += f"{job_type} | {job.name}\n"
                        result += f"   ID: {job.id}\n"
                        result += f"   Prochaine exécution: {next_run}\n"
                        
                        # Pour les jobs de vote, essayer d'extraire le challenge
                        if job.id.startswith('vote_'):
                            try:
                                # Format: vote_{challenge_id}_{timing_spec}_{timestamp}
                                parts = job.id.split('_')
                                if len(parts) >= 2:
                                    challenge_id = parts[1]
                                    timing_spec = parts[2] if len(parts) > 2 else "unknown"
                                    
                                    # Trouver le challenge correspondant
                                    challenge = next((c for c in self.all_challenges.get(self.player, []) 
                                                    if c.id == challenge_id), None)
                                    if challenge:
                                        result += f"   Challenge: {challenge.title}\n"
                                        result += f"   Timing: {timing_spec}\n"
                            except:
                                pass
                        
                        result += "\n"
                else:
                    result += "Aucun job programmé.\n\n"
            except Exception as e:
                result += f"Erreur lors de la récupération des jobs: {e}\n\n"
        else:
            result += "Scheduler non disponible.\n\n"
        
        # 2. Afficher les anciens processus (legacy)
        result += "⚙️ PROCESSUS LEGACY:\n"
        result += "-" * 50 + "\n"
        
        legacy_processes = False
        if self.config['players'][self.player].get('process'):
            for process_id in self.config['players'][self.player]['process'].keys():
                status = self.config['players'][self.player]['process'][process_id]
                if status in ('init', 'waiting', 'executing', 'done'):
                    legacy_processes = True
                    # Trouver le challenge correspondant
                    challenge_url = None
                    for part in process_id.split('-'):
                        if 'gurushots.com' in part:
                            challenge_url = part
                            break
                    
                    if challenge_url:
                        challenge = next((c for c in self.all_challenges[self.player] if c.url == challenge_url), None)
                        if challenge:
                            result += f"🔄 {challenge.title}: {status}\n"
                        else:
                            result += f"🔄 URL: {challenge_url}: {status}\n"
                    else:
                        result += f"🔄 Processus: {process_id}: {status}\n"
        
        if not legacy_processes:
            result += "Aucun processus legacy en cours.\n"
        
        result += "\n" + "=" * 60 + "\n"
        
        self.log(result)

    def get_jobs_summary(self):
        """Retourne un résumé court des jobs en cours"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return "Scheduler non disponible"
        
        try:
            jobs = self.scheduler.get_jobs()
            if not jobs:
                return "Aucun job programmé"
            
            vote_jobs = [j for j in jobs if j.id.startswith('vote_')]
            system_jobs = [j for j in jobs if not j.id.startswith('vote_')]
            
            summary = f"{len(vote_jobs)} votes programmés, {len(system_jobs)} jobs système"
            
            # Prochain job de vote
            if vote_jobs:
                next_vote = min(vote_jobs, key=lambda j: j.next_run_time if j.next_run_time else datetime.max)
                if next_vote.next_run_time:
                    time_until = next_vote.next_run_time - datetime.now()
                    if time_until.total_seconds() > 0:
                        hours, remainder = divmod(int(time_until.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        summary += f" | Prochain vote dans {hours:02d}:{minutes:02d}:{seconds:02d}"
            
            return summary
            
        except Exception as e:
            return f"Erreur: {e}"

    def count_scheduled_votes_for_challenge(self, challenge_id):
        """Compte le nombre de votes programmés pour un challenge (profil actuel)"""
        return self.count_scheduled_votes_for_challenge_and_profile(challenge_id, self.player)

    def update_challenge_list(self):
        now = datetime.now()
        self.all_challenges[self.player] = self.sort_challenges(self.all_challenges[self.player])
        #self.populate_challenge_list()
        for challenge in self.all_challenges[self.player]:
            remaining_time = challenge.end_time - now
            remaining_hours = int(remaining_time.total_seconds() / 3600)
            label = self.findChild(QLabel, f"remaining_label_{challenge.id}")
            if label:
                label.setText(f"Remaining: {remaining_hours} hours")

    @asyncSlot()
    async def fill_selected_challenges(self):
        result = f"Filling challenges: {self.selected_challenges}\n"
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                challenge.status = "In Progress"
                result += f"Filled {challenge.title} with strategy {challenge.selected_strategy}\n"

                # Mettre à jour l'état dans le tableau
                for row in range(self.challenge_table.rowCount()):
                    if self.challenge_table.item(row, 1).text() == challenge.title:
                        self.challenge_table.setItem(row, 9, self.create_centered_item("Fill"))

                # Call the votes method
                self.vote_challenge(challenge, 35)

        self.log(result)
        self.update_challenge_table()  # Update the table to reflect changes

    @asyncSlot()
    async def fin_selected_challenges(self):
        """Applique les nouvelles stratégies de timing pour les challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("Aucun challenge sélectionné")
            return
            
        # Charger les stratégies disponibles
        timing_strategies = self.load_timing_strategies()
        if not timing_strategies:
            self.log("Aucune stratégie de timing disponible")
            return
        
        # Demander à l'utilisateur quelle stratégie utiliser
        selected_strategy = self.show_strategy_selection_dialog(timing_strategies)
        
        if not selected_strategy:
            self.log("Aucune stratégie sélectionnée")
            return
            
        self.log(f"=== Application de la stratégie '{selected_strategy}' ===")
        self.log(f"Description: {timing_strategies[selected_strategy]['description']}")
        
        result = f"Application de la stratégie '{selected_strategy}' pour les challenges sélectionnés:\n"
        
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                self.log(f"\n--- Challenge: {challenge.title} ---")
                self.log(f"Fin du challenge: {challenge.end_time}")
                
                # Appliquer la stratégie de timing
                success = self.apply_timing_strategy(challenge, selected_strategy)
                
                if success:
                    result += f"✅ {challenge.title} - Stratégie programmée\n"
                    # Afficher le détail des actions programmées
                    strategy_steps = timing_strategies[selected_strategy]['steps']
                    for strategy_step in strategy_steps:
                        if len(strategy_step) >= 3:
                            method = strategy_step[0]
                            timing_spec = strategy_step[1]
                            count = strategy_step[2]
                            args = strategy_step[3:] if len(strategy_step) > 3 else []
                            args_str = f" [{', '.join(args)}]" if args else ""
                            # Calculer l'heure de déclenchement pour info
                            trigger_time = self.parse_timing_spec(challenge, timing_spec)
                            if trigger_time:
                                result += f"   • {method} {count}{args_str} à {trigger_time.strftime('%H:%M:%S')} ({timing_spec})\n"
                        elif len(strategy_step) == 2:
                            # Ancien format pour compatibilité
                            timing_spec, count = strategy_step
                            trigger_time = self.parse_timing_spec(challenge, timing_spec)
                            if trigger_time:
                                result += f"   • vote {count} à {trigger_time.strftime('%H:%M:%S')} ({timing_spec})\n"
                else:
                    result += f"❌ {challenge.title} - Échec de programmation\n"

        self.log(result)
        
        # Afficher le résumé des tâches programmées
        self.list_scheduled_jobs()

    def show_strategy_selection_dialog(self, timing_strategies):
        """Affiche un dialogue pour sélectionner une stratégie"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Sélection de stratégie")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Label d'instruction
        instruction_label = QLabel("Choisissez une stratégie de timing à appliquer :")
        instruction_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(instruction_label)
        
        # ComboBox pour sélectionner la stratégie
        self.strategy_combo = QComboBox()
        for strategy_name, strategy_data in timing_strategies.items():
            self.strategy_combo.addItem(f"{strategy_name} - {strategy_data['description']}", strategy_name)
        layout.addWidget(self.strategy_combo)
        
        # Zone de texte pour afficher le détail de la stratégie sélectionnée
        detail_label = QLabel("Détail de la stratégie :")
        detail_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(detail_label)
        
        self.strategy_detail = QTextEdit()
        self.strategy_detail.setReadOnly(True)
        self.strategy_detail.setMaximumHeight(150)
        layout.addWidget(self.strategy_detail)
        
        # Mettre à jour le détail quand la sélection change
        self.strategy_combo.currentTextChanged.connect(lambda: self.update_strategy_detail(timing_strategies))
        
        # Initialiser le détail avec la première stratégie
        self.update_strategy_detail(timing_strategies)
        
        # Boutons OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Afficher le dialogue et retourner le résultat
        if dialog.exec() == QDialog.Accepted:
            return self.strategy_combo.currentData()
        else:
            return None

    def update_strategy_detail(self, timing_strategies):
        """Met à jour le détail de la stratégie sélectionnée"""
        current_strategy = self.strategy_combo.currentData()
        if current_strategy and current_strategy in timing_strategies:
            strategy_data = timing_strategies[current_strategy]
            detail_text = f"Description: {strategy_data['description']}\n\nÉtapes:\n"
            
            for i, strategy_step in enumerate(strategy_data['steps'], 1):
                if len(strategy_step) >= 3:
                    method = strategy_step[0]
                    timing_spec = strategy_step[1]
                    count = strategy_step[2]
                    args = strategy_step[3:] if len(strategy_step) > 3 else []
                    args_str = f" ({', '.join(args)})" if args else ""
                    detail_text += f"{i}. {method} {count} à {timing_spec}{args_str}\n"
                elif len(strategy_step) == 2:
                    # Ancien format pour compatibilité
                    timing_spec, count = strategy_step
                    detail_text += f"{i}. vote {count} à {timing_spec}\n"
            
            self.strategy_detail.setPlainText(detail_text)
        
    def stop_selected_strategies(self):
        """Arrête les stratégies APScheduler pour les challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("Aucun challenge sélectionné")
            return
            
        result = f"=== ARRÊT DES STRATÉGIES ===\n"
        result += f"Challenges sélectionnés: {len(self.selected_challenges)}\n\n"
        
        jobs_removed = 0
        process_stopped = False
        
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                result += f"🛑 Challenge: {challenge.title}\n"
                
                # 1. Supprimer les jobs APScheduler pour ce challenge
                challenge_jobs_removed = self.remove_scheduler_jobs_for_challenge(challenge_id)
                jobs_removed += challenge_jobs_removed
                
                if challenge_jobs_removed > 0:
                    result += f"   ✅ {challenge_jobs_removed} job(s) APScheduler supprimé(s)\n"
                else:
                    result += f"   ⚪ Aucun job APScheduler trouvé\n"
                
                # 2. Arrêter les anciens processus legacy
                legacy_stopped = self.stop_legacy_processes_for_challenge(challenge)
                if legacy_stopped > 0:
                    result += f"   ✅ {legacy_stopped} processus legacy arrêté(s)\n"
                    process_stopped = True
                else:
                    result += f"   ⚪ Aucun processus legacy trouvé\n"
                
                # 3. Mettre à jour la colonne "Stratégie" (vider)
                for row in range(self.challenge_table.rowCount()):
                    if self.challenge_table.item(row, 1).text() == challenge.title:
                        self.challenge_table.setItem(row, 9, self.create_centered_item(""))
                        break
                
                # 4. Supprimer la stratégie de la configuration
                self.remove_scheduled_strategy(challenge_id)
                result += f"   🗑️ Stratégie supprimée de la configuration\n"
                
                result += "\n"
        
        # Résumé final
        result += "📊 RÉSUMÉ:\n"
        result += f"   • Jobs APScheduler supprimés: {jobs_removed}\n"
        result += f"   • Processus legacy arrêtés: {'Oui' if process_stopped else 'Non'}\n"
        
        if jobs_removed == 0 and not process_stopped:
            result += "\n⚠️ Aucune stratégie active trouvée pour les challenges sélectionnés.\n"
        else:
            result += f"\n✅ Arrêt terminé avec succès!\n"
            
        self.log(result)
        self.schedule_update()

    def remove_scheduler_jobs_for_challenge(self, challenge_id):
        """Supprime tous les jobs APScheduler pour un challenge donné"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        try:
            jobs = self.scheduler.get_jobs()
            jobs_removed = 0
            
            for job in jobs:
                # Vérifier si le job appartient à ce challenge ET profil actuel
                if job.id.startswith(f'vote_{self.player}_{challenge_id}_'):
                    self.scheduler.remove_job(job.id)
                    jobs_removed += 1
                    self.log(f"   🗑️ Job supprimé: {job.name} (ID: {job.id})")
            
            return jobs_removed
            
        except Exception as e:
            self.log(f"Erreur lors de la suppression des jobs pour le challenge {challenge_id}: {e}")
            return 0

    def stop_legacy_processes_for_challenge(self, challenge):
        """Arrête les processus legacy pour un challenge"""
        processes_stopped = 0
        
        if self.config['players'][self.player].get('process'):
            # Créer une copie de la liste des clés pour éviter de modifier le dictionnaire pendant l'itération
            process_ids = list(self.config['players'][self.player]['process'].keys())
            for process_id in process_ids:
                if (challenge.url in process_id and 
                    process_id in self.config['players'][self.player]['process'] and 
                    self.config['players'][self.player]['process'][process_id] in ('init', 'waiting', 'executing')):
                    
                    self.ps_update(process_id, 'stopped')
                    processes_stopped += 1
                    self.log(f"   🔄 Processus legacy arrêté: {process_id}")
        
        return processes_stopped
        
    def stop_all_strategies(self):
        """PURGE COMPLÈTE : Supprime tous les jobs mais garde APScheduler actif"""
        result = "=== 🛑 NETTOYAGE COMPLET DES JOBS ===\n\n"
        result += "🗑️ Suppression de TOUS les jobs en cours...\n"
        result += "✅ APScheduler reste actif pour de nouveaux jobs\n\n"
        
        # 1. Supprimer TOUS les jobs APScheduler (mais garder le scheduler)
        all_jobs_removed = self.clear_all_scheduler_jobs()
        result += f"🗑️ Jobs APScheduler supprimés: {all_jobs_removed}\n"
        
        # 2. Arrêter tous les processus legacy
        legacy_count = 0
        
        if self.config['players'][self.player].get('process'):
            # Créer une copie de la liste des clés pour éviter de modifier le dictionnaire pendant l'itération
            process_ids = list(self.config['players'][self.player]['process'].keys())
            for process_id in process_ids:
                if (process_id in self.config['players'][self.player]['process'] and 
                    self.config['players'][self.player]['process'][process_id] in ('init', 'waiting', 'executing')):
                    
                    self.ps_update(process_id, 'stopped')
                    legacy_count += 1
                    self.log(f"   🔄 Processus legacy arrêté: {process_id}")
        
        result += f"🔄 Processus legacy arrêtés: {legacy_count}\n\n"
        
        # 3. Mettre à jour toutes les colonnes "Stratégie" (vider)
        for row in range(self.challenge_table.rowCount()):
            self.challenge_table.setItem(row, 9, self.create_centered_item(""))
        
        # 4. Supprimer toutes les stratégies sauvegardées
        strategies_cleared = self.clear_all_scheduled_strategies()
        result += f"🗑️ Stratégies supprimées de la config: {strategies_cleared}\n\n"
        
        # 5. Redémarrer automatiquement les jobs système essentiels
        system_jobs_restored = self.restore_essential_system_jobs()
        result += f"🔄 Jobs système essentiels restaurés: {system_jobs_restored}\n\n"
        
        # 6. Résumé final
        result += "📊 RÉSUMÉ FINAL:\n"
        result += f"   • Jobs supprimés: {all_jobs_removed}\n"
        result += f"   • Processus legacy arrêtés: {legacy_count}\n"
        result += f"   • Stratégies supprimées: {strategies_cleared}\n"
        result += f"   • Jobs système restaurés: {system_jobs_restored}\n\n"
        
        if all_jobs_removed == 0 and legacy_count == 0:
            result += "⚪ Aucun job ou processus trouvé.\n"
        else:
            result += "✅ NETTOYAGE TERMINÉ !\n"
            result += "🎯 Tous les votes ont été annulés\n"
            result += "⚡ APScheduler opérationnel pour de nouvelles stratégies\n"
            
        self.log(result)
        self.schedule_update()

    def clear_all_scheduler_jobs(self):
        """Supprime TOUS les jobs mais garde APScheduler actif"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        try:
            jobs = self.scheduler.get_jobs()
            jobs_removed = 0
            
            for job in jobs:
                # Supprimer TOUS les jobs sans exception
                self.scheduler.remove_job(job.id)
                jobs_removed += 1
                
                # Identifier le type pour le log
                job_type = "🗳️ Vote"
                if job.id == 'countdown_refresh':
                    job_type = "⏱️ Décompte"
                elif job.id == 'server_sync':
                    job_type = "🔄 Sync"
                elif job.id == 'check_stalled_processes':
                    job_type = "🔍 Nettoyage"
                elif job.id == 'purge_closed_challenges':
                    job_type = "🗑️ Purge"
                elif not job.id.startswith('vote_'):
                    job_type = "📊 Système"
                
                self.log(f"   🗑️ {job_type} supprimé: {job.name}")
            
            return jobs_removed
            
        except Exception as e:
            self.log(f"Erreur lors de la suppression de tous les jobs: {e}")
            return 0

    def restore_essential_system_jobs(self):
        """Recrée automatiquement les jobs système essentiels"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        jobs_restored = 0
        
        try:
            # 1. Restaurer le décompte local (toutes les 10 secondes)
            self.scheduler.add_job(
                func=self.update_countdown,
                trigger=IntervalTrigger(seconds=10),
                id='countdown_refresh',
                name='Mise à jour du décompte local',
                replace_existing=True,
                max_instances=1
            )
            jobs_restored += 1
            self.log(f"   ✅ Décompte restauré")
            
            # 2. Restaurer la synchronisation serveur (toutes les 5 minutes)
            self.scheduler.add_job(
                func=self.sync_with_server,
                trigger=IntervalTrigger(minutes=5),
                id='server_sync',
                name='Synchronisation avec le serveur',
                replace_existing=True,
                max_instances=1
            )
            jobs_restored += 1
            self.log(f"   ✅ Sync serveur restauré")
            
            # 3. Restaurer le nettoyage des processus bloqués (toutes les minutes)
            self.scheduler.add_job(
                func=self.check_stalled_processes,
                trigger=IntervalTrigger(minutes=1),
                id='check_stalled_processes',
                name='Vérification des processus bloqués',
                replace_existing=True,
                max_instances=1
            )
            jobs_restored += 1
            self.log(f"   ✅ Nettoyage processus restauré")
            
            # 4. Restaurer la purge des challenges fermés (toutes les 5 minutes)
            self.scheduler.add_job(
                func=self.purge_closed_challenges,
                trigger=IntervalTrigger(minutes=5),
                id='purge_closed_challenges',
                name='Suppression des challenges fermés',
                replace_existing=True,
                max_instances=1
            )
            jobs_restored += 1
            self.log(f"   ✅ Purge challenges restauré")
            
            return jobs_restored
            
        except Exception as e:
            self.log(f"Erreur lors de la restauration des jobs système: {e}")
            return jobs_restored

    def purge_all_scheduler_jobs(self):
        """PURGE TOTALE : Supprime ABSOLUMENT TOUS les jobs APScheduler"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        try:
            jobs = self.scheduler.get_jobs()
            jobs_removed = 0
            
            for job in jobs:
                # Supprimer TOUS les jobs sans exception
                self.scheduler.remove_job(job.id)
                jobs_removed += 1
                
                # Identifier le type pour le log
                job_type = "🗳️ Vote"
                if job.id == 'countdown_refresh':
                    job_type = "⏱️ Décompte"
                elif job.id == 'server_sync':
                    job_type = "🔄 Sync"
                elif job.id == 'check_stalled_processes':
                    job_type = "🔍 Nettoyage"
                elif job.id == 'purge_closed_challenges':
                    job_type = "🗑️ Purge"
                elif not job.id.startswith('vote_'):
                    job_type = "📊 Système"
                
                self.log(f"   🔥 {job_type} supprimé: {job.name} (ID: {job.id})")
            
            return jobs_removed
            
        except Exception as e:
            self.log(f"Erreur lors de la purge de tous les jobs: {e}")
            return 0

    def remove_all_vote_jobs(self):
        """Supprime SEULEMENT les jobs de vote APScheduler (utilisé par stop_selected_strategies)"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return 0
        
        try:
            jobs = self.scheduler.get_jobs()
            jobs_removed = 0
            
            for job in jobs:
                # Supprimer seulement les jobs de vote, garder les jobs système
                if job.id.startswith('vote_'):
                    self.scheduler.remove_job(job.id)
                    jobs_removed += 1
                    self.log(f"   🗑️ Job de vote supprimé: {job.name}")
            
            return jobs_removed
            
        except Exception as e:
            self.log(f"Erreur lors de la suppression de tous les jobs de vote: {e}")
            return 0
    async def vote_panel(self, challenge):
        url = f"https://api.gurushots.com/challenges/{challenge.id}/vote"  # Replace with actual API URL
        await self.fetcher.votes(url, 35)
        #sleep(3)
        #await self.fetcher.votes(url, 35)


    def vote(self, args):
        self.action_exec_args(args.cha, "vote", args.vote, args)

    def strategy(self, challenge):
        st = challenge.selected_strategy
        for _strategie in self.strategies.keys():
            if st in _strategie:
                self.log(f"Lancement de la stratégie {_strategie} pour {challenge.title}")
                for step in self.strategies[_strategie].keys():
                    cmd = ' --cha ' + str(challenge.url) + ' ' + self.strategies[_strategie][step]
                    cmd_args = self.parser.parse_args(cmd.split())
                    cmd_args.cmde = cmd
                    cmd_args.func(cmd_args)
                # Forcer le rafraîchissement après avoir lancé tous les processus de la stratégie
                self.schedule_update()
                return
                
        # Si on arrive ici, c'est qu'aucune stratégie n'a été trouvée
        self.log(f"Aucune stratégie trouvée pour {challenge.title} avec {st}")




    def log_action(self, url, lib, value):
        # Cette méthode utilise self.log qui est déjà thread-safe
        self.log(f'{url} {lib} {value}')
        # Planifier une mise à jour de l'interface
        self.schedule_update()
        return

    @Slot(str)
    def on_vote_finished(self, result):
        self.log(f'on vote finished {result}')
        self.schedule_update()

    def get_challenge(self, challenge_url, player=None):
        """
        Récupère les détails d'un challenge à partir de son URL.
        Si le challenge n'est pas trouvé, renvoie None.
        
        Args:
            challenge_url: L'URL ou l'ID du challenge à trouver
            player: Le profil dans lequel rechercher (par défaut: profil actuel)
        """
        try:
            # Déterminer le profil à utiliser
            target_player = player if player else self.player
            
            # S'assurer que le dictionnaire des challenges existe
            if not hasattr(self, 'all_challenges'):
                self.all_challenges = {}
                
            # S'assurer que le profil existe
            if target_player not in self.all_challenges:
                self.all_challenges[target_player] = set()
                
            # Rechercher dans les challenges du profil spécifié
            challenge_obj = next((c for c in self.all_challenges[target_player] if c.url == challenge_url), None)
            
            # Si on trouve le challenge et qu'il a les informations nécessaires
            if challenge_obj and hasattr(challenge_obj, 'challenge'):
                return challenge_obj.challenge
            
            # Si on ne trouve pas dans le profil spécifié, essayer dans tous les profils
            if not challenge_obj:
                for profile, challenges in self.all_challenges.items():
                    if profile != target_player:  # On a déjà cherché dans target_player
                        challenge_obj = next((c for c in challenges if c.url == challenge_url), None)
                        if challenge_obj and hasattr(challenge_obj, 'challenge'):
                            self.log(f"Challenge trouvé dans le profil {profile}: {challenge_obj.title}")
                            return challenge_obj.challenge
            
            # Si on ne trouve toujours pas le challenge, notifier sans lever d'exception
            self.log(f"Challenge non trouvé: {challenge_url}")
            
            # Renvoyer une structure minimale pour éviter les erreurs
            return {
                "time_left": {
                    "days": 0,
                    "hours": 0,
                    "minutes": 0
                }
            }
        except Exception as e:
            self.log(f"Erreur lors de la récupération du challenge {challenge_url}: {e}")
            # Retourner une structure minimale pour éviter les erreurs
            return {
                "time_left": {
                    "days": 0,
                    "hours": 0,
                    "minutes": 0
                }
            }

    def on_get_challenge_finished(self, result):
        #self.result_panel.append(result)
        self.log(f'get challenge_finished {result}')

    def update_challenge_table(self):
        # Refresh the entire table
        self.populate_challenge_table()
        # Forcer le redimensionnement des colonnes dynamiques après mise à jour
        self.challenge_table.resizeColumnToContents(3)  # Remaining
        self.challenge_table.resizeColumnToContents(4)  # Votes
        self.challenge_table.resizeColumnToContents(5)  # Rank
        self.challenge_table.resizeColumnToContents(9) # Stratégie

    def refresh_challenges(self):
        self.log("Refreshing challenges...")
        self.fetch_challenges()


    def change_profile(self, profile):
        self.log(f"Changement de profil vers: {profile}")
        
        # Sauvegarder l'état actuel du profil avant de changer
        current_profile = self.player
        
        # Changer le profil sans arrêter les workers existants
        self.player = profile
        self.set_player(profile)
        
        # S'assurer que le dictionnaire des challenges existe pour ce profil
        if not hasattr(self, 'all_challenges'):
            self.all_challenges = {}
            
        # Initialiser le set pour ce profil s'il n'existe pas
        if profile not in self.all_challenges:
            self.all_challenges[profile] = set()
            
        # Mettre à jour la référence self.challenges pour pointer vers les challenges du profil actuel
        self.all_challenges[self.player] = self.all_challenges[profile]
        
        # Initialiser le reste du joueur
        self.init_player(profile)
        
        self.log(f"Profil changé de '{current_profile}' à '{profile}'. Les workers des deux profils continueront à s'exécuter.")

    def vote(self, args):
        try:
            # Vérifier que args.vote est bien un nombre
            vote_value = args.vote if isinstance(args.vote, int) else int(args.vote)
            self.action_exec_args(args.cha, "vote", vote_value, args)
            self.config['challenge'] = args.cha
            self.config.write()
        except Exception as e:
            self.log(f"Erreur dans la fonction vote: {e}")


    def action_thread_args(self, challenge, action, value, args):
       # Stocker le profil auquel ce thread appartient pour éviter les problèmes lors du changement de profil
       thread_player = self.player
       
       process_id = challenge + '-' + action + '-' + str(value) + '-'
       #args.cmde += ' --cha ' + challenge
       if 'at' in args and args.at:
           if args.at == 'now':
               at_time = datetime.now()
           else:
               at_split = args.at.split(':')
               at_day = datetime.now() + timedelta(days=int(at_split[0]))
               at_time = datetime(at_day.year, at_day.month, at_day.day, int(at_split[1]), int(at_split[2]), 0)
           process_id += 'at-'+at_time.strftime('%Y-%m-%d_%H:%M')
       else:
           if 'left' in args and args.left:
               left_delta = args.left.split(':')
               process_id += 'left-'+"{}H:{}M".format(left_delta[0], left_delta[1])
           else:
               if 'when' in args and args.when:
                   when_delta = args.when.split(':')
                   process_id += 'when-' + "{}H:{}M".format(when_delta[0], when_delta[1])
               else:
                    process_id += datetime.now().strftime('%Y-%m-%d_%H:%M')

       process_state = 'init'
       self.ps_add(process_id, process_state, action, value, args, thread_player)
       # Mettre à jour immédiatement l'interface après avoir créé le processus
       self.schedule_update()

       waiting_time = False
       exec_action = True

       try:
           # Obtenir les détails du challenge pour le profil du thread
           challenge_details = self.get_challenge(challenge, thread_player)
           
           # Log pour le débogage
           self.log(f"Traitement du challenge pour {thread_player}: {challenge}")
           
           if 'at' in args and args.at and args.at != 'now:':
               # print "at ", at
               at_now = datetime.now()
               if at_now > at_time:
                   exec_action = True
                   #raise ('too late')
               else:
                   self.ps_update(process_id, 'waiting', thread_player)

                   while datetime.now() <= at_time:
                       sleep(60)
                       # Vérifier que le profil du thread et le processus existent toujours
                       if (not self.config['players'].get(thread_player) or 
                           not self.config['players'][thread_player].get('process') or 
                           not self.config['players'][thread_player]['process'].get(process_id)):
                           self.log(f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
                           return
                       if self.config['players'][thread_player]['process'][process_id] == 'stop':
                           self.ps_update(process_id, 'stopped', thread_player)
                           return
           if 'left' in args and args.left:
               #challenge_details = self.all_challenges[self.player][challenge]
               timeleft = challenge_details["time_left"]
               timeLeftString = str("{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
               if timedelta(hours=int(timeleft['hours']),
                            minutes=int(timeleft['minutes'])) > timedelta(hours=int(left_delta[0]),
                                                                          minutes=int(left_delta[1])):
                   self.ps_update(process_id, 'waiting', thread_player)
                   waiting_time = True
                   while waiting_time:
                       try:
                           # Vérifier que le profil du thread et le processus existent toujours
                           if (not self.config['players'].get(thread_player) or 
                               not self.config['players'][thread_player].get('process') or 
                               not self.config['players'][thread_player]['process'].get(process_id)):
                               self.log(f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
                               return
                           if self.config['players'][thread_player]['process'][process_id] == 'stop':
                               self.ps_update(process_id, 'stopped', thread_player)
                               return
                           sleep(15)
                           
                           # Forcer le rafraîchissement des données de challenge depuis l'API
                           try:
                               import requests
                               # Utiliser requests de manière synchrone pour éviter les problèmes d'event loop
                               headers = self.aio_connect_session()

                               response = requests.post('https://api.gurushots.com/rest/get_my_active_challenges', headers=headers)
                               if response.status_code == 200:
                                   data = response.json()
                                   # Chercher le challenge spécifique
                                   for challenge_data in data.get('challenges', []):
                                       if challenge_data['url'] == challenge:
                                           challenge_details = challenge_data
                                           break
                               else:
                                   # En cas d'erreur API, utiliser les données en cache
                                   challenge_details = self.get_challenge(challenge, thread_player)
                           except Exception as api_error:
                               self.log(f"Erreur lors du rafraîchissement API, utilisation du cache: {api_error}")
                               challenge_details = self.get_challenge(challenge, thread_player)
                           
                           # La méthode get_challenge renvoie toujours un objet avec au moins time_left
                           timeleft = challenge_details["time_left"]
                           timeLeftString = str(
                               "{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
                           if timedelta(hours=int(timeleft['hours']), minutes=int(timeleft['minutes'])) <= timedelta(
                                   hours=int(left_delta[0]), minutes=int(left_delta[1])):
                               waiting_time = False
                       except Exception as e:
                           self.log(f"Erreur dans la boucle d'attente left: {e}")
                           sleep(30)
                           pass
           if 'when' in args and args.when:
               #challenge_details = self.challenges[challenge]
               when_day = datetime.now();
               when_time = datetime(when_day.year, when_day.month, when_day.day,when_day.hour + int(when_delta[0]), when_day.minute + int(when_delta[1]), 0)
               self.ps_update(process_id, 'waiting', thread_player)
               waiting_time = True
               while waiting_time:
                   try:
                       # Vérifier que le profil du thread et le processus existent toujours
                       if (not self.config['players'].get(thread_player) or 
                           not self.config['players'][thread_player].get('process') or 
                           not self.config['players'][thread_player]['process'].get(process_id)):
                           self.log(f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
                           return
                       if self.config['players'][thread_player]['process'][process_id] == 'stop':
                           self.ps_update(process_id, 'stopped', thread_player)
                           return
                       sleep(10)
                       if datetime.now() > when_time:
                           waiting_time = False
                   except Exception as e:
                       self.log(f"Erreur dans la boucle d'attente when: {e}")
                       sleep(30)
                       pass
           self.ps_update(process_id, 'executing', thread_player)

           if exec_action:
               if action in "vote":  # Correction: "votes" -> "vote"
                   try:
                       # Récupérer un objet challenge depuis les challenges existants
                       # Utiliser les challenges associés au profil du thread
                       challenge_obj = None
                       
                       # Utiliser les challenges du profil du thread
                       if not hasattr(self, 'all_challenges'):
                           self.all_challenges = {}
                           
                       if thread_player not in self.all_challenges:
                           self.all_challenges[thread_player] = set()
                           
                       # Chercher dans les challenges du profil du thread
                       for ch in self.all_challenges[thread_player]:
                           if ch.url == challenge or getattr(ch, 'id', None) == challenge:
                               challenge_obj = ch
                               break
                       
                       # Si nous ne trouvons pas le challenge ou si nous sommes sur un autre profil
                       if not challenge_obj:
                           # Créer un objet challenge minimal pour traiter le vote
                           from src.gs.gsprompt import GuruBatch
                           try:
                               # Essayer d'extraire l'ID du challenge à partir de l'URL
                               challenge_id = challenge.split('/')[-1] if '/' in challenge else challenge
                               challenge_obj = GurushotChallenge(
                                   id=challenge_id,
                                   title=f"Challenge {challenge_id}",
                                   end_time="",
                                   time_left="",
                                   url=challenge,
                                   votes=0,
                                   rank=0,
                                   level="",
                                   exposure=0,
                                   gps=0,
                                   challenge={"id": challenge_id}
                               )
                               self.log(f"Objet challenge créé pour le thread de profil {thread_player}: {challenge}")
                           except Exception as e:
                               self.log(f"Erreur lors de la création d'un objet challenge pour {challenge}: {e}")
                               return
                       
                       if challenge_obj:
                           self.log(f"Traitement de vote pour {challenge_obj.title}")
                           # Utiliser le mécanisme de signal/slot pour communiquer avec le thread principal
                           # Émettre le signal qui sera capturé par le slot connecté dans le thread principal
                           # Passer l'ID du processus au signal
                           self.vote_request.emit(challenge_obj, int(value), process_id)
                           # Attendre un peu pour laisser le temps à l'opération de démarrer
                           #sleep(5)
                       else:
                           self.log(f"Erreur: Challenge non trouvé: {challenge}")
                   except Exception as e:
                       self.log(f"Erreur lors de l'exécution de vote_challenge: {str(e)}")
               if action in "ps":
                   self.ps_list()

           #self.ps_update(process_id, 'success')
           exec_action = False

       except Exception as e:
           # Log plus détaillé pour aider au débogage
           self.log(f"Erreur dans action_thread_args pour le challenge {challenge} (profil: {thread_player}): {e}")
           # Essayer de mettre à jour le statut du processus
           try:
               self.ps_update(process_id, 'error', thread_player)
           except Exception as update_error:
               self.log(f"Erreur supplémentaire lors de la mise à jour du statut: {update_error}")




    def action_exec_args(self, challenge, action, value, args):
        self.threads[challenge] = threading.Thread(target=self.action_thread_args, name=challenge+action+str(value), kwargs=dict(challenge=challenge, action=action, value=str(value), args=args))
        self.threads[challenge].daemon = True  # Daemonize thread
        self.threads[challenge].start()


    def ps(self, args):
            if args.pop:
                self.ps_pop(args.pop)

            if args.purge:
                self.ps_purge(args)

            if args.restart:
                self.ps_restart(args)

            if args.stop:
                self.ps_stop(args)

            if args.list:
                #self.ps_list()
                self.action_exec_args(args.cha, "ps", "", args)

    def ps_pop(self, p_id):
        # Créer une liste des clés pour éviter de modifier le dictionnaire pendant l'itération
        process_ids = list(self.config['players'][self.player]['process'].keys())
        for process_id in process_ids:
            if p_id in process_id:
                # Supprimer l'entrée du processus
                if self.config['players'][self.player]['process'].get(process_id):
                    self.config['players'][self.player]['process'].pop(process_id)
                
                # Supprimer l'entrée de commande correspondante
                if self.config['players'][self.player].get('cmdes') and self.config['players'][self.player]['cmdes'].get(process_id):
                    self.config['players'][self.player]['cmdes'].pop(process_id)
                
                self.config.write()
                self.log("process : ", process_id, "killed")
        
        # Mettre à jour l'interface
        self.schedule_update()

    def ps_stop(self, args):
        for process_id in self.config['players'][self.player]['process'].keys():
            if args.ps in process_id and self.config['players'][self.player]['process'][process_id] in 'waiting':
                self.ps_update(process_id, 'stop')

    def ps_update(self, process_id, status, player=None):
        # Utiliser le profil spécifié ou le profil actuel par défaut
        target_player = player if player else self.player
        
        # Protéger l'accès concurrent à la configuration
        with self.config_lock:
            # Vérifier que le profil existe toujours
            if not self.config['players'].get(target_player):
                self.log(f"Impossible de mettre à jour le processus {process_id}: profil {target_player} non trouvé")
                return
                
            if not self.config['players'][target_player].get('process'):
                self.config['players'][target_player]['process'] = {}
                
            if status in ('stop', 'stopped', 'success', 'error', 'timeout', 'zombie'):
                # Suppression des entrées pour les processus terminés
                if self.config['players'][target_player]['process'].get(process_id):
                    self.config['players'][target_player]['process'].pop(process_id)
                if self.config['players'][target_player].get('cmdes') and self.config['players'][target_player]['cmdes'].get(process_id):
                    self.config['players'][target_player]['cmdes'].pop(process_id)
                self.log(f"Processus supprimé pour {target_player}: {process_id} - {status}")
            else:
                # Mise à jour normale pour les autres statuts
                self.config['players'][target_player]['process'][process_id] = status
                
            self.config.write()
            
        self.log(f"Processus mis à jour pour {target_player}: {process_id} - {status}")
        # Planifier une mise à jour de l'interface sur le thread principal
        self.schedule_update()

    def ps_list(self):
        for process_id in self.config['players'][self.player]['process'].keys():
            self.log(f'process id  : , {process_id}, status, {self.config["players"][self.player]["process"][process_id]}, cmde, {self.config["players"][self.player]["cmdes"][process_id]}')

    def ps_restart(self, args):
        if self.config['players'][self.player]['process'].keys is not None:
            for process_id in self.config['players'][self.player]['process'].keys():
                if self.config['players'][self.player]['process'][process_id] in 'waiting':
                    args = self.parser.parse_args(self.config['players'][self.player]['cmdes'][process_id].split())
                    #if args.cha is not None:
                    #    args.cha = args.cha.replace('_', '-')
                    args.func(args)
                else:
                    self.ps_pop(process_id)

    def ps_purge(self, args):
        for process_id in self.config['players'][self.player]['process'].keys():
            self.ps_pop(process_id)

    def ps_add(self, process_id, status, action, value, args, player=None):
        # Utiliser le profil spécifié ou le profil actuel par défaut
        target_player = player if player else self.player
        
        # Protéger l'accès concurrent à la configuration
        with self.config_lock:
            # Vérifier que le profil existe dans la configuration
            if not self.config['players'].get(target_player):
                self.log(f"Erreur: Le profil {target_player} n'existe pas dans la configuration")
                return
                
            if self.config['players'][target_player].get('process') == None:
                self.config['players'][target_player]['process'] = {}

            self.config['players'][target_player]['process'][process_id] = status
            self.config.write()
            
        self.cmde_add(process_id, action, value, args, target_player)
        self.log(f"Nouveau processus ajouté pour {target_player}: {process_id} - Statut: {status}")
        
        # Forcer le rafraîchissement immédiat de l'interface
        self.schedule_update()

    def find_process_owner(self, process_id):
        """Trouve le profil propriétaire d'un processus donné"""
        for player_name in self.config['players'].keys():
            if (self.config['players'][player_name].get('process') and 
                process_id in self.config['players'][player_name]['process']):
                return player_name
        return None
        
    def cmde_list(self, process_id, status, args):
        for process_id in self.config['players'][self.player]['cmdes'].keys():
            print (self.config['players'][self.player]['cmdes'][process_id])

    def cmde_add(self, process_id, action, value, args, player=None):
        # Utiliser le profil spécifié ou le profil actuel par défaut
        target_player = player if player else self.player
        
        # Protéger l'accès concurrent à la configuration
        with self.config_lock:
            # Vérifier que le profil existe dans la configuration
            if not self.config['players'].get(target_player):
                self.log(f"Erreur: Le profil {target_player} n'existe pas dans la configuration")
                return

            if self.config['players'][target_player].get('cmdes') == None:
                self.config['players'][target_player]['cmdes'] = {}

            if self.config['players'][target_player]['cmdes'].get(process_id) == None:
                self.config['players'][target_player]['cmdes'][process_id] = args.cmde
                self.config.write()
                #print 'cmde', args.cmde
            else:
                self.log(f"Commande {args.cmde} existe déjà pour {target_player}")
            
    def check_stalled_processes(self):
        """Vérifie et nettoie les processus bloqués pour tous les profils"""
        now = datetime.now()
        stalled_processes = []
        
        # Vérifier les processus en exécution dans les challenges de tous les profils
        if hasattr(self, 'all_challenges'):
            for profile, challenges in self.all_challenges.items():
                for challenge in challenges:
                    if hasattr(challenge, 'current_process_id') and challenge.current_process_id and challenge.process_start_time:
                        # Si le processus est en cours depuis plus de 5 minutes, considérez-le comme bloqué
                        elapsed_time = (now - challenge.process_start_time).total_seconds()
                        if elapsed_time > 300:  # 5 minutes
                            self.log(f"Processus bloqué détecté pour {profile}/{challenge.title}: {challenge.current_process_id}")
                            # Trouver le profil propriétaire du processus
                            process_owner = self.find_process_owner(challenge.current_process_id)
                            stalled_processes.append((challenge, challenge.current_process_id, process_owner))
        
        # Nettoyer les processus bloqués
        for challenge, process_id, process_owner in stalled_processes:
            if process_owner and process_id in self.config['players'][process_owner]['process']:
                self.ps_update(process_id, 'timeout', process_owner)
                self.log(f"Processus {process_id} nettoyé après timeout (profil: {process_owner})")
            challenge.current_process_id = None
            challenge.process_start_time = None
        
        # Vérifier les processus "zombie" dans tous les profils
        for player_name in self.config['players'].keys():
            if self.config['players'][player_name].get('process'):
                process_ids = list(self.config['players'][player_name]['process'].keys())
                for process_id in process_ids:
                    if self.config['players'][player_name]['process'][process_id] == 'executing':
                        # Vérifier si ce processus est associé à un challenge actif (dans n'importe quel profil)
                        is_active = False
                        if hasattr(self, 'all_challenges'):
                            for profile, challenges in self.all_challenges.items():
                                for challenge in challenges:
                                    if hasattr(challenge, 'current_process_id') and challenge.current_process_id == process_id:
                                        is_active = True
                                        break
                                if is_active:
                                    break
                        
                        # Si le processus n'est pas associé à un challenge actif, c'est un zombie
                        if not is_active:
                            # Vérifie si le processus est ancien (plus de 10 minutes)
                            timestamp_parts = process_id.split('-')[-1]
                            if not any(marker in timestamp_parts for marker in ['at-', 'left-']):
                                try:
                                    process_time = datetime.strptime(timestamp_parts, '%Y-%m-%d_%H:%M')
                                    if (now - process_time).total_seconds() > 600:  # 10 minutes
                                        self.log(f"Processus zombie détecté: {process_id} (profil: {player_name})")
                                        self.ps_update(process_id, 'zombie', player_name)
                                except ValueError:
                                    # Si on ne peut pas parser la date, on suppose que c'est un zombie
                                    self.log(f"Processus suspect (format de date invalide): {process_id} (profil: {player_name})")
                                    self.ps_update(process_id, 'zombie', player_name)

    def purge_challenge(self):
        #move closed challenge
        for section in self.all_challenges[self.player].keys():
            if datetime.now() > datetime.strptime(self.all_challenges[self.player][section]['end'], "%d/%m/%Y, %H:%M"):
                self.all_challenges[self.player].pop(section)
                print('challenge', section, 'popped')

def main():
    app = QApplication(sys.argv)
    
    # Create and set QEventLoop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create window after setting event loop
    window = ChallengeWindow()
    window.show()
    
    # Run the event loop
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()