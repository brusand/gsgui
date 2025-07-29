"""
GSGUI Modern Desktop UI - Interface esthétique simplifiée avec API backend
"""

import argparse
import sys
import asyncio
import threading
import os
import ssl
from datetime import datetime, timedelta

import qasync
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QListWidget, QListWidgetItem, QCheckBox, QLabel,
                               QComboBox, QPushButton, QFrame, QTextEdit, QSplitter, 
                               QApplication, QHeaderView, QTableWidget,
                               QTableWidgetItem, QDialog, QDialogButtonBox, QTabWidget,
                               QInputDialog, QMessageBox, QGridLayout, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QMetaObject, Q_ARG, QThread
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor
from configobj import ConfigObj
from qasync import QEventLoop, asyncSlot

from gsui_api_client import GSGUIApiClient

# SSL Context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class ModernChallengeItem:
    """Représente un challenge dans l'interface moderne"""
    def __init__(self, id, title, end_time, time_left, url, votes, rank, level, exposure, gps):
        self.id = id
        self.title = title
        self.end_time = end_time
        self.time_left = time_left
        self.url = url
        self.votes = votes
        self.rank = rank
        self.level = level
        self.exposure = exposure
        self.gps = gps
        self.selected_strategy = None
        self.turbo_status = 'none'  # 'none', 'running', 'completed', 'failed'


