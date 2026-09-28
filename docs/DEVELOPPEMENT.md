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
| `docs/phase0/` | Recherche : version du jeu, BizHawk, adresses, marche à suivre pour en trouver |
| `upstream/` | README et commit d'origine (uhsfiuh), pour suivre les mises à jour de l'auteur |

## Architecture

| Morceau | Rôle |
|---|---|
| **APWorld** | Checks (objets au sol, cachés, cadeaux, badges, dresseurs en option), items et logique par paliers de badges. |
| **Script Lua** | Tourne dans BizHawk : lit et écrit la mémoire (domaine `mainmemory`), retire l'objet d'origine ramassé, fenêtre d'aide. |
| **Client** | `BizHawkClient` d'Archipelago : lit les drapeaux d'événement, envoie les checks, livre les objets reçus dans le sac. |

Pas de patch de la ROM : tout passe par la mémoire du jeu pendant la partie.
Le nombre d'objets livrés est gardé dans le data storage du serveur, clé `pokemon_xy_delivered_{team}_{slot}`.

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
