"""
Command Schema — source de vérité unique pour les commandes de stratégie.
Utilisé par le backend (validation/parse) et exposé au frontend (UI dynamique).
"""

from typing import Any, Dict, List, Optional
import re

# ─────────────────────────────────────────────────────────────
#  Schéma
# ─────────────────────────────────────────────────────────────

COMMAND_SCHEMA: Dict[str, Any] = {
    "vote": {
        "label": "Voter",
        "icon": "🗳️",
        "args": [
            {"name": "timing",  "type": "timing",  "label": "Quand",  "required": True},
            {"name": "count",   "type": "integer", "label": "Votes",  "required": True, "min": 1, "max": 500},
        ],
    },
    "submit": {
        "label": "Soumettre photos",
        "icon": "📸",
        "args": [
            {"name": "timing",  "type": "timing",     "label": "Quand",         "required": True},
            {"name": "photos",  "type": "photo_list", "label": "Photos (UIDs)", "required": False, "multiple": True},
        ],
    },
    "turbo": {
        "label": "Turbo",
        "icon": "⚡",
        "args": [
            {"name": "timing", "type": "timing",      "label": "Quand",      "required": True},
            {"name": "index",  "type": "turbo_index", "label": "Photo index", "required": False},
        ],
    },
    "boost": {
        "label": "Boost",
        "icon": "🚀",
        "args": [
            {"name": "timing", "type": "timing",      "label": "Quand",      "required": True},
            {"name": "index",  "type": "turbo_index", "label": "Photo index", "required": False},
        ],
    },
    "revote": {
        "label": "Re-voter si exposition basse",
        "icon": "🔄",
        "args": [
            {"name": "timing",    "type": "timing",    "label": "Surveiller à partir de", "required": True},
            {"name": "condition", "type": "condition", "label": "Si exposition",           "required": True},
            {"name": "count",     "type": "integer",   "label": "Votes",                  "required": True, "min": 1, "max": 500},
            {"name": "deadline",  "type": "timing",    "label": "Arrêter avant",           "required": False},
        ],
    },
    "swap": {
        "label": "Échanger photos",
        "icon": "🔀",
        "args": [
            {"name": "timing",    "type": "timing",    "label": "Quand",                  "required": True},
            {"name": "photo_out", "type": "photo_uid", "label": "Photo sortante (UID)",   "required": True},
            {"name": "photo_in",  "type": "photo_uid", "label": "Photo entrante (UID)",   "required": True},
        ],
    },
    "unlocked_boost": {
        "label": "Boost gratuit auto",
        "icon": "🎁",
        "args": [
            {"name": "timing", "type": "timing",  "label": "Vérifier dans", "required": True},
            {"name": "index",  "type": "integer", "label": "Index",         "required": False},
        ],
    },
    "cancel": {
        "label": "Annuler la stratégie",
        "icon": "🛑",
        "args": [],  # Pas d'arguments — annule simplement la stratégie en cours
    },
}

# ─────────────────────────────────────────────────────────────
#  Parser  :  ligne INI  →  dict structuré
# ─────────────────────────────────────────────────────────────

