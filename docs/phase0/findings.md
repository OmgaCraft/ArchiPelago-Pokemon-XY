# Phase 0 — Résultats

Légende : ✅ vérifié · 📖 source externe (wiki/guide), à confirmer en jeu · ❓ à trouver

Voir aussi : [version_info.md](version_info.md) (version, BizHawk, script connecteur)
et [protocole_en_jeu.md](protocole_en_jeu.md) (marche à suivre en jeu).

---

## 0.A Existant

- **Aucun APWorld Pokémon X/Y public** trouvé au 2026-09-27 : on part de zéro.
- **Émulateur : BizHawk** (cœur 3DS Encore), choix de l'utilisateur : c'est l'émulateur de
  référence d'Archipelago, avec son client générique `BizHawkClient`.
- **Modèle d'architecture** : Pokémon Noir/Blanc (`pokemon_bw.apworld`), deux versions d'un
  même jeu sous BizHawk. Voir [version_info.md](version_info.md#modèle-existant--pokémon-noirblanc).
- **Randomizers Gen 6 existants**, utiles pour les formats de fichiers du jeu (Phase 1) :
  - pk3DS : éditeur/randomizer Gen 6-7 (GARC, dresseurs, rencontres…).
  - PokeRandomizer (ArcanoxDragon) : randomise pour X/Y et ROSA les Pokémon sauvages, les
    dresseurs, les starters et **les objets dans les Poké Balls au sol** (sauf les CS). Il produit
    des fichiers pour LayeredFS. Son code montre donc **où sont stockés les objets au sol**.
- **PKHeX** : décrit toute la sauvegarde de X/Y (sac, argent, badges, drapeaux d'événement…).
  Hypothèse à vérifier : la sauvegarde est gardée d'un seul bloc en mémoire. Si c'est le
  cas, une seule adresse sûre (l'argent) suffit pour situer tout le reste avec les offsets de PKHeX.

## 0.B Contenu du jeu

### Choix des checks (par défaut, rien d'imposé par l'utilisateur)
| Catégorie | Check | Item | Statut |
|---|---|---|---|
| Objets au sol (Poké Balls) | ✅ | ✅ | nombre ❓ (Phase 1, données du jeu) |
| Objets cachés | ✅ | ✅ | nombre ❓ |
| Cadeaux de PNJ | ✅ | ✅ | liste ❓ |
| CT et CS | ✅ | ✅ | liste des CT ❓ |
| Badges d'arène | ✅ (battre le champion) | ✅ | — |
| Pokédex | option future | — | — |

### Badges 📖 (Serebii)
| # | Ville | Champion | Type | Badge | Obéissance jusqu'au niv. |
|---|---|---|---|---|---|
| 1 | Neuvartault (Santalune) | Violette (Viola) | Insecte | Insecte | 30 |
| 2 | Relifac-le-Haut (Cyllage) | Lino (Grant) | Roche | Mur | 40 |
| 3 | Yantreizh (Shalour) | Cornélia (Korrina) | Combat | Lutte | 50 |
| 4 | Port Tempères (Coumarine) | Amaro (Ramos) | Plante | Plante | 60 |
| 5 | Illumis (Lumiose) | Lem (Clemont) | Électrik | Tension | 70 |
| 6 | Romant-sous-Bois (Laverre) | Valériane (Valerie) | Fée | Fée | 80 |
| 7 | Mozheim (Anistar) | Astera (Olympia) | Psy | Psychisme | 90 |
| 8 | Flusselles (Snowbelle) | Urup (Wulfric) | Glace | Iceberg | 100 |

> Noms français à vérifier en jeu (ta langue d'affichage). Les noms anglais sont ceux des sources.

- D'après les sources consultées, **les badges de X/Y ne règlent que l'obéissance** : aucune
  mention de badge requis pour utiliser une CS hors combat ❓ à confirmer en jeu.
  Conséquence pour la logique : la progression dépendrait des CS elles-mêmes et des
  événements de l'histoire, pas des badges (sauf la Route Victoire : 8 badges ❓).

### CS 📖 (Pokémon Database)
| CS | Capacité | Obtention (vanilla) |
|---|---|---|
| CS01 | Coupe (Cut) | Château de Bellerive (Parfum Palace), labyrinthe du jardin |
| CS02 | Vol (Fly) | Port Tempères, Prof. Platane à la gare du monorail |
| CS03 | Surf | Yantreizh, Serena/Calem après Cornélia et la Tour Maîtrise |
| CS04 | Force (Strength) | Relifac-le-Haut, Lino devant l'arène |
| CS05 | Cascade (Waterfall) | Route 19, Mélanie (Shauna) sur le pont |

### Objets clés et blocages de progression ❓
Liste à établir en Phase 1 depuis les données du jeu : Rollers, Poké Flûte (Ronflex de la
Route 7 📖), laissez-passer, Méga-Anneau, etc. Pour chaque blocage il faudra savoir s'il
dépend d'un **objet** (randomisable) ou d'un **événement de l'histoire** (drapeau).

### À vérifier en jeu ❓
- Les objets cachés réapparaissent-ils ? (sinon : un check chacun)
- Objets en double : l'ID d'un check doit identifier **l'emplacement**, pas l'objet.
- Défaite / K.O. de l'équipe : conséquence exacte (pour un futur death link).
- Octets libres dans la sauvegarde (pour stocker le nombre d'objets AP déjà reçus).

---

## 0.C Mémoire

### Adresses de la V1 (reprises de uhsfiuh) 📖
Domaine BizHawk `mainmemory` (le script Lua ignore le domaine demandé par le client).
Testées par l'auteur sur **Pokémon Y (USA)**, hash BizHawk `0C0C54FC3A0DA480061D661BA3A5644F`,
le même dump que celui de l'utilisateur. Non vérifiées par nous en jeu.

| Donnée | Adresse | Détail |
|---|---|---|
| Badges | `0x074D86A0` | 1 octet, bit 0 = Insecte … bit 7 = Iceberg |
| Drapeaux d'événement | `0x074E86B8` | 375 octets lus (drapeaux 0 à 0xBB7) |
| Sac : objets | `0x074D5554` | 100 cases de 4 octets (u16 id, u16 quantité) |
| Sac : objets rares | `0x074D5B94` | 60 cases |
| Sac : CT/CS | `0x074D5D14` | 106 cases |
| Sac : soins | `0x074D5EBC` | 60 cases |
| Sac : baies | `0x074D5FBC` | 70 cases |
| Rollers | drapeau `0x0A55` | capacité, pas un objet du sac |
| Panthéon (objectif) | drapeau `0x0A50` | |

### Nos relevés
Aucune adresse relevée par nous pour l'instant. À faire pour Pokémon X (et pour vérifier Y).

| Donnée | Adresse (X) | Adresse (Y) | Type | Stable après carte / sauvegarde+rechargement / redémarrage | Statut |
|---|---|---|---|---|---|
| Argent | TODO | TODO | u32 📖 | | ❓ |
| Sac : objets (id + quantité) | TODO | TODO | u16 + u16 📖 | | ❓ |
| Sac : objets rares | TODO | TODO | | | ❓ |
| Sac : CT/CS | TODO | TODO | | | ❓ |
| Badges | TODO | TODO | bits ? | | ❓ |
| Drapeaux « objet ramassé » | TODO | TODO | bits ? | | ❓ |
| Carte / zone courante | TODO | TODO | | | ❓ |
| État du jeu (titre / en jeu / combat / menu) | TODO | TODO | | | ❓ |
| Équipe | TODO | TODO | | | ❓ |
| Octets libres dans la sauvegarde | TODO | TODO | | | ❓ |

## 0.D Patches ❓
Rien de commencé. Deux façons de livrer le jeu modifié, à départager en Phase 4 :
- **Dossier de mods** dans `BizHawk\3DS\User\load\mods\<Title ID>\` (si Encore le charge) :
  `romfs\` pour les données (objets au sol, scripts, textes), `exefs\` pour le code
  (`code.ips`/`code.bps`, lié à une version exacte). Le patch Archipelago écrirait ce
  dossier, et le joueur ouvrirait son dump d'origine. Léger, mais une seule seed à la fois par jeu.
- **ROM reconstruite** (comme Noir/Blanc) : le patch produit un nouveau `.3ds`/`.cia`.
  Plus classique, mais il faut reconstruire le système de fichiers du jeu (plusieurs Go).

## 0.E Tests décisifs
| Test | Statut |
|---|---|
| Parler au script connecteur d'Archipelago dans BizHawk (lecture, écriture, `LOCK`) | ✅ contre un faux script (même protocole) ; ❓ dans le vrai BizHawk (`bizhawk_probe.py info`) |
| Le domaine « System Bus » donne bien les adresses du jeu (tas en `0x08000000`) | ❓ |
| Vitesse d'un scan complet du tas (64 Mio) par le script Lua | ❓ |
| Lire l'argent en direct | ❓ |
| Ajouter un objet au sac, visible en jeu et conservé à la sauvegarde | ❓ |
| Détecter un objet ramassé (drapeau) | ❓ |
| Détecter l'obtention d'un badge | ❓ |
| BizHawk (Encore) charge un mod `romfs` depuis `3DS\User\load\mods` (ex. un texte modifié) | ❓ |

---

## Sources
- Serebii : [Kalos Gyms](https://www.serebii.net/xy/gyms.shtml)
- Pokémon Database : [X & Y HM locations](https://pokemondb.net/x-y/hms)
- TASVideos : [BizHawk/3DS](https://tasvideos.org/Bizhawk/3DS)
- BizHawk : [cœur 3DS](https://github.com/TASEmulators/BizHawk/tree/master/src/BizHawk.Emulation.Cores/Consoles/Nintendo/3DS) (`Encore.cs`, `Encore.IMemoryDomains.cs`)
- Encore : [file_sys](https://github.com/CasualPokePlayer/encore/tree/master/src/core/file_sys) (`layered_fs.cpp`, `patch.cpp`)
- Archipelago : `data\lua\connector_bizhawk_generic.lua` (installé localement)
- [PokeRandomizer (ArcanoxDragon)](https://github.com/ArcanoxDragon/PokeRandomizer)
