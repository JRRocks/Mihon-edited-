# Journal

Les entrées les plus récentes en haut. On ne réécrit pas une entrée : une erreur se corrige par une entrée nouvelle.

## 2026-11-23 · Colorisation fidèle : l'échelle d'IA, premiers essais avec Claude

- Branche et commit : `colorisation` (commit « Record the AI ladder decisions and the Claude rung trial »).
- Objectif : appliquer les réponses Q8 à Q11 (échelle d'IA : D27 à D29, D36) et montrer la fiche en image (Q7).
- Réalisé :
  - fiche couleurs rendue en une seule image (`fiche-a-juger.jpg`, dans le dossier de la fiche, hors du dépôt) et
    envoyée à l'utilisateur ;
  - essai des quatre échelons Claude sur le chapitre 1192 avec les modèles de cette session (sous-agents), sans
    compte API : chaque modèle reçoit les 13 pages aux cadres numérotés et une image de chaque personnage de la
    fiche, copiées dans un dossier à part, loin du relevé ; il nomme chaque cadre et se dit « sûr » ou « incertain ».
    Réponses, script de calcul et scores dans `reconnaissance\claude\` du jeu d'essai.
- Résultat :
  - noms justes sur les 29 apparitions : Haiku 15, Sonnet 22, Opus 20, Fable 22. Les 6 apparitions sans cadre
    plafonnent tout le monde à 23 ;
  - échelle « le premier sûr gagne » : 19 sur 29 ; Haiku nomme Luffy, sûr de lui, un monstre de la page 14, et Fable
    prend un géant pour Usopp (page 10) ;
  - échelle « deux échelons successifs d'accord » (D37) : 22 sur 29 (76 %), aucun personnage extérieur nommé,
    6 cadres sur 99 laissés à la session ;
  - coût aux tarifs de l'API, estimé : 1 à 2 $ par chapitre au plus (toutes les pages à tous les échelons) ;
  - l'écart restant jusqu'à 85 % vient de la détection : Magi v2 ne voit pas 6 apparitions (Luffy 4 fois, Usopp,
    Franky) ; Opus et Fable en signalent 3 ou 4 sans cadre.
- Décisions : D27 à D29 et D36 (utilisateur), D37 (développeur).
- Vérifications :
  - les deux noms faux donnés « sûrs » revus à l'œil sur leur cadre : le relevé avait raison (un géant de Little
    Garden, un monstre) ;
  - modèles candidats pour le PC relevés sur leur page Hugging Face (taille, licence, date) : détecteur entraîné sur
    Manga109, étiqueteur Danbooru (connaît 7 des 10 personnages, pas Franky, Brook ni Jinbe), Qwen3-VL 8B.
- Non vérifié :
  - les échelons Claude appelés par l'API : ils ont tourné dans la session (mêmes modèles, autre consigne) ;
  - la règle D37 est choisie sur ce chapitre-ci ; le relevé est de Claude Opus, l'un des échelons essayés.
- Problèmes et dette : la fiche couleurs elle-même a des erreurs visibles (le « bas » de Luffy mesuré rouge ; Usopp
  et Chopper déjà en doute), en attente du jugement de l'utilisateur.
- Prochaine étape : accord de l'utilisateur sur les téléchargements des échelons du PC (Q12), puis tâche 3b ;
  jugement de la fiche (Q7).

## 2026-11-23 · Colorisation fidèle : fiche fusionnée, la reconnaissance échoue aussi avec CCIP

- Branche et commit : `colorisation` (fusion de `claude/magical-mendel-3nv2ua`, puis le commit « Add the CCIP
  recognition trial (task 3, D25) »).
- Objectif : appliquer les deux réponses de l'utilisateur : essayer CCIP (D25), fusionner la branche de la session
  cloud (D26).
- Réalisé :
  - fusion : l'outil de la fiche (`color_sheet.py`, paquet `colorsheet/`, 45 tests) et la fiche de One Piece
    rejoignent `colorisation` ; journal, plan et décisions gardent les entrées des deux sessions ;
  - outil `tools/colorization-server/recognize_ccip.py` : mêmes 13 pages, mêmes 101 cadres (ceux de Magi v2), même
    relevé, même banque (les 40 images de la fiche, en gris) ; grand modèle CCIP (384 Mo, empreinte SHA-256
    contrôlée), moins d'une seconde par image sur le processeur ; résultats dans `reconnaissance\ccip\` du jeu d'essai, hors du dépôt.
- Résultat : **toujours 0 nom juste sur 29**. Le nom le plus proche n'est jamais le bon (0 fois sur 23, contre 5 avec
  Magi v2) : presque tous les personnages du chapitre ressemblent le plus à Zoro ou à Nami. Aucun seuil ne sauve
  l'essai : du plus strict au plus large, 0 bon nom, et jusqu'à 70 personnages extérieurs nommés à tort.
  - CCIP lui-même fonctionne : parmi les images de la fiche, il retrouve le bon personnage 35 fois sur 35 en couleur
    et 31 sur 35 en gris. Ce qui bloque, pour les deux modèles, c'est l'écart entre les images de la fiche
    (couvertures en couleur, aspect habituel) et ce chapitre (noir et blanc et trames, Luffy transformé d'un bout à
    l'autre, Usopp casqué).
  - Avec des exemples en gris pris dans les autres pages du chapitre (cas favorable) : 66 % mais 69 personnages
    extérieurs nommés à tort ; avec les autres personnages aussi en exemples : 31 % et 12 erreurs. Magi v2 faisait
    mieux dans ce cas (69 % et 63 erreurs ; 59 % et 5 erreurs) : CCIP distingue mal les dessins en noir et blanc
    entre eux.
- Décisions : D25 et D26 (utilisateur).
- Vérifications :
  - les 45 tests de la fiche repassent après la fusion ;
  - contrôle « rien de privé » sur tout l'écart avec `origin/main` : seuls des coefficients de calcul (passage en
    OKLab, normalisation des images) ressemblent à des coordonnées GPS, sans objet ;
  - contrôle de CCIP sur les images de la fiche (ci-dessus) : le calcul est juste, l'échec ne vient pas d'une erreur
    de branchement ;
  - mêmes cadres et même relevé que pour Magi v2 : les deux essais se comparent directement.
- Non vérifié sur téléphone : sans objet, l'application n'a pas changé.
- Problèmes et dette :
  - un seul chapitre, et difficile : on ne sait pas encore si l'échec vient de ce chapitre (transformations) ou de
    la méthode (des images en couleur pour reconnaître des dessins en noir et blanc) ;
  - le serveur du PC tourne encore en mode capture, sans utilité depuis D22.
- Prochaine étape : l'utilisateur choisit la suite de la tâche 3 et dit si la fiche couleurs lui paraît juste (Q7).

## 2026-11-23 · Colorisation fidèle : essais sur le chapitre 1192, la reconnaissance des personnages échoue

- Branche et commit : `colorisation` (voir le commit « Add the character recognition trial (task 3) ») ; la fiche
  de la session cloud reste sur `claude/magical-mendel-3nv2ua`, non fusionnée (question posée à l'utilisateur).
- Objectif : faire les essais sur le fichier CBZ que l'utilisateur a déposé, sans passer par le téléphone (D22).
- Réalisé :
  - tâche 1 : le CBZ (One Piece, chapitre 1192, 14 pages, source TCB Scans) devient le jeu d'essai
    `Documents\Mihon colorisation\essais\One Piece\chapitre-1192\` (pages dans l'ordre, `pages.jsonl`,
    `chapter.json`, copie du CBZ) ; la page de crédits du groupe de traduction, en couleur, est écartée (D23) ;
  - tâche 2 : la session cloud a livré la fiche de One Piece et son outil (`color_sheet.py`, D30 à D35, sur sa
    branche) ; fiche copiée sur le PC dans `Documents\Mihon colorisation\series\one-piece--al30013\` ; ses images de
    référence (14 couvertures, 9 images AniList) y sont téléchargées et recadrées selon ses cadres ;
  - tâche 3 : outil `tools/colorization-server/recognize.py` (Magi v2, D24) : banque de 40 exemples pour les
    10 personnages de la fiche, 101 personnages trouvés sur 13 pages, 3 s par page sur le processeur ; pages
    numérotées, pages nommées, `recognition.json`, `releve.json` (relevé à l'œil), `evaluation.json` et une planche
    `pourquoi-ca-echoue.jpg`, le tout dans le dossier `reconnaissance\` du jeu d'essai, hors du dépôt.
- Résultat de la tâche 3 : **0 nom juste sur 29 apparitions** des personnages de la fiche (Luffy 24, Usopp 4,
  Franky 1) ; 23 cadres restent « Other », 6 apparitions n'ont même pas de cadre ; les deux seuls noms donnés sont
  faux (deux fois Loki nommé Luffy). Le seuil du plan (85 %) n'est pas atteint : on s'arrête, comme prévu.
  - Pourquoi : les images de la fiche montrent Luffy et Usopp sous leur aspect habituel, en couleur ; dans ce chapitre
    Luffy est en Gear 5 d'un bout à l'autre (cheveux blancs, autre visage) et Usopp porte un casque de géant. Les
    distances le confirment : le nom le plus proche n'est le bon que 5 fois sur 23, et aucun seuil ne sépare les
    personnages de la fiche des 70 autres (géants, Loki, l'ennemi).
  - Pistes mesurées sur le même relevé, avec des exemples en gris pris dans les autres pages du chapitre (cas
    favorable, puisque même chapitre) : 69 % mais 63 personnages extérieurs nommés à tort ; en ajoutant les autres
    personnages comme exemples « pas dans la fiche » : 59 % et 5 erreurs. Même ainsi, on reste loin de 85 %.
- Décisions : D22 (utilisateur), D23 et D24 (développeur).
- Vérifications :
  - les 45 tests de la fiche (session cloud) repassent sur le PC ;
  - Magi v2 téléchargé (2 Go) et contrôlé par son empreinte SHA-256 ; son code lu avant la première exécution ;
  - mêmes cadres d'un passage à l'autre (le relevé fait sur le deuxième passage vaut pour le troisième) ;
  - relevé fait sur les pages numérotées avant de regarder les noms ; les cas douteux (main seule, cadre à cheval
    sur deux personnages, silhouette du logo, personnage minuscule) sont notés « ? » et non comptés.
- Non vérifié sur téléphone : sans objet, l'application n'a pas changé.
- Problèmes et dette :
  - le relevé est fait à l'œil par Claude, sans connaître ce chapitre (paru après ses connaissances) : quelques
    étiquettes « Luffy » ou « autre » peuvent être fausses, sans changer le résultat (Magi n'a nommé que deux cadres) ;
  - ce chapitre est un cas difficile ; un chapitre où l'équipage a son aspect habituel donnerait sans doute plus ;
  - le serveur du PC tourne encore en mode capture : il ne sert plus aux essais (D22) ;
  - miroir Drive refait le 2026-11-23 (Google Drive relancé) : la copie miroir a retiré côté Drive 215 Ko de
    fichiers qui n'existaient plus sur le PC (sens unique PC vers Drive, voir `CLAUDE.local.md`) ; la corbeille du
    Drive les garde 30 jours.
- Prochaine étape : l'utilisateur choisit la suite de la tâche 3 (autre modèle, noms donnés par lui, couleurs
  stables sans nom, ou autre chapitre), dit si la fiche couleurs lui paraît juste, et si la branche de la session
  cloud doit être fusionnée.

## 2026-11-23 · Colorisation fidèle : tâche 2, la fiche couleurs de One Piece (session cloud)

- Branche et commit : `claude/magical-mendel-3nv2ua`, partie de `colorisation`, poussée ; rien sur `main`.
- Objectif : construire et essayer la recherche automatique de la fiche couleurs d'une série (tâche 2), sur One Piece.
- Réalisé :
  - accès réseau de l'environnement cloud « Canva export » ouvert par des demandes que l'utilisateur a acceptées :
    AniList, MangaDex, MangaBaka, Danbooru, wiki One Piece, Hugging Face et PyTorch. MangaBaka a changé d'adresse
    (`api.mangabaka.org`) ; Hugging Face sert ses fichiers depuis `us.aws.cdn.hf.co`, PyTorch depuis
    `download-r2.pytorch.org` ;
  - outil `tools/colorization-server/color_sheet.py` (paquet `colorsheet/`, lanceur `color-sheet.bat`) :
    - l'identité de la série est recoupée par deux bases, puis l'outil liste les personnages principaux et relève
      les mots de contrôle ;
    - il examine 30 couvertures japonaises sur 116, détecte les têtes et les apparie aux personnages ;
    - il découpe les parties et les contrôle, puis mesure les couleurs en OKLab ;
    - il applique les règles de doute et range la fiche selon le § 3 ;
  - page [`essais/one-piece/fiche.md`](../tools/colorization-server/essais/one-piece/fiche.md), avec ses pastilles
    SVG et les JSON de la fiche. Aucune image n'entre dans le dépôt : `essais/.gitignore` les refuse.
- Décisions : D30 à D35 (développeur).
- Vérifications :
  - les 45 tests de la partie pure passent (mesure sur images de synthèse, règles de doute) ;
  - essai final, parti d'un dossier de travail vide (modèles déjà téléchargés) :
    - durée 10 min 16 s ;
    - 23 images utilisées (9 images AniList et 14 couvertures, où 22 personnages ont été recadrés) ;
    - 193 têtes détectées sur 30 couvertures ;
    - 9 personnages sur 10 en doute ;
  - appariement contrôlé à l'œil sur des planches de recadrages : au seuil retenu, aucun membre de l'équipage n'est
    pris pour un autre ; un personnage extérieur (Vinsmoke Niji, cheveux bleus) reste compté pour Franky ;
  - couleurs justes à l'œil :
    - cheveux : noirs pour Luffy, verts pour Zoro, orange pour Nami, blonds pour Sanji, bleus pour Franky, noirs pour
      Robin ;
    - peau : Luffy, Zoro, Nami, Sanji.
- Non vérifié sur téléphone : la page sur GitHub, ouverte depuis le téléphone lui-même ; elle a été rendue en
  capture à la largeur d'un téléphone.
- Problèmes et dette :
  - See-through lit mal les couvertures d'Oda : il prend le visage pour des cheveux, ou oublie des cheveux noirs ou
    verts. Ses masques sont donc contrôlés avant la mesure. Sur 40 images examinées, 9 n'ont rien donné et 14 ont
    vu leurs cheveux pris dans la bande au-dessus du visage ;
  - les yeux, trop petits sur les couvertures, sont rarement mesurables et souvent faux : ce sont eux qui mettent
    Luffy, Zoro et Nami en doute ;
  - Brook (un squelette) et Jinbe (un homme-poisson à la peau bleue) : le découpage ne trouve pas de visage, rien
    n'est mesuré ;
  - Usopp, Robin, Chopper, Brook et Jinbe n'ont aucun recadrage sur les couvertures au seuil retenu. Leurs couleurs
    ne reposent que sur l'image AniList, où la zone des cheveux contient parfois autre chose : pour Usopp, le
    « bleu » mesuré est le fond ; pour Chopper, le « rouge » est son chapeau. Les deux sont signalés en doute ;
  - Hugging Face limite les téléchargements anonymes depuis l'adresse du cloud (une requête refusée pendant
    l'exploration) ;
  - sur un processeur sans bfloat16, le découpage prend environ 36 s par image au lieu de 12.
- Prochaine étape : l'utilisateur juge la page ; puis, sur le PC, la tâche 3. Pistes pour la fiche :
  - les pages couleur du manga, meilleure source selon D3, une fois le nouveau dialogue en place ;
  - plus de couvertures pour les personnages rares ;
  - les yeux mesurés seulement sur des images où ils sont assez grands.

## 2026-11-23 · Colorisation fidèle : travail sur GitHub, session cloud lancée, capture des pages prête

- Branche et commit : `colorisation` (créée le 2026-11-22 depuis `main` @ `d001e6f21`), poussée sur GitHub.
- Objectif : lancer les tests demandés « sur session cloud en nested session » (D16), série One Piece (D17).
- Réalisé :
  - tout le travail de colorisation (application, serveur, documents) commité sur la branche `colorisation` et
    poussé ; `main` n'a pas bougé ;
  - le miroir Drive est décrit dans `CLAUDE.local.md`, exclu de git ; `CLAUDE.md` part sur GitHub sans chemin privé
    (D21) ;
  - session cloud « Fiche couleurs One Piece : recherche automatique » demandée le 2026-11-22, démarrée par
    l'utilisateur ; elle travaille sur sa branche `claude/magical-mendel-3nv2ua` (tâche 2) ;
  - tâche 1 : le serveur garde les pages reçues avec l'option `--capture` (dossier
    `Documents\Mihon colorisation\essais\<série>\<démarrage>\`, pages dans l'ordre d'arrivée, `pages.jsonl`) ; le
    serveur du PC tourne en mode capture, moteur `guided`, dans une fenêtre réduite.
- Décisions : D16 à D18 (utilisateur), D19 à D21 (développeur).
- Vérifications :
  - contrôle « rien de privé » (script du skill `depot-public`) sur le commit puis sur tout l'écart avec `origin/main` :
    rien à signaler ; identité des commits `noreply` ;
  - branche `colorisation` sur GitHub au même commit que le PC (`f7c68ff79`) ;
  - documentation de Claude Code lue : session cloud de 4 processeurs, 16 Go, 30 Go de disque, aucune carte graphique
    annoncée ; accès réseau « Limited » par défaut, qui bloque AniList, MangaDex, MangaBaka, Danbooru, Fandom et
    Hugging Face ;
  - capture essayée sur un serveur à part (moteur `mc2`, port 8799) : trois pages envoyées, gardées à l'octet près
    dans l'ordre, dossier `untitled` sans titre, réponse coloriée inchangée ; puis une page sur le vrai serveur
    (`guided`, 1,4 s), effacée ensuite.
- Non vérifié sur téléphone : l'envoi d'un vrai chapitre de One Piece vers le serveur en mode capture.
- Problèmes et dette :
  - au 2026-11-23 au matin, la session cloud est inactive et sa branche n'a aucun commit propre : elle attend
    probablement l'ouverture des domaines ; un message de relance lui a été envoyé, sans réponse possible vers ce PC ;
  - le serveur en mode capture s'arrête si la fenêtre est fermée ou le PC redémarré : le relancer avec
    `start-server.bat --capture` ;
  - miroir Drive non fait le 2026-11-23 : le lecteur G: n'est pas monté (Google Drive n'est pas lancé sur le PC).
    À refaire à la prochaine session ; GitHub a tout, sauf `CLAUDE.local.md`, qui n'existe que sur le PC.
- Prochaine étape : l'utilisateur ouvre les domaines de l'environnement cloud, et lance depuis le téléphone le
  coloriage d'un chapitre de One Piece (Qualité : « Détaillée », 1024 px) ; ensuite tâche 3 sur le PC.

## 2026-11-22 · Colorisation fidèle : quatre réponses, plan réordonné

- Branche et commit : `main`, aucun commit.
- Objectif : obtenir les quatre décisions qui manquaient et arrêter le plan.
- Réalisé :
  - page d'aperçu de la logique publiée en privé (son lien est gardé hors du dépôt, qui est public) ;
  - quatre questions posées et répondues ; plan réordonné : lieux et objets, ambiances et tenues entrent dans la
    preuve sur le PC (tâches 6 à 8), l'application vient ensuite (tâches 10 à 12).
- Décisions : D10 à D13 (utilisateur), D14 et D15 (développeur).
- Vérifications :
  - page d'aperçu rendue en image à la largeur d'un téléphone (390 px, thème clair) et en bureau (clair et sombre) :
    rien ne déborde ;
  - couvertures de tomes en japonais recomptées sur MangaDex : 16 pour Frieren, 12 pour Kagurabachi, 37 pour Vagabond.
- Non vérifié sur téléphone : l'affichage de la page d'aperçu sur le téléphone lui-même.
- Problèmes et dette :
  - correction de l'entrée précédente : dans l'essai case par case, la case restée fausse (veste et œil) est dans la
    bande du haut, qui contenait les deux personnages et avait reçu la planche entière ;
  - l'application n'envoie pas au PC les pages qu'elle juge déjà en couleur : les pages couleur du manga ne serviront
    de référence qu'avec le nouveau dialogue (tâche 10) ;
  - le registre des projets externes de la Library reste à mettre à jour.
- Prochaine étape : feu vert de l'utilisateur, puis tâche 1 (le serveur garde les pages reçues, l'utilisateur lance un
  chapitre depuis le téléphone).

## 2026-11-22 · Colorisation fidèle : la logique est posée, rien n'est encore construit

- Branche et commit : `main`, aucun commit (tout le travail de colorisation du fork reste non commité).
- Objectif : trouver une façon fiable de colorier en respectant les personnages et le contexte, en commençant par
  la logique : recherche des couleurs officielles et rangement des références.
- Réalisé :
  - lecture de l'existant : le serveur colorie page par page, sans mémoire, avec quatre couleurs devinées depuis le titre ;
  - sept recherches en parallèle (modèles par référence, modèles de retouche, reconnaissance des personnages,
    sources des couleurs, projets existants, modèle « directeur », méthode des coloristes professionnels) ;
  - spécification [`specs/colorisation-fidele.md`](specs/colorisation-fidele.md), plan en douze tâches, décisions D1 à D9.
- Décisions : D1 (utilisateur), D2 à D9 (développeur). Quatre questions en attente (Q1 à Q4).
- Vérifications :
  - AniList, MangaDex, MangaBaka, Danbooru, Fandom, Wikidata interrogés en direct : réponses conformes au § 4 de
    la spécification ; Jikan arrêté depuis le 2026-10-01 ;
  - fiches des modèles et dépôts retenus lues une à une (licence, poids, date) : tableau du § 10 ;
  - essai du moteur déjà installé (FLUX.2 klein 4B) avec une image de référence, sur une page et deux personnages
    inventés : 12 s par page sans référence, 21 s avec ; écart de couleur 35 sans référence, 17 avec ; échanges de
    couleurs entre les deux personnages, corrigés à l'œil quand chaque case reçoit la référence de son seul personnage.
- Non vérifié sur téléphone : sans objet, rien n'a changé dans l'application.
- Problèmes et dette :
  - aucun essai sur de vraies pages de manga ; la reconnaissance des personnages et le découpage des parties ne
    sont pas essayés sur ce PC ;
  - la mémoire vive est courte (16 Go, 5 Go libres pendant les essais) : le moteur 9B est à surveiller ;
  - la fonction de colorisation du fork n'existe que sur le PC et dans le miroir Drive, pas sur GitHub ;
  - le registre des projets externes de la Library n'a pas été mis à jour par cette session.
- Prochaine étape : réponses aux questions Q1 à Q4, puis feu vert pour la tâche 1 du plan.
