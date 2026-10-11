"""
[FR] Génère le pack PopTracker de Pokémon X/Y depuis les données du monde.

Les checks, objets, régions et règles viennent de worlds/pokemon_xy (Locations.py, Items.py,
Regions.py) : le pack reste donc synchronisé avec l'APWorld. Rien n'est écrit à la main, sauf
les règles d'accès, qui reprennent celles de Rules.py (voir REGION_REQUIREMENTS et ci-dessous).

Usage :
    py -3.13 tools/build_tracker.py          # tracker/ (sources du pack) + dist/Pokemon_XY_Tracker.zip

Structure du pack inspirée du pack MIT de darkfire006 (xy-manual-ap-tracker), pour un autre monde.
"""

import importlib
import json
import os
import sys
import types
import zipfile
from collections import OrderedDict

from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD_DIR = os.path.join(PROJECT_DIR, "worlds", "pokemon_xy")
TRACKER_DIR = os.path.join(PROJECT_DIR, "tracker")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
GAME_NAME = "Pokemon X and Y"


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


def make_map(path, region, groups):
    """Carte d'une région : une grille de repères par lieu, regroupés par zone."""
    width, margin, pitch, pin = 980, 16, 30, 26
    columns = (width - 2 * margin) // pitch
    head = font(15)
    y = margin + 26
    placed = OrderedDict()
    layout = []
    for group, entries in groups.items():
        layout.append((y, group))
        y += 22
        for index, entry in enumerate(entries):
            row, col = divmod(index, columns)
            placed[entry] = (margin + col * pitch + pitch // 2, y + row * pitch + pitch // 2)
        y += ((len(entries) - 1) // columns + 1) * pitch + 14
    height = y + margin
    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 6), region, font=font(18), fill="#e2e8f0")
    for label_y, group in layout:
        draw.text((margin, label_y), group, font=head, fill="#94a3b8")
        draw.line((margin, label_y + 19, width - margin, label_y + 19), fill="#1e293b")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path)
    return placed, (width, height)


# ---------------------------------------------------------------------------
# Construction du pack
# ---------------------------------------------------------------------------

def build():
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

    cumulative, required = [], {}
    for region in REGION_ORDER:
        cumulative = cumulative + REGION_REQUIREMENTS[region]
        required[region] = list(cumulative)

    maps, location_nodes, item_map, location_map = [], [], {}, {}
    for region in REGION_ORDER:
        groups = by_region[region]
        if not groups:
            continue
        placed, _size = make_map(f"{TRACKER_DIR}/images/maps/{code_of(region)}.png", region,
                                 OrderedDict((g, [e[0] for e in entries]) for g, entries in groups.items()))
        maps.append({"name": region, "location_size": 24, "location_border_thickness": 3,
                     "img": f"images/maps/{code_of(region)}.png"})
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
                    "map_locations": [{"map": region, "x": x, "y": y}],
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
    tabs = {"tabbed_maps": {"type": "tabbed", "tabs": [
        {"title": m["name"].replace(" Area", ""), "content": {"type": "map", "maps": [m["name"]]}} for m in maps]}}
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
    return version, maps, location_map, item_map


def package(version):
    os.makedirs(DIST_DIR, exist_ok=True)
    target = os.path.join(DIST_DIR, "Pokemon_XY_Tracker.zip")
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, dirs, files in os.walk(TRACKER_DIR):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, TRACKER_DIR).replace(os.sep, "/"))
                count += 1
    print(f"{target} : {count} fichier(s), version {version}")


if __name__ == "__main__":
    version, maps, location_map, item_map = build()
    print(f"{len(maps)} cartes, {len(location_map)} lieux, {len(item_map)} objets suivis")
    package(version)
