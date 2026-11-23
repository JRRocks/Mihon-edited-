# Colorisation fidèle : la logique

État : proposition du 2026-11-22, questions répondues le même jour (D10 à D13), feu vert donné (D16). La recherche
de la fiche (§ 3 et 4) est codée dans `tools/colorization-server/color_sheet.py` (tâche 2, D30 à D34) ; le reste ne
l'est pas encore.
Ce qui existe aujourd'hui est décrit dans `CLAUDE.md` (moteurs `guided`, `flux`, `mc2`).

## 1. Le défaut à corriger

Le téléphone envoie les pages une par une et le serveur les colorie sans mémoire :

- il ne sait pas quels personnages sont sur la page ;
- il ne connaît que quatre couleurs par série (peau, ciel, feuillage, eau), devinées par une IA à partir du titre ;
- rien ne relie une page à la suivante.

Les personnages n'ont donc pas leurs couleurs officielles, et ils changent de couleur d'une page à l'autre.

## 2. Le principe

Apprendre la série avant de colorier, savoir qui est dans chaque case pendant, vérifier après.

| Étape | Ce que fait le PC | Quand |
|---|---|---|
| 1. Fiche de série | Cherche les personnages et leurs couleurs officielles, les range | Une fois par série, avant tout coloriage |
| 2. Lecture du chapitre | Reçoit le chapitre entier ; repère cases, bulles, personnages, scènes | À chaque chapitre, avant de colorier |
| 3. Coloriage | Colorie case par case, avec la référence des seuls personnages présents | Page par page |
| 4. Verrou | Ramène les couleurs des personnages reconnus aux valeurs de la fiche | Après chaque page |
| 5. Contrôle | Mesure l'écart avec la fiche ; refait ou signale une page douteuse | Après chaque page |
| 6. Mémoire | Note ce qui a été décidé (inconnus, lieux) pour la suite | Fin de chapitre |

Règles fixes :

1. **Une couleur est un nombre rangé dans la fiche, avec sa source.** Elle est mesurée sur une image officielle,
   jamais demandée à une IA (les modèles qui regardent une image donnent le bon code couleur dans 28 à 56 % des cas,
   ColorBench 2025).
2. **Ordre de confiance des sources** : correction de l'utilisateur > pages couleur du manga lui-même > couvertures
   des tomes > anime et visuels officiels > page déjà validée > couleur inventée et notée > réglage par défaut.
3. **Doute sur l'identité = aucune couleur imposée.** Un personnage mal reconnu avec la couleur d'un autre est pire
   qu'un personnage laissé au choix du moteur.
4. **Une page générée n'enseigne jamais une couleur officielle.** Les couleurs officielles ne viennent que de
   sources officielles ou de l'utilisateur.
5. **Un inconnu se décide une fois.** Sa couleur est choisie à sa première apparition, notée, et resservie.
6. **La fiche se corrige par ajout daté**, jamais par réécriture : on sait toujours d'où vient une couleur.
7. **Une page n'est recoloriée que si quelque chose a changé** : la page, les entrées de fiche utilisées, ou le moteur.

## 3. Comment les références sont rangées

Sur le PC, hors du dépôt et hors du cache des modèles (supprimer le cache ne doit pas effacer les fiches) :
`%USERPROFILE%\Documents\Mihon colorisation\series\<clé de la série>\`

```
series/<titre>--al<identifiant AniList>/
  series.json                 identité : titres, auteur, identifiants (AniList, MyAnimeList, MangaDex), sources
                              consultées et dates, style d'ensemble, état (automatique / validée)
  characters/<id>/
    character.json            noms, rôle, couleurs par partie, tenues, mots de contrôle, état
    refs/ref-NN.png           images officielles en couleur, recadrées sur le personnage, avec leur provenance
    bw/bw-NN.png              exemples en noir et blanc tirés du manga : ils servent à le reconnaître
  pages-ref/<empreinte>.webp  pages couleur du manga et couvertures entières
  locations/<id>.json         lieux récurrents : couleurs des grandes surfaces
  lighting.json               ambiances nommées (jour, nuit, coucher de soleil, intérieur sombre, flashback)
  chapters/<clé du chapitre>/
    scenes.json               table des scènes : pages, lieu, ambiance, tenue de chaque personnage
    pages/<empreinte>.json    qui est où (cadre, personnage ou « inconnu n », score), couleurs données aux
                              inconnus, résultat du contrôle, empreinte de coloriage
  journal.jsonl               une ligne par changement de la fiche : quoi, d'où, quand
