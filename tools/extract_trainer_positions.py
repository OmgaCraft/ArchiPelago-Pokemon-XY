"""
[FR] Extrait de la ROM la position (zone, X, Y) des dresseurs qui ont un check.

Règle vérifiée sur Pokémon Y USA : le personnage d'une zone (a/0/1/2, même format que pour les Poké Balls,
voir extract_ball_positions.py) dont le mot en 0x0A vaut 1260 + le drapeau « dresseur battu » du check
est ce dresseur (225 des 254 dresseurs du monde sont retrouvés, toujours dans la zone attendue : arène de
Santalune = zone 56, de Cyllage = 160, etc.).

Usage : py -3.13 tools/extract_trainer_positions.py "<dump.3ds>"   ->  tools/assets/trainer_positions.json
Le JSON ne contient que des coordonnées {drapeau: {zone, x, y}}, il peut être versionné.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "worlds", "pokemon_xy"))
from rom.romfs import RomFS  # noqa: E402
from rom.garc import GARC  # noqa: E402
from rom import lz11  # noqa: E402

TRAINER_SCRIPT_OFFSET = 1260   # script du personnage = drapeau du check + 1260


def main(path):
    rom = RomFS(open(path, "rb"))
    zones = GARC(rom.read_file("a/0/1/2"))
    by_script = {}
    for z in range(360):
        d = lz11.decompress(zones.files[z][0])
        n = struct.unpack_from("<H", d, 2)[0]
        o = struct.unpack_from("<%dI" % (n + 1), d, 4)
        s = d[o[1]:o[2]]
        nf, nn = s[4], s[5]
        p = 12 + 0x14 * nf
        for _ in range(nn):
            e = s[p:p + 0x30]; p += 0x30
            script = struct.unpack_from("<H", e, 10)[0]
            if 3000 <= script < 4000:
                x, y = struct.unpack_from("<HH", e, 0x28)
                by_script[script] = {"zone": z, "x": x, "y": y}
    out = {str(script - TRAINER_SCRIPT_OFFSET): v for script, v in sorted(by_script.items())}
    target = os.path.join(HERE, "assets", "trainer_positions.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print(len(out), "dresseurs ->", target)


if __name__ == "__main__":
    main(sys.argv[1])
