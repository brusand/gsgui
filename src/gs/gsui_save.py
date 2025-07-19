import argparse
import sys
import asyncio
import threading
import os
import requests

import qasync
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QListWidgetItem, QCheckBox, QLabel,
                               QComboBox, QPushButton, QFrame, QTextEdit, QSplitter, QApplication, QTableWidget,
                               QHeaderView, QTableWidgetItem)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QMetaObject
import aiohttp
from datetime import datetime, timedelta, time

from configobj import ConfigObj
from qasync import QEventLoop, asyncSlot

from src.gs.gsprompt import GuruBatch
from PySide6.QtGui import QFont
from time import sleep


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
        self.status = ""  # Statut initial vide
        self.challenge = challenge
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
            async with aiohttp.ClientSession(headers=self.aio_header) as session:
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
                            time_left="{}D {}H {}M".format(timeleft["days"], timeleft["hours"],
                                                           timeleft["minutes"]),
                            url=challenge_data['url'],
                            exposure=int(challenge_data['member']['ranking']['total']['exposure']),
                            votes=int(challenge_data['member']['ranking']['total']['votes']),
                            rank=int(challenge_data['member']['ranking']['total']['rank']),
                            level=challenge_data['member']['ranking']['total']['level_name'],
                            # if challenge_data['member']['ranking']['total'].get('gps') is not None:
                            gps=int(0),  # gps=challenge_data['member']['ranking']['total']['gps'],
                            challenge=challenge_data

                        )
                        challenges.append(challenge)
                    self.finished.emit(challenges)
        except Exception as e:
            print(f"Error fetching challenges: {e}")
            self.finished.emit([])

    async def votes(self, url, count):
        try:
            async with aiohttp.ClientSession(headers=self.aio_header) as session:
                async with session.post(url, data={'count': count}) as response:
                    if response.status == 200:
                        result = await response.text()
                        # self.vote_finished.emit(f"Voted successfully: {result}")
                        return await response.read()
                    else:
                        return await response.read()  # self.vote_finished.emit(f"Vote failed with status: {response.status}")
        except Exception as e:
            self.vote_finished.emit(f"Error during voting: {str(e)}")

    async def fetch_get_votes_panel(self, challenge, count):
        try:
            # Vérifier que le challenge a une URL valide
            if not hasattr(challenge, 'url') or not challenge.url:
                error_result = {"success": False, "message": "Challenge URL is missing or invalid"}
                self.get_votes_panel_finished.emit(challenge, error_result, -1 * count)
                return

            # Log pour le débogage
            self.loggs(
                f"Récupération des données de vote pour {challenge.title} (URL: {challenge.url}, HEADER:{self.aio_header})")

            async with aiohttp.ClientSession(headers=self.aio_header) as session:
                async with session.post('https://api.gurushots.com/rest/get_vote_data',
                                        data={'limit': 100, 'url': challenge.url}) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # Vérifier que la réponse contient bien des images
                            if not result.get('images') or len(result.get('images', [])) == 0:
                                self.loggs(f"Pas d'images disponibles pour {challenge.title}, {result}")
                                self.get_votes_panel_finished.emit(challenge,
                                                                   {"success": False, "message": "No images available",
                                                                    "challenge": {"close_time": 0}}, -1 * count)
                            else:
                                self.loggs(
                                    f"Récupération réussie: {len(result.get('images', []))} images pour {challenge.title}")
                                self.get_votes_panel_finished.emit(challenge, result, count)
                        except Exception as json_error:
                            error_text = await response.text()
                            self.loggs(f"Erreur de parsing JSON: {json_error}, Réponse: {error_text[:100]}...")
                            self.get_votes_panel_finished.emit(challenge, {"success": False,
                                                                           "message": f"JSON parsing error: {json_error}",
                                                                           "challenge": {"close_time": 0}}, -1 * count)
                    else:
                        error_text = await response.text()
                        self.loggs(f"Erreur HTTP {response.status}: {error_text[:100]}...")
                        self.get_votes_panel_finished.emit(challenge, {"success": False,
                                                                       "message": f"HTTP {response.status}: {error_text}",
                                                                       "challenge": {"close_time": 0}}, -1 * count)
        except Exception as e:
            # (f"Exception générale lors de la récupération des votes: {e}")
            self.get_votes_panel_finished.emit(challenge,
                                               {"success": False, "message": str(e), "challenge": {"close_time": 0}},
                                               -1 * count)

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
            payload[
                'c_token'] = "03AOLTBLR8mMuwAHd5TwbZo5KuuMZYDUVbM-gwQZgojsOHPf-NdlccOUjk6DXw6QE3thLUf6ASwqgQigw1-zTLI6-prjlTIS9ByBXVvePZkYXGwf6MDNIielvqiEWTemoMPWkKVSPme0EOALsd0MrbwDFHxbS02LGpt2u9GwieEKurIUmP7IKNxPEVBGwSR9UTDhWLfUimQK-yDKBVzIZYmbiEHM6gw85-9jDbtGtaAKcEGio83U6b4lmaGWVr8jhWYDKW49PDPrlc0hqYoV1nAOMySaIstamSZP56Zzp3ejo_1A0EqMOL1vGaG5aKt8a-tFY26Q9TRROHx8lVNcJoSBuBHFGUzl2n12JLjqAvJd6BcOweUMlhJapSrwSgHpRl5UQJ58G2AkWdMMvkwbplXZCqQ8cdv_HAzduBOwzutsfuubfCk0Fgqfb1wFK1FrfSGyRVhgrmci12xKmiIrIP1ZIOycaCXI7V0-sY5TW94mmjknYGwUiCdNI"

            # Envoyer la requête avec les tokens valides
            async with aiohttp.ClientSession(headers=self.aio_header) as session:
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

        # self.parser_ps = self.subparsers.add_parser('ps')
        # self.parser_ps.add_argument('ps', nargs='?', action="store", default='')
        # self.parser_ps.add_argument('--list', action="store_true", default=False)
        # self.parser_ps.add_argument('--pop', nargs='?', action="store", default='')
        # self.parser_ps.set_defaults(func=self.ps)

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

        self.config = ConfigObj('gsgui.ini')
        if self.config.get('players') == None:
            self.config['players'] = {}
        self.config.write()
        args = self.parser.parse_args()
        if args.player == '':
            self.player = self.config.get('player')
        else:
            self.player = args.player
        self.init_player(self.player)

        # Initialiser le scheduler après avoir configuré le joueur
        self.init_scheduler()





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

        self.xtoken = self.config['players'][args.player]['xtoken']

        self.threads = {}
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
        # self.challenges = self.all_challenges[self.player]
        self.selected_challenges = set()

        self.profiles = []
        # for player in self.config['players'].keys():
        #    self.profiles.append(player)
        self.profiles.append(self.player)
        # Connecter le signal de vote à la méthode de vote
        self.vote_request.connect(self.vote_challenge)

        # Timer pour nettoyer les processus bloqués
        self.process_monitor_timer = QTimer(self)
        self.process_monitor_timer.timeout.connect(self.check_stalled_processes)
        self.process_monitor_timer.start(60000)  # Vérifier toutes les minutes

        self.init_ui()
        self.fetcher.set_log(self.result_panel)

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
        top_bar.addWidget(refresh_button)
        top_bar.addWidget(all_button)
        top_bar.addWidget(none_button)
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
        # self.challenge_list = QListWidget()
        # self.challenge_list.setSelectionMode(QListWidget.NoSelection)
        # splitter.addWidget(self.challenge_list)
        # title, end_time, time_left, url, votes, rank, level, exposure, gps

        # Challenge table
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(11)
        self.challenge_table.setHorizontalHeaderLabels(
            ["Select", "Title", "End Time", "Remaining", "Votes", "Rank", "Level", "Exposure", "GPS", "Strategy",
             "En cours"])
        # Masquer la numérotation des lignes (row headers)
        self.challenge_table.verticalHeader().setVisible(False)
        # Définir Stretch pour toutes les colonnes sauf les colonnes de titre et End Time
        self.challenge_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Définir ResizeToContents pour la colonne de titre (index 1) et End Time (index 2)
        self.challenge_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.challenge_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

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
        self.log("Challenges fetching ...")

        # S'assurer que le dictionnaire all_challenges existe
        if not hasattr(self, 'all_challenges'):
            self.all_challenges = {}

        # S'assurer que le set de challenges existe pour ce profil
        if self.player not in self.all_challenges:
            self.all_challenges[self.player] = set()

        # Mettre à jour la référence pour être sûr
        # self.challenges = self.all_challenges[self.player]

        # Identifier les nouveaux challenges avant de mettre à jour
        previous_challenges = {c.id for c in self.all_challenges[self.player]} if self.all_challenges[
            self.player] else set()

        # Mettre à jour la liste complète des challenges pour le profil actuel
        sorted_challenges = self.sort_challenges(challenges)

        # Réinitialiser le set de challenges pour ce profil
        self.all_challenges[self.player] = set(sorted_challenges)

        # Mettre à jour la référence
        # self.challenges = self.all_challenges[self.player]

        # Lancer la stratégie de fin par défaut pour chaque nouveau challenge
        new_challenges = []
        for challenge in self.all_challenges[self.player]:
            if challenge.id not in previous_challenges:
                new_challenges.append(challenge)

        # Peupler le tableau des challenges
        self.populate_challenge_table()

        # Lancer les stratégies de fin automatiquement pour les nouveaux challenges
        if new_challenges:
            self.log(f"Lancement automatique des stratégies de fin pour {len(new_challenges)} nouveaux challenges...")
            for challenge in new_challenges:
                self.log(f"Nouveau challenge détecté pour {self.player}: {challenge.title}")
                # self.strategy(challenge)

        self.log(f"Challenges fetched successfully for {self.player}!")

        # Rafraîchir l'interface une dernière fois après tout traitement
        self.schedule_update()

    @Slot(list)
    def on_get_votes_panel_fetched(self, challenge, panel, count):
        self.log("Voting fetching ...")
        self.voting_challenge(challenge, panel, count)
        # sleep(3)
        # self.voting_challenge(challenge, panel, count)

    def on_post_votes_panel_fetched(self, challenge, result):
        success = result.get("success", False) if isinstance(result, dict) else False

        # Afficher le résultat du vote
        if success:
            # self.result_panel.append(f'{challenge.title} voted successfully')
            self.log(f'{challenge.title} voted successfully')
        else:
            error_msg = str(result) if not isinstance(result,
                                                      dict) else f"Vote failed: {result.get('message', 'Unknown error')}"
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
            # votes = 0
            # while votes < count:
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
            # erreur
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

            # Strategy
            strategy_combo = QComboBox()

            strategy_combo.addItems(self.strategies.keys())

            # Vérifier si une stratégie est sauvegardée dans le fichier ini
            challenge_key = challenge.url.split('/')[-1]  # Extrait la dernière partie de l'URL
            saved_strategy = None
            if self.config['players'][self.player].get('challenges') and challenge_key in \
                    self.config['players'][self.player]['challenges']:
                saved_strategy = self.config['players'][self.player]['challenges'][challenge_key]
                self.log(f"Stratégie chargée depuis gsgui.ini pour {self.player}/{challenge.title}: {saved_strategy}")

            # Priorité: 1) Stratégie sauvegardée, 2) Stratégie déjà définie, 3) Stratégie par défaut
            if saved_strategy and saved_strategy in self.strategies.keys():
                challenge.selected_strategy = saved_strategy
            elif not hasattr(challenge, 'selected_strategy') or not challenge.selected_strategy:
                challenge.selected_strategy = self.strategies.keys()[0]

            strategy_combo.setCurrentText(challenge.selected_strategy)
            strategy_combo.currentTextChanged.connect(lambda text, c=challenge: self.update_challenge_strategy(c, text))
            strategy_widget = QWidget()
            strategy_layout = QHBoxLayout(strategy_widget)
            strategy_layout.addWidget(strategy_combo)
            strategy_layout.setAlignment(Qt.AlignCenter)
            strategy_layout.setContentsMargins(0, 0, 0, 0)
            self.challenge_table.setCellWidget(row, 9, strategy_widget)

            # En cours (colonne 10) - Vérifie si des processus sont actifs pour ce challenge
            status = "Non"
            if self.config['players'][self.player].get('process'):
                for process_id in self.config['players'][self.player]['process'].keys():
                    if challenge.url in process_id and self.config['players'][self.player]['process'][process_id] in (
                            'init', 'waiting', 'executing'):
                        status = "Oui"
                        break
            self.challenge_table.setItem(row, 10, self.create_centered_item(status))

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

        # info_layout = QVBoxLayout()

        layout.addWidget(QLabel(f"{challenge.title}"))
        layout.addWidget(QLabel(f"End {challenge.end_time}"))
        layout.addWidget(QLabel(f"Left {challenge.time_left}"))

        layout.addWidget(QLabel(f"Votes {challenge.votes}"))
        layout.addWidget(QLabel(f"Rank {challenge.rank}"))
        layout.addWidget(QLabel(f"level {challenge.level}"))
        layout.addWidget(QLabel(f"exposure {challenge.exposure}"))

        # if challenge.gps > 0:
        #    layout.addWidget(QLabel(f"GURU PICK {challenge.gps}"))

        # layout.addLayout(info_layout)

        strategy_combo = QComboBox()
        strategy_combo.addItems(self.strategies.keys())

        # Vérifier si une stratégie est sauvegardée dans le fichier ini
        challenge_key = challenge.url.split('/')[-1]  # Extrait la dernière partie de l'URL
        saved_strategy = None
        if self.config['players'][self.player].get('challenges') and challenge_key in \
                self.config['players'][self.player]['challenges']:
            saved_strategy = self.config['players'][self.player]['challenges'][challenge_key]

        # Priorité: 1) Stratégie sauvegardée, 2) Stratégie déjà définie
        if saved_strategy and saved_strategy in self.strategies.keys():
            challenge.selected_strategy = saved_strategy

        strategy_combo.setCurrentText(challenge.selected_strategy)
        strategy_combo.currentTextChanged.connect(lambda text, c=challenge: self.update_challenge_strategy(c, text))
        layout.addWidget(strategy_combo)

        # status_label = QLabel(f"Status: {challenge.status}")
        # status_label.setObjectName(f"status_label_{challenge.id}")
        # layout.addWidget(status_label)

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

    def show_in_progress_challenges(self):
        result = "Challenges en cours de traitement:\n"
        active_challenges = False

        if self.config['players'][self.player].get('process'):
            for process_id in self.config['players'][self.player]['process'].keys():
                status = self.config['players'][self.player]['process'][process_id]
                if status in ('init', 'waiting', 'executing', 'done'):
                    active_challenges = True
                    # Trouver le challenge correspondant
                    challenge_url = None
                    for part in process_id.split('-'):
                        if 'gurushots.com' in part:
                            challenge_url = part
                            break

                    if challenge_url:
                        challenge = next((c for c in self.all_challenges[self.player] if c.url == challenge_url), None)
                        if challenge:
                            result += f"- {challenge.title}: {status}\n"
                        else:
                            result += f"- URL: {challenge_url}: {status}\n"
                    else:
                        result += f"- Processus: {process_id}: {status}\n"

        if not active_challenges:
            result += "Aucun challenge en cours de traitement.\n"

        self.log(result)
        # Aussi afficher la liste complète des processus
        self.ps_list()

    def update_challenge_list(self):
        now = datetime.now()
        self.all_challenges[self.player] = self.sort_challenges(self.all_challenges[self.player])
        # self.populate_challenge_list()
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
                        self.challenge_table.setItem(row, 10, self.create_centered_item("Oui"))

                # Call the votes method
                self.vote_challenge(challenge, 35)

        self.log(result)
        self.update_challenge_table()  # Update the table to reflect changes

    @asyncSlot()
    async def fin_selected_challenges(self):
        result = f"Application des stratégies pour les challenges sélectionnés:\n"
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                result += f"- {challenge.title} avec stratégie {challenge.selected_strategy}\n"

                # Application de la stratégie
                self.strategy(challenge)

        self.log(result)
        # La méthode strategy lance des processus qui vont automatiquement
        # mettre à jour la table via ps_update

    def stop_selected_strategies(self):
        result = f"Arrêt des stratégies pour les challenges sélectionnés:\n"
        process_stopped = False

        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.all_challenges[self.player] if c.id == challenge_id), None)
            if challenge:
                # Rechercher tous les processus associés à ce challenge et les arrêter
                if self.config['players'][self.player].get('process'):
                    # Créer une copie de la liste des clés pour éviter de modifier le dictionnaire pendant l'itération
                    process_ids = list(self.config['players'][self.player]['process'].keys())
                    for process_id in process_ids:
                        if challenge.url in process_id and process_id in self.config['players'][self.player][
                            'process'] and self.config['players'][self.player]['process'][process_id] in ('init',
                                                                                                          'waiting',
                                                                                                          'executing'):
                            self.ps_update(process_id, 'stopped')
                            result += f"- Arrêt et suppression du processus pour {challenge.title}\n"
                            process_stopped = True

        if not process_stopped:
            result += "Aucun processus en cours pour les challenges sélectionnés.\n"

        self.log(result)
        self.schedule_update()

    def stop_all_strategies(self):
        result = "Arrêt de toutes les stratégies en cours:\n"
        process_stopped = False

        if self.config['players'][self.player].get('process'):
            # Créer une copie de la liste des clés pour éviter de modifier le dictionnaire pendant l'itération
            process_ids = list(self.config['players'][self.player]['process'].keys())
            for process_id in process_ids:
                if process_id in self.config['players'][self.player]['process'] and \
                        self.config['players'][self.player]['process'][process_id] in ('init', 'waiting', 'executing'):
                    self.ps_update(process_id, 'stopped')
                    result += f"- Arrêt et suppression du processus: {process_id}\n"
                    process_stopped = True

        if not process_stopped:
            result += "Aucun processus en cours.\n"

        self.log(result)
        self.schedule_update()

    async def vote_panel(self, challenge):
        url = f"https://api.gurushots.com/challenges/{challenge.id}/vote"  # Replace with actual API URL
        await self.fetcher.votes(url, 35)
        # sleep(3)
        # await self.fetcher.votes(url, 35)

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
        # self.result_panel.append(result)
        self.log(f'get challenge_finished {result}')

    def update_challenge_table(self):
        # Refresh the entire table
        self.populate_challenge_table()

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

        self.log(
            f"Profil changé de '{current_profile}' à '{profile}'. Les workers des deux profils continueront à s'exécuter.")

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
        # args.cmde += ' --cha ' + challenge
        if 'at' in args and args.at:
            if args.at == 'now':
                at_time = datetime.now()
            else:
                at_split = args.at.split(':')
                at_day = datetime.now() + timedelta(days=int(at_split[0]))
                at_time = datetime(at_day.year, at_day.month, at_day.day, int(at_split[1]), int(at_split[2]), 0)
            process_id += 'at-' + at_time.strftime('%Y-%m-%d_%H:%M')
        else:
            if 'left' in args and args.left:
                left_delta = args.left.split(':')
                process_id += 'left-' + "{}H:{}M".format(left_delta[0], left_delta[1])
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
                    # raise ('too late')
                else:
                    self.ps_update(process_id, 'waiting', thread_player)

                    while datetime.now() <= at_time:
                        sleep(60)
                        # Vérifier que le profil du thread et le processus existent toujours
                        if (not self.config['players'].get(thread_player) or
                                not self.config['players'][thread_player].get('process') or
                                not self.config['players'][thread_player]['process'].get(process_id)):
                            self.log(
                                f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
                            return
                        if self.config['players'][thread_player]['process'][process_id] == 'stop':
                            self.ps_update(process_id, 'stopped', thread_player)
                            return
            if 'left' in args and args.left:
                # challenge_details = self.all_challenges[self.player][challenge]
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
                                self.log(
                                    f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
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
                                response = requests.post('https://api.gurushots.com/rest/get_my_active_challenges',
                                                         headers=headers)
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
                # challenge_details = self.challenges[challenge]
                when_day = datetime.now();
                when_time = datetime(when_day.year, when_day.month, when_day.day, when_day.hour + int(when_delta[0]),
                                     when_day.minute + int(when_delta[1]), 0)
                self.ps_update(process_id, 'waiting', thread_player)
                waiting_time = True
                while waiting_time:
                    try:
                        # Vérifier que le profil du thread et le processus existent toujours
                        if (not self.config['players'].get(thread_player) or
                                not self.config['players'][thread_player].get('process') or
                                not self.config['players'][thread_player]['process'].get(process_id)):
                            self.log(
                                f"Arrêt du processus {process_id}: profil {thread_player} ou processus non disponible")
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
                            # sleep(5)
                        else:
                            self.log(f"Erreur: Challenge non trouvé: {challenge}")
                    except Exception as e:
                        self.log(f"Erreur lors de l'exécution de vote_challenge: {str(e)}")
                if action in "ps":
                    self.ps_list()

            # self.ps_update(process_id, 'success')
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
        self.threads[challenge] = threading.Thread(target=self.action_thread_args, name=challenge + action + str(value),
                                                   kwargs=dict(challenge=challenge, action=action, value=str(value),
                                                               args=args))
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
            # self.ps_list()
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
                if self.config['players'][self.player].get('cmdes') and self.config['players'][self.player][
                    'cmdes'].get(process_id):
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
                if self.config['players'][target_player].get('cmdes') and self.config['players'][target_player][
                    'cmdes'].get(process_id):
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
            self.log(
                f'process id  : , {process_id}, status, {self.config["players"][self.player]["process"][process_id]}, cmde, {self.config["players"][self.player]["cmdes"][process_id]}')

    def ps_restart(self, args):
        if self.config['players'][self.player]['process'].keys is not None:
            for process_id in self.config['players'][self.player]['process'].keys():
                if self.config['players'][self.player]['process'][process_id] in 'waiting':
                    args = self.parser.parse_args(self.config['players'][self.player]['cmdes'][process_id].split())
                    # if args.cha is not None:
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
            print(self.config['players'][self.player]['cmdes'][process_id])

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
                # print 'cmde', args.cmde
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
                    if hasattr(challenge,
                               'current_process_id') and challenge.current_process_id and challenge.process_start_time:
                        # Si le processus est en cours depuis plus de 5 minutes, considérez-le comme bloqué
                        elapsed_time = (now - challenge.process_start_time).total_seconds()
                        if elapsed_time > 300:  # 5 minutes
                            self.log(
                                f"Processus bloqué détecté pour {profile}/{challenge.title}: {challenge.current_process_id}")
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
                                    if hasattr(challenge,
                                               'current_process_id') and challenge.current_process_id == process_id:
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
                                    self.log(
                                        f"Processus suspect (format de date invalide): {process_id} (profil: {player_name})")
                                    self.ps_update(process_id, 'zombie', player_name)

    def purge_challenge(self):
        # move closed challenge
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