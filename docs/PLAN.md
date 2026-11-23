# Plan

Chantier en cours : **colorisation fidèle** (personnages aux couleurs officielles, lieux et objets stables, ambiance
des scènes, tenues selon l'arc). La logique est décrite dans
[`specs/colorisation-fidele.md`](specs/colorisation-fidele.md), les décisions dans [`DECISIONS.md`](DECISIONS.md).

État au 2026-11-23 : feu vert donné (D16). Série d'essai : One Piece (D17). La tâche 2 est faite en session cloud,
sur la branche `claude/magical-mendel-3nv2ua` partie de `colorisation` : sa page attend le jugement de l'utilisateur.
Les autres tâches de la partie 1 se font sur le PC.

## Partie 1 : la preuve sur le PC, avec l'application actuelle

Chaque tâche se termine par une image ou une page que l'utilisateur ouvre et juge.

| N° | Tâche | Ce que l'utilisateur voit quand c'est réussi | État |
|---|---|---|---|
| 1 | Jeu d'essai : le serveur du PC garde les pages qu'il reçoit ; l'utilisateur lance depuis le téléphone le coloriage d'un chapitre de One Piece (D13, D17) | Le dossier d'essai contient les pages du chapitre, dans l'ordre, et le titre de la série | en cours (PC) |
| 2 | Fiche de la série d'essai, construite par la recherche automatique | Une page « fiche couleurs » : les personnages principaux, leurs couleurs, d'où vient chaque couleur, et les points où le PC doute (D14) ; il dit si c'est juste | à juger : [fiche One Piece](../tools/colorization-server/essais/one-piece/fiche.md) (outil `color_sheet.py`, D30 à D35) |
| 3 | Reconnaissance des personnages sur le chapitre d'essai (téléchargement autorisé par D12) | Les pages du chapitre avec un nom sur chaque personnage ; le taux de bons noms est écrit. Sous 85 % sur les personnages principaux, on s'arrête et on choisit une autre voie | à faire |
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
