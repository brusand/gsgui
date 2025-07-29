#!/usr/bin/env python3
"""
Script de démarrage GSGUI Desktop Simple
Lance le backend et l'interface utilisateur
"""

import os
import sys
import subprocess
import time
import signal
import asyncio
from pathlib import Path

# Chemin du projet
PROJECT_ROOT = Path(__file__).parent
SRC_GS = PROJECT_ROOT / "src" / "gs"

def start_backend():
    """Démarre le backend API"""
    print("🚀 Démarrage du backend API...")
    backend_cmd = [sys.executable, "backend_simple.py"]
    
    process = subprocess.Popen(
        backend_cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Attendre que le backend soit prêt
    time.sleep(3)
    
    return process

def start_ui():
    """Démarre l'interface utilisateur"""
    print("🎨 Démarrage de l'interface...")
    ui_cmd = [sys.executable, "gsui_simple.py"]
    
    process = subprocess.Popen(
        ui_cmd,
        cwd=SRC_GS
    )
    
    return process

def main():
    """Main function"""
    print("=" * 50)
    print("🎯 GSGUI Desktop Simple - Démarrage")
    print("=" * 50)
    
    backend_process = None
    ui_process = None
    
    try:
        # 1. Démarrer le backend
        backend_process = start_backend()
        
        # 2. Démarrer l'interface
        ui_process = start_ui()
        
        print("✅ Système démarré!")
        print("📋 Interface: 6 boutons essentiels (Refresh, All, None, Fill, Stratégie, Turbo)")
        print("🔧 Fonctionnalité: Nettoyage automatique des stratégies")
        print("🔴 Pour arrêter: Ctrl+C")
        print()
        
        # Attendre que l'interface se ferme
        ui_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé...")
        
    finally:
        # Arrêter les processus
        if ui_process and ui_process.poll() is None:
            print("🔴 Arrêt interface...")
            ui_process.terminate()
            
        if backend_process and backend_process.poll() is None:
            print("🔴 Arrêt backend...")
            backend_process.terminate()
            
        print("👋 Au revoir!")

if __name__ == "__main__":
    main()