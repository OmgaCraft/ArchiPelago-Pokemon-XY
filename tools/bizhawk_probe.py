"""
Outil de Phase 0 : sonde mémoire pour Pokémon X/Y sous BizHawk (cœur 3DS Encore).

Passe par le script Lua d'Archipelago `connector_bizhawk_generic.lua` (le même que
celui du futur client) : il faut le charger dans BizHawk (Tools > Lua Console).
Le script écoute en TCP sur un port de 43055 à 43060 et répond à des requêtes JSON,
une fois par image du jeu : **le jeu ne doit pas être en pause**.
Ne pas lancer en même temps le client BizHawk d'Archipelago : le script n'accepte qu'un client.

Domaine mémoire par défaut : « System Bus », adressé comme le jeu lui-même
(ex. 0x08000000 pour le tas). La 3DS est little-endian.
Aucune dépendance externe : uniquement la bibliothèque standard.

Exemples :
    py -3.13 tools/bizhawk_probe.py info
    py -3.13 tools/bizhawk_probe.py read 0x08000000 --type u32 --count 4
    py -3.13 tools/bizhawk_probe.py hexdump 0x08000000 0x40
    py -3.13 tools/bizhawk_probe.py find 3000 --type u32
    py -3.13 tools/bizhawk_probe.py refine 2800
    py -3.13 tools/bizhawk_probe.py refine changed
    py -3.13 tools/bizhawk_probe.py watch 0x08123456 --type u16
    py -3.13 tools/bizhawk_probe.py snapshot avant 0x08100000 0x10000
    py -3.13 tools/bizhawk_probe.py diff avant apres --bits --noise repos
    py -3.13 tools/bizhawk_probe.py findptr 0x08123456 --max-offset 0x400
    py -3.13 tools/bizhawk_probe.py write 0x08123456 u16 999
"""

import argparse
import base64
import json
import os
import re
import socket
import struct
import sys
import time

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Ports du script connecteur (SOCKET_PORT_FIRST et SOCKET_PORT_RANGE_SIZE dans le .lua).
PORT_FIRST = 43055
PORT_LAST = PORT_FIRST + 5
SCRIPT_VERSION = "1"

# Le script n'accepte un client qu'une fois toutes les 30 images, et ne répond qu'une fois par image.
CONNECT_TIMEOUT = 10.0
REPLY_TIMEOUT = 10.0

DEFAULT_DOMAIN = "System Bus"
# Domaines déclarés par le cœur Encore (Encore.IMemoryDomains.cs).
KNOWN_DOMAINS = ("System Bus", "FCRAM", "VRAM", "DSP RAM", "N3DS Extra RAM")

# Taille d'une requête READ/WRITE et nombre de requêtes par message.
# TODO: à ajuster selon la vitesse réelle (le script encode en base64 en Lua pur).
REQUEST_SIZE = 0x4000
REQUESTS_PER_MESSAGE = 16
SMALL_READS_PER_MESSAGE = 256

# Début du code du jeu : toujours présent quand un jeu 3DS tourne.
CODE_START = 0x0010_0000

# Plage scannée par défaut : le tas du jeu.
# TODO: à affiner — la taille réelle du tas de X/Y n'est pas encore connue.
DEFAULT_SCAN_START = 0x0800_0000
DEFAULT_SCAN_END = 0x0C00_0000

CHUNK_SIZE = REQUEST_SIZE * REQUESTS_PER_MESSAGE
MAX_STORED_HITS = 500_000

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".probe_state")
HITS_FILE = os.path.join(STATE_DIR, "hits.json")

# Types acceptés -> format struct little-endian
VALUE_TYPES = {
    "u8": "<B", "s8": "<b",
    "u16": "<H", "s16": "<h",
    "u32": "<I", "s32": "<i",
    "u64": "<Q", "s64": "<q",
    "f32": "<f", "f64": "<d",
}


# ---------------------------------------------------------------------------
# Client du script connecteur d'Archipelago
# ---------------------------------------------------------------------------

class BizHawkError(Exception):
    """BizHawk ne répond pas ou le script a renvoyé une erreur."""


class ReadRefused(BizHawkError):
    """Le script a renvoyé une erreur pour cette lecture (zone non mappée ?)."""


