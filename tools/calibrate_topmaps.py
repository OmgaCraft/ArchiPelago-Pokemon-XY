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


def _box_sums(mask, h, w):
    """Somme du masque dans chaque fenêtre h x w (image intégrale)."""
    ii = np.pad(mask.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]


def detect(path, threshold=0.30, limit=30):
    """Icônes de Poké Ball d'une carte, à plusieurs échelles (les cartes n'ont pas toutes la même taille).
    Pré-filtre par couleur (rouge au-dessus, blanc en dessous), puis comparaison avec les modèles."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    red = (R > 140) & (G < 120) & (B < 120) & (R - G > 70)
    white = np.minimum(np.minimum(R, G), B) > 180
    found = []  # (score, x, y, largeur de l'icône)
    for factor in (0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7):
        w, h = round(12 * factor), round(10 * factor)
        if a.shape[0] < h or a.shape[1] < w:
            continue
        top, bottom = max(1, round(h * 0.25)), max(2, round(h * 0.55))
        red_top = _box_sums(red, bottom - top, w)[top:top + a.shape[0] - h + 1]
        white_bottom = _box_sums(white, h - bottom - 1, w)[bottom:bottom + a.shape[0] - h + 1]
        ys, xs = np.where((red_top >= 0.15 * (bottom - top) * w) & (white_bottom >= 0.15 * (h - bottom - 1) * w))
        if len(ys) == 0:
            continue
        yy, xx = np.mgrid[0:h, 0:w]
        mask = (((yy - (h - 1) / 2) / (h * 0.43)) ** 2 + ((xx - (w - 1) / 2) / (w * 0.44)) ** 2) <= 1.0
        best = None
        for template in TEMPLATES:
            resized = np.asarray(Image.fromarray(template.astype("uint8")).resize((w, h), Image.BICUBIC)).astype(np.float32)
            scores = np.empty(len(ys), np.float32)
            for i, (y, x) in enumerate(zip(ys, xs)):
                diff = np.abs(a[y:y + h, x:x + w] - resized).sum(axis=2)
                scores[i] = 1 - ((diff < 120) & mask).sum() / mask.sum()
            best = scores if best is None else np.minimum(best, scores)
        for score, y, x in zip(best, ys, xs):
            if score <= threshold:
                found.append((float(score), x + w / 2, y + h / 2, w))
    found.sort()
    kept = []
    for sc, x, y, w in found:
        if all(abs(x - kx) > w * 0.7 or abs(y - ky) > w * 0.7 for _s, kx, ky, _w in kept):
            kept.append((sc, x, y, w))
    return sorted((round(x), round(y)) for _s, x, y, _w in kept[:limit])


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
        candidates = [f"{group}.png"] if f"{group}.png" in images else             [f"{n}.png" for n in bt.images_for(group) if f"{n}.png" in images]
        if not candidates:
            continue
        for zone, points in zones.items():
            if len(points) < 2:
                continue
            best = (0, None, None)
            for image in candidates:
                count, params = fit(points, images[image])
                if params and count > best[0]:
                    best = (count, image, params)
            count, image, params = best
            solid = count >= 3 or (count == 2 and len(points) == 2 and len(candidates) == 1
                                   and len(images.get(image, [])) == 2)
            if not (solid and count >= len(points) - 2) and len(points) >= 3:
                # Cartes un peu déformées (falaises, relief) : tolérance plus large, mais presque tous les objets
                # doivent concorder (la carte est connue par son nom, pas devinée).
                for image_name in candidates:
                    loose, loose_params = fit(points, images[image_name], tol=14.0, ratio=0.35)
                    if loose_params and loose >= max(3, round(len(points) * 0.8)) and loose > count:
                        count, image, params, solid = loose, image_name, loose_params, True
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
