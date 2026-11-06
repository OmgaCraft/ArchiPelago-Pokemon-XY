"""
[FR] Fichier de patch par joueur (.apxy), créé à la génération comme pour Pokémon Émeraude.

Il contient la graine de la partie, les options et le contenu de chaque Poké Ball au sol, tous connus dès la
génération : on le télécharge sur la page de la salle (« Download Patch File… »). Ouvert avec le Launcher,
il construit le patch du jeu depuis le dump du joueur, lance BizHawk avec le script de la partie, puis le
client. Le dump n'est jamais modifié. Les sauvegardes restent celles du jeu : sur 3DS elles sont rangées
par numéro de jeu (Title ID), pas par fichier.
"""

import json
import subprocess
from typing import Any, Dict, Optional

from worlds.Files import APAutoPatchInterface
from worlds.LauncherComponents import Component, SuffixIdentifier, Type, components, launch as launch_component

from .rom import patch as rom_patch

DATA_FILE = "pokemon_xy.json"
CONNECTOR_NAME = "pokemon_xy_connector.lua"


class PokemonXYPatch(APAutoPatchInterface):
    game = "Pokemon X and Y"
    patch_file_ending = ".apxy"
    result_file_ending = ".txt"

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.data: Dict[str, Any] = {}

    def write_contents(self, opened_zipfile) -> None:
        super().write_contents(opened_zipfile)
        opened_zipfile.writestr(DATA_FILE, json.dumps(self.data))

    def read_contents(self, opened_zipfile) -> Dict[str, Any]:
        manifest = super().read_contents(opened_zipfile)
        self.data = json.loads(opened_zipfile.read(DATA_FILE))
        return manifest

    def patch(self, target: str) -> None:
        """Appelé par Patch.py : installe le patch du jeu et écrit un petit fichier de compte rendu."""
        self.read()
        rom_path, emuhawk_path = _patch_paths()
        changed = install_patch_data(self.data, rom_path, emuhawk_path)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("Patch Pokémon X/Y installé" + (" (nouveau)" if changed else " (déjà à jour)") + ".\n"
                         "Ouvre ton dump de Pokémon Y dans BizHawk, charge pokemon_xy_connector.lua, puis le client.\n")


def _patch_paths():
    """(dump du joueur, EmuHawk.exe) depuis host.yaml ; Archipelago ouvre une fenêtre si l'un manque."""
    import settings
    host = settings.get_settings()
    return str(host.pokemon_xy_settings.rom_file), str(host.bizhawkclient_options.emuhawk_path)


def install_patch_data(data: Dict[str, Any], rom_path: str, emuhawk_path: str) -> bool:
    """Construit les fichiers du patch et les écrit dans le dossier de mods de BizHawk."""
    items = {int(index): int(item) for index, item in data.get("item_balls", {}).items()}
    files = rom_patch.build_mod_files(rom_path, items, data)
    stamp = {"seed": data.get("seed_name"), "slot": data.get("slot"), "patched_item_balls": len(items),
             "from_patch_file": True}
    return rom_patch.write_mod(rom_patch.mods_directory(emuhawk_path), files, stamp)


def launch_from_patch(*args: str) -> None:
    """Composant du Launcher : patch du jeu, BizHawk avec le script de la partie, puis le client."""
    from Utils import local_path, messagebox
    patch_path = next((arg for arg in args if arg.lower().endswith(PokemonXYPatch.patch_file_ending)), None)
    try:
        if patch_path is None:
            raise ValueError("Aucun fichier .apxy fourni.")
        patch = PokemonXYPatch(patch_path)
        patch.read()
        rom_path, emuhawk_path = _patch_paths()
        install_patch_data(patch.data, rom_path, emuhawk_path)
        connector = local_path("data", "lua", CONNECTOR_NAME)
        if not _exists(connector):
            raise FileNotFoundError(f"{CONNECTOR_NAME} est introuvable dans {local_path('data', 'lua')} : copie-le "
                                    f"depuis le zip du projet.")
        subprocess.Popen([emuhawk_path, f"--lua={connector}", rom_path], cwd=local_path("."),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as error:
        messagebox("Pokémon X/Y : patch impossible", str(error), True)
        return
    from worlds._bizhawk.context import launch as launch_bizhawk_client
    launch_bizhawk_client()


def _exists(path: str) -> bool:
    import os
    return os.path.isfile(path)


def launch_patch_component(*args: str) -> None:
    launch_component(launch_from_patch, name="PokemonXYPatchClient", args=args)


components.append(Component(
    "Pokemon X/Y Patch Client", func=launch_patch_component, component_type=Type.CLIENT, cli=True,
    file_identifier=SuffixIdentifier(PokemonXYPatch.patch_file_ending), game_name="Pokemon X and Y",
    description="Applies a Pokemon X/Y patch file (.apxy), then starts BizHawk and the client."))


def read_stamp(mod_dir: str) -> Optional[dict]:
    return rom_patch.read_stamp(mod_dir)
