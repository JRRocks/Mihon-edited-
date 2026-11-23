# Journal

Les entrées les plus récentes en haut. On ne réécrit pas une entrée : une erreur se corrige par une entrée nouvelle.

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
