#!/usr/bin/env python3
"""
Visualiseur de données turbos.feather avec requêtes SQL-like
Interface graphique simple pour explorer les données
"""

import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QTableWidget, QTableWidgetItem, QLineEdit, 
                               QPushButton, QLabel, QTextEdit, QSplitter, QHeaderView,
                               QMessageBox, QComboBox, QCheckBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class TurbosViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.current_df = None
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("🔍 Turbos Viewer - Requêtes SQL sur turbos.feather")
        self.setGeometry(100, 100, 1400, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal vertical
        main_layout = QVBoxLayout(central_widget)
        
        # === EN-TÊTE ===
        header_layout = QHBoxLayout()
        
        # Titre
        title_label = QLabel("🔍 Turbos Viewer")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Compteur de lignes
        self.count_label = QLabel("0 lignes")
        self.count_label.setFont(QFont("Arial", 10))
        header_layout.addWidget(self.count_label)
        
        main_layout.addLayout(header_layout)
        
        # === ZONE DE REQUÊTE ===
        query_group = QWidget()
        query_layout = QVBoxLayout(query_group)
        
        # Label requête
        query_label = QLabel("📝 Requête SQL-like (syntaxe pandas):")
        query_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        query_layout.addWidget(query_label)
        
        # Zone de saisie + boutons
        query_input_layout = QHBoxLayout()
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('Ex: profile_name == "bruno" and photo1_ratio > 1.5')
        self.query_input.returnPressed.connect(self.execute_query)
        query_input_layout.addWidget(self.query_input)
        
        # Boutons
        self.execute_btn = QPushButton("🔍 Exécuter")
        self.execute_btn.clicked.connect(self.execute_query)
        query_input_layout.addWidget(self.execute_btn)
        
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.clicked.connect(self.reset_view)
        query_input_layout.addWidget(self.reset_btn)
        
        self.export_btn = QPushButton("💾 Export CSV")
        self.export_btn.clicked.connect(self.export_current)
        query_input_layout.addWidget(self.export_btn)
        
        query_layout.addLayout(query_input_layout)
        
        # === REQUÊTES RAPIDES ===
        quick_layout = QHBoxLayout()
        quick_label = QLabel("⚡ Requêtes rapides:")
        quick_layout.addWidget(quick_label)
        
        self.quick_combo = QComboBox()
        self.quick_combo.addItems([
            "-- Sélectionner --",
            'profile_name == "bruno"',
            'profile_name == "caloune"',
            'profile_name == "*"',
            'profile_name == "*" view=[-10:]',
            'profile_name == "*" view=[0:10]',
            'winner_id != ""',
            'photo1_ratio > 1.5',
            'photo1_votes > photo2_votes',
            'abs(photo1_ratio - photo2_ratio) < 0.1',
            'photo1_votes > 500 and photo1_ratio > 1.5'
        ])
        self.quick_combo.currentTextChanged.connect(self.set_quick_query)
        quick_layout.addWidget(self.quick_combo)
        
        quick_layout.addStretch()
        
        # Checkbox pour afficher toutes les colonnes
        self.show_all_cols = QCheckBox("Afficher toutes les colonnes")
        self.show_all_cols.stateChanged.connect(self.update_table)
        quick_layout.addWidget(self.show_all_cols)
        
        query_layout.addLayout(quick_layout)
        main_layout.addWidget(query_group)
        
        # === SPLITTER POUR TABLE + INFO ===
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === TABLE ===
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Headers redimensionnables
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        
        splitter.addWidget(self.table)
        
        # === ZONE D'INFO ===
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setFont(QFont("Consolas", 9))
        self.info_text.setPlaceholderText("Informations sur la requête...")
        splitter.addWidget(self.info_text)
        
        # Proportions du splitter
        splitter.setSizes([600, 150])
        main_layout.addWidget(splitter)
        
        # === EXEMPLES ===
        examples_label = QLabel(
            "💡 Exemples: profile_name == 'bruno' | photo1_ratio > 1.5 | "
            "photo1_votes > photo2_votes and photo1_ratio > photo2_ratio | "
            "challenge_title.str.contains('Photo')"
        )
        examples_label.setFont(QFont("Arial", 8))
        examples_label.setStyleSheet("color: #666; margin: 5px;")
        main_layout.addWidget(examples_label)
    
    def load_data(self):
        """Charge les données turbos.feather"""
        try:
            self.df = pd.read_feather('turbos.feather')
            self.current_df = self.df.copy()
            
            self.info_text.append(f"✅ Données chargées: {len(self.df)} turbos")
            self.info_text.append(f"📋 Colonnes: {', '.join(self.df.columns)}")
            self.info_text.append(f"👥 Profils: {', '.join(self.df['profile_name'].unique())}")
            
            self.update_table()
            
        except FileNotFoundError:
            QMessageBox.critical(self, "Erreur", 
                               "Fichier turbos.feather non trouvé!\n"
                               "Exécutez d'abord extract_all_turbos.py")
            sys.exit(1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur chargement: {e}")
            sys.exit(1)
    
    def set_quick_query(self, query):
        """Définit une requête rapide"""
        if query != "-- Sélectionner --":
            self.query_input.setText(query)
    
    def execute_query(self):
        """Exécute la requête SQL-like"""
        query = self.query_input.text().strip()
        
        if not query:
            self.reset_view()
            return
        
        try:
            # Gestion des requêtes spéciales (comme dans query_turbos.py)
            view_slice = None
            original_query = query
            
            # Extraction du paramètre view=[]
            if 'view=' in query:
                import re
                view_match = re.search(r'view=\[(.*?)\]', query)
                if view_match:
                    view_param = view_match.group(1)
                    query = re.sub(r'\s*view=\[.*?\]', '', query).strip()
                    
                    # Parser le slice
                    try:
                        if ':' in view_param:
                            # Format slice [start:end]
                            parts = view_param.split(':')
                            start = int(parts[0]) if parts[0] else None
                            end = int(parts[1]) if len(parts) > 1 and parts[1] else None
                            view_slice = slice(start, end)
                        else:
                            # Index simple
                            view_slice = int(view_param)
                    except:
                        self.info_text.append(f"⚠️ Format view invalide: {view_param}")
                        return
            
            # Gestion de la requête spéciale '*'
            if query.strip() == 'profile_name == "*"':
                query = "profile_name.notna()"
            
            # Nettoyer la requête
            query = query.strip()
            if not query:
                query = "profile_name.notna()"
            
            # Exécuter la requête
            result_df = self.df.query(query)
            
            # Appliquer le slice view si spécifié
            if view_slice is not None:
                if isinstance(view_slice, slice):
                    self.current_df = result_df.iloc[view_slice]
                    self.info_text.append(f"👁️ Vue: lignes {view_slice.start or 'début'}:{view_slice.stop or 'fin'} sur {len(result_df)} résultats")
                else:
                    if view_slice < len(result_df):
                        self.current_df = result_df.iloc[[view_slice]]
                        self.info_text.append(f"👁️ Vue: ligne {view_slice} sur {len(result_df)} résultats")
                    else:
                        self.current_df = pd.DataFrame()
                        self.info_text.append(f"⚠️ Ligne {view_slice} inexistante (max: {len(result_df)-1})")
            else:
                self.current_df = result_df
            
            self.info_text.append(f"\n🔍 Requête: {query}")
            self.info_text.append(f"📊 Résultats: {len(self.current_df)} lignes")
            
            if len(self.current_df) == 0:
                self.info_text.append("⚠️ Aucun résultat trouvé")
            else:
                # Statistiques rapides
                if 'profile_name' in self.current_df.columns:
                    profils = self.current_df['profile_name'].value_counts()
                    self.info_text.append(f"👥 Par profil: {dict(profils)}")
                
                if 'winner_id' in self.current_df.columns:
                    avec_gagnant = (self.current_df['winner_id'] != '').sum()
                    self.info_text.append(f"🏆 Avec gagnant: {avec_gagnant}/{len(self.current_df)}")
            
            self.update_table()
            
        except Exception as e:
            self.info_text.append(f"\n❌ Erreur requête: {e}")
            QMessageBox.warning(self, "Erreur de requête", 
                               f"Erreur dans la requête:\n{e}\n\n"
                               f"Vérifiez la syntaxe pandas.")
    
    def reset_view(self):
        """Remet la vue à l'état initial"""
        self.current_df = self.df.copy()
        self.query_input.clear()
        self.quick_combo.setCurrentIndex(0)
        self.info_text.append(f"\n🔄 Vue réinitialisée: {len(self.current_df)} lignes")
        self.update_table()
    
    def update_table(self):
        """Met à jour l'affichage de la table"""
        if self.current_df is None:
            return
        
        # Colonnes à afficher
        if self.show_all_cols.isChecked():
            display_df = self.current_df
        else:
            # Colonnes principales seulement
            main_cols = ['profile_name', 'challenge_title', 'temps_restant', 'photo1_id', 'photo2_id',
                        'photo1_votes', 'photo2_votes', 'photo1_ratio', 'photo2_ratio', 
                        'winner_id']
            available_cols = [col for col in main_cols if col in self.current_df.columns]
            display_df = self.current_df[available_cols]
        
        # Limiter à 1000 lignes pour les performances
        if len(display_df) > 1000:
            display_df = display_df.head(1000)
            self.info_text.append(f"⚠️ Affichage limité aux 1000 premières lignes")
        
        # Configuration de la table
        self.table.setRowCount(len(display_df))
        self.table.setColumnCount(len(display_df.columns))
        self.table.setHorizontalHeaderLabels(list(display_df.columns))
        
        # Remplissage des données
        for i, (_, row) in enumerate(display_df.iterrows()):
            for j, value in enumerate(row):
                # Formatage des valeurs
                if pd.isna(value):
                    text = ""
                elif isinstance(value, float):
                    text = f"{value:.2f}"
                else:
                    text = str(value)
                
                item = QTableWidgetItem(text)
                
                # Coloration spéciale
                if display_df.columns[j] == 'winner_id':
                    if text == "":
                        item.setBackground(Qt.GlobalColor.lightGray)
                    else:
                        item.setBackground(Qt.GlobalColor.lightGreen)
                
                self.table.setItem(i, j, item)
        
        # Ajustement des colonnes
        self.table.resizeColumnsToContents()
        
        # Mise à jour du compteur
        self.count_label.setText(f"{len(self.current_df)} lignes")
    
    def export_current(self):
        """Exporte les données actuelles en CSV"""
        if self.current_df is None or len(self.current_df) == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter")
            return
        
        try:
            filename = f"turbos_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.current_df.to_csv(filename, index=False)
            
            self.info_text.append(f"\n💾 Export: {filename} ({len(self.current_df)} lignes)")
            QMessageBox.information(self, "Export réussi", 
                                  f"Données exportées:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur export", f"Erreur: {e}")

def main():
    """Fonction principale"""
    app = QApplication(sys.argv)
    
    # Style
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTableWidget {
            gridline-color: #d0d0d0;
            background-color: white;
        }
        QTableWidget::item:selected {
            background-color: #3daee9;
            color: white;
        }
        QPushButton {
            padding: 5px 10px;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: white;
        }
        QPushButton:hover {
            background-color: #e9e9e9;
        }
        QPushButton:pressed {
            background-color: #d9d9d9;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        QTextEdit {
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: #f9f9f9;
        }
    """)
    
    viewer = TurbosViewer()
    viewer.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()