def parse_command_line(line: str) -> Dict[str, Any]:
    """
    Parse une ligne de stratégie.ini en dict structuré.

    Ex: "vote, end-3m0s, 50"
        → {"type": "vote", "args": {"timing": "end-3m0s", "count": 50}}

        "revote, end-05h30m00s, <50, 50, end-01h00m00s"
        → {"type": "revote", "args": {"timing": "end-05h30m00s",
                                      "condition": "<50", "count": 50,
                                      "deadline": "end-01h00m00s"}}

        "submit, end-06h10m01s, uid1, uid2"
        → {"type": "submit", "args": {"timing": "end-06h10m01s",
                                      "photos": ["uid1", "uid2"]}}
    """
    # Enlever guillemets éventuels
    line = line.strip().strip('"').strip("'")
    parts = [p.strip() for p in line.split(",")]
    if not parts:
        raise ValueError("Ligne vide")

    cmd_type = parts[0].lower()
    raw_args = parts[1:]

    schema = COMMAND_SCHEMA.get(cmd_type)
    if schema is None:
        # Commande inconnue : on retourne quand même avec les args bruts
        return {"type": cmd_type, "args": {"_raw": ", ".join(raw_args)}, "unknown": True}

    arg_defs = schema["args"]
    result_args: Dict[str, Any] = {}

    for i, arg_def in enumerate(arg_defs):
        name = arg_def["name"]
        atype = arg_def["type"]
        multiple = arg_def.get("multiple", False)

        if i >= len(raw_args):
            if not arg_def.get("required", True):
                continue
            raise ValueError(f"Argument manquant: {name} pour commande {cmd_type}")

        raw = raw_args[i].strip()

        if multiple:
            # Consomme tous les args restants
            all_vals = [v.strip() for v in raw_args[i:] if v.strip()]
            result_args[name] = all_vals
            break
        elif atype == "integer":
            result_args[name] = int(raw) if raw else None
        elif atype in ("timing", "condition", "turbo_index", "photo_uid"):
            result_args[name] = raw if raw else None
        else:
            result_args[name] = raw

    return {"type": cmd_type, "args": result_args}


# ─────────────────────────────────────────────────────────────
#  Serializer  :  dict structuré  →  ligne INI
# ─────────────────────────────────────────────────────────────

def serialize_command(cmd: Dict[str, Any]) -> str:
    """
    Sérialise un dict structuré en ligne de stratégie.ini.

    Ex: {"type": "vote", "args": {"timing": "end-3m0s", "count": 50}}
        → "vote, end-3m0s, 50"
    """
    cmd_type = cmd.get("type", "")
    args = cmd.get("args", {})

    schema = COMMAND_SCHEMA.get(cmd_type)
    if schema is None:
        raw = args.get("_raw", "")
        return f"{cmd_type}, {raw}".rstrip(", ")

    # Defaults par type quand une valeur required est absente
    _type_defaults = {
        "timing": "now",
        "integer": "0",
        "condition": "<50",
        "turbo_index": "",
        "photo_list": "",
        "photo_uid": "",
    }

    parts = [cmd_type]
    for arg_def in schema["args"]:
        name = arg_def["name"]
        atype = arg_def["type"]
        val = args.get(name)
        if val is None or val == "" or (isinstance(val, list) and len(val) == 0):
            if not arg_def.get("required", True):
                continue
            # Arg requis manquant → fallback sur le défaut du type
            default = _type_defaults.get(atype, "")
            if default == "" and atype not in ("turbo_index", "photo_list", "photo_uid"):
                continue  # skip plutôt que planter
            val = default
        if isinstance(val, list):
            parts.extend(str(v) for v in val if v)
        else:
            parts.append(str(val))

    return ", ".join(parts)  # Pour "cancel" → schema["args"] vide → juste "cancel"


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def parse_template_commands(section: Dict) -> List[Dict[str, Any]]:
    """
    Parse toutes les commandes numérotées d'une section ConfigObj.
    Retourne la liste ordonnée de dicts structurés.
    """
    commands = []
    # Clés numériques seulement, triées
    numeric_keys = sorted(
        [k for k in section if k.isdigit()],
        key=lambda x: int(x)
    )
    for k in numeric_keys:
        line = section[k]
        try:
            commands.append(parse_command_line(line))
        except Exception as e:
            commands.append({"type": "unknown", "args": {"_raw": line}, "error": str(e)})
    return commands


def serialize_template_commands(commands: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Sérialise une liste de dicts structurés en dict {0: "...", 1: "...", ...}.
    """
    result = {}
    for i, cmd in enumerate(commands):
        result[str(i)] = serialize_command(cmd)
    return result


INSTANCE_SEP = "__"


def make_instance_name(template_name: str, profile_id: str, challenge_id: str) -> str:
    return f"{template_name}{INSTANCE_SEP}{profile_id}{INSTANCE_SEP}{challenge_id}"


def is_instance(name: str) -> bool:
    return INSTANCE_SEP in name


def split_instance_name(name: str):
    """Retourne (template_name, profile_id, challenge_id) ou None si pas une instance."""
    parts = name.split(INSTANCE_SEP, 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return None
