# Plan

Chantier en cours : **colorisation fidèle** (personnages aux couleurs officielles, lieux et objets stables, ambiance
des scènes, tenues selon l'arc). La logique est décrite dans
[`specs/colorisation-fidele.md`](specs/colorisation-fidele.md), les décisions dans [`DECISIONS.md`](DECISIONS.md).

État au 2026-11-23 : feu vert donné (D16). Série d'essai : One Piece (D17), chapitre 1192 fourni en fichier (D22).
Tâches 1 et 2 faites (la fiche de la session cloud est fusionnée dans `colorisation`, D26 ; son jugement attend
l'utilisateur, qui l'a reçue en image). Tâche 3 : Magi v2 puis CCIP (D25) restent à 0 nom juste sur 29 ; la
reconnaissance devient une échelle d'IA, le PC puis Claude, Claude en session en dernier recours (D27 à D29, D36).
Essais 3a et 3b faits : le PC trouve les personnages, Claude les nomme (D37 à D40) ; reste 3c, qui attend le compte
API de l'utilisateur.

## Partie 1 : la preuve sur le PC, avec l'application actuelle

Chaque tâche se termine par une image ou une page que l'utilisateur ouvre et juge.

| N° | Tâche | Ce que l'utilisateur voit quand c'est réussi | État |
|---|---|---|---|
| 1 | Jeu d'essai : le serveur du PC garde les pages qu'il reçoit ; l'utilisateur lance depuis le téléphone le coloriage d'un chapitre de One Piece (D13, D17) | Le dossier d'essai contient les pages du chapitre, dans l'ordre, et le titre de la série | terminée le 2026-11-23 par le fichier CBZ du chapitre 1192 (D22, D23) : 14 pages dans l'ordre, titre et numéro lus dans le fichier ; la capture depuis le téléphone reste prête mais n'a pas servi |
| 2 | Fiche de la série d'essai, construite par la recherche automatique | Une page « fiche couleurs » : les personnages principaux, leurs couleurs, d'où vient chaque couleur, et les points où le PC doute (D14) ; il dit si c'est juste | faite par la session cloud (outil `color_sheet.py`, D30 à D35), fusionnée dans `colorisation` le 2026-11-23 (D26) ; ses 45 tests repassés sur le PC ; à juger : [fiche One Piece](../tools/colorization-server/essais/one-piece/fiche.md) |
| 3 | Reconnaissance des personnages sur le chapitre d'essai (téléchargement autorisé par D12) | Les pages du chapitre avec un nom sur chaque personnage ; le taux de bons noms est écrit. Sous 85 % sur les personnages principaux, on s'arrête et on choisit une autre voie | en cours : Magi v2 puis CCIP (D25) arrêtés le 2026-11-23 à 0 nom juste sur 29 ; voie choisie : l'échelle d'IA (D27 à D29, D36), mesurée échelon par échelon sur le même chapitre et le même relevé (3a à 3c) |
| 3a | Échelons Claude (Haiku, Sonnet, Opus, Fable) sur le chapitre 1192 | Le taux de bons noms de chaque échelon et de l'échelle entière, le nombre de cas laissés à Claude en session, et le coût estimé par chapitre | faite le 2026-11-23 avec les modèles de la session, pas encore par l'API : Sonnet et Fable nomment juste 22 des 23 apparitions encadrées ; l'échelle (règle D37) donne 22 sur 29 (76 %), aucun personnage extérieur nommé, 6 cadres sur 99 pour la session, 1 à 2 $ par chapitre au plus (estimation). Sous 85 % à cause des 6 apparitions sans cadre |
| 3b | Échelons du PC entre CCIP et Claude, et un détecteur fait pour le noir et blanc (les 6 apparitions sans cadre) ; téléchargements soumis à l'accord de l'utilisateur | Même relevé : ce que chaque modèle du PC tranche seul, sans erreur sûre d'elle, et combien d'apparitions sans cadre le détecteur retrouve | faite le 2026-11-23 (téléchargements D38, image `reconnaissance\pc\echelons-du-pc.jpg` du jeu d'essai) : le détecteur Manga109 retrouve 2 des 6 apparitions sans cadre (Luffy deux fois), ce qui porte le plafond de 23 à 25 sur 29 (86 %) ; l'étiqueteur Danbooru seul nomme juste 5 sur 29 sans erreur, rien que l'échelle Claude ne nomme déjà. Gardé : le détecteur ; pas l'étiqueteur (D39) |
| 3c | L'échelle branchée au serveur : compte API Anthropic ouvert par l'utilisateur, cadres de Magi v2 et du détecteur, règles D37 et D40, cas bloqués gardés pour la session (D29) ; les échelons Claude signalent aussi les personnages qu'ils voient sans cadre (Opus et Fable en ont vu 3 ou 4 des 6) | Sur le chapitre d'essai, chaque personnage reçoit un nom sûr ou attend la session ; le taux de bons noms est écrit (barre des 85 %) ; le chapitre n'est colorié qu'ensuite | à faire : attend le compte API de l'utilisateur |
| 4 | Comparaison des moteurs sur dix pages, références données case par case : moteur installé contre moteur spécialisé (D12) | Une planche avant et après par moteur, avec le temps par page ; il choisit le moteur | à faire |
| 5 | Verrou des couleurs et contrôle | Sur tout le chapitre, cheveux, peau et tenue de chaque personnage reconnu gardent la même couleur ; la liste des pages douteuses est affichée | à faire |
| 6 | Lieux, objets et inconnus | Un décor, un objet ou un figurant revu plus loin garde la couleur de sa première apparition, dans le chapitre puis dans un second chapitre de la même série | à faire |
| 7 | Ambiances de scène : nuit, coucher de soleil, flashback | Une scène de nuit est teintée d'un bloc, et les personnages y restent reconnaissables | à faire |
| 8 | Tenues selon l'arc | Sur deux chapitres éloignés de la même série, un personnage qui a changé de tenue porte les couleurs de la bonne tenue | à faire |
| 9 | Chapitre entier de bout en bout | Un fichier CBZ colorié qu'il ouvre dans l'application, et le temps total | à faire |

Les tâches 6 et 8 demandent un deuxième chapitre de la même série, envoyé de la même façon que le premier.
Feu vert demandé sur le résultat de la tâche 9 avant la partie 2.

## Partie 2 : dans l'application

| N° | Tâche | Ce que l'utilisateur voit quand c'est réussi | État |
|---|---|---|---|
| 10 | Nouveau dialogue entre le téléphone et le PC : chapitre entier, identité de la série, pages couleur transmises | Depuis le téléphone, colorier un chapitre donne le résultat de la tâche 9 ; la mise à jour s'installe par-dessus l'ancienne | à faire |
| 11 | Fiche couleurs dans l'application (aperçu à valider avant le code) : elle ne sollicite l'utilisateur que quand le PC doute (D11) et reste consultable et corrigeable | Il est prévenu d'un doute et le tranche ; il corrige une couleur, et les chapitres concernés sont refaits | à faire |
| 12 | Sauvegarde des fiches de série sur le Drive | Les fiches figurent dans le miroir | à faire |

## À vérifier sur téléphone

Rien pour l'instant : la partie 1 se juge sur le PC ou sur des images ; le téléphone n'y sert qu'à envoyer les pages,
avec l'application déjà installée. Les tâches 10 et 11 ne pourront être confirmées que sur le téléphone.

## Ce qui passe par un aperçu avant le code

- la fiche couleurs dans l'application et la façon dont un doute est signalé (tâche 11) ;
- tout réglage ou bouton nouveau dans les écrans de colorisation (tâche 10).
