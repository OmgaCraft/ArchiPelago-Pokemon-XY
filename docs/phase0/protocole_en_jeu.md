# Phase 0 — Marche à suivre en jeu

Objectif : vérifier qu'on peut lire et écrire la mémoire du jeu depuis Python à travers
BizHawk, puis trouver les premières adresses (argent, sac, objet ramassé).
**À faire pour X, puis refaire pour Y** : les adresses peuvent différer d'un jeu à l'autre.

Toutes les commandes se lancent depuis le dossier du projet, **BizHawk ouvert, le jeu lancé
(pas en pause) et le script connecteur chargé** :

```
py -3.13 tools/bizhawk_probe.py <commande>
```

Les adresses sont celles du jeu (ex. `0x08123456`), dans le domaine « System Bus ».
Le client BizHawk d'Archipelago doit être **fermé** : le script n'accepte qu'un client à la fois.

> **Avant toute écriture en mémoire** : fais un savestate (Shift+F1) **et** copie le dossier
> `BizHawk-2.11.1-win-x64\3DS\User` (il contient la sauvegarde du jeu).

---

## Étape 0 — Lancer le jeu dans BizHawk
1. Ouvre `EmuHawk.exe`, puis File > Open ROM > ton dump de Pokémon X (ou Y).
   - Dump **chiffré** : BizHawk demandera `aes_keys.txt` et `seeddb.bin` (Config > Firmwares,
     section 3DS). Ils viennent de ta console. Un dump **déchiffré** n'en a pas besoin.
   - Si tu as la mise à jour en `.cia` : Tools > Multi-disk Bundler, ajoute le jeu **puis** la
     mise à jour, et ouvre le fichier `.xml` produit.
2. Joue jusqu'à pouvoir bouger ton personnage (nouvelle partie ou partie chargée).
3. Tools > Lua Console, puis Script > Open Script :
   `C:\ProgramData\Archipelago\data\lua\connector_bizhawk_generic.lua`.
   La console affiche « Waiting for client to connect… ». L'avertissement sur la version de BizHawk est normal.

## Étape 1 — Connexion
1. Lance `info`. Tu dois voir `Système : 3DS`, un hash de ROM, les domaines mémoire et un
   « Test de lecture » avec des octets.
   - « Aucun script connecteur trouvé » : le script n'est pas chargé, ou le client BizHawk
     d'Archipelago est ouvert.
   - « BizHawk ne répond pas » : le jeu est en pause.
2. Note le hash de la ROM et la version du jeu (mise à jour installée ou non, laquelle).

## Étape 2 — Argent
1. Note ton argent (menu, Carte Dresseur), par exemple 3000.
2. `find 3000 --type u32` (le jeu est figé pendant la recherche, c'est normal ; note la vitesse affichée).
3. Change ton argent (achète une Potion, gagne un combat), puis `refine <nouvelle somme>`.
4. Répète l'étape 3 jusqu'à avoir moins d'une dizaine d'adresses.
5. Confirme en direct : `watch 0x<adresse> --type u32`, puis dépense ou gagne de l'argent.

## Étape 3 — Stabilité de l'adresse
Refais `read 0x<adresse> --type u32` après chacune de ces actions :
- un changement de carte (entrer dans un bâtiment) ;
- une sauvegarde en jeu, puis un redémarrage (Emulation > Reboot Core) et le rechargement ;
- une fermeture complète de BizHawk (recharge ensuite le script connecteur).

Si l'adresse ne tient pas : `findptr 0x<adresse>` liste les valeurs qui pointent vers elle.

## Étape 4 — Sac (Potions)
D'après PKHeX 📖, chaque case du sac contient l'ID de l'objet (u16) puis la quantité (u16).
Lu comme un seul u32 : `quantité × 0x10000 + ID`. La Potion aurait l'ID 17 (`0x11`) 📖.
1. Avec par exemple 3 Potions : `find 0x00030011 --type u32`
2. Achète une Potion, puis `refine 0x00040011`. Répète jusqu'à avoir peu d'adresses.
   - Si rien ne sort : cherche seulement la quantité (`find 3 --type u16`), puis affine de la même façon.
3. **Savestate fait et dossier `3DS\User` copié ?** Menu fermé, passe à 5 Potions :
   `write 0x<adresse> u32 0x00050011`
4. Ouvre le sac : vois-tu 5 Potions ? Sauvegarde en jeu, redémarre : sont-elles toujours là ?

## Étape 5 — Drapeau d'un objet ramassé
Placé devant une Poké Ball au sol (pas encore ramassée) :
1. `snapshot avant 0x<argent - 0x80000> 0x100000`
2. Attends quelques secondes **sans rien faire**, puis `snapshot repos 0x<même adresse> 0x100000`
3. Ramasse l'objet, ferme le message, puis `snapshot apres 0x<même adresse> 0x100000`
4. `diff avant apres --bits --noise repos`

Recommence avec un deuxième objet. On cherche un bit qui passe de 0 à 1 à chaque fois,
à des adresses proches l'une de l'autre.

## Étape 6 (si tu arrives au premier badge) — Badge
Même méthode que l'étape 5, juste avant et juste après avoir battu Violette.

---

## Ce que tu me renvoies
- La sortie de `info`, la version du jeu (mise à jour ou non) et le format de ton dump.
- La vitesse affichée pendant `find`.
- Pour chaque adresse : ce qu'elle représente, son type, les valeurs observées et le
  résultat de chaque test de stabilité.
- Les sorties de `diff` des étapes 5 et 6.

Tu peux coller les sorties telles quelles : je complèterai `findings.md`.
