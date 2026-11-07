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
TRACKER_DIR = os.path.join(PROJECT_DIR, "tracker")          # pack public (plans schématiques)
LOCAL_DIR = os.path.join(PROJECT_DIR, "local", "tracker")   # pack local, avec les cartes vues du dessus (jamais publié)
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


def plan_layout(entries, positions, size):
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
        scale = min((size[0] - 2 * margin) / span_x, (size[1] - 2 * margin) / span_y, 14)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        pts = [(size[0] / 2 + (x - cx) * scale, size[1] / 2 + (y - cy) * scale) for _n, x, y in items]
        pts = spread(pts, size)
        plans.append([(i[0], px, py) for i, (px, py) in zip(items, pts)])
    return plans


def load_topmaps():
    """Calage des cartes vues du dessus (tools/calibrate_topmaps.py) ; vide hors version locale."""
    path = os.path.join(ASSETS_DIR, "topmap_calibration.json")
    if not USE_ZONES or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return {g: c for g, c in json.load(handle).items()
                if os.path.exists(os.path.join(ASSETS_DIR, "topmaps", c["image"]))}


def make_group_map(path, group, entries, positions=None, zone_of=None):
    """Image d'un lieu (route, ville, grotte...) : la carte vue du dessus (version locale) avec les objets
    au sol à leur place exacte, sinon un plan schématique (positions lues dans la ROM), puis les autres
    repères en grille. Renvoie la position de chaque check dans l'image."""
    positions, zone_of = positions or {}, zone_of or {}
    calib = load_topmaps().get(group)
    width, margin, pitch = 980, 16, 30
    plan_size = (290, 200)
    y = margin
    placed = OrderedDict()
    picture = None
    if calib:
        picture = Image.open(os.path.join(ASSETS_DIR, "topmaps", calib["image"])).convert("RGB")
        factor = min((width - 2 * margin) / picture.width, 640 / picture.height, 1.6)
        picture = picture.resize((int(picture.width * factor), int(picture.height * factor)), Image.LANCZOS)
        for name in entries:
            transform = calib["zones"].get(str(zone_of.get(name)))
            if transform and name in positions:
                sx, sy, tx, ty = transform
                px = min(max((sx * positions[name][1] + tx) * factor, 8), picture.width - 8)
                py = min(max((sy * positions[name][2] + ty) * factor, 8), picture.height - 8)
                placed[name] = (int(margin + px), int(y + py))
        picture_y = y
        y += picture.height + 10
    plans = plan_layout([e for e in entries if e not in placed], positions, plan_size)
    per_row = max(1, (width - 2 * margin) // (plan_size[0] + 12))
    frames = []
    for index, plan in enumerate(plans):
        row, col = divmod(index, per_row)
        ox, oy = margin + col * (plan_size[0] + 12), y + row * (plan_size[1] + 12)
        frames.append((ox, oy))
        for name, px, py in plan:
            placed[name] = (int(ox + px), int(oy + py))
    y += ((len(plans) - 1) // per_row + 1) * (plan_size[1] + 12) if plans else 0
    rest = [e for e in entries if e not in placed]
    columns = max(1, (width - 2 * margin) // pitch)
    for index, entry in enumerate(rest):
        row, col = divmod(index, columns)
        placed[entry] = (margin + col * pitch + pitch // 2, y + row * pitch + pitch // 2)
    y += ((len(rest) - 1) // columns + 1) * pitch if rest else 0
    image = Image.new("RGB", (width, max(y + margin, 120)), "#0f172a")
    draw = ImageDraw.Draw(image)
    if picture:
        image.paste(picture, (margin, picture_y))
    for ox, oy in frames:
        draw.rounded_rectangle((ox, oy, ox + plan_size[0], oy + plan_size[1]), radius=8,
                               fill="#111c33", outline="#334155", width=2)
        for gx in range(ox + 30, ox + plan_size[0], 30):
            draw.line((gx, oy + 4, gx, oy + plan_size[1] - 4), fill="#16233f")
        for gy in range(oy + 30, oy + plan_size[1], 30):
            draw.line((ox + 4, gy, ox + plan_size[0] - 4, gy), fill="#16233f")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path)
    return placed


def town_of(group):
    """Ville à laquelle appartient un lieu (« Santalune City (Gym) » -> Santalune City), ou None."""
    base = re.sub(r"\s*\(.*?\)", "", group).strip()
    base = TOWN_PARTS.get(base, base)
    return base if base in TOWNS else None


def map_tab(title, group):
    return {"title": title, "content": {"type": "map", "maps": [f"Lieu : {group}"]}}


def navigation(group_region):
    """Onglets : « Monde » (carte de chaque région, puis ses routes et lieux) et « Villes » (chaque ville,
    puis les routes qui y mènent)."""
    groups = list(group_region)
    routes = {g for g in groups if g.startswith("Route ")}
    monde = []
    for region in REGION_ORDER:
        subs = [{"title": "Carte", "content": {"type": "map", "maps": [f"{region} (carte)"]}}]
        for group in groups:
            if group_region[group] == region and town_of(group) is None:
                subs.append(map_tab("Divers" if group == region else group, group))
        monde.append({"title": region.replace(" Area", ""), "content": {"type": "tabbed", "tabs": subs}})
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
    return [{"title": "Monde", "content": {"type": "tabbed", "tabs": monde}},
            {"title": "Villes", "content": {"type": "tabbed", "tabs": villes}}]


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
    raw = json.load(open(os.path.join(ASSETS_DIR, "ball_positions.json"), encoding="utf-8"))
    for by_group in by_region.values():
        for entries in by_group.values():
            for name, data in entries:
                n = (data.flag_id or 0) - FIELD_ITEM_FLAG
                if "FIELD ITEM" in data.category and str(n) in raw:
                    ball_positions[name] = (raw[str(n)]["zone"], raw[str(n)]["x"], raw[str(n)]["y"])
                    ball_zones[name] = raw[str(n)]["zone"]
    print("objets au sol placés sur un plan :", len(ball_positions))

    cumulative, required = [], {}
    for region in REGION_ORDER:
        cumulative = cumulative + REGION_REQUIREMENTS[region]
        required[region] = list(cumulative)

    areas = json.load(open(os.path.join(ASSETS_DIR, "kalos_areas.json"), encoding="utf-8"))
    kalos_size = Image.open(os.path.join(ASSETS_DIR, KALOS_MAP)).size
    os.makedirs(f"{TRACKER_DIR}/images/maps", exist_ok=True)
    shutil.copyfile(os.path.join(ASSETS_DIR, KALOS_MAP), f"{TRACKER_DIR}/images/maps/kalos.png")
    maps, location_nodes, item_map, location_map = [], [], {}, {}
    group_region = OrderedDict()
    for region in REGION_ORDER:
        groups = by_region[region]
        if not groups:
            continue
        placed = {}
        for group, entries in groups.items():
            slug = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", group)).strip("_")
            placed.update(make_group_map(f"{TRACKER_DIR}/images/maps/lieu_{slug}.png", group,
                                         [e[0] for e in entries], ball_positions, ball_zones))
            maps.append({"name": f"Lieu : {group}", "location_size": 24, "location_border_thickness": 3,
                         "img": f"images/maps/lieu_{slug}.png"})
            group_region[group] = region
        maps.append({"name": f"{region} (carte)", "location_size": MAP_PIN, "location_border_thickness": 2,
                     "img": "images/maps/kalos.png"})
        # Position de chaque lieu sur la carte de Kalos : groupes autour de leur zone.
        anchors = OrderedDict()
        for group, entries in groups.items():
            anchors.setdefault(resolve_anchor(group, areas), []).extend(e[0] for e in entries)
        found = [a for a in anchors if a]
        fallback = (sum(a[0] for a in found) / len(found), sum(a[1] for a in found) / len(found))             if found else (kalos_size[0] / 2, kalos_size[1] / 2)
        on_map = {}
        for anchor, names in anchors.items():
            for name, xy in zip(names, cluster(len(names), anchor or fallback, kalos_size)):
                on_map[name] = xy
        children = []
        for group, entries in groups.items():
            for name, data in entries:
                x, y = placed[name]
                category = next((c for c in CATEGORY_STYLE if c in data.category), "FIELD ITEM")
                rules = list(required[region])
                reqs = data.requires or ""
                for key, parts in LOCATION_REQUIREMENTS:
                    if key in reqs:
                        rules += parts
                node = {
                    "name": clean(name),
                    "map_locations": [{"map": f"Lieu : {group}", "x": x, "y": y},
                                      {"map": f"{region} (carte)", "x": on_map[name][0], "y": on_map[name][1]}],
                    "sections": [{"name": "Check", "item_count": 1,
                                  "chest_unopened_img": f"images/checks/{CATEGORY_STYLE[category][0]}.png",
                                  "chest_opened_img": "images/checks/opened.png"}],
                }
                if rules:
                    node["access_rules"] = [",".join(rules)]
                if category == "HIDDEN ITEM":
                    node["visibility_rules"] = ["$show_hidden"]
                    node["access_rules"] = [",".join(rules + ["$dowsing_ok"])]
                elif category == "TRAINER":
                    node["visibility_rules"] = ["$show_trainers"]
                children.append(node)
                location_map[data.code] = f"@{region}/{clean(name)}/Check"
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
        handle.write("-- Généré par tools/build_tracker.py : id de lieu Archipelago -> section du pack.\nLOCATION_MAPPING = {\n")
        for ap_id, path in sorted(location_map.items()):
            handle.write(f"  [{ap_id}] = {lua_value(path)},\n")
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
    version, maps, location_map, item_map = build()
    print(f"{len(maps)} cartes, {len(location_map)} lieux, {len(item_map)} objets suivis")
    package(version, PUBLIC_DIR, os.path.join(DIST_DIR, "Pokemon_XY_Tracker.zip"))
    # Version locale avec les cartes vues du dessus (Poképédia) : à garder chez soi (droits d'auteur).
    if os.path.isdir(os.path.join(ASSETS_DIR, "topmaps")) and os.path.exists(os.path.join(ASSETS_DIR, "topmap_calibration.json")):
        if os.path.isdir(LOCAL_DIR):
            shutil.rmtree(LOCAL_DIR)
        build(LOCAL_DIR, zones=True)
        package(version, LOCAL_DIR, os.path.join(PROJECT_DIR, "local", "Pokemon_XY_Tracker.zip"))
