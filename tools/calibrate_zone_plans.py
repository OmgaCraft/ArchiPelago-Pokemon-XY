"""
[FR] Cale les plans de zone fournis (tools/assets/pack/zones/z<zone>.png : terrain lu dans la ROM, un point gris
par personnage) sur les coordonnées de la ROM : cherche l'échelle (pixels par case) et le décalage qui posent
les points gris sur les personnages de la zone (a/0/1/2). Écrit tools/assets/zone_plan_calibration.json
{zone: [image, sx, sy, tx, ty, points reconnus]} avec x_px = sx*x + tx et y_px = sy*y + ty.

Usage : py -3.13 tools/calibrate_zone_plans.py "<dump.3ds>"
"""
import collections, json, os, struct, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "worlds", "pokemon_xy"))
from rom.romfs import RomFS  # noqa: E402
from rom.garc import GARC  # noqa: E402
from rom import lz11  # noqa: E402

DOT = (111, 112, 109)
GYM_ZONES = {56, 160, 175, 191, 203, 215, 226}   # peu de personnages dessinés : 2 points suffisent


def dots(path):
    pic = np.array(Image.open(path).convert("RGB")).astype(int)
    mask = (np.abs(pic - np.array(DOT)).sum(axis=2) < 18)
    seen, out = np.zeros(mask.shape, bool), []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        stack, cells = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            cells.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if 12 <= len(cells) <= 400:
            ys, xs = zip(*cells)
            out.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    return out


def npcs(zones, z):
    d = lz11.decompress(zones.files[z][0])
    n = struct.unpack_from("<H", d, 2)[0]
    o = struct.unpack_from("<%dI" % (n + 1), d, 4)
    s = d[o[1]:o[2]]
    nf, nn = s[4], s[5]
    p = 12 + 0x14 * nf
    out = []
    for _ in range(nn):
        e = s[p:p + 0x30]; p += 0x30
        x, y = struct.unpack_from("<HH", e, 0x28)
        if x < 1500 and y < 1500:
            out.append((x, y))
    return out


def fit(points, spots):
    best = None
    for scale in range(4, 41):
        votes = collections.Counter()
        for px, py in spots:
            for x, y in points:
                votes[(round(px - scale * (x + 0.5)), round(py - scale * (y + 0.5)))] += 1
        for (tx, ty), n in votes.most_common(3):
            hits = sum(1 for px, py in spots for x, y in points
                       if abs(px - scale * (x + 0.5) - tx) < scale / 3 and abs(py - scale * (y + 0.5) - ty) < scale / 3)
            if best is None or hits > best[0] or (hits == best[0] and scale > best[1]):
                best = (hits, scale, tx, ty)
    return best


def main(path):
    zones = GARC(RomFS(open(path, "rb")).read_file("a/0/1/2"))
    out = {}
    pack = os.path.join(HERE, "assets", "pack", "zones")
    for name in sorted(os.listdir(pack)):
        if not (name.startswith("z") and name[1:4].isdigit()):
            continue
        z = int(name[1:4])
        spots = dots(os.path.join(pack, name))
        if len(spots) < 2:
            print(name, "points :", len(spots), "-> ignoré")
            continue
        hits, scale, tx, ty = fit(npcs(zones, z), spots)
        ok = (hits >= 3 or (hits == 2 and z in GYM_ZONES)) and hits >= len(spots) * 0.6
        print(name, "points", len(spots), "reconnus", hits, "échelle", scale, "OK" if ok else "rejeté")
        if ok:
            out[str(z)] = [name, scale, scale, tx + scale / 2, ty + scale / 2, hits]
    with open(os.path.join(HERE, "assets", "zone_plan_calibration.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle)


if __name__ == "__main__":
    main(sys.argv[1])
