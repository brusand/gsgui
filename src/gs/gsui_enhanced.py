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
                               QApplication, QProgressBar, QHeaderView, QInputDialog,
                               QDialog, QDialogButtonBox, QGridLayout, QGroupBox,
                               QMessageBox, QLineEdit)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QMetaObject, Q_ARG
from PySide6.QtGui import QColor, QTextCursor, QFont

try:
    import browser_cookie3
    COOKIE_SUPPORT = True
except ImportError:
    COOKIE_SUPPORT = False
    print("⚠️ browser_cookie3 not available - manual token required")


def get_gurushots_token_from_cookies():
    """Récupère le token GuruShots depuis les cookies du navigateur"""
    if not COOKIE_SUPPORT:
        return None
    
    try:
        # Essayer Chrome en premier
        try:
            cookies = browser_cookie3.chrome(domain_name='gurushots.com')
            for cookie in cookies:
                if cookie.name == 'gs_t':
                    print(f"✅ Token trouvé dans Chrome: {cookie.value[:20]}...")
                    return cookie.value
        except Exception as e:
            print(f"⚠️ Chrome cookies non accessibles: {e}")
        
        # Essayer Firefox
        try:
            cookies = browser_cookie3.firefox(domain_name='gurushots.com')
            for cookie in cookies:
                if cookie.name == 'gs_t':
                    print(f"✅ Token trouvé dans Firefox: {cookie.value[:20]}...")
                    return cookie.value
        except Exception as e:
            print(f"⚠️ Firefox cookies non accessibles: {e}")
        
        # Essayer Safari (macOS)
        try:
            cookies = browser_cookie3.safari(domain_name='gurushots.com')
            for cookie in cookies:
                if cookie.name == 'gs_t':
                    print(f"✅ Token trouvé dans Safari: {cookie.value[:20]}...")
                    return cookie.value
        except Exception as e:
            print(f"⚠️ Safari cookies non accessibles: {e}")
            
        print("❌ Token gs_t non trouvé dans les navigateurs")
        return None
        
    except Exception as e:
        print(f"❌ Erreur récupération cookies: {e}")
        return None


