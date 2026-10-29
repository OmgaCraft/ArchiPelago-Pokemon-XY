# Développement

## Organisation

| Dossier | Contenu |
|---|---|
| `worlds/pokemon_xy/` | Source de l'APWorld (monde, logique, client BizHawk, tests) |
| `lua/pokemon_xy_connector.lua` | Script à charger dans BizHawk (remplace le script générique d'Archipelago) |
| `yaml/` | Fichier joueur modèle, commenté en français |
| `dist/` | Fichiers prêts à jouer, produits par `tools/build_apworld.py` |
| `tools/build_apworld.py` | Construit l'APWorld et le zip tout-en-un ; `--install` les installe dans Archipelago |
| `tools/bizhawk_probe.py` | Sonde mémoire (lecture, écriture, recherche, snapshots) via le script connecteur |
| `tools/build_tracker.py` | Génère `tracker/` (pack PopTracker) et `dist/Pokemon_XY_Tracker.zip` depuis les données du monde |
| `tools/check_tracker.py` | Contrôle le pack avec un simulateur de l'API PopTracker (nécessite `lupa`) |
| `tools/rom_explore.py` | Explore la RomFS d'un dump : fichiers des noms d'objets, recherche de texte |
| `tools/patch_check.py` | Contrôle le patch des Poké Balls sur un vrai dump (lecture seule) |
| `tools/layeredfs_test.py` | Test du dossier de mods dans BizHawk (texte de l'écran de langue) |
| `docs/phase0/` | Recherche : version du jeu, BizHawk, adresses, marche à suivre pour en trouver |
| `upstream/` | README et commit d'origine (uhsfiuh), pour suivre les mises à jour de l'auteur |

## Architecture

| Morceau | Rôle |
|---|---|
| **APWorld** | Checks (objets au sol, cachés, cadeaux, badges, dresseurs en option), items et logique par paliers de badges. |
| **Script Lua** | Tourne dans BizHawk : lit et écrit la mémoire (domaine `mainmemory`), retire l'objet d'origine ramassé. Aucune fenêtre. |
| **Client** | `BizHawkClient` d'Archipelago : lit les drapeaux d'événement, envoie les checks, livre les objets reçus dans le sac. |

Le nombre d'objets livrés est gardé dans le data storage du serveur, clé `pokemon_xy_delivered_{team}_{slot}`.

### Patch du jeu (`worlds/pokemon_xy/rom/`)

Le dump n'est jamais modifié. À la connexion, le client demande au serveur le contenu des
Poké Balls au sol (`LocationScouts`, sans indice), reconstruit les fichiers modifiés depuis le dump
du joueur et les écrit dans le dossier de mods LayeredFS de BizHawk, que le cœur Encore lit au
démarrage du jeu : `<BizHawk>/3DS/User/load/mods/0004000000055E00/romfs/`. La livraison des objets
ne dépend pas du patch (le script Lua retire toujours l'objet donné par le jeu, puis le client livre).

| Module | Rôle |
|---|---|
| `romfs.py` | Lecture de la RomFS d'un dump `.3ds` déchiffré (NCSD, NCCH, IVFC niveau 3) |
| `garc.py` | Archives GARC v4 (lecture, réécriture identique à l'octet près) |
| `amx.py` | Scripts AMX compressés (portage de pkNX) |
| `text.py` | Fichiers texte Gen 6 chiffrés (lecture, remplacement de lignes) |
| `patch.py` | Poké Balls au sol, dossier des mods, écriture |

### Randomisation (`rom/randomize.py`, `rom/lz11.py`)

Options du YAML transmises par le `slot_data` (`rom_seed`, `randomize_*`, `experience_multiplier`), lues
par le client à la connexion. Tous les formats ont été vérifiés sur Pokémon Y (USA) et le jeu a démarré
et chargé une sauvegarde avec tous les fichiers remplacés (BizHawk 2.11.1) :

| Donnée | Fichier | Format |
|---|---|---|
| Fiches des Pokémon | `a/2/1/8` (dernier fichier) | 0x40 octets par espèce : talents 0x18-0x1A, expérience de base u16 en 0x22, stades en 0x09 |
| Capacités par niveau | `a/2/1/4` | paires (capacité u16, niveau u16) jusqu'à 0xFFFF |
| Rencontres sauvages | `a/0/1/2` | LZ11 ; 94 entrées de 4 octets (espèce 11 bits + forme 5 bits, niveaux) à partir du décalage lu en 0x10 |
| Dresseurs | `a/0/3/8` + `a/0/4/0` | données de 20 octets (format : bit 0 capacités, bit 1 objet) ; équipes de 8 octets par Pokémon (+2 objet, +8 capacités) |
| Starters | `DllPoke3Select.cro` (données, 0x10 + n x 0x54) et `DllField.cro` (code, 0xF7EDC + n x 0x18) | u16 espèce ; Kalos puis Kanto |

Le tirage utilise `random.Random(rom_seed)` : même partie, même jeu. Espèces choisies par force (somme des
statistiques) proche de l'originale ; capacités et talents tirés parmi ceux déjà présents dans le jeu.
L'encodeur LZ11 n'écrit que des octets littéraux (valide, un peu plus gros).

Données vérifiées sur Pokémon Y (USA) :
- objets au sol : script n° 0x11 de `a/0/3/1`, tableau de 207 entrées (objet, quantité, n°) après
  9 mots de données ; la Poké Ball n° i lève le drapeau `0x51A + i` (207 lieux « FIELD ITEM ») ;
- noms d'objets : fichiers n° 96 et 98 de `a/0/7/2` à `a/0/7/9` (japonais kana, kanji, anglais,
  français, italien, allemand, espagnol, coréen), 718 objets ; objets « ??? » : 113-115, 120-133,
  426, 427, 622 ;
- écran de langue : `a/0/7/4`, fichier 85, lignes 4-5.

## Construire

```
py -3.13 tools/build_apworld.py            # dist/pokemon_xy.apworld + dist/Pokemon_XY_Archipelago.zip
py -3.13 tools/build_apworld.py --install  # et copie l'apworld et le script Lua dans C:\ProgramData\Archipelago
```

La version vient de `world_version` dans `worlds/pokemon_xy/archipelago.json`.

## Tester

Les tests se lancent depuis une copie source d'Archipelago 0.6.7 (le dossier installé est compilé) :

```
git clone --depth 1 --branch 0.6.7 https://github.com/ArchipelagoMW/Archipelago.git
```

Ensuite :
1. crée un venv `py -3.13` ;
2. installe `requirements.txt` et les `worlds/*/requirements.txt`, plus `pytest` et `setuptools<81` ;
3. copie `worlds/pokemon_xy` dans `Archipelago/worlds/` ;
4. lance `python -m pytest test/general worlds/pokemon_xy/test`.

## Règles

- Aucune adresse, aucun ID ni drapeau inventé : tant qu'il n'est pas vérifié, c'est une
  constante nommée avec `TODO: à trouver`.
- Commentaires en français (préfixés `[FR]` dans le code repris), identifiants en anglais.
- Aucun fichier original du jeu n'est distribué.
