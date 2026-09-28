"""
[FR] Test : BizHawk (Encore) charge-t-il un dossier de mods LayeredFS ?

Remplace le texte « Play Pokémon Y in » de l'écran de choix de langue (a/0/7/4,
fichier 85, ligne 5) par « ARCHIPELAGO TEST in ». Visible dès le démarrage tant
qu'aucune sauvegarde n'existe.

Usage :
    py -3.13 tools/layeredfs_test.py <dump .3ds> <EmuHawk.exe> install
    py -3.13 tools/layeredfs_test.py <dump .3ds> <EmuHawk.exe> remove
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worlds", "pokemon_xy"))

from rom.garc import GARC  # noqa: E402
from rom.patch import mods_directory  # noqa: E402
from rom.romfs import RomFS  # noqa: E402
from rom.text import TextFile  # noqa: E402

TEXT_GARC = "a/0/7/4"
TEXT_FILE = 85
TEXT_LINE = 5
EXPECTED = "Play Pokémon Y in"
REPLACEMENT = "ARCHIPELAGO TEST in"


def main():
    rom_path, emuhawk, action = sys.argv[1:4]
    mod_dir = mods_directory(emuhawk)
    target = os.path.join(mod_dir, "romfs", *TEXT_GARC.split("/"))
    if action == "remove":
        if os.path.isdir(mod_dir):
            shutil.rmtree(mod_dir)
        print(f"Supprimé : {mod_dir}")
        return
    with open(rom_path, "rb") as handle:
        garc = GARC(RomFS(handle).read_file(TEXT_GARC))
    text = TextFile(garc.get(TEXT_FILE))
    if text.get_plain(TEXT_LINE) != EXPECTED:
        sys.exit(f"Texte inattendu : {text.get_plain(TEXT_LINE)!r}")
    text.set_plain(TEXT_LINE, REPLACEMENT)
    garc.set(TEXT_FILE, text.build())
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as handle:
        handle.write(garc.build())
    print(f"Écrit : {target}")


if __name__ == "__main__":
    main()
