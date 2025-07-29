#!/usr/bin/env python3
"""
GSGUI Desktop Simple - Script de lancement
Usage: python run_gsgui.py
"""

import os
import sys
import time
import signal
import subprocess
import requests
from pathlib import Path

def check_backend():
    """Vérifie si le backend est accessible"""
    try:
        response = requests.get("http://localhost:8001/", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    """Démarre le backend en arrière-plan"""
    cmd = [sys.executable, "backend_simple.py"]
    
    # Rediriger sortie vers fichier log
    with open("backend.log", "w") as log_file:
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=Path(__file__).parent
        )
    
    return process

def start_ui():
    """Démarre l'interface utilisateur"""
    cmd = [sys.executable, "gsui_simple.py"]
    src_gs = Path(__file__).parent / "src" / "gs"
    
    process = subprocess.run(cmd, cwd=src_gs)
    return process.returncode

def main():
    """Main function"""
    print("🎯 GSGUI Desktop Simple - Démarrage")
    print("=" * 40)
    
    backend_process = None
    
    try:
        # Tuer anciens processus
        os.system("pkill -f 'backend_simple.py' 2>/dev/null")
        time.sleep(1)
        
        # Démarrer backend
        print("🚀 Démarrage backend API...")
        backend_process = start_backend()
        
        # Attendre que le backend soit prêt
        print("⏳ Attente du backend...")
        for i in range(10):
            time.sleep(1)
            if check_backend():
                print("✅ Backend prêt sur port 8001")
                break
        else:
            print("❌ Backend non accessible")
            return 1
        
        # Démarrer interface
        print("🎨 Lancement interface...")
        print("📋 6 boutons: Refresh, All, None, Fill, Stratégie, Turbo")
        print("🔧 Nettoyage automatique des stratégies")
        print()
        
        start_ui()
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé...")
        
    finally:
        # Nettoyer
        if backend_process and backend_process.poll() is None:
            print("🔴 Arrêt backend...")
            backend_process.terminate()
            time.sleep(1)
            if backend_process.poll() is None:
                backend_process.kill()
        
        print("👋 Au revoir!")
        return 0

if __name__ == "__main__":
    exit(main())