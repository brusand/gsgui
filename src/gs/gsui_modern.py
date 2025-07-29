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
        
        self.log("🎨 Interface moderne initialisée")\n    \n    def load_user_config(self):\n        """Charge la configuration utilisateur"""\n        try:\n            if 'players' not in self.config:\n                self.config['players'] = {}\n            \n            # Prendre le premier joueur ou en créer un\n            if self.config['players']:\n                self.player = list(self.config['players'].keys())[0]\n                player_config = self.config['players'][self.player]\n                self.user_token = player_config.get('xtoken', '')\n                \n                if self.user_token:\n                    self.profile_label.setText(f"Profil: {self.player}")\n                    self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #27ae60;")\n                    self.log(f"✅ Profil chargé: {self.player}")\n                    \n                    # Enregistrer le profil avec l'API\n                    asyncio.create_task(self.register_api_profile())\n                else:\n                    self.log("⚠️ Aucun token trouvé dans la configuration")\n            else:\n                self.log("⚠️ Aucun joueur configuré")\n                \n        except Exception as e:\n            self.log(f"❌ Erreur chargement config: {e}")\n    \n    @asyncSlot()\n    async def register_api_profile(self):\n        """Enregistre le profil avec l'API backend"""\n        try:\n            async with self.api_client as client:\n                result = await client.register_profile(self.player, self.user_token)\n                self.log(f"🔌 Profil API enregistré: {result.get('status', 'unknown')}")\n                \n        except Exception as e:\n            self.log(f"❌ Erreur enregistrement API: {e}")\n    \n    @asyncSlot()\n    async def refresh_challenges(self):\n        """Rafraîchit la liste des challenges"""\n        try:\n            if not self.user_token:\n                self.log("❌ Aucun token disponible")\n                return\n            \n            self.refresh_btn.setEnabled(False)\n            self.refresh_btn.setText("🔄 Loading...")\n            self.status_label.setText("Chargement des challenges...")\n            \n            # Récupérer les challenges depuis l'API\n            async with self.api_client as client:\n                challenges = await client.get_challenges(self.user_token)\n            \n            # Mettre à jour la liste\n            self.update_challenge_list(challenges)\n            \n            self.log(f"✅ {len(challenges)} challenges chargés")\n            self.status_label.setText(f"{len(challenges)} challenges disponibles")\n            \n        except Exception as e:\n            self.log(f"❌ Erreur rafraîchissement: {e}")\n            self.status_label.setText("Erreur lors du chargement")\n        finally:\n            self.refresh_btn.setEnabled(True)\n            self.refresh_btn.setText("🔄 Refresh")\n    \n    def update_challenge_list(self, challenges_data):\n        """Met à jour la liste des challenges dans l'interface"""\n        try:\n            self.challenge_list.clear()\n            self.challenges = {}\n            \n            for challenge_data in challenges_data:\n                # Créer l'objet challenge\n                challenge = ModernChallengeItem(\n                    id=challenge_data.get('id', ''),\n                    title=challenge_data.get('title', 'Untitled'),\n                    end_time=challenge_data.get('end_time', ''),\n                    time_left=challenge_data.get('time_left_days', 0),\n                    url=challenge_data.get('url', ''),\n                    votes=challenge_data.get('votes', 0),\n                    rank=challenge_data.get('rank', 999),\n                    level=challenge_data.get('level', ''),\n                    exposure=challenge_data.get('exposure', ''),\n                    gps=challenge_data.get('gps', '')\n                )\n                \n                challenge.selected_strategy = challenge_data.get('selected_strategy')\n                challenge.turbo_status = challenge_data.get('turbo_status', 'none')\n                \n                self.challenges[challenge.id] = challenge\n                \n                # Créer l'item de liste\n                self.create_challenge_list_item(challenge)\n            \n            self.challenge_updated.emit()\n            \n        except Exception as e:\n            self.log(f"❌ Erreur mise à jour liste: {e}")\n    \n    def create_challenge_list_item(self, challenge):\n        """Crée un item de liste pour un challenge"""\n        try:\n            # Formatage du temps restant\n            time_left = f"{challenge.time_left}j" if challenge.time_left else "Fini"\n            \n            # Statut turbo\n            turbo_emoji = {\n                'none': '⚪',\n                'running': '🟡',\n                'completed': '🟢',\n                'failed': '🔴'\n            }.get(challenge.turbo_status, '⚪')\n            \n            # Stratégie\n            strategy_text = f"📅{challenge.selected_strategy}" if challenge.selected_strategy else "❌"\n            \n            # Texte de l'item\n            item_text = f"{turbo_emoji} {challenge.title[:40]}... | 🗳️{challenge.votes} | 🏆{challenge.rank} | ⏰{time_left} | {strategy_text}"\n            \n            # Créer l'item\n            item = QListWidgetItem(item_text)\n            item.setData(Qt.UserRole, challenge.id)\n            \n            # Couleur selon le statut\n            if challenge.turbo_status == 'running':\n                item.setBackground(QColor(241, 196, 15, 50))  # Jaune transparent\n            elif challenge.turbo_status == 'completed':\n                item.setBackground(QColor(39, 174, 96, 50))   # Vert transparent\n            elif challenge.turbo_status == 'failed':\n                item.setBackground(QColor(231, 76, 60, 50))   # Rouge transparent\n            \n            # Tooltip\n            tooltip = f"""Titre: {challenge.title}\nVotes: {challenge.votes}\nRang: {challenge.rank}\nNiveau: {challenge.level}\nExposure: {challenge.exposure}\nTemps restant: {time_left}\nStratégie: {challenge.selected_strategy or 'Aucune'}\nTurbo: {challenge.turbo_status}"""\n            item.setToolTip(tooltip)\n            \n            self.challenge_list.addItem(item)\n            \n        except Exception as e:\n            self.log(f"❌ Erreur création item: {e}")\n    \n    def get_selected_challenges(self):\n        """Retourne les challenges sélectionnés"""\n        selected = []\n        for i in range(self.challenge_list.count()):\n            item = self.challenge_list.item(i)\n            if item.isSelected():\n                challenge_id = item.data(Qt.UserRole)\n                if challenge_id in self.challenges:\n                    selected.append(self.challenges[challenge_id])\n        return selected\n    \n    def select_all_challenges(self):\n        """Sélectionne tous les challenges"""\n        for i in range(self.challenge_list.count()):\n            self.challenge_list.item(i).setSelected(True)\n        self.log(f"✅ {self.challenge_list.count()} challenges sélectionnés")\n    \n    def select_none_challenges(self):\n        """Désélectionne tous les challenges"""\n        self.challenge_list.clearSelection()\n        self.log("❌ Sélection effacée")\n    \n    @asyncSlot()\n    async def apply_strategy_to_selected(self):\n        """Applique une stratégie aux challenges sélectionnés"""\n        try:\n            selected = self.get_selected_challenges()\n            if not selected:\n                self.log("⚠️ Aucun challenge sélectionné")\n                return\n            \n            strategy_name = self.strategy_combo.currentText()\n            \n            if not strategy_name:\n                self.log("⚠️ Aucune stratégie sélectionnée")\n                return\n            \n            self.strategy_btn.setEnabled(False)\n            self.strategy_btn.setText("📅 Programmation...")\n            \n            success_count = 0\n            \n            async with self.api_client as client:\n                for challenge in selected:\n                    try:\n                        # Nettoyer les stratégies existantes pour ce challenge\n                        cancelled = await client.cancel_challenge_strategies(challenge.id)\n                        if cancelled > 0:\n                            self.log(f"🧹 {cancelled} stratégie(s) annulée(s) pour {challenge.title[:30]}...")\n                        \n                        # Programmer la nouvelle stratégie à la fin du challenge\n                        # Calculer le moment d'exécution (2 minutes avant la fin)\n                        scheduled_time = datetime.now() + timedelta(minutes=2)  # Exemple: dans 2 minutes\n                        \n                        result = await client.schedule_strategy(\n                            challenge_id=challenge.id,\n                            strategy_name=strategy_name,\n                            scheduled_at=scheduled_time,\n                            challenge_title=challenge.title\n                        )\n                        \n                        challenge.selected_strategy = strategy_name\n                        success_count += 1\n                        \n                        self.log(f"📅 Stratégie {strategy_name} programmée: {challenge.title[:30]}...")\n                        \n                    except Exception as e:\n                        self.log(f"❌ Erreur stratégie {challenge.title[:30]}...: {e}")\n            \n            # Rafraîchir l'affichage\n            await self.refresh_challenges()\n            \n            self.log(f"✅ Stratégie {strategy_name} appliquée à {success_count}/{len(selected)} challenges")\n            \n        except Exception as e:\n            self.log(f"❌ Erreur application stratégie: {e}")\n        finally:\n            self.strategy_btn.setEnabled(True)\n            self.strategy_btn.setText("📅 Stratégie")\n    \n    @asyncSlot()\n    async def execute_fill_selected(self):\n        """Exécute un fill sur les challenges sélectionnés"""\n        try:\n            selected = self.get_selected_challenges()\n            if not selected:\n                self.log("⚠️ Aucun challenge sélectionné")\n                return\n            \n            self.fill_btn.setEnabled(False)\n            self.fill_btn.setText("⚡ Execution...")\n            \n            success_count = 0\n            \n            async with self.api_client as client:\n                for challenge in selected:\n                    try:\n                        result = await client.execute_simple_vote(\n                            challenge_url=challenge.url,\n                            vote_count=80,  # Fill = max votes\n                            user_token=self.user_token\n                        )\n                        \n                        if result.get('success', False):\n                            success_count += 1\n                            self.log(f"⚡ Fill réussi: {challenge.title[:30]}...")\n                        else:\n                            self.log(f"❌ Fill échoué: {challenge.title[:30]}... - {result.get('message', 'Erreur inconnue')}")\n                        \n                    except Exception as e:\n                        self.log(f"❌ Erreur fill {challenge.title[:30]}...: {e}")\n            \n            self.log(f"✅ Fill exécuté sur {success_count}/{len(selected)} challenges")\n            \n        except Exception as e:\n            self.log(f"❌ Erreur exécution fill: {e}")\n        finally:\n            self.fill_btn.setEnabled(True)\n            self.fill_btn.setText("⚡ Fill")\n    \n    @asyncSlot()\n    async def execute_turbo_selected(self):\n        """Exécute un turbo sur les challenges sélectionnés"""\n        try:\n            selected = self.get_selected_challenges()\n            if not selected:\n                self.log("⚠️ Aucun challenge sélectionné")\n                return\n            \n            self.turbo_btn.setEnabled(False)\n            self.turbo_btn.setText("🚀 Execution...")\n            self.progress_bar.setVisible(True)\n            self.progress_bar.setMaximum(len(selected))\n            self.progress_bar.setValue(0)\n            \n            success_count = 0\n            \n            async with self.api_client as client:\n                for i, challenge in enumerate(selected):\n                    try:\n                        self.log(f"🚀 Démarrage turbo: {challenge.title[:30]}...")\n                        \n                        result = await client.execute_turbo(\n                            challenge_id=challenge.id,\n                            challenge_title=challenge.title,\n                            challenge_time_left=f"{challenge.time_left}j"\n                        )\n                        \n                        turbo_id = result.get('turbo_id')\n                        if turbo_id:\n                            challenge.turbo_status = 'running'\n                            success_count += 1\n                            self.log(f"🚀 Turbo démarré: {challenge.title[:30]}... (ID: {turbo_id})")\n                        else:\n                            self.log(f"❌ Turbo échoué: {challenge.title[:30]}...")\n                        \n                        self.progress_bar.setValue(i + 1)\n                        \n                        # Petite pause entre les turbos\n                        await asyncio.sleep(1)\n                        \n                    except Exception as e:\n                        self.log(f"❌ Erreur turbo {challenge.title[:30]}...: {e}")\n                        self.progress_bar.setValue(i + 1)\n            \n            # Rafraîchir l'affichage\n            await self.refresh_challenges()\n            \n            self.log(f"✅ Turbo démarré sur {success_count}/{len(selected)} challenges")\n            \n        except Exception as e:\n            self.log(f"❌ Erreur exécution turbo: {e}")\n        finally:\n            self.turbo_btn.setEnabled(True)\n            self.turbo_btn.setText("🚀 Turbo")\n            self.progress_bar.setVisible(False)\n    \n    def log(self, message):\n        """Ajoute un message aux logs"""\n        timestamp = datetime.now().strftime("%H:%M:%S")\n        formatted_message = f"[{timestamp}] {message}"\n        self.log_signal.emit(formatted_message)\n    \n    def append_log(self, message):\n        """Ajoute un message à la zone de logs (thread-safe)"""\n        self.log_text.append(message)\n        # Auto-scroll vers le bas\n        cursor = self.log_text.textCursor()\n        cursor.movePosition(QTextCursor.End)\n        self.log_text.setTextCursor(cursor)\n    \n    def auto_refresh_challenges(self):\n        """Rafraîchissement automatique des challenges"""\n        if hasattr(self, 'user_token') and self.user_token:\n            asyncio.create_task(self.refresh_challenges())\n    \n    def closeEvent(self, event):\n        """Gestionnaire de fermeture de l'application"""\n        try:\n            self.auto_refresh_timer.stop()\n            self.log("👋 Fermeture de l'application")\n            event.accept()\n        except Exception as e:\n            print(f"Error during close: {e}")\n            event.accept()\n\n\ndef main():\n    """Point d'entrée principal"""\n    app = QApplication(sys.argv)\n    \n    # Create and set QEventLoop\n    loop = QEventLoop(app)\n    asyncio.set_event_loop(loop)\n    \n    # Create main window\n    window = ModernGSGUI()\n    window.show()\n    \n    # Run the application\n    with loop:\n        try:\n            loop.run_forever()\n        except KeyboardInterrupt:\n            print("\\n👋 Application interrompue par l'utilisateur")\n        finally:\n            loop.close()\n\n\nif __name__ == "__main__":\n    main()