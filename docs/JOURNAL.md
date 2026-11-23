# Journal

Les entrées les plus récentes en haut. On ne réécrit pas une entrée : une erreur se corrige par une entrée nouvelle.

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
