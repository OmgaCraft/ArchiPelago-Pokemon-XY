"""
[FR] Génère le pack PopTracker de Pokémon X/Y depuis les données du monde.

Les checks, objets, régions et règles viennent de worlds/pokemon_xy (Locations.py, Items.py,
Regions.py) : le pack reste donc synchronisé avec l'APWorld. Rien n'est écrit à la main, sauf
les règles d'accès, qui reprennent celles de Rules.py (voir REGION_REQUIREMENTS et ci-dessous).

Usage :
    py -3.13 tools/build_tracker.py          # tracker/ (sources du pack) + dist/Pokemon_XY_Tracker.zip

Structure du pack, carte de Kalos et positions des zones (tools/assets/) : pack MIT de darkfire006
(xy-manual-ap-tracker), prévu pour un autre monde.
"""

import importlib
import json
import math
import os
import re
import shutil
import sys
import types
import unicodedata
import zipfile
from collections import OrderedDict

from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD_DIR = os.path.join(PROJECT_DIR, "worlds", "pokemon_xy")
TRACKER_DIR = os.path.join(PROJECT_DIR, "tracker")          # sources du pack PopTracker
PUBLIC_DIR = TRACKER_DIR
USE_ZONES = False
STATIC_SCRIPTS = ("scripts/init.lua", "scripts/logic.lua", "scripts/autotracking/archipelago.lua")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
GAME_NAME = "Pokemon X and Y"
ASSETS_DIR = os.path.join(PROJECT_DIR, "tools", "assets")
KALOS_MAP = "kalos_map.png"          # carte et positions des zones : darkfire006 (MIT), voir assets/
MAP_PIN = 16                          # taille d'un repère sur la carte de Kalos
MAP_PITCH = 19

# Zones de nos checks qui n'ont pas le même nom sur la carte de référence.
AREA_ALIASES = {
    "Route 16": "Route 16 (West)", "Dendemille Town": "Dendimille Town", "Power Plant": "Kalos Power Plant",
    "Lysandre Lab": "Lysandre Labs", "Ambrette Gate": "Ambrette Town", "Coumarine Gate": "Coumarine City",
    "Shabboneau Castle": "Camphrier Town", "Kiloude City": "Pokemon League",
    "Lumiose City (South Boulevard)": "Lumiose City (South)", "Lumiose City (Lysandre Cafe)": "Lumiose City (South)",
    "Lumiose City (Gym 2F)": "Lumiose City (North)", "Lumiose City (Gym 3F)": "Lumiose City (North)",
    "Lumiose City (Gym 4F)": "Lumiose City (North)", "Lumiose City (Gym 5F)": "Lumiose City (North)",
}


# ---------------------------------------------------------------------------
# Chargement des données du monde, sans Archipelago (BaseClasses est simulé)
# ---------------------------------------------------------------------------

def load_world():
    fake = types.ModuleType("BaseClasses")
    for name in ("Location", "Region", "Entrance"):
        setattr(fake, name, type(name, (), {"__init__": lambda self, *a, **k: None}))
    sys.modules["BaseClasses"] = fake
    package = types.ModuleType("pokemon_xy")
    package.__path__ = [WORLD_DIR]
    sys.modules["pokemon_xy"] = package
    items = importlib.import_module("pokemon_xy.Items")
    locations = importlib.import_module("pokemon_xy.Locations")
    regions = importlib.import_module("pokemon_xy.Regions")
    with open(os.path.join(WORLD_DIR, "archipelago.json"), encoding="utf-8") as handle:
        version = json.load(handle)["world_version"]
    return items, locations, regions, version


# Régions dans l'ordre de progression (Regions.py), avec ce qu'il faut pour y entrer en plus
# de la région précédente (Rules.py, set_rules). Les exigences s'additionnent.
REGION_ORDER = ["Santalune Area", "Camphrier Area", "Cyllage Area", "Shalour Area", "Coumarine Area",
                "Lumiose Area", "Laverre Area", "Anistar Area", "Snowbelle Area", "Victory Road"]
REGION_REQUIREMENTS = {
    "Santalune Area": [],
    "Camphrier Area": ["Bug_Badge"],
    "Cyllage Area": ["Poke_Flute"],
    "Shalour Area": ["Cliff_Badge"],
    "Coumarine Area": ["Rumble_Badge", "HM03_Surf"],
    "Lumiose Area": ["Plant_Badge"],
    "Laverre Area": ["Voltage_Badge", "Power_Plant_Pass"],
    "Anistar Area": ["Fairy_Badge"],
    "Snowbelle Area": ["Psychic_Badge", "Elevator_Key"],
    "Victory Road": ["Iceberg_Badge"],
}
# Exigences propres à un lieu (Rules.py, boucle « HMs require HM item + Badge Count »).
LOCATION_REQUIREMENTS = [
    ("HM01 Cut", ["HM01_Cut", "$badges|1"]),
    ("HM03 Surf", ["HM03_Surf", "$badges|3"]),
    ("HM04 Strength", ["HM04_Strength", "$badges|2"]),
    ("HM05 Waterfall", ["HM05_Waterfall", "$badges|8"]),
    ("TM94 Rock Smash", ["TM94_Rock_Smash"]),
    ("Roller Skates", ["Roller_Skates"]),
]
GYM_COLORS = {"Bug Badge": "#7fb800", "Cliff Badge": "#a0522d", "Rumble Badge": "#c0392b",
              "Plant Badge": "#2e9e4f", "Voltage Badge": "#f1c40f", "Fairy Badge": "#f48fb1",
              "Psychic Badge": "#9b59b6", "Iceberg Badge": "#4fc3f7"}