class BizHawkConnector:
    def __init__(self, domain=DEFAULT_DOMAIN):
        self.domain = domain
        self.sock = None
        self.buffer = b""
        for port in range(PORT_FIRST, PORT_LAST + 1):
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            except OSError:
                continue
            self.sock = sock
            self.port = port
            break
        if self.sock is None:
            raise BizHawkError(
                "Aucun script connecteur trouvé (ports 43055-43060) : charge "
                "connector_bizhawk_generic.lua dans BizHawk, et ferme le client BizHawk d'Archipelago.")
        self.sock.sendall(b"VERSION\n")
        version = self._readline(CONNECT_TIMEOUT).strip()
        if version != SCRIPT_VERSION:
            print(f"[!] Version du script connecteur : {version} (attendue : {SCRIPT_VERSION}).", file=sys.stderr)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _readline(self, timeout):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BizHawkError("BizHawk ne répond pas : le jeu est-il en pause ?")
            self.sock.settimeout(remaining)
            try:
                data = self.sock.recv(1 << 20)
            except socket.timeout:
                continue
            except ConnectionError:
                data = b""
            if not data:
                raise BizHawkError("Connexion fermée par BizHawk (script arrêté ou rechargé ?).")
            self.buffer += data
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line.decode("utf-8")

    def request(self, requests):
        """Envoie une liste de requêtes en un message, renvoie la liste des réponses."""
        self.sock.sendall(json.dumps(requests).encode("utf-8") + b"\n")
        responses = json.loads(self._readline(REPLY_TIMEOUT))
        if len(responses) != len(requests):
            raise BizHawkError(f"Réponse inattendue : {len(responses)} réponse(s) pour {len(requests)} requête(s).")
        return responses

    def lock(self):
        """Fige l'émulation : le script traite nos messages à la suite sans avancer d'image."""
        self.request([{"type": "LOCK"}])

    def unlock(self):
        self.request([{"type": "UNLOCK"}])

    def read_many(self, ranges):
        """Lit plusieurs (adresse, taille) en un message ; None pour une lecture refusée."""
        requests = [{"type": "READ", "address": a, "size": s, "domain": self.domain} for a, s in ranges]
        results = []
        for response in self.request(requests):
            if response.get("type") == "READ_RESPONSE":
                results.append(base64.b64decode(response["value"]))
            else:
                results.append(None)
        return results

    def read(self, address, size):
        result = bytearray()
        parts = [(a, min(REQUEST_SIZE, address + size - a)) for a in range(address, address + size, REQUEST_SIZE)]
        for index in range(0, len(parts), REQUESTS_PER_MESSAGE):
            batch = parts[index:index + REQUESTS_PER_MESSAGE]
            for (part_address, _), data in zip(batch, self.read_many(batch)):
                if data is None:
                    raise ReadRefused(f"Lecture refusée à 0x{part_address:08X} (domaine « {self.domain} »).")
                result += data
        return bytes(result)

    def write(self, address, data):
        requests = [
            {"type": "WRITE", "address": address + offset, "domain": self.domain,
             "value": base64.b64encode(data[offset:offset + REQUEST_SIZE]).decode("ascii")}
            for offset in range(0, len(data), REQUEST_SIZE)
        ]
        for response in self.request(requests):
            if response.get("type") != "WRITE_RESPONSE":
                raise BizHawkError(f"Écriture refusée : {response.get('err', response)}")

    def read_value(self, address, value_type):
        fmt = VALUE_TYPES[value_type]
        return struct.unpack(fmt, self.read(address, struct.calcsize(fmt)))[0]


def open_bizhawk(args):
    return BizHawkConnector(args.domain)


def iter_chunks(bizhawk, start, end, overlap):
    """
    Lit [start, end) par blocs, émulation figée. Chaque bloc déborde de `overlap`
    octets sur le suivant ; l'appelant ne garde que les positions < CHUNK_SIZE.
    """
    skipped = 0
    started = time.monotonic()
    last_report = 0.0
    bizhawk.lock()
    try:
        address = start
        while address < end:
            size = min(CHUNK_SIZE + overlap, end - address)
            try:
                data = bizhawk.read(address, size)
            except ReadRefused:
                # Le débordement a peut-être touché une zone illisible : on réessaie sans lui.
                try:
                    data = bizhawk.read(address, min(CHUNK_SIZE, end - address))
                except ReadRefused:
                    data = None
                    skipped += 1
            if data is not None:
                yield address, data
            address += CHUNK_SIZE
            now = time.monotonic()
            if now - last_report > 1.0:
                done = min(address, end) - start
                speed = done / max(now - started, 1e-6) / 2**20
                print(f"\r  0x{min(address, end):08X}  {100 * done // (end - start)} %  ({speed:.1f} Mio/s)",
                      end="", file=sys.stderr)
                last_report = now
    finally:
        bizhawk.unlock()
        print("\r" + " " * 50 + "\r", end="", file=sys.stderr)
    if skipped:
        print(f"[!] {skipped} bloc(s) refusé(s) ignoré(s).", file=sys.stderr)


