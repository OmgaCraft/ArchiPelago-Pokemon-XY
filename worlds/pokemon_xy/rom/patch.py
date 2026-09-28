"""
[FR] Patch du jeu livré en dossier de mods LayeredFS pour BizHawk (cœur Encore).

Encore lit `<dossier utilisateur 3DS>/load/mods/<Title ID>/romfs/` au démarrage du
jeu (encore : src/core/file_sys/ncch_container.cpp). Seuls les fichiers modifiés
y sont écrits, reconstruits à partir du dump du joueur : aucun fichier du jeu
n'est distribué.

Objets au sol : script n° 0x11 de l'archive a/0/3/1 (d'après PokeRandomizer,
OverworldItems.cs). Après 9 mots de données, un tableau de 207 entrées
(objet, quantité, n° de la Poké Ball). La Poké Ball n° i lève le drapeau
0x51A + i, celui des lieux « FIELD ITEM » du monde (vérifié sur les 207).
"""

import json
import os
from typing import Dict, Iterable, Optional, Tuple

from .amx import AMX
from .garc import GARC
from .romfs import RomFS

TITLE_ID_Y = 0x0004000000055E00

FIELD_ITEM_GARC = "a/0/3/1"
FIELD_ITEM_SCRIPT = 0x11
FIELD_ITEM_TABLE_START = 9
FIELD_ITEM_COUNT = 207
FIELD_ITEM_FLAG_BASE = 0x51A

AP_ITEM_OFFSET = 200000
# Objets rares : on ne les fait pas donner par le script des Poké Balls (jamais le cas
# dans le jeu d'origine). Même liste que les poches « Key Items » du client.
KEY_ITEM_IDS = frozenset([216, 431, 442, 445, 446, 447, 450, 465, 466, 471, 628, 629, 631, 632, 638, 641,
                          642, 643, 651, 689, 695, 696, 697, 698, 700, 701, 702, 703, 705, 712, 713, 714])

# Fichier écrit à côté des mods pour savoir quelle partie les a produits.
STAMP_FILE = "archipelago.json"


class PatchError(Exception):
    pass


def field_item_index(flag_id: int) -> Optional[int]:
    """N° de la Poké Ball au sol pour un drapeau, ou None si ce n'en est pas une."""
    index = flag_id - FIELD_ITEM_FLAG_BASE
    return index if 0 <= index < FIELD_ITEM_COUNT else None


def native_item_id(ap_item_id: int, item_player: int, my_slot: int, game_item_ids: frozenset) -> Optional[int]:
    """
    Objet que la Poké Ball peut donner elle-même, ou None s'il faut garder l'objet
    d'origine : objet d'un autre joueur, badge, objet rare.
    `game_item_ids` : ids du jeu des objets du monde qui sont de vrais objets du jeu.
    """
    if item_player != my_slot:
        return None
    game_id = ap_item_id - AP_ITEM_OFFSET
    if game_id not in game_item_ids or game_id in KEY_ITEM_IDS:
        return None
    return game_id


def read_field_items(garc_data: bytes) -> list:
    amx = AMX(GARC(garc_data).get(FIELD_ITEM_SCRIPT))
    start = amx.data_start + FIELD_ITEM_TABLE_START
    return [amx.words[start + i * 3] for i in range(FIELD_ITEM_COUNT)]


def build_field_items(garc_data: bytes, items: Dict[int, int]) -> bytes:
    """Nouvelle archive a/0/3/1 où la Poké Ball n° i donne items[i]."""
    garc = GARC(garc_data)
    amx = AMX(garc.get(FIELD_ITEM_SCRIPT))
    start = amx.data_start + FIELD_ITEM_TABLE_START
    for index, item_id in items.items():
        if not 0 <= index < FIELD_ITEM_COUNT:
            raise PatchError(f"Poké Ball n° {index} inexistante.")
        amx.words[start + index * 3] = item_id
    garc.set(FIELD_ITEM_SCRIPT, amx.build())
    return garc.build()


def build_mod_files(rom_path: str, items: Dict[int, int]) -> Dict[str, bytes]:
    """Fichiers de la RomFS à remplacer, construits depuis le dump du joueur."""
    with open(rom_path, "rb") as handle:
        rom = RomFS(handle)
        if rom.title_id != TITLE_ID_Y:
            raise PatchError(f"Ce dump n'est pas Pokémon Y (Title ID {rom.title_id:016X}).")
        original = rom.read_file(FIELD_ITEM_GARC)
    return {FIELD_ITEM_GARC: build_field_items(original, items)}


def mods_directory(emuhawk_path: str, title_id: int = TITLE_ID_Y) -> str:
    """Dossier des mods d'Encore pour ce BizHawk (chemins lus dans config.ini si possible)."""
    bizhawk_dir = os.path.dirname(os.path.abspath(emuhawk_path))
    base, user = "./3DS", "./User"
    try:
        with open(os.path.join(bizhawk_dir, "config.ini"), encoding="utf-8-sig") as handle:
            entries = json.load(handle).get("PathEntries", {}).get("Paths", [])
        for entry in entries:
            if entry.get("System") == "3DS" and entry.get("Type") == "Base" and entry.get("Path"):
                base = entry["Path"]
            if entry.get("System") == "3DS" and entry.get("Type") == "User" and entry.get("Path"):
                user = entry["Path"]
    except (OSError, ValueError, AttributeError):
        pass
    base_dir = base if os.path.isabs(base) else os.path.join(bizhawk_dir, base)
    user_dir = user if os.path.isabs(user) else os.path.join(base_dir, user)
    return os.path.normpath(os.path.join(user_dir, "load", "mods", f"{title_id:016X}"))


def write_mod(mod_dir: str, files: Dict[str, bytes], stamp: dict) -> bool:
    """Écrit les fichiers modifiés ; renvoie True si quelque chose a changé."""
    changed = False
    for path, data in files.items():
        target = os.path.join(mod_dir, "romfs", *path.split("/"))
        try:
            with open(target, "rb") as handle:
                if handle.read() == data:
                    continue
        except OSError:
            pass
        os.makedirs(os.path.dirname(target), exist_ok=True)
        temporary = target + ".tmp"
        with open(temporary, "wb") as handle:
            handle.write(data)
        os.replace(temporary, target)
        changed = True
    with open(os.path.join(mod_dir, STAMP_FILE), "w", encoding="utf-8") as handle:
        json.dump(stamp, handle, indent=2)
    return changed


def field_items_from_scouts(scouted: Iterable[Tuple[int, int, int]], flag_by_location: Dict[int, int],
                            my_slot: int, game_item_ids: frozenset) -> Dict[int, int]:
    """
    (lieu, objet, joueur) renvoyés par le serveur -> {n° de Poké Ball: objet du jeu}.
    Seules les Poké Balls qui changent sont renvoyées.
    """
    items: Dict[int, int] = {}
    for location, item, player in scouted:
        flag = flag_by_location.get(location)
        index = field_item_index(flag) if flag is not None else None
        if index is None:
            continue
        game_id = native_item_id(item, player, my_slot, game_item_ids)
        if game_id is not None:
            items[index] = game_id
    return items