CATEGORY_STYLE = OrderedDict([  # catégorie -> (code d'image, couleur, libellé)
    ("FIELD ITEM", ("field", "#3b82f6", "Objet au sol")),
    ("HIDDEN ITEM", ("hidden", "#a855f7", "Objet caché")),
    ("ITEM GIFT", ("gift", "#22c55e", "Cadeau")),
    ("TRAINER", ("trainer", "#f97316", "Dresseur")),
    ("Badge", ("badge", "#facc15", "Badge")),
    ("Goal", ("badge", "#facc15", "Objectif")),
])
# Badge -> arène où le chef se trouve (le badge est aussi placé sur le plan de l'arène).
BADGE_GYM = {"Bug Badge": "Santalune City (Gym)", "Cliff Badge": "Cyllage City (Gym)",
             "Rumble Badge": "Shalour City (Gym)", "Plant Badge": "Coumarine City (Gym)",
             "Fairy Badge": "Laverre City (Gym)", "Iceberg Badge": "Snowbelle City (Gym)",
             "Psychic Badge": "Anistar City (Gym)"}
# Arènes dont les dresseurs n'ont pas de position lisible dans la ROM (personnages mobiles) : plan schématique,
# dresseurs dans l'ordre de la liste de Bulbapedia (Coumarine Gym, Anistar Gym), chef et badge en haut.
SCHEMATIC_GYMS = {"Coumarine City (Gym)": ["Chaise", "Maurice", "Brooke", "Twiggy"],
                  "Anistar City (Gym)": ["Paschal", "Harry", "Arthur", "Arachna", "Melanie"]}
FIELD_ITEM_FLAG = 0x051A  # drapeau de la première Poké Ball au sol
# Villes (onglet « Villes ») et lieux rattachés à une ville.
TOWNS = ["Aquacorde Town", "Santalune City", "Camphrier Town", "Cyllage City", "Ambrette Town", "Geosenge Town",
         "Shalour City", "Coumarine City", "Lumiose City", "Laverre City", "Dendemille Town", "Anistar City",
         "Couriway Town", "Snowbelle City", "Pokémon Village", "Kiloude City"]
TOWN_PARTS = {"Ambrette Gate": "Ambrette Town", "Coumarine Gate": "Coumarine City",
              "Shabboneau Castle": "Camphrier Town"}
# Sorties de chaque route (Poképédia, fiche de la route) : les villes qu'elle relie.
ROUTE_LINKS = {
    "Route 1": ["Aquacorde Town"], "Route 2": ["Aquacorde Town"], "Route 3": ["Santalune City"],
    "Route 4": ["Santalune City", "Lumiose City"], "Route 5": ["Camphrier Town", "Lumiose City"],
    "Route 6": ["Camphrier Town"], "Route 7": ["Camphrier Town"], "Route 8": ["Cyllage City", "Ambrette Town"],
    "Route 9": ["Ambrette Town"], "Route 10": ["Geosenge Town", "Cyllage City"], "Route 11": ["Geosenge Town"],
    "Route 12": ["Shalour City", "Coumarine City"], "Route 13": ["Coumarine City", "Lumiose City"],
    "Route 14": ["Laverre City", "Lumiose City"], "Route 15": ["Laverre City", "Dendemille Town"],
    "Route 16": ["Lumiose City"], "Route 17": ["Dendemille Town", "Anistar City"],
    "Route 18": ["Anistar City", "Couriway Town"], "Route 19": ["Couriway Town", "Snowbelle City"],
    "Route 20": ["Snowbelle City", "Pokémon Village"], "Route 21": ["Snowbelle City"],
    "Route 22": ["Santalune City"],
}
EXTRA_TOWN_LINKS = {"Kiloude City": ["Victory Road", "Pokémon League"]}  # on y arrive par la Route Victoire
# Cartes vues du dessus (Bulbapedia, voir tools/fetch_topdown_maps.py) : lieux dont le nom diffère.
MAP_ALIASES = {"Power Plant": "Kalos Power Plant", "PokeBall Factory": "Poké Ball Factory",
               "Pokémon League": "Kiloude City"}


def topmap_stems():
    path = os.path.join(ASSETS_DIR, "topmaps")
    return sorted(f[:-4] for f in os.listdir(path) if f.endswith(".png")) if os.path.isdir(path) else []


VICTORY_ROAD = {"Inside 1": "First cave", "Inside 2": "Second cave", "Inside 3": "Third cave", "Inside 4": "Fourth cave",
                "Outside 2": "Second grove", "Entrance": "Gate"}
GYM_TOWNS = ["Santalune", "Cyllage", "Shalour", "Coumarine", "Laverre", "Anistar", "Snowbelle"]


def images_for(group):
    """Noms (sans extension) des cartes possibles pour un groupe de checks : la carte exacte (étage compris) si
    elle existe, sinon toutes celles du lieu (le calage choisit celle qui concorde)."""
    stems = {plain(s): s for s in topmap_stems()}
    named = {}
    for town in GYM_TOWNS:
        named[f"{town} City (Gym)"] = [s for k, s in stems.items() if k.startswith(plain(town + " Gym"))]
    for floors in ("2F", "3F", "4F", "5F"):
        named[f"Lumiose City (Gym {floors})"] = [stems[k] for k in stems if k.startswith(plain("Lumiose Gym 2F"))]
    named["Lumiose City (South Boulevard)"] = [stems[k] for k in stems if k == plain("Lumiose City South Boulevard")]
    for label, part in VICTORY_ROAD.items():
        named[f"Victory Road ({label})"] = [stems[k] for k in stems if k == plain(f"Kalos Victory Road {part}")]
    named["Victory Road"] = [s for k, s in stems.items() if k.startswith(plain("Kalos Victory Road"))]
    if named.get(group):
        return named[group]
    base, floor = group.split(" (")[0], re.search(r"\((.*?)\)", group)
    base = MAP_ALIASES.get(base, base)
    if floor and plain(f"{base} {floor.group(1)}") in stems:
        return [stems[plain(f"{base} {floor.group(1)}")]]
    if floor:  # plusieurs cartes pour le même étage (centre, est...)
        same_floor = [s for k, s in stems.items() if k.startswith(plain(f"{base} {floor.group(1)}"))]
        if same_floor:
            return same_floor
    exact = [stems[k] for k in (plain(base), plain("Kalos " + base)) if k in stems]
    if exact:
        return exact[:1]
    return [s for k, s in stems.items() if k.startswith(plain(base)) and base]


