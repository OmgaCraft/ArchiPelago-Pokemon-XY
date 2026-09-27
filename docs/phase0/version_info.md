# Phase 0 — Version ciblée

Légende : ✅ vérifié sur la machine · 📖 source externe, à confirmer · ❓ à relever

## Jeu

| Élément | Valeur | Statut |
|---|---|---|
| Jeux | Pokémon X **et** Pokémon Y, pris en charge tous les deux | ✅ choix utilisateur |
| Copie | Ton propre dump de cartouche (`.3ds` ou `.cia`, chiffré ou déchiffré) | ❓ format à noter |
| Title ID Pokémon X | `0004000000055D00` | 📖 bases de titres 3DS |
| Title ID Pokémon Y | `0004000000055E00` | 📖 bases de titres 3DS |
| Title ID des mises à jour | `0004000E00055D00` (X) / `0004000E00055E00` (Y) | 📖 |
| Mise à jour installée | TODO: à relever | ❓ |
| Mise à jour visée | **1.5**, la dernière | 📖 à décider ensemble |
| Dump Y testé | `Pokemon Y (USA) (En,Ja,Fr,De,Es,It,Ko).3ds`, 2 Gio, Title ID `0004000000055E00`, produit `CTR-P-EK2A`, **déchiffré** (NoCrypto) | ✅ en-tête lu le 2026-09-27 |
| Hash de la ROM (BizHawk) — Y | `0C0C54FC3A0DA480061D661BA3A5644F` (= le dump testé par uhsfiuh) | ✅ lu dans BizHawk 2.11.1 |
| Hash de la ROM (BizHawk) — X | TODO: à relever (`bizhawk_probe.py info`) | ❓ |

> **Pourquoi la version compte.** Les patches de code (`exefs`) ne s'appliquent qu'à un
> `code.bin` précis. Une mise à jour remplace ce code, et les adresses mémoire peuvent
> bouger avec elle. On choisit **une** version par jeu et on n'en change plus.
>
> **Pourquoi viser la 1.5.** La version 1.0 a un bug connu qui peut corrompre la
> sauvegarde en sauvegardant dans certains quartiers d'Illumis (Lumiose). La mise à jour 1.1
> l'a corrigé 📖. Si tu n'as que la 1.0, on peut quand même travailler dessus en évitant
> de sauvegarder dans Illumis.

## Émulateur : BizHawk (cœur 3DS Encore)

| Élément | Valeur | Statut |
|---|---|---|
| BizHawk | 2.11.1 (Windows x64) | ✅ installé |
| Cœur 3DS | Encore (fork de Citra), apparu dans BizHawk 2.10 | 📖 TASVideos |
| Formats acceptés | `.3ds` et `.cia`, chiffrés ou déchiffrés | 📖 TASVideos |
| Firmware | Seulement pour un dump **chiffré** : `aes_keys.txt` et `seeddb.bin`, venant de ta console (Config > Firmwares, section 3DS, clic droit > « Set Customization ») | 📖 ; ✅ aucun configuré pour l'instant |
| Mise à jour / DLC | Les ROMs chargées après le jeu doivent être des `.cia` : jeu + mise à jour se chargent ensemble (Tools > Multi-disk Bundler) | 📖 code de BizHawk (`Encore.cs`) |
| Dossier utilisateur 3DS | `BizHawk-2.11.1-win-x64\3DS\User` (sauvegardes, NAND, SD) | ✅ `config.ini` (dossier créé au 1er lancement) |
| Dossier de mods | Hypothèse : `3DS\User\load\mods\<Title ID>\` (`romfs\`, `exefs\`), car Encore a gardé le LayeredFS de Citra | 📖 code d'Encore (`layered_fs.cpp`, `patch.cpp`) ; ❓ à tester |

### Domaines mémoire (code de BizHawk, `Encore.IMemoryDomains.cs`) 📖
| Domaine | Contenu |
|---|---|
| **System Bus** | 4 Gio, **adressé comme le jeu** (tas en `0x08000000`, code en `0x00100000`…). C'est celui qu'on utilise. |
| FCRAM | Mémoire physique principale |
| VRAM | Mémoire vidéo |
| DSP RAM | Mémoire audio |
| N3DS Extra RAM | Seulement en mode New 3DS |

## Archipelago

| Élément | Valeur | Statut |
|---|---|---|
| Archipelago | 0.6.7, `C:\ProgramData\Archipelago` (`custom_worlds\`) | ✅ |
| Client BizHawk | `ArchipelagoBizHawkClient.exe`, module `worlds/_bizhawk` | ✅ présent |
| Script connecteur | `C:\ProgramData\Archipelago\data\lua\connector_bizhawk_generic.lua`, version 1 | ✅ |
| Protocole du script | TCP sur `localhost`, 1er port libre de **43055 à 43060**, une ligne JSON par message, données en base64, une réponse par image (plusieurs d'affilée après `LOCK`) | ✅ lu dans le script |
| Avertissement | Le script affiche « BizHawk newer than this script » au-delà de 2.10 : simple avertissement | ✅ lu dans le script |
| Python | `py -3.13` ; le `python` du PATH est la 3.10, trop ancien pour Archipelago ≥ 0.6.4 | ✅ |

## Modèle existant : Pokémon Noir/Blanc

Ton `custom_worlds\pokemon_bw.apworld` (BlastSlimey, SparkyDaDoggo, v0.3.37) a la même forme
que ce qu'on vise, **avec deux versions d'un même jeu** :

- client `BizHawkClient` (`system = "NDS"`), deux extensions de patch `.apblack` / `.apwhite` ;
- `validate_rom` lit l'en-tête du jeu pour reconnaître la version ;
- les checks sont des **drapeaux de la sauvegarde** lus en mémoire, les objets reçus sont
  écrits avec `guarded_write` ;
- données du jeu rangées dans `data/items/…` et `data/locations/…`.

Pour X/Y : `system = "3DS"`, domaine `System Bus`, extensions `.apx` / `.apy` (à définir).