def parse_value(text, value_type):
    return float(text) if value_type.startswith("f") else int(text, 0)


def pack_value(value, value_type):
    return struct.pack(VALUE_TYPES[value_type], value)


def format_value(value, value_type):
    if value_type.startswith("f"):
        return f"{value!r}"
    width = struct.calcsize(VALUE_TYPES[value_type]) * 2
    return f"{value} (0x{value & ((1 << (width * 4)) - 1):0{width}X})"


# ---------------------------------------------------------------------------
# État persistant (résultats de recherche, snapshots)
# ---------------------------------------------------------------------------

def save_hits(value_type, domain, hits):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(HITS_FILE, "w", encoding="utf-8") as handle:
        json.dump({"type": value_type, "domain": domain, "hits": hits}, handle)


def load_hits():
    if not os.path.isfile(HITS_FILE):
        sys.exit("Aucune recherche en cours : lance d'abord « find ».")
    with open(HITS_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def snapshot_paths(name):
    return os.path.join(STATE_DIR, f"{name}.bin"), os.path.join(STATE_DIR, f"{name}.json")


def print_hits(hits, value_type, limit=20):
    for address, value in hits[:limit]:
        print(f"  0x{address:08X} = {format_value(value, value_type)}")
    if len(hits) > limit:
        print(f"  ... et {len(hits) - limit} autre(s)")


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------

def cmd_info(args):
    bizhawk = open_bizhawk(args)
    system, rom_hash = bizhawk.request([{"type": "SYSTEM"}, {"type": "HASH"}])
    print(f"Script connecteur joignable (port {bizhawk.port}).")
    print(f"Système : {system.get('value')}")
    print(f"Hash de la ROM (BizHawk) : {rom_hash.get('value')}")
    if system.get("value") != "3DS":
        print("[!] Ce n'est pas un jeu 3DS qui est chargé.")
        return
    sizes = bizhawk.request([{"type": "MEMORY_SIZE", "domain": name} for name in KNOWN_DOMAINS])
    for name, response in zip(KNOWN_DOMAINS, sizes):
        if response.get("type") == "MEMORY_SIZE_RESPONSE":
            print(f"  Domaine « {name} » : 0x{response['value']:X} octets")
        else:
            print(f"  Domaine « {name} » : absent")
    try:
        data = bizhawk.read(CODE_START, 16)
        print(f"Test de lecture (début du code, « {args.domain} ») : 0x{CODE_START:08X}  {data.hex(' ').upper()}")
    except ReadRefused as error:
        print(f"[!] Test de lecture échoué : {error}")


def cmd_read(args):
    bizhawk = open_bizhawk(args)
    size = struct.calcsize(VALUE_TYPES[args.type])
    data = bizhawk.read(args.address, size * args.count)
    for index in range(args.count):
        value = struct.unpack_from(VALUE_TYPES[args.type], data, index * size)[0]
        print(f"0x{args.address + index * size:08X} = {format_value(value, args.type)}")


def cmd_hexdump(args):
    bizhawk = open_bizhawk(args)
    data = bizhawk.read(args.address, args.length)
    for offset in range(0, len(data), 16):
        line = data[offset:offset + 16]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in line)
        print(f"0x{args.address + offset:08X}  {line.hex(' ').upper():<47}  {text}")


def cmd_write(args):
    bizhawk = open_bizhawk(args)
    value = parse_value(args.value, args.type)
    old = bizhawk.read_value(args.address, args.type)
    print(f"0x{args.address:08X} : {format_value(old, args.type)} -> {format_value(value, args.type)}")
    if not args.yes and input("Confirmer l'écriture ? [o/N] ").strip().lower() not in ("o", "oui", "y"):
        print("Annulé.")
        return
    bizhawk.write(args.address, pack_value(value, args.type))
    new = bizhawk.read_value(args.address, args.type)
    print(f"Relu : {format_value(new, args.type)}")
    if new != value:
        print("[!] La valeur relue diffère : zone protégée en écriture ou réécrite aussitôt par le jeu.")


def cmd_watch(args):
    bizhawk = open_bizhawk(args)
    last = None
    print(f"Surveillance de 0x{args.address:08X} ({args.type}), Ctrl+C pour arrêter.")
    try:
        while True:
            value = bizhawk.read_value(args.address, args.type)
            if value != last:
                print(f"[{time.strftime('%H:%M:%S')}] {format_value(value, args.type)}")
                last = value
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