EXTRA_TRACKED_ITEMS = ["HM02 Fly", "Mega Ring"]
SKIPPED_PREFIXES = ("FE_", "TMFLG_", "FLAG_")


def code_of(name):
    return name.replace(" ", "_").replace(".", "").replace("'", "")


def clean(name):
    """Les noms de lieux ne peuvent pas contenir « / » (séparateur des chemins PopTracker)."""
    return name.replace("/", "-")


def font(size):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def plain(text):
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in text if not unicodedata.combining(c)).lower())


def resolve_anchor(group, areas):
    """Position (x, y) de la zone d'un check sur la carte de Kalos, ou None."""
    by_plain = {plain(name): xy for name, xy in areas.items()}
    candidates = [AREA_ALIASES.get(group), group, re.sub(r"\s*\(.*?\)", "", group).strip()]
    for candidate in candidates:
        if candidate and plain(candidate) in by_plain:
            return tuple(by_plain[plain(candidate)])
        if candidate and candidate in AREA_ALIASES and plain(AREA_ALIASES[candidate]) in by_plain:
            return tuple(by_plain[plain(AREA_ALIASES[candidate])])
    return None


def cluster(count, anchor, size):
    """Positions de `count` repères en petit groupe centré sur la zone."""
    cols = max(1, math.ceil(math.sqrt(count * 1.4)))
    rows = math.ceil(count / cols)
    out = []
    for index in range(count):
        row, col = divmod(index, cols)
        x = anchor[0] + (col - (cols - 1) / 2) * MAP_PITCH
        y = anchor[1] + (row - (rows - 1) / 2) * MAP_PITCH
        out.append((int(min(max(x, MAP_PIN), size[0] - MAP_PIN)), int(min(max(y, MAP_PIN), size[1] - MAP_PIN))))
    return out

REGION_CITY = {"Santalune Area": "Santalune City", "Camphrier Area": "Camphrier Town", "Cyllage Area": "Cyllage City",
               "Shalour Area": "Shalour City", "Coumarine Area": "Coumarine City", "Lumiose Area": "Lumiose City (South)",
               "Laverre Area": "Laverre City", "Anistar Area": "Anistar City", "Snowbelle Area": "Snowbelle City",
               "Victory Road": "Pokemon League"}
CROP_SCALE = 2.2                      # agrandissement des cartes de région (pour dimensionner les étiquettes)
LABEL_PX = 15                         # corps du texte des étiquettes sur les cartes de région


def bold(size):
    for path in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def pin_label(group):
    """Texte affiché à côté du repère d'un lieu."""
    return "Divers" if group.endswith(" Area") else group


def _overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0


def layout_pins(by_region, areas, size):
    """Position (x, y, côté de l'étiquette) de chaque lieu sur la carte de Kalos. Les lieux d'une même zone
    sont écartés en colonne autour d'elle, sans se recouvrir ni couvrir les autres zones."""
    measure = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    face = bold(LABEL_PX)
    items = []
    for region, groups in by_region.items():
        for group in groups:
            anchor = resolve_anchor(group, areas) or resolve_anchor(REGION_CITY[region], areas)
            width = measure.textlength(pin_label(group), font=face) / CROP_SCALE + 7
            items.append({"key": (region, group), "group": group, "anchor": anchor, "width": width})
    clusters = OrderedDict()
    for item in items:
        clusters.setdefault(item["anchor"], []).append(item)
    for members in clusters.values():
        plain_first = [m for m in members if "(" not in m["group"] and not m["group"].endswith(" Area")]
        main = min(plain_first or members, key=lambda m: len(m["group"]))
        main["main"] = True
    half, tall = 6.5, 5.5
    obstacles = {a: (a[0] - 7, a[1] - 7, a[0] + 7, a[1] + 7) for a in clusters}
    placed, result = [], {}

    def rects(item, x, y, side):
        label = (x + half + 1, y - tall, x + half + 1 + item["width"], y + tall) if side > 0 else                 (x - half - 1 - item["width"], y - tall, x - half - 1, y + tall)
        return [(x - half, y - half, x + half, y + half), label]

    def place(item, span, step):
        ax, ay = item["anchor"]
        best = None
        for dy in range(-span, span + 1, step):
            for dx in range(-span, span + 1, step):
                for side in (1, -1):
                    x, y = ax + dx, ay + dy
                    cost = abs(dx) * 1.3 + abs(dy) + (0 if side > 0 else 1.5)
                    boxes = rects(item, x, y, side)
                    for box in boxes:
                        if box[0] < 4 or box[1] < 4 or box[2] > size[0] - 4 or box[3] > size[1] - 4:
                            cost += 5000
                        for other in placed:
                            cost += _overlap(box, other) * 40
                        for anchor, hole in obstacles.items():
                            if anchor != item["anchor"]:
                                cost += _overlap(box, hole) * 25
                    if best is None or cost < best[0]:
                        best = (cost, x, y, side, boxes)
        _, x, y, side, boxes = best
        placed.extend(boxes)
        result[item["key"]] = (x, y, side)

    for item in (i for i in items if i.get("main")):
        place(item, 0, 1)
    others = sorted((i for i in items if not i.get("main")), key=lambda i: -len(clusters[i["anchor"]]))
    for item in others:
        place(item, 50, 5)
    return result


