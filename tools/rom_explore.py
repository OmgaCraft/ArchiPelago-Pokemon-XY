"""
[FR] Exploration de la RomFS de Pokémon X/Y (lecture seule).

Usage :
    py -3.13 tools/rom_explore.py <chemin du dump .3ds> items      # fichiers des noms d'objets
    py -3.13 tools/rom_explore.py <chemin du dump .3ds> find "texte"  # cherche un texte dans les GARC de texte
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worlds", "pokemon_xy"))

from rom.garc import GARC  # noqa: E402
from rom.romfs import RomFS  # noqa: E402
from rom.text import TextFile  # noqa: E402

# Ordre des archives de texte (déduit des unités de poids affichées) : 2 = japonais kana,
# 3 = japonais kanji, 4 = anglais, 5 = français, 6 = italien, 7 = allemand, 8 = espagnol, 9 = coréen.
GAME_TEXT_GARCS = [f"a/0/7/{n}" for n in range(2, 10)]
STORY_TEXT_GARCS = [f"a/0/8/{n}" for n in range(0, 8)]


def text_files(rom, path):
    garc = GARC(rom.read_file(path))
    for index in range(len(garc)):
        try:
            yield index, TextFile(garc.get(index))
        except Exception:
            continue


def cmd_items(rom):
    english = dict(text_files(rom, "a/0/7/4"))
    found = [i for i, t in english.items() if len(t.lines) > 700 and t.get_plain(17) == "Potion"]
    print("fichier(s) des noms d'objets (anglais) :", found)
    for index in found:
        for path in GAME_TEXT_GARCS:
            text = dict(text_files(rom, path))[index]
            sample = [text.get_plain(i) for i in (0, 3, 4, 17, 112, 422, 651, 700)]
            print(path, "fichier", index, "lignes", len(text.lines), sample)
        unused = [i for i in range(len(english[index].lines)) if english[index].get_plain(i) in ("", "???", "---")]
        print("lignes vides ou « ??? » (anglais) :", unused)


def cmd_find(rom, needle):
    for path in GAME_TEXT_GARCS + STORY_TEXT_GARCS:
        for index, text in text_files(rom, path):
            for line in range(len(text.lines)):
                plain = text.get_plain(line)
                if needle.lower() in plain.lower():
                    print(path, "fichier", index, "ligne", line, repr(plain[:100]))


def main():
    rom = RomFS(open(sys.argv[1], "rb"))
    if sys.argv[2] == "items":
        cmd_items(rom)
    elif sys.argv[2] == "find":
        cmd_find(rom, sys.argv[3])


if __name__ == "__main__":
    main()