def cmd_find(args):
    bizhawk = open_bizhawk(args)
    value = parse_value(args.value, args.type)
    pattern = pack_value(value, args.type)
    alignment = len(pattern) if not args.unaligned else 1
    hits = []
    for chunk_address, data in iter_chunks(bizhawk, args.start, args.end, len(pattern) - 1):
        position = data.find(pattern)
        while 0 <= position < CHUNK_SIZE:
            address = chunk_address + position
            if address % alignment == 0:
                hits.append([address, value])
            position = data.find(pattern, position + 1)
        if len(hits) > MAX_STORED_HITS:
            sys.exit(f"Plus de {MAX_STORED_HITS} résultats : choisis une valeur plus distinctive.")
    save_hits(args.type, args.domain, hits)
    print(f"{len(hits)} résultat(s) pour {format_value(value, args.type)}.")
    print_hits(hits, args.type)


def cmd_refine(args):
    state = load_hits()
    value_type = state["type"]
    args.domain = state.get("domain", args.domain)
    bizhawk = open_bizhawk(args)
    fmt = VALUE_TYPES[value_type]
    size = struct.calcsize(fmt)
    keywords = {
        "changed": lambda old, new: new != old,
        "unchanged": lambda old, new: new == old,
        "increased": lambda old, new: new > old,
        "decreased": lambda old, new: new < old,
    }
    if args.condition in keywords:
        keep = keywords[args.condition]
    else:
        target = parse_value(args.condition, value_type)
        keep = lambda old, new: new == target  # noqa: E731
    remaining = []
    hits = state["hits"]
    bizhawk.lock()
    try:
        for index in range(0, len(hits), SMALL_READS_PER_MESSAGE):
            batch = hits[index:index + SMALL_READS_PER_MESSAGE]
            for (address, old), data in zip(batch, bizhawk.read_many([(a, size) for a, _ in batch])):
                if data is None:
                    continue
                new = struct.unpack(fmt, data)[0]
                if keep(old, new):
                    remaining.append([address, new])
    finally:
        bizhawk.unlock()
    save_hits(value_type, args.domain, remaining)
    print(f"{len(hits)} -> {len(remaining)} résultat(s).")
    print_hits(remaining, value_type)


def cmd_snapshot(args):
    bizhawk = open_bizhawk(args)
    bizhawk.lock()
    try:
        data = bizhawk.read(args.address, args.length)
    finally:
        bizhawk.unlock()
    os.makedirs(STATE_DIR, exist_ok=True)
    bin_path, meta_path = snapshot_paths(args.name)
    with open(bin_path, "wb") as handle:
        handle.write(data)
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump({"address": args.address, "length": len(data), "domain": args.domain, "time": time.time()}, handle)
    print(f"Snapshot « {args.name} » : 0x{args.address:08X} + 0x{len(data):X} octets.")


