# Fiche couleurs : One Piece (essai)

Recherche automatique du 2026-11-23, tâche 2 du [plan](../../../../docs/PLAN.md). Aucune couleur n'a été demandée à une IA : chaque couleur est mesurée sur les pixels d'images officielles (couvertures japonaises des tomes, image AniList du personnage).

| | |
|---|---|
| **Temps total** | 10 min 16 s |
| **Images utilisées** | 23 : 9 images AniList et 14 couvertures japonaises, où 22 personnages ont été recadrés et mesurés (30 couvertures examinées sur 116, 193 têtes détectées) |
| **Personnages en doute** | 9 sur 10 |
| **Identité de la série** | recoupée : AniList 30013, MangaBaka (377) et MangaDex désignent la même série ; auteur Eiichirou Oda |
| **Découpage des parties** | modèle See-through |

Lecture : chaque partie porte trois tons, comme les fiches des coloristes d'animation : **base**, **ombre**, **reflet** (dans cet ordre sur les pastilles). La base est le ton le plus fréquent, jamais une moyenne ; sur plusieurs images, c'est le groupe de couleurs le plus nombreux qui l'emporte. **Confiance** : part des images d'accord, réduite quand elles sont peu nombreuses (1 image : 0,5 au plus ; 2 : 0,75 ; 3 : 0,88). Un personnage **automatique** sert sans question ; **à revoir** veut dire que le PC doute, pour la raison écrite.

## Personnages

