#!/usr/bin/env python3
"""
Test de la popup Fill - démo standalone
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QInputDialog, QLabel

class TestFillPopup(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Fill Popup - GSGUI Style")
        self.setGeometry(300, 300, 400, 200)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.info_label = QLabel("Cliquez sur Fill pour tester la popup comme dans GSGUI")
        layout.addWidget(self.info_label)
        
        self.fill_btn = QPushButton("⚡ Fill")
        self.fill_btn.setStyleSheet("QPushButton { background-color: #16a085; font-size: 14px; padding: 10px; }")
        self.fill_btn.clicked.connect(self.test_fill_popup)
        layout.addWidget(self.fill_btn)
        
        self.result_label = QLabel("Résultat:")
        layout.addWidget(self.result_label)
    
    def test_fill_popup(self):
        """Test de la popup Fill comme GSGUI"""
        # Simuler 3 challenges sélectionnés
        selected_count = 3
        
        # Popup identique à celle de GSGUI Enhanced
        vote_count, ok = QInputDialog.getInt(
            self, 
            "⚡ Fill - Nombre de votes", 
            f"Nombre de votes à exécuter pour {selected_count} challenge(s) sélectionné(s):",
            80,  # Valeur par défaut
            1,   # Minimum
            999, # Maximum
            1    # Step
        )
        
        if ok:
            self.result_label.setText(f"✅ Résultat: {vote_count} votes pour {selected_count} challenges")
        else:
            self.result_label.setText("❌ Fill annulé par l'utilisateur")

def main():
    app = QApplication(sys.argv)
    window = TestFillPopup()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()