def render_world_maps(out_dir, base_path, by_region, pins):
    """Carte de Kalos (noms des villes) et une carte agrandie par région (nom de chaque lieu).
    Renvoie {nom de carte: (fichier, taille d'un repère)} et la position de chaque repère sur chaque carte."""
    base = Image.open(base_path).convert("RGB")
    size = base.size
    placed, files = {}, {}
    # --- carte de Kalos entière : étiquettes jaunes pour les villes
    over = base.copy()
    draw = ImageDraw.Draw(over)
    small = bold(13)
    for (region, group), (x, y, side) in pins.items():
        if group in TOWNS or group in ("Victory Road", "Lumiose City (South)"):
            text = pin_label(group).replace(" Town", "").replace(" City", "").replace(" (South)", "")
            w = draw.textlength(text, font=small)
            box = (x - w / 2 - 6, y + 11, x + w / 2 + 6, y + 29)
            draw.rounded_rectangle(box, 8, fill=(246, 184, 0), outline=(60, 40, 0))
            draw.text((x - w / 2, y + 12), text, font=small, fill=(40, 25, 0))
    over.save(os.path.join(out_dir, "kalos.png"))
    files["Kalos (carte)"] = ("images/maps/kalos.png", 20)
    for region, groups in by_region.items():
        keys = [(region, g) for g in groups]
        if not keys:
            continue
        xs, ys = [], []
        for key in keys:
            x, y, side = pins[key]
            w = ImageDraw.Draw(Image.new("RGB", (4, 4))).textlength(pin_label(key[1]), font=bold(LABEL_PX)) / CROP_SCALE + 14
            xs += [x - 8 - (w if side < 0 else 0), x + 8 + (w if side > 0 else 0)]
            ys += [y - 8, y + 8]
        bw, bh = max(xs) - min(xs) + 60, max(ys) - min(ys) + 60
        cw = min(max(bw, bh * 1.5, 340), size[0])
        ch = cw / 1.5
        left = min(max((min(xs) + max(xs)) / 2 - cw / 2, 0), size[0] - cw)
        top = min(max((min(ys) + max(ys)) / 2 - ch / 2, 0), size[1] - ch)
        scale = 1200 / cw
        crop = base.crop((int(left), int(top), int(left + cw), int(top + ch))).resize((1200, int(ch * scale)), Image.LANCZOS)
        draw = ImageDraw.Draw(crop)
        face = bold(LABEL_PX)
        for key in keys:
            x, y, side = pins[key]
            cx, cy = (x - left) * scale, (y - top) * scale
            placed[(region, key[1])] = (int(cx), int(cy))
            text = pin_label(key[1])
            w = draw.textlength(text, font=face)
            gap = 15 * scale / CROP_SCALE
            if side > 0:
                box = (cx + gap, cy - 12, cx + gap + w + 14, cy + 12)
            else:
                box = (cx - gap - w - 14, cy - 12, cx - gap, cy + 12)
            draw.rounded_rectangle(box, 11, fill=(22, 30, 48), outline=(255, 255, 255))
            draw.text((box[0] + 7, box[1] + 1), text, font=face, fill=(255, 255, 255))
        slug = re.sub(r"[^A-Za-z0-9]+", "_", region).strip("_")
        name = f"images/maps/region_{slug}.jpg"
        crop.save(os.path.join(out_dir, f"region_{slug}.jpg"), quality=88)
        files[f"{region} (carte)"] = (name, 28)
    return files, placed


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def lua_value(value):
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def icon(path, color, text="", shape="square", size=32):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = (2, 2, size - 3, size - 3)
    if shape == "circle":
        draw.ellipse(box, fill=color, outline="#111111", width=2)
    else:
        draw.rounded_rectangle(box, radius=6, fill=color, outline="#111111", width=2)
    if text:
        f = font(13 if len(text) > 2 else 16)
        width = draw.textlength(text, font=f)
        draw.text(((size - width) / 2, size / 2 - 9), text, font=f, fill="#111111")
    image.save(path)


def make_icons(tracked):
    base = os.path.join(TRACKER_DIR, "images")
    for index, (name, code) in enumerate(tracked["badges"], start=1):
        icon(f"{base}/items/{code}.png", GYM_COLORS[name], str(index), "circle")
    short = {"HM01_Cut": "CS1", "HM02_Fly": "CS2", "HM03_Surf": "CS3", "HM04_Strength": "CS4",
             "HM05_Waterfall": "CS5", "TM94_Rock_Smash": "CT94"}
    for name, code in tracked["others"]:
        label = short.get(code, "".join(w[0] for w in name.replace("-", " ").split()[:3]).upper())
        color = "#94a3b8" if code in short else "#e2e8f0"
        icon(f"{base}/items/{code}.png", color, label)
    for key, (code, color, _label) in CATEGORY_STYLE.items():
        icon(f"{base}/checks/{code}.png", color)
    icon(f"{base}/checks/opened.png", "#475569", "✓")
    icon(f"{base}/items/opt_hidden.png", "#a855f7", "Cach")
    icon(f"{base}/items/opt_trainers.png", "#f97316", "Dres")
    icon(f"{base}/items/opt_dowsing.png", "#0ea5e9", "Cherch")


def spread(points, size, gap=22):
    """Écarte les repères trop proches (même case de la grille, quelques pixels d'écart)."""
    pts = [list(p) for p in points]
    for _ in range(40):
        moved = False
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                dist = math.hypot(dx, dy)
                if dist < gap:
                    if dist < 0.01:
                        dx, dy, dist = 1.0, 0.3 * (j - i), 1.04
                    push = (gap - dist) / 2 + 0.5
                    for k, sign in ((i, -1), (j, 1)):
                        pts[k][0] += sign * dx / dist * push
                        pts[k][1] += sign * dy / dist * push
                    moved = True
        for p in pts:
            p[0] = min(max(p[0], gap / 2), size[0] - gap / 2)
            p[1] = min(max(p[1], gap / 2), size[1] - gap / 2)
        if not moved:
            break
    return [(p[0], p[1]) for p in pts]