- [Monkey D. Luffy](#al-40) : ⚠️ à revoir
- [Roronoa Zoro](#al-62) : ⚠️ à revoir
- [Nami](#al-723) : ⚠️ à revoir
- [Usopp](#al-724) : ⚠️ à revoir
- [Sanji](#al-305) : ✅ automatique
- [Nico Robin](#al-61) : ⚠️ à revoir
- [Tony Tony Chopper](#al-309) : ⚠️ à revoir
- [Franky](#al-64) : ⚠️ à revoir
- [Brook](#al-5627) : ⚠️ à revoir
- [Jinbe](#al-18938) : ⚠️ à revoir

<a id="al-40"></a>

## Monkey D. Luffy · モンキー・D・ルフィ

**État : à revoir** ⚠️

Raisons du doute :

- Cheveux : deux couleurs dans la zone mesurée (orange sur 4 image(s), noir sur 3), sans doute un chapeau ou le fond ; noir retenu parce que les mots de contrôle le confirment.
- Cheveux : les couvertures (noir) et l'image AniList (orange) ne s'accordent pas.
- Yeux : les 3 images ne s'accordent pas ; la couleur retenue vient d'une seule (couverture).

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b40-MNypXsxSRb1R.png" height="150" alt="image AniList"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/2e0e7bbd-6038-42ba-9691-f3ca7ba94590.png.256.jpg" height="150" alt="tome 96"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/67bfe0df-f92e-47a0-b467-122c0ac28bbc.png.256.jpg" height="150" alt="tome 60"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/b33a4105-8482-4e62-9b37-71e9092d6abe.png.256.jpg" height="150" alt="tome 17"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/349c740a-f9f7-419b-a877-a244d7d5ffb5.png.256.jpg" height="150" alt="tome 76">

Images sources (affichées depuis leur adresse d'origine) : image AniList ; tome 96, cadre (381, 1601, 843×659) ; tome 60, cadre (594, 1214, 492×831) ; tome 17, cadre (434, 1343, 1002×1275) ; tome 76, cadre (366, 1112, 625×818) ; tome 68, cadre (233, 1729, 414×652) ; tome 53, cadre (758, 1252, 898×1140) ; tome 64, cadre (493, 1178, 532×550) ; tome 9, cadre (89, 808, 880×431).

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-40-hair.svg) | `#030001` · — · `#e6dcd9` | 3 images sur 7 (couvertures) | 0,38 |
| Yeux | ![Yeux](pastilles/al-40-eyes.svg) | `#1b1104` · `#100500` · `#312413` | 1 image (couverture) | 0,17 |
| Peau | ![Peau](pastilles/al-40-skin.svg) | `#fbd5b0` · `#f8b392` · `#fde0c6` | 7 images sur 7 (couvertures) | 0,99 |

- Cheveux : mesure « noir » : d'accord (Danbooru noir 67 %, orange 24 %, blond 22 % ; wiki noir ×1).
- Yeux : mesure « noir » : d'accord (wiki noir ×1).
- Peau : mesure « claire » : d'accord.

Tenue courante : bas ![bottom](pastilles/al-40-outfit-bottom.svg) `#fb4b54`, 3 images sur 3 (couvertures). Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : orange `#e18666` (t. 60, t. 64, t. 76) ; jaune `#fceb71` (t. 17) ; blanc `#fbf6f8` (t. 68) ; bleu-vert `#2fbfc5` (t. 53).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#d48d56 / #b97c51 / #e99b6a` | — | `#fde5b6` | — | `#e7261e` |
| ref-02 : tome 96, cadre (381, 1601, 843×659) — écart 0,064 avec l'image AniList | `#fda246 / #f6772d / #f2ccaa` | — | `#feecd5` | — | — |
| ref-03 : tome 60, cadre (594, 1214, 492×831) — écart 0,068 avec l'image AniList | `#fefefe / #000000 / #010101` | — | `#fdd3b0` | `#e26f73` | `#f4807e` |
| ref-04 : tome 17, cadre (434, 1343, 1002×1275) — écart 0,073 avec l'image AniList | `#111833` | — | `#fbf1e6` | `#fceb71` | — |
| ref-05 : tome 76, cadre (366, 1112, 625×818) — écart 0,077 avec l'image AniList | `#050000` | — | `#fcbd9a` | `#e3855d` | — |
| ref-06 : tome 68, cadre (233, 1729, 414×652) — écart 0,080 avec l'image AniList | — | — | — | `#fbf6f8` | — |
| ref-07 : tome 53, cadre (758, 1252, 898×1140) — écart 0,085 avec l'image AniList | `#e8ba91 / #fc8988` | `#cfc2d4` | `#fde3cc` | `#2fbfc5` | `#fb4b54` |
| ref-08 : tome 64, cadre (493, 1178, 532×550) — écart 0,088 avec l'image AniList | `#d6ac7f` | `#7a7064` | `#fcd2a2` | `#f9a681` | — |
| ref-09 : tome 9, cadre (89, 808, 880×431) — écart 0,098 avec l'image AniList | `#030001 / #fcd7b2 / #84e7b0` | `#1b1104` | `#fbaf77` | — | — |

</details>

<a id="al-62"></a>

## Roronoa Zoro · ロロノア・ゾロ

**État : à revoir** ⚠️

Raisons du doute :

- Yeux : les 2 images ne s'accordent pas ; la couleur retenue vient d'une seule (couverture).

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b62-S7oAeA9WInjV.png" height="150" alt="image AniList"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/2f4aca53-64c7-46ac-ae85-3bc9b3169890.png.256.jpg" height="150" alt="tome 1"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/5eec93a4-41ae-40c7-a2b4-ca5a951149ff.png.256.jpg" height="150" alt="tome 9"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/349c740a-f9f7-419b-a877-a244d7d5ffb5.png.256.jpg" height="150" alt="tome 76"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/875ee51d-bed5-4224-b9d0-ce8579d2167b.png.256.jpg" height="150" alt="tome 92">

Images sources (affichées depuis leur adresse d'origine) : image AniList ; tome 1, cadre (1164, 1553, 371×418) ; tome 9, cadre (170, 1114, 681×578) ; tome 76, cadre (328, 475, 539×632) ; tome 92, cadre (147, 1785, 579×663) ; tome 5, cadre (900, 1158, 280×290) ; tome 37, cadre (991, 1570, 273×291).

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-62-hair.svg) | `#92daaa` · `#88ba70` · `#ebf4eb` | 2 images sur 2 (couvertures) | 0,75 |
| Yeux | ![Yeux](pastilles/al-62-eyes.svg) | `#614c33` · `#4d3a24` · `#796042` | 1 image (couverture) | 0,25 |
| Peau | ![Peau](pastilles/al-62-skin.svg) | `#f6b67a` · `#ea9d61` · `#fbf3e0` | 2 images sur 2 (couvertures) | 0,75 |

- Cheveux : mesure « vert » : d'accord (Danbooru vert 72 %, noir 34 %, blond 31 % ; wiki vert ×1).
- Yeux : mesure « brun » : aucun mot trouvé.
- Peau : mesure « claire » : d'accord (wiki hâlée ×1).

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : blanc `#fcfae7` (AniList).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#9dcea7 / #74bc7a` | `#12100f` | `#f0ba78` | `#fcfae7` | — |
| ref-02 : tome 1, cadre (1164, 1553, 371×418) — écart 0,060 avec l'image AniList | — | — | — | — | — |
| ref-03 : tome 9, cadre (170, 1114, 681×578) — écart 0,072 avec l'image AniList | `#84e7ae / #9ab765` | `#614c33` | `#fcb17c` | — | — |
| ref-04 : tome 76, cadre (328, 475, 539×632) — écart 0,074 avec l'image AniList | — | — | — | — | — |
| ref-05 : tome 92, cadre (147, 1785, 579×663) — écart 0,105 avec l'image AniList | — | — | — | — | — |
| ref-06 : tome 5, cadre (900, 1158, 280×290) — écart 0,106 avec l'image AniList | — | — | — | — | — |
| ref-07 : tome 37, cadre (991, 1570, 273×291) — écart 0,111 avec l'image AniList | — | — | — | — | — |

</details>

<a id="al-723"></a>

## Nami · ナミ

**État : à revoir** ⚠️

Raisons du doute :

- Yeux : la couleur ne repose que sur une image (couverture).
- Yeux : mesure « gris » ; Danbooru dit surtout « brun » (30 %), « orange » (20 %) ; le wiki dit « brun ».

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b723-vp5hPptgnNEC.png" height="150" alt="image AniList"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/5eec93a4-41ae-40c7-a2b4-ca5a951149ff.png.256.jpg" height="150" alt="tome 9"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/4451e697-e861-47fc-b01e-958b305701b5.png.256.jpg" height="150" alt="tome 37"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/e74a384f-21f6-4cd4-8511-0a3a63ea0de3.png.256.jpg" height="150" alt="tome 88"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/e90a28a5-12ff-441c-9b7a-2f38d32441dd.png.256.jpg" height="150" alt="tome 5">

Images sources (affichées depuis leur adresse d'origine) : image AniList ; tome 9, cadre (662, 602, 976×2016) ; tome 37, cadre (700, 1792, 432×722) ; tome 88, cadre (968, 583, 688×1004) ; tome 5, cadre (1043, 799, 512×510) ; tome 49, cadre (448, 1675, 267×301) ; tome 64, cadre (953, 1128, 324×355).

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-723-hair.svg) | `#fc9050` · `#dc6e3b` · `#f7dfba` | 6 images sur 6 (couvertures) | 0,98 |
| Yeux | ![Yeux](pastilles/al-723-eyes.svg) | `#a0907d` · `#332f2b` · `#bca793` | 1 image (couverture) | 0,50 |
| Peau | ![Peau](pastilles/al-723-skin.svg) | `#fcdfc2` · `#f7c19f` · `#fcf3e4` | 6 images sur 6 (couvertures) | 0,98 |

- Cheveux : mesure « orange » : d'accord (Danbooru orange 85 %, noir 27 %, blond 14 % ; wiki noir ×1, orange ×1).
- Yeux : mesure « gris » : en désaccord (Danbooru brun 30 %, orange 20 % ; wiki brun ×1).
- Peau : mesure « très claire » : d'accord.

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : blanc `#fcfcfc` (t. 37, AniList) ; orange `#f6b584` (t. 9) ; jaune `#fee054` (t. 88).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#e55642 / #f1e5e5 / #a53f34` | — | `#fcb7ab` | `#fcfafb` | — |
| ref-02 : tome 9, cadre (662, 602, 976×2016) — écart 0,087 avec l'image AniList | `#84e7b0 / #f46830` | — | `#fbdebe` | `#f6b584` | — |
| ref-03 : tome 37, cadre (700, 1792, 432×722) — écart 0,090 avec l'image AniList | `#f56f53 / #f98d5d / #d76251` | — | `#fbd6b8` | `#fdfdfd` | — |
| ref-04 : tome 88, cadre (968, 583, 688×1004) — écart 0,071 avec un autre recadrage | `#fca364 / #f78653` | — | `#fcead6` | `#fee054` | — |
| ref-05 : tome 5, cadre (1043, 799, 512×510) — écart 0,071 avec l'image AniList | `#ffffff / #c8dcf2 / #fb7b3a` | — | `#fce1c6` | — | — |
| ref-06 : tome 49, cadre (448, 1675, 267×301) — écart 0,113 avec l'image AniList | `#f9b365 / #f97f50 / #e19e5a` | — | `#fef8df` | — | — |
| ref-07 : tome 64, cadre (953, 1128, 324×355) — écart 0,069 avec un autre recadrage | `#fcac60 / #c6c1aa` | `#a0907d` | `#fdd2a3` | — | — |

</details>

<a id="al-724"></a>

## Usopp · ウソップ

**État : à revoir** ⚠️

Raisons du doute :

- Cheveux : la couleur ne repose que sur une image (image AniList).
- Cheveux : mesure « bleu » ; Danbooru dit surtout « noir » (67 %), « blond » (48 %) ; le wiki dit « noir ».
- Peau : la couleur ne repose que sur une image (image AniList).

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b724-GFGgI9AJQkfy.jpg" height="150" alt="image AniList">

Images sources (affichées depuis leur adresse d'origine) : image AniList.

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-724-hair.svg) | `#2d3baa` · — · `#185bb1` | 1 image (image AniList) | 0,50 |
| Peau | ![Peau](pastilles/al-724-skin.svg) | `#f4d37e` · `#ebb865` · `#f5f0ed` | 1 image (image AniList) | 0,50 |

- Cheveux : mesure « bleu » : en désaccord (Danbooru noir 67 %, blond 48 %, orange 48 % ; wiki noir ×1).
- Peau : mesure « claire » : d'accord (Danbooru colorée 11 %, bleu 10 %).

Non mesuré : yeux (trop peu de pixels nets sur les images trouvées ; le moteur choisira).

Tenue : pas assez d'images du corps entier pour la mesurer.

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#2d3baa / #dac723 / #185bb1` | — | `#f4d37e` | — | — |

</details>

<a id="al-305"></a>

## Sanji · サンジ

**État : automatique** ✅

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b305-6lisPmHtCnLT.png" height="150" alt="image AniList"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/5eec93a4-41ae-40c7-a2b4-ca5a951149ff.png.256.jpg" height="150" alt="tome 9"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/d22dc109-d731-4d3d-901a-4b90051e79f0.png.256.jpg" height="150" alt="tome 100"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/b33a4105-8482-4e62-9b37-71e9092d6abe.png.256.jpg" height="150" alt="tome 17"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/e74a384f-21f6-4cd4-8511-0a3a63ea0de3.png.256.jpg" height="150" alt="tome 88">

Images sources (affichées depuis leur adresse d'origine) : image AniList ; tome 9, cadre (98, 1994, 664×415) ; tome 100, cadre (125, 1604, 627×1002) ; tome 17, cadre (90, 1686, 545×932) ; tome 88, cadre (0, 1053, 556×517) ; tome 64, cadre (243, 1416, 314×350) ; tome 13, cadre (459, 1839, 722×675).

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-305-hair.svg) | `#deae53` · `#c5933e` · `#f5d889` | 5 images sur 5 (couvertures) | 0,97 |
| Yeux | ![Yeux](pastilles/al-305-eyes.svg) | `#917868` · `#735d54` · `#c8b2a5` | 2 images sur 3 (couvertures) | 0,50 |
| Peau | ![Peau](pastilles/al-305-skin.svg) | `#f8d5b5` · `#f6bb9a` · `#fbefe1` | 5 images sur 5 (couvertures) | 0,97 |

- Cheveux : mesure « blond » : d'accord (Danbooru blond 76 %, vert 33 %, noir 27 % ; wiki blond ×1).
- Yeux : mesure « gris » : d'accord (Danbooru bleu 15 % ; wiki gris ×1, bleu ×1, brun ×1).
- Peau : mesure « claire » : d'accord.

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : noir `#08010d` (AniList) ; blanc `#d3e5d0` (t. 9) ; rouge `#9a3640` (t. 100) ; noir `#2f2c3f` (t. 17) / bas : rouge `#9e3640` (t. 100).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#e0cf53 / #f4f2ef / #330812` | `#ab846e` | `#f7ccb2` | `#08010d` | — |
| ref-02 : tome 9, cadre (98, 1994, 664×415) — écart 0,082 avec l'image AniList | `#c7963a / #ddb042` | `#402c11` | `#fbbf8b` | `#d3e5d0` | — |
| ref-03 : tome 100, cadre (125, 1604, 627×1002) — écart 0,089 avec l'image AniList | `#f7c849` | — | `#fdddc2` | `#9a3640` | `#9e3640` |
| ref-04 : tome 17, cadre (90, 1686, 545×932) — écart 0,090 avec l'image AniList | `#988451 / #b29957 / #826f4e` | `#776c63` | `#fbd1b4` | `#2f2c3f` | — |
| ref-05 : tome 88, cadre (0, 1053, 556×517) — écart 0,113 avec l'image AniList | `#f3bd53 / #fbd76a` | — | `#fdecda` | — | — |
| ref-06 : tome 64, cadre (243, 1416, 314×350) — écart 0,080 avec l'image AniList | `#ba9b6c / #fa997e / #d7b47e` | — | `#fdd4a7` | — | — |
| ref-07 : tome 13, cadre (459, 1839, 722×675) — écart 0,113 avec l'image AniList | — | — | — | — | — |

</details>

<a id="al-61"></a>

## Nico Robin · ニコロビン

**État : à revoir** ⚠️

Raisons du doute :

- Cheveux : la couleur ne repose que sur une image (image AniList).
- Yeux : la couleur ne repose que sur une image (image AniList).
- Yeux : mesure « noir » ; Danbooru dit surtout « bleu » (37 %).
- Peau : la couleur ne repose que sur une image (image AniList).

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b61-ywXUyyocEEqt.png" height="150" alt="image AniList">

Images sources (affichées depuis leur adresse d'origine) : image AniList.

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-61-hair.svg) | `#161720` · `#0a0b0f` · `#282c3f` | 1 image (image AniList) | 0,50 |
| Yeux | ![Yeux](pastilles/al-61-eyes.svg) | `#100e0d` · `#020202` · `#02454c` | 1 image (image AniList) | 0,50 |
| Peau | ![Peau](pastilles/al-61-skin.svg) | `#f0cbb0` · `#d8a48f` · — | 1 image (image AniList) | 0,50 |

- Cheveux : mesure « noir » : d'accord (Danbooru noir 75 %, orange 24 %, blond 12 % ; wiki noir ×2).
- Yeux : mesure « noir » : en désaccord (Danbooru bleu 37 %).
- Peau : mesure « claire » : d'accord.

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : violet `#460e5c` (AniList).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#282c3f / #161720` | `#100e0d` | `#f0cbb0` | `#460e5c` | — |

</details>

<a id="al-309"></a>

## Tony Tony Chopper · トニートニー・チョッパー

**État : à revoir** ⚠️

Raisons du doute :

- Cheveux : la couleur ne repose que sur une image (image AniList).
- Peau : la couleur ne repose que sur une image (image AniList).

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b309-H64NhbJ2ywIQ.jpg" height="150" alt="image AniList">

Images sources (affichées depuis leur adresse d'origine) : image AniList.

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-309-hair.svg) | `#fa6180` · `#ca4262` · `#fefefe` | 1 image (image AniList) | 0,50 |
| Peau | ![Peau](pastilles/al-309-skin.svg) | `#fdd792` · `#c48566` · — | 1 image (image AniList) | 0,50 |

- Cheveux : mesure « rouge » : d'accord (Danbooru noir 50 %, blond 36 %, orange 35 %).
- Peau : mesure « claire » : d'accord.

Non mesuré : yeux (trop peu de pixels nets sur les images trouvées ; le moteur choisira).

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : bleu `#5a5da4` (AniList).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#fa6180 / #ca4262` | — | `#fdd792` | `#5a5da4` | — |

</details>

<a id="al-64"></a>

## Franky · フランキー

**État : à revoir** ⚠️

Raisons du doute :

- Cheveux : les couvertures (bleu) et l'image AniList (blanc) ne s'accordent pas.

<img src="https://s4.anilist.co/file/anilistcdn/character/large/n64-ChX6ZzHHjXqA.png" height="150" alt="image AniList"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/3c5b0206-52a2-44ad-bce5-bd7acb385934.png.256.jpg" height="150" alt="tome 64"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/81362302-608a-4efa-8744-0df6f8cbde7f.png.256.jpg" height="150" alt="tome 84"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/4451e697-e861-47fc-b01e-958b305701b5.png.256.jpg" height="150" alt="tome 37"> <img src="https://uploads.mangadex.org/covers/a1c7c817-4e59-43b7-9365-09675a149a6f/875ee51d-bed5-4224-b9d0-ce8579d2167b.png.256.jpg" height="150" alt="tome 92">

Images sources (affichées depuis leur adresse d'origine) : image AniList ; tome 64, cadre (609, 545, 497×446) ; tome 84, cadre (946, 1476, 710×1130) ; tome 37, cadre (99, 561, 811×886) ; tome 92, cadre (533, 1768, 649×826).

| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |
|---|---|---|---|---|
| Cheveux | ![Cheveux](pastilles/al-64-hair.svg) | `#589dc9` · `#4788af` · `#6db4da` | 2 images sur 2 (couvertures) | 0,75 |
| Yeux | ![Yeux](pastilles/al-64-eyes.svg) | `#231d1c` · — · `#a29895` | 2 images sur 2 (couvertures) | 0,75 |
| Peau | ![Peau](pastilles/al-64-skin.svg) | `#f5caa3` · `#e6ac86` · `#f9e4cc` | 2 images sur 3 (couvertures) | 0,50 |

- Cheveux : mesure « bleu » : d'accord (Danbooru noir 57 %, bleu 52 %, blond 46 % ; wiki bleu ×1).
- Yeux : mesure « noir » : aucun mot trouvé (Danbooru bleu 11 %).
- Peau : mesure « claire » : mots trop rares pour trancher (Danbooru colorée 18 %, bleu 17 %).

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : noir `#26313d` (t. 84) / bas : noir `#2f3a45` (t. 84).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | `#b9d9dd` | `#2a201e` | `#f3cb9e` | — | — |
| ref-02 : tome 64, cadre (609, 545, 497×446) — écart 0,073 avec l'image AniList | `#6dafcf / #86c4dd` | `#1b1a19` | `#d69d7a` | — | — |
| ref-03 : tome 84, cadre (946, 1476, 710×1130) — écart 0,086 avec l'image AniList | `#438bc3 / #2ab4aa` | — | `#f7c9a7` | `#26313d` | `#2f3a45` |
| ref-04 : tome 37, cadre (99, 561, 811×886) — écart 0,057 avec l'image AniList | — | — | — | — | — |
| ref-05 : tome 92, cadre (533, 1768, 649×826) — écart 0,067 avec l'image AniList | — | — | — | — | — |

</details>

<a id="al-5627"></a>

## Brook · ブルック

**État : à revoir** ⚠️

Raisons du doute :

- Aucune couleur de cheveux, d'yeux ni de peau n'a pu être mesurée : le découpage n'a pas trouvé de visage sur les images de ce personnage.

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b5627-av8oD3zhKvDl.png" height="150" alt="image AniList">

Images sources (affichées depuis leur adresse d'origine) : image AniList.

Non mesuré : cheveux, yeux, peau (trop peu de pixels nets sur les images trouvées ; le moteur choisira).

Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : haut : bleu `#3f73e4` (AniList) / bas : bleu `#386bd8` (AniList).

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | — | — | — | `#3f73e4` | `#386bd8` |

</details>

<a id="al-18938"></a>

## Jinbe · ジンベエ

**État : à revoir** ⚠️

Raisons du doute :

- Aucune couleur de cheveux, d'yeux ni de peau n'a pu être mesurée : le découpage n'a pas trouvé de visage sur les images de ce personnage.

<img src="https://s4.anilist.co/file/anilistcdn/character/large/b18938-yZANEfjsVhW4.png" height="150" alt="image AniList">

Images sources (affichées depuis leur adresse d'origine) : image AniList.

Non mesuré : cheveux, yeux, peau (trop peu de pixels nets sur les images trouvées ; le moteur choisira).

Tenue : pas assez d'images du corps entier pour la mesurer.

<details><summary>Mesures image par image</summary>

| Image | Cheveux | Yeux | Peau | Haut | Bas |
|---|---|---|---|---|---|
| ref-01 : image AniList | — | — | — | — | — |

</details>

## Fichiers

La fiche elle-même, rangée comme le prévoit le § 3 de la [spécification](../../../../docs/specs/colorisation-fidele.md) : [`series.json`](series.json), `characters/<id>/character.json`, [`journal.jsonl`](journal.jsonl). Les recadrages (`refs/`) restent sur la machine qui a fait la recherche : ils ne sont jamais copiés dans le dépôt.

Temps par étape : identité et mots de contrôle 40 s ; téléchargement des images 45 s ; reconnaissance des personnages 2 min 35 s ; découpage et mesure des couleurs 6 min 16 s ; fiche 0 s.

