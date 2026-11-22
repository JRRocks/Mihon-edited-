# Décisions

Une décision ne se réécrit pas : elle se révise par une ligne nouvelle, datée, qui renvoie à l'ancienne.
« Utilisateur » : décidé par lui, avec ses mots. « Développeur » : choisi en cours de travail, il peut y revenir.

## Colorisation fidèle

| N° | Date | Qui | Décision | Pourquoi |
|---|---|---|---|---|
| D1 | 2026-11-22 | Utilisateur | La logique passe avant le moteur : « Le plus important est la logique apportée, comment les références sont stockées, la recherche sur les personnages et les couleurs originales, avant de faire travailler l'IA sur mon ordi ». | La colorisation actuelle ne connaît ni les personnages ni leurs couleurs |
| D2 | 2026-11-22 | Développeur | Une couleur officielle est mesurée sur une image officielle et rangée en nombres, avec sa source. Elle n'est jamais demandée à une IA. | Les modèles qui regardent une image se trompent de code couleur une fois sur deux ; un nombre se vérifie et se corrige |
| D3 | 2026-11-22 | Développeur | Ordre de confiance : correction de l'utilisateur > pages couleur du manga > couvertures des tomes > anime > page déjà validée > couleur inventée et notée > réglage par défaut. | C'est l'ordre des coloristes professionnels ; l'anime s'écarte parfois du manga |
| D4 | 2026-11-22 | Développeur | Un personnage mal reconnu ne reçoit aucune couleur imposée. | La reconnaissance publiée plafonne entre 73 et 93 % ; une couleur fausse appliquée avec assurance est le pire résultat |
| D5 | 2026-11-22 | Développeur | Une page générée n'enseigne jamais une couleur officielle, et un exemple de personnage n'entre dans la fiche que s'il est appuyé par un autre ou validé. | L'ajout automatique au meilleur score se trompe dans 62 à 89 % des cas (Re:Cognize, 2026) |
| D6 | 2026-11-22 | Développeur | Le coloriage se fait case par case, avec la référence des seuls personnages présents. | Essai du 2026-11-22 : une planche de deux personnages fait échanger leurs vêtements et leurs yeux |
| D7 | 2026-11-22 | Développeur | Les fiches de série sont rangées dans `%USERPROFILE%\Documents\Mihon colorisation\`, en fichiers lisibles (JSON et images), hors du cache des modèles. | Supprimer le cache des modèles ne doit pas effacer une fiche validée ; un fichier lisible se contrôle et se corrige à la main |
| D8 | 2026-11-22 | Développeur | Le téléphone envoie un chapitre entier, plus une page isolée. | La reconnaissance des personnages et les scènes se décident sur le chapitre |
| D9 | 2026-11-22 | Développeur | La preuve se fait d'abord sur le PC, sans toucher à l'application. | Rien n'est livré sur le téléphone tant que le résultat n'a pas été jugé sur des images |
| D10 | 2026-11-22 | Utilisateur | « Respect des contextes » couvre les quatre choix proposés, tous cochés : « Couleurs des personnages », « Lieux et objets », « Ambiance de la scène », « Tenues selon l'arc ». | Réponse à Q1 ; aucun des quatre n'est remis à plus tard |
| D11 | 2026-11-22 | Utilisateur | La fiche couleurs d'une série ne lui est soumise que quand le PC doute : « Seulement si le PC doute ». | Réponse à Q2 ; il ne valide pas chaque série. Risque annoncé et accepté : une erreur sûre d'elle passe sans être vue |
| D12 | 2026-11-22 | Utilisateur | Téléchargements autorisés depuis Hugging Face pour la preuve : « Reconnaissance + moteur, 14 Go » (Magi v2, découpage des parties, FLUX.2 klein 9B, Qwen3 8B, complément manga). Le troisième moteur (FLUX 3 Klein) n'est pas autorisé. | Réponse à Q3 ; 39 Go libres sur le disque au moment du choix |
| D13 | 2026-11-22 | Utilisateur | Les pages d'essai arrivent « Depuis le téléphone » : il lance le coloriage d'un chapitre comme d'habitude, le PC garde les pages reçues. | Réponse à Q4 ; rien à installer sur le téléphone, et ce sont les pages que l'application envoie réellement |
| D14 | 2026-11-22 | Développeur | Le PC « doute » (D11) quand une couleur ne repose que sur une image, quand deux sources se contredisent, quand aucune image en couleur n'est trouvée, ou quand l'identité de la série n'est pas recoupée par deux bases. Le reste passe sans question ; la fiche reste consultable et corrigeable à tout moment. | Donne un sens mesurable au doute, pour ne solliciter l'utilisateur ni trop ni trop peu |
| D15 | 2026-11-22 | Développeur | Lieux et objets, ambiances et tenues entrent dans la preuve sur le PC (tâches 6 à 8 du plan), avant le passage dans l'application. | Applique D10 : les quatre contextes sont jugés sur images avant d'être livrés sur le téléphone |
| D16 | 2026-11-22 | Utilisateur | « Lance les tests sur session cloud en nested session », puis, parmi les choix proposés, « Cloud, branche publique » : le travail de colorisation part sur une branche à part du dépôt public, après contrôle « rien de privé » ; il ouvre lui-même l'accès réseau de l'environnement cloud aux sites de la recherche ; le cloud fait la recherche des fiches couleurs (tâche 2), la reconnaissance et les moteurs restent sur le PC. | Les sessions cloud ont 4 processeurs et 16 Go, aucune carte graphique annoncée, aucun accès aux pages que le téléphone envoie au PC, et partent de GitHub |
| D17 | 2026-11-22 | Utilisateur | Série d'essai : « One Piece ». | Beaucoup de personnages et de tenues : met la reconnaissance et les tenues à l'épreuve |
| D18 | 2026-11-22 | Utilisateur | Pas de tests automatiques de l'application pour l'instant : « Non, la preuve seule ». | La preuve ne touche pas à l'application |
| D19 | 2026-11-22 | Développeur | Rien qui relève du droit d'auteur ne part sur la branche publique : ni pages de manga, ni couvertures, ni images de personnages. Les fiches y gardent les couleurs mesurées, l'adresse de chaque image source et les cadrages ; les images restent hors du dépôt. | Le dépôt est public ; une couleur mesurée et une adresse ne reproduisent pas l'œuvre |
| D20 | 2026-11-22 | Développeur | `CLAUDE.md` ne part pas sur GitHub tant qu'il contient le chemin du miroir Drive ; une session cloud reçoit dans son brief les consignes dont elle a besoin. | Règle « rien de privé » du dépôt public |
| D21 | 2026-11-22 | Développeur | Remplace D20 : le miroir Drive passe dans `CLAUDE.local.md`, qui reste sur le PC (exclu de git) ; `CLAUDE.md`, sans chemin privé, part sur GitHub. | Les sessions cloud lisent ainsi les consignes du projet ; Claude Code charge `CLAUDE.local.md` avec `CLAUDE.md`, rien ne change sur le PC |

## En attente

Aucune question en attente. Les quatre questions posées le 2026-11-22 ont reçu leur réponse le jour même, et le
feu vert est donné (D16).

| N° | Question | Réponse |
|---|---|---|
| Q1 | Ce que « respect des contextes » doit couvrir en premier : couleurs officielles des personnages, lieux et objets stables, ambiance de la scène, tenues selon l'arc | Les quatre (D10) |
| Q2 | Qui valide la fiche couleurs d'une série avant le coloriage : l'utilisateur une fois par série, seulement en cas de doute du PC, ou jamais | Seulement en cas de doute du PC (D11) |
| Q3 | Modèles à télécharger sur le PC pour la preuve : reconnaissance des personnages (3,5 Go), moteur spécialisé (11 Go), troisième moteur (7 Go) | Reconnaissance et moteur spécialisé, 14 Go ; pas le troisième moteur (D12) |
| Q4 | Comment les pages de la série d'essai arrivent sur le PC, et quelle série | Depuis le téléphone ; la série est celle du chapitre qu'il lancera (D13) |