class ModernGSGUI(QMainWindow):
    """Interface GSGUI moderne et simplifiée"""
    
    # Signaux
    log_signal = Signal(str)
    challenge_updated = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config_file = 'gsgui.ini'
        self.config = ConfigObj(self.config_file, encoding='utf-8')
        
        # API Client
        self.api_client = GSGUIApiClient()
        
        # État
        self.challenges = {}
        self.player = None
        self.user_token = None
        
        # Interface
        self.init_ui()
        self.load_user_config()
        
        # Timers
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_challenges)
        
        # Connecter signaux
        self.log_signal.connect(self.append_log)
        
        print("🎨 Modern GSGUI initialized")
    
    def init_ui(self):
        """Initialise l'interface utilisateur moderne"""
        self.setWindowTitle("GSGUI Modern - API Backend")
        self.setGeometry(100, 100, 1400, 800)
        
        # Style moderne
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
                color: #ecf0f1;
            }
            QWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 11pt;
                font-weight: bold;
                margin: 4px 2px;
                border-radius: 6px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #bdc3c7;
            }
            QListWidget {
                background-color: #34495e;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 5px;
                alternate-background-color: #2c3e50;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4a5568;
                margin: 2px 0px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #4a5568;
            }
            QTextEdit {
                background-color: #34495e;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
            QComboBox {
                background-color: #34495e;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #34495e;
                border: 1px solid #7f8c8d;
                selection-background-color: #3498db;
            }
            QLabel {
                color: #ecf0f1;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                text-align: center;
                background-color: #34495e;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter principal
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # --- Panel de gauche : Challenges ---
        left_panel = QWidget()
        left_panel.setMinimumWidth(600)
        left_layout = QVBoxLayout(left_panel)
        
        # Header avec boutons principaux
        header_layout = QHBoxLayout()
        
        # Profile info
        self.profile_label = QLabel("Profil: Non connecté")
        self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e74c3c;")
        header_layout.addWidget(self.profile_label)
        
        header_layout.addStretch()
        
        # Bouton Refresh
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                min-width: 120px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_challenges)
        header_layout.addWidget(self.refresh_btn)
        
        left_layout.addLayout(header_layout)
        
        # Actions rapides
        actions_layout = QHBoxLayout()
        
        # Sélection All/None
        self.all_btn = QPushButton("✅ All")
        self.all_btn.setStyleSheet("QPushButton { background-color: #f39c12; min-width: 80px; }")
        self.all_btn.clicked.connect(self.select_all_challenges)
        actions_layout.addWidget(self.all_btn)
        
        self.none_btn = QPushButton("❌ None")
        self.none_btn.setStyleSheet("QPushButton { background-color: #e67e22; min-width: 80px; }")
        self.none_btn.clicked.connect(self.select_none_challenges)
        actions_layout.addWidget(self.none_btn)
        
        actions_layout.addStretch()
        
        # Stratégies
        strategy_label = QLabel("Stratégie:")
        strategy_label.setStyleSheet("font-weight: bold; margin-right: 10px;")
        actions_layout.addWidget(strategy_label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["fill", "4m", "boost", "swap"])
        self.strategy_combo.setCurrentText("fill")
        actions_layout.addWidget(self.strategy_combo)
        
        self.strategy_btn = QPushButton("📅 Stratégie")
        self.strategy_btn.setStyleSheet("QPushButton { background-color: #9b59b6; min-width: 120px; }")
        self.strategy_btn.clicked.connect(self.apply_strategy_to_selected)
        actions_layout.addWidget(self.strategy_btn)
        
        left_layout.addLayout(actions_layout)
        
        # Actions Turbo et Fill
        turbo_layout = QHBoxLayout()
        
        self.fill_btn = QPushButton("⚡ Fill")
        self.fill_btn.setStyleSheet("QPushButton { background-color: #16a085; min-width: 100px; font-size: 12pt; }")
        self.fill_btn.clicked.connect(self.execute_fill_selected)
        turbo_layout.addWidget(self.fill_btn)
        
        self.turbo_btn = QPushButton("🚀 Turbo")
        self.turbo_btn.setStyleSheet("QPushButton { background-color: #e74c3c; min-width: 100px; font-size: 12pt; }")
        self.turbo_btn.clicked.connect(self.execute_turbo_selected)
        turbo_layout.addWidget(self.turbo_btn)
        
        turbo_layout.addStretch()
        
        left_layout.addLayout(turbo_layout)
        
        # Liste des challenges
        self.challenge_list = QListWidget()
        self.challenge_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.challenge_list)
        
        main_splitter.addWidget(left_panel)
        
        # --- Panel de droite : Logs ---
        right_panel = QWidget()
        right_panel.setMinimumWidth(500)
        right_layout = QVBoxLayout(right_panel)
        
        # Header logs
        logs_header = QLabel("📋 Logs d'activité")
        logs_header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3498db; margin-bottom: 10px;")
        right_layout.addWidget(logs_header)
        
        # Zone de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(400)
        right_layout.addWidget(self.log_text)
        
        # Barre de progression (pour turbo/stratégies)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_label = QLabel("Prêt")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 10px;")
        right_layout.addWidget(self.status_label)
        
        main_splitter.addWidget(right_panel)
        
        # Proportions du splitter
        main_splitter.setSizes([800, 600])
        
        self.log("🎨 Interface moderne initialisée")
    
    def load_user_config(self):
        """Charge la configuration utilisateur"""
        try:
            if 'players' not in self.config:
                self.config['players'] = {}
            
            # Prendre le premier joueur ou en créer un
            if self.config['players']:
                self.player = list(self.config['players'].keys())[0]
                player_config = self.config['players'][self.player]
                self.user_token = player_config.get('xtoken', '')
                
                if self.user_token:
                    self.profile_label.setText(f"Profil: {self.player}")
                    self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #27ae60;")
                    self.log(f"✅ Profil chargé: {self.player}")
                    
                    # Enregistrer le profil avec l'API
                    asyncio.create_task(self.register_api_profile())
                else:
                    self.log("⚠️ Aucun token trouvé dans la configuration")
            else:
                self.log("⚠️ Aucun joueur configuré")
                
        except Exception as e:
            self.log(f"❌ Erreur chargement config: {e}")
    
    @asyncSlot()
    async def register_api_profile(self):
        """Enregistre le profil avec l'API backend"""
        try:
            async with self.api_client as client:
                result = await client.register_profile(self.player, self.user_token)
                self.log(f"🔌 Profil API enregistré: {result.get('status', 'unknown')}")
                
        except Exception as e:
            self.log(f"❌ Erreur enregistrement API: {e}")
    
    @asyncSlot()
    async def refresh_challenges(self):
        """Rafraîchit la liste des challenges"""
        try:
            if not self.user_token:
                self.log("❌ Aucun token disponible")
                return
            
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("🔄 Loading...")
            self.status_label.setText("Chargement des challenges...")
            
            # Récupérer les challenges depuis l'API
            async with self.api_client as client:
                challenges = await client.get_challenges(self.user_token)
            
            # Mettre à jour la liste
            self.update_challenge_list(challenges)
            
            self.log(f"✅ {len(challenges)} challenges chargés")
            self.status_label.setText(f"{len(challenges)} challenges disponibles")
            
        except Exception as e:
            self.log(f"❌ Erreur rafraîchissement: {e}")
            self.status_label.setText("Erreur lors du chargement")
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("🔄 Refresh")
    
    def update_challenge_list(self, challenges_data):
        """Met à jour la liste des challenges dans l'interface"""
        try:
            self.challenge_list.clear()
            self.challenges = {}
            
            for challenge_data in challenges_data:
                # Créer l'objet challenge
                challenge = ModernChallengeItem(
                    id=challenge_data.get('id', ''),
                    title=challenge_data.get('title', 'Untitled'),
                    end_time=challenge_data.get('end_time', ''),
                    time_left=challenge_data.get('time_left_days', 0),
                    url=challenge_data.get('url', ''),
                    votes=challenge_data.get('votes', 0),
                    rank=challenge_data.get('rank', 999),
                    level=challenge_data.get('level', ''),
                    exposure=challenge_data.get('exposure', ''),
                    gps=challenge_data.get('gps', '')
                )
                
                challenge.selected_strategy = challenge_data.get('selected_strategy')
                challenge.turbo_status = challenge_data.get('turbo_status', 'none')
                
                self.challenges[challenge.id] = challenge
                
                # Créer l'item de liste
                self.create_challenge_list_item(challenge)
            
            self.challenge_updated.emit()
            
        except Exception as e:
            self.log(f"❌ Erreur mise à jour liste: {e}")
    
    def create_challenge_list_item(self, challenge):
        """Crée un item de liste pour un challenge"""
        try:
            # Formatage du temps restant
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
            
            # Texte de l'item
            item_text = f"{turbo_emoji} {challenge.title[:40]}... | 🗳️{challenge.votes} | 🏆{challenge.rank} | ⏰{time_left} | {strategy_text}"
            
            # Créer l'item
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, challenge.id)
            
            # Couleur selon le statut
            if challenge.turbo_status == 'running':
                item.setBackground(QColor(241, 196, 15, 50))  # Jaune transparent
            elif challenge.turbo_status == 'completed':
                item.setBackground(QColor(39, 174, 96, 50))   # Vert transparent
            elif challenge.turbo_status == 'failed':
                item.setBackground(QColor(231, 76, 60, 50))   # Rouge transparent
            
            # Tooltip
            tooltip = f"""Titre: {challenge.title}
Votes: {challenge.votes}
Rang: {challenge.rank}
Niveau: {challenge.level}
Exposure: {challenge.exposure}
Temps restant: {time_left}
Stratégie: {challenge.selected_strategy or 'Aucune'}
Turbo: {challenge.turbo_status}"""
            item.setToolTip(tooltip)
            
            self.challenge_list.addItem(item)
            
        except Exception as e:
            self.log(f"❌ Erreur création item: {e}")
    
    def get_selected_challenges(self):
        """Retourne les challenges sélectionnés"""
        selected = []
        for i in range(self.challenge_list.count()):
            item = self.challenge_list.item(i)
            if item.isSelected():
                challenge_id = item.data(Qt.UserRole)
                if challenge_id in self.challenges:
                    selected.append(self.challenges[challenge_id])
        return selected
    
    def select_all_challenges(self):
        """Sélectionne tous les challenges"""
        for i in range(self.challenge_list.count()):
            self.challenge_list.item(i).setSelected(True)
        self.log(f"✅ {self.challenge_list.count()} challenges sélectionnés")
    
    def select_none_challenges(self):
        """Désélectionne tous les challenges"""
        self.challenge_list.clearSelection()
        self.log("❌ Sélection effacée")
    
    @asyncSlot()
    async def apply_strategy_to_selected(self):
        """Applique une stratégie aux challenges sélectionnés"""
        try:
            selected = self.get_selected_challenges()
            if not selected:
                self.log("⚠️ Aucun challenge sélectionné")
                return
            
            strategy_name = self.strategy_combo.currentText()
            
            if not strategy_name:
                self.log("⚠️ Aucune stratégie sélectionnée")
                return
            
            self.strategy_btn.setEnabled(False)
            self.strategy_btn.setText("📅 Programmation...")
            
            success_count = 0
            
            async with self.api_client as client:
                for challenge in selected:
                    try:
                        # Nettoyer les stratégies existantes pour ce challenge
                        cancelled = await client.cancel_challenge_strategies(challenge.id)
                        if cancelled > 0:
                            self.log(f"🧹 {cancelled} stratégie(s) annulée(s) pour {challenge.title[:30]}...")
                        
                        # Programmer la nouvelle stratégie à la fin du challenge
                        # Calculer le moment d'exécution (2 minutes avant la fin)
                        scheduled_time = datetime.now() + timedelta(minutes=2)  # Exemple: dans 2 minutes
                        
                        result = await client.schedule_strategy(
                            challenge_id=challenge.id,
                            strategy_name=strategy_name,
                            scheduled_at=scheduled_time,
                            challenge_title=challenge.title
                        )
                        
                        challenge.selected_strategy = strategy_name
                        success_count += 1
                        
                        self.log(f"📅 Stratégie {strategy_name} programmée: {challenge.title[:30]}...")
                        
                    except Exception as e:
                        self.log(f"❌ Erreur stratégie {challenge.title[:30]}...: {e}")
            
            # Rafraîchir l'affichage
            await self.refresh_challenges()
            
            self.log(f"✅ Stratégie {strategy_name} appliquée à {success_count}/{len(selected)} challenges")
            
        except Exception as e:
            self.log(f"❌ Erreur application stratégie: {e}")
        finally:
            self.strategy_btn.setEnabled(True)
            self.strategy_btn.setText("📅 Stratégie")
    
    @asyncSlot()
    async def execute_fill_selected(self):
        """Exécute un fill sur les challenges sélectionnés"""
        try:
            selected = self.get_selected_challenges()
            if not selected:
                self.log("⚠️ Aucun challenge sélectionné")
                return
            
            self.fill_btn.setEnabled(False)
            self.fill_btn.setText("⚡ Execution...")
            
            success_count = 0
            
            async with self.api_client as client:
                for challenge in selected:
                    try:
                        result = await client.execute_simple_vote(
                            challenge_url=challenge.url,
                            vote_count=80,  # Fill = max votes
                            user_token=self.user_token
                        )
                        
                        if result.get('success', False):
                            success_count += 1
                            self.log(f"⚡ Fill réussi: {challenge.title[:30]}...")
                        else:
                            self.log(f"❌ Fill échoué: {challenge.title[:30]}... - {result.get('message', 'Erreur inconnue')}")
                        
                    except Exception as e:
                        self.log(f"❌ Erreur fill {challenge.title[:30]}...: {e}")
            
            self.log(f"✅ Fill exécuté sur {success_count}/{len(selected)} challenges")
            
        except Exception as e:
            self.log(f"❌ Erreur exécution fill: {e}")
        finally:
            self.fill_btn.setEnabled(True)
            self.fill_btn.setText("⚡ Fill")
    
    @asyncSlot()
    async def execute_turbo_selected(self):
        """Exécute un turbo sur les challenges sélectionnés"""
        try:
            selected = self.get_selected_challenges()
            if not selected:
                self.log("⚠️ Aucun challenge sélectionné")
                return
            
            self.turbo_btn.setEnabled(False)
            self.turbo_btn.setText("🚀 Execution...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(selected))
            self.progress_bar.setValue(0)
            
            success_count = 0
            
            async with self.api_client as client:
                for i, challenge in enumerate(selected):
                    try:
                        self.log(f"🚀 Démarrage turbo: {challenge.title[:30]}...")
                        
                        result = await client.execute_turbo(
                            challenge_id=challenge.id,
                            challenge_title=challenge.title,
                            challenge_time_left=f"{challenge.time_left}j"
                        )
                        
                        turbo_id = result.get('turbo_id')
                        if turbo_id:
                            challenge.turbo_status = 'running'
                            success_count += 1
                            self.log(f"🚀 Turbo démarré: {challenge.title[:30]}... (ID: {turbo_id})")
                        else:
                            self.log(f"❌ Turbo échoué: {challenge.title[:30]}...")
                        
                        self.progress_bar.setValue(i + 1)
                        
                        # Petite pause entre les turbos
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.log(f"❌ Erreur turbo {challenge.title[:30]}...: {e}")
                        self.progress_bar.setValue(i + 1)
            
            # Rafraîchir l'affichage
            await self.refresh_challenges()
            
            self.log(f"✅ Turbo démarré sur {success_count}/{len(selected)} challenges")
            
        except Exception as e:
            self.log(f"❌ Erreur exécution turbo: {e}")
        finally:
            self.turbo_btn.setEnabled(True)
            self.turbo_btn.setText("🚀 Turbo")
            self.progress_bar.setVisible(False)
    
    def log(self, message):
        """Ajoute un message aux logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_signal.emit(formatted_message)
    
    def append_log(self, message):
        """Ajoute un message à la zone de logs (thread-safe)"""
        self.log_text.append(message)
        # Auto-scroll vers le bas
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def auto_refresh_challenges(self):
        """Rafraîchissement automatique des challenges"""
        if hasattr(self, 'user_token') and self.user_token:
            asyncio.create_task(self.refresh_challenges())
    
    def closeEvent(self, event):
        """Gestionnaire de fermeture de l'application"""
        try:
            self.auto_refresh_timer.stop()
            self.log("👋 Fermeture de l'application")
            event.accept()
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()


def main():
    """Point d'entrée principal"""
    app = QApplication(sys.argv)
    
    # Create and set QEventLoop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create main window
    window = ModernGSGUI()
    window.show()
    
    # Run the application
    with loop:
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print("\n👋 Application interrompue par l'utilisateur")
        finally:
            loop.close()


if __name__ == "__main__":
    main()