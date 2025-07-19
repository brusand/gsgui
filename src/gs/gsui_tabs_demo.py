#!/usr/bin/env python3
"""
Demo du système multi-profil GuruShots GUI
Version simplifiée sans dépendances externes
"""

import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QLabel, QPushButton, QTextEdit, QApplication, 
                               QTableWidget, QTableWidgetItem, QTabWidget,
                               QInputDialog, QMessageBox, QHeaderView, QCheckBox)
from PySide6.QtCore import Qt, QTimer, Signal

class MockChallenge:
    """Challenge simulé pour la démo"""
    def __init__(self, id, title, end_time, time_left, votes, rank):
        self.id = id
        self.title = title
        self.end_time = end_time
        self.time_left = time_left
        self.votes = votes
        self.rank = rank
        self.selected_strategy = None

class MockConfig:
    """Configuration simulée"""
    def __init__(self):
        self.data = {
            'players': {
                'bruno': {
                    'xtoken': 'a1cad95a6d480c14f51dd0eba4914c8337b893c789ec6278bb440c7c9a673b162f042470c62684e6da2bd342ffea7777',
                    'user_name': 'ow.lala',
                    'scheduled_strategies': {}
                },
                'player2': {
                    'xtoken': 'b2cbd95a6d480c14f51dd0eba4914c8337b893c789ec6278bb440c7c9a673b162f042470c62684e6da2bd342ffea7777',
                    'user_name': 'demo.user',
                    'scheduled_strategies': {}
                }
            }
        }
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def write(self):
        pass

