"""
GSGUI Simple Desktop UI - Interface simplifiée avec API backend
"""

import sys
import asyncio
import os
import ssl
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QListWidgetItem, QLabel,
                               QComboBox, QPushButton, QTextEdit, QSplitter, 
                               QApplication, QProgressBar)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QTextCursor
from configobj import ConfigObj
import qasync
from qasync import asyncSlot

# Configuration SSL comme dans l'original
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

from gsui_api_client import GSGUIApiClient


class SimpleChallengeItem:
    """Représente un challenge simplifié"""
    def __init__(self, id, title, votes, rank, url):
        self.id = id
        self.title = title
        self.votes = votes
        self.rank = rank
        self.url = url
        self.selected_strategy = None


class SimpleGSGUI(QMainWindow):
    """Interface GSGUI simplifiée"""
    
    log_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config = ConfigObj('gsgui.ini', encoding='utf-8')
        self.api_client = GSGUIApiClient()
        self.challenges = {}
        self.player = None
        self.user_token = None
        
        self.init_ui()
        self.load_config()
        
        # Connecter signaux
        self.log_signal.connect(self.append_log)
        
        print("✅ Simple GSGUI initialized")
        print(f"Configuration loaded: {self.player}, Token: {'Oui' if self.user_token else 'Non'}")
    
    def init_ui(self):
        """Interface utilisateur simplifiée"""
        self.setWindowTitle("GSGUI Simple - API Backend")
        self.setGeometry(100, 100, 1200, 700)
        
        # Style simple
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
        
        # Widget central avec splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Panel gauche - Challenges
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
        
        self.log("🎨 Interface simple initialisée")
    
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
                    
                    # Enregistrer avec l'API
                    asyncio.create_task(self.register_profile())
                    
                    self.log("🔄 Cliquez sur 'Refresh' pour charger les challenges")
                else:
                    self.log("⚠️ Token manquant")
            else:
                self.log("⚠️ Configuration manquante")
        except Exception as e:
            self.log(f"❌ Erreur config: {e}")
    
    @asyncSlot()
    async def register_profile(self):
        """Enregistre le profil"""
        try:
            async with self.api_client as client:
                result = await client.register_profile(self.player, self.user_token)
                self.log(f"🔌 API: {result.get('status', 'ok')}")
        except Exception as e:
            self.log(f"❌ API erreur: {e}")
    
    def auto_refresh_startup(self):
        """Auto-refresh au démarrage avec QTimer"""
        self.log("🔄 Auto-refresh démarrage...")
        asyncio.create_task(self.refresh_challenges())
    
    @asyncSlot()
    async def refresh_challenges(self):
        """Rafraîchit les challenges"""
        if not self.user_token:
            self.log("❌ Token manquant")
            return
        
        try:
            self.refresh_btn.setEnabled(False)
            self.status_label.setText("Chargement...")
            
            async with self.api_client as client:
                challenges = await client.get_challenges(self.user_token)
            self.update_list(challenges)
            self.log(f"✅ {len(challenges)} challenges")
            self.status_label.setText(f"{len(challenges)} challenges")
            
        except Exception as e:
            self.log(f"❌ Refresh: {e}")
            self.status_label.setText("Erreur")
        finally:
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
            
            # Ajouter les propriétés manquantes depuis les données
            challenge.time_left = data.get('time_left_days', 0)
            challenge.selected_strategy = data.get('selected_strategy')
            challenge.turbo_status = data.get('turbo_status', 'none')
            
            self.challenges[challenge.id] = challenge
            
            # Format identique à gsui_modern_clean
            time_left = f"{challenge.time_left}j" if challenge.time_left else "Fini"
            
            # Statut turbo
            turbo_emoji = {
                'none': '⚪',
                'running': '🟡', 
                'completed': '🟢',
                'failed': '🔴'
            }.get(challenge.turbo_status, '⚪')
            
            # Stratégie
            strategy_text = f"📅{challenge.selected_strategy}" if challenge.selected_strategy else "❌"
            
            # Texte identique à modern_clean
            text = f"{turbo_emoji} {challenge.title[:40]}... | 🗳️{challenge.votes} | 🏆{challenge.rank} | ⏰{time_left} | {strategy_text}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, challenge.id)
            
            # Couleur selon le statut turbo
            if challenge.turbo_status == 'running':
                item.setBackground(QColor(241, 196, 15, 50))  # Jaune transparent
            elif challenge.turbo_status == 'completed':
                item.setBackground(QColor(39, 174, 96, 50))   # Vert transparent
            elif challenge.turbo_status == 'failed':
                item.setBackground(QColor(231, 76, 60, 50))   # Rouge transparent
            
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
    
    @asyncSlot()
    async def apply_strategy(self):
        """Applique stratégie"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
            return
        
        strategy = self.strategy_combo.currentText()
        self.strategy_btn.setEnabled(False)
        
        try:
            async with self.api_client as client:
                for challenge in selected:
                    try:
                        # Nettoyer existantes
                        await client.cancel_challenge_strategies(challenge.id)
                        
                        # Nouvelle stratégie
                        scheduled_time = datetime.now() + timedelta(minutes=2)
                        await client.schedule_strategy(
                            challenge_id=challenge.id,
                            strategy_name=strategy,
                            scheduled_at=scheduled_time,
                            challenge_title=challenge.title
                        )
                        
                        self.log(f"📅 {strategy}: {challenge.title[:30]}...")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
            
            self.log(f"✅ Stratégie {strategy} appliquée")
            
        except Exception as e:
            self.log(f"❌ Stratégie: {e}")
        finally:
            self.strategy_btn.setEnabled(True)
    
    @asyncSlot()
    async def execute_fill(self):
        """Exécute fill"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
            return
        
        self.fill_btn.setEnabled(False)
        
        try:
            async with self.api_client as client:
                for challenge in selected:
                    try:
                        result = await client.execute_simple_vote(
                            challenge_url=challenge.url,
                            vote_count=80,
                            user_token=self.user_token
                        )
                        
                        if result.get('success'):
                            self.log(f"⚡ Fill: {challenge.title[:30]}...")
                        else:
                            self.log(f"❌ Fill: {challenge.title[:20]}")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
            
            self.log("✅ Fill terminé")
            
        except Exception as e:
            self.log(f"❌ Fill: {e}")
        finally:
            self.fill_btn.setEnabled(True)
    
    @asyncSlot()
    async def execute_turbo(self):
        """Exécute turbo"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucune sélection")
            return
        
        self.turbo_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected))
        
        try:
            async with self.api_client as client:
                for i, challenge in enumerate(selected):
                    try:
                        self.log(f"🚀 Turbo: {challenge.title[:30]}...")
                        
                        result = await client.execute_turbo(
                            challenge_id=challenge.id,
                            challenge_title=challenge.title
                        )
                        
                        if result.get('turbo_id'):
                            self.log(f"✅ Turbo: {challenge.title[:20]}")
                        else:
                            self.log(f"❌ Turbo: {challenge.title[:20]}")
                        
                        self.progress_bar.setValue(i + 1)
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                        self.progress_bar.setValue(i + 1)
            
            self.log("✅ Turbo terminé")
            
        except Exception as e:
            self.log(f"❌ Turbo: {e}")
        finally:
            self.turbo_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
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


async def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Window
    window = SimpleGSGUI()
    window.show()
    
    # Run
    with loop:
        await loop.run_until_complete(asyncio.Event().wait())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Au revoir")