def plan_layout(entries, positions, size, max_scale=14):
    """Plans de zone : un cadre par zone du jeu, les objets au sol à leur vraie place relative.
    Renvoie [(liste de (nom, x, y) dans le cadre)] ; les objets sans position sont ignorés ici."""
    by_zone = OrderedDict()
    for name in entries:
        if name in positions:
            zone, x, y = positions[name]
            by_zone.setdefault(zone, []).append((name, x, y))
    plans = []
    margin = 14
    for zone, items in by_zone.items():
        xs, ys = [i[1] for i in items], [i[2] for i in items]
        span_x, span_y = max(max(xs) - min(xs), 14), max(max(ys) - min(ys), 14)
        scale = min((size[0] - 2 * margin) / span_x, (size[1] - 2 * margin) / span_y, max_scale)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        pts = [(size[0] / 2 + (x - cx) * scale, size[1] / 2 + (y - cy) * scale) for _n, x, y in items]
        pts = spread(pts, size)
        plans.append([(i[0], px, py) for i, (px, py) in zip(items, pts)])
    return plans


def load_topmaps():
    """Calage des cartes vues du dessus (tools/calibrate_topmaps.py) : {lieu: {zone: [carte, sx, sy, tx, ty]}}."""
    path = os.path.join(ASSETS_DIR, "topmap_calibration.json")
    if not USE_ZONES or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return {g: {z: v for z, v in c["zones"].items() if os.path.exists(os.path.join(ASSETS_DIR, "topmaps", v[0]))}
            for g, c in data.items()}


def fitted_picture(name, width, margin):
    picture = Image.open(os.path.join(ASSETS_DIR, "topmaps", name)).convert("RGB")
    factor = min((width - 2 * margin) / picture.width, 640 / picture.height, 1.6)
    return picture.resize((int(picture.width * factor), int(picture.height * factor)), Image.LANCZOS), factor