```

Une partie de personnage (cheveux, yeux, peau, chaque vêtement) porte trois tons, comme les fiches des coloristes
d'animation : base, ombre, reflet. Exemple avec un personnage inventé :

```json
{
  "id": "al-000000",
  "names": { "main": "Aya Mizuno", "aliases": ["Aya"] },
  "role": "main",
  "status": "automatic",
  "parts": {
    "hair": { "base": "#2aa79b", "shadow": "#1c7f78", "highlight": "#6fd6c8",
              "source": "ref-03", "kind": "volume_cover", "confidence": 0.92, "locked": true },
    "eyes": { "base": "#d98a1f", "source": "ref-03", "kind": "volume_cover", "confidence": 0.80, "locked": true },
    "skin": { "base": "#f6d3bd", "shadow": "#e2b29a", "source": "ref-01", "kind": "anime", "confidence": 0.90,
              "locked": true }
  },
  "outfits": [
    { "id": "default", "name": "tenue courante", "chapters": [1, null],
      "parts": { "top": { "base": "#b3202c", "shadow": "#7f1620" }, "bottom": { "base": "#1f2a4d" } } }
  ],
  "words": { "hair": ["aqua", "green"], "eyes": ["orange", "yellow"], "from": ["danbooru", "fandom"] },
  "refs": [ { "id": "ref-03", "kind": "volume_cover", "volume": 2, "origin": "mangadex", "added": "2026-11-22" } ]
}
```

États d'un personnage : `automatic` (trouvé et mesuré par le PC), `to_review` (sources en désaccord ou trop peu
d'images), `validated` (vu par l'utilisateur), `provisional` (inconnu rencontré dans un chapitre, couleur inventée).

Qui valide (D11, D14) : l'utilisateur n'est sollicité que quand le PC doute. Le PC doute, et passe le personnage en
`to_review`, quand une couleur ne repose que sur une image, quand deux sources se contredisent (mesure contre mots
de contrôle, couverture contre anime), quand aucune image en couleur n'est trouvée, ou quand l'identité de la série
n'est pas recoupée par deux bases. Une fiche `automatic` sert sans question. Elle reste consultable et corrigeable à
tout moment, et une correction refait les chapitres concernés.

Deux sortes de références pour un même personnage, parce qu'elles ne servent pas à la même chose :

- **couleur** (`refs/`) : nourrit le moteur et donne les nombres de la fiche ;
- **noir et blanc** (`bw/`) : sert à le reconnaître dans les pages. Les images d'anime reconnaissent mal un dessin de
  manga (73 à 75 % avec un exemple quelconque, 87 à 88 % avec un bon exemple tiré du manga, d'après les auteurs de
  Magi v2).

## 4. La recherche des personnages et des couleurs officielles

Tout se fait par des bases publiques, sans compte et sans clé. Vérifié en direct le 2026-11-22.

| Besoin | Source | Ce qu'elle donne | Limite constatée |
|---|---|---|---|
| Reconnaître la série | Identifiant de suivi du téléphone s'il existe ; sinon MangaBaka (`api.mangabaka.org` depuis novembre 2026, l'ancienne adresse `api.mangabaka.dev` ne répond plus) et AniList (recherche par titre) ; MangaDex (ses `links` donnent les identifiants AniList, MyAnimeList, MangaUpdates, Kitsu) | Une clé sûre pour la série, et l'existence ou non d'un anime | Titres ambigus, hors-séries, éditions coloriées par des amateurs : le PC exige le même identifiant dans deux sources et compare l'auteur |
| Liste des personnages | AniList | Nom, nom japonais, surnoms, rôle (principal, secondaire), une image | 30 requêtes par minute |
| Images officielles en couleur | 1. pages couleur du manga, envoyées par le téléphone · 2. couvertures de tomes en japonais (MangaDex) · 3. image du personnage (AniList) | Dessins de l'auteur, puis de l'anime | Série à l'anime installé (Frieren) : 10 images de personnage sur 10 en couleur. Série récente (Kagurabachi) : 7 sur 10 sans aucune couleur. D'où le passage par les couvertures de tomes en japonais : 16 pour Frieren, 12 pour Kagurabachi, 37 pour Vagabond (recompté le 2026-11-22) |
| Mots de contrôle | Étiquettes Danbooru du personnage (cheveux, yeux, vêtements, avec leur fréquence), encadré du wiki Fandom | « cheveux blancs 53 %, gris 35 % », « hair = Silver » | Étiquettes mêlées à celles des personnages dessinés à côté ; encadré absent de beaucoup de wikis ; mentions « (Manga) / (Anime) » à lire |

Écartés pour cette recherche : Jikan (service public arrêté le 2026-10-01, annonce lue dans son dépôt), Wikidata
(couleurs renseignées pour une minorité de personnages), images de Danbooru (dessins d'amateurs : on ne garde que
les mots), éditions marquées « Fan Colored ».

Mesure des couleurs sur une image officielle :

1. écarter les images en noir et blanc, garder un seul personnage par recadrage ;
2. découper les parties (cheveux, visage, yeux, haut, bas) ;
3. retirer le trait et les bords, travailler dans un espace de couleur perceptuel (OKLab) ;
4. prendre le ton le plus fréquent, pas la moyenne (la moyenne mélange base et ombre en une couleur qui n'existe pas) ;
5. sur plusieurs images, garder la valeur du groupe le plus dense ; deux groupes stables deviennent deux variantes
   nommées (manga et anime, deux tenues) ;
6. traduire le résultat en mot (« bleu-vert ») et le comparer aux mots de contrôle : un désaccord passe le
   personnage en `to_review`.

Pièges connus : couleurs de l'anime différentes de celles du manga (la règle 2 tranche), tenues qui changent selon
l'arc (une tenue porte une plage de chapitres), mauvais wiki pour un titre homonyme (exiger que les personnages
principaux y aient leur page), divulgâchage par les fiches de personnages (la fiche de validation ne montre que
les personnages déjà rencontrés).

## 5. La lecture du chapitre

Le chapitre est analysé en entier avant le premier coloriage, et le résultat est gardé.

- **Structure** : cases, bulles, textes.
- **Personnages** : cadres des personnages, puis nom pris dans la fiche. Le modèle retenu pour l'essai (Magi v2)
  travaille sur un chapitre entier et s'appuie sur les liens « même personnage » d'une page à l'autre.
- **Seuil et écart** : un nom n'est retenu que si son score dépasse un seuil et devance nettement le second. Sinon
  le personnage est « inconnu n » pour ce chapitre.
- **Échelle de reconnaissance** (D27 à D29, D36, après l'échec de Magi v2 et de CCIP sur le chapitre 1192) : un
  personnage que l'échelon courant ne nomme pas avec assurance passe à une IA plus grosse. D'abord les IA du PC
  (Magi v2 et CCIP, puis des modèles plus gros, chacun téléchargé avec l'accord de l'utilisateur) ; ensuite Claude
  par internet, de Haiku à Sonnet, Opus puis Fable, qui reçoit la page avec ses cadres numérotés et les images de la
  fiche. Chaque échelon répond « sûr » ou « incertain » ; seul « sûr » arrête la montée. Ce qu'aucun échelon ne
  tranche attend Claude en session, avec l'utilisateur, et le chapitre n'est colorié qu'ensuite (D29). Une IA ne
  donne qu'un nom : les couleurs restent celles de la fiche (D2, D36).
  Après les essais du chapitre 1192 : un nom est retenu quand deux échelons successifs le donnent (D37), un « ? »
  n'en est pas un (D40). Le PC trouve les personnages : cadres de Magi v2, plus ceux du détecteur Manga109 qui ne
  recouvrent aucun cadre de Magi ; les noms viennent des échelons Claude, car CCIP et l'étiqueteur Danbooru ne
  nomment presque rien en noir et blanc (D25, D39).
- **Exemples noir et blanc** : un recadrage n'entre dans la fiche que s'il est appuyé par un autre recadrage déjà
  classé dans le même groupe de pages, ou validé par l'utilisateur. L'ajout automatique au meilleur score se trompe
  dans 62 à 89 % des cas (Re:Cognize, 2026).
- **Scènes** : pages consécutives du même lieu et de la même ambiance. Une ambiance est une variante nommée,
  dérivée de la couleur de base, la même pour toute la scène.

## 6. Le coloriage

Le moteur reçoit la case et les références ; on ne garde de sa réponse que les couleurs, posées sous le trait
d'origine (c'est déjà le cas du moteur `flux`).

- **Case par case**, avec la référence des seuls personnages présents. Une planche qui montre tous les personnages
  fait échanger leurs couleurs (constaté à l'essai du 2026-11-22, voir § 9).
- **Même graine et mêmes réglages** pour tout un chapitre.
- **Empreinte de coloriage** : page + entrées de fiche utilisées + moteur et réglages.

Moteurs candidats, à départager sur de vraies pages :

| Moteur | État | Ce qu'on en sait |
|---|---|---|
| FLUX.2 klein 4B (déjà installé) | Essayé ici | Suit la référence ; 12 s par page sans référence, 21 s avec une référence (768 × 1088) |
| FLUX.2 klein 9B + complément « manga colorization by reference » | À télécharger (environ 11 Go) | Seul modèle entraîné pour « page + planche de référence ». Rapporté : 14 s par page sur un portable 6 Go. Licence non commerciale |
| FLUX 3 Image Klein | À télécharger (environ 7 Go) | Jusqu'à 10 références. Rapporté : 81 s par retouche sur un portable 8 Go. Aucun essai de colorisation publié |

## 7. Le verrou et le contrôle

- **Verrou** : pour un personnage reconnu, chaque partie reçoit la couleur de la fiche. La luminosité de la page
  d'origine est gardée ; le ton d'ombre de la fiche sert sous la trame.
- **Garde-fous** : bulles blanches, papier blanc, peau dans la plage des tons de peau.
- **Contrôle** : écart mesuré entre chaque partie coloriée et la fiche. Sous le seuil, la page est bonne ; sinon
  elle est refaite une fois, puis signalée. Le téléphone reçoit le bilan du chapitre (« 18 pages sûres, 2 à vérifier »).

## 8. Le dialogue entre le téléphone et le PC

À remplacer : `POST /colorize`, une page à la fois, avec le seul titre de la série.

| Appel | Rôle |
|---|---|
| `POST /series` | Le téléphone décrit la série (titre, auteur, source, adresse de la couverture, identifiants de suivi). Réponse : clé de la série, état de la fiche |
| `POST /chapters` | Ouvre un travail pour un chapitre (numéro, nom, nombre de pages) |
| `PUT /jobs/<id>/pages/<n>` | Envoie une page. Les pages déjà en couleur sont envoyées aussi : ce sont les meilleures références |
| `POST /jobs/<id>/start` | Lance la lecture du chapitre puis le coloriage |
| `GET /jobs/<id>` et `GET /jobs/<id>/pages/<n>` | Avancement, bilan, pages coloriées |
| `GET /series/<clé>/card` | Fiche couleurs à ouvrir dans le navigateur du téléphone |

`POST /colorize` reste en place comme mode de secours sans mémoire.

Pour la preuve (partie 1 du plan), les pages d'essai arrivent par cet appel existant : le serveur, lancé avec une
option de capture, garde les pages reçues et le titre de la série (D13). L'application ne lui envoie pas les pages
qu'elle juge déjà en couleur : celles-ci ne serviront de référence qu'avec le nouveau dialogue.

## 9. Vérifié, et pas encore

Vérifié sur ce PC le 2026-11-22 (carte NVIDIA RTX 4070 Laptop, 8 Go ; 16 Go de mémoire) :

- les sources du § 4 répondent sans compte et donnent ce qui est décrit ;
- le serveur de modèles déjà installé accepte plusieurs images de référence (lu dans son code, puis essayé) ;
- essai sur une page et deux personnages inventés, dessinés par le modèle lui-même (cas facile, sans trame) :
  l'écart de couleur avec la page d'origine passe de 35 à 17 quand on ajoute la planche de référence, mais les
  vêtements et les yeux s'échangent entre les deux personnages ; avec une bande à la fois et la référence des seuls
  personnages présents, cheveux, yeux et vêtements sont justes sur les deux bandes à un personnage ; la bande du
  haut, où les deux sont ensemble et qui a reçu la planche entière, garde une case fausse (veste et œil). La mesure
  globale, elle, ne bouge presque pas d'une méthode à l'autre : elle est dominée par les décors.

Pas encore vérifié :

- tout ce qui concerne de vraies pages de manga (trame, scans, petits personnages) ;
- la reconnaissance des personnages sur ce PC (chiffres publiés : 73 à 93 % selon les exemples fournis) ;
- le découpage des parties sur du noir et blanc tramé (aucune mesure publiée) ;
- les deux moteurs à télécharger ;
- le temps par chapitre de la chaîne complète.

## 10. Briques externes

Relevées sur leur page le 2026-11-22. Aucune n'est intégrée.

| Brique | Rôle | Licence | Poids | État |
|---|---|---|---|---|
| [Magi v2](https://huggingface.co/ragavsachdeva/magiv2) | Cases, textes, personnages nommés à partir d'une banque d'exemples, sur un chapitre entier | Usage personnel, recherche, non commercial (fiche du modèle) ; pas de fichier de licence dans le dépôt | 2 Go | Essayé le 2026-11-23 (tâche 3, D24) sur le chapitre 1192 de One Piece : 0 nom juste sur 29, avec les images de la fiche passées en gris ; ses cadres de personnages servent à l'essai de CCIP |
| [deepghs/manga109_yolo](https://huggingface.co/deepghs/manga109_yolo) | Visages, corps, cases, textes | Non indiquée sur la page ; AGPL-3.0 dans les métadonnées du modèle (Ultralytics) ; entraîné sur Manga109-s, données non commerciales | 101 Mo | Essayé le 2026-11-23 (tâche 3b, D38) sur le chapitre 1192, page gardée dans ses proportions, côté le plus long 640 : 0,2 s par page ; retrouve 2 des 6 apparitions que Magi v2 ne voit pas (Luffy deux fois ; ni Franky ni Usopp, à aucune taille essayée), mais seulement 13 des 23 apparitions que Magi v2 encadre : il complète Magi, il ne le remplace pas |
| [WD EVA02-Large tagger v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3) | Étiquettes Danbooru d'une image, dont les noms de personnages (7 des 10 de la fiche de One Piece ; ni Franky, ni Brook, ni Jinbe) | Apache-2.0 | 1,26 Go | Essayé le 2026-11-23 (tâche 3b, D38) sur les cadres du chapitre 1192 : 2,1 s par cadre sur le processeur ; au seuil de sa démo (0,85), 5 noms justes sur 29 et aucun faux ; dès 0,5, il prend un géant pour Usopp ; Usopp casqué lui évoque Mario. Pas gardé comme échelon (D39) |
| [See-through, découpage du corps](https://huggingface.co/24yearsold/l2d_sam_iter2) | 19 parties : cheveux, visage, yeux, haut, bas… | Apache-2.0 | 1,3 Go | Employé par la recherche de la fiche (tâche 2, D32) sur des images en couleur : environ 12 s par image sur le processeur ; jamais mesuré sur du noir et blanc |
| [deepghs : détection des personnages et des têtes](https://huggingface.co/deepghs/anime_head_detection) | Cadres des personnages et des têtes sur une image en couleur | MIT | 2 × 45 Mo | Employé par la recherche de la fiche (D31) |
| [deepghs : CCIP, grand modèle](https://huggingface.co/deepghs/ccip_onnx) | Dit si deux images montrent le même personnage | OpenRAIL | 384 Mo | Employé par la recherche de la fiche (D31) ; le petit modèle confond des personnages de One Piece. Essayé pour la tâche 3 (D25) sur les cadres de Magi v2 : 0 nom juste sur 29 dans les pages en noir et blanc, alors qu'il retrouve le bon personnage parmi les images de la fiche 35 fois sur 35 en couleur et 31 sur 35 en gris |
| [Complément klein 9B « by reference »](https://huggingface.co/thedeoxen/FLUX.2-klein-9B-manga-colorization-by-reference-LORA) | Page + planche de référence | Complément Apache-2.0 ; modèle de base non commercial | 158 Mo + environ 11 Go | À essayer |
| [FLUX 3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) | Retouche avec jusqu'à 10 références | Non commerciale | Environ 7 Go | À essayer |
| [1Dreamer666/MangaShot](https://github.com/1Dreamer666/MangaShot) | Outil Windows qui emploie klein 9B + le complément, réglé pour 6 Go | AGPL-3.0 : s'en inspirer, ne pas reprendre le code | — | Référence de réglages |
| [kobenguyent/kobean-manga-colorizer](https://github.com/kobenguyent/kobean-manga-colorizer), [ManoharPadul/color-manga-using-ai](https://github.com/ManoharPadul/color-manga-using-ai) | Deux outils récents avec une mémoire de série en JSON | MIT ; Apache-2.0 | — | Lus pour leur rangement ; aucun ne vérifie le respect de la palette |

Restent écartés (registre de la Library) : MangaNinja (une seule référence, 512 × 512), ColorFlow (36 Go de mémoire
vidéo), Cobra (9,3 Go au minimum, pas de version publiée). La recherche du 2026-11-22 confirme ces trois lignes.

Aucun projet publié ne réunit une fiche de série durable, la reconnaissance automatique des personnages par page
et un moteur guidé par référence : chaque pièce existe, pas l'assemblage.
