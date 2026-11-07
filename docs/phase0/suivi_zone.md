# Suivi du joueur par zone : trouver l'adresse de la zone courante

But : savoir dans quelle zone du jeu se trouve le joueur, pour que le tracker affiche « vous êtes ici ».
L'adresse mémoire de la zone courante est **encore inconnue** (voir `findings.md`, ligne « Carte / zone courante »).
Le code du tracker et du client viendra une fois l'adresse trouvée : on ne code pas une adresse inventée.

Hypothèse à vérifier : le jeu garde en mémoire le **numéro de zone** = numéro du fichier de zone dans `a/0/1/2`
(les mêmes numéros que ceux de la table ci-dessous, lus dans la ROM). Peut-être décalé de 1, ou stocké sur 16 ou 32 bits.

## Marche à suivre (BizHawk avec le script connecteur chargé, jeu **non** en pause)

1. Entre dans l'arène de Santalune (zone **56**). Dans un terminal, depuis le dossier du projet :
   `py -3.13 tools/bizhawk_probe.py find 56 --type u16`
   puis, si trop de résultats : `py -3.13 tools/bizhawk_probe.py find 56 --type u32`.
2. Sors de l'arène (zone de Santalune ville) : `py -3.13 tools/bizhawk_probe.py refine changed`.
3. Rentre dans l'arène : `py -3.13 tools/bizhawk_probe.py refine 56`.
4. Répète 2-3 avec d'autres lieux de la table (ex. arène de Cyllage = **160**, valeur à filtrer : `refine 160`).
5. Quand il reste moins de 10 adresses : `py -3.13 tools/bizhawk_probe.py watch <adresse> --type u16`
   et déplace-toi : la valeur doit changer à chaque changement de zone et valoir le numéro de la table.
6. Note l'adresse, le type, le domaine mémoire et si elle reste valable après chargement de la sauvegarde
   et après redémarrage du jeu dans `findings.md` (ligne « Carte / zone courante ») et envoie-la.

## Numéros de zone (lus dans la ROM)

| Zone | Lieu |
|---|---|
| 12 | Camphrier Town |
| 15 | Shabboneau Castle |
| 21 | Geosenge Town |
| 29 | Dendemille Town |
| 38 | Couriway Town |
| 45 | Ambrette Town |
| 56 | Santalune City (Gym) |
| 96 | Lysandre Lab |
| 100 | Lysandre Labs |
| 101 | Lysandre Labs |
| 157 | Cyllage City |
| 160 | Cyllage City (Gym) |
| 172 | Shalour City |
| 175 | Shalour City (Gym) |
| 188 | Coumarine City |
| 191 | Coumarine City (Gym) |
| 200 | Laverre City |
| 203 | Laverre City (Gym) |
| 215 | Anistar City (Gym) |
| 222 | Snowbelle City |
| 226 | Snowbelle City (Gym) |
| 233 | Kiloude City |
| 259 | Route 2 |
| 260 | Route 3 |
| 261 | Route 4 |
| 262 | Route 5 |
| 263 | Route 6 |
| 264 | Route 7 |
| 266 | Route 8 (Coast) |
| 267 | Route 9 |
| 268 | Route 10 |
| 269 | Route 11 |
| 270 | Route 12 |
| 272 | Route 13 |
| 273 | Route 14 |
| 275 | Route 15 |
| 276 | Route 16 |
| 278 | Route 17 |
| 279 | Route 18 |
| 281 | Route 19 |
| 282 | Route 20 |
| 283 | Route 21 |
| 285 | Route 22 |
| 286 | Santalune Forest |
| 287 | Parfum Palace |
| 297 | Parfum Palace |
| 302 | Parfum Palace |
| 303 | Glittering Cave |
| 304 | Glittering Cave |
| 305 | Reflection Cave (1F) |
| 306 | Reflection Cave (B1F) |
| 307 | Reflection Cave |
| 308 | Reflection Cave |
| 309 | Poké Ball Factory |
| 310 | PokeBall Factory |
| 313 | Frost Cavern |
| 314 | Frost Cavern (1F) |
| 315 | Frost Cavern |
| 316 | Frost Cavern (3F) |
| 317 | Frost Cavern |
| 318 | Pokémon Village |
| 322 | Victory Road (Inside 1) |
| 323 | Victory Road |
| 324 | Victory Road (Inside 2) |
| 325 | Victory Road |
| 326 | Victory Road (Inside 3) |
| 327 | Victory Road (Outside 4) |
| 328 | Victory Road (Inside 4) |
| 334 | Connecting Cave |
| 336 | Power Plant |
| 337 | Power Plant |
| 338 | Kalos Power Plant |
| 344 | Terminus Cave (B1F) |
| 345 | Terminus Cave |
| 346 | Terminus Cave |
| 347 | Terminus Cave |
| 348 | Terminus Cave |
| 349 | Lost Hotel |
| 350 | Chamber of Emptiness |
| 352 | Route 7 |
| 357 | Azure Bay |