def make_group_map(path, group, entries, positions=None, zone_of=None):
    """Image d'un lieu (route, ville, grotte...) : la ou les cartes vues du dessus avec les objets au sol à
    leur place exacte, sinon un plan schématique (positions lues dans la ROM), puis les autres repères en grille.
    Renvoie la position de chaque check dans l'image."""
    positions, zone_of = positions or {}, zone_of or {}
    calib = load_topmaps().get(group) or {}
    gym = "(Gym" in group      # pas de plan vu du dessus des arènes : plan dessiné depuis la ROM
    width, margin, pitch = (640 if gym else 980), 16, 30
    plan_size = (600, 380) if gym else (290, 200)
    y = margin
    placed = OrderedDict()
    pictures = []  # (image, y)
    for name in OrderedDict.fromkeys(v[0] for v in calib.values()):
        picture, factor = fitted_picture(name, width, margin)
        for entry in entries:
            transform = calib.get(str(zone_of.get(entry)))
            if transform and transform[0] == name and entry in positions:
                _n, sx, sy, tx, ty = transform
                px = min(max((sx * positions[entry][1] + tx) * factor, 8), picture.width - 8)
                py = min(max((sy * positions[entry][2] + ty) * factor, 8), picture.height - 8)
                placed[entry] = (int(margin + px), int(y + py))
        pictures.append((picture, y))
        y += picture.height + 10
    if not calib and USE_ZONES and not gym:  # carte(s) sans calage : affichées quand même, les checks restent en dessous
        names = images_for(group)
        for name in (names if len(names) <= 3 else []):
            if os.path.exists(os.path.join(ASSETS_DIR, "topmaps", f"{name}.png")):
                picture, _factor = fitted_picture(f"{name}.png", width, margin)
                pictures.append((picture, y))
                y += picture.height + 10
    plans = plan_layout([e for e in entries if e not in placed], positions, plan_size, 26 if gym else 14)
    # Arène de Lumiose (étages 2 à 5) : les dresseurs ne sont pas dans les données de zone de la ROM. D'après
    # Bulbapedia (Lumiose Gym), chaque étage a 3 dresseurs, un devant chacun des 3 ascenseurs, de gauche à droite.
    elevators, route = [], False
    if group in SCHEMATIC_GYMS and not plans:
        order = SCHEMATIC_GYMS[group]
        fighters = sorted((e for e in entries if not e.endswith("Badge")),
                          key=lambda e: next((i for i, k in enumerate(order) if k in e), 99))
        leader = [e for e in entries if e.endswith("Badge")]
        steps = len(fighters)
        plan = [(name, plan_size[0] * (0.28 if i % 2 == 0 else 0.72), plan_size[1] - 50 - i * (plan_size[1] - 130) / max(steps - 1, 1))
                for i, name in enumerate(fighters)]
        plan += [(name, plan_size[0] / 2, 40) for name in leader]
        plans, route = [plan], True
    if group.startswith("Lumiose City (Gym ") and not plans:
        trainers = [e for e in entries if e not in placed][:3]
        elevators = [plan_size[0] * (k + 1) / (len(trainers) + 1) for k in range(len(trainers))]
        plans = [[(name, elevators[k], 80) for k, name in enumerate(trainers)]]
    per_row = max(1, (width - 2 * margin) // (plan_size[0] + 12))
    frames = []
    for index, plan in enumerate(plans):
        row, col = divmod(index, per_row)
        ox, oy = margin + col * (plan_size[0] + 12), y + row * (plan_size[1] + 12)
        frames.append((ox, oy))
        for name, px, py in plan:
            placed[name] = (int(ox + px), int(oy + py))
    y += ((len(plans) - 1) // per_row + 1) * (plan_size[1] + 12) if plans else 0
    if gym and plans:
        y += 14   # place de la légende
    rest = [e for e in entries if e not in placed]
    columns = max(1, (width - 2 * margin) // pitch)
    for index, entry in enumerate(rest):
        row, col = divmod(index, columns)
        placed[entry] = (margin + col * pitch + pitch // 2, y + row * pitch + pitch // 2)
    y += ((len(rest) - 1) // columns + 1) * pitch if rest else 0
    image = Image.new("RGB", (width, max(y + margin, 120)), "#0f172a")
    draw = ImageDraw.Draw(image)
    for picture, top in pictures:
        image.paste(picture, (margin, top))
    for ox, oy in frames:
        draw.rounded_rectangle((ox, oy, ox + plan_size[0], oy + plan_size[1]), radius=8,
                               fill="#111c33", outline="#334155", width=2)
        for gx in range(ox + 30, ox + plan_size[0], 30):
            draw.line((gx, oy + 4, gx, oy + plan_size[1] - 4), fill="#16233f")
        for gy in range(oy + 30, oy + plan_size[1], 30):
            draw.line((ox + 4, gy, ox + plan_size[0] - 4, gy), fill="#16233f")
    if elevators and frames:
        for number, ex in enumerate(elevators, 1):
            ox, oy = frames[0]
            draw.rounded_rectangle((ox + ex - 38, oy + 12, ox + ex + 38, oy + 52), radius=6, fill="#1e293b", outline="#38bdf8", width=2)
            draw.text((ox + ex - 5, oy + 18), str(number), font=bold(22), fill="#7dd3fc")
        draw.text((frames[0][0] + 4, frames[0][1] + plan_size[1] + 2),
                  "Plan schématique (d'après Bulbapedia) : un dresseur devant chaque ascenseur, de gauche à droite", font=font(12), fill="#94a3b8")
    elif route and frames:
        ox, oy = frames[0]
        draw.text((ox + plan_size[0] / 2 - 22, oy + plan_size[1] - 22), "Entrée", font=font(13), fill="#94a3b8")
        draw.text((frames[0][0] + 4, frames[0][1] + plan_size[1] + 2),
                  "Plan schématique : dresseurs dans l'ordre de Bulbapedia (positions exactes inconnues), chef et badge en haut",
                  font=font(12), fill="#94a3b8")
    elif gym and frames:
        draw.text((frames[0][0] + 4, frames[0][1] + plan_size[1] + 2),
                  "Plan de l'arène : positions des dresseurs lues dans la ROM (haut = nord)", font=font(12), fill="#94a3b8")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, quality=82, optimize=True)
    return placed


def town_of(group):
    """Ville à laquelle appartient un lieu (« Santalune City (Gym) » -> Santalune City), ou None."""
    base = re.sub(r"\s*\(.*?\)", "", group).strip()
    base = TOWN_PARTS.get(base, base)
    return base if base in TOWNS else None


def map_tab(title, group):
    return {"title": title, "content": {"type": "map", "maps": [f"Lieu : {group}"]}}


def navigation(group_region):
    """Onglets : Kalos (carte entière), Régions (carte agrandie de chaque région), Arènes, Villes (chaque ville
    puis les routes qui y mènent), Routes, Grottes et lieux."""
    groups = list(group_region)
    routes = {g for g in groups if g.startswith("Route ")}
    gyms = sorted((g for g in groups if "(Gym" in g), key=lambda g: (REGION_ORDER.index(group_region[g]), g))
    regions = [{"title": r.replace(" Area", ""), "content": {"type": "map", "maps": [f"{r} (carte)"]}}
               for r in REGION_ORDER if any(group_region[g] == r for g in groups)]
    villes = []
    for town in sorted(TOWNS, key=lambda t: min((REGION_ORDER.index(group_region[g]) for g in groups
                                                  if town_of(g) == t), default=99)):
        own = [g for g in groups if town_of(g) == town]
        if not own:
            continue
        subs = []
        for group in own:
            label = re.search(r"\((.*?)\)", group)
            subs.append(map_tab(label.group(1) if label else ("Ville" if group == town else group), group))
        linked = [r for r in sorted(routes, key=lambda r: int(r.split()[1])) if town in ROUTE_LINKS.get(r.split(" (")[0], [])]
        linked += [g for g in groups if g not in routes and g.split(" (")[0] in EXTRA_TOWN_LINKS.get(town, [])]
        subs += [map_tab(g, g) for g in linked]
        villes.append({"title": town.replace(" Town", "").replace(" City", ""),
                       "content": {"type": "tabbed", "tabs": subs}})

    def sort_route(group):
        number = re.search(r"\d+", group)
        return (int(number.group()) if number else 0, group)

    other = [g for g in groups if g not in routes and g not in gyms and town_of(g) is None]

    def family(group):
        base = re.sub(r"\s*\(.*?\)", "", group).strip()
        return MAP_ALIASES.get(base, base)

    def nested(members, title):
        """Sous-menus : une région par onglet, puis une famille (étages, parties) par sous-onglet."""
        out = []
        for region in REGION_ORDER:
            mine = [g for g in members if group_region[g] == region]
            if not mine:
                continue
            families = OrderedDict()
            for g in mine:
                families.setdefault(family(g), []).append(g)
            tabs = []
            for name, parts in families.items():
                if len(parts) == 1:
                    tabs.append(map_tab(title(parts[0]), parts[0]))
                else:
                    subs = []
                    for g in parts:
                        label = re.search(r"\((.*?)\)", g)
                        subs.append(map_tab(label.group(1) if label else "Général", g))
                    tabs.append({"title": name, "content": {"type": "tabbed", "tabs": subs}})
            out.append({"title": region.replace(" Area", ""), "content": {"type": "tabbed", "tabs": tabs}})
        return {"type": "tabbed", "tabs": out}

    return [{"title": "Kalos", "content": {"type": "map", "maps": ["Kalos (carte)"]}},
            {"title": "Régions", "content": {"type": "tabbed", "tabs": regions}},
            {"title": "Arènes", "content": {"type": "tabbed", "tabs": [
                map_tab(re.sub(r"\s*\(Gym\)", "", g).replace(" City", "").replace("(Gym ", "(") if g.endswith("(Gym)")
                        else g.replace("Lumiose City (Gym ", "Lumiose ").rstrip(")"), g) for g in gyms]}},
            {"title": "Villes", "content": {"type": "tabbed", "tabs": villes}},
            {"title": "Routes", "content": nested(sorted(routes, key=sort_route), lambda g: g)},
            {"title": "Grottes & lieux", "content": nested(
                other, lambda g: "Divers" if g.endswith(" Area") else g)}]


# ---------------------------------------------------------------------------
# Construction du pack
# ---------------------------------------------------------------------------

def build(out_dir=None, zones=False):
    global TRACKER_DIR, USE_ZONES
    TRACKER_DIR, USE_ZONES = out_dir or PUBLIC_DIR, zones
    items_mod, locations_mod, regions_mod, version = load_world()
    item_table, location_table = items_mod.item_table, locations_mod.location_table

    # --- objets suivis ---------------------------------------------------
    badges = [(n, code_of(n)) for n, d in item_table.items() if d.category == "Badges"]
    others = [(n, code_of(n)) for n, d in item_table.items()
              if d.category != "Badges" and (d.progression or n in EXTRA_TRACKED_ITEMS)]
    tracked = {"badges": badges, "others": others}
    make_icons(tracked)
    item_json = [{"name": n, "type": "toggle", "img": f"images/items/{c}.png", "codes": c} for n, c in badges + others]
    for code, name in (("opt_hidden", "Objets cachés (option)"), ("opt_trainers", "Dresseurs (option)"),
                       ("opt_dowsing", "Machine Cherch'Objet requise (option)")):
        item_json.append({"name": name, "type": "toggle", "img": f"images/items/{code}.png", "codes": code})
    write_json(f"{TRACKER_DIR}/items/items.json", item_json)

    # --- lieux, regroupés par région puis par zone ------------------------
    by_region = OrderedDict((r, OrderedDict()) for r in REGION_ORDER)
    regions_dict = {r: None for r in REGION_ORDER}
    for name, data in location_table.items():
        if name.startswith(SKIPPED_PREFIXES) or "[Daily]" in name or "[Weekly]" in name or data.flag_id is None:
            continue
        region = regions_mod._resolve_region(name, data, regions_dict)
        group = name.split(" - ", 1)[0] if " - " in name else "Divers"
        by_region[region].setdefault(group, []).append((name, data))

    # Position de chaque objet au sol, lue dans la ROM (tools/extract_ball_positions.py) :
    # la Poké Ball n lève le drapeau FIELD_ITEM_FLAG + n.
    ball_positions, ball_zones = {}, {}
    trainer_raw = json.load(open(os.path.join(ASSETS_DIR, "trainer_positions.json"), encoding="utf-8"))
    leaders = json.load(open(os.path.join(ASSETS_DIR, "leader_positions.json"), encoding="utf-8"))
    extra_pins = {}
    raw = json.load(open(os.path.join(ASSETS_DIR, "ball_positions.json"), encoding="utf-8"))
    for by_group in by_region.values():
        for entries in by_group.values():
            for name, data in entries:
                n = (data.flag_id or 0) - FIELD_ITEM_FLAG
                if "FIELD ITEM" in data.category and str(n) in raw:
                    ball_positions[name] = (raw[str(n)]["zone"], raw[str(n)]["x"], raw[str(n)]["y"])
                    ball_zones[name] = raw[str(n)]["zone"]
                elif "TRAINER" in data.category and str(data.flag_id) in trainer_raw:
                    t = trainer_raw[str(data.flag_id)]
                    ball_positions[name] = (t["zone"], t["x"], t["y"])
                    ball_zones[name] = t["zone"]
    print("objets au sol et dresseurs placés sur un plan :", len(ball_positions))

    cumulative, required = [], {}
    for region in REGION_ORDER:
        cumulative = cumulative + REGION_REQUIREMENTS[region]
        required[region] = list(cumulative)

    areas = json.load(open(os.path.join(ASSETS_DIR, "kalos_areas.json"), encoding="utf-8"))
    kalos_size = Image.open(os.path.join(ASSETS_DIR, KALOS_MAP)).size
    os.makedirs(f"{TRACKER_DIR}/images/maps", exist_ok=True)
    pins = layout_pins(by_region, areas, kalos_size)
    world_maps, on_map = render_world_maps(f"{TRACKER_DIR}/images/maps", os.path.join(ASSETS_DIR, KALOS_MAP),
                                           by_region, pins)
    maps, location_nodes, item_map, location_map = [], [], {}, {}
    for name, (img, pin) in world_maps.items():
        maps.append({"name": name, "location_size": pin, "location_border_thickness": 3, "img": img})
    group_region = OrderedDict()
    for region in REGION_ORDER:
        groups = by_region[region]
        if not groups:
            continue
        placed = {}
        for group, entries in groups.items():
            slug = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", group)).strip("_")
            names = [e[0] for e in entries]
            badge = [n for b, g in BADGE_GYM.items() if g == group and (b in leaders or group in SCHEMATIC_GYMS)
                     for n in location_table if n.endswith(" - " + b)]
            gym_positions = dict(ball_positions)
            for n in badge:   # le badge est aussi posé sur le plan de l'arène, à la place du chef
                if group not in SCHEMATIC_GYMS:
                    lead = leaders[n.split(" - ", 1)[1]]
                    gym_positions[n] = (lead["zone"], lead["x"], lead["y"])
            result = make_group_map(f"{TRACKER_DIR}/images/maps/lieu_{slug}.jpg", group, names + badge,
                                    gym_positions, {**ball_zones, **{n: gym_positions[n][0] for n in badge if n in gym_positions}})
            for n in badge:
                x, y = result.pop(n)
                extra_pins[n] = {"map": f"Lieu : {group}", "x": x, "y": y}
            placed.update(result)
            maps.append({"name": f"Lieu : {group}", "location_size": 24, "location_border_thickness": 3,
                         "img": f"images/maps/lieu_{slug}.jpg"})
            group_region[group] = region
        children = []
        for group, entries in groups.items():
            sections, used = [], set()
            for name, data in entries:
                x, y = placed[name]
                category = next((c for c in CATEGORY_STYLE if c in data.category), "FIELD ITEM")
                rules = list(required[region])
                reqs = data.requires or ""
                for key, parts in LOCATION_REQUIREMENTS:
                    if key in reqs:
                        rules += parts
                visibility = []
                if category == "HIDDEN ITEM":
                    visibility = ["$show_hidden"]
                    rules = rules + ["$dowsing_ok"]
                elif category == "TRAINER":
                    visibility = ["$show_trainers"]
                style = {"chest_unopened_img": f"images/checks/{CATEGORY_STYLE[category][0]}.png",
                         "chest_opened_img": "images/checks/opened.png"}
                node = {
                    "name": clean(name),
                    "map_locations": [{"map": f"Lieu : {group}", "x": x, "y": y}] + ([extra_pins[name]] if name in extra_pins else []),
                    "sections": [dict({"name": "Check", "item_count": 1}, **style)],
                }
                if rules:
                    node["access_rules"] = [",".join(rules)]
                if visibility:
                    node["visibility_rules"] = visibility
                children.append(node)
                path = f"@{region}/{clean(name)}/Check"
                # Section du lieu entier, affichée sur la carte de Kalos et celle de la région.
                label = clean(name.split(" - ", 1)[1] if " - " in name else name)
                while label in used:
                    label += " "
                used.add(label)
                section = dict({"name": label, "item_count": 1}, **style)
                if rules:
                    section["access_rules"] = [",".join(rules)]
                if visibility:
                    section["visibility_rules"] = visibility
                sections.append(section)
                location_map.setdefault(data.code, []).extend([path, f"@{region}/{clean(group)}/{label}"])
            wx, wy = pins[(region, group)][:2]
            children.append({
                "name": clean(group),
                "map_locations": [{"map": "Kalos (carte)", "x": int(wx), "y": int(wy)},
                                  {"map": f"{region} (carte)", "x": on_map[(region, group)][0],
                                   "y": on_map[(region, group)][1]}],
                "sections": sections})
        location_nodes.append({"name": region, "children": children})
    write_json(f"{TRACKER_DIR}/maps/maps.json", maps)
    write_json(f"{TRACKER_DIR}/locations/locations.json", location_nodes)

    for name, code in badges + others:
        item_map[item_table[name].code] = code

    # --- mise en page ------------------------------------------------------
    rows = [[c for _, c in badges],
            [c for n, c in others if n.startswith(("HM", "TM"))],
            [c for n, c in others if not n.startswith(("HM", "TM"))],
            ["opt_hidden", "opt_trainers", "opt_dowsing"]]
    grid = {"type": "itemgrid", "item_margin": "2,2", "h_alignment": "left", "item_h_alignment": "center",
            "item_v_alignment": "center", "item_height": 36, "item_width": 36, "rows": rows}
    tabs = {"tabbed_maps": {"type": "tabbed", "tabs": navigation(group_region)}}
    layout = {"tracker_default": {"type": "container", "background": "#00000000", "content": {
        "type": "dock", "dropshadow": True, "content": [
            {"type": "dock", "dock": "left", "v_alignment": "stretch", "content": [
                {"type": "group", "header": "Objets", "dock": "top", "content": grid}]},
            {"type": "dock", "content": {"type": "layout", "key": "tabbed_maps"}}]}}}
    write_json(f"{TRACKER_DIR}/layouts/tabs.json", tabs)
    write_json(f"{TRACKER_DIR}/layouts/tracker.json", layout)

    # --- manifest et scripts ----------------------------------------------
    write_json(f"{TRACKER_DIR}/manifest.json", {
        "name": "Pokémon X/Y Archipelago Tracker", "game_name": GAME_NAME,
        "package_version": version, "package_uid": "pokemon_xy_archipelago",
        "author": "OmgaCraft", "min_poptracker_version": "0.30.1",
        "variants": {"standard": {"display_name": "Carte par régions", "flags": ["ap"]}}})
    scripts = os.path.join(TRACKER_DIR, "scripts")
    os.makedirs(os.path.join(scripts, "autotracking"), exist_ok=True)
    if TRACKER_DIR != PUBLIC_DIR:  # scripts écrits à la main : copiés depuis le pack public
        for relative in STATIC_SCRIPTS:
            shutil.copyfile(os.path.join(PUBLIC_DIR, relative), os.path.join(TRACKER_DIR, relative))
    with open(f"{scripts}/autotracking/item_mapping.lua", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("-- Généré par tools/build_tracker.py : id d'objet Archipelago -> code du pack.\nITEM_MAPPING = {\n")
        for ap_id, code in sorted(item_map.items()):
            handle.write(f"  [{ap_id}] = {lua_value(code)},\n")
        handle.write("}\n")
    with open(f"{scripts}/autotracking/location_mapping.lua", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("-- Généré par tools/build_tracker.py : id de lieu Archipelago -> sections du pack (carte du lieu, puis carte de Kalos).\nLOCATION_MAPPING = {\n")
        for ap_id, paths in sorted(location_map.items()):
            handle.write("  [%d] = {%s},\n" % (ap_id, ", ".join(json.dumps(item, ensure_ascii=False) for item in paths)))
        handle.write("}\n")
    unmatched = [g for r in REGION_ORDER for g in by_region[r] if resolve_anchor(g, areas) is None]
    print("zones sans position sur la carte (placées au centre de leur région) :", unmatched)
    return version, maps, location_map, item_map


def package(version, source, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, dirs, files in os.walk(source):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, source).replace(os.sep, "/"))
                count += 1
    print(f"{target} : {count} fichier(s), version {version}")


if __name__ == "__main__":
    version, maps, location_map, item_map = build(zones=bool(topmap_stems()))
    print(f"{len(maps)} cartes, {len(location_map)} lieux, {len(item_map)} objets suivis")
    package(version, PUBLIC_DIR, os.path.join(DIST_DIR, "Pokemon_XY_Tracker.zip"))
