# Journal

Les entrées les plus récentes en haut. On ne réécrit pas une entrée : une erreur se corrige par une entrée nouvelle.

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
    `start-server.bat --capture`.
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
