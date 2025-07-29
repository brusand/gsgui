"""
GSGUI Enhanced Desktop UI - Avec vrais challenges et affichage comme l'original
"""

import sys
import requests
import threading
import time
import json
import websocket
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QTableWidget, QTableWidgetItem, QLabel, QCheckBox,
                               QComboBox, QPushButton, QTextEdit, QSplitter, 
                               QApplication, QProgressBar, QHeaderView, QInputDialog)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QColor, QTextCursor
from configobj import ConfigObj


class ApiThread(QThread):
    """Thread pour les appels API"""
    result_ready = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, api_call, *args):
        super().__init__()
        self.api_call = api_call
        self.args = args
        
    def run(self):
        try:
            result = self.api_call(*self.args)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class EnhancedApiClient:
    """Client API enhanced avec requests"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001/api/v1"
        
    def get_challenges(self, user_token):
        """Récupère les vrais challenges"""
        try:
            params = {'user_token': user_token}
            response = requests.get(f"{self.base_url}/challenges/", params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('challenges', [])
            else:
                print(f"❌ API Error: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return []
    
    def register_profile(self, profile_name, gs_token):
        """Enregistre un profil"""
        try:
            data = {
                "profile_name": profile_name,
                "gs_token": gs_token
            }
            response = requests.post(f"{self.base_url}/profiles/register", json=data, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def schedule_strategy(self, challenge_id, strategy_name, scheduled_at, challenge_title=None):
        """Programme une stratégie"""
        try:
            data = {
                "challenge_id": challenge_id,
                "strategy_name": strategy_name,
                "scheduled_at": scheduled_at.isoformat(),
                "challenge_title": challenge_title
            }
            
            profile_id = "bruno"
            response = requests.post(f"{self.base_url}/profiles/{profile_id}/strategies", 
                                   json=data, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def cancel_challenge_strategies(self, challenge_id, profile_id="bruno"):
        """Annule toutes les stratégies d'un challenge"""
        try:
            # Récupérer les stratégies
            response = requests.get(f"{self.base_url}/profiles/{profile_id}/strategies", timeout=5)
            if response.status_code != 200:
                return 0
                
            strategies_data = response.json()
            strategies = strategies_data.get('strategies', [])
            
            cancelled = 0
            for strategy in strategies:
                if strategy.get('challenge_id') == challenge_id and strategy.get('status') == 'pending':
                    strategy_id = strategy.get('strategy_id')
                    try:
                        response = requests.delete(f"{self.base_url}/profiles/{profile_id}/strategies/{strategy_id}", 
                                                 timeout=5)
                        if response.status_code == 200:
                            cancelled += 1
                    except:
                        pass
            
            return cancelled
        except:
            return 0
    
    def execute_turbo(self, challenge_id, challenge_title=None):
        """Exécute un turbo"""
        try:
            data = {
                "challenge_id": challenge_id,
                "challenge_title": challenge_title,
                "challenge_time_left": "1j"
            }
            
            profile_id = "bruno"
            response = requests.post(f"{self.base_url}/profiles/{profile_id}/turbo/execute", 
                                   json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('turbo_id') is not None
            return False
        except:
            return False
    
    def execute_simple_vote(self, challenge_url, vote_count, user_token):
        """Exécute un vote simple"""
        try:
            data = {
                "challenge_url": challenge_url,
                "vote_count": vote_count
            }
            
            params = {'user_token': user_token}
            response = requests.post(f"{self.base_url}/challenges/simple-vote", 
                                   json=data, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except:
            return False


class ChallengeItem:
    """Représente un challenge enhanced"""
    def __init__(self, data):
        self.id = str(data.get('id', ''))
        self.title = data.get('title', 'Sans titre')
        self.url = data.get('url', '')
        self.votes = int(data.get('votes', 0))
        self.rank = int(data.get('rank', 999))
        self.level = data.get('level', '')
        self.exposure = data.get('exposure', '')
        self.gps = int(data.get('gps', 0))
        self.time_left_days = int(data.get('time_left_days', 0))
        self.selected_strategy = data.get('selected_strategy')
        self.turbo_status = data.get('turbo_status', 'none')
        
        # Calcul précis du temps restant depuis les données API
        time_left_data = data.get('time_left', {})
        if isinstance(time_left_data, dict):
            days = int(time_left_data.get('days', 0))
            hours = int(time_left_data.get('hours', 0))
            minutes = int(time_left_data.get('minutes', 0))
            seconds = int(time_left_data.get('seconds', 0))
        else:
            # Fallback avec days seulement
            days = self.time_left_days
            hours = minutes = seconds = 0
        
        # Calcul du temps total en secondes pour tri et countdown
        self.time_left_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
        
        # Format d'affichage du temps (style GSGUI: 0D 0H 0M 0S)
        self.time_left_display = f"{days:d}D {hours:02d}H {minutes:02d}M {seconds:02d}S"
        
        # Date de fin calculée précisément depuis le temps restant exact
        end_datetime = datetime.now() + timedelta(seconds=self.time_left_seconds)
        self.end_time = end_datetime.strftime("%d/%m %H:%M")


class EnhancedGSGUI(QMainWindow):
    """Interface GSGUI Enhanced - Comme l'original"""
    
    log_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config = ConfigObj('gsgui.ini', encoding='utf-8')
        self.api_client = EnhancedApiClient()
        self.challenges = {}
        self.selected_challenges = set()
        self.player = None
        self.user_token = None
        
        # Auto-refresh (par défaut désactivé)
        self.auto_refresh_enabled = False
        
        # Charger les stratégies
        self.strategies = self.load_strategies()
        
        self.init_ui()
        self.load_config()
        
        # Connecter signaux
        self.log_signal.connect(self.append_log)
        
        # Timer pour countdown (comme GSGUI original)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # Mise à jour chaque seconde
        
        # Timer pour auto-refresh (toutes les 15 secondes)
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_challenges)
        # Ne démarre qu'après la première connexion
        
        # WebSocket pour logs temps réel
        self.websocket_client = None
        self.connect_websocket()
        
        print("✅ Enhanced GSGUI initialized")
        
        # Charger automatiquement les challenges au démarrage
        QTimer.singleShot(500, self.auto_load_challenges)  # Attendre 500ms que l'UI soit prête
    
    def auto_load_challenges(self):
        """Charge automatiquement les challenges au démarrage"""
        if self.user_token:
            self.log("🔄 Chargement automatique des challenges...")
            self.refresh_challenges()
        else:
            self.log("⚠️ Aucun token configuré - Veuillez configurer votre profil")
    
    def load_strategies(self):
        """Charge les stratégies depuis strategies.ini"""
        try:
            strategies_config = ConfigObj('strategies.ini', encoding='utf-8')
            strategy_names = list(strategies_config.keys())
            print(f"📋 Stratégies chargées: {strategy_names}")
            return strategy_names
        except Exception as e:
            print(f"❌ Erreur chargement stratégies: {e}")
            return ["fill", "4m", "3m", "2m", "Bruno", "alain", "caloune"]
    
    def init_ui(self):
        """Interface utilisateur enhanced"""
        self.setWindowTitle("GSGUI Enhanced - Comme l'original")
        self.setGeometry(100, 100, 1400, 800)
        
        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #2c3e50; color: #ecf0f1; }
            QWidget { background-color: #2c3e50; color: #ecf0f1; font-size: 10pt; }
            QPushButton { 
                background-color: #3498db; border: none; color: white; 
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #7f8c8d; }
            QTableWidget { 
                background-color: #34495e; border: 1px solid #7f8c8d; 
                border-radius: 4px; gridline-color: #7f8c8d;
                selection-background-color: #3498db;
            }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background-color: #3498db; }
            QHeaderView::section { 
                background-color: #2c3e50; color: #ecf0f1; 
                padding: 8px; border: 1px solid #7f8c8d; font-weight: bold;
            }
            QTextEdit { 
                background-color: #34495e; border: 1px solid #7f8c8d; 
                border-radius: 4px; font-family: monospace; font-size: 9pt;
            }
            QComboBox { 
                background-color: #34495e; border: 1px solid #7f8c8d; 
                border-radius: 4px; padding: 4px; 
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header avec profil et boutons
        header_layout = QHBoxLayout()
        
        self.profile_label = QLabel("Profil: Non connecté")
        self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e74c3c;")
        header_layout.addWidget(self.profile_label)
        
        header_layout.addStretch()
        
        # Boutons principaux
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
        self.refresh_btn.clicked.connect(self.refresh_challenges)
        header_layout.addWidget(self.refresh_btn)
        
        # Bouton Auto-Refresh
        self.auto_refresh_btn = QPushButton("🔄 Auto: OFF")
        self.auto_refresh_btn.setStyleSheet("QPushButton { background-color: #7f8c8d; }")
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_btn)
        
        self.all_btn = QPushButton("✅ All")
        self.all_btn.setStyleSheet("QPushButton { background-color: #f39c12; }")
        self.all_btn.clicked.connect(self.select_all)
        header_layout.addWidget(self.all_btn)
        
        self.none_btn = QPushButton("❌ None")
        self.none_btn.setStyleSheet("QPushButton { background-color: #e67e22; }")
        self.none_btn.clicked.connect(self.select_none)
        header_layout.addWidget(self.none_btn)
        
        main_layout.addLayout(header_layout)
        
        # Actions avec stratégies
        actions_layout = QHBoxLayout()
        
        actions_layout.addWidget(QLabel("Stratégie:"))
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self.strategies)
        actions_layout.addWidget(self.strategy_combo)
        
        self.strategy_btn = QPushButton("📅 Stratégie")
        self.strategy_btn.setStyleSheet("QPushButton { background-color: #9b59b6; }")
        self.strategy_btn.clicked.connect(self.apply_strategy)
        actions_layout.addWidget(self.strategy_btn)
        
        self.fill_btn = QPushButton("⚡ Fill")
        self.fill_btn.setStyleSheet("QPushButton { background-color: #16a085; }")
        self.fill_btn.clicked.connect(self.execute_fill)
        actions_layout.addWidget(self.fill_btn)
        
        self.turbo_btn = QPushButton("🚀 Turbo")
        self.turbo_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        self.turbo_btn.clicked.connect(self.execute_turbo)
        actions_layout.addWidget(self.turbo_btn)
        
        # Bouton Stratégies en cours
        self.strategies_btn = QPushButton("📋 Stratégies en cours")
        self.strategies_btn.setStyleSheet("QPushButton { background-color: #8e44ad; }")
        self.strategies_btn.clicked.connect(self.show_active_strategies)
        actions_layout.addWidget(self.strategies_btn)
        
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Tableau des challenges (style GSGUI original)
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(10)
        self.challenge_table.setHorizontalHeaderLabels([
            "Title", "End Time", "Remaining", "Votes", "Rank", 
            "Level", "Exposure", "GPS", "Stratégie", "Turbo"
        ])
        
        # Configuration du tableau
        header = self.challenge_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Title
        
        # Largeurs fixes pour les autres colonnes
        self.challenge_table.setColumnWidth(1, 120)  # End Time  
        self.challenge_table.setColumnWidth(2, 100)  # Remaining
        self.challenge_table.setColumnWidth(3, 80)   # Votes
        self.challenge_table.setColumnWidth(4, 60)   # Rank
        self.challenge_table.setColumnWidth(5, 80)   # Level
        self.challenge_table.setColumnWidth(6, 80)   # Exposure
        self.challenge_table.setColumnWidth(7, 60)   # GPS
        self.challenge_table.setColumnWidth(8, 100)  # Stratégie
        self.challenge_table.setColumnWidth(9, 80)   # Turbo
        
        # Sélection par lignes
        self.challenge_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.challenge_table.setAlternatingRowColors(True)
        
        splitter.addWidget(self.challenge_table)
        
        # Panel droit - Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("📋 Logs"))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Prêt")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        right_layout.addWidget(self.status_label)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 400])
        
        self.log("🎨 Interface enhanced initialisée")
    
    def load_config(self):
        """Charge la configuration"""
        try:
            if 'players' in self.config and self.config['players']:
                self.player = list(self.config['players'].keys())[0]
                self.user_token = self.config['players'][self.player].get('xtoken', '')
                
                if self.user_token:
                    self.profile_label.setText(f"Profil: {self.player}")
                    self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #27ae60;")
                    self.log(f"✅ Profil: {self.player}")
                    
                    # Enregistrer profil
                    if self.api_client.register_profile(self.player, self.user_token):
                        self.log("🔌 API: registered")
                    
                    self.log("🔄 Cliquez sur 'Refresh' pour charger vos challenges")
                    
                    # Charger l'état auto-refresh
                    self.load_auto_refresh_state()
                else:
                    self.log("⚠️ Token manquant")
            else:
                self.log("⚠️ Configuration manquante")
        except Exception as e:
            self.log(f"❌ Erreur config: {e}")
    
    def load_auto_refresh_state(self):
        """Charge l'état de l'auto-refresh depuis la config"""
        try:
            auto_refresh_enabled = self.config.get('ui_settings', {}).get('auto_refresh_enabled', False)
            if isinstance(auto_refresh_enabled, str):
                auto_refresh_enabled = auto_refresh_enabled.lower() == 'true'
            
            if auto_refresh_enabled:
                self.auto_refresh_enabled = True
                self.auto_refresh_btn.setText("🔄 Auto: ON")
                self.auto_refresh_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
                self.log("📖 Auto-refresh: ON (depuis config)")
            else:
                self.log("📖 Auto-refresh: OFF (depuis config)")
        except Exception as e:
            self.log(f"⚠️ Erreur chargement auto-refresh: {e}")
    
    def save_auto_refresh_state(self):
        """Sauvegarde l'état de l'auto-refresh dans la config"""
        try:
            if 'ui_settings' not in self.config:
                self.config['ui_settings'] = {}
            
            self.config['ui_settings']['auto_refresh_enabled'] = str(self.auto_refresh_enabled)
            self.config.write()
        except Exception as e:
            self.log(f"⚠️ Erreur sauvegarde auto-refresh: {e}")
    
    def refresh_challenges(self):
        """Rafraîchit les challenges"""
        if not self.user_token:
            self.log("❌ Token manquant")
            return
        
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Chargement...")
        
        # Lancer l'appel API dans un thread
        self.api_thread = ApiThread(self.api_client.get_challenges, self.user_token)
        self.api_thread.result_ready.connect(self.on_challenges_received)
        self.api_thread.error_occurred.connect(self.on_api_error)
        self.api_thread.start()
    
    def on_challenges_received(self, challenges_data):
        """Callback quand les challenges sont reçus"""
        # Créer les objets challenges
        challenges = []
        for data in challenges_data:
            challenge = ChallengeItem(data)
            challenges.append(challenge)
        
        # Trier par temps restant croissant (comme GSGUI original)
        challenges.sort(key=lambda x: x.time_left_seconds)
        
        self.update_table(challenges)
        self.log(f"✅ {len(challenges)} challenges (triés par temps restant)")
        self.status_label.setText(f"{len(challenges)} challenges")
        self.refresh_btn.setEnabled(True)
        
        # Démarrer l'auto-refresh après le premier chargement réussi
        self.start_auto_refresh()
    
    def on_api_error(self, error):
        """Callback en cas d'erreur API"""
        self.log(f"❌ Erreur: {error}")
        self.status_label.setText("Erreur")
        self.refresh_btn.setEnabled(True)
    
    def update_table(self, challenges):
        """Met à jour le tableau des challenges"""
        self.challenge_table.setRowCount(len(challenges))
        self.challenges = {}
        
        for row, challenge in enumerate(challenges):
            self.challenges[challenge.id] = challenge
            
            # Données du challenge (sans colonne Select)
            title_item = QTableWidgetItem(challenge.title)
            title_item.setData(Qt.UserRole, challenge.id)  # Stocker l'ID pour sélection
            
            # Checkbox en début de titre pour sélection
            if challenge.id in self.selected_challenges:
                title_item.setCheckState(Qt.Checked)
            else:
                title_item.setCheckState(Qt.Unchecked)
            
            self.challenge_table.setItem(row, 0, title_item)
            self.challenge_table.setItem(row, 1, QTableWidgetItem(challenge.end_time))
            self.challenge_table.setItem(row, 2, QTableWidgetItem(challenge.time_left_display))
            self.challenge_table.setItem(row, 3, QTableWidgetItem(str(challenge.votes)))
            self.challenge_table.setItem(row, 4, QTableWidgetItem(str(challenge.rank)))
            self.challenge_table.setItem(row, 5, QTableWidgetItem(str(challenge.level)))
            self.challenge_table.setItem(row, 6, QTableWidgetItem(str(challenge.exposure)))
            self.challenge_table.setItem(row, 7, QTableWidgetItem(str(challenge.gps)))
            
            # Statut stratégie
            strategy_text = challenge.selected_strategy or ""
            self.challenge_table.setItem(row, 8, QTableWidgetItem(strategy_text))
            
            # Statut turbo avec tous les états GSGUI
            turbo_status = challenge.turbo_status
            turbo_indicators = {
                "none": "",
                "running": "🟡 Running",
                "completed": "✅ OK", 
                "failed": "❌ Failed",
                "timer": "⏰ Timer",
                "unknown": "❓ Unknown",
                "locked": "🔒 Locked",
                "free": "🆓 Free",
                "won": "🏆 Won",
                "used": "✅ Used"
            }
            turbo_text = turbo_indicators.get(turbo_status, "")
            
            turbo_item = QTableWidgetItem(turbo_text)
            
            # Couleur de fond selon l'état
            if turbo_status == "running":
                turbo_item.setBackground(QColor(255, 235, 59, 50))  # Jaune transparent
            elif turbo_status == "completed":
                turbo_item.setBackground(QColor(76, 175, 80, 50))   # Vert transparent
            elif turbo_status == "failed":
                turbo_item.setBackground(QColor(244, 67, 54, 50))   # Rouge transparent
            elif turbo_status == "timer":
                turbo_item.setBackground(QColor(255, 152, 0, 50))   # Orange transparent
            elif turbo_status == "unknown":
                turbo_item.setBackground(QColor(158, 158, 158, 50)) # Gris transparent
            elif turbo_status == "locked":
                turbo_item.setBackground(QColor(96, 125, 139, 50))  # Bleu-gris transparent
            elif turbo_status == "free":
                turbo_item.setBackground(QColor(139, 195, 74, 50))  # Vert clair transparent
            elif turbo_status == "won":
                turbo_item.setBackground(QColor(255, 193, 7, 50))   # Doré transparent
            elif turbo_status == "used":
                turbo_item.setBackground(QColor(76, 175, 80, 50))   # Vert transparent (comme completed)
                
            self.challenge_table.setItem(row, 9, turbo_item)
        
        # Connecter le signal de changement d'état des checkboxes
        self.challenge_table.itemChanged.connect(self.on_item_changed)
    
    def on_item_changed(self, item):
        """Gère les changements d'état des checkboxes"""
        if item.column() == 0:  # Colonne Title avec checkbox
            challenge_id = item.data(Qt.UserRole)
            if challenge_id:
                if item.checkState() == Qt.Checked:
                    self.selected_challenges.add(challenge_id)
                else:
                    self.selected_challenges.discard(challenge_id)
    
    def update_countdown(self):
        """Met à jour le countdown des challenges (comme GSGUI original)"""
        if not self.challenges:
            return
        
        try:
            updated = False
            for challenge in self.challenges.values():
                if challenge.time_left_seconds > 0:
                    challenge.time_left_seconds -= 1
                    
                    # Recalculer le format d'affichage
                    days = challenge.time_left_seconds // 86400
                    hours = (challenge.time_left_seconds % 86400) // 3600
                    minutes = (challenge.time_left_seconds % 3600) // 60
                    seconds = challenge.time_left_seconds % 60
                    
                    new_display = f"{days:d}D {hours:02d}H {minutes:02d}M {seconds:02d}S"
                    if new_display != challenge.time_left_display:
                        challenge.time_left_display = new_display
                        updated = True
                else:
                    if challenge.time_left_display != "0D 00H 00M 00S":
                        challenge.time_left_display = "0D 00H 00M 00S"
                        updated = True
            
            if updated:
                self.update_remaining_column_only()
                
        except Exception as e:
            pass  # Ignore countdown errors
    
    def update_remaining_column_only(self):
        """Met à jour seulement la colonne Remaining pour éviter le scintillement"""
        for row in range(self.challenge_table.rowCount()):
            title_item = self.challenge_table.item(row, 0)
            if title_item:
                challenge_id = title_item.data(Qt.UserRole)
                if challenge_id in self.challenges:
                    challenge = self.challenges[challenge_id]
                    remaining_item = self.challenge_table.item(row, 2)
                    if remaining_item and remaining_item.text() != challenge.time_left_display:
                        remaining_item.setText(challenge.time_left_display)
    
    def auto_refresh_challenges(self):
        """Auto-refresh des challenges toutes les 15 secondes"""
        if self.user_token and hasattr(self, 'refresh_btn') and self.refresh_btn.isEnabled():
            self.log("🔄 Auto-refresh...")
            self.refresh_challenges()
    
    def start_auto_refresh(self):
        """Démarre l'auto-refresh après la première connexion réussie"""
        if self.auto_refresh_enabled and not self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.start(60000)  # 1 minute
            self.log("⏰ Auto-refresh activé (1 min)")
    
    def toggle_auto_refresh(self):
        """Active/désactive l'auto-refresh"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        if self.auto_refresh_enabled:
            # Activer auto-refresh
            self.auto_refresh_btn.setText("🔄 Auto: ON")
            self.auto_refresh_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start(60000)  # 1 minute
            self.log("✅ Auto-refresh activé (1 min)")
        else:
            # Désactiver auto-refresh
            self.auto_refresh_btn.setText("🔄 Auto: OFF")
            self.auto_refresh_btn.setStyleSheet("QPushButton { background-color: #7f8c8d; }")
            if self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.stop()
            self.log("❌ Auto-refresh désactivé")
        
        # Sauvegarder l'état
        self.save_auto_refresh_state()
    
    def toggle_selection(self, challenge_id):
        """Toggle sélection d'un challenge"""
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)
    
    def get_selected(self):
        """Challenges sélectionnés"""
        return [self.challenges[cid] for cid in self.selected_challenges if cid in self.challenges]
    
    def select_all(self):
        """Sélectionne tous les challenges"""
        self.selected_challenges = set(self.challenges.keys())
        self.refresh_table_selection()
        self.log(f"✅ {len(self.selected_challenges)} challenges sélectionnés")
    
    def select_none(self):
        """Efface la sélection"""
        self.selected_challenges = set()
        self.refresh_table_selection()
        self.log("❌ Sélection effacée")
    
    def refresh_table_selection(self):
        """Refresh les checkboxes du tableau"""
        for row in range(self.challenge_table.rowCount()):
            title_item = self.challenge_table.item(row, 0)
            if title_item:
                challenge_id = title_item.data(Qt.UserRole)
                if challenge_id:
                    if challenge_id in self.selected_challenges:
                        title_item.setCheckState(Qt.Checked)
                    else:
                        title_item.setCheckState(Qt.Unchecked)
    
    def apply_strategy(self):
        """Applique stratégie avec nettoyage automatique"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucun challenge sélectionné")
            return
        
        strategy = self.strategy_combo.currentText()
        self.strategy_btn.setEnabled(False)
        
        def strategy_worker():
            try:
                success_count = 0
                for challenge in selected:
                    try:
                        # Nettoyer existantes (fonctionnalité critique)
                        cancelled = self.api_client.cancel_challenge_strategies(challenge.id)
                        if cancelled > 0:
                            self.log(f"🧹 {cancelled} stratégie(s) annulée(s): {challenge.title[:20]}...")
                        
                        # Nouvelle stratégie
                        scheduled_time = datetime.now() + timedelta(minutes=2)
                        if self.api_client.schedule_strategy(challenge.id, strategy, scheduled_time, challenge.title):
                            success_count += 1
                            self.log(f"📅 {strategy}: {challenge.title[:30]}...")
                        else:
                            self.log(f"❌ Échec stratégie: {challenge.title[:20]}")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                
                self.log(f"✅ Stratégie {strategy} appliquée à {success_count}/{len(selected)}")
                
            except Exception as e:
                self.log(f"❌ Erreur stratégie: {e}")
            finally:
                self.strategy_btn.setEnabled(True)
        
        # Lancer dans un thread
        thread = threading.Thread(target=strategy_worker)
        thread.start()
    
    def execute_fill(self):
        """Exécute fill avec popup pour saisir le nombre de votes"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucun challenge sélectionné")
            return
        
        # Popup pour saisir le nombre de votes (comme GSGUI original)
        vote_count, ok = QInputDialog.getInt(
            self, 
            "⚡ Fill - Nombre de votes", 
            f"Nombre de votes à exécuter pour {len(selected)} challenge(s) sélectionné(s):",
            80,  # Valeur par défaut
            1,   # Minimum
            999, # Maximum
            1    # Step
        )
        
        if not ok:
            self.log("❌ Fill annulé")
            return
        
        self.log(f"🚀 Démarrage Fill: {vote_count} votes sur {len(selected)} challenges")
        self.fill_btn.setEnabled(False)
        
        def fill_worker():
            try:
                success_count = 0
                for challenge in selected:
                    try:
                        if self.api_client.execute_simple_vote(challenge.url, vote_count, self.user_token):
                            success_count += 1
                            self.log(f"⚡ Fill ({vote_count}): {challenge.title[:30]}...")
                        else:
                            self.log(f"❌ Fill échoué: {challenge.title[:20]}")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                
                self.log(f"✅ Fill terminé: {success_count}/{len(selected)} challenges - {vote_count} votes chacun")
                
                # Refresh automatique après tous les fills pour mettre à jour les votes
                if success_count > 0:
                    self.log("🔄 Refresh automatique des challenges après Fill...")
                    self.refresh_challenges()
                
            except Exception as e:
                self.log(f"❌ Erreur Fill: {e}")
            finally:
                self.fill_btn.setEnabled(True)
        
        thread = threading.Thread(target=fill_worker)
        thread.start()
    
    def execute_turbo(self):
        """Exécute turbo"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucun challenge sélectionné")
            return
        
        self.turbo_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected))
        
        def turbo_worker():
            try:
                success_count = 0
                for i, challenge in enumerate(selected):
                    try:
                        self.log(f"🚀 Turbo: {challenge.title[:30]}...")
                        
                        if self.api_client.execute_turbo(challenge.id, challenge.title):
                            success_count += 1
                            self.log(f"✅ Turbo: {challenge.title[:20]}")
                        else:
                            self.log(f"❌ Turbo échoué: {challenge.title[:20]}")
                        
                        self.progress_bar.setValue(i + 1)
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                        self.progress_bar.setValue(i + 1)
                
                self.log(f"✅ Turbo sur {success_count}/{len(selected)}")
                
            except Exception as e:
                self.log(f"❌ Turbo: {e}")
            finally:
                self.turbo_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
        
        thread = threading.Thread(target=turbo_worker)
        thread.start()
    
    def log(self, message):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.log_signal.emit(formatted)
    
    def append_log(self, message):
        """Ajoute au log et gère les signaux spéciaux"""
        # Gérer le signal spécial pour afficher la fenêtre stratégies
        if message == "SHOW_STRATEGIES_DIALOG":
            try:
                self.log_text.append("[🪟] Ouverture fenêtre stratégies...")
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_text.setTextCursor(cursor)
                
                # Afficher les stratégies dans la fenêtre de log principale
                if hasattr(self, 'strategies_data'):
                    # Récupérer les logs formatés et les afficher dans notre log
                    strategies_text = self.get_formatted_strategies_text(self.strategies_data)
                    
                    # Afficher les stratégies dans la fenêtre de log principale
                    for line in strategies_text.split('\n'):
                        if line.strip():  # Ignorer les lignes vides
                            self.log_text.append(line)
                    
                    self.log_text.append("[✅] Stratégies affichées dans les logs")
                else:
                    self.log_text.append("[❌] Données stratégies manquantes")
                    
            except Exception as e:
                self.log_text.append(f"[❌] Erreur fenêtre: {e}")
            return
        
        # Log normal
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def connect_websocket(self):
        """Connecte au WebSocket pour les logs temps réel"""
        def websocket_worker():
            try:
                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        timestamp = data.get('timestamp', '')[:19]  # Couper les millisecondes
                        msg_type = data.get('type', 'info')
                        msg_text = data.get('message', '')
                        
                        # Formater selon le type
                        if msg_type == "success":
                            formatted = f"[{timestamp[-8:]}] ✅ {msg_text}"
                        elif msg_type == "error":
                            formatted = f"[{timestamp[-8:]}] ❌ {msg_text}"
                        elif msg_type == "warning":
                            formatted = f"[{timestamp[-8:]}] ⚠️ {msg_text}"
                        else:
                            formatted = f"[{timestamp[-8:]}] {msg_text}"
                        
                        # Émettre le signal pour l'UI
                        self.log_signal.emit(formatted)
                        
                    except Exception as e:
                        self.log_signal.emit(f"❌ WebSocket parse error: {e}")
                
                def on_error(ws, error):
                    self.log_signal.emit(f"🔌 WebSocket error: {error}")
                
                def on_close(ws, close_status_code, close_msg):
                    self.log_signal.emit("🔌 WebSocket connection closed")
                
                def on_open(ws):
                    self.log_signal.emit("🔌 WebSocket connected - Real-time logs enabled")
                
                # Créer et démarrer la connexion WebSocket
                ws_url = "ws://localhost:8001/ws/logs"
                self.websocket_client = websocket.WebSocketApp(
                    ws_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )
                
                self.websocket_client.run_forever()
                
            except Exception as e:
                self.log_signal.emit(f"❌ WebSocket connection failed: {e}")
        
        # Lancer dans un thread séparé
        websocket_thread = threading.Thread(target=websocket_worker, daemon=True)
        websocket_thread.start()
    
    def show_active_strategies(self):
        """Affiche la fenêtre des stratégies en cours"""
        def strategies_worker():
            try:
                self.log("🔍 Appel API /strategies/active...")
                
                # Appel API pour récupérer les stratégies actives avec token
                params = {'user_token': self.user_token} if self.user_token else {}
                response = requests.get(f"{self.api_client.base_url}/strategies/active", params=params, timeout=10)
                
                self.log(f"📡 API Response: {response.status_code}")
                
                if response.status_code == 200:
                    strategies_data = response.json()
                    total_jobs = strategies_data.get('total_jobs', 0)
                    total_count = strategies_data.get('total_count', 0)
                    
                    self.log(f"✅ Récupéré {total_count} stratégies, {total_jobs} jobs")
                    
                    # Sauvegarder les données et déclencher l'affichage
                    self.strategies_data = strategies_data
                    
                    # Émettre un signal personnalisé pour afficher la fenêtre
                    self.log_signal.emit("SHOW_STRATEGIES_DIALOG")
                    
                else:
                    self.log(f"❌ Erreur API stratégies: {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ Erreur récupération stratégies: {e}")
                import traceback
                self.log(f"📋 Traceback: {traceback.format_exc()}")
        
        # Lancer dans un thread pour éviter blocage UI
        thread = threading.Thread(target=strategies_worker, daemon=True)
        thread.start()
        
        self.log("📋 Chargement des stratégies en cours...")
    
    def get_formatted_strategies_text(self, strategies_data):
        """Génère le texte formaté des stratégies (même logique que StrategiesDialog)"""
        try:
            output = []
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            output.append("=== STRATÉGIES EN COURS ===")
            
            strategies = strategies_data.get('strategies', [])
            total_jobs = strategies_data.get('total_jobs', 0)
            
            if not strategies:
                output.append(f"[{timestamp}] [bruno] Aucune stratégie en cours")
            else:
                # Grouper par challenge
                for strategy in strategies:
                    challenge_id = strategy['challenge_id']
                    strategy_name = strategy['strategy_name']
                    actions = strategy.get('actions', [])
                    
                    # Nom du challenge (enrichi depuis l'API)
                    challenge_title = strategy.get('challenge_title', f"Challenge {challenge_id}")
                    
                    output.append(f"[{timestamp}] [bruno] 🎯 {challenge_title}:")
                    
                    if not actions:
                        output.append(f"[{timestamp}] [bruno]    ⚠️ Aucune action définie")
                    else:
                        for action in actions:
                            timing = action.get('timing', '')
                            votes = action.get('votes', 0)
                            
                            # Formater le timing (end-4m0s -> 00:04:00)
                            formatted_time = self.format_timing_simple(timing)
                            
                            output.append(f"[{timestamp}] [bruno]    ⏰ {formatted_time} - Vote {votes} pour {challenge_title}")
            
            # Résumé
            output.append("")
            output.append(f"[{timestamp}] [bruno] 📊 Total: {total_jobs} job(s) programmé(s)")
            output.append("")
            output.append(f"[{timestamp}] [bruno] 💾 Stratégies persistantes:")
            
            for strategy in strategies:
                challenge_id = strategy['challenge_id']
                strategy_name = strategy['strategy_name']
                challenge_title = strategy.get('challenge_title', f"Challenge {challenge_id}")
                output.append(f"[{timestamp}] [bruno]    📝 {challenge_title}: {strategy_name}")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"❌ Erreur formatage stratégies: {e}"
    
    def format_timing_simple(self, timing):
        """Formate le timing end-4m0s -> 00:04:00 (version simplifiée)"""
        try:
            if timing.startswith('end-'):
                # end-4m0s -> 4m0s
                time_part = timing[4:]
                
                # Parser 4m0s -> 4 minutes 0 secondes
                minutes = 0
                seconds = 0
                
                if 'm' in time_part:
                    parts = time_part.split('m')
                    minutes = int(parts[0])
                    if len(parts) > 1 and parts[1] and parts[1] != 's':
                        seconds = int(parts[1].replace('s', ''))
                
                return f"{minutes:02d}:{seconds:02d}:00"
            
            return timing
        except:
            return timing


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    window = EnhancedGSGUI()
    window.show()
    
    app.exec()


if __name__ == "__main__":
    main()