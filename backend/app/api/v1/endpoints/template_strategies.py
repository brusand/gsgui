"""
Template Strategies API — gestion visuelle des stratégies.

Templates  : sections de strategies.ini sans '__'
Instances  : sections de strategies.ini avec '__' (format: template__profile__challenge)
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict, List, Optional
import logging
from configobj import ConfigObj

from app.utils.paths import STRATEGIES_INI_PATH_STR
from app.services.command_schema import (
    COMMAND_SCHEMA,
    parse_template_commands,
    serialize_template_commands,
    make_instance_name,
    is_instance,
    split_instance_name,
    parse_command_line,
    serialize_command,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_strategies() -> ConfigObj:
    return ConfigObj(STRATEGIES_INI_PATH_STR, encoding="utf-8")


def _save_strategies(cfg: ConfigObj):
    cfg.write()


def _section_to_template(name: str, section: Dict) -> Dict[str, Any]:
    commands = parse_template_commands(section)
    info = split_instance_name(name)
    return {
        "name": name,
        "description": section.get("description", "").strip('"'),
        "schedule_when": section.get("schedule_when", "").strip('"'),
        "commands": commands,
        "is_instance": info is not None,
        "template_name": info[0] if info else None,
        "profile_id":    info[1] if info else None,
        "challenge_id":  info[2] if info else None,
    }


# ─────────────────────────────────────────────────────────────
#  Schema
# ─────────────────────────────────────────────────────────────

@router.get("/command-schema")
def get_command_schema():
    """Retourne le schéma des commandes pour le frontend."""
    return {"schema": COMMAND_SCHEMA}


# ─────────────────────────────────────────────────────────────
#  Templates
# ─────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(instances: bool = False):
    """
    Liste les templates (et optionnellement les instances).
    - instances=false (défaut) : templates seulement
    - instances=true           : tout
    """
    cfg = _load_strategies()
    result = []
    for name, section in cfg.items():
        if not isinstance(section, dict):
            continue
        if not instances and is_instance(name):
            continue
        result.append(_section_to_template(name, section))
    return {"templates": result}


@router.get("/templates/{name:path}")
def get_template(name: str):
    cfg = _load_strategies()
    if name not in cfg:
        raise HTTPException(status_code=404, detail=f"Template '{name}' introuvable")
    return _section_to_template(name, cfg[name])


@router.post("/templates/{name:path}/clone")
def clone_template(
    name: str,
    profile_id: str = Body(...),
    challenge_id: str = Body(...),
):
    """
    Clone un template en instance : {name}__{profile_id}__{challenge_id}.
    Si l'instance existe déjà elle est écrasée.
    """
    cfg = _load_strategies()
    if name not in cfg:
        raise HTTPException(status_code=404, detail=f"Template '{name}' introuvable")

    instance_name = make_instance_name(name, profile_id, challenge_id)

    # Copier la section
    src = cfg[name]
    cfg[instance_name] = {}
    for k, v in src.items():
        cfg[instance_name][k] = v

    _save_strategies(cfg)
    logger.info(f"✅ Template '{name}' cloné en '{instance_name}'")
    return _section_to_template(instance_name, cfg[instance_name])


@router.put("/templates/{name:path}")
def update_template(
    name: str,
    description: Optional[str] = Body(None),
    commands: Optional[List[Dict[str, Any]]] = Body(None),
    schedule_when: Optional[str] = Body(None),
):
    """Met à jour description et/ou commandes d'un template ou d'une instance."""
    cfg = _load_strategies()
    if name not in cfg:
        # Créer si inexistant
        cfg[name] = {}

    section = cfg[name]

    if description is not None:
        section["description"] = description

    if schedule_when is not None:
        if schedule_when.strip():
            section["schedule_when"] = schedule_when.strip()
        else:
            # Remove schedule_when if empty
            if "schedule_when" in section:
                del section["schedule_when"]

    if commands is not None:
        # Supprimer anciennes clés numériques
        old_keys = [k for k in list(section.keys()) if k.isdigit()]
        for k in old_keys:
            del section[k]
        # Écrire nouvelles
        serialized = serialize_template_commands(commands)
        for k, v in serialized.items():
            section[k] = v

    _save_strategies(cfg)
    logger.info(f"✅ Template '{name}' mis à jour")
    return _section_to_template(name, cfg[name])


@router.delete("/templates/{name:path}")
def delete_template(name: str, force: bool = False):
    """
    Supprime une section. Par défaut refuse de supprimer un template pur
    (uniquement des instances). Passer force=true pour forcer.
    """
    cfg = _load_strategies()
    if name not in cfg:
        raise HTTPException(status_code=404, detail=f"'{name}' introuvable")

    if not is_instance(name) and not force:
        raise HTTPException(
            status_code=400,
            detail="Refus de supprimer un template pur. Passer force=true pour forcer."
        )

    del cfg[name]
    _save_strategies(cfg)
    logger.info(f"🗑️ '{name}' supprimé")
    return {"deleted": name}


# ─────────────────────────────────────────────────────────────
#  Parse / Serialize helpers (utilisés par le frontend live)
# ─────────────────────────────────────────────────────────────

@router.post("/parse-command")
def parse_command(line: str = Body(..., embed=True)):
    """Parse une ligne brute en dict structuré."""
    try:
        return parse_command_line(line)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/serialize-command")
def serialize_cmd(command: Dict[str, Any] = Body(...)):
    """Sérialise un dict structuré en ligne INI."""
    try:
        return {"line": serialize_command(command)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
