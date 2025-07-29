"""
GSGUI Final Desktop UI - Version définitive sans problèmes SSL
"""

import sys
import requests
import threading
import time
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QListWidgetItem, QLabel,
                               QComboBox, QPushButton, QTextEdit, QSplitter, 
                               QApplication, QProgressBar)
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


class FinalApiClient:
    """Client API final avec requests (sans problèmes SSL)"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001/api/v1"
        
    def get_challenges(self, user_token):
        """Récupère les challenges"""
        try:
            params = {'user_token': user_token}
            response = requests.get(f"{self.base_url}/challenges/", params=params, timeout=5)
            
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


class SimpleChallengeItem:
    """Représente un challenge simplifié"""
    def __init__(self, id, title, votes, rank, url):
        self.id = id
        self.title = title
        self.votes = votes
        self.rank = rank
        self.url = url
        self.time_left = 0
        self.selected_strategy = None
        self.turbo_status = 'none'


class FinalGSGUI(QMainWindow):
    """Interface GSGUI finale - Sans problèmes SSL"""
    
    log_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config = ConfigObj('gsgui.ini', encoding='utf-8')
        self.api_client = FinalApiClient()
        self.challenges = {}
        self.player = None
        self.user_token = None
        
        self.init_ui()
        self.load_config()
        
        # Connecter signaux
        self.log_signal.connect(self.append_log)
        
        print("✅ Final GSGUI initialized")
    
    def init_ui(self):
        """Interface utilisateur"""
        self.setWindowTitle("GSGUI Final - Sans SSL")
        self.setGeometry(100, 100, 1200, 700)
        
        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #2c3e50; color: #ecf0f1; }
            QWidget { background-color: #2c3e50; color: #ecf0f1; font-size: 11pt; }
            QPushButton { 
                background-color: #3498db; border: none; color: white; 
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #7f8c8d; }
            QListWidget { 
                background-color: #34495e; border: 1px solid #7f8c8d; 
                border-radius: 4px; padding: 4px;
            }
            QListWidget::item { padding: 6px; border-radius: 3px; }
            QListWidget::item:selected { background-color: #3498db; }
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
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Panel gauche
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Header
        self.profile_label = QLabel("Profil: Non connecté")
        self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e74c3c;")
        left_layout.addWidget(self.profile_label)
        
        # Boutons principaux
        buttons_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
        self.refresh_btn.clicked.connect(self.refresh_challenges)
        buttons_layout.addWidget(self.refresh_btn)
        
        self.all_btn = QPushButton("✅ All")
        self.all_btn.setStyleSheet("QPushButton { background-color: #f39c12; }")
        self.all_btn.clicked.connect(self.select_all)
        buttons_layout.addWidget(self.all_btn)
        
        self.none_btn = QPushButton("❌ None")
        self.none_btn.setStyleSheet("QPushButton { background-color: #e67e22; }")
        self.none_btn.clicked.connect(self.select_none)
        buttons_layout.addWidget(self.none_btn)
        
        left_layout.addLayout(buttons_layout)
        
        # Stratégies
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("Stratégie:"))
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["fill", "4m", "boost", "swap"])
        strategy_layout.addWidget(self.strategy_combo)
        
        self.strategy_btn = QPushButton("📅 Stratégie")
        self.strategy_btn.setStyleSheet("QPushButton { background-color: #9b59b6; }")
        self.strategy_btn.clicked.connect(self.apply_strategy)
        strategy_layout.addWidget(self.strategy_btn)
        
        left_layout.addLayout(strategy_layout)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        self.fill_btn = QPushButton("⚡ Fill")
        self.fill_btn.setStyleSheet("QPushButton { background-color: #16a085; }")
        self.fill_btn.clicked.connect(self.execute_fill)
        actions_layout.addWidget(self.fill_btn)
        
        self.turbo_btn = QPushButton("🚀 Turbo")
        self.turbo_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        self.turbo_btn.clicked.connect(self.execute_turbo)
        actions_layout.addWidget(self.turbo_btn)
        
        left_layout.addLayout(actions_layout)
        
        # Liste des challenges
        self.challenge_list = QListWidget()
        left_layout.addWidget(self.challenge_list)
        
        splitter.addWidget(left_panel)
        
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
        splitter.setSizes([700, 500])
        
        self.log("🎨 Interface finale initialisée")
    
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
                    
                    self.log("🔄 Cliquez sur 'Refresh' pour charger les challenges")
                else:
                    self.log("⚠️ Token manquant")
            else:
                self.log("⚠️ Configuration manquante")
        except Exception as e:
            self.log(f"❌ Erreur config: {e}")
    
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
    
    def on_challenges_received(self, challenges):
        """Callback quand les challenges sont reçus"""
        self.update_list(challenges)
        self.log(f"✅ {len(challenges)} challenges")
        self.status_label.setText(f"{len(challenges)} challenges")
        self.refresh_btn.setEnabled(True)
    
    def on_api_error(self, error):
        """Callback en cas d'erreur API"""
        self.log(f"❌ Erreur: {error}")
        self.status_label.setText("Erreur")
        self.refresh_btn.setEnabled(True)
    
    def update_list(self, challenges_data):
        """Met à jour la liste"""
        self.challenge_list.clear()
        self.challenges = {}
        
        for data in challenges_data:
            challenge = SimpleChallengeItem(
                id=data.get('id', ''),
                title=data.get('title', 'Sans titre'),
                votes=data.get('votes', 0),
                rank=data.get('rank', 999),
                url=data.get('url', '')
            )
            
            challenge.time_left = data.get('time_left_days', 0)
            challenge.selected_strategy = data.get('selected_strategy')
            challenge.turbo_status = data.get('turbo_status', 'none')
            
            self.challenges[challenge.id] = challenge
            
            # Format d'affichage
            time_left = f"{challenge.time_left}j" if challenge.time_left else "Fini"
            
            turbo_emoji = {
                'none': '⚪',
                'running': '🟡', 
                'completed': '🟢',
                'failed': '🔴'
            }.get(challenge.turbo_status, '⚪')
            
            strategy_text = f"📅{challenge.selected_strategy}" if challenge.selected_strategy else "❌"
            
            text = f"{turbo_emoji} {challenge.title[:40]}... | 🗳️{challenge.votes} | 🏆{challenge.rank} | ⏰{time_left} | {strategy_text}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, challenge.id)
            
            # Couleur selon statut
            if challenge.turbo_status == 'running':
                item.setBackground(QColor(241, 196, 15, 50))
            elif challenge.turbo_status == 'completed':
                item.setBackground(QColor(39, 174, 96, 50))
            elif challenge.turbo_status == 'failed':
                item.setBackground(QColor(231, 76, 60, 50))
            
            self.challenge_list.addItem(item)
    
    def get_selected(self):
        """Challenges sélectionnés"""
        selected = []
        for i in range(self.challenge_list.count()):
            item = self.challenge_list.item(i)
            if item.isSelected():
                challenge_id = item.data(Qt.UserRole)
                if challenge_id in self.challenges:
                    selected.append(self.challenges[challenge_id])
        return selected
    
    def select_all(self):
        """Sélectionne tout"""
        for i in range(self.challenge_list.count()):
            self.challenge_list.item(i).setSelected(True)
        self.log(f"✅ {self.challenge_list.count()} sélectionnés")
    
    def select_none(self):
        """Efface sélection"""
        self.challenge_list.clearSelection()
        self.log("❌ Sélection effacée")
    
    def apply_strategy(self):
        """Applique stratégie avec nettoyage automatique"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
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
        """Exécute fill"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
            return
        
        self.fill_btn.setEnabled(False)
        
        def fill_worker():
            try:
                success_count = 0
                for challenge in selected:
                    try:
                        if self.api_client.execute_simple_vote(challenge.url, 80, self.user_token):
                            success_count += 1
                            self.log(f"⚡ Fill: {challenge.title[:30]}...")
                        else:
                            self.log(f"❌ Fill échoué: {challenge.title[:20]}")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                
                self.log(f"✅ Fill sur {success_count}/{len(selected)}")
                
            except Exception as e:
                self.log(f"❌ Fill: {e}")
            finally:
                self.fill_btn.setEnabled(True)
        
        thread = threading.Thread(target=fill_worker)
        thread.start()
    
    def execute_turbo(self):
        """Exécute turbo"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
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
        """Ajoute au log"""
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    window = FinalGSGUI()
    window.show()
    
    app.exec()


if __name__ == "__main__":
    main()