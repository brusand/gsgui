"""
Endpoints pour la gestion des logs
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pathlib import Path

router = APIRouter()

def get_log_file_path(log_type: str) -> Path:
    """Retourne le chemin du fichier de log selon le type"""
    # Chemin vers le répertoire logs depuis le backend
    logs_dir = Path(__file__).parent.parent.parent.parent.parent / "logs"
    
    if log_type == "backend":
        return logs_dir / "backend.log"
    elif log_type == "frontend":
        return logs_dir / "frontend.log" 
    elif log_type == "manager":
        return logs_dir / "manager.log"
    else:
        raise HTTPException(status_code=400, detail=f"Type de log non supporté: {log_type}")

@router.get("/logs/{log_type}")
async def get_logs(log_type: str):
    """
    Récupère le contenu d'un fichier de log
    
    Args:
        log_type: Type de log (backend, frontend, manager)
        
    Returns:
        Contenu du fichier de log en texte brut
    """
    try:
        log_file = get_log_file_path(log_type)
        
        if not log_file.exists():
            return PlainTextResponse(
                content=f"# Fichier de log non trouvé\n# Chemin: {log_file}\n# Le fichier sera créé au démarrage de l'application",
                status_code=200
            )
        
        # Lire le fichier de log
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Limiter la taille si le fichier est trop gros (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(content) > max_size:
            # Prendre les dernières lignes pour rester dans la limite
            lines = content.split('\n')
            truncated_lines = []
            current_size = 0
            
            # Partir de la fin et remonter
            for line in reversed(lines):
                line_size = len(line) + 1  # +1 pour le \n
                if current_size + line_size > max_size:
                    break
                truncated_lines.append(line)
                current_size += line_size
            
            # Remettre dans l'ordre et ajouter un message d'info
            truncated_lines.reverse()
            content = "# Fichier tronqué - seules les dernières lignes sont affichées\n" + '\n'.join(truncated_lines)
        
        return PlainTextResponse(
            content=content,
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture du fichier de log: {str(e)}"
        )