class ProfileTab(QWidget):
    """Widget d'onglet pour un profil spécifique - Version Demo"""
    
    log_message = Signal(str, str)  # (profile, message)
    
    def __init__(self, profile_name, config):
        super().__init__()
        self.player = profile_name
        self.config = config
        self.challenges = []
        self.selected_challenges = set()
        
        # Générer des challenges de démo
        self.generate_demo_challenges()
        
        # Créer l'UI
        self.init_ui()
        
        # Timer pour simulation
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.update_demo)
        self.demo_timer.start(5000)  # Update toutes les 5 secondes
    
    def generate_demo_challenges(self):
        """Génère des challenges de démo"""
        base_challenges = [
            ("Winter Landscapes", "2D 4H 15M 30S", 145, 23),
            ("Street Photography", "1D 12H 45M 20S", 89, 67),
            ("Portrait Masters", "3D 8H 22M 15S", 234, 12),
            ("Urban Lights", "0D 6H 33M 45S", 67, 45),
            ("Nature's Beauty", "4D 2H 18M 10S", 178, 34)
        ]
        
        self.challenges = []
        for i, (title, time_left, votes, rank) in enumerate(base_challenges):
            challenge = MockChallenge(
                id=f"{self.player}_{i+1}",
                title=f"[{self.player}] {title}",
                end_time=datetime.now().strftime("%d/%m/%Y, %H:%M"),
                time_left=time_left,
                votes=votes,
                rank=rank
            )
            self.challenges.append(challenge)
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info du profil
        profile_info = QLabel(f"Profil: {self.player}")
        profile_info.setStyleSheet("font-weight: bold; color: blue; padding: 5px;")
        layout.addWidget(profile_info)
        
        # Barre d'outils
        self.create_toolbar(layout)
        
        # Tableau des challenges
        self.create_challenges_table(layout)
        
        # Panel de résultats
        self.create_results_panel(layout)
        
        # Populer le tableau
        self.populate_table()
    
    def create_toolbar(self, parent_layout):
        """Crée la barre d'outils"""
        toolbar = QHBoxLayout()
        
        # Boutons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_challenges)
        toolbar.addWidget(refresh_btn)
        
        all_btn = QPushButton("All")
        all_btn.clicked.connect(self.select_all)
        toolbar.addWidget(all_btn)
        
        none_btn = QPushButton("None")
        none_btn.clicked.connect(self.select_none)
        toolbar.addWidget(none_btn)
        
        strategy_btn = QPushButton("Apply Strategy")
        strategy_btn.clicked.connect(self.apply_strategy)
        toolbar.addWidget(strategy_btn)
        
        test_btn = QPushButton("Test Multi-Profile")
        test_btn.clicked.connect(self.test_multiprofile)
        toolbar.addWidget(test_btn)
        
        toolbar.addStretch()
        
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        parent_layout.addWidget(toolbar_widget)
    
    def create_challenges_table(self, parent_layout):
        """Crée le tableau des challenges"""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Select", "Title", "Time Left", "Votes", "Rank", "Strategy"])
        
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        parent_layout.addWidget(self.table)
    
    def create_results_panel(self, parent_layout):
        """Crée le panel de résultats"""
        self.result_panel = QTextEdit()
        self.result_panel.setMaximumHeight(150)
        self.result_panel.setReadOnly(True)
        parent_layout.addWidget(self.result_panel)
    
    def populate_table(self):
        """Remplit le tableau"""
        self.table.setRowCount(len(self.challenges))
        
        for row, challenge in enumerate(self.challenges):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(challenge.id in self.selected_challenges)
            checkbox.stateChanged.connect(lambda state, cid=challenge.id: self.toggle_selection(cid))
            self.table.setCellWidget(row, 0, checkbox)
            
            # Données
            self.table.setItem(row, 1, QTableWidgetItem(challenge.title))
            self.table.setItem(row, 2, QTableWidgetItem(challenge.time_left))
            self.table.setItem(row, 3, QTableWidgetItem(str(challenge.votes)))
            self.table.setItem(row, 4, QTableWidgetItem(str(challenge.rank)))
            self.table.setItem(row, 5, QTableWidgetItem(challenge.selected_strategy or ""))
    
    def toggle_selection(self, challenge_id):
        """Toggle la sélection d'un challenge"""
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)
        self.log(f"Challenge {challenge_id} {'sélectionné' if challenge_id in self.selected_challenges else 'désélectionné'}")
    
    def select_all(self):
        """Sélectionne tous les challenges"""
        self.selected_challenges = set(c.id for c in self.challenges)
        self.populate_table()
        self.log("✅ Tous les challenges sélectionnés")
    
    def select_none(self):
        """Désélectionne tous les challenges"""
        self.selected_challenges.clear()
        self.populate_table()
        self.log("❌ Tous les challenges désélectionnés")
    
    def refresh_challenges(self):
        """Simule un refresh des challenges"""
        self.log("🔄 Refresh des challenges...")
        # Modifier légèrement les données pour simuler un refresh
        import random
        for challenge in self.challenges:
            challenge.votes += random.randint(-5, 10)
            challenge.rank += random.randint(-3, 3)
            challenge.rank = max(1, challenge.rank)
        self.populate_table()
        self.log(f"📥 {len(self.challenges)} challenges mis à jour")
    
    def apply_strategy(self):
        """Applique une stratégie aux challenges sélectionnés"""
        if not self.selected_challenges:
            self.log("❌ Aucun challenge sélectionné")
            return
        
        strategies = ["conservative", "aggressive", "last_minute", "precision_strike"]
        strategy, ok = QInputDialog.getItem(self, "Stratégie", "Choisir une stratégie:", strategies, 0, False)
        
        if ok and strategy:
            for challenge in self.challenges:
                if challenge.id in self.selected_challenges:
                    challenge.selected_strategy = strategy
                    self.log(f"📅 Stratégie '{strategy}' appliquée à {challenge.title}")
            self.populate_table()
    
    def test_multiprofile(self):
        """Test du système multi-profil"""
        self.log(f"🧪 Test multi-profil pour {self.player}")
        self.log(f"   - Challenges: {len(self.challenges)}")
        self.log(f"   - Sélectionnés: {len(self.selected_challenges)}")
        self.log(f"   - Token: {self.config['players'][self.player]['xtoken'][:20]}...")
    
    def update_demo(self):
        """Met à jour la démo périodiquement"""
        # Décrémenter le temps restant
        import random
        for challenge in self.challenges:
            if "0D 0H 0M" not in challenge.time_left:
                # Simuler la décrémentation du temps
                if random.random() < 0.3:  # 30% de chance de décrémenter
                    parts = challenge.time_left.split()
                    if len(parts) >= 4:
                        seconds = int(parts[3][:-1])  # Retirer le 'S'
                        if seconds > 0:
                            seconds -= random.randint(1, 5)
                            challenge.time_left = f"{parts[0]} {parts[1]} {parts[2]} {seconds}S"
        
        self.populate_table()
    
    def log(self, message):
        """Log un message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.result_panel.append(formatted_message)
        self.log_message.emit(self.player, formatted_message)

class MultiProfileDemo(QMainWindow):
    """Démo du système multi-profil"""
    
    def __init__(self):
        super().__init__()
        self.config = MockConfig()
        self.profile_tabs = {}
        
        self.init_ui()
        self.load_profiles()
    
    def init_ui(self):
        """Initialise l'interface"""
        self.setWindowTitle("GuruShots GUI - Multi-Profile Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Barre d'outils globale
        self.create_global_toolbar(layout)
        
        # Onglets
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tab_widget)
        
        # Logs globaux
        self.create_global_logs(layout)
    
    def create_global_toolbar(self, parent_layout):
        """Crée la barre d'outils globale"""
        toolbar = QHBoxLayout()
        
        title = QLabel("GuruShots Multi-Profile Demo")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        toolbar.addWidget(title)
        
        new_profile_btn = QPushButton("+ Nouveau Profil")
        new_profile_btn.clicked.connect(self.create_new_profile)
        toolbar.addWidget(new_profile_btn)
        
        test_btn = QPushButton("Test Multi-Profile")
        test_btn.clicked.connect(self.test_all_profiles)
        toolbar.addWidget(test_btn)
        
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
        self.global_logs.setMaximumHeight(120)
        self.global_logs.setReadOnly(True)
        self.global_logs.setStyleSheet("background-color: #f8f9fa;")
        parent_layout.addWidget(self.global_logs)
    
    def load_profiles(self):
        """Charge les profils existants"""
        for profile_name in self.config['players'].keys():
            self.add_profile_tab(profile_name)
    
    def add_profile_tab(self, profile_name):
        """Ajoute un onglet de profil"""
        if profile_name not in self.profile_tabs:
            profile_tab = ProfileTab(profile_name, self.config)
            profile_tab.log_message.connect(self.on_profile_log)
            
            self.profile_tabs[profile_name] = profile_tab
            self.tab_widget.addTab(profile_tab, profile_name)
            
            self.log_global(f"✅ Profil '{profile_name}' chargé")
    
    def close_tab(self, index):
        """Ferme un onglet"""
        if index >= 0 and index < self.tab_widget.count():
            # Trouver le profil correspondant
            tab_widget = self.tab_widget.widget(index)
            profile_name = None
            
            for name, widget in self.profile_tabs.items():
                if widget == tab_widget:
                    profile_name = name
                    break
            
            if profile_name:
                reply = QMessageBox.question(
                    self, "Fermer l'onglet", 
                    f"Voulez-vous fermer l'onglet '{profile_name}' ?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.tab_widget.removeTab(index)
                    del self.profile_tabs[profile_name]
                    self.log_global(f"🗑️ Onglet '{profile_name}' fermé")
    
    def create_new_profile(self):
        """Crée un nouveau profil"""
        profile_name, ok = QInputDialog.getText(
            self, "Nouveau Profil", "Nom du profil:"
        )
        
        if ok and profile_name and profile_name not in self.profile_tabs:
            # Ajouter à la config
            self.config['players'][profile_name] = {
                'xtoken': f'demo_token_{profile_name}',
                'user_name': f'demo.{profile_name}',
                'scheduled_strategies': {}
            }
            
            self.add_profile_tab(profile_name)
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
            self.log_global(f"🆕 Nouveau profil '{profile_name}' créé")
    
    def test_all_profiles(self):
        """Test tous les profils"""
        self.log_global("🧪 Test Multi-Profil Global:")
        for profile_name, tab in self.profile_tabs.items():
            self.log_global(f"   📊 {profile_name}: {len(tab.challenges)} challenges, {len(tab.selected_challenges)} sélectionnés")
    
    def on_profile_log(self, profile_name, message):
        """Reçoit les logs d'un profil"""
        self.log_global(f"[{profile_name}] {message}")
    
    def log_global(self, message):
        """Affiche un message dans les logs globaux"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.global_logs.append(f"[{timestamp}] {message}")

def main():
    app = QApplication(sys.argv)
    
    # Créer et afficher la fenêtre
    window = MultiProfileDemo()
    window.show()
    
    # Démarrer l'application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()