def load_snapshot(name):
    bin_path, meta_path = snapshot_paths(name)
    if not os.path.isfile(bin_path):
        sys.exit(f"Snapshot « {name} » introuvable.")
    with open(meta_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    with open(bin_path, "rb") as handle:
        return meta["address"], handle.read()


def cmd_diff(args):
    address_a, data_a = load_snapshot(args.before)
    address_b, data_b = load_snapshot(args.after)
    if address_a != address_b or len(data_a) != len(data_b):
        sys.exit("Les deux snapshots ne couvrent pas la même plage.")
    # Snapshot « bruit » : pris entre avant et après SANS rien faire en jeu.
    # Tout ce qui a changé entre « avant » et « bruit » (minuteurs, animations…) est ignoré.
    data_noise = None
    if args.noise:
        address_n, data_noise = load_snapshot(args.noise)
        if address_n != address_a or len(data_noise) != len(data_a):
            sys.exit("Le snapshot de bruit ne couvre pas la même plage.")
    size = 1 if args.bits else struct.calcsize(VALUE_TYPES[args.type])
    changes = 0
    for offset in range(0, len(data_a) - size + 1, size):
        old_bytes = data_a[offset:offset + size]
        new_bytes = data_b[offset:offset + size]
        if old_bytes == new_bytes:
            continue
        if data_noise is not None and data_noise[offset:offset + size] != old_bytes:
            continue
        address = address_a + offset
        if args.bits:
            # Un bit par ligne : les drapeaux d'événement (objet ramassé, badge…) sont souvent des bits.
            flipped = old_bytes[0] ^ new_bytes[0]
            for bit in range(8):
                if flipped & (1 << bit):
                    changes += 1
                    if changes <= args.limit:
                        state = "0 -> 1" if new_bytes[0] & (1 << bit) else "1 -> 0"
                        print(f"  0x{address:08X} bit {bit} : {state}  (bit n° {offset * 8 + bit} de la zone)")
        else:
            changes += 1
            if changes <= args.limit:
                old = struct.unpack(VALUE_TYPES[args.type], old_bytes)[0]
                new = struct.unpack(VALUE_TYPES[args.type], new_bytes)[0]
                print(f"  0x{address:08X} : {format_value(old, args.type)} -> {format_value(new, args.type)}")
    print(f"{changes} différence(s).")


def cmd_findptr(args):
    """Cherche les u32 alignés dont la valeur tombe dans [cible - max_offset, cible]."""
    bizhawk = open_bizhawk(args)
    low = max(args.target - args.max_offset, 0)
    high = args.target
    # En little-endian, les 16 bits de poids fort sont les octets 2 et 3 du u32 :
    # on les repère d'abord (recherche rapide en C), puis on filtre.
    prefixes = range(low >> 16, (high >> 16) + 1)
    patterns = [re.compile(b"(?=.." + re.escape(struct.pack("<H", prefix)) + b")", re.DOTALL) for prefix in prefixes]
    results = []
    for chunk_address, data in iter_chunks(bizhawk, args.start, args.end, 3):
        for pattern in patterns:
            for match in pattern.finditer(data):
                position = match.start()
                if position >= CHUNK_SIZE or (chunk_address + position) % 4:
                    continue
                value = struct.unpack_from("<I", data, position)[0]
                if low <= value <= high:
                    results.append((chunk_address + position, value))
    results.sort()
    for address, value in results[:args.limit]:
        print(f"  0x{address:08X} -> 0x{value:08X}  (cible - 0x{high - value:X})")
    print(f"{len(results)} pointeur(s) candidat(s).")


# ---------------------------------------------------------------------------
# Ligne de commande
# ---------------------------------------------------------------------------

def auto_int(text):
    return int(text, 0)


def build_parser():
    parser = argparse.ArgumentParser(description="Sonde mémoire BizHawk / Pokémon X-Y (Phase 0).")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Domaine mémoire BizHawk (défaut : System Bus)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Vérifie la connexion, le système et les domaines mémoire").set_defaults(func=cmd_info)

    p = sub.add_parser("read", help="Lit une ou plusieurs valeurs")
    p.add_argument("address", type=auto_int)
    p.add_argument("--type", choices=VALUE_TYPES, default="u32")
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("hexdump", help="Affiche une zone en hexadécimal")
    p.add_argument("address", type=auto_int)
    p.add_argument("length", type=auto_int)
    p.set_defaults(func=cmd_hexdump)

    p = sub.add_parser("write", help="Écrit une valeur (demande confirmation)")
    p.add_argument("address", type=auto_int)
    p.add_argument("type", choices=VALUE_TYPES)
    p.add_argument("value")
    p.add_argument("--yes", action="store_true", help="Pas de confirmation")
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("watch", help="Affiche chaque changement d'une valeur")
    p.add_argument("address", type=auto_int)
    p.add_argument("--type", choices=VALUE_TYPES, default="u32")
    p.add_argument("--interval", type=float, default=0.25)
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("find", help="Recherche une valeur exacte (nouvelle recherche)")
    p.add_argument("value")
    p.add_argument("--type", choices=VALUE_TYPES, default="u32")
    p.add_argument("--start", type=auto_int, default=DEFAULT_SCAN_START)
    p.add_argument("--end", type=auto_int, default=DEFAULT_SCAN_END)
    p.add_argument("--unaligned", action="store_true", help="Accepte les adresses non alignées")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("refine", help="Filtre la recherche : valeur, changed, unchanged, increased, decreased")
    p.add_argument("condition")
    p.set_defaults(func=cmd_refine)

    p = sub.add_parser("snapshot", help="Sauvegarde une zone mémoire")
    p.add_argument("name")
    p.add_argument("address", type=auto_int)
    p.add_argument("length", type=auto_int)
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("diff", help="Compare deux snapshots")
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--type", choices=VALUE_TYPES, default="u8")
    p.add_argument("--bits", action="store_true", help="Affiche chaque bit modifié (drapeaux)")
    p.add_argument("--noise", help="Snapshot pris sans rien faire : ses changements sont ignorés")
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("findptr", help="Cherche des pointeurs vers une adresse (ou juste avant)")
    p.add_argument("target", type=auto_int)
    p.add_argument("--max-offset", type=auto_int, default=0x400)
    p.add_argument("--start", type=auto_int, default=DEFAULT_SCAN_START)
    p.add_argument("--end", type=auto_int, default=DEFAULT_SCAN_END)
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_findptr)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except BizHawkError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
