"""
[FR] Extrait de la ROM la position (zone, X, Y) de chacune des 207 Poké Balls au sol.

Format (vérifié sur Pokémon Y USA) : a/0/1/2 = GARC de 361 entrées ; les 360 premières sont des
fichiers de zone compressés LZ11 (conteneur "ZO"), la dernière (360) est la table des zones
(0x38 octets par zone, non utilisée ici). La section 1 du
conteneur liste meubles (0x14 octets) puis personnages (0x30 octets) ; un personnage dont le mot
en 0x0A vaut 7000+n est la Poké Ball n, sa position est en 0x28 (X) et 0x2A (Y).

Usage : py -3.13 tools/extract_ball_positions.py "<dump.3ds>"   ->  tools/assets/ball_positions.json
Le JSON ne contient que des coordonnées (aucune donnée du jeu), il peut être versionné.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "worlds", "pokemon_xy"))
from rom.romfs import RomFS  # noqa: E402
from rom.garc import GARC  # noqa: E402
from rom import lz11  # noqa: E402


def main(path):
    rom = RomFS(open(path, "rb"))
    zones = GARC(rom.read_file("a/0/1/2"))
    out, sizes = {}, {}
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
            if 7000 <= script < 7207:
                x, y = struct.unpack_from("<HH", e, 0x28)
                out[script - 7000] = {"zone": z, "x": x, "y": y}
    assert len(out) == 207, len(out)
    target = os.path.join(HERE, "assets", "ball_positions.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump({str(k): out[k] for k in sorted(out)}, f, ensure_ascii=False, indent=0)
    print(len(out), "balles dans", len({v["zone"] for v in out.values()}), "zones ->", target)


if __name__ == "__main__":
    main(sys.argv[1])
