"""
[FR] Cale les positions de la ROM (tools/assets/ball_positions.json) sur les cartes vues du dessus
de Poképédia (tools/assets/topmaps/, voir fetch_topdown_maps.py).

Ces cartes dessinent chaque Poké Ball au sol. On détecte ces icônes, puis, pour chaque zone du jeu,
on cherche la transformation (échelle x/y + décalage) qui fait tomber les objets de la ROM sur les
icônes. Une zone n'est retenue que si au moins 3 objets concordent (ou les 2 d'une zone qui n'en a
que 2). Sortie : tools/assets/topmap_calibration.json (des nombres seulement, versionnable).

Usage : py -3.13 tools/calibrate_topmaps.py
"""
import collections
import itertools
import json
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MAPS = os.path.join(HERE, "assets", "topmaps")
sys.path.insert(0, HERE)
import build_tracker as bt  # noqa: E402

# Modèles d'icône (10 x 12 px) pris sur Route 9 : une balle posée sur deux fonds différents.
_REF = np.asarray(Image.open(os.path.join(MAPS, "Route 9.png")).convert("RGB")).astype(float)
TEMPLATES = [_REF[127:137, 488:500], _REF[180:190, 629:641]]
_yy, _xx = np.mgrid[0:10, 0:12]
MASK = (((_yy - 4.5) / 4.3) ** 2 + ((_xx - 5.5) / 5.3) ** 2) <= 1.0


INDOOR = ("Cave", "Cavern", "Factory", "Gym", "Lab", "Power", "Palace", "Tower", "Dungeon", "Chamber",
          "Road", "League", "Area")


def detect(path, threshold=0.30):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    if a.shape[0] < 10 or a.shape[1] < 12:
        return []
    windows = swv(a, (10, 12, 3))[:, :, 0]
    score = None
    for template in TEMPLATES:
        diff = np.abs(windows - template).sum(axis=4)
        part = 1 - ((diff < 120) & MASK).sum(axis=(2, 3)) / MASK.sum()
        score = part if score is None else np.minimum(score, part)
    points = []
    for y, x in np.dstack(np.unravel_index(np.argsort(score, axis=None), score.shape))[0]:
        if score[y, x] > threshold:
            break
        if all(abs(y - py) > 6 or abs(x - px) > 6 for py, px in points):
            points.append((int(y), int(x)))
    return sorted((x + 6, y + 5) for y, x in points)


def fit(points, icons, tol=6.0, smin=3.0, smax=14.0, ratio=0.18):
    """Meilleure transformation (sx, sy, tx, ty) de [(n, x, y)] vers les icônes : (accords, paramètres)."""
    best = (0, None)
    for (_, x1, y1), (_, x2, y2) in itertools.combinations(points, 2):
        if x1 == x2 or y1 == y2:
            continue
        for a, b in itertools.permutations(icons, 2):
            sx, sy = (b[0] - a[0]) / (x2 - x1), (b[1] - a[1]) / (y2 - y1)
            if not (smin <= sx <= smax and smin <= sy <= smax and abs(sx / sy - 1) < ratio):
                continue
            tx, ty = a[0] - sx * x1, a[1] - sy * y1
            used, count, err = set(), 0, 0.0
            for _n, x, y in points:
                d, i = min((np.hypot(sx * x + tx - c[0], sy * y + ty - c[1]), i) for i, c in enumerate(icons))
                if d <= tol and i not in used:
                    used.add(i)
                    count += 1
                    err += d
            if count > best[0] or (count == best[0] and best[1] and err < best[1][4]):
                best = (count, (sx, sy, tx, ty, err))
    return best


def main():
    _items, locations, _regions, _version = bt.load_world()
    raw = json.load(open(os.path.join(HERE, "assets", "ball_positions.json"), encoding="utf-8"))
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for name, data in locations.location_table.items():
        key = str((data.flag_id or 0) - bt.FIELD_ITEM_FLAG)
        if data.flag_id is not None and "FIELD ITEM" in data.category and key in raw:
            groups[name.split(" - ")[0]][raw[key]["zone"]].append((int(key), raw[key]["x"], raw[key]["y"]))
    images = {f: detect(os.path.join(MAPS, f)) for f in sorted(os.listdir(MAPS)) if f.endswith(".png")}
    result = {}
    for group, zones in sorted(groups.items()):
        if f"{group}.png" in images:
            candidates = [f"{group}.png"]
        elif any(word in group for word in INDOOR):  # souterrains, bâtiments : pas de carte extérieure
            continue
        else:
            candidates = sorted(images)
        for zone, points in zones.items():
            if len(points) < 2:
                continue
            best = (0, None, None)
            for image in candidates:
                count, params = fit(points, images[image])
                if params and count > best[0]:
                    best = (count, image, params)
            count, image, params = best
            solid = count >= 3 or (count == 2 and len(points) == 2 and len(images.get(image, [])) == 2)
            if solid and count >= len(points) - 2:
                entry = result.setdefault(group, {"image": image, "zones": {}})
                if entry["image"] == image:
                    entry["zones"][str(zone)] = [round(v, 3) for v in params[:4]]
                    print(f"{group}: zone {zone} -> {image} ({count}/{len(points)})".encode("ascii", "replace").decode())
    target = os.path.join(HERE, "assets", "topmap_calibration.json")
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    print(len(result), "lieux calés ->", target)


if __name__ == "__main__":
    main()