class ProfileSelectionDialog(QDialog):
    """Dialog pour sélectionner le profil utilisateur au démarrage"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔑 Sélection du Profil GSGUI")
        self.setFixedSize(400, 300)
        self.selected_profile = None
        
        self.setup_ui()
        self.load_profiles_from_ini()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre
        title_label = QLabel("Sélectionnez votre profil GSGUI")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        
        # Liste des profils disponibles
        self.profile_combo = QComboBox()
        self.profile_combo.setStyleSheet("font-size: 14px; padding: 5px;")
        
        # Bouton pour nouveau profil
        new_profile_btn = QPushButton("➕ Nouveau Profil")
        new_profile_btn.clicked.connect(self.create_new_profile)
        
        # Boutons OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(title_label)
        layout.addWidget(QLabel("Profils disponibles:"))
        layout.addWidget(self.profile_combo)
        layout.addWidget(new_profile_btn)
        layout.addStretch()
        layout.addWidget(buttons)
    
    def load_profiles_from_ini(self):
        """Charge les profils depuis le backend et crée automatiquement si aucun"""
        try:
            # Appeler le backend pour récupérer la liste des profils disponibles
            try:
                response = requests.get("http://localhost:8001/api/v1/profiles", timeout=5)
                if response.status_code == 200:
                    profiles_data = response.json()
                    profiles = profiles_data.get('profiles', [])
                    
                    for profile in profiles:
                        profile_name = profile.get('name', '')
                        has_token = profile.get('has_token', False)
                        display_name = f"{profile_name} {'✅' if has_token else '❌'}"
                        self.profile_combo.addItem(display_name, profile_name)
                    
                    if len(profiles) > 0:
                        return  # Profils chargés avec succès
                else:
                    print(f"⚠️ Erreur backend profils: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Backend non disponible: {e}")
            
            # Fallback: profils par défaut si backend non disponible
            known_profiles = ["bruno"]  # Profils connus
            for profile in known_profiles:
                self.profile_combo.addItem(profile)
            
            if self.profile_combo.count() == 0:
                # Aucun profil trouvé, essayer la création automatique
                gs_token = get_gurushots_token_from_cookies()
                if gs_token:
                    # Proposer la création automatique
                    msg = QMessageBox()
                    msg.setWindowTitle("Création Automatique de Profil")
                    msg.setText("Aucun profil trouvé, mais token GuruShots détecté!")
                    msg.setInformativeText(f"Token: {gs_token[:20]}...\n\nVoulez-vous créer automatiquement un profil 'auto' ?")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    
                    if msg.exec() == QMessageBox.Yes:
                        try:
                            self.save_profile_to_ini("auto", gs_token)
                            self.profile_combo.addItem("auto")
                            print("✅ Profil 'auto' créé automatiquement")
                        except Exception as e:
                            print(f"❌ Erreur création profil auto: {e}")
                            self.profile_combo.addItem("Aucun profil trouvé")
                    else:
                        self.profile_combo.addItem("Aucun profil trouvé")
                else:
                    self.profile_combo.addItem("Aucun profil trouvé")
                    
        except Exception as e:
            print(f"❌ Erreur chargement profils: {e}")
            self.profile_combo.addItem("Erreur chargement profils")
    
    def create_new_profile(self):
        """Crée un nouveau profil avec récupération automatique de gs_token"""
        profile_name, ok = QInputDialog.getText(self, "Nouveau Profil", "Nom du profil:")
        if ok and profile_name:
            try:
                # Essayer d'abord la récupération automatique depuis les cookies
                gs_token = get_gurushots_token_from_cookies()
                
                if gs_token:
                    # Token trouvé automatiquement
                    msg = QMessageBox()
                    msg.setWindowTitle("Token Trouvé")
                    msg.setText(f"Token GuruShots trouvé automatiquement dans votre navigateur!")
                    msg.setInformativeText(f"Token: {gs_token[:20]}...\n\nVoulez-vous l'utiliser pour le profil '{profile_name}' ?")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    
                    if msg.exec() == QMessageBox.Yes:
                        # Utiliser le token trouvé
                        self.save_profile_to_ini(profile_name, gs_token)
                        self.profile_combo.addItem(profile_name)
                        self.profile_combo.setCurrentText(profile_name)
                        QMessageBox.information(self, "Succès", f"Profil '{profile_name}' créé avec succès!")
                        return
                
                # Fallback: récupération manuelle si automatique échoue
                msg = QMessageBox()
                msg.setWindowTitle("Configuration Manuelle")
                if gs_token:
                    msg.setText("Récupération manuelle du token")
                    msg.setInformativeText("Token automatique refusé ou récupération manuelle demandée.")
                else:
                    msg.setText(f"Impossible de récupérer automatiquement le token pour '{profile_name}'")
                    msg.setInformativeText("Veuillez le récupérer manuellement:\n\n"
                                         "1. Connectez-vous sur gurushots.com\n"
                                         "2. F12 → Application → Cookies → gurushots.com\n"
                                         "3. Copiez la valeur du cookie 'gs_t'")
                
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                
                if msg.exec() == QMessageBox.Ok:
                    gs_token_manual, token_ok = QInputDialog.getText(self, "Token Manuel", 
                                                                   "Collez votre gs_t token ici:")
                    if token_ok and gs_token_manual:
                        self.save_profile_to_ini(profile_name, gs_token_manual)
                        self.profile_combo.addItem(profile_name)
                        self.profile_combo.setCurrentText(profile_name)
                        QMessageBox.information(self, "Succès", f"Profil '{profile_name}' créé avec succès!")
                    else:
                        QMessageBox.warning(self, "Annulé", "Création de profil annulée - token manquant")
                        
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la création du profil: {e}")
    
    def save_profile_to_ini(self, profile_name, gs_token):
        """Enregistre le profil via le backend"""
        try:
            # Enregistrer le profil directement via l'API backend
            import requests
            data = {
                "profile_name": profile_name,
                "gs_token": gs_token
            }
            response = requests.post("http://localhost:8001/api/v1/profiles/register", 
                                   json=data, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Profil '{profile_name}' enregistré via backend")
            else:
                raise Exception(f"Backend registration failed: {response.status_code}")
            
        except Exception as e:
            print(f"❌ Erreur enregistrement profil: {e}")
            raise
    
    def get_selected_profile(self):
        """Retourne le profil sélectionné"""
        if self.profile_combo.currentText() and self.profile_combo.currentText() != "Aucun profil trouvé":
            # Si on a des données utilisateur (userData), utiliser ça, sinon parser le texte
            current_data = self.profile_combo.currentData()
            if current_data:
                return current_data  # Retourne le nom du profil sans emoji
            else:
                # Fallback: parser le texte pour enlever les emojis
                text = self.profile_combo.currentText()
                return text.replace(" ✅", "").replace(" ❌", "").strip()
        return None


class TurboAlgorithmDialog(QDialog):
    """Dialog pour sélection des algorithmes turbo comme GSGUI original"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Sélection Algorithme Turbo")
        self.setFixedSize(500, 400)
        
        # Algorithmes disponibles avec leurs statistiques
        self.algorithms = {
            'hybrid': {'name': 'Hybrid (67.2%)', 'desc': 'Logique équilibrée', 'checked': True},
            'position_aware': {'name': 'Position Aware (58.5%/67%*)', 'desc': 'Patterns par position', 'checked': True},
            'adaptive_time': {'name': 'Adaptive Time (59.0%/67%*)', 'desc': 'Stratégie temporelle', 'checked': True},
            'ratio_low': {'name': 'Ratio Low (66.5%)', 'desc': 'Privilégie ratios stables', 'checked': False},
            'votes_high': {'name': 'Votes High (68.6%)', 'desc': 'Priorité votes élevés', 'checked': False},
            'bruno_custom': {'name': 'Bruno Custom (63.9%)', 'desc': 'Champion historique', 'checked': False},
            'votes_ratio': {'name': 'Votes Ratio (64.6%)', 'desc': 'Balance votes/ratio', 'checked': False},
            'random': {'name': 'Random (57.0%)', 'desc': 'Baseline aléatoire', 'checked': False}
        }
        
        self.checkboxes = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre et description
        title_label = QLabel("Sélection des algorithmes Turbo")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("Sélectionnez un ou plusieurs algorithmes pour le vote ensemble (majorité gagne)")
        desc_label.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc_label)
        
        # Groupe algorithmes
        group_box = QGroupBox("Algorithmes disponibles")
        group_layout = QGridLayout(group_box)
        
        row = 0
        for algo_key, algo_info in self.algorithms.items():
            checkbox = QCheckBox(algo_info['name'])
            checkbox.setChecked(algo_info['checked'])
            checkbox.setToolTip(algo_info['desc'])
            
            desc_label = QLabel(algo_info['desc'])
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            
            group_layout.addWidget(checkbox, row, 0)
            group_layout.addWidget(desc_label, row, 1)
            
            self.checkboxes[algo_key] = checkbox
            row += 1
        
        layout.addWidget(group_box)
        
        # Boutons reset et optimal
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("🔄 Reset Optimal")
        reset_btn.setToolTip("Réinitialiser à l'ensemble optimal par défaut")
        reset_btn.clicked.connect(self.reset_to_optimal)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Boutons OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def reset_to_optimal(self):
        """Réinitialise à l'ensemble optimal par défaut"""
        optimal_algos = ['hybrid', 'position_aware', 'adaptive_time']
        
        for algo_key, checkbox in self.checkboxes.items():
            checkbox.setChecked(algo_key in optimal_algos)
    
    def get_selected_algorithms(self):
        """Retourne la liste des algorithmes sélectionnés"""
        selected = []
        for algo_key, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(algo_key)
        return selected


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
    """Client API enhanced avec système de profils"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001/api/v1"
        self.profile_name = None
        
    def set_profile(self, profile_name):
        """Définit le profil actuel"""
        self.profile_name = profile_name
    
    def register_profile(self, profile_name, gs_token=None):
        """Enregistre un profil auprès du backend"""
        try:
            data = {
                "profile_name": profile_name,
                "gs_token": gs_token
            }
            response = requests.post(f"{self.base_url}/profiles/register", json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result
            return None
        except Exception as e:
            print(f"❌ Erreur register profile: {e}")
            return None
        
    def get_challenges(self):
        """Récupère les vrais challenges pour le profil actuel"""
        try:
            if not self.profile_name:
                raise Exception("Aucun profil sélectionné")
                
            params = {'profile_name': self.profile_name}
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
    
    def execute_turbo(self, challenge_id, challenge_title=None, algorithm=None):
        """Exécute un turbo avec algorithme sélectionné - utilise le profil"""
        try:
            if not self.profile_name:
                raise Exception("Aucun profil sélectionné")
                
            data = {
                "challenge_id": challenge_id,
                "challenge_title": challenge_title,
                "challenge_time_left": "1j",
                "algorithm": algorithm or "hybrid"
            }
            
            params = {'profile_name': self.profile_name}
            response = requests.post(f"{self.base_url}/challenges/turbo", 
                                   json=data, params=params, timeout=60)  # Plus de temps pour turbo
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except Exception as e:
            print(f"❌ Erreur turbo: {e}")
            return False
    
    def execute_simple_vote(self, challenge_url, vote_count):
        """Exécute un vote simple avec le profil actuel"""
        try:
            if not self.profile_name:
                raise Exception("Aucun profil sélectionné")
                
            data = {
                "challenge_url": challenge_url,
                "vote_count": vote_count
            }
            
            params = {'profile_name': self.profile_name}
            response = requests.post(f"{self.base_url}/challenges/simple-vote", 
                                   json=data, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except Exception as e:
            print(f"❌ Erreur vote simple: {e}")
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
    editor_signal = Signal(str)  # Signal pour ouvrir l'éditeur
    
    def __init__(self):
        super().__init__()
        
        # Plus besoin de ConfigObj - le backend gère les profils
        self.api_client = EnhancedApiClient()
        self.challenges = {}
        self.selected_challenges = set()
        self.profile_name = None
        
        # Auto-refresh (par défaut désactivé)
        self.auto_refresh_enabled = False
        
        # Charger les stratégies
        self.strategies = self.load_strategies()
        
        self.init_ui()
        
        # Sélection du profil au démarrage
        if not self.select_profile_at_startup():
            QApplication.quit()
            return
        
        self.load_config()
        
        # Connecter signaux
        self.log_signal.connect(self.append_log)
        self.editor_signal.connect(self.show_strategy_editor)
        
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
        self.websocket_thread = None
        self.websocket_should_stop = False
        self.connect_websocket()
        
        print(f"✅ Enhanced GSGUI initialized with profile: {self.profile_name}")
        
        # Charger automatiquement les challenges au démarrage
        QTimer.singleShot(500, self.auto_load_challenges)  # Attendre 500ms que l'UI soit prête
    
    def auto_load_challenges(self):
        """Charge automatiquement les challenges au démarrage"""
        if self.profile_name:
            self.log("🔄 Chargement automatique des challenges...")
            self.refresh_challenges()
        else:
            self.log("⚠️ Aucun profil sélectionné")
    
    def select_profile_at_startup(self):
        """Sélectionne le profil au démarrage de l'application"""
        try:
            dialog = ProfileSelectionDialog(self)
            if dialog.exec() == QDialog.Accepted:
                selected_profile = dialog.get_selected_profile()
                if selected_profile:
                    self.profile_name = selected_profile
                    self.api_client.set_profile(selected_profile)
                    
                    # Enregistrer le profil auprès du backend
                    result = self.api_client.register_profile(selected_profile)
                    if result:
                        print(f"✅ Profil '{selected_profile}' enregistré avec succès")
                        return True
                    else:
                        QMessageBox.warning(self, "Erreur Profil", 
                                          f"Impossible d'enregistrer le profil '{selected_profile}'")
                        return False
                else:
                    QMessageBox.warning(self, "Aucun Profil", "Aucun profil sélectionné. L'application va se fermer.")
                    return False
            else:
                return False
        except Exception as e:
            print(f"❌ Erreur sélection profil: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sélection du profil: {e}")
            return False
    
    def load_strategies(self):
        """Charge les stratégies par défaut (le backend gère les vrais fichiers de config)"""
        try:
            # Liste des stratégies standard - le backend gère les détails
            strategy_names = ["fill", "4m", "3m", "2m", "Bruno", "alain", "caloune", "fill70", "fill20"]
            print(f"📋 Stratégies par défaut: {strategy_names}")
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
        
        # Bouton déconnexion
        self.logout_btn = QPushButton("🚪 Déconnexion")
        self.logout_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        self.logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(self.logout_btn)
        
        main_layout.addLayout(header_layout)
        
        # Actions principales: refresh, all, none, fill, turbo, stratégie, stratégies en cours
        actions_layout = QHBoxLayout()
        
        # 1. Refresh
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("QPushButton { background-color: #3498db; }")
        self.refresh_btn.clicked.connect(self.refresh_challenges)
        actions_layout.addWidget(self.refresh_btn)
        
        # 2. All
        self.all_btn = QPushButton("✅ All")
        self.all_btn.setStyleSheet("QPushButton { background-color: #f39c12; }")
        self.all_btn.clicked.connect(self.select_all)
        actions_layout.addWidget(self.all_btn)
        
        # 3. None
        self.none_btn = QPushButton("❌ None")
        self.none_btn.setStyleSheet("QPushButton { background-color: #e67e22; }")
        self.none_btn.clicked.connect(self.select_none)
        actions_layout.addWidget(self.none_btn)
        
        # 4. Fill
        self.fill_btn = QPushButton("⚡ Fill")
        self.fill_btn.setStyleSheet("QPushButton { background-color: #16a085; }")
        self.fill_btn.clicked.connect(self.execute_fill)
        actions_layout.addWidget(self.fill_btn)
        
        # 6. Turbo
        self.turbo_btn = QPushButton("🚀 Turbo")
        self.turbo_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        self.turbo_btn.clicked.connect(self.execute_turbo)
        actions_layout.addWidget(self.turbo_btn)
        
        # 7. Stratégie
        self.strategy_btn = QPushButton("📅 Stratégie")
        self.strategy_btn.setStyleSheet("QPushButton { background-color: #9b59b6; }")
        self.strategy_btn.clicked.connect(self.apply_strategy)
        actions_layout.addWidget(self.strategy_btn)
        
        # 8. Stratégies en cours
        self.strategies_btn = QPushButton("📋 Stratégies en cours")
        self.strategies_btn.setStyleSheet("QPushButton { background-color: #8e44ad; }")
        self.strategies_btn.clicked.connect(self.show_active_strategies)
        actions_layout.addWidget(self.strategies_btn)
        
        # 9. Edition stratégie
        self.edit_strategies_btn = QPushButton("✏️ Edition")
        self.edit_strategies_btn.setStyleSheet("QPushButton { background-color: #34495e; }")
        self.edit_strategies_btn.clicked.connect(self.edit_strategies)
        actions_layout.addWidget(self.edit_strategies_btn)
        
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
        """Charge la configuration - Utilise maintenant le système de profils"""
        try:
            if self.profile_name:
                self.profile_label.setText(f"Profil: {self.profile_name}")
                self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #27ae60;")
                self.log(f"✅ Profil sélectionné: {self.profile_name}")
                self.log("🔄 Cliquez sur 'Refresh' pour charger vos challenges")
                
                # Charger l'état auto-refresh
                self.load_auto_refresh_state()
            else:
                self.profile_label.setText("Profil: Non sélectionné")
                self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e74c3c;")
                self.log("❌ Aucun profil sélectionné")
        except Exception as e:
            self.log(f"❌ Erreur config: {e}")
    
    def load_auto_refresh_state(self):
        """Initialise l'état de l'auto-refresh (par défaut OFF)"""
        try:
            # Auto-refresh désactivé par défaut - peut être activé manuellement
            self.log("📖 Auto-refresh: OFF (par défaut)")
        except Exception as e:
            self.log(f"⚠️ Erreur initialisation auto-refresh: {e}")
    
    def save_auto_refresh_state(self):
        """Sauvegarde l'état de l'auto-refresh (en mémoire seulement)"""
        try:
            # État conservé en mémoire pour la session actuelle
            status = "ON" if self.auto_refresh_enabled else "OFF"
            self.log(f"💾 Auto-refresh state: {status}")
        except Exception as e:
            self.log(f"⚠️ Erreur sauvegarde auto-refresh: {e}")
    
    def refresh_challenges(self):
        """Rafraîchit les challenges"""
        if not self.profile_name:
            self.log("❌ Aucun profil sélectionné")
            return
        
        # Éviter les refresh multiples simultanés
        if hasattr(self, 'api_thread') and self.api_thread and self.api_thread.isRunning():
            self.log("⏳ Refresh déjà en cours...")
            return
        
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Chargement...")
        
        # Lancer l'appel API dans un thread (plus besoin de user_token)
        self.api_thread = ApiThread(self.api_client.get_challenges)
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
        if self.profile_name and hasattr(self, 'refresh_btn') and self.refresh_btn.isEnabled():
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
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start(60000)  # 1 minute
            self.log("✅ Auto-refresh activé (1 min)")
        else:
            # Désactiver auto-refresh
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
    
    def logout(self):
        """Déconnexion propre et retour à l'écran de sélection des profils"""
        try:
            self.log("🚪 Déconnexion en cours...")
            
            # Fermer la connexion WebSocket proprement
            self.disconnect_websocket()
            self.log("🔌 WebSocket déconnecté")
            
            # Masquer la fenêtre principale
            self.hide()
            
            # Afficher la boîte de dialogue de sélection des profils
            dialog = ProfileSelectionDialog(self)
            result = dialog.exec()
            
            if result == QDialog.Accepted and dialog.selected_profile:
                # Nouveau profil sélectionné
                new_profile = dialog.selected_profile
                self.profile_name = new_profile
                self.profile_label.setText(f"Profil: {new_profile}")
                self.profile_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #27ae60;")
                
                # Réinitialiser l'API client avec le nouveau profil
                self.api_client = ApiClient(base_url=f"http://localhost:8001/api/v1", profile_name=new_profile)
                
                # Reconnecter le WebSocket avec le nouveau profil
                self.connect_websocket()
                
                # Réafficher la fenêtre et rafraîchir
                self.show()
                self.log(f"👤 Reconnecté avec le profil: {new_profile}")
                
                # Petit délai pour s'assurer que la connexion est établie
                QTimer.singleShot(1000, self.refresh_challenges)
            else:
                # Annulation - fermer l'application
                self.log("❌ Déconnexion annulée - Fermeture de l'application")
                QApplication.quit()
                
        except Exception as e:
            self.log(f"❌ Erreur lors de la déconnexion: {e}")
            # En cas d'erreur, forcer l'arrêt propre
            self.disconnect_websocket()
            QApplication.quit()
        
    
    
    def edit_strategies(self):
        """Ouvre l'éditeur de stratégies"""
        def editor_worker():
            try:
                # Récupérer le contenu du fichier strategies.ini
                response = requests.get(f"{self.api_client.base_url}/strategies/config", timeout=10)
                if response.status_code != 200:
                    self.log(f"❌ Erreur récupération strategies.ini: {response.status_code}")
                    return
                
                data = response.json()
                content = data['content']
                
                # Ouvrir l'éditeur via signal Qt (thread-safe)
                self.editor_signal.emit(content)
                
            except Exception as e:
                self.log(f"❌ Erreur ouverture éditeur: {e}")
        
        # Exécuter dans un thread séparé
        thread = threading.Thread(target=editor_worker, daemon=True)
        thread.start()
    
    def show_strategy_editor(self, content):
        """Affiche l'éditeur de stratégies"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QLabel
            from PySide6.QtGui import QFont
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Éditeur de stratégies - strategies.ini")
            dialog.setModal(True)
            dialog.resize(800, 600)
        
            layout = QVBoxLayout()
            
            # Label d'information
            info_label = QLabel("Éditez le fichier strategies.ini. Un backup sera créé automatiquement.")
            info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            layout.addWidget(info_label)
            
            # Éditeur de texte
            editor = QTextEdit()
            editor.setPlainText(content)
            editor.setFont(QFont("Consolas", 10))
            layout.addWidget(editor)
        
            # Boutons
            buttons_layout = QHBoxLayout()
            
            save_btn = QPushButton("💾 Sauvegarder")
            save_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
            save_btn.clicked.connect(lambda: self.save_strategies(editor.toPlainText(), dialog))
            buttons_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("❌ Annuler")
            cancel_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
            cancel_btn.clicked.connect(dialog.reject)
            buttons_layout.addWidget(cancel_btn)
            
            buttons_layout.addStretch()
            layout.addLayout(buttons_layout)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            self.log(f"❌ Erreur dans show_strategy_editor: {e}")
    
    def save_strategies(self, content, dialog):
        """Sauvegarde le fichier strategies.ini"""
        def save_worker():
            try:
                # Envoyer le contenu au backend
                response = requests.post(
                    f"{self.api_client.base_url}/strategies/config",
                    json={"content": content},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ {data['message']}")
                    self.log(f"📁 Backup: {data['backup']}")
                    QTimer.singleShot(0, dialog.accept)
                else:
                    self.log(f"❌ Erreur sauvegarde: {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ Erreur sauvegarde strategies.ini: {e}")
        
        # Exécuter dans un thread séparé
        thread = threading.Thread(target=save_worker, daemon=True)
        thread.start()
    
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
        """Applique stratégie avec nettoyage automatique - d'abord sélectionner les challenges, puis la stratégie"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucun challenge sélectionné")
            self.log("👆 Veuillez d'abord sélectionner les challenges dans la liste")
            return
        
        # Récupérer la liste des stratégies depuis le backend
        try:
            response = requests.get("http://localhost:8001/api/v1/strategies/list", timeout=5)
            if response.status_code == 200:
                strategies_data = response.json()
                strategies_list = strategies_data.get('strategies', [])
                # Extraire seulement les noms pour le QInputDialog
                strategies = [strategy['name'] for strategy in strategies_list]
            else:
                # Fallback en cas d'erreur
                strategies = ["2m", "3m", "4m", "fill", "fill20", "fill70"]
        except Exception as e:
            self.log(f"⚠️ Erreur chargement stratégies: {e}")
            # Fallback en cas d'erreur réseau  
            strategies = ["2m", "3m", "4m", "fill", "fill20", "fill70"]
        
        # Demander quelle stratégie appliquer
        strategy, ok = QInputDialog.getItem(
            self, 
            "Choix de stratégie", 
            f"Sélectionnez la stratégie à appliquer aux {len(selected)} challenges sélectionnés:", 
            strategies, 
            0, 
            False
        )
        
        if not ok or not strategy:
            self.log("❌ Stratégie annulée")
            return
        
        self.strategy_btn.setEnabled(False)
        
        def strategy_worker():
            try:
                success_count = 0
                current_profile = getattr(self, 'current_profile', 'bruno')  # Profile par défaut
                
                for challenge in selected:
                    try:
                        # Programmer la stratégie via l'API backend
                        scheduled_time = datetime.now() + timedelta(minutes=2)
                        
                        # Construire la requête pour l'API backend
                        strategy_data = {
                            "challenge_id": challenge.id,
                            "strategy_name": strategy,
                            "scheduled_at": scheduled_time.isoformat(),
                            "challenge_title": challenge.title
                        }
                        
                        # Envoyer la requête à l'API backend
                        response = requests.post(
                            f"http://localhost:8001/api/v1/profiles/{current_profile}/strategies",
                            json=strategy_data,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            success_count += 1
                            self.log(f"📅 {strategy}: {challenge.title[:30]}...")
                        else:
                            error_msg = response.json().get('detail', 'Unknown error')
                            self.log(f"❌ Échec stratégie {challenge.title[:20]}: {error_msg}")
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                
                self.log(f"✅ Stratégie {strategy} appliquée à {success_count}/{len(selected)}")
                
                # Refresh automatique après application de stratégies pour voir les changements
                if success_count > 0:
                    self.log("🔄 Refresh automatique des challenges après Stratégie...")
                    # Appel thread-safe depuis le thread principal
                    QMetaObject.invokeMethod(self, "refresh_challenges", Qt.QueuedConnection)
                
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
                        if self.api_client.execute_simple_vote(challenge.url, vote_count):
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
                    # Appel thread-safe depuis le thread principal
                    QMetaObject.invokeMethod(self, "refresh_challenges", Qt.QueuedConnection)
                
            except Exception as e:
                self.log(f"❌ Erreur Fill: {e}")
            finally:
                self.fill_btn.setEnabled(True)
        
        thread = threading.Thread(target=fill_worker)
        thread.start()
    
    def execute_turbo(self):
        """Exécute turbo avec sélection d'algorithme comme GSGUI"""
        selected = self.get_selected()
        if not selected:
            self.log("⚠️ Aucun challenge sélectionné pour Turbo")
            return
        
        # Popup de sélection d'algorithme comme GSGUI original
        dialog = TurboAlgorithmDialog(self)
        if dialog.exec() != QDialog.Accepted:
            self.log("❌ Turbo annulé")
            return
        
        selected_algorithms = dialog.get_selected_algorithms()
        if not selected_algorithms:
            self.log("⚠️ Aucun algorithme sélectionné")
            return
        
        # Format d'algorithme pour le backend (ensemble ou single)
        algorithm_str = f"[{','.join(selected_algorithms)}]" if len(selected_algorithms) > 1 else selected_algorithms[0]
        
        self.log(f"🚀 Démarrage Turbo: {algorithm_str} sur {len(selected)} challenges")
        self.turbo_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected))
        
        def turbo_worker():
            try:
                success_count = 0
                for i, challenge in enumerate(selected):
                    try:
                        self.log(f"🚀 Turbo ({algorithm_str}): {challenge.title[:30]}...")
                        
                        if self.api_client.execute_turbo(challenge.id, challenge.title, algorithm_str):
                            success_count += 1
                            self.log(f"✅ Turbo: {challenge.title[:20]}")
                        else:
                            self.log(f"❌ Turbo échoué: {challenge.title[:20]}")
                        
                        self.progress_bar.setValue(i + 1)
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.log(f"❌ {challenge.title[:20]}: {e}")
                        self.progress_bar.setValue(i + 1)
                
                self.log(f"✅ Turbo terminé: {success_count}/{len(selected)} challenges - {algorithm_str}")
                
                # Refresh automatique après turbo pour mettre à jour les statuts
                if success_count > 0:
                    self.log("🔄 Refresh automatique des challenges après Turbo...")
                    # Appel thread-safe depuis le thread principal
                    QMetaObject.invokeMethod(self, "refresh_challenges", Qt.QueuedConnection)
                
            except Exception as e:
                self.log(f"❌ Erreur Turbo: {e}")
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
        # Arrêter le WebSocket existant s'il y en a un
        self.disconnect_websocket()
        
        # Réinitialiser le flag d'arrêt
        self.websocket_should_stop = False
        
        def websocket_worker():
            try:
                def on_message(ws, message):
                    try:
                        # Vérifier si on doit s'arrêter
                        if self.websocket_should_stop:
                            return
                            
                        data = json.loads(message)
                        timestamp = data.get('timestamp', '')[:19]  # Couper les millisecondes
                        msg_type = data.get('type', 'info')
                        msg_text = data.get('message', '')
                        msg_profile_id = data.get('profile_id')
                        
                        # Filtrer par profil - n'afficher que les messages pour le profil connecté
                        if msg_profile_id and msg_profile_id != self.profile_name:
                            return  # Ignorer les messages des autres profils
                        
                        # Formater selon le type avec support pour les votes
                        if msg_type == "vote_execution":
                            formatted = f"[{timestamp[-8:]}] 🎯 {msg_text}"
                        elif msg_type == "vote_success":
                            formatted = f"[{timestamp[-8:]}] 🗳️✅ {msg_text}"
                        elif msg_type == "vote_error":
                            formatted = f"[{timestamp[-8:]}] 🗳️❌ {msg_text}"
                        elif msg_type == "vote_simulation":
                            formatted = f"[{timestamp[-8:]}] 🎭 {msg_text}"
                        elif msg_type == "refresh_trigger":
                            # Message de refresh + déclencher le refresh automatique
                            formatted = f"[{timestamp[-8:]}] {msg_text}"
                            # Déclencher le refresh de manière thread-safe
                            QMetaObject.invokeMethod(self, "refresh_challenges", Qt.QueuedConnection)
                        elif msg_type == "success":
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
                        if not self.websocket_should_stop:
                            self.log_signal.emit(f"❌ WebSocket parse error: {e}")
                
                def on_error(ws, error):
                    if not self.websocket_should_stop:
                        self.log_signal.emit(f"🔌 WebSocket error: {error}")
                
                def on_close(ws, close_status_code, close_msg):
                    if not self.websocket_should_stop:
                        self.log_signal.emit("🔌 WebSocket connection closed")
                
                def on_open(ws):
                    if not self.websocket_should_stop:
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
                
                # Boucle avec vérification d'arrêt
                while not self.websocket_should_stop:
                    try:
                        self.websocket_client.run_forever()
                        break  # Sortir de la boucle si run_forever se termine normalement
                    except Exception as e:
                        if not self.websocket_should_stop:
                            self.log_signal.emit(f"❌ WebSocket connection failed: {e}")
                            break
                
            except Exception as e:
                if not self.websocket_should_stop:
                    self.log_signal.emit(f"❌ WebSocket worker error: {e}")
        
        # Lancer dans un thread séparé
        self.websocket_thread = threading.Thread(target=websocket_worker, daemon=True)
        self.websocket_thread.start()
    
    def disconnect_websocket(self):
        """Déconnecte proprement le WebSocket"""
        try:
            # Signaler l'arrêt
            self.websocket_should_stop = True
            
            # Fermer la connexion WebSocket
            if hasattr(self, 'websocket_client') and self.websocket_client:
                try:
                    self.websocket_client.close()
                except Exception as e:
                    print(f"⚠️ Erreur fermeture WebSocket: {e}")
            
            # Attendre que le thread se termine (avec timeout)
            if hasattr(self, 'websocket_thread') and self.websocket_thread and self.websocket_thread.is_alive():
                self.websocket_thread.join(timeout=2.0)
            
            # Nettoyer les références
            self.websocket_client = None
            self.websocket_thread = None
            
        except Exception as e:
            print(f"⚠️ Erreur disconnect_websocket: {e}")
    
    def show_active_strategies(self):
        """Affiche la fenêtre des stratégies en cours"""
        def strategies_worker():
            try:
                self.log("🔍 Appel API /strategies/active...")
                
                # Appel API pour récupérer les stratégies actives avec profil
                params = {'profile_name': self.profile_name} if self.profile_name else {}
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
                            
                            # Utiliser l'heure d'exécution calculée par le backend si disponible
                            execution_time = action.get('execution_time')
                            if execution_time:
                                formatted_time = execution_time  # Utiliser l'heure calculée par le backend
                            else:
                                # Fallback à l'ancien système si pas d'heure calculée
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