# PROGRESS LOG — MyAnimeRPG

Journal de progression, une entrée par tour de travail significatif. Le plus
récent en haut.

Ce fichier est **la source de vérité sur l'état du projet**. `STATE.md` est le
journal historique jusqu'au 2026-05-31 et n'est plus tenu à jour — voir la note
en tête de ce fichier-là.

Une copie de ce fichier est publiée sur un dépôt public pour lecture externe :
<https://raw.githubusercontent.com/broussemilan-beep/rrr/main/progress/PROGRESS_LOG.md>
(texte seul — aucun code source, aucun asset).

---

## Le projet en une page — pour un lecteur qui arrive sans contexte

**Ce que c'est.** Un jeu de combat Roblox sur rig **R6** (6 parties : Torso,
Head, Right/Left Arm, Right/Left Leg + HumanoidRootPart, reliés par 6 `Motor6D`,
3 DOF rotationnels chacun, aucune translation). Style anime/manhwa, références :
The Strongest Battlegrounds, Jujutsu Kaisen, Blox Fruits, Solo Leveling.

**Le vrai sujet du projet** n'est pas le jeu mais le **générateur
d'animations** : produire automatiquement des animations R6 qui tiennent debout
à côté de ces références. Le jeu est ce qui les consomme et les valide.

**Conventions Roblox** utilisées partout : Y haut, **−Z vers l'avant**, +X à
droite, unités en studs (1 stud ≈ 0.28 m à l'échelle personnage par défaut).

### Ce qui existe et tourne

| brique | état |
|---|---|
| Moteur de combat | 14 services serveur, ~22 contrôleurs client. Prédiction client + validation serveur, rollback (buffer de snapshots), hitbox, stamina, block, lock-on, dash, double-jump, transformations, VFX, camera shake, hitstop. **Vérifié en Play Solo : 0 erreur, 0 warning, 61 fps.** |
| Ship path animations | JSON → bake KeyframeSequence → upload Open Cloud → câblage AnimationDB → joué en jeu. **Prouvé bout en bout 2026-08-24.** |
| FK géométrique | `r6_fk.py` — validé contre le moteur à **0.0001 stud**. |
| Cascade de gates | 9 gates déterministes + jugement **par classe de coup** (straight / hook / uppercut / overhead / wide), seuils calibrés sur un pack commercial. |
| Capture visuelle | MCP Studio officiel Roblox — capture le viewport **en Play mode**, Studio pas besoin d'être au premier plan. |

### Ce qui manque — c'est le jeu, pas la technique

```
Shop  0 fichier    Currency  0    Inventory  0    Leaderboard  0
Matchmaking  0     Lobby  0       Progression  0
```

Données joueur sauvegardées, en entier :
`PROFILE_TEMPLATE = { Race, Class, Level = 1, Experience = 0 }` — et rien ne
fait monter Level ni Experience.

**Aucune UI en jeu** : les seuls `ScreenGui` du projet sont des VFX (flash
d'écran, speedlines). Pas de barre de vie, pas de stamina visible, pas de
cooldowns, pas de menu.

**Qualité du corpus d'animations** : au gate par classe, bras seul — **10/12 au
vert** après amplification, amplitude médiane 2.43 studs et ratio de forme médian
0.97 (pack commercial : 0.65–0.98). Les seeds ont la bonne *forme* (ratio de classe 0.71–0.95) ; c'est
l'amplitude qui manque. Les seeds amplifiés ne sont pas encore bakés ni en jeu.

### Les trois chantiers ouverts de R&D externe

1. **Prises à deux personnages synchronisées** — solveur de contact couplé livré,
   voir les entrées du 2026-08-25.
2. **Génération procédurale de décors** — jamais abordé.
3. **Transfert de style webtoon → 3D jouable** (référence : *The Player*) —
   jamais abordé.

Détail : `artifacts/RESEARCH_TRACKS_2026-08-25.md`.

---

## 2026-09-01 (suite 4) — VFXAudit : le détecteur de recettes muettes

### Ce qu'il fait

`src/shared/Modules/VFXAudit.lua`. Il répond à la seule question que personne ne
posait : **est-ce qu'un objet est né ?**

Deux pannes, deux messages distincts — on a rencontré les deux, et les confondre
ferait chercher au mauvais endroit :

| | signification | où chercher |
|---|---|---|
| **ATOME MUET** | joué, aucune instance créée | dans le code de l'atome |
| **ATOME ÉCARTÉ** | dans la recette, jamais joué | dans le câblage et le budget |

**Pas bruyant, et c'est délibéré.** `AssetVerifier` criait faussement à chaque
lancement et ce bruit permanent masquait tout — c'est pour ça que personne ne l'a
jamais lu. Ici : on n'avertit que sur une panne réelle, chaque couple
(recette, atome, panne) n'avertit **qu'une fois par session**, le message est
encadré, et l'audit **ne tourne qu'en Studio**. Un silence veut dire quelque chose.

### Le test volontaire a trouvé DEUX défauts dans le détecteur lui-même

C'était l'exigence la plus importante, et elle a payé deux fois.

**Défaut 1 — il ne criait pas.** Le compteur était global sur une fenêtre de
0,4 s : n'importe quelle instance créée ailleurs pendant la fenêtre — une autre
VFX, un personnage — était créditée à l'atome. En jeu réel, il n'aurait **jamais**
crié. Un détecteur à faux négatifs est pire qu'aucun détecteur.

**Défaut 2 — il criait à tort.** Après passage en mesure synchrone, un atome qui
créait réellement un `Part` était signalé MUET. Cause : **en Roblox moderne les
signaux sont différés**. `DescendantAdded` ne se déclenche pas dans la frame où
l'objet est parenté, donc un delta synchrone basé dessus vaut toujours zéro.

**Corrigé** : comptage direct de `#Workspace:GetDescendants()` avant et après.
Plus coûteux, mais c'est la seule mesure à la fois **synchrone et exacte** — et
les deux sont nécessaires. Le coût est assumé : l'audit s'éteint hors Studio.

**Résultat du test après correction :**
```
MUET signale   : 1   (attendu 1, et 1 SEULE malgre 2 appels — dedup OK)
ECARTE signale : 1   (attendu 1)
faux positif   : 0   (attendu 0)
VERDICT        : LE DETECTEUR MARCHE
```

Sans ce test, j'aurais livré deux fois de suite un détecteur cassé en le croyant bon.

---

## `GroundChunks` — l'atome marche, le défaut est ailleurs

### Il n'y avait rien à construire

`CombatVFX.GroundChunks` existe, et **il fonctionne**. Appel direct mesuré :

```
avant       :  0 eclats
juste apres : 14 eclats
a +0,5 s    : 14 eclats
VERDICT     : L'ATOME FONCTIONNE
```

Il est déjà câblé sur les quatre compétences (14 / 18 / 20 / 24 éclats). Et il est
**déjà non-collisionnant** (`CanCollide = false` dans le code) — la question de
performance posée est donc à moitié réglée d'avance.

### Mais il ne part pas en jeu, et le détecteur ne l'explique pas

Le remote livre bien les trois atomes :
```
DemiDieu_Skill1_Impact -> atomes : SlashTrail, Impact, GroundChunks
DemiDieu_Skill2_Impact -> atomes : SlashTrail, Impact, GroundChunks
```
Et pourtant : **zéro éclat dans le monde, et le détecteur reste silencieux.**

Or son silence devrait être impossible : si `GroundChunks` avait été tronqué, il
aurait crié ÉCARTÉ ; s'il avait été joué sans rien produire, il aurait crié MUET.
**Il y a donc un troisième chemin que je n'ai pas encore identifié**, et je le dis
plutôt que d'inventer une cause. C'est le point de reprise, et il est étroit.

### Une erreur de mesure à moi, attrapée par le détecteur

J'ai d'abord compté « 0 éclat » en filtrant sur des `Part` **nommées** « chunk ».
Elles n'ont pas de nom : elles s'appellent `Part`. **Ma mesure était fausse, et le
silence du détecteur avait raison contre moi.** C'est la troisième fois cette
semaine que je mesure la mauvaise chose — et la première fois qu'un outil me
rattrape au lieu de Milan.

## 2026-09-01 (suite 3) — Aura arrêtée, éclats déjà là, flash calé

### 1. Aura — le test ciblé est fait, et il conclut

Les **deux** corrections demandées ont été appliquées :

1. **Rapport d'échelle inversé** : or petit (0,35–1,1) et serré (dispersion 6°),
   fumée grande (0,8–3,0) et dispersée (55°).
2. **Ordre corrigé** : en regardant à nouveau les références, **la couleur est la
   couche INTÉRIEURE**, plaquée au corps, et **le noir le contour EXTÉRIEUR**.
   J'avais construit un rapport avant/arrière là où c'est un rapport
   intérieur/extérieur.

**Ça ne lit toujours pas. On arrête**, comme convenu.

### Mais le constat est plus utile qu'« inatteignable »

| vérification | résultat |
|---|---|
| attaches créées | ✅ **6**, une par membre |
| émetteurs présents | ✅ deux par attache |
| émission qui tourne | ✅ `Emit()` toutes les 0,09 s depuis un script vivant |
| textures | ✅ **les cinq chargent** (`PreloadAsync`) |
| **rendu à l'écran** | ❌ **rien** |

Ce n'est pas une impasse de conception : c'est un **échec de rendu circonscrit**.
Tout ce qui devrait produire l'image est en place et l'image n'apparaît pas. C'est
un point de départ précis pour qui reprendra le sujet, pas un mur.

### Une erreur de méthode à moi, et elle est grosse

**Mes trois mesures précédentes portaient sur la scène, pas sur mon aura.**
65,3/1,8 puis 60,9/1,6 puis 58,1/1,6 — je commentais l'évolution d'un rapport
fumée/or qui appartenait au décor. Un appel antérieur n'avait laissé **aucune
attache**, et je ne l'avais pas vérifié avant de mesurer.

J'ai tiré des conclusions de chiffres qui ne portaient pas sur ce que je croyais.
La leçon est la même que celle du plafond de lisibilité : **vérifier que la chose
existe avant de mesurer ce qu'elle fait.**

### 2. Les éclats de terrain — ils existent déjà

`CombatVFX.GroundChunks` **est déjà implémenté** : de vrais `Part` solides
projetés par `BodyVelocity`, durée 4 s, fondu sur 1 s, filet `Debris` à 5,5 s.
C'est exactement la nature d'effet que montre la référence.

Et il est **déjà câblé sur les quatre compétences** :

| recette | éclats | rayon |
|---|---|---|
| Skill1 Main du Colosse | 14 | 10 |
| Skill2 Frappe Céleste | 18 | 12 |
| Skill3 Marche du Titan | 20 | 13 |
| Ultime | 24 | 16 |
| **les quatre M1** | **aucun** | — |

**Il n'y a donc rien à construire.** Il y a à vérifier qu'il part — c'est un atome
de priorité **ambiante (2)**, exactement comme `Impact` l'était, donc le premier
candidat à la troncature. Ma correction d'aujourd'hui a promu `Impact` en héros,
**pas `GroundChunks`**.

### 3. Flash — calé sur la référence

Mesure sur la référence de jeu : **plein écran blanc, 0,20 s** (3 frames à 15 fps).
Le nôtre était partiel et plafonné à 0,12 s.

- plafond de durée **0,120 → 0,200 s**
- luminosité **0,55 → 1,15 × peak**

La progression par `peak` est conservée : c'est elle qui distingue un jab d'un
ultime. Seul le haut de l'échelle s'ouvre, pour que les gros coups atteignent
vraiment le blanc.

## 2026-09-01 (suite 2) — La référence de combat, et l'aura à moitié construite

### Nature du matériau — vérifiée en premier, comme demandé

**C'est une capture de jeu réelle**, pas une démo d'animateur : HUD avec boutons de
capacités, barres de vie et de stamina, pseudo d'un autre joueur au loin, tableau
des scores, filigrane « makeagif ». Contrairement aux deux références précédentes,
**celle-ci est transposable** : elle a la latence, le HUD et la caméra d'un vrai jeu.

### Ce qui rend le coup « puissant » — mesuré

| élément | référence | nous |
|---|---|---|
| flash à l'impact | **plein écran blanc, 0,20 s** | teinte partielle, **0,12 s max**, jamais plein écran |
| éclats + poussière au pic | **91 % de l'écran** | cœur saturé à **2,9 %** du cadre |
| éclats + poussière tenus | **~26 % pendant des secondes** | — |
| persistance des éclats | **≥ 3,5 s**, intacts | poussière particulaire, ~1,25 s |
| caméra à l'armement | **épaule, le torse remplit le cadre** | 8,5 stud |

### La différence structurelle, et c'est la vraie réponse à Milan

La référence ne projette pas de la *poussière* : elle **casse le terrain**. Des
**éclats angulaires solides** sont projetés sur un large rayon et **restent au
sol**, avec une **colonne de fumée grise** qui monte au milieu. Ce sont des
**objets**, pas des particules — c'est pour ça qu'ils persistent et occupent
durablement le quart de l'écran.

Notre onde au sol est une couche de particules qui vit 1,25 s. **Même parfaitement
réglée, elle ne peut pas produire ce que Milan regarde.** L'écart n'est pas un
réglage, c'est une nature d'effet.

### Ce qui rend l'animation « propre »

Pas de secousse parasite entre les phases : l'armement, la frappe et la
récupération s'enchaînent en une courbe continue, et la caméra suit sans à-coup.
C'est cohérent avec ce qu'on vient de corriger de notre côté (verrou d'entrée
séparé de la fin du geste), donc **ce point-là n'est plus notre écart principal**.

### Ce qui nous manque VRAIMENT, versus ce qu'on a et qui ne se voyait pas

- **Manque réel** : les éclats de terrain solides et persistants. On n'a rien de
  cette nature.
- **Manque réel** : un flash plein écran court. Le nôtre est plafonné à 0,12 s et
  n'est jamais plein écran.
- **On l'avait, ça ne se voyait pas** : l'onde au sol et le flash d'impact — l'atome
  `Impact` était écarté à chaque coup par le plafond de lisibilité, corrigé plus
  haut aujourd'hui.

---

## L'aura, reconstruite sur les références

### Une mesure qui contredit l'intuition

Milan pensait qu'on avait le patron dans les packs. **Sur les 181 auras de
SoulShroud : zéro couche de fumée sombre, zéro lumière.** Ce sont toutes des
nuages émissifs à couche unique — exactement ce qui ne lit pas. La couche sombre
est donc **autorée**, pas trouvée.

### Ce qui marche

| trait attendu | état |
|---|---|
| monte au-dessus de la tête | ✅ colonne visible bien au-dessus du crâne |
| éclaire le décor | ✅ halo au sol mesuré à **32,6 %** de la zone |
| continue | ✅ émission toutes les 0,09 s |

### Ce qui ne marche pas — et je m'arrête plutôt que d'empiler

| trait attendu | état |
|---|---|
| deux couches en contraste | ❌ colonne à **60,9 % sombre contre 1,6 % doré** |
| épouse la silhouette | ❌ la colonne monte *derrière*, elle n'enveloppe pas le corps |

J'ai tenté **un** rééquilibrage mesuré — fumée allégée de 0,42 à 0,62, or agrandi
de 1,5 à 2,4 et densifié de 3 à 6. Résultat : **65,3 % → 60,9 % de sombre**, l'or
reste à 1,6 %. **Ça n'a rien changé.**

Cause probable, non vérifiée : six membres émettent de la fumée à une échelle de
2,6 à 3,4, contre un or à 2,4 sur un seul plan — le volume sombre écrase
mécaniquement l'émissif, et jouer sur l'opacité ne compense pas un rapport de
volume. Il faudrait sans doute inverser le rapport d'échelle, pas les
transparences.

**Je ne pousse pas une troisième itération à l'aveugle** — c'est la leçon de cette
semaine. L'aura est à moitié construite et je le dis tel quel.

## 2026-09-01 (suite) — Milan avait raison : l'impact était écarté à CHAQUE coup

Cinquième instance du même schéma cette semaine. Le signal — « je ne le vois pas »
alors que la mesure dit présent — a de nouveau eu raison contre la mesure.

### La chaîne remontée maillon par maillon

| maillon | résultat |
|---|---|
| confirmation côté client | ✅ `M1_1 result=Hit`, trois fois |
| payload sur le remote `CombatFX` | ✅ `procedural_atoms : SlashTrail, Impact` |
| `hitPos` transporté | ✅ `(0.0, 3.0, 45.0)` |
| **`ImpactFlash` créé** | ❌ **jamais** |
| **onde au sol créée** | ❌ **jamais** |

Tout arrivait correctement, et rien n'était produit.

### La cause

```lua
priority = if i == 1 then 0 else 2
```

Le rang de **héros** revenait au **premier atome déclaré**, quel qu'il soit. Les
recettes M1 du Demi-Dieu déclarent `SlashTrail` **avant** `Impact` : la traînée
prenait le rang — et comme je l'avais moi-même sortie en `exempt` le 2026-08-31,
**ce rang était perdu**. `Impact` se retrouvait classé **ambiant (2)**, donc
dernier au tri, donc le **premier supprimé** par la troncature.

Avec `screen_flash` et `camera_kit` qui occupent aussi `pending`, cela faisait
**3 atomes pour un plafond Light de 2**. L'impact était écarté **à chaque coup**.

**Corrigé** : la priorité se lit sur le **kind**. Un impact est le héros d'une
recette de coup — ça ne dépend pas de l'ordre dans lequel quelqu'un a tapé la
table. C'est une classe de bug fermée, pas une instance.

### Réponses aux quatre questions posées

**1. Toutes les pièces ?** Oui sur le papier — les 16 recettes Demi-Dieu portent un
atome `Impact`. Mais **aucune ne le jouait**, M1 comme compétences. Ma mesure du
2026-09-01 qui annonçait l'onde « posée à Y=2.15 » portait sur un cast de
compétence dont le `pending` était moins encombré ; je l'avais généralisée à tort.

**2. Sur un cast qui rate ?** **Non, jamais.** Et c'est structurel, distinct du
bug ci-dessus : `CombatService` le dit dans son propre commentaire — *« Skipped on
Whiff (no recipe for misses) »* — et les modules de compétence conditionnent tous
leur diffusion à `hitTarget and hitPosition`. **Un joueur qui rate, ou qui frappe
sans cible, ne voit rien : ni onde, ni poussière.** Non corrigé : c'est une
décision de design, pas un défaut.

**3. La poussière persiste-t-elle ?** Oui. Relevé après correction : le socle est
**toujours vivant à +0,8 s**, avec ses 3 émetteurs. Elle n'est pas mangée par le
flash.

**4. Visible à 8,5 stud ?** Oui — vérifié sur une capture **cadrée sur le sol**, en
plongée. L'arc doré balaie le sol depuis le point d'impact.

### Note de vocabulaire

L'« **air comprimé** » que Milan mentionne **n'a jamais été implémenté** — il n'a
été qu'**identifié** comme device disponible dans les packs. Ce n'est pas la
poussière au sol, qui est une couche distincte, et qui elle existe désormais.

### Sur ACCAD

L'essai a **conclu négativement** au tour précédent (rig cassé à l'écran, cause :
pose de repos non gérée par `bvh_to_r6`). Il n'y a rien à y continuer sans une
décision sur la construction d'un vrai retargeter, qui est un chantier à part
entière et non une suite d'essai.

## 2026-09-01 — Essai ACCAD : conclu NÉGATIF, et c'est un bon résultat

### L'attribution, prévue AVANT — comme demandé

`CREDITS.md` créé **avant** toute intégration. Il formalise les **trois statuts
distincts** qu'on avait confondus — **licence**, **sécurité**, **attribution** — et
pose le plan : fichier de dépôt (fait), **panneau Crédits en jeu** et **description
de l'expérience** (obligatoires dès qu'une ressource attribuée est retenue, pas
optionnels).

### Tout a marché, sauf l'essentiel

| étape | résultat |
|---|---|
| Licence | ✅ CC BY 3.0 Unported, citée |
| Audit malveillant | ✅ **3/3 SAFE** (`audit_pack_safety.py`) |
| Compatibilité squelette | ✅ tous nos `BONE_ALIASES` trouvent leur os |
| Conversion `bvh_to_r6` | ✅ sans erreur — 128 / 89 / 88 keyframes |
| Chargement en moteur | ✅ durées correctes : 4,23 / 2,93 / 2,90 s |
| **Rendu à l'écran** | ❌ **tas de membres effondrés** |

Joué sur le personnage, `E7_SuperFastAdvance` ne donne **aucune pose humaine
reconnaissable**. Capture : `artifacts/animator_ai/accad_essai/pose_cassee_en_moteur.png`.

### La cause

`bvh_to_r6.py` le dit lui-même dans son en-tête : *« Tested on HumanML3D 22-joint
template »*. **Des noms de joints identiques ne garantissent pas une pose de repos
identique.** Les données ACCAD datent de 2006 ; leur T-pose n'est pas celle du
template sur lequel le convertisseur a été calibré.

C'est un problème de **retargeting**, pas de licence ni de format. Notre propre
journal l'avait écrit le 2026-05-28 — *« voie viable mais exige refs curées +
retargeter plus sophistiqué »*. **L'essai le confirme sur mesure au lieu d'en
discuter, ce qui était exactement son but.**

### Ce que l'archive contenait quand même — pour mémoire

La page ACCAD annonce les arts martiaux **en c3d seulement**. C'est inexact :
`Male2_bvh.zip` contient **149 fichiers BVH**, dont une série E complète de boxe
(`JabLeft`, `CrossRight`, `HookLeft`, `UppercutRight`, **8 blocks**,
`Advance`/`QuickAdvance`/`SuperFastAdvance`) et une série G d'arts martiaux
(20 coups de pied). Le corpus **est** riche et **est** pertinent. Ce qui manque,
c'est le retargeter.

### Verdict

**On garde le pack.** Le dash v2 (Close Combat, `Stylized Jump / Vault`) reste en
place : appui **3,13** stud, poussée **1,72**, ordre appui→poussée respecté.
Aucune attribution due, puisque rien n'est retenu.

### Une erreur de méthode que j'ai failli commettre

Ma première passerelle de mesure donnait des chiffres nets — ACCAD perdait sur
tous les axes — et **ils étaient faux**. Mon mappage des jambes était incorrect :
en FK, les pieds sortaient **au-dessus du torse** 88 à 100 % du temps.

J'allais conclure sur ces chiffres. C'est le **contrôle de sanité géométrique** —
tête au-dessus du torse, pieds en dessous, longueur d'os stable — qui l'a
rattrapé. Une mesure qui donne un résultat net n'est pas pour autant une mesure
juste.

---

## Captures des deux corrections précédentes

Filmées comme demandé. `24_competences_completes.mp4` montre Main du Colosse puis
Frappe Céleste jouées **jusqu'au bout** — cette dernière déploie enfin sa nova
dorée complète, là où elle était coupée à 54 %.

Rappel des mesures : **64 % → 88,1 %** et **54 % → 85,8 %**, sans qu'une
milliseconde de réactivité soit payée.

## 2026-09-01 — Recherche de packs : un seul candidat, et deux corrections livrées

### La recherche — conclusion d'abord

**Un seul candidat retenu. Rien téléchargé, rien importé.**

#### ✅ ACCAD Open Motion Project — Ohio State University

- **Source** : <https://accad.osu.edu/research/motion-lab/mocap-system-and-data> — centre
  de recherche universitaire, projet identifiable avec une histoire.
- **Licence, citée verbatim** : *« Open Motion Project by ACCAD/The Ohio State
  University is licensed under a Creative Commons Attribution 3.0 Unported
  License »*. CC BY 3.0 : **usage commercial autorisé**, dérivés autorisés
  (donc le retargeting), sous réserve d'attribution.
- **Ce qu'il apporte qu'on n'a pas** : le corpus « Male 2 » contient **95 fichiers
  d'arts martiaux** — coups de pied, coups de poing, **postures** et déplacements.
  Ça vise deux de nos manques nommés : le **geste franc de garde** et la **frappe
  au sol**. Formats dont **BVH**, que `scripts/bvh_to_r6.py` sait déjà lire.
- **Audit malveillant** : **sans objet, structurellement**. Le BVH et le C3D sont
  des formats de données de mouvement, sans contenu exécutable. Notre
  `audit_pack_safety.py` cible les `.rbxm`/`.rbxl`, les conteneurs Roblox qui
  peuvent embarquer des `Script` — ce vecteur n'existe pas ici.

#### ❌ Bandai Namco Research Motion Dataset — écarté sur la licence

3 000 mouvements dont du combat, en BVH. Mais licence **CC BY-NC-ND**, citée :
*« free for research and personal use under a Creative Commons Attribution
Non-Commercial No Derivatives licence »*. **Deux blocages** : usage non commercial,
et **pas de dérivés** — or retargeter vers R6 EST un dérivé. Écarté sans discussion,
exactement la règle qu'on vient de se donner.

#### ❌ Dépôts R6 open-source sur GitHub — rien

Aucun dépôt d'animations de combat R6 sous licence permissive. Le marché R6 est
**commercial** (BuiltByBit, KitsBlox, robloxanimations.com) : ce sont des achats à
arbitrer, pas des trouvailles sous licence libre.

#### ⚪ CMU mocap — déjà chez nous, et maigre sur le combat

`vendor/cmu-mocap` contient déjà **2 548 clips BVH**, avec une licence explicite
citée dans son propre README : *« CMU places no restrictions on the use of the
original dataset, and I (Bruce) place no additional restrictions »*. Mais recherche
ciblée sur nos manques : **un seul** `punch/strike` (02_05), **une seule**
`defensive guard pose` (76_04), un sujet « Martial Arts **Walks** » (marches, pas
frappes). Il est là, il est libre, il ne couvre pas nos besoins.

#### VFX : rien à ajouter

Les trois devices BZ1 posés couvrent l'arc, le sol et l'aura. **Je n'ajoute rien** —
c'est la réponse, pas une absence de recherche.

#### La réserve que je pose sur ACCAD

Notre propre histoire dit que le mocap → R6 déçoit régulièrement : *« raw SMPL→R6
projection casse les poses »*, *« A-native bat B-cloud sans vrai retargeter »*, et
le pivot référence concluait *« voie viable mais exige refs curées + retargeter plus
sophistiqué »*. ACCAD est un **candidat**, pas une promesse. Si tu valides, je
propose un essai étroit : **3 à 4 clips** (garde, frappe au sol, appui-poussée) à
travers `bvh_to_r6` + la cascade de gates, avant tout import en volume.

---

### Correction 1 — Main du Colosse 64 % → 88 %, Frappe Céleste 54 % → 86 %

**Cause réelle** : `recovery` **ne coupe pas** l'animation. Il fait passer la FSM en
`Locomotion.Idle`, et c'est `Idle` qui écrase la piste. Deux choses distinctes
étaient confondues : le **verrou d'entrée** et la **fin du geste**.

Séparées :

| | avant | après |
|---|---|---|
| `recovery` — rend la main au joueur | 0,55 s | **0,55 s, inchangé** |
| retour de la FSM à l'idle | 0,55 s | **fin réelle de la piste** |

| pièce | avant | après |
|---|---|---|
| Main du Colosse | 64 % | **88,1 %** |
| Frappe Céleste | 54 % | **85,8 %** |
| Marche du Titan | 96 % | 98,4 % |

Le reliquat (~12 %) est le **fondu** vers l'idle, pas une troncature. **La
réactivité n'a pas bougé** : si le joueur agit dans l'intervalle, sa nouvelle
action écrase la piste comme avant. On ne paie pas la lisibilité du geste en temps
de blocage.

### Correction 2 — l'ordre des marqueurs, garanti par construction

**Cause racine** : deux règles indépendantes plaçaient des marqueurs censés être
ordonnés. `Whoosh` était posé à `0,55 × contact` dans l'absolu, sans regarder où
tombe `Windup` (valeur héritée, 0,51 à 0,77 du contact). Seul M1_2 respectait
l'ordre ; M1_3 et M1_4 avaient même `Whoosh` **après** `Impact`.

Nouvelle règle : **`Whoosh` à mi-chemin entre `Windup` et `Impact`**. L'ordre est
garanti quelle que soit la valeur de `Windup` — on supprime la **classe** de bug,
pas ses quatre instances.

Vérifié en moteur, par les signaux réels :
```
M1_1  Windup@0.117 -> Whoosh@0.163 -> Impact@0.200
M1_2  Windup@0.125 -> Whoosh@0.183 -> Impact@0.246
M1_3  Windup@0.171 -> Whoosh@0.208 -> Impact@0.233
M1_4  Windup@0.225 -> Whoosh@0.308 -> Impact@0.325
```

**Un piège au passage** : ma première passe posait `Whoosh` à un temps non **snappé
sur une frame**. Le convertisseur indexe par temps de frame arrondi — le marqueur
n'était donc associé à aucune keyframe et **n'était pas baké du tout**. Constaté en
moteur : seul `Impact` firait. Le snap est obligatoire, il ne s'agit pas d'un
arrondi cosmétique.

## 2026-09-01 — TRANCHE COMPLETE : les trois devices sont posés et mesurés

### Les quatre états, même métrique, même caméra (8,5 stud)

| état | pale médiane | pale pic |
|---|---|---|
| sans traînée | 1 475 | 6 086 |
| traînée seule | 1 527 *(+3,5 %)* | 7 384 |
| + `Beam` (largeur 4,0) | 3 922 | 6 755 |
| **+ onde au sol + braises, `Beam` 2,2** | **4 458** | **6 360** |

**×2,9 de médiane** contre la traînée seule, et le **pic baisse** — plus de
présence tenue, moins d'éblouissement. C'est la bonne direction : ce qu'on
cherchait, c'est un geste lisible pendant toute sa course, pas un flash plus fort.

### Device 2 — onde au sol

Paramètres relevés sur `Impact Structures + Larger VFX/Shockwave`, recolorés
(l'original est magenta). Trois couches, telles que le pack les articule :

| couche | vitesse | durée | rôle |
|---|---|---|---|
| anneau | 26 | 0,30 s | le choc, ~7,8 stud de propagation |
| poussière | 7 | 1,25 s | **ce qui reste après le coup** |
| escarbilles | 7 | 1,10 s | le grain qui accroche la lumière |

Posé **au sol par raycast** sous le point d'impact — vérifié : `Y=2.15` pour un
joueur à `Y=3.00`, donc 0,85 stud sous lui. Jusqu'ici nos coups se produisaient
en l'air et le sol ne répondait pas. **La poussière qui reste est ce qui distingue
une frappe qui a touché de quelque chose d'un simple flash.**

### Device 3 — braises, en complément

Relevé sur `Auras/Humanoid Fx/CharacterAura162`, recoloré (l'original est violet).
Vitesse **0,125–0,25**, taille 0,20–0,40, durée 1,0–1,4 s, émission rare.

Ce sont ces valeurs **basses** qui font que la couche complète au lieu d'écraser :
des braises rares et lentes se lisent **devant** un embrasement sans le
concurrencer. Le feu doré-blanc validé n'est pas touché. Vérifié : émetteur sur le
`Torso`, vitesse 0,125–0,25, couleur (255,205,92).

### Un réglage que j'avais calé sur une caméra qui n'existe plus

Le `Beam` était à **4,0 stud** de large — valeur calée **avant** que la caméra
passe à 8,5 stud. Constaté sur capture : à cette distance, 4 stud sur un bras de 2
stud donne une **plaque qui recouvrait le torse** pendant un cast.

Ramené à **2,2** (la traînée fait 2,2 stud au total, donc le Beam reste au-dessus
en largeur utile). La médiane n'a pas baissé — elle a **monté** (3 922 → 4 458),
parce que le sol et les braises apportent la présence que la largeur excessive
apportait de force.

**Deuxième fois cette semaine qu'un réglage calé à une distance devient faux à une
autre.** Tout paramètre VFX exprimé en stud doit être revalidé quand la caméra
bouge.

### Ce que ça donne

Sur la capture finale : le personnage est **entièrement visible**, un **arc doré**
court en travers du cadre, et des braises parsèment le sol autour de l'impact.
C'est le meilleur état visuel de la semaine.

## 2026-09-01 — Licence levée, et le `Beam` répond enfin sur la traînée

### Licence : deux statuts, désormais séparés dans l'audit

Milan confirme l'usage commercial sur **SoulShroud V1.7**, **Blood Engine V1.4** et
**Ultimate RPG Combat & Loot V1.3**. `artifacts/safe_packs_recovered.md` distingue
maintenant explicitement :

- **SÉCURITÉ** (`vérifié`) = pas de script malveillant. Ne dit **rien** sur le droit
  d'usage.
- **LICENCE COMMERCIALE** (`confirmée`) = droit d'exploiter.

La confusion des deux a coûté un aller-retour complet. `15+ HQ Aura VFX` reste
**hors périmètre** (licence non confirmée, statut sécurité litigieux), avec la
correction factuelle : sa description « DUPE de Close Combat » est fausse pour le
fichier actuel — 16 groupes de vrais émetteurs — mais la mention « arnaque » porte
sur la transaction, que je ne peux pas vérifier, et reste en place.

### Remesure demandée : le cadrage n'a pas suffi

Traînée activée contre désactivée, même chaîne de 4 M1, **à la nouvelle distance
de caméra (8,5 stud et non plus 13,2)** :

| | pale médiane | pale pic |
|---|---|---|
| sans traînée | 1 475 | 6 086 |
| traînée seule | 1 527 *(+3,5 %)* | 7 384 *(+21 %)* |

Le `Trail` contribue, mais il reste **marginal même au nouveau cadrage**. Sa
largeur est bornée par le bras qui le porte : **2,2 stud**. Le rapprochement de la
caméra n'a donc pas résolu le problème à lui seul — l'hypothèse du `Beam` tient.

### Le `Beam` : la médiane double

Un `Beam` a une largeur **propre**, indépendante du membre. Le pack l'exploite avec
un profil **10 → 0** — large à la racine, fuselée à la pointe.

| | pale médiane | pale pic |
|---|---|---|
| sans traînée | 1 475 | 6 086 |
| traînée seule | 1 527 | 7 384 |
| **traînée + Beam** | **3 922** | 6 755 |

**+157 % de médiane** contre la traînée seule. C'est le chiffre qui compte : une
médiane qui double veut dire que l'arc est présent **pendant tout le geste**, pas
seulement à un pic. La traînée n'avait déplacé que le pic.

Vérifié par le vrai chemin — devices réellement créés :
```
Trail sur Right Arm   couleur (255,205,92)
Beam  sur Right Arm   larg 4.00 -> 0.40  couleur (255,205,92)  tex 6706234595
```

**Ce qu'on prend du pack** : la texture et le profil de largeur. **Ce qu'on garde** :
notre doré-blanc validé, pas le rouge d'origine. Et on **double** la traînée au lieu
de la remplacer — on ne jette pas un acquis mesuré.

### Ce que je ne survends pas

À l'œil, sur capture, le coup a désormais un **champ doré large et structuré** là
où il n'avait qu'un éclat ponctuel. Mais il lit comme un **impact plus plein**, pas
encore comme un **arc balayé distinct** : le Beam se fond dans la gerbe. Le gain
mesuré est réel et net ; la lecture « trait de sabre » ne l'est pas encore.

### Outils : trois pièges des `.rbxm` de pack

1. Les `.rbxl` sont **binaires** — une lecture texte ne rend rien.
2. **Adresser par chemin, pas par nom** : trois nœuds de SoulShroud s'appellent
   `Shockwave`, et le premier trouvé est un `MeshPart` **nu**. Ma première
   extraction a sorti une coquille vide.
3. Le séparateur est `>` et non `/` : un groupe s'appelle littéralement
   `Auras/Humanoid Fx`, slash inclus.
4. Mode `devices` : les groupes de démonstration embarquent un **rig complet**
   (Humanoid, BodyColors, 12 Part). On ne veut pas d'un personnage fantôme.

### Les deux autres devices : extraits, pas encore câblés

- `shockwave.rbxm` — 12 émetteurs + 22 `PointLight` (poussière/fracture au sol)
- `aura.rbxm` — 34 `Beam` + 63 émetteurs, élagué du rig de démonstration

**Ils sont extraits et caractérisés, mais NON câblés ni vérifiés.** Je préfère le
dire que les brancher à la va-vite en fin de course sans les mesurer — c'est
exactement la leçon de cette semaine sur les itérations à l'aveugle.

## 2026-09-01 — JALON B : la caméra, dans l'ordre des prérequis

### 1. L'écart FOV élucidé — ce n'était pas un mystère, c'était un conflit de constantes

| module | constante | ce qu'il faisait |
|---|---|---|
| `CameraController` | `BASE_FOV = 72` | annonçait 72 au démarrage et **l'imprimait** |
| `Surhumain` | `FOV_BASE = 72` | commentaire : « must match CameraController » |
| **`CameraJuice`** | **`BASE_FOV = 70`** | **écrivait 70 par-dessus** |
| **`MovementController`** | **`FOV_BASE = 70`** | **tweenait vers 70** |

Le dernier qui écrit gagne, et ce n'est pas celui qui croit décider. FOV effectif
mesuré : **70**. Aucune enquête n'était nécessaire une fois les constantes mises
côte à côte.

### 2. Centralisation — `CameraDirector`

**FOV = base + somme de décalages NOMMÉS.** Un même effet qui se redéclenche
remplace sa propre contribution au lieu de s'empiler — deux coups rapprochés
cumulaient leurs dips.

Migrés : `CameraController` (hit, dash), `CameraJuice` (sprint tenu, punch),
`MovementController` (sprint, dash), `CombatFXReceiver` (fxkick).

Les deux modules **partagés** ne peuvent pas requérir un module client :
`VFXLibrary` et `Surhumain_LimitBreak` posent l'attribut caméra `FovImpulse`, que
`CombatFXReceiver` transforme en décalage nommé. Surhumain exprime désormais un
**écart** à la base et non une valeur absolue — sa cible absolue écrasait la base
des autres.

**Vérifié : plus une seule écriture de `FieldOfView` hors `CameraDirector`.**

### 3. Caméra dynamique

`PROCHE = 8,0` stud pendant l'échange, `LARGE = 13,0` en déplacement. On ne paie
les **−48 %** de vision périphérique que pendant le combat.

Le resserrement se déclenche sur un **vrai coup confirmé par le serveur**
(`CombatConfirm`), pas sur une heuristique de proximité seule — un PNJ qui passe
à côté ne doit pas resserrer le cadre. La proximité d'un adversaire vivant à
moins de 18 stud, à l'arrêt, compte aussi : sinon le resserrement arrive toujours
en retard d'un échange.

**On ne prend pas la main sur la caméra** (pas de `CameraType.Scriptable`) : on
borne la plage de zoom. Une caméra qu'on arrache au joueur pendant un combat est
pire que le problème qu'elle résout.

### Un défaut trouvé dans ma propre approche

`CameraMaxZoomDistance` ne fait que **borner**. Mesuré :

```
joueur eloigne a 40 stud du mannequin
zoom 0.5-13.0 (borne relachee)  mais distance reelle 8.51, immobile
```

L'abaisser tire bien la caméra vers l'intérieur, mais **le relâcher ne la repousse
pas** — le zoom du joueur reste où la borne l'avait amené. **La caméra se serait
rapprochée définitivement.** C'est le minimum qui force le zoom vers l'extérieur :
on pilote donc les deux bornes.

Puis un second défaut dans ma correction : la condition de libération comparait la
cible à `_zoomMax` (400), donc jamais vraie — le joueur n'aurait jamais récupéré
son zoom. L'intention est maintenant passée explicitement.

### Vérifié par le vrai chemin, aller-retour complet

```
engage (5 stud)   distance  8.51   zoom tenu 8.0-8.0
eloigne +0.6 s    distance 13.28   zoom 0.5-12.9
eloigne +1.2 s    distance 13.30   zoom 0.5-13.0   <- liberte rendue au joueur
```

Le FOV reste à 70 de base sur toute la séquence, avec des décalages transitoires
(70,7 / 70,2) qui reviennent bien à la base — le modèle de décalages fonctionne.

## 2026-09-01 — JALON A : packs VFX dépouillés, et un blocage de licence à trancher

### 1. Statut de licence — rapporté, pas supposé

| pack | vendeur | statut sécurité documenté | **licence commerciale** |
|---|---|---|---|
| `Ultimate RPG Combat & Loot VFX V1.3` | BZ1 Studios | vérifié, `_SAFE_PACKS.01` **présent** | **non documentée** |
| `Blood Engine Ultimate VFX V1.4` | BZ1 Studios | vérifié, slot réservé | **non documentée** |
| `SoulShroud Ultimate VFX V1.7` | BZ1 Studios | vérifié, slot réservé | **non documentée** |
| `15+ HQ Aura VFX` | Skater Studios | ⚠️ noté « ARNAQUE confirmée » | **non documentée** |

**Aucun des quatre n'a de licence commerciale documentée dans le dépôt.** Milan a
confirmé l'usage commercial sur Battleground et Close Combat — pas sur ceux-ci.
« Vérifié » dans l'audit sécurité veut dire *sans script malveillant*, pas
*utilisable commercialement*. Les deux choses ont été confondues jusqu'ici.

**Rien n'a été importé.** C'est le blocage à trancher avant toute application.

### 2. Une note d'audit à corriger

`artifacts/safe_packs_recovered.md` dit du pack d'auras : « ARNAQUE confirmée —
c'est un DUPE de BZ1 Close Combat, pas le contenu vendu ». **L'ouverture du
fichier contredit cela** : il contient 16 groupes nommés, tous de vrais jeux de
`ParticleEmitter` — `Mist`, `Blink`, `Flashstep`, `Fire`, `Lightning`,
`Colourful Flashy Lightning`, `Black Flash`, `Rocks`, `Windy`, `Heal`, `Boost`,
`Bleeding`, et 4 `Misc.` — soit 83 émetteurs. Ce n'est pas un doublon d'un pack
d'animations. Je ne peux pas dire ce qui était vrai en mai ; je dis ce que
contient **ce fichier, aujourd'hui**.

### 3. L'inventaire réel

Les `.rbxl` sont **binaires** — une lecture par expression régulière ne donne
rien, il faut les désérialiser (outils ajoutés : `scripts/vfx_packs/*.luau`).

| pack | devices | dont Beam | dont Trail |
|---|---|---|---|
| SoulShroud V1.7 | **7 496** | **969** | **103** |
| Blood Engine V1.4 | 2 120 | 334 | 68 |
| Ultimate RPG Combat & Loot V1.3 | 1 723 | 47 | 24 |
| 15+ HQ Aura VFX | 105 | 0 | 0 |

**Groupes nommés qui répondent à nos manques identifiés** (noms énumérés, pas
devinés) :

- **L'aura** — SoulShroud `Auras/Humanoid Fx` : 2 265 émetteurs, 476 Beams, 6 Fire.
  Registre exact, et le `Fire` va dans le sens du feu/embrasement doré-blanc validé.
- **La traînée qui ne lit pas** — SoulShroud porte **969 Beams**. Un `Beam` est une
  bande à largeur contrôlée, bien plus lisible à 13 stud qu'un `Trail` de 2,2 stud
  attaché au bras. `Impact Structures + Larger VFX / Slash` est le candidat direct.
- **Poussière et fractures au sol, qu'on n'a jamais eues** — `Impact Structures +
  Larger VFX / Shockwave` : 12 émetteurs + 22 `PointLight`.

### 4. Ce chantier est plus gros qu'annoncé — je le signale avant de m'engager

11 444 devices sur trois packs exploitables, et **la question de licence n'est
tranchée pour aucun**. Importer quoi que ce soit sans ce feu vert serait exactement
le genre de dette qu'on ne veut pas.

**Ce que je propose, si la licence est confirmée** : une tranche étroite plutôt que
tout ouvrir — `Slash` (la traînée lisible), `Shockwave` (poussière/fracture), et
un aura de `Auras/Humanoid Fx` en complément du doré-blanc **sans l'écraser**.
Trois devices, pas trois packs.

## 2026-09-01 — Recoupage M1 appliqué, et les VFX dorment ailleurs

### Le recoupage : 47,3 % → 37,2 % mesurés en moteur

Cible validée : **35,5 %**, pas 25 %. Le raisonnement retenu — un coup lourd a
droit à son anticipation, 25 % est la valeur de jeux dont les M1 sont des jabs
légers ; mais 47 % n'est plus « lourd », c'est **en retard**, et le coût se paie
en délai entre le clic et l'impact.

**Méthode** — `retime_anticipation` : remappage linéaire **par morceaux** du temps,
`[0,c] → [0,cible]` et `[c,1] → [cible,1]`. L'anticipation se comprime, le
follow-through s'étire d'autant, la durée totale ne bouge pas.

| M1 | classe | avant | cible | **moteur** | anticipation |
|---|---|---|---|---|---|
| M1_1 | straight | 49,3 % | 33 % | **34,1 %** | 0,271 → 0,181 s |
| M1_2 | hook | 58,3 % | 38 % | **41,0 %** | 0,350 → 0,228 s |
| M1_3 | uppercut | 38,8 % | 33 % | **34,0 %** | 0,252 → 0,214 s |
| M1_4 | overhead | 42,9 % | 38 % | **39,7 %** | 0,364 → 0,323 s |

L'écart aux cibles est **inférieur à une frame** (33 ms à 30 fps) : le marqueur se
cale sur une frame réelle.

### Les contraintes, vérifiées et non supposées

- **Aucune keyframe ajoutée** : 72 / 37 / 50 / 36 avant **et** après.
- **Gate de classe PASS** sur les quatre, amplitude **inchangée au millième**
  (3,233 / 2,893 / 3,069 / 4,118) — un remappage du temps ne touche pas la
  géométrie.
- **Le poids n'est pas perdu** : le follow-through **s'allonge** de +9 % à +49 %.
  Le poids d'un coup vient de la suite du geste et du hitstop, pas de la longueur
  de la préparation.

### Un défaut préexistant mis au jour, non corrigé ici

L'ordre attendu `Windup → Whoosh → Impact` n'est respecté que par **M1_2**. Avant
ce recoupage, M1_3 et M1_4 avaient déjà `Whoosh` **après** `Impact` (0,300 vs
0,252 et 0,400 vs 0,364), ce qui n'a pas de sens pour un marqueur documenté comme
« pre-impact » dans `AnimationMarkerRouter`. Deux règles différentes posent ces
marqueurs et personne ne les a jamais rapprochées. Le rapport `Windup / Impact`
est **exactement préservé** par mon remappage (0,61 / 0,51 / 0,77 / 0,70 avant
comme après) : l'incohérence est **héritée, pas introduite**. Non corrigée ici —
ce serait changer une convention en douce au milieu d'un autre chantier.

### Devices inutilisés : ils ne sont pas où on les cherchait

Les dumps de packs ne contiennent **que des animations** (`anims`, `pose_names`,
`rig`). Ils ont été extraits en données de keyframes : aucun `ParticleEmitter`,
`Beam`, `Trail` ni `Sound` n'y a jamais été capturé. Chercher des devices dedans
ne pouvait rien donner.

**En revanche, cinq packs VFX dédiés dorment sur le disque, jamais dépouillés :**

| fichier | note |
|---|---|
| `15+ HQ Aura VFX.rbxl` | auras — exactement le registre Demi-Dieu |
| `SoulShroud Ultimate VFX Pack V1.7` | marqué SAFE à l'audit sécurité |
| `Blood Engine Ultimate VFX Pack V1.4` | marqué SAFE (deux copies sur disque) |
| `Ultimate RPG Combat & Loot VFX Pack V1.3` | combat + loot |

Le `.rbxl` de Close Combat est également toujours présent, donc ses devices
éventuels restent extractibles.

**Rien n'a été extrait ni importé** — signalé pour décision commune, comme demandé.
Deux questions à trancher avant d'y toucher : la **licence commerciale** de ces
cinq packs (seuls Battleground et Close Combat sont confirmés), et lesquels
valent le coût d'extraction.

## 2026-09-01 — Dash v2 : la catapulte existe enfin

### Le trou

Le dash n'avait **jamais** cherché ailleurs que dans les **19 clips de
Battleground**, alors que Close Combat en contient **210**. C'était le trou le plus
évident du kit, sur sa pièce la plus faible.

### Une métrique d'abord, parce que la première était fausse

`max − min` sur l'angle de torse renvoyait **347 degrés** en tête de classement :
un spin kick enroule l'angle. Cette métrique classait les rotations, pas les
projections. Remplacée par une mesure **géométrique** via la FK — amplitude, en
stud, du décalage avant entre la tête et la racine — insensible à la rotation.

### Ce que le §4 demande, et ce que chaque clip fait

Le pied **frappe le sol**, *puis* le corps **se projette**. Donc deux grandeurs et
un **ordre** :

| clip | appui | poussée | appui à | poussée à | ordre |
|---|---|---|---|---|---|
| `[3] Forward Dash` *(source v1)* | 1,34 | 0,94 | 63 % | 0 % | **non** |
| `[1] Run` *(source v1)* | 0,28 | 0,17 | 95 % | 95 % | oui |
| `Regular Kick` | 3,37 | 1,04 | 71 % | 71 % | simultané |
| **`Stylized Jump / Vault`** | **3,06** | **1,75** | **69 %** | **76 %** | **oui** |

Le vault est le **seul** clip du corpus licencié qui porte les deux phases dans le
bon ordre, avec la poussée la plus forte. `Regular Kick` a de bonnes magnitudes
mais appui et poussée coïncident — ce n'est pas une catapulte, c'est un choc.

### Résultat

Span 0,55–0,95 du vault, retimé (0,871) vers 0,45 s :

| | appui | poussée | ordre |
|---|---|---|---|
| v1 | 0,42 | 0,26 | **non** (poussée à 44 %, appui à 67 %) |
| **v2** | **3,13** | **1,72** | **oui** (appui à 38 %, poussée à 59 %) |

**7,5× l'appui, 6,6× la poussée**, et l'ordre inversé remis à l'endroit. Gate
mouvement PASS (`static_run` 0,1613).

### Vérifié par le vrai chemin

Slot `PasDivin` d'`AnimationDB`, animation chargée depuis l'identifiant réel
(`93826732069681`, uploadé par asphalt) : durée **0,450 s**, marqueur **`Plant`
qui fire à 0,1833 s** (posé à 0,1742, soit moins d'une frame d'écart).

### Un troisième artefact de mesure, à consigner

Mon premier relevé disait « le marqueur ne fire pas ». **Faux** : je jouais la
piste à `Play(0, 0, 1)`, donc **à poids 0** — et un marqueur ne se déclenche pas
sur une piste de poids nul. À poids 1,0 il fire normalement.

Trois artefacts de mesure ce tour, tous du même genre : **sonde expirée**,
**`AssemblyLinearVelocity` à 0 sous contrainte**, **marqueur muet à poids 0**.
Aucun n'était un défaut du jeu ; tous auraient pu être rapportés comme tels.

## 2026-09-01 — Marche du Titan touche enfin, et elle marche toujours

Reprise. Machine, plugin MCP, Play et synchro rojo verifies avant toute mesure ;
**aucune sonde residuelle** (Client, Serveur, Edit) — un seul ecart de synchro,
`AssetVerifier`, resynchronise.

### Le balayage demandé : le schéma existe ailleurs, mais il n'est pas seul en cause

Six modules déplacent le personnage **et** frappent sur un délai fixe :
`Skill1_DashStrike`, `Skill1_MainDuColosse`, `Skill2_FrappeCeleste`,
`Skill2_TorrentCarnassier`, `Skill3_MarcheDuTitan`, `Ultimate` (déjà corrigé).

Mais Skill1 et Skill2 **touchent** (20 et 22 dégâts mesurés) : le schéma seul
n'est pas le défaut. Le critère qui discrimine est **le trajet parcouru pendant
le délai contre la portée du coup** :

| module | portée | trajet | verdict |
|---|---|---|---|
| Skill3_MarcheDuTitan | 7,0 | **24,8 stud** | dépasse sa portée de 3,5× |
| Ultimate | 14,0 | 14,0 | limite — son défaut était vertical, corrigé |

*(Ma première version du balayage a raté Marche du Titan : `finalStrike` est
appelée via une fonction, le corps du `task.delay` ne contient pas la frappe. J'ai
corrigé l'heuristique pour résoudre un niveau d'indirection avant de m'y fier.)*

### La mesure, avant correction

```
t=0.05  distance  2.05  cible DEVANT et a portee
t=0.12  distance  4.79  cible DERRIERE
t=0.86  distance 23.99  la marche s'arrete
t=1.05                  finalStrike part enfin
```

La fenêtre utile dure **0,12 s** ; le coup partait **8,75× trop tard**, et la
cible n'était pas seulement loin, elle était **derrière**.

### Trois corrections, chacune corrigeant la précédente

1. **Arrêt au contact.** Marche → touche. Mais mesure à 8 stud : le coup partait
   *avant* que le personnage bouge, la hitbox étant une boîte centrée en avant qui
   mord déjà à cette distance. **La Marche du Titan ne marchait plus.** Corriger un
   défaut de portée en supprimant l'identité du coup n'est pas une correction.
2. **Découplage** frapper / s'arrêter : le coup part au contact, le pas en cours va
   au bout, seuls les pas restants sont annulés.
3. **Premier pas inconditionnel et synchrone.** Le guet gagnait la course contre
   le `task.delay(0)` du pas 1 et annulait *tous* les pas.

### Vérifié à trois distances, par le vrai chemin

| départ | trajet réel | dégâts |
|---|---|---|
| 20 stud | 20 → 2 stud | **35** |
| 8 stud | 8 → 2,84 stud | **35** |
| 5 stud | 5 → 1,86 stud | **35** (+35 au compteur cumulatif) |

Elle marche à chaque distance, et elle touche à chaque distance.

### Une erreur de mesure à consigner

Deux relevés intermédiaires m'ont fait conclure « le personnage ne bouge pas ».
**C'était faux, deux fois, pour deux raisons différentes :**
- une sonde à fenêtre de 3 s expirait avant l'injection clavier MCP (retard
  variable) — je relisais des lignes périmées ;
- `AssemblyLinearVelocity` lit **0** côté serveur pendant qu'une `LinearVelocity`
  pilote la position. Il faut guetter **la contrainte**, pas la vitesse.

À retenir pour toute mesure de déplacement piloté par contrainte.

## 2026-08-31 — NOTE DE REPRISE (pause demandée)

À lire en premier à la reprise. Pause posée par l'utilisateur ; le second passage
packs et le recoupage M1 sont **explicitement hors périmètre** jusqu'à nouvel ordre.

### Verdict de l'état des lieux — il est bouclé

Les 4 compétences et l'ultime jouent, poids 1,00, aucun Idle prématuré, aucune
couche qui en écrase une autre. **Deux sont tronquées par leur propre `recovery`**
(Main du Colosse 64 %, Frappe Céleste 54 %), pas par un conflit d'animation. Les
réactions du rig sont cohérentes avec le coup reçu sur les trois paliers. Le
kit est **nettement meilleur** qu'il y a trois jours sur l'ultime, les réactions,
le flash et la vérification d'assets ; **équivalent** sur les M1, la gerbe et le
cadrage ; **encore faible** sur quatre points listés plus bas.

### Ce qui a été corrigé sur l'ultime — fini, vérifié

Trois défauts enchaînés, tous mesurés à 20 Hz sur le vrai chemin :

1. **L'impact partait sur un délai fixe** de `RISE + SUSPEND + FALL` = 1,15 s,
   alors que le commentaire du code disait déjà « Impact, at landing ».
   L'atterrissage réel est à **0,92 s**.
2. **L'impulsion de chute** (`FALL_SPEED = -90`, `MaxForce = math.huge`)
   continuait de pousser dans le sol jusqu'à `FALL_DURATION`. Le solveur éjecte :
   le personnage repartait vers le haut à 1,07 s et dépassait 80 stud.
3. Conséquence : à 1,15 s l'onde cherchait ses cibles depuis **22 stud de haut**,
   hors de `IMPACT_RADIUS = 14`. **Zéro dégât, zéro erreur en console.**

Corrections livrées (`2c27d00`, `2a5d9f7`, `82ba7f5`) :
- impact calé sur l'atterrissage **réel** ;
- détection **géométrique** (hauteur mémorisée au cast) et non `FloorMaterial` —
  celui-ci renvoie `Air` à l'atterrissage parce que l'impulsion enfonce le
  personnage **sous** le sol (hauteur 1,37 pour un repos à 3,00) ;
- purge de `AssemblyLinearVelocity` + repose à la hauteur de départ : détruire la
  `LinearVelocity` ne suffisait pas, il remontait encore à 30 stud.

**Après : 50 dégâts infligés, hauteur max 27,68 stud (l'apogée voulue), plus
d'éjection, réaction `KnockedDown`.**

### PISTE À NE PAS REPERDRE — même famille de bug sur Marche du Titan

`FALL_SPEED` et l'impact-à-l'atterrissage sont réglés pour l'ultime, mais
**Marche du Titan souffre exactement du même schéma** : elle joue à 96 % et
n'inflige jamais de dégât. Trace de distance relevée pendant le cast :

```
6,93 -> 4,92 -> 8,38 -> 10,85 -> 15,98 -> 18,84 stud
```

Elle traverse la cible (4,92) puis emmène le joueur **19 stud au-delà**. Son
`finalStrike` utilise `HitboxService.ComputeTargets` avec une portée de 7, mais il
se déclenche quand le joueur est déjà loin. **Hypothèse à vérifier en premier à la
reprise** : le coup final est lui aussi câblé sur un délai fixe plutôt que sur la
fin réelle du déplacement — c'est-à-dire le même défaut que l'ultime, dans le
module `src/server/Skills/Skill3_MarcheDuTitan.lua`. Ne pas corriger à l'aveugle :
mesurer d'abord l'instant réel de `finalStrike` contre l'instant réel d'arrêt.

### PISTE DASH — trouvée, en attente de reprise

**Le dash n'a jamais cherché dans Close Combat.** Il ne s'appuie que sur les
**19 clips de Battleground**, alors que Close Combat en contient **210**. C'est le
trou le plus évident du kit sur la pièce dont la correspondance est la plus faible.

Référence mesurée du dash actuel : **appui 0,42 stud, poussée 0,26 stud**.
Meilleure piste trouvée : `closecombat / Regular Kick` — appui **3,37**, poussée
**1,04**, durée **0,20 s** (8× l'appui, 4× la poussée, la seule durée de dash de
la liste). Réserve : un coup de pied lève une jambe haut, ça peut mal lire sur un
dash — **il faut assembler et passer la cascade de gates avant de conclure**.
Analyse rejouable : `scripts/animator_ai/dash_second_pass.py`.

**Cette piste attend la reprise. Rien n'a été assemblé ni modifié.**

### Ce qui reste ouvert

**Défauts connus, non corrigés :**
1. Main du Colosse coupée à **64 %**, Frappe Céleste à **54 %** par leur
   `recovery` de 0,55 s. (Le chiffre est plus sévère que les 84 % documentés le
   29, qui mesuraient le mouvement vu, pas la position de la piste.)
2. **Marche du Titan ne touche jamais** — voir la piste ci-dessus.
3. **Jugement inatteignable au momentum plein** : `R` est partagé avec l'ultime,
   qui gagne dès que le momentum est à 100. Question de **design**, pas un bug.
4. **Les traînées ne lisent pas** — deux itérations mesurées, la cause est
   l'échelle relative à la gerbe, pas la traînée elle-même.
5. `test_moving_contact::TestTracking` rouge depuis le 2026-08-25.

**Décisions qui t'appartiennent :**

- **Arbitrage caméra (Milan, non tranché).** Notre caméra de combat est à 13 stud,
  FOV 70, le personnage occupe 27,5 % de la hauteur d'écran. À 6,7 stud il en
  occupe 53 % et le travail VFX devient lisible. Coût mesuré en vision
  périphérique : le cadre passe de **38,0 à 19,6 stud de large**, soit **−48 %**.
  Proposition remontée : une caméra qui se rapproche pendant l'échange et recule
  en déplacement. Deux éléments pour décider : (a) `CameraController` pose
  `BASE_FOV = 72` mais le FOV **effectif est 70** — un écart à éclaircir AVANT de
  régler quoi que ce soit ; (b) cinq modules touchent au FOV ou à la caméra, donc
  le coût réel n'est pas la caméra mais la **centralisation** en un point d'entrée.
  **Rien n'a été touché sur la caméra.**

- **Cible intermédiaire du timing M1 — à valider avant que je touche à quoi que
  ce soit.** Contact réel mesuré : 49,3 % / 58,3 % / 38,8 % / 42,9 %, moyenne
  **47,3 %**.

  | M1 | classe | actuel | cible proposée | contact |
  |---|---|---|---|---|
  | M1_1 | straight | 49,3 % | **33 %** | 0,271 → 0,182 s |
  | M1_2 | hook | 58,3 % | **38 %** | 0,350 → 0,228 s |
  | M1_3 | uppercut | 38,8 % | **33 %** | 0,252 → 0,215 s |
  | M1_4 | overhead | 42,9 % | **38 %** | 0,364 → 0,323 s |

  Moyenne 47,3 % → **35,5 %**. **Pas 25 %** : c'est la valeur de jeux dont les M1
  sont des jabs légers, et l'identité Demi-Dieu est le coup lourd, qui a droit à
  plus d'anticipation. Mais 47 % n'est plus « lourd », c'est **en retard** — le
  coût se paie en délai entre le clic et l'impact. Le poids reste dans le
  follow-through et le hitstop, qu'on ne touche pas. Méthode : remappage temporel
  du seul segment d'anticipation, durée totale inchangée, **aucune keyframe
  ajoutée**.

- **Licence des packs.** Seuls Battleground et Close Combat sont autorisés. Les
  six autres dumps ne peuvent rien fournir en production — et 3 d'entre eux sont
  de toute façon R15. Cela bloque aussi l'inventaire des devices VFX.

### État machine à la pause

La machine était déjà repartie avant la demande de pause : `screencapture` échoue
avec `could not create image from display`, le MCP répond `Place is not open`.
**Studio n'a pas été fermé par moi, et aucune sauvegarde n'a pu être confirmée.**

Toutes les sondes étaient insérées dans le DataModel de **Play** (serveur :
`play_scene_server`, `sonde_kit`, `sonde_ult`, `sonde_ult2`, `sonde_dist`,
`sonde_log`, `sonde_hits`, `sonde_reactions`, `sonde_trails` ; client :
`_SondeKitClient`, `_SondeTrailsClient`). Play étant arrêté, elles ont disparu
avec lui. **Aucune sonde n'a jamais été insérée en Edit** — seules des sources de
modules identiques au disque y ont été poussées. À vérifier tout de même à la
reprise, place rouverte.

## 2026-08-31 (suite 3) — Second passage packs : deux blocages, et une piste chiffrée pour le dash

### Deux blocages à signaler avant tout

1. **Trois des six autres dumps sont R15** — `free` (104 clips), `movesets` (120),
   `virtualvogue` (50). C'est le mauvais rig, et c'est exactement ce dont on vient
   de sortir avec les réactions. Inutilisables tels quels.
2. **La licence commerciale n'est confirmée que sur Battleground et Close
   Combat.** Les six autres dumps n'ont pas d'autorisation documentée dans le
   dépôt. Rien de ce qu'ils contiennent ne peut partir en production sans que
   Milan tranche.

Le second passage utile s'est donc porté sur ce qui est actionnable : les
**229 clips des deux packs licenciés**, dont Close Combat (210 clips) que le dash
n'avait **jamais** fouillé — il ne s'appuyait que sur les 19 clips de
Battleground. C'était le trou évident.

### Une métrique fausse, corrigée avant de conclure

Premier passage : « poussée de torse » mesurée en `max − min` de l'angle du
RootJoint. Résultat, des clips à **347 degrés** en tête de classement — un spin
kick enroule l'angle, ce n'est pas une inclinaison avant. La métrique classait
les rotations, pas les projections.

Remplacée par une mesure **géométrique** via la FK : amplitude, en stud, du
décalage avant entre la tête et la racine. Insensible à la rotation, et c'est ce
que « le corps se projette » veut dire physiquement.

### Ce que ça donne

**Référence, le dash actuel : appui 0,42 stud, poussée 0,26 stud.** La poussée est
quasi nulle — ça chiffre en stud la faiblesse déjà notée (13,6 deg d'amplitude).

Les candidats des packs licenciés qui font mieux sans perdre l'appui :

| pack | clip | appui | poussée | durée |
|---|---|---|---|---|
| closecombat | **Regular Kick** | **3,37** | **1,04** | **0,20 s** |
| closecombat | Elbow Jab | 3,37 | 0,32 | 0,20 s |
| battleground | [3] Downslam V1 | 1,72 | 2,59 | 1,08 s |
| closecombat | Jumping Spin Kick | 2,86 | 2,56 | 0,88 s |
| closecombat | Stylized Jump / Vault | 3,06 | 1,75 | 1,35 s |

**`Regular Kick` est la piste sérieuse** : 8× l'appui actuel, 4× la poussée, et
0,20 s — la seule durée de la liste qui soit une durée de dash. Les trois autres
en tête sont un slam (déjà assigné à Chute Divine par le §8), un saut tourné et
un vault : aucun n'est un déplacement au sol.

**Réserve que je ne masque pas** : un coup de pied lève une jambe haut, ce qui
peut mal lire sur un dash. Il faut assembler et passer la cascade de gates avant
de conclure — et ça demande le moteur.

### Non fait, et pourquoi

**La machine est repartie en cours de second passage** : `screencapture` échoue
avec `could not create image from display` et le MCP répond `Place is not open`.
Studio n'a pas été fermé par moi. Donc pas d'assemblage vérifié, pas de passage
par les gates, pas de capture du dash. L'analyse disque est complète et rejouable
(`scripts/animator_ai/dash_second_pass.py`).

L'inventaire des **devices VFX inutilisés** est bloqué sur le même point de
licence : les devices des six dumps non autorisés ne peuvent pas être embarqués.

## 2026-08-31 (suite 2) — État des lieux du kit avec le harnais corrigé

Milan demande si les compétences et l'ultime jouent bien, et si c'est réellement
meilleur. Réponse mesurée, harnais corrigé, repositionnement avant chaque cast.

### Le piège, confirmé : nos jugements passés étaient faussés

Deux défauts du harnais, tous deux corrigés aujourd'hui :

1. `STAND_OFF = 8` stud alors que M1_1..M1_3 portent à 6 → un seul coup sur
   quatre touchait.
2. `faceDummy()` ne tournait **qu'une fois à l'insertion**. Après un dash ou une
   Marche du Titan, le joueur se retrouvait à 26 puis 68 stud du mannequin, et
   les compétences suivantes « ne touchaient pas ». Ce n'était pas la compétence.

Le harnais a maintenant un repositionnement à la demande (attribut `Replace`).

### Ce que jouent réellement les animations

| pièce | durée | atteint | poids | interruption |
|---|---|---|---|---|
| Pas Divin | 0,45 s | **96 %** | 1,00 | non |
| Main du Colosse | 0,70 s | **64 %** | 1,00 | `recovery` 0,55 s |
| Frappe Céleste | 0,83 s | **54 %** | 1,00 | `recovery` 0,55 s |
| Marche du Titan | 0,97 s | **96 %** | 1,00 | non |
| Ultime | 4,50 s | **91 %** | 1,00 | non |

Poids 1,00 partout : aucune n'est écrasée par une autre couche, aucun Idle
prématuré. Les deux qui sont coupées le sont par leur `recovery`, pas par un
conflit d'animation.

### L'ultime : il était cassé, il ne l'est plus

Trouvé en mesurant à 20 Hz. Deux défauts qui se renforçaient :

1. L'impact se déclenchait sur un **délai fixe** de RISE+SUSPEND+FALL = 1,15 s,
   alors que le commentaire du code disait déjà « Impact, at landing ».
2. L'impulsion de chute (LinearVelocity −90, MaxForce infini) continuait de
   pousser dans le sol ; le solveur éjectait le personnage vers le haut.

```
t=0.92  hauteur  2.64  distance 3D  4.98   dans le rayon
t=1.07  hauteur 11.28  distance 3D 10.23   dans le rayon
t=1.15  hauteur 23.48  distance 3D 21.98   HORS RAYON (14)   <- l'impact
```

**L'onde cherchait ses cibles depuis 22 stud de haut. Zéro dégât, sans la moindre
erreur en console.** Et c'est ce qui envoyait ensuite le joueur à 68 stud, ce qui
faisait passer les compétences suivantes pour cassées.

Corrigé en trois passes, chacune mesurée :
- impact calé sur l'atterrissage réel ;
- `FloorMaterial` ne marche pas ici (l'impulsion enfonce le personnage **sous**
  le sol, hauteur 1,37 pour un repos à 3,00, le rayon de détection part de sous
  la géométrie) → détection géométrique sur la hauteur de départ ;
- purge de `AssemblyLinearVelocity` à l'atterrissage : détruire la
  LinearVelocity ne suffisait pas, le personnage remontait encore à 30 stud.

**Après : 50 dégâts infligés, hauteur max 27,68 stud (l'apogée voulue), plus
d'éjection.** Réaction déclenchée : `KnockedDown`, 1,25 s au sol.

### Les réactions du rig sont cohérentes avec le coup

```
4 x M1   6 dégâts  ->  Front_V3, Front_V2, Face, Front_V2   (léger, varié)
Skill1  20 dégâts  ->  HitReactHeavy                        (lourd)
Skill2  22 dégâts  ->  HitHeavy_GutFast                     (lourd)
Ultime  50 dégâts  ->  KnockedDown                          (projection)
```

Tous à 5,00 stud mesurés, tous par le vrai chemin.

### Comparaison honnête avec il y a trois jours

**Meilleur, chiffres à l'appui :**

| | 2026-08-28 | aujourd'hui |
|---|---|---|
| ultime, dégâts | 0 (non détecté) | **50** |
| ultime, éjection | jusqu'à 80+ stud | **aucune** |
| ultime, `recovery` | 1,40 s (coupait à 31 %) | 4,50 s (91 %) |
| réactions du rig | 3, conversions R6→R15 | **13 natives R6**, 3 paliers variés |
| réaction sur un jab | palier faussé par le cumul | correcte |
| flash d'impact | 1 flash blanc pour 23 recettes | différencié par pièce |
| assets vérifiés | inconnu (l'outil ne pouvait pas) | **58/58 mesurés** |
| hitstop | 0–2 ms | 114–136 ms |
| secousse caméra | 0,16 stud | 1,0–1,4 stud |

**Équivalent :** les animations M1 elles-mêmes, la gerbe d'impact (le −30 % n'a
donné que −10 % à l'écran), le cadrage.

**Reste faible, sans enjoliver :**
1. **Main du Colosse coupée à 64 %, Frappe Céleste à 54 %.** Le `recovery` de
   0,55 s tronque les deux. C'est l'arbitrage en attente depuis le 2026-08-29 —
   et le chiffre réel est plus sévère que les 84 % documentés alors, qui
   mesuraient le mouvement vu, pas la position de la piste.
2. **Marche du Titan ne touche toujours pas.** Elle joue à 96 %, mais elle
   déplace le joueur au-delà de la cible : trace de distance 6,93 → 4,92 → 8,38
   → 10,85 → 15,98 → 18,84 stud. Le coup final cherche ses cibles quand le
   joueur est déjà 19 stud plus loin. Même famille de bug que l'ultime.
3. **Jugement est inatteignable au momentum plein.** `R` est partagé : au-dessus
   de 100 de momentum il part toujours en ultime. Question de design, pas un bug
   — je ne tranche pas.
4. **Les traînées ne lisent toujours pas.** Deux itérations mesurées, la cause
   est l'échelle relative à la gerbe, pas la traînée.

## 2026-08-31 (suite) — Trois bugs de fond trouves en verifiant, pas en cherchant

Reprise de la file d'attente. Chaque etape a revele un defaut plus serieux que
l'etape elle-meme.

### 1. Capture apres la gerbe −30 % — et le harnais etait faux

Avant de pouvoir comparer, la sonde a montre que **le harnais de capture placait
le joueur hors de portee de trois M1 sur quatre**. `STAND_OFF = 8` stud, alors que
M1_1 a M1_3 portent a 6 et M1_4 a 7. Sur une chaine de quatre clics, **un seul
coup touchait**. Toutes les captures faites avec ce reglage montraient des impacts
absents qu'on pouvait prendre pour un defaut de VFX.

Corrige a 5 stud : 4 impacts sur 4.

Comparaison refaite, cadrages apparies sur la taille du personnage a l'ecran :

| | couverture doree | coeur sature |
|---|---|---|
| avant (gerbe pleine) | 19,85 % | 1,71 % |
| apres (gerbe −30 %) | 17,71 % | 2,94 % |

**−30 % sur les parametres ne donne que −10 % a l'ecran**, et le coeur sature ne
bouge pas. La trainee ne lit toujours pas. Sonde cote client : elle est bien
creee sur le bras, active, 2,20 stud d'envergure, opaque — **elle est correcte,
juste minuscule face a la gerbe**. Ce n'est pas un probleme de trainee.

### 2. Les 13 reactions natives R6

Uploadees par asphalt (13 identifiants reels), reparties sur les trois paliers :
4 legeres, 4 lourdes, 4 projections, 1 etourdissement. Le mannequin tire dans le
pool du palier sans repetition immediate.

**Et la variete a revele un bug qui dormait :** la reaction escaladait sur le
**cumul** de degats, pas sur le coup. `MAX_HP - newHp` mesure les degats depuis
les PV pleins, et le mannequin ne se soigne qu'apres 2 s. Mesure :

```
chaine 6/6/8/12  ->  cumul 6/12/20/32/38/44
reactions        ->  leger, lourd, lourd, lourd, lourd, PROJECTION
```

**Un jab a 6 degats declenchait la reaction reservee a l'ultime.** Le bug
preexistait ; avec trois reactions seulement il etait invisible, parce que
« lourd » et « projection » se ressemblaient assez. La variete l'a rendu lisible.

Verifie apres correction, par le vrai chemin : 6 et 8 -> leger, 20 et 22 ->
lourd, 50 -> projection, avec variation a chaque palier.

### 3. `AssetVerifier` ne pouvait pas verifier

`classify` regardait la **forme** de l'identifiant et renvoyait `UNVERIFIED` des
qu'il ressemblait a un vrai id, avec le commentaire « TimeLength not yet
confirmed ». Rien, nulle part, ne confirmait ce TimeLength : **la branche
`VERIFIED` n'existait pas dans le code.**

`VERIFIED=0 UNVERIFIED=45` etait un artefact de construction. Le meme resultat
serait sorti avec 45 animations parfaitement fonctionnelles — un diagnostic
incapable de diagnostiquer, sur l'outil cense faire respecter la regle
anti-hallucination du projet.

Reecrit : chaque slot est charge sur un Animator jetable et sa duree **mesuree**.
Nouveau statut `FAILED` pour le cas dangereux que la regle decrit (pcall qui
reussit sur une animation vide) — il n'avait aucune categorie.

Passe en Play Solo : **`VERIFIED=58 FAILED=0 NOTUPLOADED=0 ROBLOXDEFAULT=0`**.
`verified_assets.json` regenere avec la duree mesuree de chaque slot.

### 4. Les 23 recettes decrivaient leur flash, les 23 donnaient le meme

Chaque recette ecrit `screen_flash = { color, duration, peak }`. Le receveur
appelait `Flash()` **sans argument** : les 23 produisaient a l'ecran exactement le
meme flash blanc de 0,050 s. Le jab Demi-Dieu (peak 0,11) et l'ultime (0,32)
etaient indiscernables.

Mon propre commentaire dans le receveur affirmait que « `Flash()` ne prend aucun
argument ». **C'etait faux** : il decrivait `src/client/V1/ImpactFrameController.lua`,
qui porte le meme nom mais n'est pas le module requis. Consequence a signaler :
la baisse de 30 % appliquee plus tot portait entre autres sur `peak`, qui
n'atteignait pas l'ecran — cette part-la etait sans effet.

Puis **ma premiere correction s'est trompee dans l'autre sens.** J'avais cale la
correspondance pour rester sous l'ancien preset. Mesure dans un coin d'ecran
eloigne de l'action, ou seul un effet plein ecran peut changer quelque chose :

| | luminance | saturation |
|---|---|---|
| avant cablage | + 2,9 | − 1,3 |
| teinte brute | **+41,1** | **−63,6** |
| teinte interpolee | +13,2 | −10,4 |

`TintColor` est un **multiplicateur sur toute l'image** : poser GOLD_PALE brut
repeignait la scene entiere. L'intention ne remplace pas la mesure. Corrige en
interpolant depuis le blanc proportionnellement au peak.

### Elements pour l'arbitrage camera (je ne tranche pas)

- **Ce que le joueur perd concretement en se rapprochant** : a 13 stud le cadre
  couvre **38,0 stud de large** au plan du personnage ; a 6,7 stud, **19,6 stud**,
  soit **48 % de moins**. C'est le chiffre reel du cout en vision peripherique.
- **Un ecart interne a signaler** : `CameraController` pose `BASE_FOV = 72` et
  l'imprime au demarrage, mais le FOV effectif mesure en jeu est **70**. Quelque
  chose en aval le corrige. A eclaircir avant de regler quoi que ce soit sur la
  camera, sinon on reglera sur une valeur qui n'est pas celle qui s'applique.
- **Ce que d'autres systemes supposent** : cinq modules touchent au FOV ou a la
  camera (`CameraController`, `CameraJuice`, `MovementController`,
  `CombatFXReceiver`, `Surhumain_LimitBreak`). Une camera dynamique devra passer
  par un seul point d'entree, sinon les dips de FOV existants et le rapprochement
  se combattront. C'est le vrai cout : pas la camera elle-meme, la centralisation.

## 2026-08-31 — Le cadrage est un vrai sujet, mais la traînée ne lit toujours pas

**Méthode imposée par Milan, et elle était juste** : tester l'hypothèse 2 (le
cadrage) avant l'hypothèse 1 (alléger la gerbe), parce que l'hypothèse 2 ne coûte
rien alors que l'hypothèse 1 dégrade un effet déjà validé.

### Notre caméra de combat, mesurée

| grandeur | valeur en jeu |
|---|---|
| distance au personnage | 13,0 stud |
| champ de vision | 70° |
| viewport | 1231 × 588 |
| hauteur du personnage à l'écran | 162 px = **27,5 %** |
| hauteur d'un bras à l'écran | 65 px |

Même chaîne de 4 M1 recapturée avec une caméra **de capture seule** à ~6,7 stud
(aucune valeur de jeu touchée, restauration automatique) : le personnage occupe
**53 %** de la hauteur d'écran, soit environ le double.

### Verdict, partagé

- **Le cadrage compte, beaucoup.** À 6,7 stud l'embrasement d'impact est riche et
  lisible — arcs électriques, aura dorée, recul du mannequin bien visible. À 13
  stud le même effet est un petit éclat. Une grande partie du travail VFX ne se
  voit pas en jeu.
- **Mais la traînée ne ressort toujours pas** comme un ruban distinct, même de
  près. L'hypothèse 2 tombe *sur la traînée* : c'est bien la gerbe qui la couvre.

### Ce que j'ai appliqué

Gerbe **−30 % sur les M1 uniquement** — magnitudes, taille de l'atome d'impact,
pic du flash d'écran. L'ultime et les 4 compétences ne bougent pas : leur
embrasement a été validé.

| recette | magnitudes | taille impact | pic flash |
|---|---|---|---|
| M1_1 | 0,42 | 1,26 | 0,11 |
| M1_4 | 0,70 / 0,70 / 0,63 | 2,10 | 0,21 |
| Skill1 *(témoin, inchangé)* | 1,0 / 1,0 / 1,0 / 0,8 | 3,00 | 0,28 |
| Ultime *(témoin, inchangé)* | 1,1 / 1,3 / 1,3 | 3,20 | 0,32 |

Tests 7/7, stylua et selene propres, poussé et vérifié dans la place avant l'arrêt.

### Ce qui n'est PAS fait, et pourquoi

**La capture après −30 % n'existe pas.** La machine est devenue indisponible en
cours de route : le plugin MCP ne répond plus (`Place is not open`) et
`screencapture` échoue avec `could not create image from display` — la signature
d'un écran verrouillé ou endormi. Je n'ai pas fermé Studio. La comparaison
avant/après de la gerbe reste donc à faire dès que la machine revient.

### Constat UX/systèmes, plus large qu'une capture

Notre caméra de combat est **trop reculée pour que le travail d'animation se voie
en jeu**. 27,5 % de hauteur d'écran pour le personnage, c'est un cadrage
d'exploration, pas de combat. Ça conditionne le rendement de *tout* ce qu'on
produit en animation et en VFX : on peaufine des gestes qui arrivent au joueur à
65 px de bras. À arbitrer — je ne tranche pas.

## 2026-08-31 — Traînées réglées, nameplate masqué — et la traînée ne lit toujours pas

### Appliqué comme validé

`Lifetime` **0,14 → 0,30 s**, attaches **±0,8 → ±1,1 stud** (ruban de 2,2 stud).
Vérifié dans la place : `LightEmission = 0.35`, `Lifetime = 0.30`, attaches 1.1.

### Nameplate masqué

Le nom et la barre de vie du rig sont coupés
(`DisplayDistanceType = None`, `HealthDisplayType = AlwaysOff`). Vérifié en
moteur, et visible sur la capture : ils ont disparu du cadre.

**Moyen de les rendre pour déboguer**, sans toucher au script :
`dummy.Humanoid:SetAttribute("ShowNameplate", true)`.

### Le constat honnête : ça ne suffit pas

Après le réglage validé, j'ai regardé — **la traînée ne se lit toujours pas comme
un arc**. J'ai cherché la cause plutôt que de le présenter comme réussi.

**Cause mesurée : un problème de CONTRASTE, pas de durée.**
`trail.Color` partait du **blanc pur** avant de virer vers la couleur demandée, et
les recettes envoyaient `GOLD_PALE` (255,236,179) ou `DIVINE_WHITE` (255,252,240)
— **des rubans quasi blancs sur un personnage R6 quasi blanc, dans une scène
claire**, avec `LightEmission = 0.7` qui les délavait encore.

**Deuxième itération appliquée :** la courbe part directement de la couleur
demandée et s'assombrit vers la queue, `LightEmission` **0,7 → 0,35**, et les
**9 traînées passent en `GOLD_BRIGHT`** (255,205,92) — les teintes pâles et
blanches sont abandonnées.

**Et après cette deuxième itération : ça ne lit toujours pas.** Le ruban existe
(compte d'instances 0 → 2, sur les bons membres), mais à cette distance de caméra
il reste écrasé par la gerbe d'impact qui, elle, occupe tout le cadre.

### Mon analyse, à trancher

Deux hypothèses, que je ne peux pas départager sans un choix de direction :

1. **La gerbe d'impact est trop dominante.** Elle sature la zone au moment précis
   où la traînée devrait se voir. La rendre plus discrète ferait apparaître l'arc
   — mais c'est l'effet que Milan a validé comme « embrasement ».
2. **La traînée n'est pas le bon device à cette distance de caméra.** Dans la
   référence, la caméra est proche et le geste occupe l'écran ; chez nous elle est
   reculée et le bras R6 balaie peu de pixels.

Je n'ai pas continué à tâtonner sur les valeurs : deux itérations mesurées
suffisent à dire que le levier n'est pas là.

### Non commencé

Les 13 `Get Hit` natifs R6, `AssetVerifier`, la proposition sur
`ImpactFrameController.Flash()`.

---

## 2026-08-31 — Traînées hors plafond + seuil Heavy 15→10, les deux vérifiés

### 1. Traînées exclues du décompte, plafond inchangé

Implémenté comme arbitré : les `SlashTrail` sortent du décompte **et** de la
troncature, sans toucher au plafond global — le relever aurait rouvert la porte à
la surcharge de particules qu'on venait de fermer sur l'ultime. Elles ne
consomment pas non plus le budget des autres effets, donc elles ne peuvent pas
faire écarter un impact au coup suivant.

**Vérifié en moteur :**

```
M1_1   trainees pic 1  [Right Arm]              <- 1 bras declare
M1_2   trainees pic 2  [Left Arm, Right Arm]    <- 2 bras declares  (etait 1 avant)
```

Les pièces « serrées » affichent bien leurs deux traînées.

### 2. À l'œil : elles ne se lisent pas comme du bruit — elles se lisent à peine

Réponse honnête à la question posée. Sur la capture, ce qui porte le coup c'est
l'**éclat doré d'impact** ; la traînée ne ressort pas comme un ruban distinct.
Deux traînées ne créent donc aucun encombrement — le problème est inverse.

Cause chiffrée, lue dans `CombatVFX.SlashTrail` :

| paramètre | valeur actuelle | conséquence |
|---|---|---|
| attaches | ±0,8 stud | ruban de **1,6 stud** de large |
| `Lifetime` | **0,14 s** | le ruban ne persiste que **140 ms** derrière le bras |

À la vitesse mesurée du poignet, 140 ms laisse un arc très court. La référence
d'animateur analysée montrait au contraire un **grand arc balayé** qui reste
visible pendant toute la course du membre.

**Proposition, non appliquée** — `SlashTrail` est partagé par tout le jeu, donc
même catégorie de décision que le plafond :
- `Lifetime` **0,14 → 0,30 s** (l'arc suit vraiment la course au lieu de la
  frôler) ;
- attaches **±0,8 → ±1,1 stud** (ruban de 2,2 stud, proportionné à un bras R6 de
  2 stud, sans devenir une nappe).

Capture avant/après à fournir si tu veux trancher dessus.

### 3. Seuil Heavy 15 → 10 : appliqué et vérifié

Test par **identifiant d'asset** et non par nom d'instance — le rig R6 par défaut
embarque un script `Animate` dont toutes les pistes s'appellent « Animation »,
ce qui rendait ma première sonde illisible :

```
  M1 #1/#2            6 degats -> HitReactLight_Front
  M1 #3               8 degats -> HitReactLight_Front
  M1 #4 finisher     12 degats -> HitReactHeavy        <- LE SEUL QUI BASCULE
  Main du Colosse    20 degats -> HitReactHeavy
  Marche du Titan    35 degats -> HitReactHeavy
  ULTIME             50 degats -> Knockback
```

**Seul M1 #4 change de réaction.** Rien d'autre ne bouge, comme annoncé.

---

### Signalement mineur

Le rig R6 par défaut affiche **son nom (« CombatDummy ») et une barre de vie**
au-dessus de lui, hérités du `Humanoid` standard. Pratique pour tester, mais
c'est de l'interface non voulue dans les captures. Trivial à masquer
(`DisplayDistanceType = None`) si ça gêne — dis-moi.

### Reste du tri, non commencé

Les 13 `Get Hit` natifs R6, puis `AssetVerifier`, puis la proposition chiffrée
sur `ImpactFrameController.Flash()`.

---

## 2026-08-31 — Étape 2 : les traînées sont réveillées (elles étaient inertes depuis toujours)

### « Ne pas recréer, améliorer » — cas d'école

`CombatVFX.SlashTrail` existait, était câblé dans `VFXLibrary`, et **n'avait
jamais rien rendu** : il exige un `part` (ou `ctx.attackPart`), et **aucune
recette ni aucun appelant n'en fournissait**. Zéro ligne de VFX à écrire — il
fallait juste alimenter un paramètre.

### Le membre frappeur est MESURÉ, pas deviné

Vitesse de pointe du poignet, par pièce :

```
M1_1  Right Arm  (1.358 contre 1.058, ratio 1.28)
M1_2  Left Arm   (1.574 contre 1.450, ratio 1.09)   <- serre
M1_3  Right Arm  (1.136 contre 0.868, ratio 1.31)
M1_4  Left Arm   (2.126 contre 1.863, ratio 1.14)   <- serre
S1    Left Arm   (3.332 contre 2.498, ratio 1.33)
S2    Right Arm  (1.236 contre 1.160, ratio 1.07)   <- serre
S3    Right Arm  (1.257 contre 1.256, ratio 1.00)   <- serre
S4    Right Arm  (1.342 contre 1.223, ratio 1.10)   <- serre
ULT   Left Arm   (5.024 contre 4.729, ratio 1.06)   <- serre
```

**6 pièces sur 10 ont les deux bras à vitesse quasi égale.** Y mettre une seule
traînée serait arbitraire : ces pièces en déclarent **deux**. Le champ
`attack_limbs` est porté par la recette et résolu côté client sur le modèle de
l'attaquant.

### Preuve en moteur

```
au repos : 0 Trail sur le personnage
BILAN : pic 1 Trail (base 0, donc +1) | portes par : Right Arm
```

De **zéro à une traînée vivante**, attachée au bon bras.

### Limite trouvée, non corrigée : le plafond d'atomes

Une seule traînée apparaît là où les pièces « serrées » en déclarent deux. Cause :
le plafond de lisibilité de `VFXLibrary` (light 2 / medium 4 / heavy 6) compte la
traînée comme un atome. Sur une recette `light` — les M1 — `Impact` + 2 traînées
font 3 atomes pour un plafond de 2, donc une est écartée.

Ce plafond avait été mis de côté au tour précédent (sujet des débris). Il bloque
maintenant une fonctionnalité validée. **Non touché** : c'est un arbitrage.

### Corrigé en passant

`scripts/visual_check/play_scene_server.luau` cherchait `TrainingDummy`, disparu.
Il accepte désormais les deux noms, pour rester utilisable sur une place non
encore mise à jour.

---

### CORRECTION d'un de mes propres signalements

J'avais écrit que la réaction `Knockback` ne se déclenchait jamais, « le coup le
plus fort faisant 22 dégâts ». **C'était faux** : je n'avais regardé que les M1 et
Skill1/2. Chiffres complets :

| pièce | dégâts | réaction déclenchée |
|---|---|---|
| M1 #1 / #2 | 6 | Light |
| M1 #3 | 8 | Light |
| M1 #4 (finisher) | 12 | **Light** |
| Main du Colosse | 20 | Heavy |
| Frappe Céleste | 22 | Heavy |
| Marche du Titan | 35 | Heavy |
| **Ultime** | **50** | **Knockback ✓** |

Seuils actuels : Knockback ≥ 40, Heavy ≥ 15, Light sinon. **Le seuil de 40 est
donc atteignable — par l'ultime, et par lui seul.** C'est défendable comme
design : la projection est réservée au coup ultime.

**Le vrai défaut est ailleurs** : M1 #4, le **finisher** de la chaîne, ne fait que
12 dégâts et déclenche donc la même réaction légère qu'un jab à 6. Pour une
identité « coups lourds », le quatrième coup mérite une réaction distincte.

**Recommandation :** abaisser le seuil Heavy de **15 à 10**, ce qui fait passer
M1 #4 en Heavy sans toucher au reste. Un seul nombre, effet net sur la lecture de
la chaîne. Décision à Milan.

---

## 2026-08-31 — Rig de test : cible R6 immortelle qui se réancre seule (étape 1/4)

### Audit AVANT retrait, comme demandé

Deux créateurs seulement (`TrainingDummies.server.lua` et `DummyService.server.lua`),
et **une seule référence externe** : `scripts/visual_check/play_scene_server.luau`,
un script de capture qui cherche par nom. **Aucun système de jeu n'en dépendait.**
Les deux anciens sont **désactivés, pas supprimés** — corps conservé entre
`--[==[ ]==]`, réversion triviale.

### Le point qui a changé la conception

L'ancien mannequin était **R15** (`CreateHumanoidModelFromDescription` sans rig
type). Or le projet est **R6 uniquement** et le kit du joueur l'est : un rig R15
ne peut pas porter correctement des animations R6. Le nouveau est explicitement
`Enum.HumanoidRigType.R6`.

### Les trois propriétés, mesurées par le vrai chemin

**1. Les réactions jouent réellement.** Observées via `AnimationPlayed` sur
l'Animator — pas un `LoadAnimation` qui réussit :

```
REACTION jouee : HitReactLight_Front    len=0.383
REACTION jouee : HitReactHeavy          len=0.517
  ... 12 declenchements sur la sequence
BILAN : 2 type(s) de reaction joue(s)
```

**2. Les dégâts restent lisibles.** PV min **468** — le signal « 500 → 468 » qui
sert de preuve qu'un coup touche est préservé — puis **remontés à 500**
automatiquement après 2 s. Un `MaxHealth = math.huge` aurait supprimé ce signal ;
c'est pour ça que l'immortalité est faite par **soin différé** et non par
invulnérabilité.

**3. Le réancrage — et la nuance honnête.** Pendant la séquence de combat, la
dérive maximale a été de **0,03 stud** : rien n'a jamais déplacé la cible, donc le
réancrage **ne s'était pas déclenché** et n'était pas prouvé. Testé directement :

```
projection horizontale       ecart 25.0 stud -> revenu en 0.05 s
projection en l'air (ultime) ecart 24.2 stud -> revenu en 0.12 s
knockback violent            ecart 17.7 stud -> revenu en 0.75 s
position finale : 0, 3.00, 44.99
```

Le cas « knockback violent » met 0,75 s **par conception** : on attend que la
vitesse retombe sous 6 stud/s avant de ramener, sinon on annulerait le mouvement
qu'on cherche justement à regarder.

### Ce que ça débloque

Les captures de cette session ont buté quatre fois sur la cible : mannequin à
43 studs pour une portée de 8, dérive du knockback précédent, PV à réinitialiser,
replacement scripté avant chaque enregistrement. **Toutes les captures futures
deviennent comparables entre elles.**

---

### Signalements hors périmètre (à trier)

Conformément au nouveau cadrage — rapporter large, même hors sujet :

1. **`Knockback` ne se déclenche jamais.** Le seuil est de 40 dégâts sur un seul
   coup, et aucun coup du kit ne l'atteint (M1 ~8, Skill1 20, Skill2 22). Une des
   trois animations de réaction est donc morte. Seuil à revoir, ou à réserver à
   l'ultime.
2. **Les trois réactions sont des conversions R15.** Leurs commentaires dans
   `AnimationDB/Reactions.lua` disent « 6to15 : Hit 1 … R6 → R15 ». Elles jouent
   correctement sur le rig R6 (longueurs conformes), mais leur **fidélité visuelle
   sur R6 n'est pas vérifiée**. Le pack Close Combat contient 13 `Get Hit`
   natifs R6 non uploadés — candidats évidents.
3. **`scripts/visual_check/play_scene_server.luau` est cassé** : il cherche encore
   `TrainingDummy` par nom, qui n'existe plus.
4. **`ImpactFrameController.Flash()` ne prend aucun argument** et désature tout
   l'écran de −0,6, de façon fixe, pour toutes les compétences. C'est ce qui fait
   perdre son identité violette à l'arène à chaque impact. Effet partagé, non
   touché.
5. **`AssetVerifier` rapporte `VERIFIED=0 UNVERIFIED=45`** à chaque Play, alors
   que les assets sont bel et bien valides. Sa vérification ne fonctionne pas en
   session — bruit permanent dans la console qui masquerait un vrai problème.
6. **Rojo n'a pas synchronisé de la session.** Tous les fichiers sont poussés à la
   main via un serveur local, puis vérifiés. Ça marche, mais c'est le principal
   risque de mesurer du code périmé.

---

## 2026-08-31 — Analyse des deux vidéos de référence (regardées, pas déduites)

Frames extraites avec `ffmpeg` et **ouvertes une par une**, y compris un zoom
pleine résolution sur la timeline de l'éditeur d'animation. Aucune conclusion
tirée des métadonnées seules.

### Ce que sont réellement ces deux vidéos — à dire d'emblée

**Ni l'une ni l'autre n'est une capture de jeu.** Ce sont deux **enregistrements
d'écran de réseau social** montrant des démos d'animateurs Roblox.

**Réf 1** (16,9 s · 888×1920 · 60 fps, portrait téléphone) : un fil social qui
défile. Segment 1 titré **« Linear Easing Test »**, rig R6 dans un vide blanc,
avec une traînée blanche rectiligne. Segment 2, clip de `EclipseTheGenima…`, avec
les légendes successives **« No camera movement »** puis **« No effects +
Slowdown »** — l'auteur montre son animation **brute, sans effets, ralentie**.

**Réf 2** (45,4 s · 888×904 · 60 fps) : clip signé **« HOVA »** (9 565 likes),
montrant l'éditeur d'animation avec une timeline de 0 à 1100+ frames. Il alterne
des segments à **deux personnages sur une plateforme surélevée** et des segments
à un seul rig dans le vide. Les rigs sont les mannequins d'animation standard
(blocs colorés étiquetés FRONT / BACK / L / B).

Le contenu correspond bien à ce que Milan décrit (un enchaînement, une plateforme
utilisée), mais **la nature du matériau change ce qui est transposable** : on
compare notre jeu à du travail d'animateur présenté en vitrine, pas à un jeu
concurrent en situation.

### Ce qui est mesurable dans ces références

**1. Le rig est R6.** Timeline lisible au zoom : pistes `Rig / Torso / Right Arm /
Head / Left Arm / CFrame`. **Notre rig n'est donc pas la limite.**

**2. La densité de keyframes est MODÉRÉE, pas dense.** Règle de frames lisible de
15 à 120+, avec des keyframes **discrètes et espacées** — de l'ordre de 2 à 3
colonnes par intervalle de 15 frames, soit **une clé toutes les 5 à 7 frames**.

C'est l'inverse de ce que je supposais. Nos animations issues des packs sont
**bakées à ~60 kf/s**. La qualité de la référence ne vient donc **pas** de la
densité : elle vient du **choix des poses**.

**3. Le VFX principal est une TRAÎNÉE de mouvement, pas une gerbe de particules.**
Sur la frame d'impact la plus nette, un **arc blanc unique** suit la course du
membre. Et l'auteur revendique **« No effects »** : la lisibilité vient de
l'animation, la traînée n'est qu'un soulignement.

**4. Le « décor » de la réf 2 est une simple plateforme.** Pas de destruction, pas
de scénographie : de la géométrie de niveau basique sur laquelle deux personnages
s'appuient.

### L'écart avec notre kit, chiffré

| critère | référence | notre kit | écart |
|---|---|---|---|
| rig | R6 | R6 | aucun |
| densité de keyframes | ~1 clé / 5-7 frames | **~60 kf/s (bakées)** | on est *plus* dense, sans bénéfice |
| VFX porteur | **traînée sur le membre** | gerbe de particules à l'impact (22-55 émetteurs) | **device absent chez nous** |
| anticipation M1 | — | 0,298 s (réf jeu mesurée avant : 0,067 s) | 4,4× trop long |
| position de l'impact | — | 46 % du clip (réf jeu : 23 %) | 2× trop tard |
| traînées de membre | présentes | **ZÉRO** | total |

**Le constat le plus actionnable :** nous avons déjà l'atome `SlashTrail`
(`CombatVFX.SlashTrail`, câblé dans `VFXLibrary`), mais il exige un `part` ou un
`ctx.attackPart` — et **`attackPart` n'est fourni nulle part dans le dépôt**.
J'avais retiré les `SlashTrail` des recettes Demi-Dieu précisément parce qu'ils ne
rendaient rien. Le device central de la référence est donc **déjà implémenté chez
nous et inerte faute d'un seul paramètre.**

### Ce qui est atteignable, et ce qui ne l'est pas

**Atteignable, à coût faible :**
- **Traînées sur le membre frappeur.** Le code existe ; il manque de passer la
  partie du bras dans `ctx.attackPart`. C'est le plus gros gain visuel par rapport
  à la référence, pour le plus petit changement.
- **Réduire l'anticipation des M1** en recoupant les sources (`span`), pour passer
  de 46 % à ~25 % sur la position de l'impact.

**Atteignable, à coût moyen :**
- Retravailler les poses plutôt que la densité. Nos clips viennent de packs
  professionnels, donc la qualité de pose est déjà là ; le levier est le
  **recoupage** et le **retiming**, pas l'ajout de keyframes.

**NON atteignable dans l'état, et je le dis franchement :**
- **L'interaction avec le décor de la réf 2.** Notre arène est statique et
  l'ultime ne l'utilise pas. Même la version minimale de la référence — deux
  personnages qui prennent appui sur une plateforme — suppose un système
  d'ancrage au décor qui n'existe pas. Ce n'est pas un réglage, c'est un chantier.
- **La comparaison de « fluidité » elle-même est biaisée** : la référence est un
  rendu d'éditeur ralenti, sans contraintes de latence réseau, sans prédiction
  client, sans interruption par l'entrée du joueur. Notre chaîne M1 est jugée en
  conditions de jeu. Une partie de l'écart perçu n'est pas rattrapable parce
  qu'elle ne porte pas sur la même chose.

### Ce que je propose (rien codé ce tour)

1. **Câbler `ctx.attackPart`** pour rendre les traînées vivantes, puis les remettre
   sur les M1 et compétences. Petit changement, device central de la référence.
2. **Recouper les sources M1** pour ramener l'impact de 46 % à ~25 % du clip.
3. **Ne pas augmenter la densité de keyframes** — la référence prouve que ce n'est
   pas de là que vient la qualité.
4. **Traiter le décor comme un chantier séparé**, pas comme un réglage de l'ultime.

### Note d'outillage

Codex n'a pas été employé : ce tour demandait explicitement de **regarder** les
frames, ce qui ne se délègue pas. Il sera utile sur le répétitif — par exemple
appliquer un même recoupage à plusieurs seeds.

---

## 2026-08-31 — Étape 5 : l'Ultime noyait bien le geste, allégé — et un bug d'étiquettes trouvé

État de reprise vérifié d'abord : plugin MCP revenu, Play arrêté, **`DESYNC = 0`**
sur les 5 points du chantier, aucune sonde résiduelle côté Edit.

### Ce que la charge VFX fait dans le temps

Sonde allégée (la précédente parcourait `workspace:GetDescendants()` à chaque
échantillon et n'avait rendu qu'un point à t=0 ; celle-ci écoute
`DescendantAdded`, donc ne compte que ce qui apparaît) :

```
ULTIME anim 4.50 s — 64 emetteurs APPARUS pendant le geste
  t=1.5-2.0 s   64 ##################################################
  (toutes les autres tranches : 0)
```

**Les 64 émetteurs tombent dans une seule fenêtre de 0,5 s.** Ce n'est pas une
surcharge continue : c'est une décharge concentrée à l'impact, et les trois temps
du geste (élévation, chute, relevé) n'ont rien d'autre que l'aura.

### Verdict : oui, ça noyait le geste

Frame d'impact mesurée : **luminance 203/255, 22,3 % de pixels saturés**. À
l'écran, l'arène perdait son identité violette, tout virait au blanc, et **le
personnage n'était plus distinguable**.

### Allégé, pas augmenté

`Impact Burst` et `GroundSmash` faisaient doublon au même instant → un seul gardé.
Magnitudes 1.6-1.8 → 1.1-1.3. Atome `Impact` blanc 6.0 → 3.2 et passé en doré.
Flash 0.65 → 0.32. Shake 2.20 → 1.60. **Poussière et fracture conservées et même
allongées** (1800→2200 ms, 2400→2800 ms) : ce sont elles qui portent le geste dans
la durée, là où le blanc ne faisait que masquer.

| | avant | après |
|---|---|---|
| pixels saturés au pic | **22,3 %** | **11,9 %** |
| couches d'émetteurs | 4 | 3 |
| atomes procéduraux | 4 | 3 |

À l'œil : le personnage est de nouveau **lisible**, silhouette distincte,
géométrie de l'arène lisible.

### Bug trouvé en chemin : des étiquettes de vitrine affichées en jeu

La capture montrait le texte **« ight Wave Impact »** à l'écran. Vérifié : **5 des
11 émetteurs** que nos recettes clonent embarquent un `BillboardGui` affichant
leur propre nom — `Impact Burst`, `Light Wave Impact`, `Wind Flare`,
`Shockwave Impact V`, `Ground Skill II`. Ce sont les étiquettes de la place de
démonstration du pack.

Elles touchaient M1 #1, #2, #3, Skill1, Skill3, Skill4 et l'Ultime.

Corrigé **à la source du clonage** (`CombatFXBroadcaster.SpawnVFXLayer`) plutôt
que recette par recette : le correctif couvre aussi les émetteurs qu'on ajoutera
plus tard. Preuve inverse, sur une session avec 2 M1 + l'ultime :

```
BILAN : 0 GUI apparus dans le workspace | textes : AUCUN
```

### Reste ouvert

Le voile global qui subsiste à l'impact ne vient pas de la recette mais de
`ImpactFrameController.Flash()`, qui applique une désaturation fixe de **−0.6** à
tout l'écran, sans paramètre. C'est un effet **partagé par tout le kit** : je ne
l'ai pas touché, ce serait un changement de game-feel sur toutes les compétences,
pas un réglage de l'ultime.

### Note d'outillage

Codex et la parallélisation n'ont pas été employés ici : ce tour était de
l'investigation et de la vérification moteur, exactement ce qui ne se délègue pas.
Ils seront utiles sur le travail répétitif — appliquer un même geste à plusieurs
pièces, par exemple.

---

## 2026-08-30 — PAUSE (4) — note de reprise

### Ce qui est fait

**Étapes 1 à 4, plus l'étape 6 en partie** — détail complet dans l'entrée
ci-dessous.

1. **Inventaire du réel** : les 10 sources de VFX du kit, avec couleur, émetteur
   et déclencheur pour chacune.
2. **Ce que les packs contiennent déjà**, énuméré et non deviné : pression/air
   (`Wind`, `Wind Flare`…), onde/anneau (`Light Wave Impact`, `Shockwave
   Impact V`…), poussière/sol (`Dust`, `CraterDust`, `Cracks`…). Les 12 noms
   retenus ont été vérifiés un par un en moteur avant écriture.
3. **Bug rouge corrigé.** Ce n'étaient pas « certains hits » : **les quatre M1**
   tiraient les anciennes recettes cramoisies avec des émetteurs de sang, via
   `CombatService.MOVE_FX`. Preuve inverse mesurée sur une chaîne M1 complète au
   contact : `ROUGES=0 | dore/blanc=14 | autres=0`.
4. **Différenciation.** `Skill1` et `Skill3` n'étaient pas « similaires » mais
   **identiques** (mêmes émetteurs, mêmes teintes). Chaque pièce a maintenant sa
   signature dans la même palette.
6. **Couche secondaire ajoutée EN PLUS** du doré : `Wind` sur Main du Colosse,
   `Light Wave Impact` sur Jugement, `CraterDust` sur Marche du Titan et M1 #4.

Dernier commit : `5d7c83d`. Arbre propre.

### Ce qui reste — étape 5, NON FAITE

**Capture dédiée de l'Ultime** pour juger si son VFX noie le geste réparé
(animation 100 %, aura 4,545 s).

Ce qui a été établi avant l'interruption :
- synchro vérifiée, `DESYNC = 0` ;
- composition mesurée : **4 couches d'émetteurs + 4 atomes procéduraux = 8
  sources**, avec un `screen_flash` à 0,65 de pic et un shake à 2,20 — de loin la
  pièce la plus chargée du kit. C'est un candidat sérieux à l'allègement, mais
  **ce n'est pas une conclusion** : elle demande de voir le rendu.

Ce qui a échoué et qu'il faudra refaire :
- **la sonde de charge visuelle n'a rendu qu'un échantillon à t=0** (`pic 0
  emetteurs a t=0.00`), donc **aucune mesure valable** ;
- **l'enregistrement écran n'a laissé aucun fichier** (`ult5.mov` absent) — la
  tâche a été interrompue sans marqueur de fin.

Aucun jugement n'a donc été porté sur l'Ultime. À reprendre de zéro.

### Points ouverts

1. **Rojo ne synchronise plus depuis le redémarrage de Studio.** Le listener
   écoute bien sur `127.0.0.1:34872`, mais le plugin ne s'est jamais reconnecté :
   **tous** les fichiers de ce chantier ont dû être poussés à la main, via la
   source exacte servie en local, puis vérifiés avant chaque mesure. Ça marche,
   mais reconnecter le plugin supprimerait ce détour et le risque d'oubli.
2. **Le plugin MCP de Studio s'est déconnecté** en fin de session : Studio tourne
   toujours au niveau système, mais plus aucune instance n'est listée. **Play n'a
   donc pas pu être arrêté et les sondes n'ont pas pu être balayées par script.**
   Sans conséquence sur le dépôt : toutes les sondes ont été insérées **à
   l'exécution en mode Play** (`PlayerGui` et `ServerScriptService` de la session
   courante), donc elles disparaissent d'elles-mêmes à l'arrêt de Play — elles
   n'ont jamais fait partie de la place enregistrée. Les seules écritures
   persistantes faites dans la place sont les `Source` de fichiers poussées pour
   contourner rojo, et elles sont identiques au disque.
3. `recovery` de Frappe Céleste (0,55 s, geste vu à 84 %) — arbitrage toujours en
   attente.
4. `test_moving_contact::TestTracking` — 2 rouges antérieurs au 25/08,
   couverture 53,8 %.

---

## 2026-08-30 — Analyse VFX complète, bug rouge corrigé, M1 différenciés (étapes 1-4)

### 1. Inventaire du réel — ce qui tire sur chaque pièce

| pièce | recette | déclencheur | émetteurs | couleur |
|---|---|---|---|---|
| M1 #1 | `M1_1` **(ancienne)** | hit M1, via `CombatService.MOVE_FX` | `Blood Hit Impact` | **rgb(255,80,80)** |
| M1 #2 | `M1_2` **(ancienne)** | hit M1 | `Blood Splatter I` | **rgb(255,60,60)** |
| M1 #3 | `M1_3` **(ancienne)** | hit M1 | `Stike Impact` | **rgb(255,70,70)** + CRIMSON_BRIGHT |
| M1 #4 | `M1_4` **(ancienne)** | hit M1 | `Heavy Slashes I` | **rgb(220,40,40)** + CRIMSON_DEEP |
| Main du Colosse | `DemiDieu_Skill1_Impact` | hit (module) | Impact Burst + Dust + Big-Crack-01 | doré |
| Frappe Céleste | `DemiDieu_Skill2_Impact` | hit (module) | GroundSmash + Dust + Big-Crack-01 | blanc/doré |
| Marche du Titan | `DemiDieu_Skill3_Impact` | hit (module) | **identique à Skill1** | doré |
| Jugement | `DemiDieu_Skill4_Counter` | contre (module) | Impact Burst + Dust | blanc |
| Ultime | `DemiDieu_Ultimate_Impact` | impact (module) | Impact Burst + GroundSmash + Dust + Big-Crack-01 | blanc/doré |
| les 5 compétences | `DemiDieu_Cast_Aura` | **départ du geste** (client) | atomes seuls | doré |

### 2. Ce que les packs contiennent déjà — énuméré, pas inventé

| besoin | effets unitaires disponibles |
|---|---|
| pression / air | `Wind` (6 ém.), `WindV2` (6), `Wind-01` (6), `Wind Flare` (5) |
| onde / anneau | `Magic Circle` (7), `Light Wave Impact` (6), `Hit Impact ShockWaves III` (5), `Shockwave Impact V` (4), `Impact Wave` (1) |
| poussière / sol | `Ground Skill` (6), `Dust` (4), `Big-Crack-01` (4), `Dirt Specs` (2), `Smoke` (2), `CraterDust` (1), `Cracks` (1) |

**Aucune recette n'a eu à être inventée** : les 12 noms retenus ont été vérifiés un
par un en moteur avant écriture.

### 3. Bug rouge — source exacte trouvée et corrigée

`CombatService.MOVE_FX` routait `M1_1`..`M1_4` vers les **anciennes recettes
cramoisies**, avec des émetteurs de sang. Ce n'était pas « certains hits » : **les
quatre** étaient rouges, du rgb(220,40,40) au rgb(255,80,80).

Quatre recettes dorées créées et le routage recâblé.

**Preuve inverse, mesurée en moteur** — couleur réelle de chaque émetteur apparu
pendant une chaîne M1 complète au contact (mannequin 500 → 468 PV, donc les 4
coups touchent) :

```
BILAN sur 14 emetteurs apparus : ROUGES=0 | dore/blanc=14 | autres=0
```

### 4. Différenciation — le hit n'était pas « similaire », il était identique

`DemiDieu_Skill1_Impact` et `DemiDieu_Skill3_Impact` avaient **exactement** les
mêmes 3 émetteurs et les mêmes 3 teintes ; seules les magnitudes de caméra
différaient. Marche du Titan reçoit désormais sa propre signature — onde de choc
et effet de sol, là où Main du Colosse est un éclat frontal. Même palette.

Chaque M1 a aussi sa signature, plutôt qu'une recette recyclée :

```
M1_1 direct    [Impact Burst]
M1_2 crochet   [Light Wave Impact]              onde laterale, pas un point
M1_3 uppercut  [Wind + Wind Flare]              air qui monte
M1_4 finisher  [GroundSmash + CraterDust + Crack-01]   cratere
Skill1         [Impact Burst + Dust + Big-Crack-01 + Wind]
Skill3         [Shockwave Impact V + Ground Skill + CraterDust]
Skill4         [Impact Burst + Dust + Light Wave Impact]
```

### 6 (partiel). Couche secondaire ajoutée EN PLUS du doré

`Wind` sur Main du Colosse (pression d'air d'une frappe ample), `Light Wave
Impact` sur Jugement (onde de déflexion d'un contre), `CraterDust` sur Marche du
Titan et M1 #4. Le style feu/embrasement est conservé, rien n'a été remplacé.

### Reste à faire

**Étape 5** : capture dédiée de l'Ultime pour juger si son VFX noie le geste
réparé — et l'alléger si oui, plutôt que d'ajouter dessus. Non commencée.

---

## 2026-08-30 — Aura étendue à Jugement et à l'Ultime : 100 % sur les cinq

**Décision de style actée :** on garde le **feu / embrasement**. Poussière et
fracture au sol séparées abandonnées. Les débris `GroundChunks` et le plafond de
lisibilité ne sont plus un manque à combler — sujet clos.

### Constat qui simplifie le travail

`InputController` route **R vers `TrySkill(5)`** quand `IsUltimateReady()` : les
deux pièces gelées passaient donc **déjà** par `TrySkill`, où l'aura client avait
été posée au tour précédent. Il n'y avait rien à ajouter — seulement le doublon
serveur à retirer. Vérifié : **plus aucun module serveur ne déclenche l'aura.**

### Preuve chiffrée en moteur

```
Skill4_Jugement              anim 0.57 s | apparait 0.000 s | disparait 0.602 s | COUVERTURE 100%
Ultimate_DescenteDuDemiDieu  anim 4.50 s | apparait 0.000 s | disparait 4.545 s | COUVERTURE 100%
```

**Le point sensible de l'ultime est réglé :** l'aura dure **4,545 s** pour une
animation de 4,50 s. Si la durée était restée sur une constante (0,75 s), la
couverture serait tombée à ~17 %. Elle suit donc bien `track.Length`.

Les cinq pièces sont maintenant à 100 % : Skill1 (0,70 s), Skill2 (0,83 s),
Skill3 (0,97 s), Jugement (0,57 s), Ultime (4,50 s).

### Cast rejeté — la garde tient

Point soulevé après mon erreur du tour précédent (insertion passée avant la
vérification du momentum). Le déclenchement serveur ayant été retiré, il ne peut
plus partir sur un rejet serveur. Côté client, l'aura suit l'animation : `R` avec
momentum à 0 a produit **Jugement**, pas l'ultime — le routage
`IsUltimateReady()` empêche l'aura d'ultime sur un cast non prêt. Observé dans la
même session : une ligne Jugement avant la charge de momentum, une ligne Ultime
après.

Réserve honnête : si un cast passait la garde client et était rejeté **côté
serveur**, l'aura jouerait quand même — mais l'animation aussi. C'est le
comportement de la prédiction client, antérieur à ce travail, pas une régression.

### Deuxième limite trouvée dans mon outil vidéo

`inspect_video.py` déclare une « queue morte » sur le clip de l'ultime. Vérifié :
c'est un artefact du **seuil relatif**. Un clip qui démarre très lumineux (l'aura)
fait monter le pic et relève donc la barre pour la queue — même geste, queue à 5
pour un pic de 60 avec l'aura, contre 9 pour un pic de 46 sans. **La fin n'est pas
plus morte, le début est plus vif.** La mesure moteur tranche dans l'autre sens
(TimePosition 4,545 / 4,50, couverture 100 %). Limite documentée dans l'outil, qui
reste un contrôle secondaire.

Piège de synchro attrapé encore une fois : rojo ne synchronise toujours pas depuis
le redémarrage de Studio ; les 3 fichiers ont été poussés depuis la source exacte
et vérifiés avant mesure.

---

## 2026-08-30 — Aura de cast : couverture 33-41 % → 100 %, et j'avais mal diagnostiqué

**Correction préalable de mon propre rapport.** Milan a regardé les deux vidéos :
les impacts sont de vrais embrasements de particules, pas des flashs. J'avais
sous-vendu le résultat en le qualifiant de « partiel » sur la seule base que la
poussière n'était pas lisible au cadrage que j'avais choisi.

### Le diagnostic que j'avais annoncé était faux

J'avais écrit que l'aura ne couvrait que 33-41 % du geste parce que son
`lifetime` (0,75 s) était trop court, et que le fondu d'entrée la faisait démarrer
en retard. **Les deux étaient faux.** Chronométrage :

```
Skill1  anim 0.70 s | aura apparait a 0.509 s | disparait a 1.297 s | duree 0.788 s
Skill2  anim 0.83 s | aura apparait a 0.490 s | disparait a 1.295 s | duree 0.805 s
Skill3  anim 0.97 s | aura apparait a 0.556 s | disparait a 1.358 s | duree 0.802 s
```

La durée était **conforme** (0,79-0,81 s). Le problème était le **départ, 0,50 s
trop tard** — et pas à cause du fondu : le client n'envoie la requête serveur
qu'au **marqueur d'impact** (`fallbackImpactTime` ≈ 0,44 s). Le module de
compétence, et l'aura avec lui, ne s'exécutait donc qu'**à l'impact**.

**Rallonger le `lifetime`, comme je l'avais proposé, aurait allongé la queue sans
combler le début nu.** C'est la mesure qui a évité la fausse correction.

### La correction réelle

L'aura est désormais déclenchée **côté client, dans `CombatController.TrySkill`,
à l'instant exact où l'animation part** — plus de round-trip serveur. Sa durée est
calée sur `track.Length`, donc sur la longueur **réelle de chaque animation**,
pas sur une valeur unique.

Le déclenchement serveur, devenu redondant et mal placé, a été retiré des trois
compétences testées.

### Preuve chiffrée

```
Skill1  anim 0.70 s | apparait 0.000 s | disparait 0.748 s | COUVERTURE 100%
Skill2  anim 0.83 s | apparait 0.000 s | disparait 0.872 s | COUVERTURE 100%
Skill3  anim 0.97 s | apparait 0.000 s | disparait 0.990 s | COUVERTURE 100%
```

Constat de départ : **33-41 %**. L'aura s'éteint juste après la fin de chaque
geste, sans traîner.

Piège de synchro attrapé une fois de plus : rojo ne synchronise toujours pas
depuis le redémarrage de Studio. Les 4 fichiers ont été poussés depuis la source
exacte et vérifiés avant toute mesure.

### Gelé en attente de l'arbitrage de Milan

Le style actuel est du **feu / embrasement**, pas de la **poussière / fracture au
sol**. Tant que Milan n'a pas dit si ce style lui convient :

- **`Skill4_Jugement` et `Ultimate_DescenteDuDemiDieu` ne sont pas touchés** : ils
  gardent leur aura serveur, tardive, plutôt que de propager un choix qui pourrait
  changer.
- **Le plafond de lisibilité et les débris `GroundChunks` ne sont pas touchés**
  non plus (`debris 0` reste ouvert).

---

## 2026-08-30 — Le quatrième câblage réparé : les VFX apparaissent enfin, mais deux manques restent

### Piège de synchro attrapé d'abord

Après le redémarrage de Studio, **rojo n'avait rien synchronisé** : les 7 fichiers
du chantier VFX étaient périmés dans la place, y compris ceux du tour précédent.
Poussés via la source exacte servie en local (`MANQUANTS = 0` après contrôle).
Sans ce contrôle, j'aurais mesuré l'ancien code et conclu à tort.

### 1. `VFXLibrary` câblé dans `CombatFXReceiver.dispatch`

`dispatch` traitait hitstop, `camera_kit`, `flash`, posture, FOV, dilatation et
audio — jamais `procedural_atoms`. Les atomes sont désormais joués, **pour tous
les clients** et pas seulement l'attaquant local : une aura portée par le
personnage doit se voir par l'adversaire, sinon elle ne sert à rien en PvP.

### 2. Soupçon `screen_flash` vs `flash` — CONFIRMÉ

`dispatch` ne lisait que `payload.flash`, alors que **toutes** les recettes
écrivent `screen_flash`, et `merge` ne fait aucune correspondance entre les deux.
Le flash d'impact des recettes n'était donc jamais déclenché. Corrigé.

Au passage : `ImpactFrameController.Flash()` ne prend **aucun argument**, alors
que le receiver lui en passait deux — ignorés en silence.

### 3. La preuve inverse, chiffrée

Le premier essai n'a rien prouvé : le mannequin était à **43 studs** pour une
portée de 8, donc aucun coup ne touchait et les couches d'impact ne partaient
pas. Personnage replacé au contact (mise en place scriptée ; le chemin de combat
reste entièrement réel). Preuve que ça touche : **mannequin 500 → 458 PV**.

| | aura sur le perso | émetteurs à l'impact |
|---|---|---|
| Main du Colosse | +1, sur **41 %** du geste | **+32** |
| Frappe Céleste | +1, sur 35 % | **+55** |
| Marche du Titan | +1, sur 34 % | **+22** |

Constat de départ : **+0 partout**.

### 4. Face à l'ambition demandée — franchement

| attendu | état | preuve |
|---|---|---|
| **Vraie frame d'impact visible** | ✅ **atteint** | la scène entière vire à l'or sur la frame d'impact, avec un éclat au torse |
| **Poussière et fractures au sol** | ⚠️ **partiel** | 22 à 55 émetteurs apparaissent réellement, mais ils **ne se voient pas** au cadrage capturé |
| **Aura pendant TOUT le geste** | ❌ **non atteint** | +1 émetteur seulement, présent sur **33-41 %** du geste |

Deux manques identifiés, non corrigés :
- **`GroundChunks` ne produit aucun débris** (`debris 0` mesuré) alors qu'il
  reçoit maintenant `count` 14 à 34. Piste : le plafond de lisibilité de
  `VFXLibrary` (light 2 / medium 4 / heavy 6 / ultimate 8) compte les couches ET
  les atomes, et pourrait écarter les atomes en surnombre.
- **L'aura ne couvre que ~40 % du geste.** Son `lifetime` est fixé à 0,75 s alors
  que les gestes durent 0,70 à 0,97 s, et elle démarre après le fondu d'entrée.

### État honnête

Le chemin est réparé et le prouve chiffré : on passe de « rien du tout » à des
dizaines d'émetteurs et une vraie frame d'impact dorée. Mais **l'habillage n'est
pas encore au niveau demandé** : la poussière au sol n'est pas lisible à l'écran
et l'aura n'accompagne pas le geste de bout en bout. Je le dis plutôt que de
présenter les +32/+55 comme une réussite complète.

---

## 2026-08-30 — VFX : l'écart mesuré, le blocage des packs levé, et un QUATRIÈME câblage mort

Synchro vérifiée d'abord (Studio avait redémarré, nouvel identifiant d'instance) :
`DESYNC total = 0` sur `recovery` ultime, `recovery` Skill1, recettes VFX,
normalisation du shake et gel du hitstop.

### 1. Ce que les recettes produisaient RÉELLEMENT — l'écart, chiffré

| compétence | atomes | ce qui apparaissait |
|---|---|---|
| Skill1 | Impact(3.0), SlashTrail, GroundChunks(size 2.0) | 2 Parts + 1 PointLight ; **SlashTrail ne rendait RIEN** (exige un `part`, aucune recette n'en fournissait) ; 8 débris (le `size` passé était **ignoré** — GroundChunks lit `count`/`radius`) |
| Skill2 | Impact(3.6), GroundChunks | idem, **aucune aura** |
| Skill3 | Impact(4.0), GroundChunks, Afterimage | **aucune aura** |
| Skill4 | Impact(3.2), SetAura(1, 0.6 s), SlashTrail | aura à **Rate 20** — le minimum du clamp [20,200] — et déclenchée **à l'impact** |
| ULT | Impact(6.0), GroundChunks, SetAura(1, 1.6 s), SpeedLines | idem |

**Écart face à l'ambition demandée :**
- **Poussière : 0 émetteur.** `GroundChunks` lance des cubes solides, ce n'est pas
  de la poussière.
- **Fractures au sol : 0.** Rien ne marque le sol.
- **Aura pendant tout le geste : absente sur 3/5**, et sur les 2 autres elle
  démarre **à l'impact**, à la cadence minimale.
- **Frame d'impact :** un flash de 2 Parts + un PointLight. Aucun émetteur,
  aucune onde.
- **Et le VFX ne partait que dans `if hitTarget and hitPosition`** — donc
  uniquement à l'impact ET uniquement si le coup **touche**. Un cast dans le vide
  n'affichait strictement rien.

### 2. Blocage des packs : levé, et pour une raison que je n'avais pas vue

J'avais écarté les émetteurs de pack faute de pouvoir vérifier leurs noms.
Énumération dans la place : **16 621 émetteurs**, dont **15 749 sous
`ServerStorage`** — exactement les deux racines que `findVFXByName` explore
(`_SAFE_PACKS` puis `_WORKSPACE_ARCHIVE_2026-05-11`). **`ReplicatedStorage` en
contient 0.**

Ce n'était donc pas qu'un problème de noms : les émetteurs sont **invisibles au
client**. Mais `vfx_layers` est résolu **côté serveur** et les clones se
répliquent — c'est précisément pour ça que ce chemin existe. Et `SpawnVFXLayer`
**avertit** quand un nom est introuvable : l'échec n'est pas silencieux.

Noms retenus, **énumérés et non devinés**, en ne prenant que des effets unitaires
(1 à 8 émetteurs — les conteneurs de premier niveau en portent jusqu'à 2 751) :

| besoin | émetteur | vérifié en moteur |
|---|---|---|
| impact | `"Impact Burst"` | archive, 8 émetteurs |
| poussière | `"Dust"` | _SAFE_PACKS, 4 émetteurs |
| fracture au sol | `"Big-Crack-01"` | archive, 4 émetteurs |
| onde au sol | `"GroundSmash"` | _SAFE_PACKS, 12 émetteurs |

### 3. Ce qui a été construit

- **`vfx_layers` ajoutés aux 5 recettes** avec ces noms vérifiés.
- **Deux bugs de paramètres corrigés** : `GroundChunks` reçoit enfin `count` et
  `radius` (14 à 34 selon la compétence, au lieu du défaut 8) ; les `SlashTrail`
  sans `part` ont été retirés plutôt que laissés inertes.
- **Aura de cast** : nouvelle recette `DemiDieu_Cast_Aura` (intensity 3.5 → Rate
  140 au lieu de 20) et **déclenchement au début du geste** ajouté dans les 5
  modules, après les gardes de rejet.

Tests : **7/7**.

### 4. QUATRIÈME câblage mort — trouvé, PAS corrigé

Vérification en moteur de l'aura de cast : **delta +0 émetteur sur le personnage**.
Elle ne part pas. Cause remontée :

`CombatFXBroadcaster.Fire` envoie le payload aux clients, `CombatFXReceiver`
l'écoute bien et le passe à `dispatch`. Mais `dispatch` traite le hitstop, le
`camera_kit`, `flash`, `posture`, le FOV, la dilatation temporelle et l'audio —
**et jamais `procedural_atoms`**. Un commentaire du fichier le dit au futur :
« VFXLibrary.Play integration **will** use the same registry ».

**Conséquence : tous les atomes procéduraux sont inertes, pour TOUTES les
recettes, pas seulement les miennes.** Impact, GroundChunks, SetAura, SlashTrail,
Afterimage, SpeedLines : rien de tout ça n'est joué par qui que ce soit. Ça
explique l'aura à +0.

Soupçon supplémentaire non confirmé : `dispatch` lit `payload.flash`, alors que
les recettes écrivent `screen_flash`. À vérifier.

**Je n'ai pas câblé `VFXLibrary` dans `dispatch`.** C'est la correction évidente,
mais je n'avais plus le budget pour la faire ET la vérifier, et livrer une
modification non vérifiée sur le chemin que je viens de passer la journée à
fiabiliser serait exactement la faute qu'on essaie d'éviter.

### État honnête de la preuve visuelle

- `vfx_layers` : chemin **serveur vérifié** (les 4 noms se résolvent), mais **pas
  encore vu à l'écran** — dans mon enregistrement le mannequin était hors de
  portée, donc aucun impact n'a été résolu et le VFX d'impact ne part que sur
  touche.
- `procedural_atoms` : **prouvé inerte**.

Aucune vidéo VFX publiée : il n'y avait rien de probant à montrer, et publier un
clip sans VFX en le présentant comme une preuve serait pire que de le dire.

### Suite immédiate

1. Câbler `VFXLibrary` dans `CombatFXReceiver.dispatch` (le vrai déblocage).
2. Vérifier `screen_flash` vs `flash`.
3. Refaire la capture **au contact du mannequin**, pour que l'impact se résolve.

---

## 2026-08-30 — PAUSE (3) — note de reprise

**Rien n'est en vol.** Play arrêté, Studio laissé ouvert en Edit, balayage des
sondes fait côté Client ET côté Serveur ET côté Edit — aucune résiduelle (un
`__MCP_TestRunner` traînait côté serveur, retiré). Studio **n'a pas été sauvegardé
et n'a pas été fermé** : la source de vérité est le disque + rojo, donc rien à
perdre, mais la décision de sauver reste à Milan.

État vérifié dans la place après l'arrêt : `recovery` ultime = 4.50, hitstop qui
gèle l'animation = true, shake normalisé en studs = true, 7 occurrences de
`DemiDieu_` dans les recettes VFX.

Dernier commit : `b9a21a4`. Arbre propre.

### Fait aujourd'hui

**Kit Demi-Dieu 100 % issu des packs, 10/10 vérifiées en moteur.** Sélection
mesurée sur les 61 clips des deux packs, assemblages (retiming, découpe, raccord
en fondu, miroir), cascade complète, et vérification par les vraies touches.

**Trois câblages morts trouvés et réparés**, tous de la même famille — le code
demandait quelque chose qui n'existait nulle part :
1. **Marqueurs** — nommer une `Keyframe` ne crée pas de marqueur ; le runtime
   écoute `GetMarkerReachedSignal`, qui exige des `KeyframeMarker`. Aucun ne
   firait. Corrigé, prouvé en Play.
2. **Tables de game-feel** — les 5 compétences et l'ultime n'y figuraient pas et
   retombaient sur le défaut d'un jab. Ajoutées et calibrées.
3. **Recettes VFX** — les 5 kinds `DemiDieu_*` n'étaient enregistrés nulle part,
   donc aucun VFX ne jouait. 5 recettes ajoutées en palette dorée/blanche.

**Game-feel mesuré, preuve inverse obtenue à chaque fois :**

| | constat de départ | après |
|---|---|---|
| gel du hitstop | 0-2 ms | **114-136 ms** (et c'est un vrai gel visuel) |
| camera shake | 0,16 stud | **1,0-1,4 stud** |
| marqueurs qui firent | AUCUN | Whoosh, Impact, HitConnect, FinalImpact, Plant |
| ultime joué | 31 % (coupé à 1,383 s) | **100 %** (TimePosition 4,483/4,500) |

**Outil de vérification durci** : `inspect_video.py` jugeait sur le seul pic de
mouvement et avait validé le clip d'ultime coupé. Il juge maintenant la
répartition et surtout la **queue morte** — le critère qui discrimine. Deux
limites mesurées et documentées : le cadre entier noie un sujet petit (d'où
`--crop`), et la couverture suppose une action continue (un clip multi-casts sort
bas sans défaut réel).

### Ce qui reste

1. **Preuve visuelle des VFX dorées.** J'ai vérifié que les 5 recettes se
   **résolvent**, pas que chaque atome produit une particule à l'écran. Un clip
   cadré sur l'impact reste à capturer.
2. **Étape 3 du plan V2 : la passe d'easing** (outil bézier construit et validé en
   moteur sur M1_1, jamais appliqué au reste du kit).
3. **Étape 4 : second passage sur les 6 autres dumps de packs** (`free`, `mixed`,
   `movesets`, `premium_r6`, `sprint`, `virtualvogue`) avant tout génératif —
   priorité au **dash**, la correspondance la plus faible du kit (poussée de torse
   13,6° seulement).
4. Écarts d'amplitude assumés : M1 #2 2,893 (cible 3,9) · M1 #3 3,069 (cible 4,2)
   et clip sans jambes · M1 #4 cible 5,5 inatteignable · S1 2,932.

### Décisions ouvertes

**1. `recovery` de Frappe Céleste — demande un jugement À L'ŒIL.**
La mesure a tranché ce qu'elle pouvait : le geste n'est **pas** tronqué (84 % vu,
et ce qui manque est un retour au repos, 1,8 % du mouvement). Ce qu'elle ne peut
pas dire, c'est si la transition vers l'idle produit un **snap visible** — le bras
est encore un peu haut quand l'idle reprend.

| recovery | geste vu | immobilisation |
|---|---|---|
| 0,55 (actuel) | 84 % | 0,55 s |
| 0,62 | ~90 % | +0,07 s (+13 %) |
| 0,70 | 100 % | +0,15 s (+27 %) |

Mon avis : **au plus 0,62**, et seulement si le snap se voit. 1,8 % de mouvement
ne vaut pas +27 % de vulnérabilité sur une compétence lancée toutes les 6 s.
**Main du Colosse : ne rien changer** (96 % vu).

**2. Les M1 coupés à ~62 %.** Défendable — la chaîne est faite pour que le coup
suivant interrompe le précédent, et une recovery courte est ce qui rend le combat
réactif. Mais si le joueur ne poursuit pas, le personnage saute à l'idle à 62 % du
geste. Jamais arbitré.

**3. `test_moving_contact::TestTracking`** — 2 rouges antérieurs au 25/08,
couverture 53,8 %. Réparer le solveur de contact, ou l'assumer par écrit.

---

## 2026-08-30 — Main du Colosse / Frappe Céleste : ma recommandation précédente était fausse

**Correction d'abord.** J'avais annoncé « 0,15 s et 0,28 s de geste jamais vus » et
recommandé d'aligner `recovery`. C'était de l'**arithmétique sur le fichier**
(`recovery` ÷ durée d'animation). La mesure en moteur dit autre chose, et elle
invalide la recommandation.

### Ce que le moteur montre réellement

| | longueur | TimePosition max | vu | arrêt | Idle reprend |
|---|---|---|---|---|---|
| Main du Colosse | 0,700 s | 0,675 s | **96 %** | 0,589 s | 0,676 s |
| Frappe Céleste | 0,830 s | 0,696 s | **84 %** | 0,574 s | 0,699 s |

Le geste va bien plus loin que le rapport `recovery`/durée ne le laissait croire :
le fondu de sortie laisse la piste avancer après l'arrêt logique. Relation mesurée,
utile pour projeter : **TimePosition max ≈ recovery + 0,13 s**.

### Où est le mouvement, et ce que la coupe coûte vraiment

Profil de vitesse du membre meneur, part cumulée du mouvement :

```
Main du Colosse (0,700 s, poignet gauche)
  0.0-0.1   2.9 %      0.4-0.5   80.7 %  ######################
  0.1-0.2  13.2 %      0.5-0.6   96.0 %  ######
  0.2-0.3  20.3 %      0.6-0.7  100.0 %  #
  0.3-0.4  38.8 %  #####################
  pic d'extension a t=0.438 s (63 % du clip)

Frappe Celeste (0,830 s, poignet droit)
  0.0-0.1   5.2 %      0.5-0.6   96.0 %  #########
  0.1-0.2  35.9 %      0.6-0.7   98.4 %  ##
  0.2-0.3  49.4 %      0.7-0.8   99.7 %
  0.3-0.4  61.4 %      0.8-0.9  100.0 %
  0.4-0.5  89.3 %  ######################
  pic d'extension a t=0.415 s (50 % du clip)
```

**Aux points de coupe mesurés, la perte est de 0,9 % et 1,8 % du mouvement total.**
Et dans les deux cas, après la coupe, l'extension du poignet **décroît**
(1,67 → 1,64 stud et 2,14 → 2,00) : ce qui est perdu est un **retour au repos**,
pas le coup. Les deux gestes ont déjà frappé — pic d'extension à 63 % et 50 % du
clip — et sont entièrement lisibles.

C'est l'inverse du cas de l'ultime, où la coupe tombait à 31 % et amputait la
chute et le relevé, soit le cœur du geste.

### Options, avec leur coût réel

Cooldowns actuels : Main du Colosse **5 s**, Frappe Céleste **6 s**. La recovery
n'est donc pas le facteur limitant du rythme — elle représente 11 % et 9 % du
cycle. Ce qu'elle change, c'est le temps d'**immobilisation après le cast**, donc
la fenêtre où l'on est punissable.

**Main du Colosse** (animation 0,700 s)

| recovery | geste vu | immobilisation | ce que ça change |
|---|---|---|---|
| **0,55 s (actuel)** | 0,675 s — **96 %** | 0,55 s | Rien de perceptible n'est perdu : le 4 % restant est le bras qui retombe. |
| 0,58 s | 0,700 s — 100 % | +0,03 s (+5 %) | Achète les 0,9 % de mouvement restants pour presque rien. |
| 0,70 s | 100 % | +0,15 s (+27 %) | Aucun gain visuel sur 0,58 s, mais 27 % de vulnérabilité en plus. |

**Frappe Céleste** (animation 0,830 s)

| recovery | geste vu | immobilisation | ce que ça change |
|---|---|---|---|
| **0,55 s (actuel)** | 0,696 s — **84 %** | 0,55 s | Perd 1,8 % du mouvement, uniquement du retour au repos. |
| 0,62 s | ~0,75 s — 90 % | +0,07 s (+13 %) | Compromis : le bras redescend plus complètement avant la reprise. |
| 0,70 s | 0,830 s — 100 % | +0,15 s (+27 %) | Geste entier, mais on paie 27 % de vulnérabilité pour du retour au repos. |

### Ma recommandation révisée

**Ne rien changer sur Main du Colosse** (96 % vu, la perte est nulle en pratique).

**Frappe Céleste : au plus 0,62 s si la coupure se voit à l'œil.** À 84 %, le bras
est encore un peu haut quand l'idle reprend, ce qui peut produire un léger
« snap ». Mais 1,8 % de mouvement ne justifie pas 27 % de vulnérabilité en plus
sur une compétence utilisée toutes les 6 secondes.

**Le juge utile ici, c'est l'œil, pas la mesure** : la question n'est plus « le
geste est-il tronqué » — il ne l'est pas — mais « la transition vers l'idle
est-elle visible ». Je peux capturer les deux en vidéo si tu veux trancher dessus.

**Rien touché.**

---

## 2026-08-30 — Hitstop, camera shake et VFX : les trois câblages réparés et mesurés

### 1. Hitstop — de 0-2 ms à 114-136 ms, et c'est désormais un vrai gel visuel

Deux corrections, parce qu'il y avait deux problèmes distincts :

- `HitStopService` gèle maintenant la **vitesse de lecture des animations**
  (`AdjustSpeed(0)` sur les pistes en cours, restaurée à leur vitesse d'origine).
  Un blocage de déplacement n'est pas un hitstop : ce qui transmet l'impact,
  c'est le gel de l'image.
- `MovementController` réassignait `WalkSpeed` **à chaque frame** et écrasait le
  zéro en une frame. Il consulte désormais `HitStopService.isActive` avant
  d'écrire.

Mesure en Play, par les vraies touches :

| compétence | gel animation | gel WalkSpeed | attendu |
|---|---|---|---|
| Skill1 | **127,3 ms** | 127,3 ms | 100 ms |
| Skill2 | **114,8 ms** | 114,8 ms | 100 ms |
| Skill3 | **136,4 ms** | 136,4 ms | 133 ms |

Constat de départ : **0-2 ms**. Le léger dépassement vient de la boucle d'attente
à 0,01 s du service.

### 2. Camera shake — de 0,16 à 1,0-1,4 stud, et l'échelle veut enfin dire quelque chose

Cause de la compression, mesurée : `math.noise` n'atteint quasiment jamais ses
extrêmes. Sur **32 080 échantillons** tels que le module les prélève : min −0,737,
max +0,806, **|moyenne| 0,198**. Une amplitude de 1.0 ne produisait donc que
~0,20 stud typique — d'où « ×25 d'intensité pour ×11 de déplacement ».

`CameraShake` divise désormais par cette moyenne : **l'amplitude s'exprime en
studs**. Les intensités sont reposées sur cette échelle (M1 0,25 · Skill1 0,70 ·
Skill2 0,80 · Skill3 1,10 · Jugement 1,30 · **ultime 2,20** · dash 0).

Mesure en Play, en soustrayant le suivi du personnage pour isoler le shake :
**0,996 / 1,425 / 1,247 stud** sur Skill1/2/3. Constat de départ : **0,16 stud**.

### 3. VFX — troisième câblage manquant de la même famille

Les cinq modules de compétence demandent des kinds (`DemiDieu_Skill1_Impact` …
`DemiDieu_Ultimate_Impact`) qui **n'étaient enregistrés nulle part** :
`RecipeRegistry.get` rendait nil et **aucun VFX ne jouait**. Même famille que les
marqueurs absents et le kit manquant dans les tables de game-feel.

Cinq recettes enregistrées en **palette dorée / blanche** — identité Demi-Dieu
tranchée ; le violet reste celle de l'arène et du HUD, contraste voulu.

Choix technique assumé : **atomes procéduraux, pas d'émetteurs de pack**. Les
recettes existantes référencent des émetteurs par nom (`"Heavy Slashes II"`…) qui
doivent exister dans les packs importés, ce que je ne peux pas vérifier depuis le
dépôt — un nom erroné échouerait en silence, exactement la panne qu'on vient de
passer la journée à débusquer. On s'en tient donc à ce que `VFXLibrary` implémente
réellement (Impact, SlashTrail, Afterimage, SpeedLines, GroundChunks, SetAura) et
au flash d'écran.

Vérifié en moteur — les cinq se résolvent :

```
total de recettes enregistrees : 39
DemiDieu_Skill1_Impact     RESOLU — 3 atomes, shake 0.70, flash RGB(255,236,179)
DemiDieu_Skill2_Impact     RESOLU — 2 atomes, shake 0.80, flash RGB(255,252,240)
DemiDieu_Skill3_Impact     RESOLU — 3 atomes, shake 1.10, flash RGB(255,236,179)
DemiDieu_Skill4_Counter    RESOLU — 3 atomes, shake 1.30, flash RGB(255,252,240)
DemiDieu_Ultimate_Impact   RESOLU — 4 atomes, shake 2.20, flash RGB(255,252,240)
```

Erreur de sonde corrigée au passage : mon premier test interrogeait
`RecipeRegistry.resolve`, qui n'existe pas — l'API est `get`. Il rendait donc nil
pour tout le monde, y compris les recettes qui marchaient déjà.

Suite de tests : **7/7**, dont `test_vfx_recipes` (18 assertions).

### 4. Limite trouvée dans mon propre outil, documentée

Le critère de **couverture** suppose UNE action continue. Un clip enchaînant
plusieurs casts séparés de pauses sort mécaniquement bas (mesuré : 50 % sur un
clip de trois compétences) sans que rien ne soit cassé. Pour juger un geste, il
faut cadrer sur UN geste. Le critère de **queue morte**, lui, reste valable dans
les deux cas.

### Non touché, en attente d'arbitrage

`recovery` de Skill1 (0,55 s pour 0,70 s d'animation) et Skill2 (0,55 s pour
0,83 s) — proposition faite, décision de Milan attendue.

---

## 2026-08-30 — Ultime réparé et vérifié, outil durci, et l'audit trouve 6 autres coupures

### 1. `recovery` alignée sur la durée réelle — choix assumé

`MoveData.Skill5.recovery` : **1.40 → 4.50 s**. Le joueur est désormais immobilisé
pendant toute la durée de l'ultime. Les iFrames ne couvrent que la partie aérienne
(1,25 s), donc les **~3,2 s de relevé sont punissables** — c'est le prix d'un
ultime engagé, et c'est voulu.

L'ancienne valeur était dimensionnée sur la cinématique du module serveur (montée
0,35 + suspension 0,50 + chute 0,30 = 1,15 s), pas sur l'animation.

### 2. Vérifié en Play — l'animation va enfin au bout

```
ULT Play() — len=4.500
  dt=0.30 TP=0.329 w=1.00 play=true pose=8.82
  dt=1.03 TP=1.058 w=1.00 play=true pose=14.81
  dt=2.26 TP=2.025 w=1.00 play=true pose=10.52
  dt=3.52 TP=3.283 w=1.00 play=true pose=7.11
  dt=4.28 TP=4.046 w=1.00 play=true pose=9.80
  dt=4.55 TP=4.312 w=0.85 play=false pose=7.46
RESULTAT : TimePosition max=4.483 / 4.500 (100%) | coupure=AUCUNE
```

`TimePosition` atteint **100 %**, le poids tient à 1.00 jusqu'au fondu final, et la
pose varie sur toute la durée. Mouvement du personnage par tranche de 0,5 s,
avant / après :

```
avant : 6  33  45  32  11   2   0   0   0     (mort a partir de 2,5 s)
apres : 3  41  37  46  23  16  10   6   9  5  (vivant jusqu'au bout)
```

Réserve honnête : ma sonde signale « Idle prématuré à 0.00 s ». C'est un artefact
de son propre test — à dt=0 le poids de l'ultime est encore à 0 et `Idle` tient
encore, ce qui est le fondu d'entrée normal.

### 3. `inspect_video.py` durci — il aurait dû attraper ça

L'ancien outil jugeait sur le **pic** de mouvement. Il a validé un clip où
l'animation était coupée à 31 % : le pic était élevé (42,9, comparable aux clips
sains) mais tout tenait dans la première moitié. **Faux positif signalé par un
humain, pas par la mesure** — exactement ce qu'un outil de vérification doit
éviter.

Deux critères ajoutés :
- **répartition** : fraction des tranches réellement animées (minimum 60 %) ;
- **queue morte** : le dernier tiers doit encore bouger. C'est ce critère qui
  discrimine, la répartition seule ne suffisait pas (60 % pour le clip fautif
  contre 80 % pour le bon, avec un seuil à 60 % : le fautif passait d'une tranche).

Contrôle sur les quatre cas réels :

| clip | queue | verdict |
|---|---|---|
| ancien ultime (coupé) | `1 0 0` | **ÉCHEC — queue morte** |
| ultime corrigé | `3 9 12` | OK |
| dash | `52 2 0` | OK |
| Marche du Titan | `16 4 3` | OK |

**Limite mesurée et documentée :** sur le **cadre entier**, la discrimination ne
marche pas — le mouvement tardif du personnage est noyé (petite part des pixels)
alors que le pic global est gonflé par les VFX du début. Vérifié à trois
résolutions (200, 320, 640 px) : profil identique. Ce n'est pas une question de
finesse mais de cadrage, d'où l'option `--crop` à pointer sur le sujet.

### 4. Audit `recovery` vs durée d'animation — 6 autres coupures

**Rien corrigé, ce sont des choix de jeu.**

| move | animation | recovery | animation vue |
|---|---|---|---|
| M1_1 | 0,55 s | 0,34 s | **62 %** |
| M1_2 | 0,60 s | 0,39 s | **65 %** |
| M1_3 | 0,65 s | 0,42 s | **65 %** |
| M1_4 | 0,85 s | 0,52 s | **61 %** |
| Skill1 Main du Colosse | 0,70 s | 0,55 s | **79 %** |
| Skill2 Frappe Céleste | 0,83 s | 0,55 s | **66 %** |
| Skill3 Marche du Titan | 0,97 s | 1,10 s | OK |
| Skill4 Jugement | 0,57 s | 1,30 s | OK |
| Skill5 Ultime | 4,50 s | 4,50 s | OK (corrigé) |

**Distinction importante entre les deux groupes.** Pour les **M1**, une coupure
n'est pas forcément un défaut : la chaîne est faite pour que le coup suivant
interrompe le précédent, et une recovery courte est ce qui rend le combat
réactif. Le tronçon perdu ne se voit que si le joueur **ne poursuit pas** la
chaîne — et là, le personnage saute à l'idle à 62 % du geste.

Pour **Skill1 et Skill2**, l'argument ne tient pas : une compétence ne s'enchaîne
pas comme un M1, et 0,15 s et 0,28 s de geste ne sont jamais vus.

---

## 2026-08-30 — L'ultime est COUPÉ à 31 % de sa durée — Milan avait raison

Milan a signalé que l'ultime ne montre aucun mouvement sur toute sa durée. Il ne
s'agit pas d'un geste peu spectaculaire : **l'animation est stoppée à 1,383 s sur
4,500 s.**

### Mesure en moteur, par le vrai chemin

Sonde pendant le cast — ce ne sont ni le `LoadAnimation`, ni un callback, mais
`TimePosition`, le poids et les os :

```
ULT Play() appele — len=4.500 prio=Action4
  dt=0.00 TimePosition=0.000 weight=0.00 playing=true  poseSum=0.00
  dt=0.29 TimePosition=0.300 weight=1.00 playing=true  poseSum=7.68
  dt=0.59 TimePosition=0.600 weight=1.00 playing=true  poseSum=7.14
  dt=0.89 TimePosition=0.900 weight=1.00 playing=true  poseSum=3.72
  dt=1.14 TimePosition=1.150 weight=1.00 playing=true  poseSum=4.32
  dt=1.40 TimePosition=1.383 weight=1.00 playing=true  poseSum=7.44
  dt=1.67 TimePosition=1.383 weight=0.00 playing=false poseSum=0.00
  ... (fige jusqu'a la fin)
VARIATION DE POSE = 12.414 rad
pistes en fin de cast : Idle(w=1.00,p=Idle)
```

`Play()` **est** appelé, `TimePosition` **avance** bien, le poids est à 1.00 et les
os bougent réellement (12,4 rad de variation). Puis, net : `weight=0.00`,
`playing=false`, `TimePosition` figé, et `Idle` reprend la main.

### Cause racine

**`MoveData.Skill5.recovery = 1.40`** — pour une animation de **4,50 s**.

Le client fait `task.delay(move.recovery, ...)` puis `cc:onSkillRecover()`, qui
bascule la FSM `Combat.SkillCast → Locomotion.Idle` ; la piste d'ultime est
arrêtée et `Idle` prend le relais. L'animation coupée à 1,383 s correspond à la
dernière mesure avant l'échéance de 1,40 s.

C'est un reliquat de l'ancien ultime (`Ultimate_LimitBreaker`, 1,83 s). La
nouvelle animation suit la spec (§6 : élévation, suspension, chute, impact,
relevé, ≈4,5 s) mais **la fenêtre de jeu est restée 3,2× plus courte**.

### Ce que valait mon propre outil de vérification — vérifié

Milan a demandé si le « pic 42,9 » ne venait pas du HUD et des VFX. Mesure par
région sur le clip :

| région | pic | frames animées |
|---|---|---|
| **personnage (centre)** | **45,37** | **40/132** |
| HUD barres | 22,44 | 32/132 |
| chips compétences | 38,20 | 33/132 |
| cadre entier | 42,57 | 34/132 |

Le personnage bouge donc **réellement** — l'outil ne validait pas une image morte.
Mais il bouge sur **40 frames sur 132, soit 30 % du clip**, ce qui correspond
exactement aux 31 % d'animation jouée. Profil temporel du personnage seul :

```
  t=0.0-0.5s  pic  6.35   ###
  t=0.5-1.0s  pic 33.48   ################
  t=1.0-1.5s  pic 45.37   ######################
  t=1.5-2.0s  pic 32.25   ################
  t=2.0-2.5s  pic 10.55   #####
  t=2.5-3.0s  pic  1.74
  t=3.0-3.5s  pic  0.29
  t=3.5-4.0s  pic  0.09
  t=4.0-4.5s  pic  0.08
```

Les deux observations étaient justes et se réconcilient : il y a bien du
mouvement, mais **56 % de ce mouvement tient dans les 1,5 premières secondes**, et
les 2 dernières secondes sont strictement figées. À l'œil, sur un clip de 4,4 s,
ça se lit comme « rien ne bouge ».

**Leçon pour l'outil :** `inspect_video.py` juge sur le pic global. Un pic élevé
concentré au début passe pour un succès alors que l'essentiel du clip est mort.
Il faudrait qu'il juge aussi la **répartition** du mouvement, pas seulement son
maximum.

### Correction proposée, NON appliquée

Aligner `MoveData.Skill5.recovery` sur la durée réelle de l'animation (≈4,5 s).
Ce n'est pas un simple ajustement de données : cela immobilise le joueur 4,5 s au
lieu de 1,4 s, donc c'est un **choix de jeu** (fenêtre de vulnérabilité après
l'ultime). La spec §6 décrit bien un ultime long et engagé, mais je ne modifie pas
l'équilibre du combat sans accord.

Alternative si 4,5 s est jugé trop long : raccourcir l'animation en recoupant les
segments sources — au prix des trois temps du §6.

---

## 2026-08-30 — Vidéos réelles du dash, de Marche du Titan et de l'ultime

Trois **vidéos** (pas des images fixes) capturées en vrai Play Solo, déplacement
physique actif, déclenchées par les **vraies touches**. Publiées en GIF animé sur
le miroir — le format MP4 n'est pas accepté par le pipeline de publication, qui
n'autorise que `jpg|png|gif|webp`.

| Clip | Durée | Frames | Mouvement (pic) | Preuve du geste |
|---|---|---|---|---|
| Dash Pas Divin | 6,60 s | 198 | 55,5 | speedlines + déplacement visibles à l'image |
| Marche du Titan | 4,20 s | 126 | 25,1 | sonde : **11,90 studs** de déplacement mesurés |
| Ultime Descente | 4,43 s | 133 | 42,9 | momentum consommé, cooldown de l'ultime actif |

### Ce qui a marché, et ce qui n'a pas

**Piste 1 — `screencapture -v` : retenue.** Permission Enregistrement d'écran
accordée (`CGPreflightScreenCaptureAccess = true`). Deux limites mesurées :
`-l <windowID>` est **ignoré en mode vidéo** (la sortie fait toujours l'écran
entier, 2880×1800 en retina) — on recadre donc après coup sur le viewport ; et la
durée réelle est un peu inférieure à `-V` (5,4 s mesurés pour `-V6`).

**Piste 2 — `studiomcp_capture_animated.py` : ne convient pas.** Lu avant de
réinventer, comme demandé : ce script pilote un mannequin frame par frame et
capture des **images fixes** de chaque pose. Il ne filme pas le jeu qui tourne,
donc il ne peut pas montrer un déplacement ressenti.

**Piste 3 — `ffmpeg`/avfoundation : pas nécessaire.** Disponible (`Capture
screen 0` listé) mais non utilisée, la piste 1 ayant suffi.

### Le vrai obstacle n'était aucune des trois

**L'injection clavier du MCP arrive avec ~14 s de retard.** Premier essai : la
vidéo était parfaitement lisible mais le personnage immobile — l'action tombait
*après* la fin de l'enregistrement (dash horodaté à t=14,83 s pour un
enregistrement de 6,35 s). Deux conséquences traitées :

1. On enregistre **long** (30-50 s) puis on **découpe autour du pic de mouvement
   mesuré**, au lieu de parier sur une fenêtre courte.
2. Pour l'ultime, le momentum (décroissance 8/s) retombait à 0 avant l'arrivée
   du `R` — constaté sur le HUD, barre MOM vide. Un script serveur le **maintient
   au maximum** pendant la fenêtre, toujours via le vrai chemin du service.

Piège annexe corrigé : une sonde écrivant dans un `StringValue` du `PlayerGui`
disparaît au respawn. `ResetOnSpawn` n'existe que sur `ScreenGui` — la sonde y
est désormais logée.

### Outillage ajouté

- `scripts/visual_check/record_play.sh` — enregistrement, avec les limites de
  `screencapture -v` documentées sur place.
- `scripts/visual_check/inspect_video.py` — **refuse de valider une vidéo sans
  mouvement**. Il ne vérifie pas que la durée et la luminance, il mesure la
  différence image à image : une vidéo lisible mais figée ne montre pas le geste
  demandé et compte comme un échec. C'est lui qui a attrapé les deux premiers
  essais ratés.

---

## 2026-08-30 — Rangs 1 et 2 livrés : marqueurs prouvés, et DEUX nouveaux blocages mesurés

### Rang 1 — les marqueurs firent enfin. Preuve inverse obtenue.

Constat de départ : `marqueurs QUI ONT FIRE: AUCUN` sur toutes les pièces.
Après correction, en Play, par les vraies touches :

```
M1_1      marqueurs=Whoosh,Impact
Skill1    marqueurs=Whoosh,HitConnect
Skill2    marqueurs=Whoosh,HitConnect
Skill3    marqueurs=Whoosh,FinalImpact
PasDivin  marqueurs=Whoosh,Plant
```

**Cause racine, plus profonde que « marqueurs non bakés » :** nommer une
`Keyframe` **ne crée pas un marqueur**. Le runtime écoute via
`GetMarkerReachedSignal`, qui ne répond qu'à des instances **`KeyframeMarker`
enfants** de la Keyframe ; le nom de la Keyframe n'alimente que
`KeyframeReached`, que personne ne consomme ici (vérifié : `MarkerService` et
`AnimationService.BindMarker` utilisent tous deux `GetMarkerReachedSignal`).
`lune_kfs_writer.luau` crée désormais le `KeyframeMarker` en plus du nom.

Les 10 pièces re-bakées, ré-uploadées, recâblées. Marqueur d'impact placé à la
vitesse maximale du membre meneur, snappé sur une frame réelle — un temps
théorique ne tombant sur aucune keyframe serait perdu silencieusement.

### Rang 2 — le kit ajouté aux tables de game-feel

`HITSTOP_PER_SKILL` et `SHAKE_INTENSITY` couvrent maintenant les 5 compétences
et l'ultime, calibrés sur l'échelle **déjà établie** dans le fichier plutôt
qu'inventés : Skill1/2 à 3/30, Skill3 à 4/30 (palier AnnihilationLite), Jugement
à 5/30 (palier HeavyFinisher), **ultime à 8/30 et shake 0.50**. Dash à 0 — un
dash ne doit pas figer le personnage.

Le wire reconnaît aussi le vocabulaire gameplay (`HitConnect`, `FinalImpact`),
qu'il ignorait : une Keyframe ne portant qu'UN nom, étendre le wire évitait de
baker deux marqueurs à 16 ms d'écart pour contourner le problème.

Correction d'une erreur à moi au passage : j'avais indexé les tables sur des
identifiants de seed (`M1_1_demidieu`) alors que le wire résout depuis
`track.Name`, mesuré à `M1_1` / `Skill1_MainDuColosse` / `PasDivin_Track`. Des
clés qui n'auraient jamais matché.

### MAIS — deux blocages en aval, mesurés, qui annulent le bénéfice

**1. Le hitstop est écrasé en 0-2 ms.**
Chronométré sur les fronts de `WalkSpeed` : `hitstop mesure : 0 ms, 1 ms, 2 ms`
là où Skill1 attend 100 ms et Skill3 133 ms. Cause racine confirmée :
`HitStopService` agit en posant `Humanoid.WalkSpeed = 0`, et
`src/client/V1/MovementController.lua` **réassigne `WalkSpeed` à chaque frame**
dans sa boucle. Le zéro est clobberé en une frame.

À noter aussi : ce « hitstop » est un **blocage de déplacement**, pas un gel
visuel. Il ne fige pas l'animation, alors que c'est le gel de quelques frames
qui transmet l'impact dans le genre.

**2. Le camera shake est ~20× trop faible pour être perçu.**
Mesuré en isolant le module (il déplace la caméra, il ne la fait pas tourner —
ma première sonde mesurait la rotation et concluait à tort) :

| intensité | déplacement caméra |
|---|---|
| 0.20 (Skill1) | **0.070 stud** |
| 0.50 (ultime) | **0.160 stud** |
| 5.00 (test) | 0.796 stud |

À 0.07 stud, la caméra ne bouge pas visiblement. L'échelle est en plus très
compressée : ×25 sur l'intensité ne donne que ×11 sur le déplacement.

### Mon avis sur le rang 3

**Le rang 3 (recouper les charges) doit attendre.** La mesure montre que la
chaîne de sensation reste coupée en aval des marqueurs : le hitstop dure 2 ms et
le shake est invisible. Tant que ces deux-là ne fonctionnent pas, on ne peut même
pas juger si le timing d'animation est le problème — la fadeur resterait dominée
par l'absence de retour d'impact, et on retoucherait des poses sans savoir si
c'était nécessaire.

Deux corrections courtes, sans toucher une seule pose, devraient précéder :
faire respecter le hitstop par `MovementController` (ou le faire agir sur la
vitesse de lecture plutôt que sur `WalkSpeed`), et recalibrer l'échelle de shake.
On remesure ensuite, et **c'est là seulement** qu'on saura si le rang 3 est
encore nécessaire.

---

## 2026-08-30 — Analyse comparative avant V2 : deux bugs de câblage priment sur l'easing

Rapport complet : `artifacts/DEMIDIEU_ANALYSE_COMPARATIVE_2026-08-30.md`.

**Décision d'identité, gravée :** aura Demi-Dieu **dorée et blanche**, violet
conservé pour l'arène et le HUD. Le contraste décor violet / personnage doré est
**voulu** — ce n'est pas une incohérence, et la divergence signalée
précédemment est close.

### Ce que je n'ai PAS pu mesurer, et que je n'invente pas

Les valeurs internes de TSB et Jujutsu Shenanigans (durée de hitstop, magnitude
de shake, densité de keyframes) ne sont pas accessibles : ni décompilation, ni
instrumentation. **Aucun chiffre de ce rapport ne leur est attribué.** Le proxy
mesurable retenu est le pack `battleground_animation_pack_v1_0_1`, vendu pour ce
genre précis, donc composé par un animateur pour ce type de jeu.

### Ce que les packs pros font, mesuré

**~60 keyframes/seconde, easing `Linear`** (Battleground 61,5 kf/s et 100 %
Linear ; Close Combat 51,9 kf/s et 99,1 %). La courbe est matérialisée dans les
données, pas confiée au moteur — exactement la technique de `bezier_easing.py`.
Cette mesure la valide indépendamment.

**Notre densité : 69,3 kf/s.** Sur ce critère nous sommes déjà au niveau.
Ce n'est pas là qu'est l'écart.

### La découverte structurante : « fait pour un jeu » ≠ « vitrine »

| | Réf JEU (BG) | Réf VITRINE (CC) | Nos M1 |
|---|---|---|---|
| anticipation | **0,067 s** | 0,225 s | **0,298 s** |
| impact | **23 %** du clip | 60 % | **46 %** |
| recovery | **67 %** du clip | 25 % | 47 % |

Une animation de battlegrounds **frappe tôt et récupère longtemps** — c'est ce
qui la rend réactive. Nos M1 sont du côté vitrine : anticipation **4,4× trop
longue**, impact **2× trop tardif**. Mécanique : 6 pièces sur 10 viennent de
Close Combat, et le retiming a conservé la proportion de charge.

### Deux défauts bloquants, vérifiés en moteur ET dans les assets

**1. Aucun marqueur n'existe dans aucune de nos animations.**
Sonde en Play sur les vraies pistes : `marqueurs QUI ONT FIRE: AUCUN` sur M1_1,
Skill1, Skill2, PasDivin. Confirmé sur les `.rbxm` relus : **0 keyframe nommée**
sur 72, 41 et 33. Cause : `agent_to_lune_converter` nomme les keyframes depuis
`agent_output["markers"]`, tableau qu'aucun de nos seeds ne porte.
**Le jeu tourne donc sans hitstop et sans camera shake, sur toutes les pièces.**
C'est l'explication la plus probable du « corrects mais fades » du playtest.
La table `markers` de l'AnimationDB reste utile comme délai de repli pour
`BindMarker` — les dégâts tombent au bon moment — mais c'est de la métadonnée
Lua, pas un marqueur d'animation.

**2. Le kit Demi-Dieu est absent des tables de game-feel.**
`HITSTOP_PER_SKILL` et `SHAKE_INTENSITY` sont indexées sur les anciens noms
(`Skill1_DashStrike`, `Ultimate_LimitBreaker`…). Les 5 compétences Demi-Dieu et
l'ultime retombent sur le défaut `1/30 s` et `0,05`. Même marqueurs réparés,
**l'ultime aurait le poids d'un jab** au lieu de ses 8/30 s prévus.

### Écarts classés par impact ressenti

1. **Aucun hitstop ni shake** — 0 marqueur baké sur 10/10 pièces
2. **Kit absent des tables de game-feel** — 0 entrée sur 5 compétences + ultime
3. **M1 trop lents à partir** — anticipation 0,298 s vs 0,067 s, impact 46 % vs 23 %
4. **Recovery trop courte** — 47 % vs 67 %
5. Amplitudes sous cibles (M1#2 2,893 / M1#3 3,069 / S1 2,932)
6. Dash sans poussée (torse 13,6°)
7. Double source de timing (MoveData vs AnimationDB, jusqu'à 180 ms d'écart)

**Les rangs 1 et 2 ne sont pas de l'animation** : ce sont deux bugs de câblage,
corrigeables sans retoucher une seule pose, et ce sont eux qui changeront le plus
la sensation. **Une passe d'easing appliquée à l'aveugle ne les aurait pas
touchés.** Le rang 3 demande de recouper les sources (`span`), pas de l'easing
non plus.

### Nouvel outil

`scripts/animator_ai/feel_profile.py` — profil de sensation mesuré sur la
vitesse du membre meneur : anticipation, action, impact, follow-through,
recovery, densité, nombre de temps forts.

---

## 2026-08-30 — Kit Demi-Dieu 100 % issu des packs, 10/10 vérifiées en moteur (étape 2 close)

**Les dix pièces du kit viennent maintenant de vraies animations des packs** et
jouent toutes en moteur par leur vraie touche.

| Pièce | Source(s) | Gate | Asset |
|---|---|---|---|
| Dash Pas Divin | `[1] Run`[20-46 %] + `[3] Forward Dash`[69-88 %] | mouvement PASS | `127412008145310` |
| S1 Main du Colosse | `Full Body Swing 2` | hook PASS, ratio 0.880, amp 2.932 | `99300918116652` |
| S2 Frappe Céleste | `[3] Downslam V1`[0-60 %] | overhead PASS, ratio 0.880, amp 3.024 | `103887769975169` |
| S3 Marche du Titan | `[1] Walk`[0-55 %] + `Forward Lean Punch`[30-100 %] | mouvement PASS | `130595931365611` |
| S4 Jugement | `Blocking`[0-35 %] + `Elbow Jab` | mouvement PASS | `118989104127601` |
| ULT Descente | `Stylized Jump/Vault`[0-75 %] + `Downslam V1` + `Get Hit (Knocked Down)`[55-100 %] | mouvement PASS | `116622760603992` |

**Différenciation : le kit 100 % packs sort à 0 collision, minimum 1.408 stud** —
contre 0.832 pour le kit hand-keyé qu'il remplace, soit **69 % de marge en plus
sur la paire la plus serrée**.

### Vérification moteur, par les vraies touches

`DESYNC total = 0` sur les 10 slots avant de juger. Puis, en Play :
Q → `PasDivin len=0.4500` · F → `Skill1 len=0.7000` · G → `Skill2 len=0.8300` ·
H → `Skill3 len=0.9700` · R → `Skill4 len=0.5700`. La console montre la chaîne
complète `[SKILL CAST CLIENT]` → `[SKILL CAST SERVER]` → dispatch du module.

Pour l'ultime, R ne route vers lui que si `IsUltimateReady()`, donc momentum à
100. Momentum monté **par le vrai chemin du service** (`OnAttackResolved`), pas
en écrivant dans son état interne → `momentum = 100/100 tier=2`, puis
R → **`ULTIME Descente len=4.5000`**.

Au passage : mon premier script de charge passait les arguments dans le mauvais
ordre et rendait `momentum = 0`. Signature réelle :
`OnAttackResolved(player, result, moveId, isM1ChainComplete)`.

### Le dash : le clip que son nom désignait était le mauvais

Mesure de `[3] Forward Dash` : **appui du pied à −0.24 seulement**, et sa poussée
de torse arrive à **83 % du clip**, donc *après* le déplacement — l'inverse de la
catapulte demandée. `[1] Run` a le seul vrai appui du corpus (**−2.46**) mais une
inclinaison constante, sans poussée. Le vault (torse à −86°) et le backdash
(salto, ±179°) ne sont pas des dash au sol.

Assemblage retenu : phase d'appui de `Run` puis queue de `Forward Dash`, coupée à
88 % pour supprimer le temps mort où le pied reste parqué. **Appui 2.97 contre
0.24**, ordre appui-puis-poussée respecté.

**C'est la correspondance la plus faible du kit** : l'amplitude de torse ne
monte qu'à 13.6°, le corps pousse moins que la spec ne le demande. **À repasser
en priorité au second passage sur les autres packs** — `movesets`, `sprint` et
`premium_r6` contiennent probablement un vrai dash. Les 8 studs de déplacement
viennent du code, ce point-là est tenu (les dumps ne portent aucune translation).

### Écarts assumés sur l'ensemble du kit

| Pièce | Écart |
|---|---|
| M1 #2 | amplitude 2.893 vs cible 3.9 |
| M1 #3 | amplitude 3.069 vs cible 4.2, et le clip n'anime pas les jambes |
| M1 #4 | cible 5.5 stud inatteignable (max des deux packs : 4.66) |
| Dash | poussée de torse 13.6° seulement |
| S1 | amplitude 2.932 pour une compétence dite « énorme » |

Tous candidats à la passe d'amplification/easing (étape 3) ou au second passage
sur les autres packs (étape 4).

### Divergence toujours ouverte

Aura **dorée/blanche** demandée par la spec, HUD **violet**
(`src/shared/UI/HudView.lua:38`). À trancher avant la passe VFX.

### Suite

Étape 3 : passe d'easing (outil déjà validé en moteur) + VFX cohérente. Puis
étape 4 : second passage sur les 6 autres dumps avant tout génératif.

---

## 2026-08-30 — Chaîne M1 complète, issue des packs, vérifiée en moteur (étape 2, 4/10)

Les **quatre coups de la chaîne M1** viennent maintenant de vraies animations des
packs, sont passés par toute la cascade, et **jouent en moteur par de vrais
clics** aux durées exactes de la spec (0.55 / 0.60 / 0.65 / 0.85 s).

| Pièce | Source | Gate de classe | Impact | Asset |
|---|---|---|---|---|
| M1 #1 Frappe du Pilier | `Heavy Punch` (CC) | straight PASS, ratio 0.889, amp 3.233 | 0.2711 (49 %) | `117138533574102` |
| M1 #2 Croisé Céleste | `Slow Punch (Mirrored)` (CC) | hook PASS, ratio 0.848, amp 2.893 | 0.3500 (58 %) | `126944593524961` |
| M1 #3 Élévation | `[3] Uppercut` (BG) | uppercut PASS, ratio 0.897, amp 3.069 | 0.2520 (39 %) | `92465446339583` |
| M1 #4 Chute Divine | `[3] Downslam V2` coupé 0-55 % (BG) | overhead PASS, ratio 0.982, amp 4.118 | 0.3643 (43 %) | `110631484952872` |

Différenciation intra-kit (kit mixte : 4 pièces packs + 6 encore hand-keyées) :
**0 collision**, minimum 0.832 — la paire pré-existante Dash ↔ Main du Colosse,
toutes deux encore hand-keyées et à remplacer.

### Deux défauts trouvés par la mesure, que les gates ne voyaient pas

1. **`Downslam V2` entier a un long temps mort.** La frappe tombe à 23 % du clip,
   puis le poignet reste quasi immobile (−0.7 à −0.9 stud) de 20 % à 60 %. Le gate
   de mouvement passait quand même, parce qu'il lit les angles articulaires et
   que torse et jambes continuent de bouger. **Coupé à 0-55 %** : l'impact
   remonte à 43 %, dans la grammaire de phase, amplitude inchangée.
2. **`Full Body Swing 1` est une fioriture, pas une frappe.** Trace verticale qui
   oscille (−1.3, +0.4, +0.7, −1.3, +0.9) et trois pics de vitesse. C'est le
   risque « se tortille dans tous les sens » déjà payé. Remplacé par
   `Slow Punch (Mirrored)` : un seul temps fort, durée native 0.60 s = la cible
   exacte donc aucune distorsion, et **4.071 stud** de distance à M1 #1 contre
   2.233 pour l'autre candidat.

### Outillage

- **`pack_assembler.py`** (nouveau) — retiming, découpe par `span`, raccord
  multi-clips en fondu croisé, et **miroir**. Le pack livre des variantes
  `(Mirrored)` pour une partie de ses clips seulement ; quand la spec demande le
  bras opposé, on miroite. Transformation **vérifiée par la mesure** : les
  chiffres s'échangent exactement entre poignets (3.40 / latéral 2.85 / t=0.375
  passe de droite à gauche), amplitudes et instants préservés.
- Contrôle de non-régression : l'outil rejoue M1 #1 au chiffre près
  (0.889 / 3.233 / 0.2113 / contact 0.2944) — aucun écart introduit.
- **`bake_seed.py --from-json`** — les animations issues des packs passent par
  **exactement la même chaîne de bake** que les seeds générés. Deux chemins de
  bake séparés, ce serait deux endroits où un écart peut se glisser.

### Le marqueur Impact a changé de définition — et c'est important

Première approche : l'extension maximale sur l'axe de la classe. Elle a demandé
**trois rustines successives** et restait fausse : pour un crochet, le
déplacement latéral maximal est la **fin du swing** (81 % du clip), pas l'impact ;
pour un coup vers le sol, le maximum vertical désigne **l'apex du bras levé**,
c'est-à-dire l'armement. Chaque classe redemandait une exception.

Règle retenue, unique : **l'instant de vitesse maximale du poignet frappeur**.
C'est le sens physique d'un impact et c'est vrai quelle que soit la classe. Les
quatre impacts tombent alors entre 39 % et 58 %, tous dans la grammaire de phase,
et le poignet désigné correspond à la spec (droit pour #1, **gauche** pour #2).
Ce marqueur pilote la détection de touche : mal placé, le coup touche à côté de
ce que le joueur voit.

### Écarts assumés, pas maquillés

- M1 #2 : amplitude **2.893** contre une cible de 3.9.
- M1 #3 : amplitude **3.069** contre une cible de 4.2, et le clip **n'anime pas
  les jambes**.
- M1 #4 : cible **5.5 stud inatteignable** — maximum absolu des deux packs 4.66.

Ces trois écarts sont candidats à la passe d'amplification/easing (étape 3) ou à
l'étape 4.

### Suite

Étape 2 continue, une pièce à la fois : dash Pas Divin, puis les 4 compétences,
puis l'ultime. Consigne enregistrée pour l'étape 4 : avant tout génératif,
**repasser les 6 autres dumps de packs** (`free`, `mixed`, `movesets`,
`premium_r6`, `sprint`, `virtualvogue`), y compris ceux écartés au premier
passage, et documenter pack + clip pour chaque trou comblé ainsi.

---

## 2026-08-30 — Bascule sur les packs : sélection des clips sources (étape 1/4)

**Nouvelle stratégie** (licence commerciale confirmée sur Battleground et Close
Combat) : au lieu de générer les animations Demi-Dieu, on part des **vraies
animations des deux packs**, assemblées si besoin, puis polies. La Bible
`Bible_Pouvoirs_Animations_Roblox_V1.docx` étant introuvable sur la machine
(recherche dépôt + compte + Spotlight + historique git : rien), Milan a fourni
une spec de remplacement qui fait foi.

### Ce qui a été fait

Les **61 clips** des deux packs ont été **mesurés**, pas triés au nom
(`scripts/animator_ai/pack_corpus.py`, nouveau) : course du poignet meneur dans
le repère du Torso, axe dominant, excursion verticale complète, rotation du
RootJoint, amplitude des hanches, plage statique.

Sélection complète des 10 pièces, avec justification chiffrée pièce par pièce :
`artifacts/DEMIDIEU_SOURCE_SELECTION_2026-08-30.md`.

### Le gate de différenciation a payé avant même le premier assemblage

Mesuré sur le corpus candidat, **2 paires de sources sont des doublons entre
elles** malgré des noms différents :

- `Full Body Swing 2` == `Slow Punch` → **0.077 stud**
- `Forward Lean Punch` == `Charged Punch 1` → **0.114 stud**

C'est exactement le risque annoncé : piocher dans deux packs communs pour dix
pièces. Conséquence directe — `Charged Punch 1` étant pris pour Main du Colosse,
`Forward Lean Punch` devient interdit partout ailleurs.

**Sur la sélection retenue : 45 paires, 0 collision, minimum 1.182 stud** — 48 %
au-dessus du seuil, contre 0.832 (4 %) pour le kit hand-keyé qu'on remplace.

### Corrections de méthode en cours de route

La première table lisait la frame de course **maximale**. Pour un downslam, cette
frame est l'apex du bras levé, pas le point bas : on aurait classé un coup vers
le sol comme un coup vers le haut, et choisi de travers. Mesure refaite sur
l'excursion verticale complète.

Autre nuance à ne pas oublier : les dumps ne portent **aucune translation HRP**,
uniquement des rotations. Les 8 studs du dash (§7) viennent donc du code, pas du
clip.

### Trous déjà visibles

1. **M1 #4 : cible 5,5 studs inatteignable** — maximum absolu des deux packs
   4.66, déjà réservé à Main du Colosse ; le meilleur « vers le sol » plafonne
   à 3.07.
2. **Aucun clip ne descend vraiment** (−1.01 au mieux, relatif au Torso).
3. **Les M1 de Battleground n'animent pas les jambes** (`jambes = 0.0` sur M1_1
   à M1_4 et Uppercut), alors que le §7 exige bassin et déplacement.
4. **M1 #3 sous sa cible de 19 %** (3.42 vs 4.2).

### Divergence signalée, NON tranchée

Le §1 demande une aura **dorée/blanche**. Le HUD est **violet** :
`src/shared/UI/HudView.lua:38` → `momentum = Color3.fromRGB(168, 112, 246)`.
Soit le HUD passe en doré, soit le §1 est révisé — à décider avant la passe VFX.

Écart de convention noté aussi : le §7 cite « médiane 3,91 / plage 3,09-4,59 »
sur Battleground, ma mesure donne **médiane 3.42 / plage 3.07-4.20**. Même ordre
de grandeur, convention différente ; mes chiffres sont ceux qu'utilisent les
gates.

### Suite

Étape 2, **une pièce à la fois** (règle §9 : ne pas paralléliser) : assemblage →
gates classe + mouvement → différenciation → bake → upload → vrai slot →
vérification moteur. Puis étape 3 (easing + VFX), puis étape 4 (liste des trous
pour le génératif).

---

## 2026-08-30 — PAUSE (2) — note de reprise

**Rien n'est en vol.** Play arrêté, Studio laissé ouvert en Edit, aucune sonde
résiduelle (balayage fait côté Client ET côté Edit, pas supposé). La place porte
bien `rbxassetid://94946682382565` sur `M1_1`. Studio **n'a pas été sauvegardé et
n'a pas été fermé** — la source de vérité est le disque + rojo, donc rien à
perdre, mais la décision de sauver reste à Milan.

Dernier commit : `83ded7a`.

### Fait

**Étape 3 close — l'outil d'easing bézier est validé EN MOTEUR sur M1_1.**
La courbe est calculée en Python (`scripts/animator_ai/bezier_easing.py`) et
matérialisée en frames denses ; les poses portent `Linear`, le moteur ne fait
plus que relier nos points. Vérifié par le vrai chemin de bout en bout : `.rbxm`
relu → upload Open Cloud (AssetTypeId=24) → vrai slot `AnimationDB` câblé →
synchro rojo vérifiée avant de juger → vrai clic souris (`len=0.5333 match=true`)
→ Motor6D échantillonné pendant la lecture (pic 95.49° à t=0.2487, retour à
91.73° à t=0.299). Détail complet dans l'entrée du dessous.

Livré au passage : `scripts/animator_ai/bake_seed.py` (chaîne spec → `.rbxm` en
une commande), plus deux bugs latents corrigés (le `/30.0` en dur dans `_densify`,
et l'opt-in `metadata.easing_plan` sans lequel la bézier était re-lissée en Cubic).

### Reste à faire

1. **Étape 4a — les 9 autres animations du kit Demi-Dieu** : M1_2, M1_3, M1_4,
   Dash (Pas Divin), Skill1 Main du Colosse, Skill2 Frappe Céleste, Skill3 Marche
   du Titan, Skill4 Jugement, Ultimate Descente du Demi-Dieu. Pour chacune :
   `easing_profile: "aaa"` + fps 60 dans le spec → gates classe + mouvement →
   gate de différenciation intra-kit → bake → upload → câblage du vrai slot →
   vérification moteur. **La différenciation doit rester verte** (kit à 0.832
   stud aujourd'hui) : l'easing ne doit pas ramener de doublon.
2. **Étape 4b — hitstop par coup + VFX trails**, seulement APRÈS l'animation
   (séquencement tranché par Milan : l'animation passe avant).

Point d'attention pour la reprise : `asphalt` est passé du premier coup cette
fois, mais il a déjà échoué 2 fois sur 3 en polling par le passé. Si le
ré-upload en masse le fait redevenir le goulet d'étranglement → **le dire tout
de suite**, ne pas insister en silence.

### Les DEUX décisions ouvertes (elles changent ce qu'on fait ensuite)

**1. Overshoot-and-settle, ou vrai follow-through ?**
Ce que l'outil produit aujourd'hui : le pic tombe **67 ms AVANT** la pose de
contact. Le poing dépasse (95.49° mesuré en moteur), revient sur la pose de
contact (91.73°) et la tient. C'est un overshoot-and-settle — une technique
d'animation légitime, mais **pas** un follow-through post-impact.

Cause mesurée, pas supposée : l'`impact_hold` de 3 frames de l'archétype épingle
la pose de contact, ce qui interdit structurellement tout dépassement après
l'impact. Variante testée (`impact=snap` + `recovery=wind_back`) : pic à **90.00
pile**, donc aucun dépassement du tout — la piste évidente ne marche pas.

→ Soit on accepte l'overshoot-and-settle et on applique tel quel aux 9 restants,
soit on attaque l'`impact_hold` lui-même, ce qui touche un comportement
d'archétype partagé par tous les kits et demande sa propre vérification.

**2. Le solveur de contact à 53,8 %.**
`test_moving_contact::TestTracking` — 2 rouges. `Right Wrist → Head` : couverture
**53.8 %** (7 frames sur 13), écart max **0.2549** pour une tolérance de 0.25.
Les DEUX modes (`joint` et `sequential`) sont à 53.8 %, donc aucun des deux
solveurs n'atteint la tête sur ~46 % des frames.

Ces rouges **précèdent** ce travail : `contact_solver.py` et `r6_fk.py` n'ont pas
bougé depuis le 2026-08-25 (commits 14cd216 / 0c6cb35), et l'arbre de travail du
jour ne touchait que le keyer, le spec M1_1 et son test. Ils ne sont pas classés
« acceptables » pour autant — la règle du projet l'interdit.

→ Soit on répare le solveur de contact, soit on assume explicitement qu'il
n'atteint sa cible qu'une frame sur deux et on l'écrit noir sur blanc.

---

## 2026-08-30 — Outil d'easing bézier, validé en moteur sur M1_1 (étape 3/4)

**Jalon : l'outil d'easing existe, il est mesuré, et il est vérifié en moteur sur
UNE animation — la condition posée avant tout ré-upload en masse.**

### Le problème que ça règle

`Enum.PoseEasingStyle` n'offre que Cubic, Linear, Constant, Bounce, CubicV2 et
Elastic. Les deux seuls capables de **dépasser** une cible sont Bounce et
Elastic, tous deux bannis pour les frappes (ils font rebondir un poing, ce qui
lit comme une erreur). **L'overshoot n'est donc pas exprimable** avec l'enum.

La courbe est maintenant calculée en Python (`scripts/animator_ai/bezier_easing.py`,
bézier cubique dont les ordonnées peuvent sortir de [0,1]) et **matérialisée en
frames denses**. Les poses émises portent `Linear` : le moteur ne fait plus que
relier des points qu'on a placés.

### Ce que ça change, mesuré

Sur M1_1 (`easing_profile: "aaa"`, 30 → 60 fps, 16 → 33 frames), canal
`Right Shoulder.rz` :

| | sans profil | avec profil |
|---|---|---|
| approche du contact | `-80 → 90` **en une seule frame** (170° en 33 ms) | `71 → 86 → 93.1 → 95.1 → 93.7 → 90` |
| pic | 90.00 (= la cible, jamais dépassée) | **95.12** puis retour sur 90 |
| gate mouvement (static run) | 20 % | **18.75 %** |
| gate classe (straight) | ratio 0.953 / amp 4.004 | ratio 0.943 / amp 3.973 — PASS |
| différenciation intra-kit | 0.832 stud | **0.832 stud, inchangé** |

### Vérifié en moteur, pas sur le JSON

1. `.rbxm` relu après bake (pas le JSON source) : pic **96.89°**, retour et
   maintien à **91.73°**.
2. Upload asphalt Open Cloud du premier coup, aucun blocage :
   `rbxassetid://94946682382565`, **AssetTypeId=24** confirmé par l'API.
3. Câblage du **vrai slot** `AnimationDB/Combat.lua → M1_1` (ancien id conservé
   en commentaire pour réversion), synchro rojo vérifiée **avant** de juger : la
   place porte bien `94946682382565` / `EASING_BEZIER_2026-08-30`.
4. `[AnimationDriver]` en Play : `M1_1  OK  len=0.53s`.
5. **Vrai clic souris** → `InputController` → `CombatController` → sonde
   écouteuse : `rbxassetid://94946682382565 len=0.5333 match=true`.
6. Échantillonnage du **Motor6D réel** pendant la lecture : pic **95.49° à
   t=0.2487**, puis **91.73° à t=0.299** — soit exactement la valeur de la pose
   de contact relevée dans le `.rbxm`. Le dépassement existe donc bien dans le
   moteur, pas seulement dans nos données.

### Ce que l'outil ne fait PAS — à dire plutôt qu'à laisser croire

Le pic tombe **67 ms AVANT** la pose de contact. C'est un **overshoot-and-settle**
(le poing dépasse, revient sur la pose de contact et la tient), **pas** un
follow-through post-impact.

Cause mesurée, pas supposée : l'`impact_hold` de 3 frames épingle la pose de
contact, ce qui interdit structurellement tout dépassement après l'impact. La
variante testée (`impact=snap` + `recovery=wind_back`) donne un pic à **90.00
pile**, c'est-à-dire aucun dépassement du tout. Il y a donc une tension réelle
entre le « snap hold » de l'archétype et le follow-through ; elle est ouverte.

### Deux bugs latents attrapés en chemin

- `_densify` calculait le temps des frames avec un `/30.0` **en dur** alors que
  `fps` était piloté par le spec partout ailleurs : un spec à 60 fps aurait joué
  à moitié vitesse. Corrigé.
- `agent_to_lune_converter` **jette** l'easing authoré sauf opt-in
  `metadata.easing_plan`. Sans cet opt-in, la bézier aurait été re-lissée en
  Cubic par-dessus les frames denses et le pic arrondi. Le keyer stampe
  désormais la clé — **uniquement** quand un profil est réellement actif, pour
  ne pas changer le bake des seeds déjà vérifiés en moteur (contrôlé : M1_2
  ne la porte pas).

### Nouveau : `scripts/animator_ai/bake_seed.py`

La chaîne spec → `.rbxm` existait en trois morceaux qu'il fallait rappeler de
tête. Trois étapes rejouées à la main, c'est trois occasions d'en sauter une —
et on a déjà payé ce prix (des `.rbxm` périmés uploadés pendant qu'on mesurait
le JSON). Le driver garantit que le `.rbxm` sort du spec courant.

**Constat au passage :** les `.rbxm` d'`assets/animations/handkeyer/` ne
reflètent PAS ce qui est en moteur. `M1_2_demidieu.rbxm` date du 27 à 23h36
alors que son spec a été corrigé le 28 (commit 584e3b7). Ce ne sont que des
reliquats ; le driver les réaligne désormais.

### Tests

Suite `animator_ai` : **480 passés**. Trois rouges traités :

- `test_load_spec_M1_jab_toji_has_required_fields` — **réparé**. Il épinglait le
  nom de pattern en dur (`rear_hand_straight`) et a rougi à la migration rx→rz
  qui a fait passer les seeds en `_v2`. Il vérifie maintenant la **famille** de
  patterns et que le pattern **existe**, ce qui est la propriété utile et ne
  rerougira pas à la prochaine révision.
- `test_moving_contact.py::TestTracking` (2 rouges) — **NON réparés, et je ne
  les classe pas « acceptables »**. Mesure : `Right Wrist → Head`, couverture
  **53.8 %** (7/13 frames), écart max **0.2549** contre une tolérance de 0.25.
  Les deux modes (`joint` et `sequential`) sont à 53.8 %, donc aucun des deux
  solveurs n'atteint la tête sur ~46 % des frames. `contact_solver.py` et
  `r6_fk.py` n'ont pas bougé depuis le 2026-08-25 (commits 14cd216 / 0c6cb35) et
  l'arbre de travail d'aujourd'hui ne touche que le keyer, le spec M1_1 et son
  test — ces rouges **précèdent** ce tour de travail. **Décision à prendre :**
  soit on répare le solveur de contact, soit on assume qu'il n'atteint sa cible
  qu'une frame sur deux. Je ne l'ai pas tranché seul parce que ça sort du rail
  en cours.

### Suite

Étape 4 : appliquer le profil au reste du kit Demi-Dieu (M1_2→M1_4, dash, 4
skills, ultimate), puis hitstop + VFX. La différenciation intra-kit devra rester
verte à chaque seed.

---

## 2026-08-30 — PAUSE — état exact pour la reprise

Arrêt propre au milieu du chantier « Demi-Dieu fini ». Rien n'est à mi-chemin :
les étapes 1 et 2 sont commitées, uploadées, câblées, vérifiées en moteur et
publiées. Aucune étape 3 ou 4 n'a été entamée.

### Fait (vérifié par le vrai chemin)

- **Étape 1 — dettes de doublons demidieu : fermées.** Minimum du kit
  **0.832 stud**, au-dessus du seuil de 0.8. Gate de différenciation vert.
- **Étape 2 — Jugement : corrigé.** Lit comme une garde (axe de fermeture
  mesuré, pas deviné). Garde fermée à 230 ms, dans la fenêtre de parade serveur.
- 4 animations réautorées, uploadées, câblées, `track.Length` mesuré en Play :
  `PasDivin` 0.433 · `Skill1_MainDuColosse` 0.699 ·
  `Skill3_MarcheDuTitan` 0.966 · `Skill4_Jugement` 0.566
- Patterns créés ce tour : `titan_charge`, `guard_cross`.
- Suite de tests **7/7**, gate intra-kit inclus.

### Reste à faire

- **Étape 3 — outil d'easing par courbe précalculée.** Bézier calculée nous-
  mêmes, matérialisée en **keyframes denses** (l'enum `PoseEasingStyle` de
  Roblox est trop pauvre : Cubic / Linear / Constant / Bounce / CubicV2 /
  Elastic, et les deux seuls à overshoot sont bannis pour les frappes). À
  **valider sur une seule animation d'abord**, vérifiée en moteur, avant toute
  généralisation.
- **Étape 4 — application au kit, ralenti à l'impact, traînée VFX.**
  Dispatchable en parallèle une fois l'outil éprouvé.

### QUESTION OUVERTE — à trancher à la reprise

**Faut-il inverser l'ordre et faire ralenti + VFX AVANT l'easing ?**

L'argument pour inverser :

- Le **ralenti à l'impact** et la **traînée VFX** ne vivent pas dans
  l'animation. Le ralenti est piloté au runtime (`HitstopController` et
  `TimeDilationController` existent déjà et sont audités) ; la traînée vient des
  packs VFX via `AnimationMarkerRouter`. Ce sont des passes **runtime**, réglées
  dans les données de marqueurs — **aucun ré-upload**.
- L'easing, lui, impose de ré-échantillonner et de **ré-uploader tout le kit**.
  Or `asphalt` a échoué 2 fois sur 3 en polling cette semaine sur un seul
  fichier. Dix animations × plusieurs itérations de réglage = le poste de risque
  n°1 du chantier.

Faire d'abord ce qui ne coûte pas d'upload donne un gain de ressenti immédiat et
garde le risque pour la fin. **Décision non prise — elle appartient à
l'utilisateur.**

### État de l'environnement

- Studio **ouvert**, Play **arrêté**, datamodel Edit actif. Rien fermé, aucune
  sauvegarde forcée.
- Place propre : aucun script temporaire à moi. Seul subsiste
  `ServerScriptService.__MCP_TestRunner`, qui appartient à l'outillage MCP.
- `rojo serve` **tourne** sur `127.0.0.1:34872`. Les serveurs HTTP local et
  rodeo sont arrêtés.
- **Attention à la reprise** : le plugin Rojo de Studio ne s'est pas reconnecté
  après le dernier redémarrage de Studio. Les sources ont été poussées dans la
  place par `GetAsync` depuis un serveur HTTP local. **Vérifier la synchro avant
  de juger quoi que ce soit** — c'est le piège qui a coûté une régression cette
  semaine.

Commit `ecb22d0`.

---

## 2026-08-30 — Kit Demi-Dieu : dettes fermées, garde corrigée (étapes 1-2/4)

Jalon intermédiaire du chantier « Demi-Dieu fini ». Étapes 1 et 2 livrées et
vérifiées ; l'outil d'easing (étape 3) est le prochain morceau.

### Étape 1 — les quatre dettes demidieu sont payées

| paire | avant | après |
|---|---|---|
| `M1_2` ↔ `Skill3_MarcheDuTitan` | **0.023** | **2.013** |
| `M1_1` ↔ `Skill1_MainDuColosse` | 0.063 | 2.439 |
| `Dash` ↔ `M1_1` | 0.123 | 2.550 |
| `Dash` ↔ `Skill1` | 0.179 | 0.832 |

**Minimum du kit : 0.832 stud**, au-dessus du seuil de 0.8. Le gate est vert sur
demidieu, et `test_known_debt_is_still_real` a exigé le retrait des quatre
entrées — la dette est payée, pas masquée.

Attributions : `Dash` → `front_palm_cast_v2`, `Skill1` → `two_handed_thrust_v2`
(deux mains : le poignet gauche bouge aussi, donc la silhouette change),
`Skill3` → `titan_charge` (**pattern dédié**).

`titan_charge` a été créé parce que **réutiliser une famille déjà prise dans le
kit ramène mécaniquement un doublon** — c'est la leçon des trois patterns
successifs de Marche du Titan : `dash_strike_v2` (doublon avec Main du Colosse),
`lead_hook_v2` (doublon avec M1_2, ma régression), `dual_arm_slash` (1.411 pour
un plancher WIDE à 2.00 — pattern jamais utilisé, donc jamais mesuré : la classe
WIDE se juge sur l'axe X, que `rz` ne produit pas).

### Étape 2 — Jugement lit enfin comme une garde

Première version de `guard_cross` : **échec**, confirmé en capture. Les bras
partaient en croix. Cause trouvée en **mesurant l'axe** au lieu de le deviner —
un axe à la fois depuis le repos, la méthode qui avait déjà résolu le bug d'axe
d'origine :

```
Right Shoulder rx = +90  ->  dx -2.000   (EN TRAVERS du corps)
Right Shoulder rz = +90  ->  dz -1.500, dy +1.500   (DEVANT, et haut)
Right Shoulder ry = +-90 ->  +-0.500     (negligeable)
```

J'avais mis `rx` **négatif**, ce qui écarte : poignets à `dx ±2.26` du torse.
Une garde se ferme avec **`rx` positif**. Corrigé à `rz 78 / rx 52` : poignets à
`dx ±1.07`, `dz −1.48` — devant, hauteur de poitrine, largeur d'épaules.

Timing choisi sur la mécanique, pas sur le gate : garde fermée à **230 ms**,
donc **dans** la fenêtre de parade de 0.25 s du module serveur. À 300 ms elle se
fermait après la fenêtre — le gate passait, le jeu était faux.

### Vérification

Les quatre slots résolus depuis `AnimationDB` (jamais un AssetId en dur),
chargés, `track.Length` mesuré en Play : 0.433 / 0.699 / 0.966 / 0.566 s. Casts
réels via `DashController.TryDash` et `CombatController.TrySkill`. Suite **7/7**.

### Reste à faire

Étape 3 : l'outil d'easing par courbe précalculée en keyframes denses, à valider
sur une seule animation en moteur avant généralisation. Étape 4 : application au
kit, ralenti à l'impact, traînée VFX.

Commit `6d7bf30`.

---

## 2026-08-29 (suite 12) — Gate de différenciation intra-kit, permanent

### 1. `M1_4_demidieu` ↔ `heavy_finisher_sukuna` : coïncidence, pas câblage

Vérifié avant de classer. Les deux specs sont **bien distinctes** — fichiers
séparés, `move_id` différents, archétypes différents (`demidieu` / `sukuna`),
durées 0.85 s vs 1.1 s, timings différents, hash MD5 différents. Aucun fichier
réutilisé, aucun câblage accidentel.

Elles partagent le **pattern** `overhead_chop`, et c'est suffisant pour produire
la même silhouette, parce que le système d'archétype est bien plus faible qu'il
n'en a l'air : `_resolve_key_poses` ne met à l'échelle que
`Right/Left Shoulder.rx`, **uniquement à la phase `contact`**, par un facteur
`0.70 + 0.30 × amplitude`. Soit 0.955 pour demidieu contre 0.970 pour sukuna —
et cette mise à l'échelle se voit bien dans les données (`rx` max 90.7 vs 92.2).

Mais le **pic** calculé par la métrique tombe sur l'**apex** (`rx = −75`, bras
haut), phase que l'archétype ne module **pas du tout** : les valeurs y sont
reprises verbatim du pattern. D'où **0.000000 stud**, à la précision machine.

**Conclusion : le pattern porte toute l'identité du geste ; l'archétype ne
différencie rien de visible.** C'est un constat de conception, pas un bug — mais
il explique pourquoi deux personnages différents peuvent frapper identiquement.

### 2. Le gate est implémenté et permanent

`scripts/animator_ai/kit_differentiation.py` — métrique validée :
positions d'effecteurs (poignets + tête) au pic **calculé**, en repère Torso,
distance = **max** des trois écarts, seuil **0.8 stud**, portée **intra-kit**.

Application **automatique**, condition posée :
`scripts/animator_ai/tests/test_kit_differentiation.py` découvre les kits en
groupant les specs par `archetype` — **aucun nom de personnage en dur**. Un
archétype ajouté demain est couvert sans toucher au fichier. Branché dans
`tests/run_all.sh` : la suite passe de 6 à **7/7**.

Le gate est aussi exposé depuis `stage4_gate_cascade.py` comme gate n°8, avec
la note expliquant pourquoi il ne peut pas entrer dans `run_cascade(animation)`
— il est **croisé**, il n'a pas de sens sur une animation isolée.

**Vérifié qu'il crie vraiment** : en retirant une entrée de dette, la suite
échoue avec le bon message et le bon chiffre. Un gate qui ne peut pas échouer ne
vaut rien.

### 3. Il a trouvé huit doublons — dont un que je venais de créer

| paire | distance | statut |
|---|---|---|
| `M1_2_demidieu` ↔ `Skill3_MarcheDuTitan` | **0.023** | **régression de ma part** |
| `M1_1_demidieu` ↔ `Skill1_MainDuColosse` | 0.063 | héritée |
| `Dash_demidieu` ↔ `M1_1_demidieu` | 0.123 | héritée |
| `M1_cross_toji` ↔ `dash_strike_toji` | 0.130 | héritée |
| `M1_jab_toji` ↔ `dash_strike_toji` | 0.152 | héritée |
| `M1_jab_toji` ↔ `M1_cross_toji` | 0.158 | héritée |
| `Dash_demidieu` ↔ `Skill1_MainDuColosse` | 0.179 | héritée |
| `M1_4_demidieu` ↔ `heavy_finisher_sukuna` | 0.000 | héritée |

**La première est une régression que j'ai introduite au tour précédent.** En
sortant Marche du Titan de `dash_strike_v2` pour casser son doublon avec Main du
Colosse, je l'ai posée sur `lead_hook_v2` — que **M1_2 utilisait déjà**. J'ai
échangé un doublon contre un autre, parce que je ne comparais que les 5
compétences et pas le kit entier (chaîne M1 et dash inclus). Le gate l'a attrapé
à sa toute première exécution.

Les sept autres sont antérieures. **Aucune n'est corrigée ici**, comme demandé :
elles sont nommées et datées dans `KNOWN_DEBT`, pas masquées en baissant le
seuil. Un second test, `test_known_debt_is_still_real`, fait échouer la suite si
une entrée n'est plus un doublon — la liste ne peut pas devenir un cimetière.

### Limite connue, dite plutôt que cachée

Le gate échantillonne **une** frame. Pour un overhead, le pic ainsi défini tombe
sur l'apex, précisément la phase que l'archétype ne module pas — c'est la raison
du 0.000000 ci-dessus. Une version ultérieure gagnerait à comparer **deux**
instants (apex ET contact) et à ne conclure au doublon que si les deux
coïncident. La version simple attrape déjà tout ce qui a été constaté.

Jugement n'est pas touché : sa pose ne lit pas comme une garde, c'est un
problème de conception, pas de duplication.

Commit `319031e`.

---

## 2026-08-29 (suite 11) — Doublons cassés + métrique de différenciation proposée

### Les deux doublons sont résolus

| paire | avant | après |
|---|---|---|
| Frappe Céleste ↔ Descente du Demi-Dieu | **0.000 stud** | **1.257** |
| Main du Colosse ↔ Marche du Titan | **0.148 stud** | **2.034** |

**Marche du Titan → `lead_hook_v2`.** Un crochet balaie latéralement : silhouette
franchement différente d'un direct, et « coup final orientable » s'accommode
mieux d'un arc que d'une ligne. Gates : classe hook 0.892 / 3.016, mouvement
0.138. `rx range [-72, 97]`.

**Frappe Céleste → `overhead_chop_planted`** (pattern créé). Gates : classe
overhead 0.891 / 3.241, mouvement 0.20. `rx range [-100, 103]`.

### Une voie essayée, mesurée, abandonnée

J'ai d'abord tenté un **écrasement à deux mains symétrique** (`two_handed_slam`).
Il plafonne à **2.27 stud** d'amplitude pour un plancher à 2.85, et la cause est
structurelle : le chop simple tire son amplitude de la **rotation du torse**, et
c'est précisément ce qu'un geste symétrique supprime. Remettre la rotation
restaure l'amplitude (3.016) mais casse la verticalité (ratio 0.698 pour 0.78,
`FAIL_SHAPE`). Le geste est coincé entre les deux — mesuré sur sept variantes,
pas supposé.

D'où `overhead_chop_planted` : le bras **droit** garde le chop qui passait déjà,
seuls le bras **gauche** (qui descend et s'ancre au lieu de rester en garde) et
le pitch changent. Suffisant, puisque la métrique mesure les **effecteurs** et
que le poignet gauche en est un.

Correction en cours de route, trouvée en ouvrant l'image : un pitch de
`RootJoint` à −42 faisait basculer tout le corps de 45° — ça lisait comme une
**chute en avant**, pas un écrasement. Ramené à −26.

### La métrique proposée (à valider — non implémentée)

Voir le rapport de ce tour. En bref : **distance au pic entre positions
d'effecteurs, dans le repère du Torso**, seuil proposé **0.8 stud**, portée
**intra-kit**.

Calibrage sur le corpus réel (16 animations) :

- doublons constatés : 0.000 (Frappe Céleste ↔ ultime), 0.148 (Main du Colosse
  ↔ Marche du Titan), et **deux autres déjà présents** que personne n'avait
  vus : `M1_4_demidieu` ↔ `heavy_finisher_sukuna` à **0.000**, `M1_jab_toji` ↔
  `M1_cross_toji` à **0.158** ;
- paire légitime la plus serrée **dans un même kit** : `M1_3` ↔ `M1_4` à
  **1.107**.

Le seuil à 0.8 attrape les quatre doublons et laisse 1.107 tranquille avec 27 %
de marge. La fenêtre est large, ce n'est pas un réglage au millimètre.

Commit `d4e8fcf`.

---

## 2026-08-29 (suite 10) — Les 5 gestes photographiés à leur pic réel

Cinq captures, chacune figée à l'instant le plus lisible du clip, chacune
ouverte et jugée. Trois défauts de lisibilité trouvés — tous des problèmes de
**différenciation**, pas d'échec technique : les cinq passent les gates.

### Méthode — viser, pas capturer au hasard

Une capture met 1–2 s à partir : viser 0,244 s au vol est impossible. Le clip
est donc **figé** (`track:AdjustSpeed(0)` puis `TimePosition`), chargé par le
vrai slot `AnimationDB`. La pose photographiée est exactement celle du clip.

Deux corrections en cours de route, l'une et l'autre trouvées en regardant :

1. **Angle de caméra faux.** Mon premier offset avait un `+Z`, or l'avant du
   personnage est `−Z` : la caméra était *derrière* lui et le coup partait loin
   de l'objectif. Corrigé en vue de profil / trois-quarts avant.
2. **Instant deviné au lieu d'être mesuré.** J'ai d'abord visé le marqueur
   `HitConnect` (0.30) — à côté du pic. Les pics ont ensuite été **calculés sur
   les données du clip** : extrême de `rz` pour un direct, de `rx` pour un
   overhead.

| geste | pic mesuré | ce qu'il est |
|---|---|---|
| Main du Colosse | **0.244 s** | `rz` +90, extension avant maximale |
| Frappe Céleste | **0.277 s** | `rx` +103, écrasement |
| Marche du Titan | **0.655 s** | `rz` +92, frappe finale |
| Jugement | 0.30 s | posture engagée |
| Descente du Demi-Dieu | **0.583 s** | `rx` +103, écrasement |

### Mon jugement, franchement

**Main du Colosse — lit bien.** Bras à l'horizontale en pleine extension, torse
engagé, tête derrière le bras. C'est un direct propre et sans ambiguïté.

**Marche du Titan — lit bien, mais quasi identique à Main du Colosse.** Les deux
sont de classe *straight* (`rear_hand_straight_v2` et `dash_strike_v2`) et leurs
poses de contact se ressemblent au point qu'on ne les distingue pas à l'arrêt.
La différence est dans le déplacement, qu'une image fixe ne montre pas — mais en
combat, au moment du contact, un joueur aura du mal aussi.

**Frappe Céleste — passable, pas « céleste ».** Ça lit comme un coup diagonal
descendant avec tout le corps qui bascule vers l'avant, pas comme une hache
verticale venue du ciel. Cause identifiée : sur ce rig `rx = −100` monte le bras
**et le ramène en travers de la poitrine** (`rx = −90` → `dy +2.000` mais aussi
`dx +1.000`). L'apex ne met donc jamais le bras au-dessus de la tête. Le gate est
satisfait (3.213 stud de chute sur Y) — mais le gate mesure une chute, pas une
verticale.

**Descente du Demi-Dieu — identique à Frappe Céleste.** Même pattern
`overhead_chop_v2`, même pose au pic. Un ultime qui ressemble à une compétence
ordinaire rate son travail.

**Jugement — le plus faible.** Ça lit comme des bras qui s'ouvrent vers
l'extérieur, un haussement d'épaules ou un cast — **pas une garde**. Une posture
de contre aurait les bras remontés et fermés devant. `wide_open_cast` ouvre vers
l'extérieur et vers le bas : le gate de mouvement passe (les bras bougent), mais
le *sens* est faux.

### Ce que ça dit du chantier

Les cinq sont techniquement livrés et vérifiés. Mais **trois sur cinq ne portent
pas encore leur intention** : deux paires se confondent, et Jugement ne dit pas
ce qu'il fait. C'est un problème de **vocabulaire de patterns**, pas de
pipeline : on n'a que trois familles de gestes pour cinq compétences. Il faudra
des patterns dédiés — une vraie garde fermée, un overhead réellement vertical —
avant que le kit se lise.

Commit `b633f38`.

---

## 2026-08-29 (suite 9) — Les 5 slots sortent de PENDING_UPLOAD

`[AnimLoader] All slots uploaded ✓` — plus aucun `PENDING_UPLOAD` dans le kit
Demi-Dieu. Le PlaytestReporter passe de 4–5 avertissements à **0**.

| slot | pattern | gate classe | gate mouvement | `rx range` | longueur moteur |
|---|---|---|---|---|---|
| Skill1_MainDuColosse | `rear_hand_straight_v2` | 0.942 / 3.987 | 0.19 | **[0.0, 0.0]** | 0.699 s |
| Skill2_FrappeCeleste | `overhead_chop_v2` | 0.871 / 3.213 | 0.24 | [−100, 103] | 0.833 s |
| Skill3_MarcheDuTitan | `dash_strike_v2` | 0.932 / 3.819 | 0.138 | **[0.0, 0.0]** | 0.966 s |
| Skill4_Jugement | `wide_open_cast` | **exempté** | 0.30 | [14, 86] | 0.666 s |
| Ultimate_DescenteDuDemiDieu | `overhead_chop_v2` | 0.945 / 3.213 | 0.171 | [−100, 103] | 1.166 s |

`rx range [0.0, 0.0]` sur les deux seeds de classe *straight* : la course avant
est bien sur `rz`. Le bug d'axe du 2026-08-28 n'est pas réintroduit. Sur les
overhead, `rx` est l'axe correct (Y) — le contrôle systématique sert justement à
distinguer les deux cas au lieu de « corriger » par réflexe.

### Deux refus de facilité

**`overhead_chop` donnait 2.853 stud pour un plancher à 2.85** — 0.1 % de marge.
Ce n'est pas un échec, mais c'est le profil exact des seeds qui ne passaient que
grâce au clamp dur et ont produit le tortillement. Nouveau pattern
`overhead_chop_v2` (apex plus haut, contact plus bas, pitch de RootJoint plus
marqué) : **3.213, soit 12.7 % de marge**. L'original est intact.

**`Skill3` a été REJETÉ par le gate de mouvement** : figé 0.467 s, 48 % du clip
(max 40 %). Allonger le clip à 1.25 s le faisait passer — et c'était du **gaming
de métrique** : la demi-seconde morte restait, en absolu, identique. Refusé. La
vraie cause était la phase `windup → impact` de 500 ms sans pose intermédiaire ;
`windup_ms` porté de 200 à 520 la supprime pour de bon (**0.133 s**) et colle à
l'intention : deux pas lourds, puis la frappe qui s'engage tard.

Même levier sur l'ultime, qui passait à **0.400 pile** — la limite exacte, trop
juste pour être crédible. `windup_ms` 150 → 430, résultat 0.171.

### Jugement — exemption appliquée

Décision actée : `Skill4_Jugement` est une **posture de contre**, pas une
frappe. Le gate de classe mesure où va le poignet le long d'un axe de frappe ;
appliqué à une garde il mesure la mauvaise chose — même erreur de catégorie que
`strike_classes.py` a été écrit pour corriger. **Gate de mouvement seul**, et il
reste pertinent : une posture doit bouger, sinon c'est une pose figée. PASS à
0.30.

### Vérification, deux fois par le vrai chemin

1. Slot résolu depuis `AnimationDB` (jamais un AssetId en dur), chargé,
   `track.Length > 0.1` — un `LoadAnimation` réussi ne prouve rien.
2. Cast via `CombatController.TrySkill(1..5)`, l'appel exact d'`InputController`.
   Le runtime a logué `playing:` pour les cinq, avec les bonnes longueurs.

Piège re-confirmé au passage : une tentative de cast via `execute_luau` a donné
« PAS JOUÉ » sur les cinq — le `require` isolé rend un `CombatController` dont
`_character` est nil. Seul un vrai `LocalScript` compte.

Les 5 entrées sont dans `verified_assets.json` en `VERIFIED`, avec les preuves.

Commit `449c798`.

---

## 2026-08-29 (suite 8) — Skill1_MainDuColosse sort de PENDING_UPLOAD (1/5)

Premier des 5 slots d'animation restants passé de bout en bout. La chaîne est
prouvée sur un cas réel ; les 4 autres suivent le même rail.

### Chaîne complète, un seed

| étape | résultat |
|---|---|
| spec autorée | `hand_keyer/specs/Skill1_MainDuColosse.json`, pattern `rear_hand_straight_v2` |
| hand_keyer | 22 frames, 0.7333 s — `Right Shoulder rx range [0.0, 0.0]` |
| gate **classe** (straight) | ratio **0.942** (plancher 0.67), amplitude **3.987 stud** (plancher 2.25) — **PASS** |
| gate **mouvement** | plage statique **0.19** (max 0.40), rotation totale 290° — **PASS** |
| bake | `assets/animations/handkeyer/Skill1_MainDuColosse.rbxm`, 3 517 o |
| upload | asphalt Open Cloud → `rbxassetid://73293100136338` |
| câblage | `AnimationDB/Skills.lua`, vrai slot |
| **vérification moteur** | par le **vrai slot**, `track.Length = 0.699 s` |
| **cast réel** | `[AnimationDriver] playing: Skill1_MainDuColosse (len=0.70)` |

`rx range [0.0, 0.0]` n'est pas cosmétique : c'est la preuve que le bug d'axe
corrigé le 2026-08-28 sur 7 seeds n'est pas réintroduit. La course avant est bien
pilotée sur `rz`.

Les marges sont larges (0.942 / 3.987 contre 0.67 / 2.25) : le seed passe par sa
propre qualité, pas sauvé par une amplification poussée au clamp — c'est
exactement ce qui avait produit le tortillement de M1_2/3/4.

`[AnimLoader] 4 slot(s) still PENDING` — de 5 à 4, confirmé par le runtime.

### Vérification par le vrai chemin, deux fois

1. Résolution du slot depuis `AnimationDB` (jamais un AssetId en dur), chargement,
   puis `track.Length > 0.1`. Un `LoadAnimation` qui réussit ne prouve rien —
   règle du projet, respectée.
2. Cast via `CombatController.TrySkill(1)`, l'appel exact d'`InputController`
   sur F. Le runtime a joué l'animation.

### Restent 4, et un cas de conception à trancher

`Skill2_FrappeCeleste` (overhead), `Skill3_MarcheDuTitan` (dash + coup final),
`Ultimate_DescenteDuDemiDieu` (overhead) entrent dans le moule des gates.

**`Skill4_Jugement` est un vrai cas à part** : c'est une **posture de contre**,
pas une frappe. Le gate de classe mesure où va le poignet le long d'un axe de
frappe — appliqué à une garde, il mesure la mauvaise chose. Deux options
honnêtes : le classer `wide` (« bras qui s'ouvrent depuis neutre », ce qu'une
garde fait réellement), ou l'exempter du gate de classe et ne lui appliquer que
le gate de mouvement, qui reste pertinent (la posture doit BOUGER). À trancher
avant de l'autorer, pas pendant.

### Note d'environnement

Rojo n'était plus lancé et Studio avait redémarré ; le plugin Rojo ne se
reconnecte pas seul. Les sources sont poussées dans la place par `GetAsync` sur
un serveur HTTP local, à l'octet près depuis le disque — le disque reste la
source de vérité.

Commit `b29fc91`.

---

## 2026-08-29 (suite 7) — Retouches HUD : glyphes F et H, étiquettes de barres

Trois défauts signalés par Milan à l'écran, corrigés et vérifiés en capture.

**Glyphe F (Main du Colosse)** — lisait comme une tache. Un poing se reconnaît à
trois choses : la masse fermée, les phalanges en dents, l'avant-bras qui part
derrière. Les trois y sont maintenant. Piège évité au passage : ma première
version creusait les phalanges avec des barres couleur-de-fond — or la
désaturation en cooldown repeint **tous** les enfants du glyphe, les creux
seraient devenus gris au lieu de disparaître. Tout est dessiné en positif.

**Glyphe H (Marche du Titan)** — lisait comme deux points, sans direction. Deux
empreintes maintenant, semelle + talon détaché chacune, décalées en diagonale et
inclinées : le pas et son sens.

**Étiquettes de barres** — « rien ne distingue le cyan du violet sans le savoir
déjà ». `PV` / `STA` / `MOM` dans une gouttière de largeur fixe à gauche des
pistes, à chasse fixe donc alignées. Pas de texte *sous* la barre : ça aurait
fait grossir le panneau et serait passé sous les ~11 pt que la direction
visuelle interdit (§6).

### Une désynchro attrapée avant de conclure

La première capture ne montrait **ni** les étiquettes **ni** les nouveaux
glyphes. Réflexe du projet : vérifier la synchro avant d'accuser le code.
`rojo serve` ne tournait plus (Studio avait été redémarré, nouvel id d'instance)
et le plugin Rojo ne se reconnecte pas tout seul. La source exacte du disque a
été poussée dans la place via un `GetAsync` sur un serveur HTTP local — pas de
réécriture, pas d'échappement, 29 158 octets identiques au disque. Vérifié dans
la place avant de recapturer.

C'est exactement l'erreur de M1_2/3/4 de la semaine dernière, évitée cette fois
parce que le contrôle de synchro passe avant le jugement.

Commit `390abcc`.

---

## 2026-08-29 (suite 6) — Respawn (§2) vérifié, compteur de kills (§3) livré

### §2 Respawn — déjà implémenté, donc vérifié plutôt que réécrit

Première chose faite : **lire avant d'écrire**. `ArenaBootstrap.server.lua` fait
déjà tout ce que la spec demande — `hum.Died:Once` → `task.delay(3)` →
`LoadCharacter` → placement round-robin sur les pads, face au centre. Aucune
pénalité nulle part. Rien à construire.

Vérifié aussi qu'il n'y a **pas de respawn concurrent** : `RaceClassService` en
contient un second, mais `ServiceLoader` est retiré du chemin V1
(`init.server.lua`), donc il ne tourne pas. Pas de double `LoadCharacter`.

**Vraie mort, vrai cycle** (`Health = 0` côté serveur déclenche `Died` ; jamais
d'appel direct à `LoadCharacter`), 3 cycles :

| cycle | pad avant | pad après | distance au pad | délai | vie |
|---|---|---|---|---|---|
| 1 | Spawn_1 | Spawn_2 | **0.00** | 3.08 s | 100/100 |
| 2 | Spawn_2 | Spawn_3 | **0.00** | 3.02 s | 100/100 |
| 3 | Spawn_3 | Spawn_4 | **0.00** | 3.02 s | 100/100 |

Les 8 pads sont bien là, le round-robin avance, le placement est exact.

**Re-bind du HUD sur le vrai cycle** : le HUD courant est lié au 4ᵉ `Humanoid`,
né d'une vraie mort. Des dégâts serveur lui sont appliqués et la barre suit à
chaque échantillon — vie 42 → 51, **écart max 0**. Un HUD resté accroché à
l'ancien `Humanoid` détruit n'aurait pas bougé.

Note de méthode : ma première sonde a renvoyé un « écart 0 » qui ne prouvait
rien — les dégâts n'étaient pas passés (écouteur armé après le tir). J'ai ajouté
un drapeau `degats_ont_bien_ete_appliques` avant de croire le chiffre.

### §3 Compteur de kills — session uniquement

Roblox ne transporte aucune attribution : `TakeDamage` ne dit pas qui frappe.
L'attribution est donc posée à la main **à chaque site qui inflige réellement
des dégâts** : `DamageService.Apply` (tout le M1) et les 4 modules de skills qui
tapent en direct sans passer par lui (choix antérieur documenté dans
`Skill4_Jugement.lua`). Fenêtre de crédit de 8 s, sinon on hériterait d'un kill
pour un coup porté une minute plus tôt ou pour une chute.

Vérifié par le vrai chemin — `TryM1` en boucle (l'appel exact d'`InputController`
au clic), dégâts via `CombatService` → `DamageService` :

| essai | mannequin | mort | kills après |
|---|---|---|---|
| 1 | TrainingDummy | oui | **1** |
| 2 | TrainingDummy_1 | oui | **2** |
| 3 | TrainingDummy_2 | oui | **3** |

Le HUD affiche « 3 KILLS ». Pas de leaderboard, pas de DataStore, pas de
persistance — le total meurt avec la session, comme demandé.

**Choix assumé** : les mannequins comptent. Dans une arène de combat libre à un
seul joueur connecté, un compteur qui reste à zéro ne serait ni vérifiable ni
utile. Une ligne à changer dans `onDied` si ça doit devenir joueurs-seulement.

### Un bug trouvé par la capture

La barre de **momentum à 0 pulsait en rouge** comme une vie mourante : mon seuil
critique s'appliquait à **toutes** les barres. Or « critique » est une notion de
vie — un momentum vide est l'état normal. Restreint à la vie
(`criticalEnabled`). Encore un défaut que seul le fait de regarder l'image
révèle.

### Fichiers

- `src/server/V1/KillCounterService.lua` — nouveau, attribution + total session
- `src/server/V1/DamageService.lua` — crédit sur le chemin M1
- `src/server/Skills/{Skill1,Skill2,Skill3,Ultimate}` — crédit sur leurs dégâts
- `src/server/V1/ArenaBootstrap.server.lua` — init du service
- `src/shared/UI/HudView.lua` — compteur + correctif du seuil critique
- `src/client/UI/HUD.client.lua` — écoute `Remotes/HUD/KillCount`

Captures : `respawn-avant`, `respawn-apres`, `kills-compteur`.

Commit `caa2036`.

---

## 2026-08-29 (suite 5) — Direction visuelle du HUD implémentée, 6 étapes, capture à chaque

Première fois que le projet itère sur du visuel **en jugeant les images**, étape
par étape, sans attendre personne. Sept captures en jeu, toutes ouvertes et
regardées, toutes publiées.

### Ce que chaque étape a donné

**1 — Couper l'UI native.** Barre de vie verte, liste de joueurs et chat :
**partis**. Reste le bouton Roblox/menu : `SetCore("TopbarEnabled", false)` est
accepté (le pcall réussit, aucun avertissement) mais **n'a plus aucun effet** —
la topbar est toujours là sur la capture. Roblox impose ce bouton. Documenté
dans le code pour qu'on n'y revienne pas en croyant à un bug.

**2 — Contraste inversé sur les chips.** Avant : le chip était allumé et une
ombre le mangeait. Maintenant : le chip s'éteint et un **liseré violet vif
grandit le long du bord bas**. Sur la capture, on lit d'un coup d'œil quelles
compétences sont prêtes — c'était le défaut n°1, constaté deux fois. Plus flash
blanc-violet + pop d'échelle (1 → 1.08 → 1) au retour à disponible.

**3 — Libellés supprimés, glyphes + grosse lettre.** Les noms complets à 9 pt
disparaissent. Six silhouettes géométriques (traits de vitesse, poing, chevron
au sol, appuis, losange, double chevron) construites **en Frames** : le projet
interdit d'inventer un AssetId, donc pas d'icônes en image. Lettre de touche
18 → 22 px.

**4 — Aura de Momentum en bord d'écran.** Quatre bandes à dégradé + particules
montantes au cap, `ZIndex 0` derrière le HUD. Tier 0 = rien et **immobile**.
Première version trop discrète (l'arène est elle-même bleu/violet), renforcée,
puis **resserrée en étape 6** parce qu'elle lavait l'écran au lieu de le cadrer.

**5 — Vie physique.** Éclat d'impact (0,12 s, plus court que le fantôme à
0,35 s), pointe chaude en dégradé sur les trois barres, seuil critique sous 25 %
avec contour rouge pulsant. Capture prise à 8 PV : le contour rouge et l'éclat
sont tous deux visibles.

**6 — Harmonisation.** Un seul rayon, une seule épaisseur, un seul accent.
Chiffres en `RobotoMono` (chasse fixe) pour que le HUD ne tremble pas au
décompte. Aura resserrée. Éclat d'impact reparenté au remplissage.

### Deux bugs trouvés *par* les captures

- **Le HUD mentait** : la barre affichait « 100 » à 99,6 (arrondi) pendant que
  le test d'armement de l'ultime utilise `>= max` — chip verrouillé, barre à
  100. Corrigé en `math.floor`. Repéré uniquement parce que j'ai regardé
  l'image.
- **L'éclat d'impact blanchissait toute la piste**, y compris la portion vide,
  rendant la barre illisible au moment où elle compte le plus. Reparenté au
  remplissage.

### Réserve honnête sur la direction

La **coupe diagonale** demandée au §5 n'est pas implémentée : Roblox ne sait pas
découper un polygone arbitraire sans masque en image, et le projet interdit
d'inventer un AssetId. Ce qui est unifié l'est sur ce qui est réellement
contrôlable — rayon, épaisseur, accent. La coupe demandera une vraie texture
uploadée et vérifiée.

### Mon jugement sur l'image finale

Ce qui marche : les liserés de disponibilité se lisent sans lire, les décomptes
monospace ne gigotent plus, l'aura cadre l'écran au lieu de le laver, le seuil
critique est net.

Ce qui reste faible : le glyphe **poing** (F) lit comme une tache, le glyphe
**appuis** (H) comme deux points — ce sont les deux moins reconnaissables des
six. Et les trois barres n'ont aucune étiquette : un joueur neuf ne sait pas
laquelle est la stamina.

Le HUD reste du **rendu pur** : aucune autorité ajoutée, la règle §1 est intacte.

Captures : `artifacts/visual_checks/2026-08-29_hud-play.png` (avant) puis
`hud-etape1` à `hud-etape6-final`.

Commit `dfeac2b`.

---

## 2026-08-29 (suite 4) — Enregistrement d'écran accordé : première capture en jeu

Milan a coché la permission. Elle a pris effet **sans redémarrer Claude** —
contrairement à ce que je craignais.

### Aucune boîte de dialogue : macOS ne la repropose jamais

Les trois déclencheurs ont échoué avant l'octroi manuel :

| tentative | résultat |
|---|---|
| `screencapture -x -o -l 90` | `could not create image from window`, aucun fichier |
| `CGWindowListCreateImage` | `None` |
| `CGRequestScreenCaptureAccess()` — l'API explicite | **`False`**, sans rien afficher |

Une demande déjà présentée et refusée une fois n'est jamais reproposée. Il
fallait passer par Réglages Système, comme pour l'Accessibilité.

### Vérifié par le contenu, pas par la taille

`CGPreflightScreenCaptureAccess()` → **`True`**.

Puis capture de la fenêtre Studio, **ouverte et regardée** : on y voit la barre
de titre « MyAnimeMMORPG — Roblox Studio », le ruban Home, le panneau Explorer,
la barre de commande et le viewport 3D. C'est bien la fenêtre, pas un fond
d'écran.

C'est le contrôle que j'avais sauté deux fois. Cette fois il est fait.

### Première vérification visuelle dynamique du projet

Capture en **mode Play, jeu en train de tourner** — onglets Client/Server,
bordure Play, HUD par-dessus l'arène avec des valeurs vivantes
(vie 85, stamina 100, momentum 21, Jugement à « 2 » en cooldown).

`artifacts/visual_checks/2026-08-29_hud-play.png`, publiée sur le miroir.

### Nouvel outil : `scripts/visual_check/capture_window.py`

Voie **A**, désormais la voie par défaut : capture la fenêtre Studio au niveau
macOS, donc **en Play**, contournant entièrement `CaptureService`. La voie Edit
livrée au tour précédent devient le repli.

Le script ne juge **pas** par la taille du fichier. Il s'appuie sur une
propriété plus forte : `screencapture -l <windowID>` ne compose que la fenêtre
demandée — permission refusée, il échoue franchement et n'écrit rien, il ne
peut pas retomber sur le fond d'écran. Il vérifie en plus que les dimensions
correspondent à la fenêtre. Et il imprime, à chaque run, que **le seul contrôle
qui compte est d'ouvrir l'image**.

### Ce que je vois moi-même sur la capture en jeu

- **Le balayage de cooldown est trop peu contrasté** — confirmé en jeu, pas
  seulement sur la maquette Edit. Le chiffre porte toute l'information ; le
  remplissage sombre-sur-sombre ne se lit pas.
- **Deux UI Roblox par défaut polluent l'écran** : la barre supérieure (logo,
  menu, chat) en haut à gauche, et surtout **la barre de vie verte native en
  haut à droite**, qui double la nôtre et se voit plus qu'elle. À désactiver
  (`StarterGui:SetCoreGuiEnabled`).
- **Le HUD est petit à l'échelle réelle** ; les libellés à 9 pt sont limites.
- Le contraste violet du HUD tient bien sur l'arène bleu/violet.
- **Le momentum retombe vite** : 100 → 21 le temps de quelques casts. C'est
  correct (skill dans le vide = −10, puis décroissance 8/s), mais c'est un sujet
  de ressenti à trancher.

Rien de tout ça n'est corrigé : ce tour portait sur l'outil de vérification.

### Dépendance ajoutée

`~/.cache/myanimerpg/capture-venv` — venv isolé avec `pyobjc-framework-Quartz`,
hors du Python système, uniquement pour trouver l'ID de fenêtre et interroger la
permission. Supprimable ; les scripts disent comment le recréer.

Commit `f74aebc`.

---

## 2026-08-29 (suite 3) — Vérification visuelle autonome : résolue

« Milan regarde à l'écran » n'est plus la seule voie. Procédure répétable,
scriptée et versionnée : `scripts/visual_check/`.

### Ce qui marche — capture en mode Edit, avec le vrai HUD

Découverte décisive : **un `ScreenGui` parenté à `StarterGui` est rendu dans le
viewport de l'éditeur**, donc il apparaît dans une capture Edit — laquelle
fonctionne (contrairement à Play). Le HUD est donc jugeable sans présence
humaine et sans mode Play.

Pour que l'image vaille quelque chose, elle doit montrer **le vrai HUD**, pas un
sosie reconstruit dans un harnais. D'où le refactor : tout est bâti par
`src/shared/UI/HudView.lua`, partagé par les deux appelants —
`HUD.client.lua` (dans `PlayerGui`, vraies sources serveur) et
`hud_scene.luau` (dans `StarterGui`, valeurs injectées). Le harnais change les
**valeurs**, jamais la mise en page, la palette ni la géométrie.

**Refactor revérifié en jeu par le vrai chemin** : écart vie **0** sur deux
dégâts serveur, 3 barres, 6 chips, cooldown Skill1 réel armé via le remote
(4,7 s déduites pour 5). Le refactor n'a rien cassé.

Pipeline validé de bout en bout : scène montée → capture → `pull_capture.py` →
`REELLE, 1 283 104 octets` → rangée dans `artifacts/visual_checks/`.

### Le garde-fou, vérifié dans les deux sens

`pull_capture.py` juge **par la taille du fichier**, jamais par un code de
retour. Testé : il range une capture Edit (1,28 Mo) et **refuse** une capture
Play (8 549 octets, exit 1, rien rangé).

Mesures sur cette machine, toutes captures en `2462x1176` :

| | taille |
|---|---|
| image réelle | 1,28 – 1,77 Mo |
| frame noire | **8 549 octets** |

### Une erreur à moi, corrigée — et c'est la leçon du tour

Le 2026-08-27 j'avais publié une « correction » affirmant que l'Enregistrement
d'écran macOS **était accordé**, sur la seule foi d'un PNG de 8,7 Mo. J'ai refait
exactement la même erreur ce tour-ci avec un PNG de 9,2 Mo — avant d'ouvrir
l'image : ce ne sont que **le fond d'écran et la barre de menus, sans aucune
fenêtre**. C'est précisément ce que macOS produit quand la permission est
**refusée**.

Confirmé par un test que la taille ne peut pas masquer :
`screencapture -l <windowID>` sur la fenêtre principale de Studio répond
`could not create image from window` et n'écrit rien.

La ligne d'origine était donc juste, et ma correction était fausse.
`artifacts/STUDIO_PLUGINS_DIAG_2026-08-27.md` §5 est rectifié.

**Leçon, la même que pour `pcall(LoadAnimation)` : un proxy qui a l'air bon ne
vaut pas une vérification du contenu.** Une taille de fichier ne prouve pas
qu'une image montre quelque chose.

### Les quatre pistes, résultat de chacune

| piste | état | raison |
|---|---|---|
| 1. `screencapture` macOS | **bloquée** | permission Enregistrement d'écran refusée à `/Applications/Claude.app`. Une case à cocher humaine la débloquerait. |
| 2. Mode Run | **non testable** | le MCP n'expose que Play (`is_start`) ; déclencher Run demande l'UI de Studio, inaccessible sans Accessibilité. |
| 3. Hors viewport | **non nécessaire** | la piste 4 a abouti avant. |
| 4. **Reconstituer en Edit** | **RETENUE** | fonctionne, et fidèle grâce au module partagé. |

Écarté aussi : `rodeo exec` (le serveur démarre, le plugin Studio ne s'y
connecte pas, `exec` sort sans rien produire).

Note d'environnement : la fenêtre Studio est bien à l'écran et non minimisée
(`kCGWindowIsOnscreen = True`, 1440×814) — ce n'était donc pas ça non plus.

### Livrables

- `src/shared/UI/HudView.lua` — construction du HUD, sans source de données
- `src/client/UI/HUD.client.lua` — n'a plus que le câblage aux autorités
- `scripts/visual_check/hud_scene.luau` — harnais de mise en scène Edit
- `scripts/visual_check/pull_capture.py` — récupération + jugement par octets
- `scripts/visual_check/README.md` — procédure, pièges, et ce qui ne marche pas
- `artifacts/visual_checks/2026-08-29_hud.png` — première image, publiée

### Limite honnête

C'est une capture **statique en mode Edit**. Elle montre fidèlement la mise en
page, la palette, la lisibilité et les états demandés. Elle ne montre **pas** le
mouvement, ni le ressenti d'une transition, ni ce qui n'existe qu'en jeu. Pour
ça, un œil humain en Play reste nécessaire.

Commit `0151cc8`.

---

## 2026-08-29 (suite 2) — Capture noire : diagnostic dédié, cause localisée

Deux chantiers d'affilée bloqués sur la vérification visuelle. Diagnostic plutôt
qu'un contournement de plus. Rapport complet :
`artifacts/DIAGNOSTIC_CAPTURE_2026-08-29.md`.

### Verdict

**La capture n'est pas cassée.** Elle marche en **Edit** et rend du noir en
**Play**, de façon reproductible et réversible — même fenêtre, même viewport, à
deux minutes d'écart :

| # | mode | résultat |
|---|---|---|
| 1 | Edit | **image réelle** |
| 2 | Play | **noir** |
| 3 | Play | **noir** |
| 4 | Edit (après arrêt) | **image réelle** |

### La preuve la plus nette : la signature disque

`~/Library/Roblox/tmp-capture-storage/`, en-têtes PNG lus directement :

```
wob-...057  2462x1176   1 743 193 o   Edit  — réelle
wob-...058  2462x1176       8 549 o   Play  — noire
wob-...059  2462x1176       8 549 o   Play  — noire
wob-...060  2462x1176   1 766 751 o   Edit  — réelle
wob-...062  2462x1176       8 549 o   Play  — noire (CaptureService moteur)
```

Les cinq font **2462×1176** = `1231×588` en Retina 2×. **La surface noire est
plein-format** : allouée, bien dimensionnée, simplement jamais dessinée. Une
surface « collapsée » ne produirait pas ça.

### Cinq hypothèses éliminées par la mesure

- **Seuil viewport 600 px** — le viewport est à 588, sous le seuil documenté,
  mais **Edit réussit à cette exacte taille**. Pas la variable.
- **Veille écran / économiseur / verrouillage** — `CurrentPowerState = 4`,
  `UserIsActive = 1`, aucun `ScreenSaverEngine`, et **état identique** entre le
  succès et l'échec.
- **Focus / espace macOS** — pilotage distant, Studio n'est pas l'app active, et
  **les captures Edit réussissent quand même**.
- **Queue morte pour la session** — Edit réussit **immédiatement après** deux
  Play noires, sans redémarrage.
- **Overlay GUI / Lighting / bug de l'outil MCP** — aucun overlay opaque,
  Lighting normal, et `CaptureService` du **moteur** donne le même noir.

### Une conclusion intermédiaire que j'ai dû corriger

J'avais écrit en cours de diagnostic que `CaptureService` « fonctionne en Play »
parce que son callback part en 0,41 s. **Faux** : le callback part, l'image est
noire. Le callback ne prouve rien sur le contenu — même piège que
`pcall(LoadAnimation)` qui renvoie `ok` sur un AssetId invalide. Vérifier la
**taille du fichier** (≈8,5 Ko = noir).

### Ce qui est établi

Le moteur **rend normalement** en Play (`RenderCPUFrameTime ≈ 0.0154`, ~65 fps).
En Play, la vue affichée à l'écran et la surface offerte à la capture ne sont
donc pas la même chose, et la seconde n'est jamais dessinée.

### Ce que je n'ai pas élucidé — dit clairement

**Pourquoi la régression est apparue.** Les captures Play marchaient le
2026-08-27 (vérifié, pas supposé : la capture publiée montre le personnage
joueur et les plaques « Training Dummy » avec barres de vie, GUI de runtime). Or
rien de local n'a changé après : Studio.app date du **26 août**, tous les
plugins d'avant le 27. L'outil de capture vit dans l'Assistant intégré à Studio,
qui s'auto-met à jour et n'est pas datable depuis le disque.

Je m'arrête là plutôt que de continuer à retenter, comme demandé.

**Piste probable, non vérifiée** : un back-buffer Play jamais composé quand
Studio n'est pas l'app active, là où le chemin Edit sait redessiner à la demande.
Testable en une manipulation humaine (Studio réellement au premier plan, vue 3D
visible, Play, puis capture) — impossible pour moi : `osascript` n'a pas l'accès
d'aide sur cette machine (`-25211`), la même permission qui bloque le Cmd+S.

### Mémoire projet corrigée

La note `captureservice-viewport-bug` portait deux affirmations que ce
diagnostic réfute par la mesure (seuil 600 px, queue morte pour la session).
Réécrite avec les faits mesurés.

Commit `ab83848`.

---

## 2026-08-29 (suite) — Nouveau chantier : HUD V1, vérifié en Play Solo

Premier vrai contenu visible du jeu. Élément 1 sur 3 (HUD → respawn → compteur
de kills). **En attente du jugement visuel de Milan devant l'écran** avant de
passer au respawn.

### Le vrai problème à régler d'abord : aucun canal de cooldown n'existait

Trois autorités serveur possèdent les cooldowns aujourd'hui, et aucune ne les
publiait :

- `CombatService.server.lua` — Skill1..Skill5, via `state.skillCooldowns`
  contre `MoveData[moveId].serverCooldown`
- `DashService.server.lua` — Pas Divin, via `DashCooldown`
- chaque module de `src/server/Skills/` — sa propre constante `COOLDOWN`

Un HUD qui aurait chronométré lui-même aurait été une **quatrième** autorité,
condamnée à diverger des trois autres. Vérifié au passage : les constantes des
modules correspondent exactement aux `serverCooldown` (5 / 6 / 10 / 12), donc il
n'y a pas de contradiction à arbitrer.

Nouveau `src/server/V1/HudFeed.lua` : au moment **exact** où le service
propriétaire valide le cooldown, le serveur annonce « cette capacité est
indisponible N secondes ». Le client ne fait que décompter un nombre qu'on lui a
donné — du rendu, pas de l'autorité. Rien dans le HUD ne peut faire partir ou
non un coup.

Le remote est **push-only** : rien ne connecte `OnServerEvent`, donc il n'y a
pas de point d'entrée client à protéger par `RemoteGuard`.

`HudFeed.PushSnapshot` renvoie le **reste** d'un cooldown en cours à chaque
`CharacterAdded` : rien ne purge `skillCooldowns` à la mort, donc un joueur qui
meurt pendant un cooldown doit le retrouver en train de s'écouler.

### Vérification — par le vrai chemin, jamais un raccourci

Sondes en vrais `LocalScript` / `Script` insérés (le `require()` d'un
`execute_luau` isolé donne une copie morte — piège déjà payé cette semaine). Les
casts passent par `CombatController.TrySkill` / `DashController.TryDash`, c'est-
à-dire l'appel exact que fait `InputController` sur F/G/H/R/Q, donc le cooldown
affiché a fait le vrai aller-retour remote.

| élément | source | attendu | mesuré |
|---|---|---|---|
| vie | `Humanoid.Health` (écrit serveur) | ratio serveur | **écart max 0** sur 3 dégâts (74/48/22) |
| stamina | `Stamina.Changed` | module | écart **0.0037** |
| momentum bas | mirror serveur | 11.9 / tier 0 | barre 0.119, ultime **verrouillé** |
| momentum plein | mirror serveur | 100 / tier 2 | barre 1.000, ultime **armé** |
| Pas Divin (Q) | `DashService` | 0.55 s | chip armé, balayage 0.972 |
| Main du Colosse (F) | `CombatService` | 5 s | 4.9 |
| Frappe Céleste (G) | `CombatService` | 6 s | 5.9 |
| Marche du Titan (H) | `CombatService` | 10 s | 9.7 |
| Jugement (R) | `CombatService` | 12 s | 11.6 |
| Descente (ultime) | momentum au cap | verrouillé ↔ armé | correct **dans les deux sens** |

Les durées déduites tombent 2–3 % court parce que j'échantillonne le balayage
une frame après son armement — artefact de mesure, pas erreur du HUD.

**Survie au respawn** testée séparément (mort provoquée côté serveur — poser
`Health = 0` côté client ne réplique pas) : le `ScreenGui` survit, et le
re-binding sur le nouveau `Humanoid` fonctionne (barre 1.000 contre ratio
serveur 1.000, texte « 100 », 6 chips intacts).

### Une divergence signalée, pas maquillée

La spec suppose que `Stamina.lua` est un miroir serveur comme `Momentum.lua`.
**Il ne l'est pas** : il régénère et dépense localement. Le HUD le lit par le
même patron `Changed`, donc le HUD n'ajoute aucune autorité client — mais « la
barre de stamina affiche une valeur serveur » est **faux aujourd'hui**. Rendre
cela vrai demande une autorité stamina côté serveur, ce qui touche au gating du
combat : chantier séparé, hors périmètre ici. Signalé plutôt que corrigé en
douce.

### Fichiers

- `src/server/V1/HudFeed.lua` — nouveau, canal serveur→client des cooldowns
- `src/server/V1/CombatService.server.lua` — push au commit du cooldown skill
- `src/server/V1/DashService.server.lua` — push au commit du cooldown dash
- `src/client/UI/HUD.client.lua` — le HUD (remplace un stub désactivé)

Palette sombre + accents violets/aura, cohérente avec la direction artistique de
l'Arène Fracturée (§17 interdit explicitement le beige/gris d'arène classique).
La maquette HTML jamais validée n'a pas été reproduite, conformément au brief.

Tests **6/6**. Commit `cb32d5a`.

### Suite

**Point d'arrêt : le HUD attend le jugement visuel de Milan devant l'écran.**
La capture est structurellement cassée dans cet environnement (frame noire
systématique), il n'y a donc pas d'alternative automatisée. Ensuite : respawn
(§2), puis compteur de kills (§3).

---

## 2026-08-29 — Les deux derniers bugs mécaniques de Demi-Dieu : fermés

Périmètre : cancels (3/8) et Marche du Titan (dérive). Un à la fois, chacun
vérifié par **le vrai chemin d'exécution du jeu** — vrai `CombatController`,
vrai `MoveData`, vrai `AnimationDB`, vrai `Skill3.Execute` — pas d'AssetId en
dur, pas de mesure isolée sur les données. Prérequis vérifiés avant toute
conclusion : `rojo serve` écoute sur `127.0.0.1:34872`, et les valeurs
mesurées sont relues depuis la place, pas depuis le disque.

### Deux pièges de méthode rencontrés, et corrigés

1. **`execute_luau` obtient son propre cache `require()`.** Ma première sonde
   lisait un `CombatController` isolé dont `_character` est nil : `TryM1()`
   sortait en silence et les 4 lignes renvoyaient `0`. Toutes les sondes
   suivantes passent par un **vrai `LocalScript`/`Script` inséré**, qui partage
   le cache réel. Même piège sur le miroir Momentum côté client et sur
   `MomentumService` côté serveur.
2. **`ComboResetTime = 1.0`.** Ma deuxième sonde espaçait les swings de ~1,3 s,
   donc `_comboStep` repassait à 1 : les quatre lignes mesuraient toutes M1_1
   sans le dire. Corrigé en chaîne continue.

### Bug 1 — Cancels : deux mécanismes distincts, un seul est un bug

La fenêtre annoncée est `CANCEL_WINDOW_SECONDS = 0.2`, mais elle s'ouvre **au
marqueur Impact** et `TryCancelIntoDash` exige `_busy`, que le timer de
`recovery` libère. La fenêtre réellement utilisable vaut donc
`recovery − Impact`. Mesuré en jeu sur deux cycles complets :

| move | Impact | recovery | fenêtre réelle | frames @60 |
|---|---|---|---|---|
| M1_1 | 0.30 | 0.34 | **47 ms** | 2.8 |
| M1_2 | 0.3333 | 0.34 | **13–19 ms** | 0.8–1.1 |
| M1_3 | 0.3667 | 0.42 | 65–67 ms | 3.9 |
| M1_4 | 0.4667 | 0.52 | 65–68 ms | 4.0 |

Vérification que le chemin de repli n'était plus en cause : **0 `WARN marker
fallback` sur 12 swings** — le correctif `901213b` a bien réglé ça.

Puis test de cancel réel, sondage frame-parfait, par palier de Momentum :

- **tier 2 (surchargé)** : 12/12 puis 11/12. M1_1 **6/6**, M1_4 **6/6**.
  L'unique raté est M1_2, celui dont la fenêtre tient sous une frame.
- **tier 1 (chargé)** : **3/12** — M1_1 0/3, M1_2 0/3, M1_3 3/3, M1_4 0/3.

Ce 3/12 reproduit exactement le 3/8 historique et le sépare en deux :

- **M1_1 et M1_4 ne sont pas un bug.** La règle d'éligibilité
  `tier >= 2 or (tier >= 1 and (step == 2 or step == 3))` les exclut
  délibérément au tier 1. Au tier 2 ils passent 6/6.
- **M1_2 est un vrai bug** : éligible sur le papier, 6,7 ms de marge nominale,
  inattrapable en pratique.

**Correctif** : `MoveData.M1_2.recovery` 0.34 → 0.39 (~57 ms, aligné sur M1_3
et M1_4). Même classe de correctif que `901213b`, non détectée alors parce que
la marge de M1_2 était positive au lieu d'être négative.

**Re-test après resync, par le vrai chemin** (`m1_2_recovery_live = 0.39` relu
depuis la place) : M1_2 **0/3 → 3/3**, total tier 1 **3/12 → 6/12**, soit
**100 % des étapes éligibles**.

### Bug 2 — Marche du Titan : ce n'était pas une dérive latérale

Le HRP du joueur est **network-owned par le client** (`owner = milou_158`).
Toutes les mesures précédentes de ce bug étaient prises côté **serveur**, donc
sur une copie répliquée et corrigée par le lag — c'est de là que venaient les
« ~7 studs de dérive latérale ». Remesuré sur le pair qui possède réellement la
simulation, la dérive latérale réelle vaut **0,3 à 1,9 stud**, négligeable
contre une hitbox de 5 studs de large.

Isolation demandée, une impulsion à la fois, 4 répétitions, yaw épinglé et gate
de stabilisation :

| impulsions | latéral | balayage yaw |
|---|---|---|
| **1** | **−0.01** | **0.0°** |
| 2 | 0.25 – 1.08 | 15.6° – 108.7° |
| 3 | 0.38 – 0.98 | 67.4° – 117.6° |

**La dérive est purement un effet de composition** : absente de la première
impulsion, elle apparaît dès la deuxième. Et elle est **rotationnelle**, pas
latérale. Ce n'est pas `AutoRotate` : à `AutoRotate = false` le balayage est
identique, donc le couple est physique (le zéro brutal de la vitesse
horizontale en fin de pas, sur une assemblée Humanoid en contact au sol).

`finalStrike` calcule sa hitbox depuis `hrp.CFrame` à l'instant exact où elle
part. Erreur de visée mesurée à cet instant :

| pas | erreur de visée |
|---|---|
| 2 | **−25° à −79°** |
| 3 | **−83° à −112°** |

À 83–112° d'écart, la hitbox 7×5 pointe presque de côté. **C'est ça qui faisait
rater le coup**, pas la dérive latérale.

**Correctif** : `beginFacingLock` — un `AlignOrientation` rigide posé pour toute
la durée du cast, dont la cible suit `Humanoid.MoveDirection`. Le couple
parasite est annulé, et « orientable pendant le déplacement » (l'en-tête du
fichier) devient vrai en pratique au lieu d'être décidé par le bruit physique.

**Vérification bout-en-bout par le vrai `Skill3.Execute`, contre un vrai
mannequin, avec dégâts réels** (mannequin réépinglé entre chaque essai — le
premier run avait un raté dû au mannequin qui dérivait encore du knockback
précédent) :

| essai | erreur de visée | avance | dégâts | touché |
|---|---|---|---|---|
| 1 | 0.0° | 15.4 | 35 | oui |
| 2 | 0.0° | 17.5 | 35 | oui |
| 3 | 0.0° | 15.4 | 35 | oui |
| 4 | −0.1° | 16.3 | 35 | oui |

**4/4.** L'avance retombe à 15,4–17,5 studs pour 16,5 promis — le dépassement
d'environ 20 % constaté avant le correctif disparaît lui aussi.

### Un test rouge réparé, pas contourné

`test_combat_modules` criait : `JugementWindow.lua — no COOLDOWN constant`.
`JugementWindow` est un helper d'état pur, factorisé hors de
`Skill4_Jugement.lua` (qui déclare bien son `COOLDOWN`) : il n'a ni `Execute`
ni cooldown. Le test identifiait les skills par appartenance au dossier. Il les
identifie désormais par leur **contrat** (exposer `Execute`). Vérifié : le
critère mord toujours sur les **10** vrais skills, seul le helper est exempté.
Suite complète **6/6**.

### Fichiers

- `src/shared/V1/MoveData.lua` — `M1_2.recovery` 0.34 → 0.39
- `src/server/Skills/Skill3_MarcheDuTitan.lua` — `getStepAttachment`,
  `beginFacingLock`, appel dans `Execute`
- `tests/test_combat_modules.luau` — skills détectés par contrat

Commit `37a6dd1`. Rapport détaillé :
`artifacts/DEMIDIEU_DERNIERS_BUGS_2026-08-29.md`.

### Non fait, volontairement

Le chantier expressivité (« corrects mais fades ») et les animations des 4
compétences Demi-Dieu (5 slots encore `PENDING_UPLOAD` :
`Skill1_MainDuColosse`, `Skill2_FrappeCeleste`, `Skill3_MarcheDuTitan`,
`Skill4_Jugement`, `Ultimate_DescenteDuDemiDieu`) restent ouverts. Demi-Dieu
s'arrête ici ; la suite est le pivot HUD / méta-jeu.

Capture de contrôle : toujours pas publiée — les frames rendues restent noires
(10724 octets), et rien d'illisible n'est publié sur le miroir.

---

## 2026-08-28 (suite 9) — Tortillement corrigé sur les trois (M1_2, M1_3, M1_4)

**Contrôle final — pas > 45° par articulation, 60 échantillons par clip :**

| | avant | après |
|---|---|---|
| **M1_2** | **11** pas / 5 articulations / **3 RootJoint** | **1** / épaule seule / **0 root** |
| **M1_3** | 3 / 2 articulations / **1 RootJoint** | 3 / **épaule seule** / **0 root** |
| **M1_4** | **9** / 5 articulations / **3 RootJoint** | **1** / épaule seule / **0 root** |

**Zéro événement RootJoint sur les trois.** Tout ce qui reste est sur l'épaule
frappeuse : le snap d'impact voulu, signature identique aux 7 déjà corrigées.

**M1_2 et M1_3 ont exigé plus qu'une ré-amplification** — et la mesure l'a dit
avant toute écriture de code : une fois le clamp remplacé par la limite douce,
**aucun `k` n'atteint leur plancher** (M1_2 plafonne à 1.708 pour 1.75, M1_3 à
2.725 pour 2.75). Leurs versions livrées ne passaient donc que comme **artefact
du clamp**. Deux nouveaux patterns :

- `lead_hook_v2` — jeu de poses v1 trop petit ; espace balayé, pas deviné.
  amp **2.948** (plancher 1.75), ratio 0.960.
- `uppercut_v2` — **erreur de signe** : le v1 pilotait le contact à `rx=+100`,
  or `rx=+90` donne `dx −2.000 / dy +1.000` (deux fois plus de latéral que de
  montée) sur un coup jugé sur la montée +Y ; `rx=−90` donne `dy +2.000`.
  v2 finit à `rx=−138` : amp **3.212** (plancher 2.75), ratio 0.975.

Assets : M1_2 `88787651210963`, M1_3 `123966496280637`, M1_4 `127432679584327`.
Rollbacks conservés. Patterns d'origine intacts.

**Rapport complet** : `artifacts/FIX_TORTILLEMENT_2026-08-28.md`
**Commit** : `584e3b7`. 51 tests verts.

---

## 2026-08-28 (suite 9a) — Détail M1_4 (première étape)

Séquence complète, même discipline que les 7 précédents.

**M1_4** — ré-amplifié `k=1.0` via `soft_limit` (pas de réautorage : le pattern
`overhead_chop` utilise l'axe Y, que `rx` produit correctement — seul le clamp
était en cause).

| | valeur |
|---|---|
| saturation \|≥175°\| | **22 → 0** |
| saut max source | **360° → 166°** |
| class amplitude | 2.853 (plancher 2.85) |
| class ratio | 0.952 (plancher 0.78) |
| gate mouvement | ok |
| asset | `rbxassetid://127432679584327` (AssetTypeId=24) |
| rollback conservé | `87702115873385` |

**Contrôle par articulation en moteur — la preuve demandée :**

| | total pas >45° | RootJoint | R.Ép. | L.Ép. | R.Hanche | L.Hanche |
|---|---|---|---|---|---|---|
| avant (clamp dur) | **9** | **3** (54° · **128°** · 55°) | 2 | 1 | 2 | 1 |
| après (soft limit) | **1** | **0** | 1 | 0 | 0 | 0 |

Le pic restant (129°) est un **pas unique sur l'épaule frappeuse** : c'est le
snap d'impact voulu, exactement la signature de M1_1 (2 pas, épaule seule, 0
root). **Le tortillement a disparu, pas seulement les gates qui passent.**

---

## 2026-08-28 (suite 8) — DIAGNOSTIC : le perso qui se tortille = M1_2 et M1_4

Retour de Milan après la démo : le M1 part bien vers l'avant (fix validé à
l'œil), les coups sont « corrects mais fades », et **le perso se tortillait dans
tous les sens** à un moment de la boucle. Diagnostic demandé avant toute
correction.

### Mesure 1 — sources : sauts angulaires bruts

| animation | saut max/frame | où | valeurs \|≥175°\| | flip de signe à 180 |
|---|---|---|---|---|
| M1_1 (réautoré) | 170.0° | R.Shoulder.rz | **0** | 0 |
| **M1_2** (jamais réautoré) | **286.1°** | R.Shoulder.rx | **8** | 0 |
| **M1_3** (jamais réautoré) | **260.8°** | R.Shoulder.rx | **4** | 0 |
| **M1_4** (jamais réautoré) | **360.0°** | R.Shoulder.rx (−180 → +180) | **22** | **1** |
| PasDivin | 170.0° | R.Shoulder.rz | 0 | 0 |
| Skill1_DashStrike | 170.0° | R.Shoulder.rz | 0 | 0 |
| Skill2_BeamOrProjectile | 150.0° | R.Shoulder.rz | 0 | 0 |

### Mesure 2 — moteur : ce que le rig fait réellement

Les poses bakées sont des CFrames, pas des Euler : le moteur peut interpoler par
le chemin court, donc une valeur source ne prouve rien. J'ai scrubé chaque asset
sur 60 points et mesuré l'angle réel entre orientations consécutives (via la
trace de la matrice de rotation — aucune ambiguïté de wrap), **en excluant
l'entrée en pose depuis le repos** (artefact de mesure repéré au premier essai).

Le critère discriminant n'est pas le pic isolé — un grand pas unique, c'est le
snap d'impact voulu — mais **le NOMBRE de pas violents** :

| animation | pas > 45° (sur 60) | 3 plus gros |
|---|---|---|
| M1_1 | **2** | 75° @0.216 épaule |
| **M1_2** | **8** | 114° @0.255 épaule · **91° @0.217 RootJoint** · 81° @0.425 |
| M1_3 | 3 | 67° @0.422 épaule |
| **M1_4** | **6** | **128° @0.361 RootJoint** · 82° @0.388 épaule · 55° @0.486 RootJoint |
| PasDivin | 2 | 83° @0.151 épaule |
| Skill1_DashStrike | 2 | 99° @0.284 épaule |
| Skill2_BeamOrProjectile | 1 | 114° @0.421 épaule |

**Les 4 réautorés font 1-2 pas violents : un snap propre.** M1_2 en fait 8 et
M1_4 en fait 6, dont des rotations du **RootJoint** (91° et 128°) — c'est le
corps entier qui fouette, plusieurs fois, en pleine animation. C'est ça, le
tortillement.

**La corrélation est parfaite et monotone** : le nombre de valeurs saturées près
de 180° dans la source prédit le nombre de pas violents en moteur
(22→6, 8→8, 4→3, 0→1-2).

### Mesure 3 — d'où vient la saturation

| seed | BRUT : \|≥175°\| | BRUT : saut max | AMPLIFIÉ : \|≥175°\| | AMPLIFIÉ : saut max |
|---|---|---|---|---|
| M1_2 | **0** | 103.0° | **8** | 286.1° |
| M1_3 | **0** | 125.5° | **4** | 260.8° |
| M1_4 | **0** | 165.7° | **22** | 360.0° |

**Les seeds bruts sont propres. C'est `amplify_seed` qui crée la saturation** —
le clamp dur qui écrase toutes les valeurs hors bornes sur la même. C'est
exactement le bug corrigé plus tôt dans la session par `soft_limit`… mais ces
trois fichiers n'ont **jamais été régénérés** depuis. Le correctif existe, il
n'a simplement pas été appliqué à eux.

### Mesure 4 — répartition PAR ARTICULATION (la mesure qui tranche)

« Se tortiller dans tous les sens » est une lecture du **corps entier**. Un pas
violent sur une épaule, c'est un coup ; un pas violent sur le **RootJoint**,
c'est tout le personnage qui pivote. J'ai donc recompté les pas > 45° par
articulation.

| animation | RootJoint | R.Épaule | L.Épaule | R.Hanche | L.Hanche | total | événements RootJoint |
|---|---|---|---|---|---|---|---|
| M1_1 (réautoré) | **0** | 2 | 0 | 0 | 0 | **2** | — |
| **M1_2** | **3** | 1 | 4 | 2 | 1 | **11** | 91° @0.22 · 76° @0.23 · 48° @0.36 |
| M1_3 | 1 | 2 | 0 | 0 | 0 | 3 | 46° @0.25 (limite) |
| **M1_4** | **3** | 2 | 1 | 2 | 1 | **9** | 54° @0.35 · **128° @0.36** · 55° @0.49 |

**M1_1 est propre** : 2 pas violents, tous sur l'épaule qui frappe, **zéro sur le
RootJoint**. C'est la signature d'un coup net.

**M1_2 et M1_4 convulsent** : 11 et 9 pas violents répartis sur **5
articulations chacune**, dont 3 rotations du corps entier et les deux hanches.
Ce n'est pas un coup, c'est une secousse générale.

M1_3 est en limite basse (3 pas, un seul événement root à 46°) — le même défaut,
en beaucoup plus discret.

### Verdict

**Coupables : M1_2 et M1_4, les deux.** Elles jouaient toutes les deux dans la
boucle et convulsent toutes les deux sur 5 articulations. Je ne peux pas
attribuer ce que Milan a vu à une seule des deux, et je ne vais pas le
prétendre : **M1_4 produit le fouetté le plus violent du corpus** (128° sur le
RootJoint en une trame), **M1_2 la convulsion la plus soutenue** (11 pas
violents, le plus haut total). M1_3 porte le même défaut en très atténué (3).

Ce sont précisément les trois animations que je n'ai jamais réautorées — elles n'étaient pas touchées par le bug d'axe (hook et
uppercut/overhead utilisent des axes que `rx` produit bien), donc elles sont
passées à travers les 7 corrections.

Aucune des 4 animations réautorées n'est en cause.

**Rien corrigé** — diagnostic demandé avant correction. Le chemin est direct :
régénérer M1_2/3/4 via `amplify_seed` avec le `soft_limit` désormais en place,
puis re-gate + bake + upload + câblage + vérif moteur, comme les 7 autres.

### Point séparé, non traité : « corrects mais fades »

Le retour « Pas Divin n'a rien de divin, c'est bien un dash mais le perso
marche » est un problème de **caractère**, pas de correction — distinct du
tortillement. Les gates actuels mesurent l'amplitude, la direction et le
mouvement ; aucun ne mesure la personnalité. À traiter comme un chantier propre.

---

## 2026-08-28 (suite 7) — 7e et dernier seed : spear_thrust_jinwoo — et une correction de ma part

`spear_thrust_jinwoo` réautoré sur `two_handed_thrust_v2`, séquence complète.

| étape | résultat |
|---|---|
| gate de classe | amp **0.417 → 2.345** (plancher 2.25), ratio **0.434 → 0.839** |
| gate de mouvement | static 26 % (max 40 %) |
| poignet frappeur | gauche → **droit** |
| amplification | **aucune** (5.40× était requis avant) |
| upload | `rbxassetid://77395105000123`, AssetTypeId=24 |
| câblage | `Skills.Skill3_Launcher`, rollback `93808724347108` conservé |
| vérification moteur | via le **vrai slot** : length 0.767 s, les 2 bras **0.97 stud** avant, z +0.36 → −0.61, `rz` +94 / −94 en miroir |

### CORRECTION — j'avais tort sur l'impact en jeu

J'ai annoncé ce seed comme « le seul dont la correction change quelque chose
immédiatement ». **C'est faux, et le commentaire déjà présent dans le code le
disait.** Vérifié cette fois :

- `MoveData.Skill3` utilise `Skill3_MarcheDuTitan`, pas `Skill3_Launcher`.
- Le seul consommateur de `Skill3_Launcher` est l'alias legacy
  `Fighter_RushBrisant` → `SkillConfigs/Fighter/RushBrisant.lua`, et
  `SkillConfigs` n'est requis par **aucun service runtime** (seulement par la
  plomberie d'alias `_LegacyAliases` / `AnimationDB.init`).

Donc `Skill3_Launcher` charge et joue si on l'appelle, mais **rien ne l'appelle
en jeu réel**. La correction est juste et vaut d'être faite, mais elle ne change
rien au ressenti actuel.

**Bilan des 3 slots qui changent réellement quelque chose** (inchangé) :
`Skill1_DashStrike`, `Skill2_BeamOrProjectile`, `PasDivin`.

### Rojo est revenu

La synchro disque→Studio fonctionne de nouveau (`rojo serve` écoute sur 34872,
plugin chargé) : le changement de `Skill3_Launcher` était déjà dans la place
avant que je le pousse à la main. Plus besoin d'injecter les Source par
`execute_luau`.

**Les 7 seeds du bug d'axe sont traités.** Rien d'autre à cartographier.

---

## 2026-08-28 (suite 6) — Vérification moteur des 6 seeds réautorés, un par un

MCP rétabli après fermeture complète + relance de Studio (4 plugins utilisateur
chargés cette fois : `AnimExport`, `Rojo`, `WeppyRobloxMCP`, `rodeo`).

**Méthode par seed** : charger l'AssetId directement, **attendre que
`track.Length > 0`** (sans cette attente la piste n'est pas encore streamée et
le scrub échantillonne la pose de repos — faux négatif rencontré au premier
essai), puis scruber 11 points et mesurer la position du bras en **repère
torse**. Le repère torse est le point clé : en monde, on ne distingue pas « le
bras a frappé » de « le corps a tourné et le bras a suivi ».

| seed | asset | length | course avant | z min → max | poses distinctes | verdict |
|---|---|---|---|---|---|---|
| `M1_jab_toji` | `84765772735982` | 0.567 s | **1.27 stud** | +0.63 → −0.64 | 10/11 | ✅ |
| `M1_cross_toji` | `115046854915075` | 0.500 s | **1.29 stud** | +0.64 → −0.65 | 9/11 | ✅ |
| `dash_strike_toji` | `115418436010731` | 0.633 s | **1.24 stud** | +0.61 → −0.63 | 9/11 | ✅ **slot actif** |
| `Dash_demidieu` | `109116933091807` | 0.433 s | **1.24 stud** | +0.61 → −0.63 | 7/11 | ✅ **slot `PasDivin`, était PENDING_UPLOAD** |
| `devil_fruit_cast_luffy` | `121861953419707` | 0.767 s | **1.12 stud** (les 2 bras) | +0.54 → −0.58 | — | ✅ **slot actif**, cast symétrique |
| `M1_palm_gojo` | `109793014132139` | 0.433 s | **1.16 stud** | +0.58 → −0.58 | 10/11 | ✅ (non câblé — aucun slot ne le consomme) |

**Les 6 sont vérifiés en moteur.** Tous montrent le même profil sain : le bras
s'arme en arrière (z positif), traverse jusqu'en extension avant (z négatif),
`rz` passe du négatif profond au positif franc, et `rx` reste à ~0 — la frappe
est bien portée par l'axe correct.

**Piège rencontré et corrigé** : au premier essai `track.Length` valait 0 et le
scrub échantillonnait la pose de repos, donnant un faux résultat. C'est le piège
documenté du projet (« `LoadAnimation` réussi ≠ animation prête »). Toutes les
mesures ci-dessus attendent `track.Length > 0` avant d'échantillonner.

### Slots réellement modifiés en jeu

| slot | avant | après |
|---|---|---|
| `Skills.Skill1_DashStrike` | `102837166428258` | `115418436010731` |
| `Skills.Skill2_BeamOrProjectile` | `98944001215922` | `121861953419707` |
| `Mobility.PasDivin` | `PENDING_UPLOAD_Dash_demidieu` | `109116933091807` |

`M1_jab_toji` et `M1_cross_toji` alimentent les blocs de réversion Toji
(commentés — le kit Demi-Dieu occupe M1_1/M1_2). `M1_palm_gojo` n'est consommé
par aucun slot. Anciens ids conservés en rollback dans chaque commentaire.

---

## 2026-08-28 (suite 5) — 6 seeds réautorés sur le bon axe ; 1 uploadé, 5 en attente ; RIEN vérifié en moteur

### Résultats des 6 réautorages

Toutes ces animations pilotaient leur frappe sur `Shoulder.rx`, qui produit zéro
course avant. Réautorées sur les patterns v2 (avant = `rz`, positif à droite /
négatif à gauche). Même intention, mêmes timings — seul l'axe change.

| seed | amplitude (plancher 2.25) | ratio | poignet frappeur | static |
|---|---|---|---|---|
| `M1_jab_toji` | 0.580 → **2.626** | 0.817 → 0.875 | gauche → **DROIT** | 24 % |
| `M1_cross_toji` | 0.749 → **2.682** | 0.907 → 0.869 | gauche → **DROIT** | 27 % |
| `dash_strike_toji` | 0.738 → **2.444** | 0.852 → 0.814 | gauche → **DROIT** | 26 % |
| `Dash_demidieu` | 0.736 → **2.588** | 0.765 → 0.864 | gauche → **DROIT** | 23 % |
| `devil_fruit_cast_luffy` | 0.349 → **2.781** | 0.397 → 0.945 | gauche (symétrique) | 26 % |
| `M1_palm_gojo` | 0.319 → **2.424** | 0.713 → 0.827 | gauche → **DROIT** | 23 % |

**Les six passent les deux gates sans aucune amplification**, là où ils exigeaient
auparavant 3.00× à 7.05× — tous au-delà de la limite de validité (~3×), le
mécanisme même qui avait fini par geler le bras de M1_1.

**Le basculement du poignet frappeur de gauche à droite sur 5 des 6 est la
confirmation la plus nette** : le gate désignait la main de garde parce que le
bras nominalement frappeur n'avançait pas du tout. Luffy reste « gauche » à juste
titre — `front_palm_cast` est un cast symétrique à deux mains.

### État de livraison — à lire attentivement

| seed | baké | uploadé | câblé | vérifié moteur |
|---|---|---|---|---|
| `M1_jab_toji` | ✅ | ✅ `84765772735982` | ✅ (bloc Toji commenté) | ❌ |
| `M1_cross_toji` | ✅ | ❌ | ❌ | ❌ |
| `dash_strike_toji` | ✅ | ❌ | ❌ | ❌ |
| `Dash_demidieu` | ✅ | ❌ | ❌ | ❌ |
| `devil_fruit_cast_luffy` | ✅ | ❌ | ❌ | ❌ |
| `M1_palm_gojo` | ✅ | ❌ | ❌ | ❌ |

### BLOCAGE — vérification moteur impossible

Studio a été relancé en cours de session : le process tourne et une place est
ouverte (195 entrées `builtin_` dans le log), mais **son serveur MCP n'est pas
activé** — `list_roblox_studios` retourne `{"studios":[]}` et le log ne contient
aucune trace MCP. L'activer demande un clic dans Assistant, et l'envoi de frappes
clavier automatisées est refusé (`osascript n'est pas autorisé à envoyer de
saisies`, erreur 1002 — testé ce tour).

**Tous les chiffres ci-dessus sont des mesures disque (gates déterministes), pas
des observations en moteur.** Rien n'est déclaré vérifié en jeu.

**Aucune animation livrée ne change de comportement** du fait de ce tour : les
cinq non uploadées ne le peuvent pas, et `M1_jab_toji` alimente un bloc commenté
dont le slot est occupé par le kit Demi-Dieu.

### Note d'outillage

Les deux premières tentatives `asphalt sync cloud` ont expiré à 2 min sans rien
uploader, alors que `--dry-run` voyait bien le fichier. Simple latence Roblox :
au 3e essai avec une marge large, ça passe. À prévoir pour les 5 uploads
restants.

### Reste en attente

1. Activation du MCP Studio → vérification moteur de `M1_jab_toji`, puis upload +
   câblage + vérification des 5 autres.
2. **`spear_thrust_jinwoo`** — 7e seed affecté (`two_handed_thrust`, 5.40×
   requis), câblé sur `Skills.lua:Skill3_Launcher` et **actif en jeu**. Toujours
   hors périmètre, à trancher.

**Commit** : `32154e0`. Tests : 51 verts. Patterns d'origine intacts, seuls les 6
specs ciblés repointés.

---

## 2026-08-28 (suite 4) — Audit du bug d'axe sur tout le corpus : 7 seeds touchés, 5 patterns corrigés, rien réautoré

### Croisement patterns ↔ seeds livrés

| pattern (sur `rx`) | seeds bakés | ampli requis | poignet désigné |
|---|---|---|---|
| `dash_strike` | `Dash_demidieu` | **3.06×** | gauche |
| | `dash_strike_toji` | **3.05×** | gauche |
| `front_palm_cast` | `devil_fruit_cast_luffy` | **6.45×** | gauche |
| `lead_palm` | `M1_palm_gojo` | **7.05×** | gauche |
| `rear_hand_cross` | `M1_cross_toji` | **3.00×** | gauche |
| `two_handed_thrust` | `spear_thrust_jinwoo` | **5.40×** | gauche |
| `rear_hand_straight` (v1) | `M1_jab_toji` | **3.88×** | gauche |

**7 seeds**, pas 6 : `M1_jab_toji` utilise toujours `rear_hand_straight` v1, que
je n'avais corrigé que pour M1_1 au tour précédent.

**Signature identique sur les 7** : course avant **0.19-0.29 stud** contre
**1.02-1.56 stud** de latéral (5 à 7× plus de côté que devant), amplification
requise **3.00× à 7.05× — tous au-delà** de la limite de validité (~3×) que le
module documente lui-même, et le gate de classe désigne le poignet **gauche**
sur les sept. Ce dernier point est le révélateur : le bras nominalement frappeur
ne va nulle part.

**Non affectés** : `lead_hook` (X), `uppercut` / `overhead_chop` (Y),
`dual_arm_slash` / `wide_open_cast` (classe wide). Ils ont besoin d'axes que
`rx` produit réellement. Seule la classe *straight* avait besoin de Z.

### Ce que ça implique sur l'histoire du projet

Le constat fondateur « nos seeds font 5.3× moins que le pack commercial », qui
avait motivé la création d'`amplify_seed`, s'explique très probablement par ce
bug : **les seeds ne sont pas petits, ils pointent de côté.** L'amplification
aurait alors toujours été un pansement — et c'est elle qui, poussée à son
plafond, a fini par produire le bras gelé de M1_1.

### 5 patterns corrigés, en NOUVEAUX fichiers

Même discipline que `rear_hand_straight_v2` : les fichiers d'origine sont
**intacts** (vérifié via `git status`), donc aucun seed existant ne change.

| nouveau pattern | avant ampli | ratio |
|---|---|---|
| `dash_strike_v2` | 2.30 | 0.782 |
| `front_palm_cast_v2` | 2.73 | 0.929 |
| `lead_palm_v2` | 2.37 | 0.873 |
| `rear_hand_cross_v2` | 2.51 | 0.763 |
| `two_handed_thrust_v2` | 2.30 | 0.891 |

(planchers 2.25 / 0.67 — tous passent **sans aucune amplification**.)

Convention établie et inscrite dans chaque fichier : **`rz` positif = avant sur
l'épaule droite, `rz` négatif = avant sur l'épaule gauche** (elles se
mirrorent), `rx` = balayage en travers du corps.

### Rien n'a été réautoré ni re-livré

Comme demandé : les 7 seeds affectés restent tels quels en jeu. Ils sont bakés,
uploadés et vérifiés en moteur ; les réautorer est une décision par seed, à
prendre délibérément comme pour M1_1. Ce tour rend seulement les bons patterns
disponibles et mesure l'ampleur.

Les 4 M1 livrés passent toujours les deux gates (vérifié après coup).

**Capture de contrôle** : toujours non tentée, en attente de Milan devant l'écran.

**Commit** : `f800422`. Tests : 51 verts.

---

## 2026-08-28 (suite 3) — M1_1 réautoré : le direct était piloté sur un axe qui ne va PAS vers l'avant

### La vraie cause, enfin

En cherchant comment donner plus de marge au seed, j'ai mesuré sa trajectoire
réelle plutôt que de supposer. Le poignet droit **ne va jamais vers l'avant** :
sa coordonnée z reste entre −0.11 et +0.07 sur tout le clip (course avant :
0.181 stud). En x il part de +0.95, passe par +1.93, puis traverse à **−0.37** —
le bras balaie *en travers du corps*.

Sonde axe par axe depuis la pose de repos, via `r6_fk` :

```
Right Shoulder rx = +90  ->  dx -2.000  dy +1.000  dz  0.000     <- ZÉRO avant
Right Shoulder ry = +90  ->  dx -0.500  dy  0.000  dz -0.500
Right Shoulder rz = +90  ->  dx  0.000  dy +1.500  dz -1.500     <- l'axe du direct
```

L'avant est −Z. **`rx` produit exactement zéro déplacement avant.** Or le pattern
`rear_hand_straight` pilote le contact sur `rx: 90`, et son propre en-tête
affirme « POSITIVE rx = forward » — ce qui était vrai **avant** le fix C0/C1 de
`r6_fk` du 24/08 (qui a dé-permuté les plans sagittal et coronal). Les fichiers
de patterns n'ont jamais été mis à jour derrière.

**Toute la chaîne causale du punch mou tient là-dedans** : le seed mesurait 0.617
stud contre un plancher de 2.25 (le poignet partait de côté — le gate de classe
désignait même le poignet **gauche** comme frappeur), `amplify_seed` a été poussé
à son plafond k=12 (4× au-delà du ~3× où l'échelle linéaire d'Euler reste
valide), et le clamp dur a alors figé l'épaule à ±180° sur 47 % du clip. Tous les
gates passaient, parce qu'un bras gelé en pleine extension mesure quand même
comme « étendu ».

**Pourquoi M1_2/3/4 allaient bien** : hook (X) et uppercut/overhead (Y) ont
besoin d'axes que `rx` produit effectivement. Seule la classe *straight* avait
besoin de Z. C'est exactement pour ça que M1_1 exigeait 3.65× là où les trois
autres tournaient à 1.0-2.4×.

### Réautorage

Nouveau pattern `rear_hand_straight_v2`, même intention de personnage (frappe du
pilier lourde, armé profond, torse qui se déroule derrière), authoré sur `rz`.
Créé comme **nouveau fichier** plutôt qu'en modifiant le partagé : cinq autres
patterns de classe *straight* ont le même défaut et leurs seeds sont déjà bakés
et livrés — les toucher ici aurait été un balayage non demandé et non vérifié.

**Résultat, sans aucune amplification (k=1.0) :**

| | valeur | plancher |
|---|---|---|
| class amplitude | **2.704** | 2.25 (+20 % de marge) |
| class ratio | **0.905** | 0.67 |
| longest static run | **20 %** | max 40 % |
| poignet frappeur détecté | **droit** | (c'était le gauche avant) |

C'est bien « plus de marge réelle avant amplification », pas une nouvelle
tentative du pipeline sur le même seed insuffisant.

### Bake → upload → câblage → moteur

Uploadé `rbxassetid://127337837827260` (AssetTypeId=24 vérifié), câblé, tous les
ids précédents commentés pour retour arrière.

**Vérifié en vrai Play Solo**, en scrubbant la piste live :

```
t=0.10-0.20   arm z = +0.63   (armé en arrière)   rz = -80.1
t=0.25-0.30   arm z = -0.65   (extension avant)   rz = +90
```

**1.28 stud de course avant en repère torse**, là où l'ancien asset restait cloué
à −0.5 pendant toute la fenêtre de frappe. `rx` reste à 0 : le coup est bien
porté par `rz`.

### Reste ouvert, volontairement non touché

`dash_strike`, `front_palm_cast`, `lead_palm`, `rear_hand_cross` et
`two_handed_thrust` pilotent eux aussi leurs frappes avant sur `rx`. C'est très
probablement la cause d'origine du constat « nos seeds font 5.3× moins que le
pack commercial » qui avait motivé `amplify_seed` — autrement dit, l'amplification
a peut-être toujours été un pansement sur ce bug d'axe.

**Capture de contrôle** : non tentée, en attente que Milan soit physiquement
devant l'écran (le rendu en pilotage à distance reste cassé).

**Commit** : `48d8089`. Tests : 51 verts.

---

## 2026-08-28 (suite 2) — Gate de mouvement construit, clamp dur remplacé, et M1_1 déclaré non réparable par amplification

### 1. Nouveau gate : « le bras bouge-t-il ? » (`strike_motion.py`)

Tous les gates existants mesurent **où le membre arrive**. Aucun ne voit s'il a
bougé. Un bras qui se téléporte en pleine extension puis se fige les satisfait
tous — le poignet *est* étendu. C'est ce qui a été livré.

**Deux erreurs de ma part en cours de route, gardées en commentaire dans le code
parce qu'elles sont instructives :**

1. *Première version : mesurer la position monde du poignet.* Elle **n'a pas
   détecté le bug** (0.100 s / 20 %, PASS). Raison : le `RootJoint` passe de
   +7.1° à −118.0° à la frame 6, donc le corps tourne et traîne le poignet dans
   l'espace pendant que le bras reste soudé au torse. La position monde ne
   distingue pas « le bras a frappé » de « le corps a pivoté ». Corrigé : on
   mesure les **angles propres de l'épaule**, relatifs au torse.
2. *Sélection du « bras le plus actif ».* Elle **ratait aussi le bug** : un bras
   clampé tourne peu *parce qu'il est clampé*, donc l'heuristique choisissait la
   main de garde libre et rapportait 0.100 s au lieu des vrais 0.233 s. Corrigé :
   on juge **le pire des deux bras**.

**Le wrap d'angle est porteur** : le seed écrit −180° puis +180° (même rotation).
Une différence naïve lit 360° de « mouvement » au moment le plus figé —
exactement l'inverse d'un détecteur. Les écarts sont ramenés dans [−180, 180].

**Calibration sur les 17 seeds authorés, pas au doigt mouillé :**

| | `longest_static_run_frac` |
|---|---|
| seed cassé (M1_1 amplifié) | **47 %** |
| pire livré (`heavy_finisher_sukuna`) | 34 % |
| `M1_uppercut_saitama` | 31 % |
| typique | 20-28 % |

Seuil à **40 %** — dégage des deux côtés. `motion_ratio` est **délibérément non
gaté**, et le code dit pourquoi : le clip cassé score 40 %, soit **plus** que
`uppercut_saitama` (34 %) et `Dash_demidieu` (38 %) qui sont livrés et validés.
Un critère qui crie sur du bon en ratant du mauvais, c'est un gate qu'on apprend
à ignorer.

**Vérifié comme demandé : 17/17 seeds livrés PASS, le seed cassé FAIL.** Le gate
est câblé dans `stage4_gate_cascade.run_cascade_frames` (gate n°7).

### 2. `amplify_seed` : clamp dur → saturation douce

Coupable : `nv = max(lo, min(hi, nv))`. Un clamp dur envoie **toutes** les
valeurs hors bornes sur le même nombre — une série de frames sur-amplifiées
s'écrase en plateau. C'est le mécanisme exact du bras gelé.

Remplacé par un `soft_limit` en `tanh` : strictement monotone (deux entrées
distinctes gardent deux sorties distinctes → **aucun plateau ne peut se former**),
asymptotique à la borne sans jamais l'atteindre, et **identité exacte** sous le
genou (80 % de la plage) — donc les 17 animations validées ne peuvent pas être
restylées en silence. L'ancien comportement reste accessible via `soft=False`
pour reproduire l'existant au bit près.

### 3. BLOCAGE — M1_1 n'est pas réparable par amplification

Balayage de `k` avec la saturation douce, les **deux** gates évalués :

```
    k     amp   ratio  static  classe  mouvement
  1.0   0.617   0.824    20%    FAIL      ok
  3.0   1.591   0.895    20%    FAIL      ok
  5.0   2.175   0.989    20%    FAIL      ok     <- meilleure amplitude atteignable
  8.0   1.833   0.710    20%    FAIL      ok
 12.0   2.356   0.817    47%     ok      FAIL    <- ce qui est livré aujourd'hui
```

**Il n'existe aucun `k` où les deux gates passent.** En dessous de k=8 le
mouvement est sain mais l'amplitude plafonne à **2.175** (plancher 2.25, il
manque 3.3 %). À k=12 l'amplitude passe **uniquement grâce au plateau du clamp**.

Autrement dit : **l'animation livrée ne passait le gate de classe que comme
artefact du clamp.** Enlever l'artefact, et le seed n'atteint plus le plancher.
Le module documente lui-même que l'échelle linéaire d'Euler cesse d'être valide
au-delà de ~3× ; on tournait à 12×.

**Conclusion : ce seed est trop petit pour être sauvé par mise à l'échelle. Il
faut le ré-autorer (poses plus amples), pas l'amplifier.** C'est précisément ce
que le nouveau gate est censé révéler — et il le révèle immédiatement, au lieu
d'après livraison.

**Rien n'a donc été ré-uploadé** : je ne livre pas une animation qui échoue un
gate juste après avoir passé la session à construire ce gate. Et je ne bascule
pas M1_1 sur l'animation Toji de moi-même — c'est une décision d'identité du
personnage, pas une décision technique.

### 4. Rayon d'action : contenu à M1_1

| animation livrée | static | verdict |
|---|---|---|
| M1_1 | 47 % | **FAIL** |
| M1_2 | 24 % | PASS |
| M1_3 | 21 % | PASS |
| M1_4 | 20 % | PASS |

Seul le **premier coup de la chaîne** est mort — celui qu'on sent le plus.

**Commit** : `340efea`. Tests : 51 verts.

**Capture de contrôle** : non tentée ce tour. Le rendu en pilotage à distance
reste cassé (constat du tour précédent, non résolu), et il n'y avait de toute
façon rien de nouveau à montrer en jeu puisque rien n'a été uploadé.

---

## 2026-08-28 (suite) — Provenance tranchée, easing branché, et LA cause racine du punch mou trouvée

### 1. Provenance de l'asset uploadé — TRANCHÉE, mon soupçon était faux

Méthode valide cette fois : passer les deux sources par **le même
convertisseur** et hasher la sortie canonique contre le `.lune.json`
réellement baké. Aucune corrélation statistique, aucune extraction d'Euler.

```
UPLOADED (baked into the .rbxm)  sha=0894ed0ef172a30c
M1_1_demidieu.json               sha=a89cd2dbce464648  IDENTICAL=False
M1_1_demidieu_amplified.json     sha=0894ed0ef172a30c  IDENTICAL=True
```

**Les 4 M1 ont été bakés depuis la version AMPLIFIÉE.** Le seed faible n'a
jamais été shippé. Mon soupçon de l'entrée précédente était **faux** — aucun
ré-upload correctif n'était nécessaire.

### 2. Blocage : le Cmd+S automatisé ne marche PAS

Testé pour de vrai : `osascript n'est pas autorisé à envoyer de saisies (1002)`.
Lire le processus au premier plan est autorisé, **envoyer des frappes clavier
est une permission distincte, toujours refusée**. Mon test précédent (« System
Events répond ») était insuffisant. Vérifié après coup : 0 ligne de sauvegarde
ajoutée au log Studio. **Politique inchangée : jamais de fermeture sans
sauvegarde confirmée.**

### 3. Blocage : l'overshoot est IMPOSSIBLE via l'easing

Le bake a planté sur `The enum item 'Sine' does not exist for enum
'PoseEasingStyle'`. Les poses de KeyframeSequence n'utilisent pas
`Enum.EasingStyle` (le grand set TweenService) mais **`Enum.PoseEasingStyle`**,
énuméré via Lune :

```
PoseEasingStyle: Cubic, Linear, Constant, Bounce, CubicV2, Elastic
PoseEasingDirection: In, InOut, Out
```

Ni `Back`, ni `Quint`, ni `Quad`, ni `Sine`. Ma politique d'easing était donc
**entièrement inimplémentable** — je validais contre le mauvais enum, c'est un
bug de ma part, corrigé et désormais **verrouillé par un test**.

**Conséquence structurelle** : `Elastic` et `Bounce` sont les *seuls* membres
capables d'overshoot, et les deux sont bannis pour les frappes (régression de
dérive latérale du Day 19). **L'overshoot n'est donc pas exprimable en easing.**
Un vrai follow-through exige des **keyframes supplémentaires**, qui changent les
valeurs de pose et doivent repasser les gates — c'est une autre technique.

### 4. L'easing atteint enfin le bake (opt-in)

`agent_to_lune_converter` recalculait toujours l'easing depuis la phase et
**jetait silencieusement** `frame["easing"]` — ce qui rendait tout easing
authoré en amont sans effet au bake. Corrigé, mais **en opt-in** via
`metadata.easing_plan` : tous les seeds existants portent déjà des champs
`easing` qui ne correspondent PAS au mapping par phase, donc les honorer
inconditionnellement aurait changé le bake de chaque seed et cassé la
repro bit-à-bit des assets déjà vérifiés en moteur. Vérifié dans les deux sens.

### 5. Passe easing M1_1 livrée bout-en-bout — et elle NE corrige PAS le défaut

Re-gate (bit-identique : ratio 0.792000, amp 2.447000, bounds ok) → bake →
upload (`rbxassetid://76339372524545`, AssetTypeId=24 vérifié) → câblage
(ancien id commenté) → vérification moteur.

**Résultat : le hold mort est toujours là.** Scrub du nouvel asset en Play
Solo : pose identique à t=0.15, 0.20, 0.25 et 0.30.

### 6. LA cause racine — saturation de l'amplification, pas l'easing

En inspectant le canal du bras frappeur image par image :

```
frame   t       Right Shoulder (rx, ry, rz)
   3  0.1000  ( -180.00,  91.00,  0.00)
   4  0.1333  ( -180.00,  91.00,  0.00)
   5  0.1667  ( -180.00,  91.00,  0.00)
   6  0.2000  ( -180.00,  91.00,  0.00)
   7  0.2333  (  180.00,  91.00,  0.00)
   8  0.2667  (  180.00,  91.00,  0.00)
   9  0.3000  (  180.00,  91.00,  0.00)
  10  0.3333  (  180.00,  91.00,  0.00)
```

**Le Right Shoulder est bloqué à ±180° de t=0.10 à t=0.333** — 0.23 s, presque
la moitié du clip (−180° et +180° sont la même rotation). `amplify_seed` a
amplifié la rotation de frappe jusqu'à **saturer contre la borne articulaire de
180°**, aplatissant toute la frappe en une pose statique.

Aucun easing ne peut interpoler entre deux valeurs identiques — d'où l'échec de
la passe easing. Et **le gate ne peut pas voir le problème** : la FK mesure le
poignet *étendu*, ce qu'un bras figé en extension satisfait parfaitement. Le
gate valide l'amplitude, pas le fait que le bras bouge.

C'est l'explication du punch qui ne lit pas — plus convaincante que le hold
mort, qui n'en était que le symptôme.

### 7. Capture de contrôle — obtenue sur disque, inexploitable

Le rendu du viewport reste fortement dégradé même Studio au premier plan
(session pilotée à distance). Fichier sur disque mais illisible — **non publié
sur le miroir**, plutôt que de publier une image inutilisable.

**Commit** : `4e65f3b`. Tests : 39 verts sur mes modules.

### 8. Deux tests rouges trouvés dans la suite complète — PAS de moi, mais documentés

La suite complète `scripts/animator_ai/tests/` : **455 passed, 2 failed**
(11 min 31). Règle du projet : un test rouge n'est jamais « acceptable ».

```
FAILED test_moving_contact.py::TestTracking::test_gate_passes_on_the_real_face_hit_trajectory
FAILED test_moving_contact.py::TestTracking::test_joint_solve_dominates_the_sequential_one
```

**Ce n'est pas causé par mes changements**, prouvé de deux façons :
1. Fermeture d'imports du test = `{contact_solver, moving_contact, r6_fk}` —
   aucun de mes modules (nouveaux ou modifiés) n'y est atteignable.
2. `git log` : ces trois fichiers datent de `14cd216` (2026-08-25) et
   `70c2196` (2026-08-24) ; mes deux commits n'y touchent pas.

*(Une comparaison en worktree sur le commit d'avant était non concluante : les
tests s'y **skippent**, car ils dépendent du dump du pack Close Combat, un
artefact non commité. C'est aussi pourquoi ils ne crient qu'ici.)*

**Ce qu'ils disent, chiffres réels :**

```
[FAIL] Right Wrist -> victim Head:
       mean 0.1604 / max 0.2549 studs sur 13 frames (53.8% within 0.25)
assert joint.coverage == seq.coverage == 1.0   ->   0.5385 == 1.0
```

Les deux échecs ont **la même racine** : la couverture est de 53.8 % (7 frames
sur 13) au lieu de 100 %, **en mode joint comme en séquentiel**. Ce n'est donc
pas « le solveur joint est moins bon » — les deux modes échouent identiquement,
et le test qui garde la promesse du commit `14cd216` (« solve the whole
trajectory jointly ») ne tient plus.

**Détail qui interpelle** : le tableau des distances plafonne à ~0.2484 sur de
nombreuses frames consécutives — **encore une signature de saturation contre une
limite**, structurellement identique au clamp à ±180° du Right Shoulder trouvé
au §6. Deux symptômes indépendants de « la valeur se colle à sa borne et y
reste » dans le même pipeline. À creuser ensemble plutôt que séparément.

Non corrigé (hors du périmètre demandé ce tour), mais tracé ici comme canari,
pas étouffé.

**Prochain pas évident** : le vrai correctif n'est ni Wang ni l'easing, c'est
de **replafonner l'amplification** pour qu'elle n'écrase plus la courbe contre
la borne — et d'ajouter au gate un critère « le bras bouge-t-il pendant la
fenêtre de frappe ? », que la cascade actuelle est structurellement incapable
de détecter.

---

## 2026-08-28 — Diagnostic M1 clos (l'anim joue vraiment) + filtre de Wang et easing planner

Pilotage à distance, Milan absent de son PC.

### Diagnostic : que joue réellement le M1 ?

Question posée : le M1 testé jouait-il le vrai asset Demi-Dieu, un fallback
procédural, ou un reliquat Toji en cache — et `AnimationTrack:Play()` tourne-t-il
vraiment (pas juste un `LoadAnimation` qui réussit) ?

**Réponse : tout est correct.** Mesuré via un vrai `LocalScript` inséré dans le
DataModel live (partage le cache `require` réel) :
- `m1_asset_actually_playing = rbxassetid://137721498143059` → le **vrai M1_1
  Demi-Dieu**, pas le Toji (`90222523479903`), pas un procédural.
- `m1_timeposition_advanced = true` — TimePosition avance réellement :
  0 → 0.079 → 0.129 → 0.200 → 0.258 → 0.317.
- `weight` 0 → 1 (fade-in correct), priorité `Action`, l'Idle se coupe bien.

**Et les os bougent vraiment** (le point qui restait douteux). Ma première sonde
disait « pose gelée == pose neutre au bit près », ce qui ressemblait au bug B11
de `RECURRING_BUGS.md`. Cette sonde était **buggée** (mesure relative au HRP au
lieu du Torso). Sonde corrigée, en scrubbant l'animation image par image :

| t | Right Shoulder (rx,ry,rz)° | Right Arm vs Torso |
|---|---|---|
| repos (aucune anim) | 0, 0, 0 | 1.5, 0, 0 |
| 0.00 | 20, −16.6, 0 | 1.27, −0.14, 0.14 |
| 0.15 | 0.3, 88.9, 179.6 | 1.0, 0.99, −0.5 |
| 0.30 | 0.3, 88.9, 179.6 | 1.0, 0.99, −0.5 |
| 0.45 | 171.1, 88.9, −180 | 1.06, 0, −0.5 |

**Mais le diagnostic révèle un vrai défaut d'animation** : la pose est
strictement identique de t=0.15 à t=0.30 — **150 ms morts pile sur le marqueur
Impact**, sans follow-through ni overshoot. La source le confirme :
`metadata.impact_hold_frames = 3` + easing `Constant` sur ces frames. Le moteur
et les données d'origine concordent.

**Capture de contrôle : non obtenue.** Le viewport rend en noir ou fortement
dégradé quand Studio est en arrière-plan (Milan absent) — une capture partielle
lisible, les suivantes noires. La preuve géométrique ci-dessus la remplace et
est plus forte : c'est le juge stable selon la doctrine du projet.

### Découverte annexe non résolue — provenance de l'asset uploadé

Le seed **brut** `M1_1_demidieu.json` **échoue** le gate class-aware
(amp 0.617 vs min 2.25, soit 3.6× sous le seuil). La version **amplifiée**
passe (amp 2.447, ratio 0.792) — et ce sont exactement les chiffres cités dans
`AnimationDB/Combat.lua`. Lequel des deux a été baké dans le `.rbxm` uploadé ?
**Non tranché** : mes deux tentatives de comparaison (extraction d'Euler depuis
le CFrame baké, puis r6_fk contre la mesure moteur) ont toutes deux une
incohérence de convention (~1 stud de résidu des deux côtés, corrélations
0.18/0.15 → méthode invalide). Je ne conclus donc rien. À trancher proprement,
c'est potentiellement l'explication d'un M1 qui lit faible en jeu.

### R&D 1 — Filtre de Wang (`cartoon_filter.py`)

`x* = x − k·G(x″)` par canal, numpy seul, sans rien connaître de Roblox.
**Validé d'abord sur signal synthétique**, propriétés vérifiables à la main :

```
anticipation : −0.0287  (source exactement 0.0)
overshoot    : +1.0375  (source exactement 1.0)
creux frame 31 (montée commence à 30) / pic frame 53 (montée finit à 54)
no-op exact sur constante et sur rampe (x″=0)  -> écart max 0.00e+00
overshoot strictement linéaire en strength
```

Compromis documenté et asserté : le padding par extrapolation linéaire force
`x″=0` aux deux échantillons de bord — accepté pour que le filtre n'invente
jamais un à-coup sur la frame 0 (qui ferait un pop au blend-in). 21 tests.

### R&D 2 — Re-passage par les gates (`apply_cartoon_filter.py`)

Obligatoire, et **il a servi** : sur le vrai M1_1 Demi-Dieu, le filtre
**dégrade** l'amplitude de classe.

| strength | class_amplitude (min 2.25) | verdict |
|---|---|---|
| original | 2.447 | PASS |
| 0.25 | 2.277 | PASS (de justesse) |
| 0.50 | 2.005 | **REGRESSION** |
| 1.00 | 1.688 | **REGRESSION** |
| 2.00 | 1.185 | **REGRESSION** |

`joint_bounds` tient partout — ce n'est pas l'anatomie qui casse, c'est la
métrique de classe. Cause structurelle, pas un bug : nos seeds sont en
pose-à-pose avec des holds morts, donc `x″` est dominé par les discontinuités
hold/snap, et soustraire `k·G(x″)` érode exactement l'amplitude que
`amplify_seed` avait ajoutée. **Le filtre de Wang combat l'amplification au
lieu de la compléter.**

**Résultat négatif assumé : la piste 1 n'a PAS prouvé sa valeur sur un vrai
coup Demi-Dieu.** C'était le critère fixé avant d'ouvrir la piste 4 (Blender
headless) — elle reste donc fermée.

### R&D 3 — Easing planner (`easing_planner.py`)

Le bon levier pour ces courbes, et pour une raison structurelle : **les gates
jugent les valeurs de keyframes, l'easing ne change que l'interpolation entre
elles**. Un overshoot obtenu via `Back/Out` est donc **gate-neutre par
construction**, contrairement au filtre qui réécrit les valeurs.

Vérifié empiriquement sur la vraie seed : 16 frames replanifiées, **toutes les
métriques bit-identiques** (`class_ratio 0.792000`, `class_amplitude 2.447000`,
`joint_bounds ok`).

Politique par phase, sur enums Roblox stock (aucune dépendance nouvelle) :
`windup → Quad/In` (accélère au lieu de tenir), `impact → Quint/Out`
(décélération dure = la frappe lit comme de la force), `recovery → Back/Out`
(**le follow-through manquant**). `Elastic` et `Bounce` sont **bannis dans le
code avec la raison inscrite à côté du ban** (régression de dérive latérale du
Day 19). 16 tests.

`--replan-holds` cible exactement le hold mort de 150 ms mesuré en moteur
(frames 6-9 : `Constant` → `Quad/In` + `Quint/Out`).

**Commit** : `830b258` (5 fichiers, 889 insertions, 37 tests verts).

**Studio** : laissé ouvert, Play arrêté, scripts de test nettoyés. La permission
Accessibilité est maintenant accordée (System Events répond), mais aucune
sauvegarde n'était nécessaire (rien de modifié côté place) — donc ni Cmd+S ni
fermeture déclenchés, conformément à la politique.

---

## 2026-08-27 (suite 5) — Vérification réelle Play Solo : Jugement OK, bug Momentum trouvé et corrigé

Studio débloqué (Rojo connecté, sauvegarde faite par l'utilisateur). Reprise en
ordre de risque décroissant, avec de vrais remotes réseau à chaque étape —
aucun claim "vérifié" sans test réel qui a effectivement tourné.

**1. Jugement (le plus risqué — touche `DamageService.Apply`, chemin de
dégâts partagé) : PASS, réel.**
Deux scripts `Script` réels insérés côté serveur (bypassent le piège
d'isolation `require()` d'`execute_luau` documenté en mémoire) :
- Cas parry réussi : `hp_after=100` (inchangé), `dummy_hp_after=975`
  (contre-coup de 25 appliqué), `momentum_after=24.01` (récompense
  Jugement). `jugement_execute_ok=true`.
- Cas régression (pas de parry actif) : `hp_after_unparried=85` = exactement
  100−15, `hp_after_missed_window=75` = exactement 85−10. **Le hook parry ne
  touche rien en dehors de sa fenêtre — `DamageService.Apply` se comporte à
  l'identique d'avant Jugement.**

**2. Routage touche R de l'Ultime : bug réel trouvé, corrigé, re-testé PASS.**
Premier test (`ULTIMATE_ROUTING_TEST_RESULT`, budget 15s) : grind M1 réel
plafonne à `momentum_after_grind=97.75`, jamais 100.
Deuxième test (`ULTIMATE_ROUTING_TEST2_RESULT`, budget 25s — pour écarter
l'hypothèse "pas assez de temps") : même plafond, `97.60`. Confirme que ce
n'est pas un problème de durée.

Cause identifiée dans `src/server/V1/MomentumService.lua` :
`TryConsumeForUltimate` exigeait `momentum == 100` (égalité stricte), mais
`Tick()` (branché sur `RunService.Heartbeat`) décroît le Momentum de −8/s
**sans exception, y compris au plafond**. Dès qu'un coup portait le Momentum
à exactement 100.0 (via `math.clamp`), la frame Heartbeat suivante (~16ms)
le faisait redescendre — avant qu'un vrai appui R (RemoteEvent, jamais
synchronisé sur cette frame précise) puisse l'observer. L'Ultime était
structurellement infirable en jeu réseau réel.

**Fix (commit `18e1016`)** : la décroissance est maintenant gelée dès que le
Momentum atteint 100, et ne reprend qu'après consommation par l'Ultime ou
perte suite à un coup encaissé. `stylua`/`selene`/`scan_recurring_bugs.py
--staged` : clean, 0 blocker.

**Ce bug n'invalide PAS la Phase 1 déclarée vérifiée** : à l'époque,
`TryConsumeForUltimate` n'avait aucun appelant (le fichier le disait
lui-même : *"nothing calls it yet"*) — seul `Ultimate_DescenteDuDemiDieu.lua`
(Phase 4) l'appelle. Ce que la Phase 1 avait testé (gain M1, seuils de
tiers, bonus de chaîne, cooldown dash) ne dépend pas de ce chemin.

**Re-test après fix, session Play Solo relancée à zéro** (obligatoire — les
modules déjà `require()`és dans l'ancienne session gardaient l'ancienne
logique en mémoire) : `ULTIMATE_ROUTING_TEST3_RESULT` —
`momentum_after_grind=100`, `momentum_after_1s_hold=100` (le gel tient
vraiment, pas un pic d'une frame), `is_ready_after_hold=true`
(`CombatController.IsUltimateReady()` — exactement ce que lit
`InputController` pour router R vers le slot 5, donc c'est bien le verrou
Momentum qui gouverne, pas l'ancien `TransformController.IsTransformed()`),
`ultimate_confirm_1.result="Module"` (serveur dispatche),
`momentum_after_ultimate=0` (jauge consommée). **PASS réel, propre.**

---

## 2026-08-27 (suite 6) — Skill1/Skill2 OK, Skill3 cassé puis partiellement corrigé, Cancels non fonctionnels, statut animations confirmé

Suite directe de la vérification ci-dessus. Tous les résultats viennent de
vrais tests Play Solo (remotes réseau réels, scripts `Script`/`LocalScript`
insérés dans le DataModel live, jamais `execute_luau` isolé pour lire un état
mutable — piège documenté en mémoire).

**Main du Colosse (Skill1) : PASS réel.** Dégâts mesurés 2000→1980, delta
exact = 20 (`MoveData.Skill1.damage`).

**Frappe Céleste (Skill2) : PASS réel.** Dégâts mesurés 1980→1958, delta
exact = 22.

**Marche du Titan (Skill3) : bug réel trouvé, diagnostiqué, corrigé
partiellement, re-testé.**
Deux premiers tests (3 studs puis 13 studs de distance de départ) : 0/2
touchés. Position loguée après le skill : le joueur avait parcouru ~20.7
studs pour 2 pas dont le calcul propre (55 studs/s × 0.15s × 2) ne prévoit
que ~16.5 — largement dépassé la cible.

Cause : `applyStepImpulse` (`Skill3_MarcheDuTitan.lua`) détruisait la
contrainte `LinearVelocity` sans jamais remettre à zéro
l'`AssemblyLinearVelocity` résiduelle — le personnage continuait de glisser
sur son élan bien après la durée annoncée du pas (le contrôleur Humanoid de
Roblox ne reprend la main que progressivement). **Fix commit `05a4910`** :
remise à zéro de la composante horizontale de la vélocité à la fin de
chaque pas. Session Play Solo relancée à zéro (obligatoire, même raison que
pour Momentum). Re-test : distance parcourue ramenée à ~16.7 studs, conforme
au calcul du skill — le fix est réel et confirmé.

**Mais le skill rate encore.** Un troisième test, avec l'orientation du
joueur explicitement verrouillée sur la cible juste avant le cast (pour
éliminer toute ambiguïté de facing), montre une **dérive latérale de ~7
studs** pendant la séquence de 2 pas — le joueur finit à côté de la cible,
pas dessus. Cause non isolée : soit un vrai bug de recalcul de facing entre
les pas, soit un artefact du test (aucune touche de direction n'est
maintenue pendant le script, contrairement à un vrai joueur). **Marche du
Titan reste NON FIABLE en l'état** — un fix a été appliqué et confirmé
utile, mais le skill ne touche toujours pas sa cible dans mes tests. À
retester avec un vrai joueur tenant une touche de direction avant de
considérer le skill livrable.

**Cancels (Phase 2) : NON FONCTIONNEL en pratique, confirmé.**
Grind réel jusqu'au tier "chargé" (10 coups, momentum 40.7), puis 4
tentatives de cancel avec sondage `RunService.Heartbeat` à chaque frame
(réaction "parfaite", meilleur cas possible) : **0/4 réussies.** Tous les
`busyEndedAt` mesurés (0.34-0.47s) collent exactement aux valeurs de
`recovery` de chaque coup M1, pas à la fenêtre de cancel de 0.2s censée
suivre l'impact. Confirme, avec des vrais coups à tier réellement chargé
(pas juste un calcul), le diagnostic déjà repéré dans les logs bruts :
`[V1] WARN marker fallback for M1_3` et `M1_4` apparaissent systématiquement
(jamais pour M1_1/M1_2) — pour ces deux coups, le marker `Impact` arrive
après (ou quasi en même temps que) `recovery` dans `MoveData.lua`, donc le
minuteur de secours ne se déclenche jamais à temps et la fenêtre de cancel
ne s'ouvre jamais. Pour M1_1/M1_2 le marker arrive bien avant `recovery`,
mais la marge (6.7ms pour M1_2) est trop courte pour être exploitable même
par un sondage frame-parfait. **Non corrigé ce tour-ci** — root cause
identifiée avec précision, mais le fix touche soit les valeurs de timing
`MoveData.lua` (resynchroniser `recovery` avec les vrais markers `Impact`
Demi-Dieu, qui ont changé de valeurs par rapport aux anciens markers Toji)
soit la logique de fenêtre elle-même ; pas fait faute de temps, à traiter
en session dédiée.

**Statut animations M1 — confirmé inchangé, avec preuve visuelle directe
cette fois.** Les 4 `.rbxm` existent bien sur disque
(`artifacts/animator_ai/agent_outputs/M1_*_demidieu_handkeyed/upload/`),
mais `Combat.lua` porte toujours les 4 IDs littéraux `PENDING_UPLOAD_*`,
`verified_assets.json` ne contient aucune entrée `demidieu`, et
`scripts/verify_asset.py` n'a jamais tourné dessus. Confirmé en direct
cette session : chaque `[AssetVerifier]` de chaque Play Solo affiche
`VERIFIED=0`, et chaque `[AnimationDriver]` log `M1_1..4 -> FAILED:
LoadAnimation error`. Deux captures d'écran réelles (voir ci-dessous)
montrent la conséquence visuelle : le personnage ne joue AUCUNE animation
de coup (pose statique) pendant que les VFX d'impact et les dégâts, eux,
fonctionnent normalement. **Verdict inchangé : baké + gates géométriques
passés, PAS uploadé, PAS câblé, PAS vérifié en moteur** — catégoriquement
différent des 12 seeds Toji réelles.

**Captures in-game : prises, affichées, PAS publiées sur le miroir.**
Deux captures réelles via `screen_capture` (Play Solo, vrai combat M1 en
cours) confirment visuellement l'état ci-dessus. Limitation technique
rencontrée : l'outil de capture retourne l'image directement dans la
conversation sans l'écrire sur disque à un chemin accessible en shell —
aucune méthode trouvée cette session pour la sauvegarder localement et donc
la faire passer par `scripts/sync_progress_log.sh` (qui exige un fichier
local). Contrairement aux captures d'arène précédentes (probablement
sauvegardées via un pipeline différent), celles-ci restent donc visibles
uniquement dans la conversation Claude Code, pas sur le miroir public.

---

## 2026-08-27 (suite 7) — Animations M1 uploadées + câblées + vérifiées, Cancels amélioré, Marche du Titan diagnostiquée, captures enfin publiées

Suite directe des trois demandes en attente de l'entrée précédente.

**1. Upload + câblage + vérification des 4 animations M1 Demi-Dieu — FAIT,
pipeline complet réel, pas juste les gates.**
`assets/animations/handkeyer/M1_[1-4]_demidieu.rbxm` (déjà bakés) uploadés
via `asphalt sync cloud` (Open Cloud réel, gratuit — aucun Robux, cf. règle
gravée en mémoire) : `M1_1=137721498143059`, `M1_2=138058194756149`,
`M1_3=102280920188057`, `M1_4=87702115873385`. Câblés dans
`AnimationDB/Combat.lua` (remplace les 4 `PENDING_UPLOAD_*`) — `Fighter_M1_
1..4` (`_LegacyAliases.lua`) héritent automatiquement des mêmes IDs, ce sont
des références à la MÊME table, pas des entrées séparées. **Vérifié en
moteur, vrai Play Solo** : `[AnimationDriver]` loadout report —
`M1_1..4 OK len=0.50/0.57/0.63/0.83s` (et `Fighter_M1_1..4` identiques),
largement au-dessus du seuil 0.1s. Entrées ajoutées dans
`verified_assets.json` (status=VERIFIED) pour les 8 noms de slot. Commit
`a2c35fc`.

**2. Cancels — vérifié si le vrai upload corrige le timing "naturellement"
avant tout correctif séparé, comme demandé.**
Réponse : **PARTIELLEMENT.** Avec les vraies animations chargées, M1_1/M1_2
cessent d'émettre `[V1] WARN marker fallback` (leur marker réel arrive à
temps) et un premier cancel réussit enfin (0 succès avant → 1/4). Mais
`WARN marker fallback for M1_3` et `M1_4` **persistent** même avec les
vraies animations : la cause n'était pas "pas d'animation réelle", c'était
`MoveData.lua`'s `recovery` (0.34/0.45) plus court que le marker `Impact`
propre de `Combat.lua` (0.3667/0.4667) — la course était perdue avant même
de regarder l'animation. **Correctif appliqué (commit `901213b`)** :
`M1_3.recovery` 0.34→0.42, `M1_4.recovery` 0.45→0.52. Session Play Solo
relancée à zéro, re-testé avec 8 tentatives réelles (sondage
`Heartbeat` frame-parfait) : **3/8 réussies**, contre 0/4 puis 1/4 avant.
Succès reproductibles sur M1_2/M1_3 à tier "chargé". M1_1 et M1_4 ratent
encore par moments même en sondage parfait — **progrès réel et mesuré, pas
encore 100% fiable.** Root cause exacte identifiée si besoin d'aller plus
loin : marge de M1_1 à tier2 semble insuffisante face à la latence de
polling ; à creuser en session dédiée si le taux de 3/8 ne suffit pas.

**3. Marche du Titan avec vrai input directionnel — dérive latérale
confirmée réelle, PAS un artefact de test.**
Test avec `Humanoid:Move(direction, false)` réasserti à chaque frame
pendant tout le cast (reproduit fidèlement ce que fait le `ControlModule`
natif quand un joueur tient W) : **0 dégât, encore.** Le dépassement en Z
est bien corrigé (1.68 studs de trop contre ~7.7 avant, cohérent avec le
fix de vélocité résiduelle de l'entrée précédente) mais une **dérive
latérale en X quasi identique (~+7 studs) apparaît malgré un input tenu en
continu vers une cible alignée sur le même axe X que le joueur**. Conclusion
ferme : ce n'est pas un artefact d'absence d'input — c'est un vrai bug dans
le mécanisme des pas (`Skill3_MarcheDuTitan.lua`), cause non identifiée
(candidat le plus probable : les deux appels `applyStepImpulse` successifs
interagissent avec la physique du Humanoid d'une façon qui introduit une
composante latérale non voulue). **Non corrigé** — diagnostic net livré,
correctif à faire en session dédiée avec plus de marge d'investigation.

**4. Chemin disque pour les captures — RÉSOLU.**
L'outil de capture exposé par le harness ne touche jamais le disque, mais
`scripts/studiomcp_capture_animated.py` (déjà dans le repo, jamais utilisé
pour un besoin ad-hoc jusqu'ici) montre la voie : se connecter DIRECTEMENT
à `StudioMCP --stdio` (même binaire, même session Studio, connexion JSON-RPC
indépendante de celle du harness) et décoder soi-même le base64 retourné.
Script autonome écrit (`capture_demidieu_m1.py`), lancé pendant un vrai
combat M1 en cours : **2 PNG réels sur disque** (276KB/281KB), confirmés
visuellement avant publication. **Publiés sur le miroir public** (commit
mirror `f88f449`) :
- <https://raw.githubusercontent.com/broussemilan-beep/rrr/ba10f79638c7386fb9c02d88de6d3acb5954b2aa/progress/screenshots/2026-08-27_demidieu-m1-capture-1.jpg>
- <https://raw.githubusercontent.com/broussemilan-beep/rrr/ba10f79638c7386fb9c02d88de6d3acb5954b2aa/progress/screenshots/2026-08-27_demidieu-m1-capture-2.jpg>

**Commits de cette suite** : `a2c35fc` (upload+câblage+vérif animations),
`901213b` (fix recovery M1_3/M1_4).

---

## 2026-08-27 (suite 4) — Demi-Dieu Phase 4 (Ultimate), disque-seul, rien vérifié en jeu

Même consigne : disque-seul, même exigence d'honnêteté, décision bloquante
tranchée par défaut plutôt que laissée ouverte, et signaler explicitement
tout chemin partagé ou mécanique neuve — comme pour Jugement en Phase 3.

### Ce chantier touche un chemin partagé — signalé avant d'écrire le module

`MoveData.Skill5` (la touche R au-delà du slot 4) n'était pas un
emplacement libre : il appartenait déjà à l'ultimate d'un **autre**
personnage (`Ultimate_SaitamaAsura_Verdict`), gaté par un mécanisme
**complètement différent** de Momentum — `TransformController.IsTransformed()`,
un flag client posé par la touche Y. Ce système est **réellement vivant**
aujourd'hui (`TransformationService` s'initialise au boot, confirmé dans la
capture console Play Solo de la Phase 1) — pas du code mort à ignorer.

Un simple OR entre les deux conditions aurait créé une vraie collision : un
joueur ayant pressé Y (transformé) mais pas à 100 de Momentum aurait vu sa
touche R silencieusement rejetée par le nouveau module Ultimate au lieu de
lancer Jugement — une régression, pas un no-op propre. Remplacé
entièrement (même schéma que tous les autres swaps par défaut de cette
session : ancienne condition commentée, pas supprimée) plutôt que superposé.
Fichiers touchés par ce remplacement : `InputController.lua` (routage de la
touche R), `CombatController.lua` (nouvelle `IsUltimateReady()`, lit le
miroir Momentum déjà injecté en Phase 2 — aucun nouveau point d'accès à
Momentum créé), `MoveData.lua` (Skill5).

**À vérifier en premier au prochain Play Solo, avant le reste du module** :
le routage de la touche R lui-même. Si le routage est faux, rien du
mécanisme ci-dessous n'est même observable.

### Le module — `Ultimate_DescenteDuDemiDieu.lua`

« S'élève, suspend brièvement le combat, puis chute comme un projectile.
Impact = onde circulaire massive + cratère, puis relevé final. » Coût :
Momentum à 100, consommé entièrement — vérifié en premier et de façon
atomique via `MomentumService.TryConsumeForUltimate` (posé et testé dès la
Phase 1) : si ça échoue, rien d'autre ne s'exécute, pas même le cooldown
de sécurité.

- Montée puis chute : même mécanisme `LinearVelocity` + `Attachment` que
  `Skill1_DashStrike.lua`/`Skill3_MarcheDuTitan.lua`, noms d'objets propres
  (`UltimateRise`/`UltimateFall`) pour ne jamais entrer en collision.
- i-frames pendant toute la phase aérienne (`CombatStateService.SetIFrames`)
  — cohérent avec le reste du projet, évite de punir un joueur suspendu en
  l'air sans defense.
- Ciblage : « onde circulaire massive » est réellement circulaire, pas un
  cône avant — `HitboxService.ComputeTargets` (la convention du reste du
  dossier) ne peut pas exprimer ça, une boîte ne peut pas être un cercle.
  Utilisé un calcul de distance manuel à la place — délibérément pas
  `GetPartBoundsInRadius` (interdit par la règle B3 du scanner du projet
  pour tout hitbox de combat) ni `GetPartBoundsInBox` (ne peut pas être
  circulaire sans déborder aux coins ou sous-couvrir en diagonale).
- Knockback radial (loin du centre du cratère), pas une direction unique —
  cohérent avec « onde de choc ».
- Dégâts 50, stun 1.8s, rayon 14 studs, cooldown de sécurité 3s (Momentum à
  100 est le vrai verrou, pas ce cooldown).

**Piège de scanner retrouvé, cette fois dans mon propre commentaire** : le
scanner fait du texte brut, pas de l'analyse Lua — il a détecté la chaîne
`GetPartBoundsInRadius` **dans le commentaire qui explique pourquoi je ne
l'utilise pas**, l'a pris pour du vrai code, et a bloqué le commit.
Reformulé sans citer le nom littéral de la fonction. Aucune règle nouvelle
apprise ici (déjà su que le scanner est du texte brut depuis le piège B12
sur les blocs Toji commentés en Phase 3), juste une nouvelle façon de s'y
faire prendre.

### Tests

Aucun spec dédié pour `Ultimate_DescenteDuDemiDieu.lua` lui-même — même
précédent que Skill1/2/3 en Phase 3 (fortement couplé à `Workspace`/
`Instance`, pas de sous-module pur à en extraire comme `JugementWindow`).
`MomentumService.spec.lua` (Phase 1) couvre déjà `TryConsumeForUltimate` à
exactement 100 vs 99 — le vrai verrou de cette compétence, pas dupliqué ici.

`stylua` + `selene` + `scan_recurring_bugs.py --staged` propres sur tous
les fichiers.

### Honnêtement non vérifié

**Rien de ce tour n'a tourné.** Le routage de la touche R (le point le
plus fragile, cf. ci-dessus) et le calcul de distance radiale sont
raisonnés sur papier, pas exécutés.

### Bloqué, en attente du retour de Milan

- Toute vérification Play Solo — Phases 2, 3 et 4 comprises.
- Rojo, Cmd+S — toujours reportés par Milan.
- Décision M1/Skills/Ultimate Toji-Saitama vs Demi-Dieu — appliquée par
  défaut sur toute la ligne maintenant (M1, 4 compétences, ultimate),
  réversible, à confirmer à la vérif.

**Les 4 phases du plan Demi-Dieu sont maintenant toutes écrites** (Momentum,
M1, Dash, Cancels, 4 compétences, Ultimate). Rien n'a tourné une seule fois
en dehors des tests réels de la Phase 1 (avant que Rojo/Cmd+S soient
reportés). La prochaine session Play Solo a du pain sur la planche, dans
l'ordre de risque : Jugement (chemin `DamageService.Apply` partagé) →
routage R de l'Ultimate → le reste.

---

## 2026-08-27 (suite 3) — Demi-Dieu Phase 3 (les 4 compétences), disque-seul, rien vérifié en jeu

Consigne inchangée : continuer sans Studio ni Rojo, même exigence
d'honnêteté (papier ≠ vérifié), et cette fois : trancher la décision M1
Toji-vs-Demi-Dieu par défaut (cohérent, réversible) plutôt que la laisser
en suspens.

### Décision appliquée — M1 et Skills, Demi-Dieu = kit par défaut, réversible

`AnimationDB/Combat.lua` (M1_1..4) ET `MoveData.lua` (Skill1..4) basculés sur
Demi-Dieu. Chaque ancienne entrée (Toji M1, Chasseur Fantôme, Torrent
Carnassier, Annihilation Lite, HeavyFinisher) est commentée juste en dessous
de la nouvelle, pas supprimée — un reverse est un copier-coller d'un bloc,
pas une ré-autorisation. Les anciens modules serveur
(`Skill1_DashStrike.lua` etc.) restent intacts sur disque, juste plus
référencés par `MoveData`. Les 4 nouvelles animations M1 utilisent les seeds
hand-keyées de la Phase 1 (gates déjà passées) ; aucune n'est uploadée.

### Recentrage de périmètre, assumé explicitement

Contrairement à la chaîne M1 (Phase 1), **aucune animation n'a été
hand-keyée pour les 4 compétences ce tour**. Raison : une entrée
`PENDING_UPLOAD` non uploadée se comporte de façon strictement identique
qu'elle soit issue d'un hand-keyer soigné ou d'un simple placeholder —
`AnimationService.LoadTrack` retombe sur le générateur procédural dans les
deux cas, et je ne peux vérifier ni l'un ni l'autre sans Studio. La Phase 3
a donc porté sur la **mécanique réelle** (modules serveur, `MoveData`,
câblage Momentum), pas sur l'authoring — même logique de périmètre que la
Phase 2, qui n'avait pas eu besoin de nouvelles animations non plus.

### Les 4 compétences — `src/server/Skills/`

**Skill1 (F) — Main du Colosse** (★★☆☆☆) : un seul coup horizontal large,
`HitboxService.ComputeTargets` (le helper partagé, pas une resweep à la
main comme le font les anciens modules Skill1/Skill2 malgré leur propre
commentaire TODO qui dit le contraire). Dégâts 20, cooldown 5s.

**Skill2 (G) — Frappe Céleste** (★★☆☆☆) : frappe au sol courte portée. Le
palier Momentum « surchargé » élargit la zone de x1.5 (rayon, pas dégâts —
exactement ce que le spec §2 demande), lu une fois à l'Impact via
`MomentumService.GetTier(player)`.

**Skill3 (H) — Marche du Titan** (★★★☆☆) : 2 pas lourds à impulsion (même
mécanisme `LinearVelocity` + `Attachment` que `Skill1_DashStrike.lua`
existant, nom d'objet différent pour ne jamais entrer en collision) puis
coup final. Palier « chargé »+ ajoute un 3e pas. Le coup final relit la
`HumanoidRootPart.CFrame` **au moment où il tire**, pas une direction
capturée au lancement — ce qui donne « orientable pendant le déplacement »
gratuitement, sans système de visée séparé. Bug trouvé et corrigé avant
lint : au palier chargé (3 pas), la résolution serveur tombe à 1.05s mais
`recovery` client était à 0.90s — le joueur aurait pu ré-agir avant que son
propre coup final atterrisse. `recovery` remonté à 1.10s.

**Skill4 (R) — Jugement** (★★★★☆) : la seule des 4 qui demandait une vraie
architecture neuve. Confirmé par investigation avant d'écrire une ligne :
**aucun mécanisme de parade/contre ne vit dans ce projet.**
`BlockService.lua` existe mais est mort (rien ne le require, son
équivalent client est un stub 2 lignes « legacy runtime disabled ») — pas
réutilisé, ni pour éviter de ranimer du code non vérifié ni parce que
c'est un mécanisme de blocage (réduit/annule), pas une parade-contre.

Construit : `JugementWindow.lua` (état pur, fenêtre de 0.25s, extrait pour
être testable — même raisonnement que `DashCooldown.lua` en Phase 1) +
`Skill4_Jugement.lua` (active la fenêtre, expose `TryConsumeParry`).
Nouveau point d'intégration : `DamageService.Apply` gagne un 4e paramètre
optionnel (`attacker: Model?`, rétrocompatible — un appelant qui l'omet
se comporte exactement comme avant) et consulte `TryConsumeParry` avant
d'appliquer les dégâts ; `CombatService.server.lua` passe `char` à ses deux
sites d'appel existants. Sur une parade réussie : dégâts de la victime
annulés, contre-coup fixe (25 dégâts) + projection sur l'attaquant,
`MomentumService.OnJugementSuccess` (+25, le hook posé en Phase 1 attendait
exactement ça).

**Trois limitations documentées explicitement dans le code, pas cachées :**
- Le hook n'intercepte que les dégâts qui passent par `DamageService.Apply`
  (les M1, oui). Les compétences (les 4 nouvelles ET les anciennes déjà en
  place) infligent leurs dégâts en direct via `humanoid:TakeDamage(...)`,
  **sans jamais passer par `DamageService`** — un vrai gap déjà présent
  avant ce tour, pas introduit par Jugement. Parer une attaque de
  compétence adverse ne marchera pas aujourd'hui.
- « Mange le combo entier » sur une parade ratée n'est **pas** implémenté —
  toucherait l'état privé de combo de `CombatService.server.lua`, jamais
  exposé nulle part. Le « gros recovery » (moitié réellement demandée) l'est
  (`recovery = 1.30s`, la plus haute des 4 mouvements Demi-Dieu).
- Une parade réussie ne débloque pas les touches du joueur en avance — même
  limitation d'asymétrie de recovery déjà notée pour Pas Divin en Phase 1 ;
  demanderait un nouveau signal serveur→client, pas ajouté ce tour.

### Tests

`tests/JugementWindow.spec.lua` — 8 cas sur l'état pur (fenêtre ouverte/
fermée/à la frontière, consommation unique, "raté" vs consommé, `Clear`,
ré-ouverture, deux joueurs indépendants). `MomentumService.spec.lua`
(Phase 1) couvrait déjà `OnSkillResolved`/`OnJugementSuccess` — pas
dupliqué ici.

`stylua` + `selene` + `scan_recurring_bugs.py --staged` (le vrai mode du
hook, pas `--files` qui scanne le fichier entier et fait remonter une
fausse alerte sur une ligne pré-existante de `CombatService.server.lua`
jamais touchée par mon diff — piège évité, pas re-tombé dedans) propres sur
tous les fichiers.

### Honnêtement non vérifié

**Rien de ce tour n'a tourné**, ni en Play Solo ni même les specs TestEZ
(confirmé en Phase 2 : aucun moyen de les lancer hors Studio dans ce
projet). Jugement est, de loin, la pièce la plus à risque : c'est de la
mécanique neuve, sans aucun précédent vivant dans le code à copier, et le
hook `DamageService.Apply` touche un chemin que TOUT dégât M1 emprunte —
si quelque chose s'y casse, ça casse le combat entier, pas juste Jugement.
**À vérifier en premier** à la prochaine session Play Solo, avant tout le
reste de la Phase 3.

### Bloqué, en attente du retour de Milan

- Toute vérification Play Solo — Phases 2 et 3 comprises, rien n'est dans
  la place.
- Connexion Rojo, Cmd+S — toujours reportés par Milan.
- Décision M1/Skills Toji vs Demi-Dieu — appliquée par défaut cette fois
  (pas laissée en suspens), réversible, à confirmer à la vérif.
- Phase 4 (Ultimate) — pas commencée ; dépend de A (Momentum,
  `TryConsumeForUltimate` déjà prêt depuis la Phase 1) — écrivable de la
  même façon disque-seule si Milan le souhaite.

---

## 2026-08-27 (suite 2) — Bug TrainingDummies corrigé, Phase 2 (Cancels) écrite, tout non vérifié en jeu

Session en deux temps : Milan reprend la main sur Rojo/Cmd+S lui-même une
fois de retour chez lui, pas maintenant. Consigne : continuer ce qui ne
demande ni Studio ni Rojo, dire clairement ce qui est bloqué. Rien de ce tour
n'a été poussé dans la place ni testé en Play Solo — c'est le prix assumé de
cette consigne, pas un oubli.

### Bug corrigé — `TrainingDummies.server.lua`

Celui trouvé et contourné pendant la vérification de la Phase 1 (mannequin
flottant 7 studs au-dessus du sol, Y codé sur l'ancienne île). Remplacé par
le même raycast que `DummyService.server.lua` utilise déjà (`findGroundY`),
déplacé après le `WaitForChild("ArenaFracturee", 30)` existant (relocalisé
depuis le bas du fichier) pour qu'il ait un sol à toucher. Commit `9e52af9`.

### Phase 2 — Cancels, écrite intégralement, aucune dépendance Studio pour l'écrire

Dépend de A (Momentum) + B (chaîne M1), tous deux prêts depuis la Phase 1 —
pas de parallélisation nécessaire, un seul fil de travail.

**Découverte avant d'écrire une ligne** : le dash actuel (`DashController.
TryDash()`, appelé depuis `InputController.lua` sur Q) n'avait **aucune**
conscience de l'état M1 — un joueur pouvait déjà annuler sa recovery M1 en
dashant à N'IMPORTE QUEL palier de Momentum, y compris 0. Ce n'était pas
juste une fonctionnalité manquante : c'était l'inverse de la règle du spec
(« 0-33 éteint : rien n'est bridé » suppose une base sans annulation à
débrider, pas une base déjà permissive). Corrigé en même temps que l'ajout
du vrai système d'annulation.

**Mécanique implémentée** (`CombatController.lua`, `InputController.lua`,
`V1/init.client.lua`) :

- Fenêtre d'annulation ouverte à l'Impact d'un coup M1, 0.2s, seulement si
  le palier Momentum (lu sur `Momentum.GetTier()`, le vrai miroir client
  server-authoritative de la Phase 1) l'autorise : palier 1 (chargé)
  seulement après le 2e ou 3e coup, palier 2 (surchargé) après chaque coup,
  palier 0 jamais.
- `CombatController.IsBusy()` / `TryCancelIntoDash()` exposés ;
  `InputController`'s Q ne déclenche `DashController.TryDash()`
  qu'après l'accord explicite de `TryCancelIntoDash()` si un M1 est en
  cours — sinon comportement Q inchangé (dash libre hors combat).
- **Aucun changement serveur nécessaire** : `CombatService.server.lua`
  accepte déjà n'importe quel `sentStep` dans [1,4] et snap son compteur de
  combo dessus (règle « forgiving » du v7 Phase 0c.3) — annuler en dash
  revient juste à envoyer moins/différemment de `CombatRequest`, ce que le
  serveur absorbe déjà.
- Jeton d'annulation par tentative (`_cancelFlag = { canceled = false }`)
  pour qu'un timer de recovery périmé, s'il se déclenche après une
  annulation, ne réinitialise pas un état qu'une tentative plus récente
  possède déjà.
- Tout le câblage échoue **ouvert** vers l'ancien comportement (vérif
  d'existence de fonction avant chaque appel) plutôt que fermé — une copie
  partielle ou périmée de `CombatController` ne peut pas bloquer la touche
  Dash, seulement lui retirer la capacité d'annulation.

Fichiers : `src/client/V1/CombatController.lua`,
`src/client/V1/InputController.lua`, `src/client/V1/init.client.lua`,
`tests/CombatController_Cancels.spec.lua` (5 cas, mocks — palier 0 jamais,
palier 1 pas au coup 1, palier 1 au coup 2 utilisable une fois puis épuisé,
expiration de la fenêtre à 0.2s, palier 2 dès le coup 1). Au passage,
supprimé 3 déclarations mortes pré-existantes dans `CombatController.lua`
(`Players`, `SKILL_KEYS`, `SKILL_BINDS`, jamais utilisées) — sans ça le hook
pre-commit bloque sur n'importe quel avertissement `selene` du fichier
entier, pas seulement sur le diff ajouté (même piège que la Phase 1).

`stylua` + `selene` + `scan_recurring_bugs.py` propres sur les 4 fichiers.

### Honnêtement non vérifié

**Rien de ce tour n'a tourné.** Ni en Play Solo, ni même le spec TestEZ —
confirmé qu'il n'existe aucun moyen de lancer un `.spec.lua` (TestEZ) hors
Studio dans ce projet : `tests/run_all.sh` ne lance que les
`tests/test_*.luau` (couche Lune, smoke tests structurels), pas la suite
TestEZ, qui a besoin du Test Service de Roblox. Le raisonnement sur le
timing (recovery M1_1 = 0.34s, fenêtre 0.2s, `ComboResetTime` = 1.0s) a été
vérifié à la main contre les vraies constantes du projet, pas supposé — mais
« vérifié sur le papier » n'est pas « vérifié en jeu ».

### Bloqué, en attente du retour de Milan

- **Toute vérification Play Solo** — Phase 2 (Cancels) et le fix
  `TrainingDummies` compris. Rien de tout ça n'est dans la place, disque
  seulement.
- **Connexion du plugin Rojo** et **Cmd+S** — reportés explicitement à plus
  tard par Milan, pas oubliés.
- **Décision sur les M1 Toji vs Demi-Dieu** dans `AnimationDB/Combat.lua` —
  toujours en attente, inchangée depuis la Phase 1.
- Phase 3 (les 4 compétences) et Phase 4 (Ultimate) — pas commencées ;
  Phase 3 ne dépend que de A (Momentum), pourrait être écrite de la même
  manière disque-seule si Milan le souhaite avant son retour.

---

## 2026-08-27 (suite) — Demi-Dieu Phase 1 : construit, poussé à la main, vérifié en jeu réel

Trois agents en parallèle (MomentumService+miroir, chaîne M1 4 coups, dash Pas
Divin), chacun vérifié indépendamment (fichiers réels, `require` réel, lint
propre) avant confiance — l'un des trois (M1) a correctement refusé d'écraser
les animations Toji déjà vérifiées et a remonté la décision plutôt que de
trancher seul.

### Rojo hors service — poussé à la main via Luau

`rojo serve` tournait mais le plugin Studio (`Rojo_autoReconnect: false`)
n'avait plus retenté de connexion depuis 15:59 — confirmé par le journal
Studio (dernière ligne `34872` avant le début de la Phase 1). Aucun des
10 fichiers de la Phase 1 n'était donc dans la place. Poussés un par un par
`execute_luau`, en répliquant exactement le mapping `default.project.json`
(`src/server` → `ServerScriptService.Server`, etc.), source embarquée en
chaîne longue Lua avec niveau de crochets calculé pour éviter toute collision.

### Un vrai test Play Solo a trouvé une vraie régression

Premier Play Solo après le push : le terrain est remonté à **20.6 % de voxels
solides** — quasiment le défaut d'avant la correction de l'île. Cause : la
suppression d'`IslandGenerator.server.lua` n'avait été faite que **sur
disque** (`git mv` vers `disabled/`) au tour précédent ; jamais poussée dans
la place réelle faute de sync Rojo. Le script existait donc toujours,
intact, dans `ServerScriptService.Server.World`, et Play Solo clone l'état
Édition à chaque lancement — il régénérait l'île et le terrain à chaque
partie. Confirmé, corrigé (`IslandGenerator:Destroy()` en direct + push des
3 scripts re-séquencés sur `ArenaFracturee`), re-testé : terrain à
**0.00 %**, `IslandRoot` absent, aucune régénération.

C'est exactement le genre d'écart que la règle « vérification Play Solo
réelle, pas le rapport qui fait foi » est censée attraper — et elle a
attrapé une régression sur **mon propre** travail d'arène, pas seulement
sur celui des agents.

### Vérification fonctionnelle réelle — piège d'outillage découvert au passage

Interroger `MomentumService.Get(joueur)` via des appels `execute_luau`
isolés retournait obstinément 0 après de vrais coups qui infligeaient bien
des dégâts (988/1000 PV après 2 coups) — **piège d'outillage** : chaque appel
`execute_luau` obtient sa propre instance `require()`, séparée de celle que
`CombatService.server.lua` a chargée une fois au démarrage. Prouvé en isolant
un appel `OnAttackResolved` + `Get` dans le **même** `execute_luau` (0 → 6,
cohérent) contre un `Get` séparé sur l'état réellement vivant (toujours 0).
**À retenir pour toute vérification future** : ne jamais lire l'état d'un
service en re-`require`-ant depuis `execute_luau` — écouter le vrai
`RemoteEvent` réseau à la place, qui lui ne connaît pas cette isolation.

Une fois corrigé, vérification bout-en-bout par de vrais remotes réseau
(clic gauche simulé sans effet — `user_keyboard_input` sur `MouseLeftButton`
n'a jamais déclenché `InputController` ; remplacé par `CombatRequest
:FireServer(...)`, le même appel que fait le vrai contrôleur) :

```
2 coups M1 réels sur un mannequin  -> dégâts 1000 -> 988 (2 x 6, confirmé)
Momentum, écouté sur le vrai remote -> premier push après un coup : 6
                                     -> décroissance -8/s mesurée sur les pushs suivants
Dash t=0.00  -> accepté (silencieux)
Dash t=0.33  -> REJETÉ  reason=on_cooldown  (fenêtre 0.55s respectée)
Dash t=0.70  -> accepté (silencieux)
Dash + M1_4 sous 1.2s -> +31 en un push = 6 (coup) + 10 (chaîne M1 complète,
                          comboStep était à 4) + 15 (dash converti) — les 3
                          bonus se sont cumulés correctement en une seule
                          requête réelle
```

Terrain 0.00 %, `IslandRoot` absent après un Play Solo complet, 0 erreur
dans `PlaytestReporter` (`errors: []`), seul avertissement = `PasDivin`
(animation non uploadée, attendu et documenté).

### Bug trouvé, non corrigé — hors périmètre de ce tour

`TrainingDummies.server.lua` (le mannequin singulier, pas ceux de
`DummyService`) a un `DUMMY_HRP_Y` calculé sur l'ancien sol de l'île
(`SURFACE_Y = 7`), jamais mis à jour depuis le passage de l'arène à
`BASE_Y = 0` — le mannequin flotte 7 studs au-dessus du sol réel. Découvert
en essayant de le viser pour le test M1 (raté systématiquement malgré une
portée de 6 studs et une cible à 4). Contourné en ciblant un mannequin de
`DummyService` à la place (qui se cale au sol par raycast, donc insensible
au problème). Le fix est mécanique (remplacer la constante par un raycast,
comme `DummyService` le fait déjà) mais n'a pas été fait — hors périmètre
de la vérification Demi-Dieu.

### Ce qui reste UNVERIFIED, honnêtement

Les 5 animations (M1_1..4, PasDivin) sont hand-keyées et passent les gates
géométriques (M1 : direction FORWARD/classe correcte sur les 4 ; Pas Divin :
direction FORWARD confirmée sur la courbe brute, mais pas de gate dédié aux
déplacements). Aucune n'est uploadée — `PENDING_UPLOAD_*`, `status =
"UNVERIFIED"` partout, conforme à la règle anti-hallucination. `M1_1..4`
actuels dans `AnimationDB/Combat.lua` restent ceux de Toji (vérifiés,
uploadés) — pas écrasés, décision en attente de l'utilisateur.

### Toujours en suspens

- Sauvegarde Studio (Cmd+S) et connexion manuelle du plugin Rojo dans
  Studio — aucun des deux n'a abouti au moment d'écrire ceci.
- Le bug `TrainingDummies` Y ci-dessus.
- Le remplacement (ou non) des animations M1 Toji par celles de Demi-Dieu.

---

## 2026-08-27 — Cycle de vie Studio, 3 décisions arène, et les deux défauts fermés, 3 décisions arène, et les deux défauts fermés

Quatre tours, quatre rapports : `artifacts/STUDIO_LIFECYCLE_2026-08-27.md`,
`artifacts/STUDIO_PLUGINS_DIAG_2026-08-27.md`, `artifacts/ARENE_DECISIONS_2026-08-27.md`.
Résumé ici, détail chiffré dans ces fichiers.

### Studio fermé n'est pas gratuit à relancer

Objectif : arrêter Studio entre deux tâches (pâte thermique changée, mais la
chaleur inutile reste à éviter). Mesuré : Studio ouvert = 19-34 % CPU en continu
juste pour le viewport, fermé = 0 %. Coût du cycle : ~5 s à l'ouverture, ~2 s à
la fermeture — négligeable.

Mais **rouvrir Studio ne suffit pas à le rendre pilotable**. Deux lancements ont
échoué avec `Invalid Launch Intent` (le `placeId` utilisé était en réalité un
gameId — le vrai est `73755316903092`, recoupé sur les `AutoSaves` et les
`Rojo_priorEndpoints`). Un premier diagnostic croyait les 4 plugins tiers
(Weppy/Rojo/AnimExport/rodeo) absents de tout lancement — **c'était une erreur
de mesure** : Roblox charge les plugins utilisateur sous le préfixe `user_`,
distinct de `builtin_`/`sabuiltin_`, et mon filtre ne cherchait ni l'un ni
l'autre correctement. Une fois la bonne place ouverte à la main, les 4 plugins
chargent normalement (`builtin_=49`, les 4 `user_*` présents) — pas de bug Rojo
isolé, contrairement à l'hypothèse de départ.

Rojo a quand même été réinstallé (`rojo plugin install`, 7.6.1) par précaution ;
sauvegarde de l'ancien binaire conservée. Sans effet direct puisque le vrai
problème était la place jamais ouverte, mais sans risque non plus.

### Les 3 décisions, exécutées et vérifiées dans la place

1. **Île supprimée, `BASE_Y` 300 → 0.** `Terrain:Clear()` puis translation
   −300 en Y de l'arène et de son entourage (418 parts, 0 perdue). Terrain
   avant 21.3 % de voxels solides autour de l'origine, après 0.00 %.
   `IslandGenerator.server.lua` déplacé vers `disabled/` (sinon il régénère le
   terrain à chaque démarrage serveur). Trois scripts qui attendaient
   `IslandRoot` re-séquencés sur `ArenaFracturee` (`DummyService`,
   `TrainingDummies`, `SetupLighting`) — sans ça, 30 s de blocage au démarrage
   pour rien. `RaceClassService.lua` a la même attente bloquante mais n'est
   chargé par aucun service en mode V1 actuel — laissé tel quel, à traiter
   avant tout retour au `ServiceLoader`.
2. **Dôme + murs de Map Detailing supprimés.** Le dôme mesurait 2013×1895×1935
   studs — son bord passait à 187 studs du centre de l'arène malgré un centre
   à 1193 studs, d'où l'occupation d'un quadrant entier du ciel. 12 BaseParts
   supprimées (`Sphere`, `Main Wall`, tout `Dividers`), `Map Detailing` 178 →
   98 descendants. Capture avant/après : ciel bleu dégagé.
3. **Échelle : pas touchée, verdict confirmé plutôt que supposé.** Capture à
   hauteur d'œil réelle (y=5.5, mesure R6, pas une estimation) : l'arène ne se
   lit plus d'un coup d'œil. Relief solide max 11.0 → 16.0 studs, platitude
   16:1 → 11:1, parts au-dessus de l'œil 8/154 → 56/170, bandes radiales vides
   5 → 2. L'impression de petitesse n'est pas confirmée à cette hauteur : par
   consigne, `PLAYABLE_RADIUS` reste à 88, aucun recalcul par ratios.

### Les deux défauts restants, fermés ce tour

**Bande r80-90 vide** — dernière bande radiale sans relief après les
corrections ci-dessus (mesuré : 0 part de plus de 2 studs). Fermée avec le même
prop qui avait déjà comblé r60-70 : une colonne de plus, un anneau plus loin,
pas un nouvel élément. Paire diagonale-symétrique à r=83, theta 10°/80°
(6 studs de diamètre, 14 de haut, Marbre — géométrie et couleur identiques à la
colonne extérieure existante), mirée sur les 4 quadrants = 8 colonnes. Mesuré
après : r80-90 passe de 0 à **8 parts**.

**`Fire Arrow` × 2** — `UnionOperation` orange (rgb 213,115,61) au bord de
l'arène (r=90), rig VFX complet (~40 descendants : particules, beams,
PointLight). Aucune référence dans le code (`grep` sur `src/` et `scripts/` :
zéro résultat). Supprimées plutôt que recolorées : un rig de flamme reteint en
violet-ardoise aurait été visuellement plus faux que la couleur d'origine, donc
moins propre à exécuter que la suppression. Une des deux instances était déjà
hors-monde (y = −2 668 834) — reliquat cassé, aucune perte réelle. Mesuré
après : **zéro** couleur chaude dans un rayon de 200 studs autour de l'arène.

Édits faits en double : sur `src/shared/Arena/ArenaSpec.lua` (source de
vérité, avec le commentaire expliquant le choix de placement) et en direct dans
la place via Luau, avec la même géométrie que produirait `ArenaBuilder.Build()`
— **pas** un appel à `Build()` lui-même, parce que le module `ArenaSpec` chargé
en mémoire par la place lisait encore `BASE_Y = 300` au moment des mesures :
`rojo serve` ne tournait pas cette session (`ConnectFail` sur le port du plugin
dans le journal Studio), donc aucune synchronisation automatique. `rojo serve`
relancé en tâche de fond à la fin de ce tour pour la suite ; la connexion du
plugin dans Studio reste à faire à la main, je n'ai pas les moyens de cliquer
dans l'interface.

### Ouvert

- Studio ouvert avec des changements non sauvegardés depuis plusieurs heures ;
  sauvegarde demandée à la personne physiquement présente, non confirmée par le
  journal Studio au moment d'écrire ceci (aucune ligne de sauvegarde/publication
  après l'ouverture de la place).
- `rojo serve` tourne mais le plugin Studio n'est pas connecté — resync manuel à
  faire.
- `RaceClassService.lua` : boucle d'attente infinie sur `IslandRoot`/`IslandSpawn`,
  dormante en mode V1, à corriger avant réactivation du `ServiceLoader`.

---

## 2026-08-26 — §18-6/7/8 : le disque, et le miroir public réparé pour de bon

`52a1143`

Deux chantiers en parallèle, découpés par **propriété de fichiers** pour qu'aucun
conflit d'écriture ne soit possible : un agent sur toute la chaîne de publication,
moi sur `src/shared/Arena/*`.

Captures de ce tour (résoudre la base courante via `LATEST.md`, cf. plus bas) :
`2026-08-26_capture-disc-fixed.jpg`, `2026-08-26_capture-materials-eye.jpg`,
`2026-08-26_capture-plate-closeup.jpg`.

### §18-6 — le carré devient un disque

Le §1 demandait une forme « presque circulaire ». Le premier graybox posait un
**carré** de 180×180. Les lignes de vue et la symétrie étaient justes, la
**forme** était simplement fausse — aucune mesure ne pouvait le dire, la première
capture l'a dit.

Sol en anneaux concentriques (8 / 16 / 16 segments sur les rayons 0-30, 30-56,
56-78, périphérie 78-88). Sert le §1 **et** les « motifs circulaires » du §17. Les
comptes de segments sont des multiples de 4 : la symétrie d'ordre 4 devient une
propriété du générateur, le miroir n'a plus à reproduire le sol.

**Deux défauts, aucun visible à l'œil :**

1. Boîtes dimensionnées sur le rayon **médian** — une boîte droite tenant lieu de
   secteur annulaire est la plus large où l'arc est le plus long, d'où des trous
   en coin externe.
2. Et le vrai : **la convention d'axe était inversée**. Avec
   `CFrame.Angles(0, -a, 0)`, le X **local** d'une Part tombe sur la direction
   **radiale**, pas tangentielle. Un secteur annulaire s'écrit donc
   `Vector3.new(radial, épaisseur, tangentiel)` — l'inverse de la lecture
   intuitive. À l'envers on construit une rosace au lieu d'un anneau. La même
   erreur était dans le monument, la périphérie et l'anneau suspendu.

`CheckFloorHoles` (raycasts sur grille polaire) : **183 trous** au premier disque,
**0** après le fix d'axe. Sans lui la map partait avec des trous où l'on tombe.

### §18-7/8 — et l'image a corrigé mon propre diagnostic

J'avais rapporté que les plaques fracturées se lisaient comme des panneaux plats.
**Faux.** Le gros plan montre que les dalles inclinées sont l'élément qui se lit
le mieux. Les rectangles blancs étaient les **pads de spawn**, qui portaient le
pâle du monument et le concurrençaient.

**Le vrai défaut** : une plaque **flottait dans le vide**. Les coordonnées Q1 sont
cartésiennes et l'arène est ronde — `(74, 74)` se lit « près du bord » et vaut
**r = 104.7** contre un disque de 88. Trois plaques rentrées à r 77.7–79.2.

`CheckOverhang` ajouté, et il a fallu **deux corrections avant qu'il soit fiable** :
lancé depuis sous chaque Part il rapportait 38 faux positifs (l'origine était
*dans* la dalle, et un raycast Roblox n'accroche pas la Part où il démarre) ; puis
il signalait les 8 murs posés légitimement **sur une plaque** — une plaque
déplacée *est* du sol.

**Et une erreur à moi** : le commit `14e6a07` affirmait que les pads avaient pris
l'accent chaud. Ils ne l'avaient pas — toujours `rgb(214,208,226)`. Mon
remplacement visait un appel d'une ligne que stylua avait reformaté sur sept :
il n'a rien matché, en silence. Corrigé et **mesuré sur l'arène construite** :
`pad rgb(186,138,96) | monument rgb(214,208,226) | distincts = true`.

```
154 parts | centre 8/8 | opposés 8/8 | trous 0 | porte-à-faux 0
§18-5 rejoué sur le disque : chaîne M1 complète, traversée r=42.4 -> r=12.4
franchissant la limite d'anneau à r=30 sans chute, 0 erreur
```

**§18-9 non faite volontairement.** Le §17 exige que les VFX d'environnement ne
gênent jamais la lisibilité PvP — vérifiable seulement en playtest avec des
pouvoirs qui n'existent pas encore.

### Le miroir public : deux caches, pas un échec de sync

Ce n'était pas un échec de synchronisation. **Deux caches indépendants**, tous
deux mesurés :

- **Fastly sur les URLs de branche.** `max-age=300` et **GitHub ne purge pas au
  push** : sur une sonde V1→V2, V1 était encore servi à **T+242 s**. Le
  cache-busting `?t=<epoch>` **ne marche pas** (la query string n'est pas dans la
  clé de cache) et l'en-tête de requête `Cache-Control: no-cache` est **ignoré**
  — donc ma vérification « no-cache » d'un tour précédent ne prouvait rien.
- **Le cache du lecteur, et c'est le dominant.** `WebFetch` met en cache ~15 min
  et **ignore le `max-age`** de la réponse. Preuve au même instant, même URL :
  `curl → V2`, `WebFetch → V1`.

Puisque la couche 2 ignore les en-têtes serveur, **aucun réglage côté serveur ne
peut corriger ça**. Le seul levier est que la **chaîne d'URL change**. D'où des
URLs **épinglées au SHA** : une URL qu'aucun client n'a jamais lue, donc qu'aucun
cache ne peut détenir.

`progress/LATEST.md` est le point d'entrée à URL stable — il porte le
`content_commit`, un `generated_utc` et les URLs épinglées. Il reste cacheable,
mais il est **auto-daté** : la péremption devient *visible* au lieu d'être
silencieuse, et la chaîne se termine toujours sur du contenu immuable.

### Captures publiées

`scripts/sync_progress_log.sh [IMAGE ...]` publie sous `progress/screenshots/`.
Validation par **magic bytes, pas par extension** — vérifié indépendamment : un
`.lua` renommé en `.jpg` daté est refusé et le miroir reste propre.

### À utiliser désormais

**Point d'entrée** :
<https://raw.githubusercontent.com/broussemilan-beep/rrr/main/progress/LATEST.md>

### Correction — une capture publiée était périmée

Relecture de `2026-08-26_capture-disc-fixed.jpg` par le propriétaire : deux
plaques semblaient posées sur l'herbe, hors du disque. **L'observation était
juste ; l'image était périmée.** Elle datait de l'étape du fix d'axe, AVANT que
trois plaques soient rentrées dans le disque, et je l'avais publiée pour
illustrer un état postérieur déjà corrigé. Vraie sur son propre instant,
trompeuse comme preuve.

État réel mesuré sur l'arène courante :

```
bord du sol            r = 92.1
plaques, coin le plus loin  r = 86.7 a 87.2   -> les 12 sur le sol
```

Capture périmée **retirée du miroir public**, remplacée par
`2026-08-26_capture-disc-current.jpg`.

**Règle qui en découle** : une capture doit être prise après le build FINAL du
tour, pas au milieu d'une itération. Une image publiée est une preuve, et une
preuve datée d'un état intermédiaire ment sur l'état courant.

L'anneau suspendu du §5 a aussi été vérifié à la demande, avec deux cadrages
dédiés (`2026-08-26_capture-ring-from-ground.jpg`,
`2026-08-26_capture-ring-from-under.jpg`) : il se lit comme un cercle clair net
contre le ciel depuis le sol — la silhouette et l'outil d'orientation que le §5
demande. Les pads en accent chaud y sont visibles et distincts du marbre.

### Ouvert

- Décision île : effacer le Terrain et remettre `BASE_Y = 0`.
- Playtest multi-joueurs (§16 : 4-8 répartis) — le round-robin des spawns n'est
  toujours pas vérifié en conditions réelles.
- §18-9 (VFX d'environnement), en attente de pouvoirs jouables.
- Non établi par l'agent : les en-têtes réels de GitHub Pages (non activé) et le
  TTL exact de `WebFetch` (prouvé > 6 min, pas déroulé jusqu'à 15).

---

## 2026-08-26 — Spawns câblés, playtest §18-5 passé, capture réparée

`e9e1c93`

### 1. Pourquoi `screen_capture` timeout — trouvé en une commande

**La fenêtre Studio était minimisée** (`AXMinimized = true`). `execute_luau` n'a
besoin d'aucun rendu et continue de répondre ; `screen_capture` rend le viewport,
qui n'a plus de surface quand la fenêtre est réduite. D'où l'asymétrie exacte
observée.

**Précision utile sur la note existante** : arrière-plan ≠ minimisé. Studio peut
être **en arrière-plan** (une autre app au premier plan) et la capture marche —
c'était déjà mesuré le 2026-08-24. **Minimisé**, elle ne marche pas. Vérifié en
dé-minimisant : la capture est repassée du premier coup.

Remède : `osascript -e 'tell application "System Events" to tell process
"RobloxStudio" to set value of attribute "AXMinimized" of front window to false'`

### 2. La capture a immédiatement trouvé ce que les mesures ne voyaient pas

Première image de l'arène : **seuls les deux anneaux étaient visibles**. Le reste
était enterré dans le terrain natif de l'île existante — **47 % des voxels** d'une
boîte 200×60×200 autour du centre sont solides.

Les 130 Parts existaient, la symétrie était correcte, les lignes de vue mesurées
justes. Et la carte était invisible. Aucune de nos mesures ne pouvait le dire.

Arène relevée à `BASE_Y = 300` — réversible, et **la suppression de l'île reste
une décision du propriétaire, pas un effet de bord d'un graybox**. À remettre à 0
quand l'île partira (§1 et §15 interdisent le Terrain et font de cette arène le
monde unique).

### 3. Spawns câblés

`ArenaBootstrap.server.lua` préfère désormais les 8 pads de l'arène et retombe
sur `IslandSpawn` sinon — l'ancienne île continue de fonctionner jusqu'à sa
suppression.

Attribution **round-robin, pas aléatoire** : les huit pads sont symétriques par
construction (§14), et les distribuer dans l'ordre est la seule façon que cette
symétrie atteigne réellement les joueurs. Un tirage aléatoire réintroduit le
regroupement que le miroir existe pour empêcher. Le spawn oriente vers le centre.

### 4. Playtest §18-5 — M1 + dash uniquement

```
spawn          Spawn_1, 3.5 studs du pad, 42.4 du centre   (spec §13 : 35-50)
combo M1       M1_1, M1_2, M1_3, M1_4 — chaîne complète sur 4 clics
dash           7 déclenchements
locomotion     Idle x9, Walk x4, AthleticRun x2
erreurs        0   (hors les permissions d'assets pré-existantes)
chute          aucune — y=303 sur un sol à 300, hp 100
```

Vérification finale après relevage : `parts=130, spawns=8, y=300, centre 8/8
bloqué, opposés 8/8 bloqués`.

### Ce que l'œil dit et que la mesure ne disait pas

- La palette tient : violet-ardoise et marbre pâle, **clairement pas le
  beige/gris désertique** que le §17 désigne comme la contrainte de
  différenciation la plus importante.
- L'anneau suspendu fonctionne comme silhouette — lisible depuis le sol,
  reconnaissable.
- **Les plaques fracturées ne se lisent pas comme des fractures** : blanches sur
  violet, elles ressemblent à des panneaux posés à plat plutôt qu'à du sol
  déplacé. À reprendre à la passe matériaux (§18-7).
- **Le sol est carré, pas « presque circulaire »** comme le demande le §1. Les
  dalles forment un carré de 180×180 ; seule la périphérie est annulaire.

### Ouvert

- Décision île : effacer le Terrain et remettre `BASE_Y = 0`, ou garder les deux.
- Forme carrée contre §1.
- Lisibilité des plaques de fracture.
- Playtest multi-joueurs (§16 demande 4–8 répartis) — un seul joueur testé, donc
  le round-robin des spawns n'est pas vérifié en conditions réelles.
- §18 étapes 6–10 non faites.

---

## 2026-08-26 — L'Arène Fracturée : graybox V1 bâti et mesuré

`049f686`

Spec reçue (`artifacts/ARENE_FRACTUREE_spec.md`), étapes 1 à 4 de son §18 faites.

### Conflit de spec tranché, pas contourné

Le §3 demande quatre secteurs d'identités **différentes** (Nord dalle ouverte,
Est colonnes, Sud cour brisée, Ouest terrain fracturé) tandis que le §14 impose
le **miroir par quadrant**. Les deux ne peuvent pas tenir : le miroir produit
quatre quadrants identiques, donc un secteur cardinal ne peut pas avoir son
caractère propre.

Le §14 est marqué « confirmé par la recherche externe, pas juste pratique », et
l'équité dans un monde PvP libre est structurante — la symétrie l'emporte. Les
caractères de secteur sont conservés en **bandes radiales** : chaque quadrant
porte de la dalle ouverte près du centre, des colonnes à mi-rayon, des fragments
de mur au-delà, des plaques fracturées sur le pourtour. Chaque joueur rencontre
les quatre textures de jeu quel que soit son spawn.

### Bâti

- `src/shared/Arena/ArenaSpec.lua` — quadrant maître Q1 déclaratif
- `src/shared/Arena/ArenaBuilder.lua` — construction, miroir, spawns, outil §19

Le miroir est **du code, pas une étape de modélisation** : Q1 est écrit une fois,
Q2/Q3/Q4 en dérivent. Le lacet s'inverse sur un miroir à un seul axe et se
conserve quand les deux s'inversent (cette composition est une rotation de 180°,
pas une réflexion) — c'est le seul endroit où la transformation n'est pas un
simple changement de signe, et la source habituelle d'une carte discrètement
asymétrique.

```
parts = 130        spawns = 8        quadrants = 4
jouable = 180 x 180 studs
distance spawn -> centre = 42.4 studs   (spec §13 : 35-50)
```

**130 Parts** pour le graybox complet — le §15 s'inquiétait du budget, il y a de
la marge.

### L'outil de lignes de vue a trouvé un défaut réel, deux fois

C'est exactement ce que le §19 demandait, et il a servi immédiatement.

**Première mesure** : spawns 2 et 6 avec ligne dégagée vers le centre **et** l'un
vers l'autre, les six autres bloqués. Cause : les deux fissures du monument
étaient sur les segments 4 et 12 de 16, soit exactement 180° d'écart — un rayon
diamétral entrait par l'une et sortait par l'autre.

**Deuxième mesure**, fissures déplacées en 3 et 10 : opposés 8/8 bloqués, mais le
spawn 5 seul voyait le centre — la fissure 10 couvre 191–214° et le spawn 5 est à
199.3°.

**Placement final, dérivé au lieu d'être choisi à l'œil** : les huit spawns sont à
19.3, 70.7, 109.3, 160.7, 199.3, 250.7, 289.3 et 340.7° ; **tout segment impair**
évite ces angles. Fissures sur 3 (45°) et 9 (180°), 135° d'écart donc aucun rayon
diamétral ne traverse les deux.

```
centre bloqué  8/8   (uniforme = true)
opposés bloqués 8/8   <- exigence §13 satisfaite
```

L'uniformité compte plus que la valeur : aucun spawn n'a d'avantage systématique.

### Piège d'outillage noté

Le cache `require` de Studio a servi un module périmé après mise à jour de la
source : l'arène rebâtie gardait les anciennes fissures alors que la source était
correcte. Vérifié en comparant la source injectée aux Parts réellement présentes,
pas en supposant. Contournement : recréer les `ModuleScript` (changer l'identité
d'instance casse le cache).

### Ouvert

- **Capture visuelle non obtenue** : `screen_capture` a timeout deux fois de suite
  alors que Studio répondait à `execute_luau`. Non diagnostiqué. Les mesures sont
  complètes, l'œil ne l'est pas.
- Étapes §18 5–10 (playtest PvP, correction des volumes, matériaux, fractures,
  VFX) non faites — le §18 interdit explicitement de paralléliser 7–9 avant que
  1–6 soient validées en vrai playtest.
- `ArenaBootstrap.server.lua` attend un `IslandSpawn` : le câblage des 8 spawns de
  l'arène au flux de respawn n'est pas fait.
- L'arène vit dans la place Studio, pas encore synchronisée par Rojo.

---

## 2026-08-25 — Réglage fin + diagnostic de forme sur luffy

`a7565af`

### 1. Réglage sur les deux seeds à 3 % du plancher

Balayage serré du facteur d'échelle, ces deux seeds seulement.

| seed | avant | après | plancher | ratio | verdict |
|---|---|---|---|---|---|
| `spear_thrust_jinwoo` | 2.17 | **2.45** (k=8.70) | 2.25 | 0.75 | **PASS** |
| `M1_jab_toji` | 2.19 | 2.19 (k=5.30) | 2.25 | 0.99 | FAIL |

**`spear_thrust_jinwoo` passe.** Ce qui le bloquait n'était pas sa géométrie mais
mon plafond `k_max = 8.0` — une valeur devinée, jamais mesurée. Relevée à 12 ; le
pic réel du seed est à k≈10.25 pour 2.71 studs.

**`M1_jab_toji` ne passe pas, et c'est un vrai plafond.** La courbe monte puis
redescend (2.185 à k=5.25, 2.05 à k=6.25) : c'est un maximum, pas une saturation.
L'espace de tâche donne **2.191** — les deux méthodes convergent à 0.006 stud
l'une de l'autre, ce qui confirme une contrainte structurelle du seed et non un
défaut de méthode. Il reste 2.7 % sous le plancher.

**Corpus : 10/12 au vert.**

### 2. `devil_fruit_cast_luffy` — diagnostic, pas de réécriture

Trois défauts distincts, chacun mesuré :

**a) Le mouvement est latéral, pas frontal.** Au pic (frame 12, t=0.400 — pile
sur le marker `Whoosh`) :

```
avant   0.349 stud
latéral 0.803 stud      <- 2.3x plus que l'avant
vertical 0.092 stud
```

Pour atteindre le seuil de forme 0.67 il faudrait un hors-axe ≤ 0.387 stud ; on
est à 0.808. Le geste balaie de côté là où un `front_palm_cast` doit projeter
devant.

**b) Un saut de 2.57 studs en une image.** Entre f12 (t=0.400) et f13 (t=0.433),
le poignet gauche traverse : `dx` passe de −0.803 à +1.545. C'est un
téléport de 2.57 studs en 1/30 s, entre le `Whoosh` et le `Hit`. Aucune
interpolation ne rattrape ça — c'est un défaut d'écriture, pas de rendu.

**c) 26 % du clip est figé.** Les frames 6 à 11 (t=0.200 → 0.367) sont
rigoureusement identiques : 6 frames sur 23 à déplacement nul, juste avant la
frappe. Un temps de pose de 0.2 s peut être voulu, mais placé là il mange le
windup.

**Les deux bras sont mauvais**, ce n'est pas une erreur de sélection du poignet :

```
Right Wrist : avant max 0.216   latéral max 1.557   ratio 0.18
Left Wrist  : avant max 0.349   latéral max 1.545   ratio 0.40
```

**Cible de réécriture** : le geste doit projeter sur `−Z` au marker `Hit`
(t=0.4667), pas balayer sur X ; supprimer le hold f6–f11 ou le déplacer avant le
windup ; et lisser la transition f12→f13, qui porte à elle seule le tiers du
déplacement total du clip.

### Ouvert

- `M1_jab_toji` : 2.19 contre 2.25. Deux méthodes indépendantes plafonnent au même
  endroit — à investiguer côté structure du seed, pas côté amplification.
- `devil_fruit_cast_luffy` : diagnostiqué, pas réécrit.
- Rien n'est baké ni uploadé.

### Correction de process

Les entrées du journal étaient taguées `` `a7565af` `` au lieu d'un SHA : le
dernier commit visible dans le journal **publié** restait donc `e1385da` alors que
trois commits avaient suivi. Corrigé, et `sync_progress_log.sh` estampille
désormais le SHA du HEAD automatiquement.

À noter pour lever une ambiguïté : **le dépôt MyAnimeRPG n'a aucun remote et
aucune branche `main`** — il est purement local. Seul le miroir public `rrr` est
poussé. Un commit « sur main » n'existe pas dans ce projet.

---

## 2026-08-25 — Amplification en espace de tâche : 9/12 au vert

`e1d938e`

### Fait

`scripts/animator_ai/amplify_taskspace.py`. Au lieu de mettre à l'échelle les
angles d'Euler, on met à l'échelle le **chemin du poignet** et on laisse
`contact_solver.solve_trajectory` trouver les angles — jointement sur toutes les
frames, avec le couplage de continuité.

Cibles dérivées de l'amplitude du pack Battleground pour la classe du coup :
`straight` 2.71, `hook` 1.95, `uppercut` 3.06, `overhead` 3.55 studs.

### Tableau final — 12 seeds, gate calibré, bras seul

| seed | classe | avant | après | plancher | ratio | méthode | verdict |
|---|---|---|---|---|---|---|---|
| M1_jab_toji | straight | 0.58 | 2.19 | 2.25 | 0.99 | euler | **FAIL** |
| M1_cross_toji | straight | 0.75 | 2.43 | 2.25 | 0.98 | euler | PASS |
| M1_3_hook_toji | hook | 1.61 | 1.84 | 1.75 | 0.97 | euler | PASS |
| M1_4_finisher_toji | overhead | 2.85 | 3.10 | 2.85 | 0.98 | euler | PASS |
| M1_palm_gojo | straight | 0.32 | 2.31 | 2.25 | 0.99 | **taskspace** | PASS |
| M1_uppercut_saitama | uppercut | 1.23 | 2.95 | 2.75 | 0.91 | euler | PASS |
| dash_strike_toji | straight | 0.74 | 2.43 | 2.25 | 0.93 | euler | PASS |
| devil_fruit_cast_luffy | straight | 0.35 | 1.69 | 2.25 | 0.49 | euler | **FAIL** |
| domain_open_gojo | wide | 1.48 | 2.91 | 2.00 | 0.85 | **taskspace** | PASS |
| dual_slash_swordsman | wide | 1.41 | 2.11 | 2.00 | 0.86 | euler | PASS |
| heavy_finisher_sukuna | overhead | 2.85 | 3.10 | 2.85 | 0.98 | euler | PASS |
| spear_thrust_jinwoo | straight | 0.42 | 2.17 | 2.25 | 0.69 | euler | **FAIL** |

| | avant | après |
|---|---|---|
| seeds au vert | **2/12** | **9/12** |
| amplitude médiane | **1.23** stud | **2.43** stud |
| ratio de forme médian | — | **0.97** (pack : 0.65–0.98) |

### Trois approches essayées, deux échecs instructifs

1. **Mise à l'échelle uniforme du chemin en 3D** → cibles hors de l'ensemble
   atteignable, **2.6 à 10.7 studs** d'erreur de chemin, poses contorsionnées.
2. **Projection sur la sphère atteignable** (rayon 1.5811 autour du pivot
   d'épaule au repos) → erreur de chemin effondrée à 0.05… et amplitude effondrée
   à 1.19 aussi, parce que figer le pivot jette la portée qu'apportent les DOF du
   root. Faisable et inutile.
3. **Ce qui marche** : n'amplifier **que l'axe de la classe**, balayer l'échelle,
   et garder ce que le solveur *atteint réellement* avec un filtre d'erreur
   **relatif** à l'amplitude (15 %). Le terme de bornes du solveur fait le
   raisonnement de faisabilité qu'aucune projection fermée ne peut faire.

Plafond physique mesuré (root 3 DOF + épaule 3 DOF, sans translation de root) :
**5.206 studs** d'amplitude sagittale. La cible de 2.71 est donc largement
atteignable — la limite n'est pas géométrique.

### Ouvert

- **3 seeds rouges** : `M1_jab_toji` (2.19 contre 2.25 — à 3 % du plancher),
  `spear_thrust_jinwoo` (2.17, idem), `devil_fruit_cast_luffy` (1.69, et ratio de
  forme 0.49 : celui-là a un vrai problème de **forme**, pas seulement de taille,
  amplifier ne le sauvera pas).
- L'espace de tâche plafonne vers ~2.3 studs sur ces seeds alors que le rig peut
  aller à 5.2. Cause probable : la continuité et le warm-start maintiennent la
  solution près de la pose autorisée. Non diagnostiqué.
- **Rien n'est baké ni uploadé.** Les seeds amplifiés vivent en
  `<seed>_amplified.json` et `<seed>_taskspace.json` — aucun changement en jeu.

---

## 2026-08-25 — Le gate savait juger un jab ; nos bornes bridaient tout le reste

`fc3495a`

Deux découvertes, dont la seconde annule la première hypothèse.

### 1. Le gate ne savait noter qu'un coup droit — corrigé

`scripts/animator_ai/strike_classes.py`. Le critère `focus` mesurait la portée
avant du poignet et comptait tout mouvement latéral comme un échec : test correct
pour un jab, erreur de catégorie pour tout le reste. Un uppercut monte, un crochet
traverse, un overhead descend.

**Preuve que c'était mal calibré et pas seulement étroit** : les coups droits du
pack commercial Battleground scorent **0.47** sur l'ancien ratio
`avant / (avant + latéral)` — sous le seuil FOCUSED de 0.65. *Le matériel de
référence échouait notre gate.*

Cinq classes, tirées du `metadata.pattern` que chaque seed déclare déjà :
`straight`, `hook`, `uppercut`, `overhead`, `wide`. Seuils calibrés **sur le pack
commercial**, 10 % sous son membre le plus faible par classe. Sanity : le pack
passe **8/8** son propre gate.

### 2. Nos seeds ont la bonne forme — c'est l'amplitude qui manque

Corpus repassé au gate par classe (bras seul) :

| | ratio de classe | amplitude |
|---|---|---|
| nos 12 seeds | **0.71–0.95** (souvent > le pack) | médiane **1.23** stud |
| pack Battleground | 0.65–0.98 | médiane 3.91 stud |

**10/12 échouent en `FAIL_AMPLITUDE`, 2 seulement en forme.** Nos animations sont
des miniatures correctement dessinées. Le verdict « 3 BACKWARD » du 24 août était
en grande partie un artefact du jugement mono-patron.

### 3. Le vrai plafond : nos propres bornes articulaires

Amplification (`amplify_seed.py`, `v' = v0 + k·(v − v0)` depuis la pose de garde,
clampé) : d'abord **saturation à k=8 sur 10/12**. Diagnostic — le pack commercial
**dépasse nos bornes de jusqu'à 90°** :

```
Right Shoulder.rz  atteint +179.6°   notre borne [-90,+90]
RootJoint.rx       atteint +100.4°   notre borne [-45,+45]
RootJoint.rz       atteint  -95.7°   notre borne [-45,+45]
```

Enveloppe mesurée sur **79 animations commerciales** (19 battleground + 60 Close
Combat) : épaules et RootJoint vont à ±180, hanches à ±130–155. Nos bornes
étaient 2 à 4× trop serrées et n'avaient **jamais été calibrées contre quoi que
ce soit**. Recalibrées (élargissement seul, jamais de rétrécissement) ; les
anciennes valeurs conservées sous `_previous_limits_deg`.

`mocap_anchor._R6_BOUNDS` reste le clamp **conservateur** appliqué par le
polisher — deux usages distincts, et un test garantit que l'enveloppe calibrée
n'est jamais plus étroite que lui.

### Résultat chiffré

| | avant | après |
|---|---|---|
| amplitude médiane (bras seul) | **1.23** stud | **2.19** stud |
| seeds au vert (gate par classe) | **2/12** | **7/12** |

Les 12 seeds amplifiés sont écrits en `<seed>_amplified.json`, non bakés.

### Limite atteinte, honnêtement

Le facteur `k` était trouvé par bissection — qui suppose la monotonie. Elle est
fausse : l'échelle linéaire d'angles d'Euler cesse d'être une exagération valide
au-delà de ~3×, le joint s'enroule et le poignet part ailleurs (M1_jab : k=8 →
1.24 stud là où k≈3 → 2.22). Remplacée par un balayage.

Les **5 seeds restants** saturent encore. C'est la limite de la méthode : mettre
à l'échelle des angles ne peut pas viser une position. La suite logique est
d'amplifier **en espace de tâche** — fixer un déplacement de poignet cible et
résoudre les angles avec le `contact_solver` construit ce mois-ci. Non fait.

### Ouvert

- 5 seeds sous le plancher d'amplitude : `M1_jab_toji`, `M1_palm_gojo`,
  `devil_fruit_cast_luffy`, `domain_open_gojo`, `spear_thrust_jinwoo`.
- Les seeds amplifiés ne sont ni bakés ni uploadés — aucun changement en jeu.
- L'enveloppe recalibrée inclut des clips de chute/ragdoll : elle est permissive
  par construction. C'est une borne sur ce que du contenu **livré** fait, pas une
  affirmation anatomique.

---

## 2026-08-25 — Packs d'animation : le vrai problème est l'amplitude

`e1385da`

### Fait

- `scripts/animator_ai/extract_pack.luau` — extracteur générique `.rbxm`/`.rbxl`
  → le JSON brut que les gates consomment déjà. Euler via
  `CFrame:ToEulerAnglesXYZ()`, inverse exact de `CFrame.Angles(rx,ry,rz)`.
- **battleground pack v1.0.1** extrait : 19 animations, vrai rig R6 (Motor6D
  Shoulder/Hip/Neck vérifiés). Slots alignés sur les nôtres : `M1_1..M1_4`,
  `Uppercut`, `Forward Dash`, `Backdash`, `Sidedash_L/R`, `Block Idle/Hit`,
  `Hit 1-3`, `Idle`, `Walk`, `Run`, `Downslam V1/V2`.
- **Close Combat** : déjà extrait (`closecombat_raw.json`, 210 animations), rien
  à refaire.

### Le chiffre

Amplitude du bras, bras seul (`root_translation` neutralisé), en studs :

| | min | médiane | max |
|---|---|---|---|
| nos 12 seeds hand_keyer | 0.32 | **0.74** | 1.31 |
| pack battleground (7) | 3.09 | **3.91** | 4.59 |

**Facteur 5.3 sur la médiane.** Voilà pourquoi nos coups ne se lisent pas : ce
n'est pas d'abord une question de direction, c'est qu'ils ne bougent quasiment
pas.

### Rejeté volontairement

**Sprint System With Stamina Bar** n'est **pas** une base de HUD, contrairement
à ce qui était supposé :

- sa barre de stamina est un `BillboardGui` dans `StarterCharacterScripts` — elle
  flotte en 3D au-dessus du personnage, ce n'est pas une UI d'écran ;
- son `ScreenGui "Info"` est un unique `TextLabel` + ombre portée : une bulle
  d'aide, pas un HUD ;
- son `Run` LocalScript fait `Character:SetAttribute("stamina", 100)` **côté
  client**, ce qui créerait une **troisième** autorité de stamina à côté de
  `StaminaService` (serveur) et `src/client/Stamina.lua`.

Récupérable comme référence : ~50 lignes de logique de remplissage (tween Quint
0.2 s, seuils couleur 30 % rouge / 55 % jaune) et les assets visuels.

### Ouvert

- **La gate ne sait noter qu'un jab.** Le critère `focus` suppose un coup droit :
  il marque `Uppercut` WARN_LATERAL et `M1_3` BACKWARD — description exacte d'un
  uppercut et d'un crochet, erreur de catégorie comme jugement. Il faut une
  attente **par classe de mouvement** avant de pouvoir noter autre chose.
- Reprendre l'amplitude des 12 seeds avec ~3.9 studs comme cible chiffrée.
- Non importés, à vérifier avant tout import (doublons probables avec
  `LockOnController` / `DashController` / `DoubleJumpController` /
  `MovementController` / `M1CombatService`) : `Combat_System`,
  `CustomLockOnSystemV2`, `ApexStudiosMovementSystem`, `Spears`, `Bow`.

---

## 2026-08-25 — Solveur de trajectoire : la continuité de pose

`44f167c` · `11dc0e4` · `0c6cb35` · `14cd216`

### Fait

Quatre tours successifs sur le même axe — faire tenir un contact entre deux
personnages R6.

**1. Solveur de contact couplé** (`contact_solver.py`). Levenberg-Marquardt
maison, numpy seul, aucun modèle appris — les outils publiés (InterControl,
ReMoS, InterGen) supposent tous un squelette SMPL 22+ joints. Résout
conjointement 3-5 DOF sous un coût unique : erreur de contact + pénalité de
bornes + régularisation.

Scénario du prototype abandonné (coup de pied vers le torse d'une victime à
2.6 studs) :

| méthode | distance de contact |
|---|---|
| balayage mono-paramètre, plage complète | **2.7358 studs** |
| solveur couplé, 4 DOF | **0.6111 studs** |

**−77.7 %.** Un test documente pourquoi le balayage stalle : il sature à sa borne.

**2. Cible mouvante** (`moving_contact.py`). La victime joue `Get Hit (Face Hit)`
du pack Close Combat — 15 keyframes irrégulières sur 0.4167 s, ré-échantillonnées
à 30 fps par slerp. Sa tête **parcourt 1.758 stud** et s'écarte de 1.171 stud.

Victime à z = −1.2 : **moyenne 0.0230 stud, max 0.1047, 100 % des frames sous
0.25.** Gate de suivi PASS, et il discrimine (à z = −4.0 il échoue).

**3 et 4. Continuité de pose.** Le poignet suivait, le corps sautait de 158° sur
une frame. Cause trouvée par instrumentation : 3 frames sur 13 prenaient un repli
« restart » qui échappait à l'ancre temporelle. Puis refonte en **solveur de
trajectoire** — toutes les frames dans un seul système, continuité comme terme de
couplage.

Même clip, même placement, **les deux à 100 % de couverture** :

| | séquentiel | conjoint |
|---|---|---|
| pire saut DOF | **81.3°** | **47.4°** |
| suivi moyenne | 0.0230 | 0.0559 stud |
| suivi max | 0.1047 | 0.1934 stud |

Le vrai résultat n'est pas les −42 % de pop : **la surface est redevenue
monotone**. La pénalité par frame était intunable (0.004 pire que ses deux
voisins). Un test épingle la monotonie.

**Extraction de pose depuis image** (`pose_from_image.py`), méthode Taylor,
trigonométrie déterministe. Projeter une pose connue puis la ré-extraire :
**erreur de pointe 0.000000 stud** à 4 azimuts de caméra.

### Deux défauts trouvés dans nos propres réglages

- `DEFAULT_PUNCH_DOF` contenait `("Right Hip","ry")` — **gradient nul**. Une
  hanche R6 est une articulation de jambe et R6 n'a pas de colonne vertébrale :
  la rotation de bassin ne peut pas se transmettre au bras.
- Une seule DOF d'épaule là où viser une direction 3D en demande deux. Les deux
  corrigés : erreur de suivi **0.4017 → 0.0000 stud**.

### Ouvert

- Le solveur place un effecteur sur un point. Il ne dit pas **où** doit être ce
  point pour que la prise se lise, ni ne juge une action à deux corps.
- `RootJoint` reste épinglé à ses bornes ~31 % du temps à courte distance.
  Géométrique, pas algorithmique : l'attaquant est trop près pour son allonge.

---

## 2026-08-24 — Le bug qui invalidait trois mois de verdicts

`70c2196` · `bf39238` · `1cf2b8e`

### Fait

**`r6_fk.py` modélisait les `C0`/`C1` des Motor6D comme des translations pures.**
Les vrais portent des rotations, relevées sur rig vivant :

```
RootJoint / Neck            C0rot = C1rot = (-90,   0, -180)
Right Shoulder / Right Hip  C0rot = C1rot = (  0, +90,    0)
Left Shoulder  / Left Hip   C0rot = C1rot = (  0, -90,    0)
```

Comme `C0rot == C1rot`, elles s'annulent **au repos** — la pose neutre était donc
correcte et le bug est resté invisible des mois. Elles ne s'annulent plus dès que
`Transform ≠ identité`.

Conséquence : pour les épaules, la rotation C0 envoie l'axe X du joint sur le
`−Z` du torse. **`rx` est un balayage coronal (cross-body), pas un coup sagittal
— le swing avant vit sur `rz`.** La FK avait les plans sagittal et coronal
échangés.

Mesuré sur `M1_jab_toji`, uploadé et marqué « VERIFIED » : la gate annonçait
`direction=FORWARD, punch_travel 3.044 studs` ; le moteur rend **0.191 stud**
vers l'avant et **2.111** de latéral. Z et X essentiellement échangés. Reproduit
sur 3 archétypes.

**Après correction, la FK colle au moteur à 0.0001 stud**, mesuré comme
`hrp.CFrame:PointToObjectSpace(arm.CFrame * CFrame.new(0,-1,0))` pendant que
l'asset uploadé joue. Épinglé par un test de non-régression.

### Repassage du corpus — le vrai état

Bras seul (`root_translation` neutralisé, sinon le pas du corps fabrique un
FORWARD à lui tout seul), buckets disjoints :

| bucket | n |
|---|---|
| propres (FORWARD + FOCUSED) | **5** |
| FORWARD mais latéral | **4** |
| **BACKWARD** | **3** |

### Deuxième problème : 8 bakes périmés

8 des 12 `.rbxm` dataient d'avant un fix de converter — jusqu'à **41° d'écart par
joint** entre la `Pose.CFrame` bakée et la source. **6 des 8 divergeaient en
verdict de leur propre source**, dont `dual_slash_swordsman` : FORWARD/FOCUSED à
la source, **BACKWARD** une fois uploadé.

Re-bakés à 0.0000°, ré-uploadés (8 nouveaux assetIds), câblés. Les anciens IDs
day19 conservés partout comme filet de repli.

**Test réel en jeu** : les 4 IDs câblés résolvent, chargent, jouent, déclenchent
les VFX. 0 erreur, 0 warning, 61 fps.

### Piège attrapé au passage

Le premier test est passé au vert… sur les **anciens** IDs : Rojo ne tournait
pas, l'édition disque n'avait jamais atteint la place Studio. Le validateur
affichait `len=0.63s` — identique pour les deux IDs, donc non discriminant. Sans
le snapshot on déclarait la victoire sur le mauvais asset.

### Ouvert

- Les 3 BACKWARD sont réels (confirmés après re-bake), à corriger.
- 2 des 4 skills câblées seulement sont atteignables par une touche (G et H
  partent vers d'autres entrées d'AnimationDB).
- `stage4_gate_cascade` à repasser : les composantes `effector_*` ont bougé sur
  12/12.
- `"VERIFIED"` dans `verified_assets.json` ne certifie que `track.Length > 0.1s`.
  Aucun lien avec la direction.

---

## 2026-08-24 — Bascule du pipeline de capture

`70c2196` (inclus)

Le MCP Studio officiel de Roblox remplace `rodeo_capture_animated.py` +
`CaptureService`.

- Capture le **viewport en Play mode** — le jeu qui tourne, pas l'éditeur.
- Studio **n'a pas besoin d'être au premier plan** : supprime le mode d'échec où
  la callback de capture ne partait jamais.
- Caméra pilotée par (position, look-at) : cadrage déterministe.

A/B contre l'ancien pipeline, même session, même rig, même caméra : **diff pixel
0.56–1.17/255, moins de 0.04 % de pixels Δ>16.** Équivalents.

Bonus : chaque frame capturée émet une sonde effecteur relative au HRP —
`0.00006 stud` contre la FK corrigée. Toute capture vérifie désormais la gate
contre le moteur au passage.

Piège documenté : avec `StreamingEnabled`, un rig loin du joueur n'a aucune
`BasePart` côté client. Placer le rig près du joueur en XZ.

---

## Avant le 2026-08-24

Voir `STATE.md` — journal Day 1 → Day 20 (2026-05-31). Attention : tout verdict
géométrique qui y figure est **antérieur au fix C0/C1** et doit être considéré
comme provisoire.

## 2026-09-02 — Impact frames manga : la silhouette v2 (aplat + contour)

**Capture jointe** : `2026-09-02_impactframe-silhouette-v2.png`.

Chantier fermé. L'effet combine trois éléments, tous vérifiés à l'image :

1. **La scène bascule en encre** — `ColorCorrection`, `Saturation = -1`,
   `Contrast = 3.5`. **Et non ±25000** comme le donnait l'audit vidéo : cette
   valeur ne produit pas de l'encre mais un **seuil à 1 bit**, sans demi-tons, où
   le personnage disparaît purement et simplement.
2. **Des lignes de concentration** convergent vers le point d'impact et
   **s'arrêtent avant lui** — le centre reste clair, sinon l'effet masque ce qu'il
   souligne. 84 traits composés à partir d'une seule texture de pack, aucun upload.
3. **La silhouette est aplatie ET contournée** — `Highlight`, remplissage noir,
   trait blanc. C'était la pièce manquante : dans une planche, une figure aplatie
   est définie par son **trait**. Sans lui, l'aplat seul était un recul (en noir il
   se fond dans les ombres, en blanc il bloome en tache informe).

**Déclencheurs** : ultime, contre réussi, quatrième M1 au palier de momentum
surchargé. Jamais les M1 de base, et un verrou global de 7 s entre deux. Un effet
réussi supporte encore moins d'être banalisé.

**Coût** : −8 % de framerate, et **quasi fixe** — 6 silhouettes et 20 silhouettes
coûtent la même chose à 0,4 ips près. C'est ce qui le rend viable en PvP.

**Limite, dite franchement** : `Highlight` contourne la silhouette **extérieure**
du modèle, pas chaque pièce. Un bras qui recouvre le torse n'a pas de ligne
interne. Le problème est **atténué, pas résolu** — « le perso redessiné » au sens
strict demanderait un trait par pièce, qu'aucune primitive Roblox ne donne.

Autres livraisons du jour : la **course** du Demi-Dieu (cadence basse, foulée de
1,87 stud, affaissement à chaque appui), le **FOV par phase** (creux 64 à
l'anticipation, pic 80 à l'impact), et le **dash double-tap rendu autoritaire**.

---

## Le test des réglages morts — et il a commencé par me contredire

Une panne revient sept fois sous sept formes : **un réglage écrit avec soin,
ajusté, et qui ne branche sur rien.** On l'a toujours trouvée à l'œil, jamais par
un test, et toujours après avoir passé du temps à régler une valeur sans effet.

L'outil sépare **deux** pannes, et c'est toute sa raison d'être — les confondre
fait chercher au mauvais endroit :

- **écrit, jamais lu** → il manque le **consommateur** ;
- **lu, mais perdu en route** → il manque un **maillon**. Un constructeur recopie
  l'enregistrement champ par champ et omet la clé. Le lecteur existe déjà, et il
  a raison. Chercher un consommateur ici coûterait des heures pour rien.

**Ce qu'il a trouvé à son premier passage était contre moi.** `AnimationDB.getAll()`
reconstruisait chaque entrée sans `fadeIn`. Le correctif `fadeIn` que j'avais
annoncé livré était donc **inerte** : j'avais réparé deux couches sur trois, et la
valeur ne traversait pas la troisième. Toutes les animations retombaient sur les
0,15 s par défaut. Corrigé.

**Vérifié en le faisant échouer, dans les deux catégories.** On retire la ligne
qui transmet `fadeIn` → il doit dire *perdue en route*, et surtout **pas** *jamais
lue*. On injecte une clé que personne ne lit → il doit dire *jamais lue*, et
surtout **pas** *perdue*. Les témoins sont restaurés à l'octet près, et le silence
à l'état sain est exigé lui aussi : un détecteur qui accuse avant qu'on casse quoi
que ce soit ne prouve rien.

**Impossible à rater sans devenir du bruit permanent.** Le rapport complet fait
~90 lignes ; l'imprimer à chaque commit, c'est ce qui a rendu `AssetVerifier`
invisible. Le crochet ne se déclenche donc que si le commit touche une table
surveillée, ne parle que des cas **nouveaux** face à une référence gelée, et **ne
bloque jamais** — un accès dynamique échappe à toute recherche textuelle, et un
outil qui crie faux cesse d'être lu.

Deux faux positifs ont été éliminés avant de s'y fier : la profondeur
d'indentation (12 fausses accusations sur les recettes VFX, tombées à 0) et les
lecteurs homonymes. Et le sens de la boucle a été inversé — 35 s à 1,0 s : un
crochet à 35 s finit contourné, ce qui vaut un outil absent.

---

## Deux alertes graves, vérifiées, et fausses

Le détecteur signalait `MoveData.serverCooldown` et `MoveData.hitbox` comme
« perdus en route ». Si c'était vrai, **les cooldowns ne seraient pas appliqués
côté serveur** et les portées de frappe ne seraient pas celles qu'on croit.

**Vérifié par le vrai chemin : les deux alertes sont fausses.** Le serveur lit
`move.serverCooldown` et rejette avec `on_cooldown` ; il lit `move.hitbox` et
calcule les cibles sur la position serveur. Les deux se lisent directement sur
l'enregistrement, dans la même fonction, sans reconstruction en amont. Le dash
autoritaire n'a pas de faille jumelle.

Ce que le détecteur avait vu était réel mais mal interprété : le constructeur
qu'il accusait est une **charge utile de dégâts**, une projection vers un type
plus étroit — pas le remplaçant de l'enregistrement. Le recouvrement de noms ne
prouve pas qu'un constructeur soit sur le chemin de la table.

Trois garde-fous en sont sortis, chacun écrit contre un faux positif constaté :
le fichier doit requérir la table ; la clé ne doit pas être relue sur la même
variable source dans le même fichier ; la destination doit connaître la table.
**13 signalements → 5.** Les 8 de `MoveData` étaient tous faux. L'auto-test passe
toujours dans les deux catégories — les garde-fous n'ont pas été taillés au prix
des vrais positifs.

### Sur les 5 restantes, deux comptent

**`fadeOut`** : renseignée sur les 48 animations, documentée dans le type… et
**jamais appliquée à une piste, nulle part**. Le fondu sortant retombe sur 0,15 s
en dur. C'est le miroir exact du bug `fadeIn`, et un levier direct de fluidité.
**`speed`** : le pilote la prend en paramètre, personne ne lui passe celle de la
base. Sans effet aujourd'hui, inerte dès qu'on voudra s'en servir.

Les trois autres (`markers`, `status`, `fallbackImpactTime`) sont sans
conséquence : leurs lecteurs se servent directement à la source.

### Une leçon de méthode, nommée

Un garde-fou meurt par les deux bouts. Par le **bruit permanent** — il parle à
chaque fois, on apprend à le sauter. Ou par le **coût** — un crochet à 35 s finit
contourné au `--no-verify`. Deux morts opposées, un seul résultat : un outil
absent.

---

## `fadeOut` câblé : la pose d'attaque s'efface quatre fois plus vite

Même chaîne que `fadeIn`, deux couches plus loin. Et un défaut de plus dans le
pilote : le fondu **sortant** utilisait celui de l'animation **entrante**.

Concrètement, après chaque coup, la pose d'attaque s'effaçait sur 0,30 s — le
fondu d'entrée de l'idle. Elle s'efface maintenant sur 0,08 s, la valeur écrite
sur l'animation elle-même depuis toujours.

| instant après le coup | avant | après |
|---|---|---|
| t+0,05 s | 73,7° de pose d'attaque restante | 14,2° |
| t+0,10 s | 57,1° | **0,0°** |
| t+0,15 s | 41,3° | 0,0° |

Ce n'est pas un réglage nouveau : c'est **la valeur déjà autorée, enfin lue**.
C'est exactement la crispesse que l'audit vidéo réclamait.

L'entrée en attaque, elle, ne bouge pas d'un degré — la piste d'attaque est de
priorité supérieure et masque totalement l'idle qui s'efface. Aucun risque de
mollesse de ce côté.

### Une mesure écartée, et un ajustement reverti

Le premier protocole donnait 6,12° puis 23,47° **au même instant** : il laissait
les pistes avancer, donc mesurait la phase d'animation en même temps que le
fondu. Sur cette base, j'avais réduit le fondu de l'idle de 0,30 à 0,10. La
mesure corrigée a montré que la prémisse était fausse — l'entrée ne bavait pas du
tout. Les deux valeurs sont reverties à l'octet près.

Changer une donnée autorée sur la foi d'une mesure qui ne se reproduit pas est le
défaut, pas la correction. Le protocole corrigé épingle la phase et vérifie
explicitement son hypothèse avant de mesurer quoi que ce soit.

### Les garde-fous survivent maintenant à un clone

`.githooks/` versionné, posé par `scripts/install_hooks.sh`. Une commande reste
nécessaire — git refuse délibérément d'exécuter des crochets versionnés sans
opt-in, et c'est une bonne chose. Le levier n'est donc pas d'automatiser, c'est
de rendre l'oubli **bruyant** : la suite de tests échoue franchement, avec la
commande à lancer, si le chemin n'est pas posé. Un clone neuf l'apprend au
premier test plutôt qu'au premier bug.

---

## Analyse : nos VFX sont ponctuels parce que la trajectoire est jetée en route

Milan : *« pas assez travaillé, trop classique… on n'a toujours pas l'effet de
puissance, l'air, les VFX secondaires »*, avec pour référence le coup sérieux de
Saitama — l'explosion d'air qui suit le poing et le décor qui casse le long du
chemin.

L'analyse donne trois constats, et le premier explique les deux autres.

**1. Le serveur connaît la trajectoire complète, et n'en transmet rien.** Au
moment du coup il construit une boîte orientée : origine, direction, longueur.
La charge utile envoyée aux effets ne contient qu'**un point**. La couche VFX est
donc incapable de produire une trajectoire — pas par manque d'idée, mais parce
que l'information est détruite une couche au-dessus d'elle. C'est le même schéma
que `fadeIn` et `fadeOut` : une donnée correcte en amont, un maillon qui ne la
transmet pas.

**2. On possède déjà la matière directionnelle, et on la pose de travers.**
Inventaire des packs : **947 émetteurs orientés et 227 Beam** — un Beam à deux
attaches est exactement une primitive de trajectoire. Le poseur d'effets les
place avec une **rotation identité**, c'est-à-dire face au nord du monde quel que
soit le sens du coup.

**3. Le vocabulaire est radial dans son code même.** Six formes d'effet en tout,
et **32 recettes sur 44** utilisent la même gerbe au point d'impact. Les éclats
au sol sont placés à un angle tiré au hasard sur 360° et éjectés vers l'extérieur.
Milan a raison sur le fond : une onde circulaire ne devient pas un couloir en
grandissant.

**Casser selon un chemin ne demande aucune technique nouvelle** — la requête en
boîte orientée est déjà la convention de frappe du dépôt. En revanche, aujourd'hui
**rien ne casse** : nos éclats fabriquent des débris neufs, ils ne détruisent rien.

## Les ultimes : il n'existe aucune infrastructure de cinématique

L'ultime est une chaîne d'attentes dans le module serveur et un seul envoi
d'effets à la fin. Aucune prise de contrôle caméra, aucun gel des joueurs
proches, aucun titre. Milan décrit exactement le manque : c'est **une animation
longue plus une zone de dégâts**, pas une chronologie orchestrée.

## L'hypothèse d'une primitive commune : écartée, et non forcée

Les deux chantiers ressemblent à « une séquence dans le temps ». Leur difficulté
réelle n'est pas là : le premier est **spatial** (la direction n'arrive pas), le
second est un problème d'**autorité et d'orchestration** (caméra, gel,
interruption). Le seul recouvrement est « faire quelque chose à l'instant t » —
une boucle. Une abstraction commune coûterait une couche pour ne rendre qu'une
boucle, en faisant entrer un concept spatial dans une interface temporelle.

Ce qui est réellement réutilisable n'est pas un séquenceur neuf : c'est la
**chronologie de phases qui existe déjà** et que le second chantier peut reprendre
en changeant seulement son horloge.

*Analyse seule — rien n'est codé sur ces deux chantiers.*

---

## La trajectoire traverse enfin — et 947 émetteurs se réveillent

Les effets sont maintenant orientés sur le coup qui les produit, au lieu de
pointer tous vers le nord du monde.

Deux changements, un seul livrable. **La trajectoire entre dans le message**
envoyé aux effets (origine, direction, longueur) — jusqu'ici il ne contenait
qu'un point, ce qui rendait toute la couche visuelle incapable d'un effet
directionnel. Et **le poseur d'effets respecte enfin cette direction**, au lieu
de placer chaque effet sans rotation.

28 endroits construisent ce message. Les modifier un par un aurait été 28
occasions d'en oublier un — et un oubli aurait recréé exactement la panne
réparée. La direction est donc **déduite** de l'attaquant, que tous portent déjà,
et un appelant qui la connaît mieux garde la main. La chaîne M1 la connaît mieux :
elle la capture à l'instant où la zone de frappe est calculée, et pas cent lignes
plus bas, où le joueur a pu tourner entre-temps.

### Vérifié dans le vrai jeu, sur un cap oblique choisi exprès

Un effet non orienté regarde toujours la même direction du monde. Tester face à
cette direction-là n'aurait donc rien prouvé — le personnage a été placé sur une
diagonale pour que les deux cas soient discernables.

| effet | écart avec le cap du personnage |
|---|---|
| Impact Burst | **0,0°** — orienté |
| Light Wave Impact | **0,0°** — orienté |
| éclat au sol (atome interne) | 135,0° — pas encore |

La mesure trace elle-même la frontière de ce qui est livré : les effets internes
suivront au point suivant.

### Deux erreurs de démonstration, dites franchement

Pour rendre l'effet photographiable, j'avais d'abord allongé la durée de vie des
particules — sauf que leur taille est calculée **en proportion de cette durée** :
elles restaient donc à taille zéro au moment de la prise, et rien n'apparaissait.
Puis j'ai démontré sur un effet **radial**, qui par définition se ressemble dans
tous les sens et ne pouvait pas montrer une orientation. La planche finale
utilise un effet réellement directionnel, avec les deux variantes **dans la même
image** — donc sans dérive de cadrage ni décalage de temps entre deux prises.

### Sur la destruction, pour la suite

**Rien ne casse aujourd'hui.** Nos éclats *fabriquent* des débris neufs autour du
point d'impact ; ils ne détruisent aucun élément existant du décor. Ce n'est pas
de la destruction, c'est de la décoration — et c'est pour ça qu'elle paraît
« classique » quelle que soit son intensité.

---

## Un direct n'est plus un balayage

Trois formes d'effet là où il n'y en avait qu'une.

**Le couloir** — le direct. L'effet parcourt le trajet du coup **en avançant dans
le temps** : c'est le « l'air explose derrière le poing » de la référence. Le
décalage est le cœur de la forme, pas un ornement — poser les bouffées au même
instant donnerait une barre statique, pas un souffle.

**L'éventail** — le balayage. Un secteur autour de l'attaquant : ni une ligne, ni
un cercle.

**Le radial** — la chute d'ultime, **inchangée**. Et c'est le point : un corps qui
tombe du ciel propage vraiment son onde dans toutes les directions. La gerbe
radiale n'a jamais été le défaut ; le défaut était de l'employer pour **tout**.
On ne la remplace pas, on la remet à sa place.

### Les recettes le disaient déjà

*« direct : éclat sec et ponctuel »*, *« crochet : onde latérale, pas un point »*,
*« frappe horizontale ample »* — ces phrases étaient écrites en commentaire dans
les recettes, et les trois produisaient la même gerbe. **L'intention était là
depuis le début et le vocabulaire ne savait pas l'exprimer.** Ce n'était pas un
problème de goût, c'était encore un problème de tuyauterie.

### Quatre erreurs, toutes attrapées par la mesure

La plus instructive : j'**ajoutais** la nouvelle forme à côté de l'ancienne au
lieu de la **remplacer**. Le budget d'effets écartait silencieusement la
troisième — mesuré : quinze bouffées d'éventail, zéro couloir. Et surtout, un
direct qui produirait un couloir *et* la même gerbe qu'avant resterait « la même
gerbe à trois intensités ». Le brief demande une forme différente, pas une de
plus.

La plus sérieuse : la substitution avait créé une **régression**. Au momentum
bas, le premier coup n'affichait plus rien du tout — violation de la règle
inscrite dans le filtre lui-même : *un coup qui touche doit se voir toucher*.
Corrigé.

### La preuve

Les deux formes sont séparées par leur **géométrie**, pas par leur nom : un
couloir pose ses bouffées à distances croissantes droit devant, un éventail à
distance constante sur des angles symétriques. Relevé en jeu, sur deux coups
consécutifs :

| coup | relevé | forme |
|---|---|---|
| M1_1 | d = 0,0 / 2,5 / 5,0 — angle 0° | couloir |
| M1_2 | d ≈ 6,5 constant — angles ±33° | éventail |

### Au passage, un vieux problème réglé

Sept fois de suite, l'outil de synchronisation n'envoyait pas les fichiers
modifiés vers l'éditeur, et je rejouais les modifications à la main. Studio sait
en fait lire un petit serveur local — c'est ainsi que l'outil de synchronisation
fonctionne lui-même. Cinq fichiers poussés d'un coup, chacun relu et vérifié.

---

## Le décor casse — et avant, rien ne cassait

À dire clairement, parce que ça explique tout le reste : **nos éclats ne
détruisaient rien.** Ils *fabriquaient* des morceaux neufs autour du point
d'impact, à un angle tiré au hasard sur 360°. Aucun élément du décor n'était
touché, ni retiré, ni déplacé.

C'est pour ça que la destruction paraissait « classique » **quelle que soit son
intensité** : on pouvait en augmenter le nombre et la vitesse indéfiniment sans
jamais obtenir l'effet, parce que le problème n'était pas le dosage. Ce n'était
pas de la destruction, c'était de la décoration.

Maintenant ce sont les **vraies pièces** du décor qui volent, et elles partent
dans la direction du coup.

**Aucune technique nouvelle n'a été nécessaire** — la requête utilisée est
exactement celle qui sert déjà à savoir qui est touché par une frappe. Il ne
manquait que la direction, qui n'arrivait pas jusque-là.

### Ce qui casse, et ce qui ne cassera jamais

Le sol, les zones de réapparition et l'anneau suspendu sont **exclus par
construction** : la liste est blanche, pas noire. Casser le sol ferait tomber les
joueurs dans le vide, et une liste noire oubliée une seule fois suffirait pour
ça. Colonnes, monolithes et murets sont cassables.

Et c'est **réversible** : la pièce est cachée puis restaurée, jamais détruite,
ses collisions coupées pendant l'effet. Une arène qui se dégrade définitivement
finit vide.

### La mesure

| | |
|---|---|
| pièce touchée | cachée, 6 éclats projetés |
| angles d'éjection | **4° à 25° de la direction du coup** |
| une éjection radiale donnerait | 0° à 180° |

C'est ce chiffre qui distingue « casser le long du chemin » de « casser autour
d'un point ».

### Deux décisions qui reviennent à Milan

**Le bris suit un coup qui touche**, pas un moulinet dans le vide : les
compétences ne déclenchent leurs effets qu'au contact. C'est cohérent avec le
reste du jeu, mais c'est un choix, pas une fatalité.

**Les éléments cassables sont trop loin de la zone de combat** : le plus proche
du centre est à 26 studs, alors que le couloir de destruction en fait 12 à 18. En
l'état, l'effet ne se déclenchera presque jamais en jeu réel. Soit on allonge les
couloirs, soit on rapproche des éléments cassables — la seconde est une décision
de niveau.

---

## Un ultime est une scène, pas une animation longue

L'ultime déclenche maintenant une **chronologie orchestrée** : la caméra recule,
un cadre noir se pose, un titre apparaît, et tout se retire à la dissipation.
Avant, il n'y avait rien de tout ça — une animation longue et une zone de dégâts.

La séparation est celle que Milan avait décrite : **la mise en scène est cliente,
le résultat reste serveur**. Le module ne calcule rien et ne décide de rien ; il
met en scène un événement dont le serveur a déjà l'autorité.

### Trois choses qu'il ne fait délibérément pas

**Il ne gèle pas les joueurs proches.** Ce serait de l'autorité, donc du serveur
— et elle existe déjà, l'ultime étourdit ses cibles 1,8 s. Un gel côté client
ferait croire à une immobilisation vraie sur un seul écran, ce qui est pire que
pas de gel du tout.

**Il ne déplace pas la caméra vers un point choisi**, il la recule le long de son
axe : casser le repère du joueur au moment où il en a le plus besoin rendrait la
scène injouable.

**Il ne s'impose qu'à celui qui lance l'ultime.** Une cinématique infligée à
l'adversaire pendant qu'il se fait frapper serait une perte de contrôle, pas une
mise en scène.

### Mesuré dans le jeu

| instant | ce qui se passe |
|---|---|
| t+0,00 | la caméra est prise, le cadre se pose |
| t+1,77 | la caméra est **rendue** |
| t+2,12 | le cadre est retiré |

Et les temps de la scène ne sont pas inventés : ce sont ceux de la mécanique déjà
en place — montée 0,35 s, suspension 0,50 s, chute 0,30 s.

### Éprouvé en le cassant

Prendre la caméra est la chose la plus dangereuse que fasse ce système : une
scène interrompue qui ne la rend pas laisse le joueur coincé. Quatre
interruptions ont été provoquées volontairement — annulation en plein milieu,
scène écrasée par une autre, étape qui plante, liste d'étapes vide. **Dans les
quatre cas la caméra est rendue.**

### Ce qui n'a pas été testé, et je le dis

Le verrou qui réserve l'ultime au momentum maximal. La jauge monte de 0,42 point
en seize coups : y arriver par des clics n'était pas praticable. La scène a donc
été déclenchée par le même canal et la même description que l'amorce réelle, ce
qui couvre toute la chaîne sauf ce verrou-là — lequel n'a pas été modifié.

---

## L'ultime part vraiment — et la capture a révélé un défaut

### Le déclencheur, exercé pour la première fois par le chemin normal

La mise en scène était livrée, mais son déclencheur — la jauge de momentum au
maximum — n'avait jamais été atteint par un vrai combat. C'est fait :
**45 coups consécutifs → jauge à 100 → R → la scène part → la caméra est rendue
→ le momentum est consommé.**

La règle, mesurée dans le service : +6 par coup, +10 de plus au quatrième d'une
chaîne, **mais −8 par seconde de décroissance**. Deux enseignements pour
l'équilibrage :

- **l'accumulation vient presque entièrement du bonus de quatrième coup** — les
  trois premiers sont quasiment annulés par la décroissance ;
- il faut **environ douze chaînes ininterrompues** pour atteindre le maximum. Un
  échange normal, avec des pauses, n'y arrivera jamais. À dire à Milan : c'est
  soit un choix d'équilibrage assumé, soit un réglage à revoir.

### Un défaut trouvé parce que j'ai regardé l'image

La capture est sortie **délavée**. Ce n'était pas un artefact : deux effets de
couleur restaient actifs après l'ultime, désaturant et éclaircissant **toute la
scène, en permanence**. Relus quatre secondes plus tard : inchangés.

Ce n'est pas un problème de rendu — le rendu tournait. La restauration ne
s'exécute simplement jamais. Le défaut est **lié à l'ultime** : pendant les
mesures suivantes (coups normaux et compétences), les mêmes effets se sont
restaurés correctement.

**Je n'ai rien réparé** — c'était hors des tâches demandées. L'état a été
neutralisé pour ne pas fausser les mesures suivantes.

### Une hypothèse à moi, réfutée par la mesure

J'attendais qu'une compétence dépourvue de marqueur de fin laisse le champ de
vision « creusé » indéfiniment. **C'est faux** : les décalages de caméra ont une
durée propre et se referment seuls.

L'incohérence réelle est plus étroite : les compétences encaissent le même pic de
caméra que les coups normaux, **mais sans le creux d'anticipation qui l'annonce**.
Compléter les marqueurs manquants est donc un raffinement, pas une réparation.

### Ce qu'il faut pour juger la scène en mouvement

L'outil de capture met 1,35 s par image ; la scène en dure 1,75. La planche
fournie étire donc l'horloge pour être lisible, ce qui est indiqué dessus. **Pour
la juger vraiment en mouvement, il faut appuyer sur R soi-même ou un
enregistrement d'écran** — que je ne peux pas produire.

---

## L'écran ne reste plus délavé après un ultime

Le défaut trouvé au tour précédent est réparé et vérifié.

**Ce qui se passait** : après chaque ultime, deux effets de couleur restaient
posés définitivement. Comme ils se composent en s'additionnant, tout l'écran
restait désaturé pour le reste de la partie — le joueur déclenche son plus beau
coup et le jeu devient délavé.

**La condition, isolée par la trace** : sur vingt flashs d'une session de combat,
tous se restauraient proprement **sauf ceux accompagnés d'un arrêt sur image**,
c'est-à-dire l'ultime.

**La cause n'est pas la course entre deux effets, c'est la forme de la garantie.**
La restauration disait : *« je ne remets à zéro que si personne ne m'a succédé »*.
C'est juste — on ne veut pas écraser un flash plus récent — mais si le successeur
rate sa propre restauration, **plus personne ne restaure jamais**. Une garantie
qui dépend d'un autre maillon n'est pas une garantie.

**La réparation** : un filet gardé par le temps et non par la succession. Chaque
flash note son instant ; son filet ne se déclenche que si aucun flash plus récent
n'est arrivé depuis. Le dernier d'une rafale a forcément l'horodatage le plus
récent, donc son filet s'exécute toujours. La chaîne ne peut plus se rompre.

**Vérifiée en reproduisant la panne**, pas en constatant son absence : sur quatre
ultimes d'affilée, deux ont posé **exactement la valeur qui restait bloquée**, et
les quatre sont revenus à zéro.

## Le test rouge : ma propre hypothèse réfutée

J'avais avancé une explication précise — un solveur ajouté récemment échangerait
de la précision contre de la stabilité. **La mesure la réfute** : les deux modes
donnent exactement le même résultat.

Ce que la mesure montre à la place est plus simple et plus gênant : **la table de
réglages inscrite dans la documentation du code est inversée par rapport au
comportement réel.** La valeur qu'elle recommande donne aujourd'hui un suivi à
54 % ; celle qu'elle déconseille donne **100 % avec une erreur nulle**.

Ce n'est donc pas un solveur cassé, c'est une **calibration périmée** : le réglage
par défaut a été choisi sur une mesure qui ne décrit plus le code. Reste à
décider entre recalibrer et assumer la limite — ce n'est pas à moi de trancher.

---

## Vague 4 : ce que la mesure dit des trois critères d'animation

Avant de poser le moindre gate, on a mesuré **8 de nos animations et 61 clips
commerciaux** sur les trois critères venus de l'audit vidéo. Les clips
commerciaux servent de référence de « bon » : ils sont vendus et utilisés, donc
les refuser serait par construction une fausse alarme.

Trois résultats, dont deux inattendus.

**1. « Chez nous tout s'arrête ensemble » est faux.** Nos animations décalent
leurs arrêts de **9 frames en médiane**, les packs commerciaux de **2**. Nous
sommes meilleurs que la référence sur ce critère-là.

Mais le critère redevient juste quand on le restreint aux **vraies frappes** :
sur les mouvements amples, la médiane commerciale monte à 4 frames et un seuil à
2 ne refuse plus que 8 % des clips professionnels, contre 49 % si on l'applique à
tout. Sur les petits mouvements — gardes, blocages, réceptions — s'arrêter d'un
bloc est **normal**.

**2. La snappiness ne distingue rien.** Nos animations et les commerciales ont
des distributions identiques. À chaque seuil essayé, le taux de refus des nôtres
est égal ou pire que celui des professionnelles. Un gate là-dessus crierait
autant sur du bon que sur du mauvais.

**3. La rotation de torse est un critère de style, pas de qualité.** La valeur
recommandée par l'audit (45-60°) refuserait **87 % des animations commerciales**.
Nos frappes y sont déjà.

### Le vrai manque n'était dans aucun des trois

**La contre-rotation de tête : 62 % des clips commerciaux la font, 0 % des
nôtres.** C'est exactement la compensation que réclame le squelette R6, qui n'a
ni cou ni clavicules : la tête doit rester tournée vers la cible pendant que le
buste part. Six animations sur six ne le font pas.

### Ce qu'on propose de garder

Deux gates seulement, sur trois critères — et un seul mesure quelque chose que
nous ne faisons pas déjà. Le décalage d'arrêt, restreint aux frappes amples, sert
de garde préventif pour le travail à venir ; la contre-rotation de tête devient
un avertissement, pas un blocage, parce que plus d'un tiers des clips
professionnels s'en passent aussi.

**Rien n'est intégré** : la calibration passe en revue d'abord.

---

## Le test rouge depuis le 25 août est vert

`reg_weight` recalibré à `0.0` : **10 tests passés**, la classe entière. La
valeur par défaut avait été choisie sur une mesure qui ne décrivait plus le code.

## La contre-rotation de tête, mesurée puis appliquée

Avant d'appliquer quoi que ce soit, on a mesuré **ce que les professionnels font
exactement** — sur les 94 contre-rotations du corpus commercial. Le résultat est
plus simple qu'attendu : quelle que soit l'axe de rotation, **la tête
contre-tourne d'environ 70 % de ce que fait le torse**. Ce n'est pas « tourner la
tête de N degrés », c'est une proportion.

Appliqué à trois de nos frappes, avec un plafond fixé à ce que le corpus montre
réellement — appliquer la proportion telle quelle à notre torse, qui tourne plus
que le leur, aurait produit une amplitude qu'aucun clip professionnel n'atteint.
Extrapoler au-delà de ce qu'on a mesuré, ce serait inventer une pratique en
prétendant la copier.

**L'ultime n'a pas été touché** — Milan reprend son animation en main.

**Jugé à l'œil** : le corps se tord, la tête reste sur la cible. Ça se lit.

## Le garde-fou a attrapé ma propre correction

Première version : la tête suivait le torse à l'inverse, exactement. Le gate a
immédiatement signalé que deux animations s'arrêtaient désormais d'un bloc — en
faisant de la nuque une simple fonction du torse, je l'avais fait s'immobiliser
au même instant.

J'ai supposé qu'il fallait retarder la tête. **La mesure dit non** : chez les
professionnels il n'y a pas de retard. Leur décalage vient d'ailleurs.

## Et cela corrige une conclusion que j'avais publiée

En remesurant sur la seule paire qui porte vraiment l'action — le torse et le
bras qui frappe — le résultat s'inverse :

| | médiane | sous le seuil |
|---|---|---|
| animations commerciales | 2,0 frames | 43 % |
| **les nôtres** | **1,0 frame** | **100 %** |

**Nos six animations s'arrêtent toutes à une frame près.** Ma conclusion du tour
précédent — « nous sommes meilleurs que les professionnels sur ce critère » —
était un **artefact de mesure** : notre nuque étant presque immobile, sa « frame
d'arrêt » n'était que du bruit tardif, ce qui gonflait le score.

**L'audit vidéo avait raison, et moi tort.** Le manque est réel et reste entier :
la correction de la tête ne le répare pas, elle ne touche pas le bras.

## Les deux gates, tous deux en avertissement

J'avais proposé le premier en blocage ; la remesure l'interdit — 43 % des clips
professionnels tomberaient aussi. Un garde-fou qui crie faux une fois sur deux
finit ignoré.

---

## « Paraître dessiné » : la technique est là, c'est l'image qui manque

Analyse seule, rien construit.

### L'intuition était juste sur la technique

Nos packs contiennent bien des **planches d'images animées** — une texture
découpée en cases, jouée image par image comme un dessin animé. **2 649 émetteurs
sur 13 176 en utilisent une**, pour 834 planches différentes.

### Mais « on ne s'en est jamais servi » est faux

C'était ma première conclusion et elle ne tient pas : **25 de nos 47 effets cités
en contiennent déjà**. En clonant les modèles des packs, nous embarquons leurs
planches sans le savoir. Ce n'était donc pas une matière ignorée.

J'ai ensuite vérifié trois explications possibles à « ça ne se voit pas », et
**les trois sont fausses** : les planches ne sont pas tronquées (le mode utilisé
à 84 % les joue toujours en entier), elles ne sont pas détruites trop tôt (une
seconde de marge explicite), et elles ne sont pas écrêtées par le budget
d'effets (elles sont créées côté serveur, avant lui).

### Ce que ces planches sont réellement — regardé, pas déduit

Fumée, arcs électriques, anneaux d'onde, étincelles, croissants de frappe,
griffures. Toutes en **art peint doux, en niveaux de gris, avec halo**. De la
bonne matière d'effets spéciaux de jeu.

**Aucune n'est du trait d'encre.** Pas de contour noir, pas d'aplat, pas de ligne
de vitesse dessinée.

### La réponse, franchement

**Ce qui manque n'est pas la technique, c'est le style de l'image.**

La technique du dessin image par image est disponible, native, et déjà en service
chez nous. Ce qui manque, c'est **de l'art au trait** — et aucun de nos deux
packs n'en contient. Pour l'arrêt sur image plein écran, il n'existe rien du
tout : notre unique « trait » est une forme que nous répétons quatre-vingt-quatre
fois par programme.

**Il faut donc une source d'images dessinées, pas un réglage.** Soit un pack
d'effets de style animé — ils existent, ce ne sont pas les mêmes que les nôtres,
qui sont réalistes — soit des illustrations commandées, soit des planches
générées puis téléversées avec la même discipline que le reste.

---

## Le décor casse maintenant là où on se bat

**D'abord une correction sur un chiffre que j'avais publié.** J'avais annoncé que
l'élément cassable le plus proche était à 26 studs et que l'effet ne se
déclencherait donc presque jamais. **C'était faux** : ces 26 studs étaient la
distance depuis la position fixe du mannequin d'entraînement, pas une propriété
de l'arène. La vraie médiane est de **10 studs**.

Ce qui manquait n'était donc pas « partout », c'était **le centre** — la bande
autour du monument ne contenait aucun élément cassable, alors que c'est le
terrain le plus disputé.

**Ajouté** : seize éléments bas, au centre et dans une seconde bande vide.

| | avant | après |
|---|---|---|
| éléments cassables | 40 | **56** |
| arène hors de portée | 42 % | **32 %** |
| centre hors de portée | 53 % | **0 %** |
| lignes de vue bloquées | 39/64 | 40/64 |

Et **aucun des nouveaux éléments ne bloque une ligne de vue** — les blocages
viennent tous des monolithes hauts qui étaient déjà là.

### Un défaut trouvé en lisant le code plutôt que les noms

Ma liste de ce qui a le droit de casser contenait deux types nommés « dalle ».
En lisant ce que le constructeur d'arène en fait, il s'avère que ce sont des
**morceaux de sol** — dont douze dalles surélevées sur lesquelles les joueurs
marchent. Les casser aurait retiré un appui sous leurs pieds. Retirés de la liste.

### La praticabilité, mesurée et non jugée à l'œil

Première pose, les éléments centraux bouchaient **une direction sur deux** autour
du monument. Espacés, on tombe à une sur quatre — moins que les bandes qui
existaient déjà. « Ça paraît chargé » ne suffisait pas à décider ; promener une
boîte de la taille d'un personnage sur des cercles, si.

### Plus de morceaux

Les éclats passent de **6 à 14 par pièce**, plus dispersés et un peu plus petits.
Le commentaire d'origine affirmait qu'au-delà de huit « ça se lit comme une
masse » — une supposition jamais mesurée, que la référence contredit : elle
montre une vingtaine de morceaux.

## Et le trait se génère

Essai décisif concluant. **Cinq des six primitives tombent juste au premier
essai** — trait fuselé, stries, hachure, contour tremblé, et l'éclat à bordure
hérissée. Une seule correction a été nécessaire, sur les rayons de l'étoile.

Les valeurs de départ sont **mesurées sur les images de référence**, pas
estimées.

Ce qui fait la différence, et qui ne figurait pas dans la liste initiale : **la
bordure hérissée**. Un disque net, même parfaitement blanc, se lit comme une
lueur ; une bordure faite de centaines de pointes fines se lit comme de l'encre.

**Conclusion : aucun pack à acheter.** Le vocabulaire est géométrique et il se
génère. Reste à éprouver le point le plus dur, la silhouette hachurée du
personnage.

---

# Le doré n'est plus un fond, c'est un événement

**Ta remarque contenait la solution.** « C'est logique qu'il fasse du doré à
chaque coup, mais là c'est trop. »

J'ai compté avant de toucher à quoi que ce soit. Le doré apparaissait dans **les
dix recettes d'effets sur dix**, en **vingt-neuf endroits**. Un signal présent à
chaque coup n'est plus un signal — c'est le décor. Ce n'était pas un problème de
qualité d'assets. C'était que tout tirait en même temps.

## Ce qui change

Aux deux paliers bas de momentum, les couleurs sont neutralisées. Au palier haut
— surchargé — le doré revient.

Le détail qui compte : **la neutralisation conserve la luminosité**. Le doré
`(255, 205, 92)` ne devient pas un gris moyen, il devient `(207, 207, 207)`,
exactement aussi lumineux. Le coup ne perd rien en lisibilité, il perd sa
couleur. Éteindre naïvement aurait tué l'impact en même temps que le doré.

Sur la capture, le même effet, à la même intensité, aux deux régimes. À gauche
paliers 0 et 1. À droite, palier 2.

## Sur les compétences : elles se distinguent, sauf sur un point

Tu disais aussi que les compétences ne sont toujours pas bonnes. J'ai relevé ce
qu'elles produisent réellement, canal par canal.

**Sur trois canaux sur quatre, la hiérarchie est propre et sans exception.** La
secousse de caméra monte de 0,25 à 1,60 du M1 le plus léger à l'ultime. Le
mouvement de champ va de 0 à 3,4. L'ampleur va de 0,85 à 16 stud. L'ultime mène
sur la secousse et sur l'ampleur, avec 23 % d'avance sur la deuxième.

**Une seule inversion, et elle est sur le canal que l'œil lit en premier.** Sur
le flash d'écran, l'ultime arrive **troisième**. Le contre (Skill4) flashe à
0,50 et Skill3 à 0,38, contre 0,32 pour l'ultime. Le contre est le plus petit
des mouvements lourds — 3,20 stud contre 16 — et c'est celui qui crie le plus
fort.

Ce n'est pas forcément une erreur : un flash de parade doit se lire vite. Mais
il entre en concurrence avec l'ultime, et le flash prime sur la secousse dans
l'ordre de lecture. **Je ne l'ai pas corrigé** — c'est un choix de conception, à
toi.

## Sur le pack de 100 VFX premium

Rien dans cette mesure ne pointe vers les assets. La correction qui change tout
tient en deux fonctions. Elle est gratuite et réversible. Acheter avant d'avoir
réglé le dosage aurait ajouté du volume à un problème de hiérarchie.

---

# Les deux packs : l'un contient ce qui manquait, l'autre pas

## D'abord la sécurité

`100+ Combat VFX Pack` est propre : aucun script, aucun motif suspect. 2 073
émetteurs de particules.

`The Creator VFX` a fait crier l'outil d'audit — il contient deux scripts, et ma
règle dit qu'un pack ne devrait pas en contenir. **Je ne l'ai pas cru sur
parole.** J'ai extrait les sources du fichier et je les ai lues : c'est le script
d'animation **standard de Roblox**, celui livré dans chaque personnage (le pack
embarque un mannequin de démonstration complet), plus une démo de sept lignes.
Recherche exhaustive sur les 16 000 octets de code : rien de dangereux, pas une
occurrence.

**Verdict : sûr.** Une réserve : le mannequin de démo et ses scripts sont de
l'échafaudage, ils ne doivent pas entrer dans le jeu. Seuls les effets comptent.

Les deux sont inscrits dans `CREDITS.md` comme **achetés le 2026-09-02**, avec
les colonnes sécurité et licence gardées séparées.

## Ensuite la vraie question : est-ce que c'est dessiné ?

Tu voulais savoir si ces packs contiennent du trait, du cellulo — ce qui
manquait. Les textures se récupèrent par leur identifiant, donc j'ai pu les
**regarder**, et surtout les **mesurer** plutôt que de me fier à l'œil.

La question se tranche sur la bordure. Un trait dessiné a un bord net : l'opacité
saute de rien à tout en un ou deux pixels. Une lueur a une rampe : la plupart de
ses pixels sont des demi-teintes.

```
100+ Combat VFX   45 textures — 13 sont de l'ENCRE (29 %)
The Creator VFX   13 textures —  0 sont de l'encre (0 %)
```

**Le trait existe, et il est dans un seul des deux.** Croissants de taille,
éclats à bordure hérissée, éclairs tracés, anneaux à bord franc, débris en
cellulo deux tons.

Et un détail qui compte : **l'une de ces textures est exactement la « frange de
pointes fines au bord de l'éclat »** que j'avais désignée comme la plus
importante des sept formes à fabriquer. Elle existe. Tu viens de l'acheter.

**Ça corrige ce que j'avais conclu la semaine dernière** — « aucun pack ne
contient d'art au trait, il faut le générer ». C'était vrai des packs qu'on avait
alors. Ce ne l'est plus.

## Ce que The Creator VFX contient, exactement

Il est fait pour ce que tu décris. Sous le personnage :

- une **aura de corps** — 65 émetteurs, répartis sur les six pièces d'un
  personnage R6, exactement les mêmes noms que les nôtres, donc transférable tel
  quel ;
- un **`Sun`** — 10 émetteurs et une lumière ;
- **six `Star`** — 30 émetteurs et six lumières.

C'est littéralement un soleil entouré de six astres.

## L'ultime : ce qui change et ce qui ne change pas

**Rien de ce qui a été construit n'est perdu.** La scène, l'horloge de phases, le
gel, la caméra : c'était de l'architecture, et elle ne dépendait pas du contenu.
Seuls changent les noms des étapes et ce qui est joué à chacune.

Proposition : **invocation → ascension → embrasement → rasage → dissipation.**
Il ne saute plus, il appelle. Bras levés, l'aura s'allume ; l'astre monte au-
dessus de lui avec ses six satellites ; tout se fige une demi-seconde ; l'astre
s'abat. 2,6 secondes au lieu de 1,75 — une invocation qui ne se fait pas
attendre n'en est pas une.

Bonus non prévu : le saut disparaissant, toute la dette de physique qui
l'accompagnait disparaît avec (le personnage éjecté à 80 stud après l'impact, la
purge de vitesse, le repositionnement forcé).

Deux choses que je ne tranche pas : **est-il invulnérable pendant l'invocation ?**
(1,4 seconde immobile, c'est très long en PvP) et **le rayon** — 14 stud était
calibré sur un corps qui tombe, « pour tout raser » suggère plus large.

## Les M1 et les compétences : différencier par la nature

Ta correction — « le doré est représentatif de sa nature mais ne doit pas être
partout, d'autres VFX sont permis » — débloque exactement ce qu'on cherchait.
Elle est inscrite dans la spec, datée et signée.

Jusqu'ici la hiérarchie ne pouvait jouer que sur l'intensité : doré atténué
contre doré plein. Chaque M1 était donc *une version faible de l'ultime*.

Proposition : **les M1 passent à l'encre, les compétences mélangent trait et
lueur, l'ultime est de la lumière pure.** Un M1 est rapide et répété — le trait
se lit en trois images, pas la lueur. Un ultime est long et unique — la lumière a
le temps d'exister. Et quand l'astre arrive après quarante coups à l'encre, il
n'est pas le même effet en plus fort : il est d'une autre matière.

Ça règle ton reproche sur les M1 sans rien acheter de plus. Ils cessent d'être
dorés **parce qu'ils cessent d'être de la lumière**, pas parce qu'on les a
atténués.

---

# Les M1 ne sont plus dorés — parce qu'ils ne sont plus de la lumière

Tu avais validé le principe : différencier par la **nature** de l'effet, pas par
son intensité. C'est fait pour les quatre M1.

## Ce qu'ils sont devenus

| coup | forme | ce qui a disparu |
|---|---|---|
| 1 — direct | éclat à bordure hérissée | la gerbe dorée, **le flash** |
| 2 — crochet | anneau à bord franc | l'onde lumineuse, **le flash** |
| 3 — uppercut | croissant + poussière d'encre | le vent doré, **le flash** |
| 4 — finisseur | débris en cellulo + décharge | rien — **il garde son flash** |

Le finisseur garde sa lumière exprès. C'est le seul des quatre au palier
supérieur, et le passage de l'encre à la lumière est justement ce qui annonce
que le quatrième coup n'est pas un coup de plus.

La propriété qui fait tout, techniquement, tient en un réglage : `LightEmission`
à zéro. C'est elle qui sépare un trait d'une lueur. À un, même une texture à
bordure parfaitement nette se lit comme un halo, parce qu'elle s'additionne au
fond. C'est très exactement pourquoi « baisser les lumières » ne pouvait pas
marcher.

## Le doré n'a pas disparu — il a fallu le réinstaller

Piège évité de justesse : en écrivant les M1 en gris à la source, le portail de
momentum n'avait plus rien à neutraliser, donc **le doré ne serait jamais
revenu, à aucun palier**. Ta consigne — « le doré reste l'identité » — aurait été
vidée de son sens par un détail technique.

Le portail repose donc la teinte au palier surchargé, en conservant la
luminosité. La **forme ne change pas** : l'encre reste de l'encre, bordure nette.
Seule sa couleur change.

## Trois garde-fous qui criaient faux, corrigés le même jour

Tu m'avais demandé de réparer celui de l'audit. En le faisant, j'en ai trouvé
deux autres avec le même défaut.

1. **L'audit des packs** criait « DANGER » sur tout pack contenant un script —
   donc sur toute une catégorie, puisque n'importe quel pack de VFX livré dans un
   mannequin de démonstration en contient. Nouveau verdict : **« à lire »**. Ce
   n'est pas un feu vert : il interdit d'importer sans avoir lu les sources.
2. **La liste des effets de contact** a manqué un effet pour la troisième fois.
   Résultat : trois des quatre M1 ne produisaient **plus rien du tout** à bas
   momentum. Un coup sans retour est pire qu'un coup trop bruyant. Cette fois il
   y a un test, et je l'ai vérifié en le cassant exprès.
3. **La règle sur les identifiants d'assets** avertissait sur *tous* les
   identifiants, y compris ceux correctement enregistrés — donc à chaque commit,
   pour toujours. Un avertissement qu'on ne peut jamais satisfaire n'est pas un
   garde-fou, c'est du bruit, et le bruit finit ignoré. Il vérifie maintenant.

Le point commun des trois n'est pas la coïncidence : aucun n'avait de test qui le
prenne au mot.

## L'ultime : le rayon, mesuré

Tu m'as demandé de le déduire de la taille réelle de l'astre. Mesure faite sur le
fichier : la pièce `Sun` fait **16,48 stud**, sa plus grande particule **23,08**.
L'astre se lit donc sur environ 23 stud de diamètre, soit un **rayon de 11,5**.

C'est le contraire de ce qu'on attendait : **l'astre du pack est plus petit que
notre zone de dégâts actuelle** (14). Élargir creuserait l'écart entre ce qu'on
voit et ce qui touche — exactement ce que ta consigne interdit.

Proposition : que le rayon **découle** de l'échelle d'affichage de l'astre, au
lieu d'être un nombre réglé à part. Les deux ne peuvent alors plus diverger.

Les deux changements de l'ultime — les iframes limitées au gel, et ce rayon — ne
sont **pas encore câblés** : ils appartiennent au même bloc que la suppression du
saut, et le saut n'a de sens de disparaître qu'avec l'astre. Les appliquer seuls
rendrait le personnage punissable **en l'air**, ce qui serait une régression.

Il reste donc une seule chose bloquante : **les deux fichiers `.rbxm` doivent
être glissés dans Studio.**

---

# Les deux packs sont dans le jeu — sans glisser-déposer

Tu ne voulais pas le faire à la main. C'est fait autrement : les fichiers ont été
**lus, décodés et rebâtis** dans la place.

## Ce que ça a donné

| pack | reconstruit | vérifié |
|---|---|---|
| **The Creator VFX** | 212 objets, **111 émetteurs**, 7 lumières, le `Sun` à 16,48 stud, six `Star` | 4 792 propriétés comparées — **4 écarts, aucun sur un émetteur** |
| **100+ Combat VFX** | 2 505 objets, **2 073 émetteurs**, 27 faisceaux, 11 traînées | 79 357 propriétés comparées — **aucun écart** |

Les quatre écarts sont les positions des membres du mannequin de démonstration,
déplacés par le moteur quand il a raccordé leurs articulations. C'est de
l'échafaudage, pas du contenu.

## Pourquoi j'ai vérifié propriété par propriété

Un émetteur réglé, c'est quarante réglages, dont trois courbes — la taille, la
transparence, la couleur au fil du temps. Une reconstruction qui perdrait une
seule courbe donnerait un effet **plausible et faux**. Rien ne crierait. C'est
le pire mode de panne qu'on connaisse, et on en a mangé plusieurs.

Le programme relit donc chaque réglage **sur l'objet fabriqué** et le compare à
ce que le fichier déclare, point de courbe par point de courbe.

Une contre-vérification qui m'a rassuré : le code Python lit « 23,08 » pour la
plus grande particule du soleil en décodant le fichier ; l'émetteur reconstruit
répond « 23.08 » au moteur de jeu. Deux chemins indépendants, le même nombre.

## Ce qui ne se reconstruit pas — je le dis plutôt que de l'approcher

- **Les scripts du pack : refusés exprès**, pas par incapacité. Ce sont
  l'animation standard de Roblox et une démo de sept lignes. Importer du code
  d'un pack tiers ne doit pas pouvoir arriver par accident.
- **Les propriétés physiques d'un objet** : je ne sais pas les décoder. Deux
  dispositions essayées, les deux échouent, et les deux fichiers laissent 33
  octets inexpliqués. Sans conséquence ici — tous les supports d'effets sont
  fixes et sans collision. Si un pack livre un jour un objet physique, il faudra
  y revenir.
- **Seize réglages refusés** sur le pack de combat, tous des métadonnées internes
  de texture. **Aucun sur un émetteur.**

## L'astre

Il est vivant, et c'est bien ce que tu décrivais : une boule de feu tournante
avec sa couronne d'éruptions et six satellites. Reconstruit entièrement à partir
du fichier binaire.

Le contenu est rangé par usage : le soleil et ses satellites d'un côté ; l'aura
de corps de l'autre, répartie en six dossiers portant **exactement les noms des
pièces de nos personnages** — donc transférable sans retouche ; les effets de
frappe à part. **111 émetteurs sur 111 conservés.**

Tout ça est rangé là où le jeu cherche déjà ses effets, donc les recettes
pourront s'en servir **sans une ligne de code en plus**.

## Une chose que je ne peux pas faire

La reconstruction vit dans Studio mais **la place n'est pas sauvegardée**, et je
n'ai aucun moyen de la sauver moi-même — il n'existe pas de commande de
sauvegarde accessible depuis mon côté. **Il faut un Ctrl+S dans Studio.** Sinon
tout est perdu à la fermeture. C'est rejouable en deux commandes, mais autant ne
pas avoir à le refaire.

---

# Ton transfert et ma reconstruction : identiques, mesuré

Tu as transféré `The Creator VFX` toi-même. Les deux versions se sont donc
retrouvées côte à côte dans la place — et c'était l'occasion de répondre à ta
question sans rien téléverser.

```
ma reconstruction     111 émetteurs, 47 signatures distinctes
ton transfert         111 émetteurs, 47 signatures distinctes
écart, dans les deux sens : 0
```

Chaque signature compare trente réglages **plus les trois courbes** — taille,
transparence, couleur au fil du temps — point par point. C'est exactement là
qu'une reconstruction pourrait mentir de façon crédible. **Aucun écart.**

Ta question était la bonne, et la réponse est que sur ces fichiers les deux
voies se valent. Le désérialiseur de Roblox a servi d'arbitre.

## Le doublon — et ce qu'il cachait de pire

Ton transfert était dans le **Workspace**, avec le mannequin de démonstration
complet : 111 émetteurs et un personnage fantôme **dans la zone de jeu**. Le
doublon était le moindre des deux problèmes.

Je l'ai **déplacé, pas supprimé** — il est prouvé identique, donc rien ne serait
perdu, mais rien n'oblige non plus à détruire ton travail. Il est hors de portée
du résolveur d'effets : plus aucune ambiguïté sur ce qui tire.

## Un piège attrapé de justesse

Le jeu retrouve ses effets **par nom exact, premier trouvé**. Notre astre
s'appelait `Sun` — et un `Sun` existait déjà dans le kit Demon Slayer, rangé
avant. J'ai rejoué l'algorithme : il rendait un `Sun` à **un seul émetteur**.

Notre astre à dix émetteurs **n'aurait jamais tiré**, et l'ultime aurait produit
une étincelle sans que rien ne signale l'erreur. Renommés.

## L'ultime est maintenant une invocation

`invocation → ascension → embrasement → rasage → dissipation`.

Il ne saute plus, il appelle. Et **avec le saut disparaît toute la dette de
physique** : l'éjection à 80 stud après l'impact, la purge de vitesse, le
repositionnement forcé, l'attente du sol. Le rasage tombe désormais sur un
instant daté — le décalage qui faisait que l'ultime **ne touchait personne** ne
peut plus exister.

Invulnérable **pendant le gel seulement** : 0,40 s au lieu de 1,25.

Le rayon **découle** de la taille de l'astre : 11,54 stud, soit moins qu'avant.
Il ne se règle plus à côté. Pour couvrir plus, on agrandit l'astre et le rayon
suit tout seul.

La mise en scène côté joueur n'a demandé **aucune modification** — elle était
déjà pilotée par les données.

## Deux choses pour toi

**La seconde page Studio, je ne peux pas la fermer.** Elle n'est pas connectée à
mon pont : je ne la vois pas et je ne peux pas vérifier ce qu'elle contient. Ce
que je peux garantir, c'est que **tout le contenu du pack est dans notre place**
— 111 émetteurs sur 111, prouvés identiques. Ce que je ne peux pas garantir,
c'est que tu n'aies rien modifié dedans depuis. **À toi de la fermer.**

**Et il reste 601 émetteurs dans la zone de jeu**, dans le dossier de
démonstration du pack BZ1, bien antérieur à ce chantier. Ce n'était pas mon
sujet aujourd'hui, mais c'est beaucoup pour une zone où on se bat.

---

# Le dossier `Read Me!` : ce qu'il contient, et une trouvaille à côté

## D'abord, je me suis trompé

J'ai écrit la dernière fois que ces 601 émetteurs étaient « en pleine zone de
combat ». **C'est faux, et je l'avais déduit sans mesurer.**

Le dossier est centré à 1 096 stud du centre de l'arène, et sa pièce la plus
proche est à **875 stud**. L'anneau de l'arène est à 37. C'est vingt-quatre fois
plus loin que l'arène n'est large. Aucun joueur ne s'en approchera.

## Ce que c'est

Une **vitrine de démonstration** : 26 auras BZ1, chacune portée par un mannequin
avec son étiquette. 575 émetteurs, 36 personnages, 22 panneaux de texte.

**Et il n'apporte rien d'unique.** Les 26 auras qu'il contient sont *toutes*
déjà dans notre archive, qui en compte 137. Intersection complète, zéro
exclusivité.

## Est-ce que ça coûte ? Oui, mais pas là où on croyait

563 des 575 émetteurs sont allumés. Mais le jeu a le **streaming activé** et le
dossier est à 875 stud : il n'est jamais envoyé au joueur qui se bat. **Le coût
d'affichage est nul.**

Le vrai coût, c'est **19 scripts actifs** qui tournent en boucle, image par
image, sur le serveur :

```lua
while true do
    -- fait tourner le modele de 0,08 radian
    task.wait()
end
```

Le streaming n'empêche pas un script du Workspace de tourner. Ces dix-neuf
boucles s'exécutent en permanence pour faire tourner une décoration que personne
ne verra jamais.

## Est-ce que quelque chose s'en sert ? Non — mais j'ai trouvé pire

Le jeu ne cherche pas ses effets dans le Workspace, donc ce dossier ne peut
détourner personne. Bonne nouvelle.

**Mais en vérifiant, j'ai trouvé une fragilité de fond.** Sur les 40 effets que
nos recettes appellent par leur nom :

```
 2 se trouvent dans le dossier des packs sûrs
37 n'y sont PAS — ils sont trouvés par un chemin de SECOURS, dans l'archive
```

**Toute la couche d'effets du jeu tient à un dossier nommé « archive du
2026-05-11 »** — c'est-à-dire quelque chose qu'on range un jour de ménage. Si ce
dossier disparaît, les effets s'arrêtent **sans aucune erreur** : le code se
contente d'un avertissement et ne fait rien. Exactement comme notre astre qui
n'aurait jamais tiré sous le nom `Sun`, mais à l'échelle de tout le kit.

*(J'ai aussi trouvé un nom en double, `Dust`, utilisé par quatre compétences. J'ai
comparé les trois candidats réglage par réglage : ils sont identiques. Sans
conséquence — je le dis plutôt que de crier au loup.)*

## Et le trait ? Presque rien

31 textures mesurées sur 209 (les autres refusent le téléchargement — donc c'est
un échantillon de 15 %, et je ne l'extrapole pas).

```
Read Me!           6 % d'encre
100+ Combat VFX   29 % d'encre
The Creator VFX    0 %
```

Et sur les deux « encres » trouvées, une seule est utilisable : une décharge
angulaire à bords francs. L'autre fait 64 pixels et n'est qu'un motif de fond.

**Ce dossier n'apporte rien pour le trait.**

## Ce que je n'ai pas fait

Rien supprimé, rien déplacé, comme demandé. Les faits sont posés.

---

# Deux systèmes de combat regardés — et une mesure qui explique beaucoup

## Ce que j'ai pu voir, et ce que je n'ai pas pu

Les deux pages refusent la lecture automatique ; je les ai ouvertes au
navigateur. J'ai la description, la liste des fonctionnalités, le guide
d'installation, le prix, les avis.

**Je n'ai pas le code, ni le nombre d'animations, ni les durées, ni les fenêtres
de jeu, ni la structure réseau.** Les vidéos ne sont pas lisibles par mes outils.
Juger leur fluidité réelle serait de l'invention — c'est l'erreur que j'ai faite
sur Strikeborn, je ne la refais pas.

## Un fait à connaître avant d'acheter

**Les deux sont du même vendeur, `skaterstudios`.** Ce nom est déjà dans nos
dossiers : son pack d'auras est le **seul** du projet écarté **sur la sécurité**.

Ce n'est pas un verdict sur ces deux-là, qui n'ont pas été audités. Mais leur
propre guide d'installation demande d'activer **« Allow HTTP Requests »** — un
système de combat n'a aucune raison technique de sortir sur le réseau.

## Ce qui nous manque vraiment

Mesuré en cherchant dans notre code, pas estimé :

**Absent chez nous : feinte, roll cancel, clash, combos aériens, casse de garde,
et tout le support mobile** (zéro ligne, pas une seule).

Déjà présent : dash directionnel, ragdoll, blocage, parade, uppercut, downslam,
barre de ressource. Et sur les **réactions de coup**, nous sommes devant : 16
animations avec des variantes multiples, là où leurs pages n'en mentionnent
aucune.

## La mesure qui explique le « c'est primitif »

Notre code annonce une fenêtre d'annulation de 200 ms. Mais elle s'ouvre au
moment de l'impact et se referme à la fin de la récupération — sa vraie durée est
donc la différence entre les deux :

```
coup     fenetre reelle    images a 60 ips
M1_1         40 ms              2,4
M1_2        162 ms              9,7
M1_3        200 ms             12,0
M1_4        197 ms             11,8
```

**Le premier coup de la chaîne — celui qu'on presse le plus — a une fenêtre cinq
fois plus étroite que les trois autres.** Deux images et demie.

Ce n'est pas une supposition : c'est exactement le bug qu'on avait déjà trouvé et
corrigé en août pour les coups 2, 3 et 4. **Le premier a été oublié.**

Un enchaînement qui accroche à son ouverture, à chaque fois, et rien ne le
signale.

## Architecture ou assemblage ?

**L'assemblage, très majoritairement.**

Trois choses mesurées le même jour disent la même chose : la fenêtre du premier
coup vaut 40 ms au lieu de 200 ; 37 de nos 40 effets ne tiennent qu'à un dossier
nommé « archive » ; et le jeu allait chercher un mauvais « soleil » à un seul
émetteur au lieu du nôtre à dix.

Aucun des trois n'est un défaut de conception. Aucun ne produit d'erreur. Le jeu
tourne, les effets sortent, l'enchaînement passe — **moins bien qu'il ne devrait,
sans que rien ne le dise.**

**Le vrai manque de conception est court** : roll cancel, feinte, clash. Trois
mécaniques d'**interruption** — c'est précisément ce qui sépare un combat qui se
lit comme une suite d'actions d'un combat qui se lit comme un échange. Notre
moteur sait déjà annuler ; il ne sait annuler que vers un dash.

## Ma recommandation : ne rien acheter

Vendeur déjà écarté ailleurs sur la sécurité. Accès réseau demandé sans raison.
Et ce qu'ils apporteraient — trois mécaniques — se décrit en trois paragraphes,
sur des fondations qu'on a déjà.

Acheter un système complet pour trois mécaniques nous ferait hériter d'**un
second moteur de combat à côté du nôtre**.

Ce que je ferais à la place, dans l'ordre : corriger la fenêtre du premier coup
(une valeur, mesurable tout de suite), puis roll cancel, puis feinte, puis clash.

---

# Je retire un chiffre que je t'ai donné — et l'archive est réglée

## D'abord la correction

Je t'ai annoncé que le premier coup de la chaîne avait une fenêtre d'annulation
de **40 ms au lieu de 200**, et tu as relayé ce chiffre à Milan.

**C'est faux. Elle vaut 159 ms, et il n'y a aucun bug.**

Ma mesure lisait le *texte* du fichier au lieu de la *table* de données, et elle
a attrapé une valeur qui traînait dans un vieux commentaire — commentaire
lui-même périmé depuis une re-génération de l'animation.

J'ai donc écrit un balayage qui regarde les **neuf** coups du kit, lit la vraie
table, et tient compte du fait que chaque coup a son propre nom de repère (les
M1 utilisent « Impact », les compétences « HitConnect »). Résultat :

```
neuf coups, fenetres de 113 a 200 ms — AUCUNE alerte
```

La correction d'août n'a laissé aucun survivant. **Sur ce point, le système est
sain.** Mon diagnostic « c'est l'assemblage, pas l'architecture » perd une de ses
trois preuves ; les deux autres tiennent et restent mesurées.

## L'archive : réglée

J'ai suivi l'ordre validé — mesurer, déplacer, re-mesurer.

```
AVANT   47 effets — 5 sains, 42 trouvés par le chemin de secours
APRÈS   47 effets — 47 sains, 0 par le secours
42 déplacés, aucun échec, aucun effet perdu
```

**Déplacés, jamais copiés.** Copier aurait créé un doublon de nom par effet, et
c'est exactement ce qui a failli nous faire tirer un mauvais soleil.

Effet de bord non prévu et bienvenu : **les doublons de noms passent de 11 à 2.**

L'archive garde 10 560 effets dont **plus aucun n'est utilisé** — elle redevient
ce que son nom dit, quelque chose qu'on peut ranger.

## Un doublon actif à te signaler

Sur les deux qui restent, l'un est inoffensif (trois copies identiques). L'autre
ne l'est pas : **deux effets différents s'appellent `Wind`** — l'un à six
émetteurs, l'autre à un seul — et c'est le premier trouvé qui gagne. Il est
utilisé par la première compétence.

**Ce n'est pas cassé aujourd'hui** : le jeu prend depuis toujours celui à six.
Mais réorganiser un dossier suffirait à basculer sur celui à un, sans erreur.
Le correctif est le même que pour le soleil — un nom unique. Je ne l'ai pas
appliqué : choisir lequel des deux est le bon est un choix, pas une mesure.

## Trois garde-fous en place

Une **liste explicite** des 47 effets dont le jeu dépend — elle n'existait nulle
part. Un **test** qui échoue dès qu'une recette utilise un effet absent de la
liste. Et un **contrôle en jeu** qui répond, pour chaque effet : *introuvable /
sain / trouvé par le secours*. C'est ce troisième mot qui compte : il transforme
une dépendance invisible en ligne de rapport.

Et l'avertissement « effet introuvable » ne se répète plus à chaque coup — une
fois par nom, avec un compteur. C'est le troisième garde-fou de la semaine qu'on
corrige pour avoir crié trop fort pour être écouté.

---

# Premier contact réel : tout tourne, et un défaut apparaît

Ta sauvegarde a tenu. Les deux packs sont là et le jeu les retrouve **en jeu**,
pas seulement dans l'éditeur.

## La chaîne de coups à l'encre marche

Quatre clics réels, quatre coups, et chacun produit exactement les formes que sa
recette annonce — l'éclat pour le direct, l'anneau pour le crochet, le croissant
et sa poussière pour l'uppercut, les débris pour le finisseur.

Je les ai vues vivantes en jeu, sur fond sombre. **Ce sont bien des traits** :
bordures franches, pas de halo.

*(Une réserve honnête : le pont ne me laisse pas enregistrer les images sur le
disque. Elles existent dans le fil de la session, pas dans le dépôt.)*

## Le momentum : ce n'était pas un bug, c'était ma façon de tester

Douze coups portés et la barre restait à zéro. J'ai cru à une panne. En posant
une sonde sur le canal de momentum, la vérité était plus simple : **le crédit
marche parfaitement** — six points par coup, seize au quatrième de la chaîne —
mais il redescend de huit points par seconde, et mes pauses entre rafales
duraient des dizaines de secondes.

En frappant sans interruption, la barre monte à **100 sur 100** et s'y fige.
Aucune correction n'était nécessaire ; c'est mon protocole qui était faux.

## L'ultime a tiré, avec l'astre

C'est la première fois que l'ensemble tourne. L'animation part, **l'astre du
pack apparaît avec ses six satellites**, le sol est rasé, et **vingt-quatre
éclats de terrain** volent — le chantier du décor cassable et celui de l'ultime
se rencontrent enfin. Le momentum est consommé.

## Mais le rythme ne tient pas, et c'est visible

La chronologie qu'on a validée prévoit **0,95 seconde entre l'apparition de
l'astre et le rasage** — c'est le gel, le temps suspendu, tout l'intérêt de la
mise en scène.

**Mesuré : 0,19 seconde.** L'astre apparaît et le sol explose presque en même
temps. Les cinq phases s'écrasent en un seul instant. Et l'astre arrive une
seconde et demie après le début du geste, au lieu d'une demi-seconde.

**Je ne sais pas encore pourquoi**, et je ne vais pas inventer une cause. Deux
explications tiennent debout : soit le serveur émet en retard, soit c'est
l'astre — une pièce lourde, dix émetteurs — qui met une seconde à voyager
jusqu'à l'écran pendant que les effets de rasage, eux, sont calculés localement
et arrivent instantanément. Une mesure horodatée des deux côtés tranchera.

Je n'ai pas non plus vérifié le bandeau noir ni le titre : ma sonde regardait le
monde, or une interface vit ailleurs. Je n'ai donc aucune preuve qu'ils aient
joué.

## Ce que je ferai ensuite

Séparer les deux hypothèses sur le retard, vérifier le bandeau, **et seulement
après** juger la scène à l'œil. Une scène dont le rythme est cassé ne se juge
pas au goût — on répare l'horloge d'abord.

---

# Prêt à tester : la surcharge se voit

**1. La décroissance du momentum est en pause.** Comme demandé, et proprement :
un drapeau nommé dans le service, pas une ligne commentée qu'on oublierait de
remettre. La vraie valeur (8 par seconde) reste juste au-dessus, intacte — c'est
elle qui fera foi quand on réglera vraiment ce paramètre. **Pour la réactiver :
un seul `true` à passer en `false`.**

C'est noté au journal comme dette assumée, avec la raison, pour qu'une session
future ne prenne pas ça pour l'équilibrage voulu.

**2. Au maximum, le personnage s'embrase.** L'aura dorée monte de tout le corps
— 65 émetteurs, répartis sur les six pièces, ceux du pack `The Creator` qui
dormaient depuis le transfert. Et un geste de montée en puissance se joue une
fois au passage à 100.

Je n'ai rien fabriqué : l'animation existait déjà dans nos packs, 1,33 seconde,
le personnage qui se ramasse et se redresse. Cherché avant d'autorer, comme
toujours.

**L'aura est posée côté serveur, et c'est voulu** : la spec dit que l'état chargé
doit être lisible **par l'adversaire**. Une aura montée sur l'écran du porteur ne
serait vraie que pour lui.

**3. Le défaut de rythme de l'ultime est réglé.** Le gel dure maintenant sa
durée dès le premier déclenchement.

Au passage, une leçon que je note contre moi : mon premier correctif annonçait
fièrement « 47 effets sur 47 préchauffés » — et avait raté **exactement les deux
seuls qui comptaient**, parce que l'ultime les appelle directement au lieu de
passer par une recette. Le premier tir est alors devenu *pire* qu'avant. C'est le
compte affiché qui a permis de le voir.

```
premier declenchement, duree du gel      cible 0,95 s
  avant                                  0,58 s
  correctif incomplet                    0,07 s
  correctif complet                      1,00 s
```

**C'est prêt.** Frappe le mannequin une quinzaine de fois : la barre se remplit
et ne redescend plus, le personnage s'embrase, et `R` déclenche l'ultime.

---

# L'astre était détruit par notre propre code

## Pourquoi tu ne le voyais pas

`DemiDieu_Astre` n'est pas un support invisible : c'est une **boule lumineuse de
16 stud**, le corps du soleil lui-même.

Or notre code faisait, sur tout effet cloné : *rendre la pièce invisible et la
réduire à un dixième de stud*. C'est **juste pour 46 effets sur 47** — nos packs
livrent des pièces-support qui ne portent que des particules, avec une boîte de
présentation qu'il ne faut surtout pas montrer en jeu. Pour l'astre, ça
**détruisait exactement ce qu'on voulait voir**.

L'effet naissait, je le mesurais, je vérifiais qu'il se résolvait — et il ne se
voyait pas. C'est précisément le piège qu'on traque depuis dix jours : **mes
mesures étaient justes et ne disaient rien du problème.**

## Et maintenant il raconte ton geste

*« Elle apparaît puis explose sur le sol, comme si on lançait un soleil. »* Un
objet qui apparaît et reste suspendu ne raconte pas ça. Mesuré en jeu :

```
il apparait, petit et bas          taille  6,5   hauteur  9,8
il monte en grossissant            taille 16,5   hauteur 21,0
il TIENT, immobile                 0,37 s        c'est le gel
il s'abat, lent puis brutal                      hauteur  0,5
il eclate et disparait             taille 39,5
```

Le corps ne survit pas à l'impact — un soleil posé au sol ferait « décor » au
lieu d'« événement ».

## Le rig : le garde existait, il n'était posé que d'un côté

Bonne nouvelle d'abord : **aucun reste du saut supprimé.** La position du
personnage est parfaitement stable pendant tout l'ultime.

Le vrai défaut : une **petite animation d'inactivité** (le personnage qui incline
la tête) démarrait un dixième de seconde **avant** l'ultime et continuait à
bouger tête, bras et torse pendant une seconde et demie par-dessus.

Notre code refusait déjà de *lancer* ces fioritures pendant une compétence — son
propre commentaire dit qu'elles « corrompent visuellement les animations ». Mais
il ne coupait pas celles déjà en cours. Corrigé.

## L'aura : tu choisis la couleur

Quatre variantes prêtes à essayer, un seul mot à changer : **origine** (les
flammes du pack, réglage actuel), **doré** (la signature du kit), **blanc**
(plus froid, plus « demi-dieu »), **pourpre** (registre menace).

## Et le pack en double

Tu avais re-déposé le pack de combat — 2 073 effets dans la zone de jeu. Il était
à 46 stud de l'arène, donc sans rapport avec l'astre, et le jeu ne le consultait
pas. Rangé, pas supprimé.

## Ce que je n'ai pas réussi

**Aucune image de l'astre en vol**, après cinq tentatives. La raison est bête et
je la pose : mes commandes mettent trois secondes à faire l'aller-retour, et
l'astre n'est à pleine taille que quatre dixièmes de seconde. Je peux le mesurer,
pas le photographier.

**Il faut que tu le regardes toi-même.** Les chiffres disent ce que tu verras ;
ils ne remplacent pas ton œil.

---

# Retenue sur l'ultime : ce qui saute, et une erreur que j'ai attrapée à temps

## D'abord un empilement que personne n'avait voulu

En regardant ce que l'ultime empile, j'ai trouvé une fuite : **l'aura de
surcharge n'était jamais retirée**. Les 65 émetteurs restaient sur le personnage
pendant tout l'ultime — où la recette du rasage en ajoute encore une — puis
restaient indéfiniment après.

La cause : la consommation du momentum écrit « zéro » par un chemin qui
court-circuitait le code chargé d'éteindre l'aura. Corrigé.

## L'erreur que j'ai failli publier

Première image, soleil + six satellites : le soleil apparaissait **brun et
terne**. J'allais conclure que les satellites le noyaient — conclusion attendue,
cohérente avec un cas qu'on avait déjà rencontré.

**C'était l'ordre des captures.** Les particules s'accumulent avec le temps ; ma
première image était simplement prise plus tôt. J'ai remis les satellites et
repris la photo au même endroit : **le soleil est resté éclatant.**

Ils ne noient rien. Je l'aurais écrit comme cause si je m'étais arrêté à la
première image.

## Mais ils sautent quand même, pour une autre raison

```
rayon du soleil          8,24
rayon de leur couronne   9,81
distance a la SURFACE    1,57
```

Ce ne sont pas des satellites **autour** du soleil : ce sont des décorations
**posées sur son disque**. On les voit sur l'image — quatre étoiles blanches
plaquées sur sa face, qui concurrencent sa propre texture.

On pourrait les repousser plus loin pour qu'ils lisent comme une vraie couronne.
Je ne l'ai pas fait : le geste, c'est **« on lance UN soleil »**, et une seconde
idée visuelle autour dilue la première. Les 30 émetteurs restent dans le pack —
**disponible n'est pas une raison.**

## Deux effets d'impact sautent aussi

- **La traînée de taille** : il n'y a aucune taille dans ce geste. L'astre tombe,
  le personnage n'arme rien. C'était du vocabulaire de M1 posé sur un ultime
  parce qu'il était là.
- **La sphère lumineuse au point de contact** : l'astre explose désormais
  lui-même en gonflant du simple au double avant de disparaître. Une seconde
  sphère au même endroit au même instant est un doublon.

## Ce qui reste, et pourquoi

Les trois couches de sol — écrasement, poussière, fissures — **sont** ce que
« raser la zone » veut dire ; sans elles l'impact n'a aucune conséquence
visible. Les débris projetés. Et une aura sur le personnage, pour que le geste
lui appartienne encore et pas seulement à l'astre.

```
phase montee / gel   40 effets  ->  10   (-75 %)
phase impact          4 atomes  ->   2
```

**Rien ajouté.**

## Une réserve honnête

**Le soleil seul, je le trouve juste** — noyau clair, langues de flamme,
silhouette nette. Il se lit comme un soleil dès la première image.

Si tu le trouves maigre après cette coupe, ce que je défendrais n'est pas de
rajouter des couches autour : c'est **d'agrandir l'astre lui-même**, ce qui
élargit aussi sa zone d'impact puisque les deux sont liés. Une seule idée, plus
grande, plutôt que plusieurs idées empilées.

---

# Tu peux juger l'ultime sans être devant

## Le blocage de capture est levé

Je disais que je ne pouvais pas écrire d'image. C'était la mauvaise question :
l'outil de capture macOS fonctionne très bien. Le vrai obstacle, c'était le
**temps** — mes commandes mettent trois secondes à faire l'aller-retour, et
l'astre n'est à pleine taille que quatre dixièmes de seconde.

La solution est celle qu'on avait déjà employée pour les animations : **figer**.
J'ai rejoué les cinq instants mesurés côte à côte, en statique, et je les ai
photographiés d'un coup.

**La planche est là. Tu peux juger le geste entier à ton retour.**

*(Deux pièges au passage : ma première capture a photographié Safari au lieu de
Studio, et les particules ne s'animent pas dans l'éditeur — il faut être en mode
jeu. C'est la même confusion qui m'avait fait conclure de travers sur les
satellites.)*

## Les M1 : ce n'était pas une question de goût

En comparant les quatre recettes, une différence saute aux yeux :

**M1_1 est le seul à porter un élément de direction** — un couloir le long du
coup, en plus de sa forme. Et M1_2 n'avait qu'une seule forme, la plus maigre
des quatre.

Ça correspond exactement à ton jugement sans que tu aies eu à l'expliquer. J'ai
donné à M1_2 son propre élément directionnel : un éventail au sol, parce qu'un
crochet balaie.

Je n'ai pas touché aux deux autres : elles portent déjà deux formes et sont au
plafond de lisibilité. Changer sans savoir ce qui échoue serait deviner.

## La fluidité : la mesure contredit ce qu'on pensait

J'ai appliqué ta piste — proportionner le fondu à la durée du geste — et elle est
juste. Mais elle dit autre chose que prévu :

```
                          duree   avant   apres
M1_1                       0,55   0,020   0,033
Skill1                     0,70   0,050   0,050     <- ne bouge pas
Skill2                     0,83   0,050   0,050     <- ne bouge pas
Ultime                     4,50   0,080   0,180
```

**Les compétences ne bougent pas.** Elles durent moins d'une seconde, donc leur
fondu proportionnel reste sous la valeur déjà écrite. **Le fondu n'explique donc
pas le « saccadé » sur les compétences.** La règle reste bonne et profite surtout
à l'ultime.

## Les compétences : j'ai trouvé une cause mécanique

Trois faits, dont un sérieux :

- Deux compétences ont leur repère d'impact au même millième, sur des gestes de
  durées différentes. Il a été posé par recopie, pas par le geste.
- Leur fenêtre d'enchaînement est la plus courte du kit — elles « collent ».
- **Le contrôle revient avant la fin du geste.** Les deux rendent la main à
  0,55 seconde alors qu'elles durent 0,70 et 0,83. Le joueur peut relancer une
  action pendant que l'animation tourne encore — et la nouvelle écrase l'ancienne
  en plein mouvement.

**C'est mécanique, pas esthétique**, et c'est très probablement ce que tu vois.
Je n'ai rien changé : c'est le même genre de correction que celle du 29 août sur
les M1, elle mérite le même soin.

## Une décision qui t'appartient

L'animation de l'ultime dure **4,5 secondes**, la mise en scène **2,6**. Elle
traîne près de deux secondes après que tout s'est refermé. Deux issues :
allonger la scène, ou accélérer l'animation. **C'est ton animation, je ne
tranche pas.**

---

# Trois vérifications, trois surprises

## 1. Ce n'était pas un défaut — et j'avais tort

Tu m'as demandé de vérifier avant de corriger. Bien vu : **la correction du
2 septembre est intacte**, ligne pour ligne. Le verrou se lève tôt, mais le
retour à l'immobilité attend la fin réelle du geste. Son propre commentaire dit
qu'une nouvelle action écrase la piste **à dessein**.

J'avais signalé comme défaut un comportement qu'on a construit exprès.

## 2. Ton hypothèse ne tient pas non plus — mesurée

Ta lecture était que la coupure se voit plus sur un geste ample que sur un jab.
J'ai mesuré l'écart de pose au moment exact où le joueur reprend la main :

```
jab              618
Main du Colosse  619
Frappe Celeste   656
```

**C'est le même saut.** Une compétence ne se coupe pas plus brutalement qu'un
coup rapide. Et Main du Colosse a même *moins* de geste restant qu'un jab.

## 3. Ce que la mesure a trouvé à la place

```
Marche du Titan   animation 0,97 s   verrou 1,10 s   ->  0,13 s de blanc
Jugement          animation 0,57 s   verrou 1,30 s   ->  0,73 s de blanc
```

**Jugement bloque le joueur plus de deux fois plus longtemps que son propre
geste ne dure.** Ce n'est pas une coupure trop brutale — c'est l'inverse : le
geste finit, puis il ne se passe plus rien pendant trois quarts de seconde.

C'est très probablement ce qui fait « pas premium ». **Je n'ai rien changé** :
c'est un réglage d'équilibrage, pas une réparation.

## 4. Les repères d'impact étaient justes

Tu m'avais dit d'y aller — deux valeurs identiques au millième, ça sent la
recopie. J'ai mesuré l'instant où le bras va le plus vite, dans chaque
animation :

```
                    mesure    declare    ecart
Main du Colosse     0,4317     0,4375    6 ms
Frappe Celeste      0,4288     0,4368    8 ms
Marche du Titan     0,5173     0,5089    8 ms
```

Les trois écarts sont **sous la précision de ma propre mesure**. Les deux
compétences frappent réellement vers 0,43 seconde — la ressemblance est un fait
sur les animations, pas une paresse de transcription.

**Je n'ai rien recalé.** Corriger des valeurs déjà justes aurait été du bruit.

## 5. L'ultime : la scène suit enfin le geste

En mesurant l'animation image par image, j'ai trouvé ceci :

```
0,50 s   premier elan
0,95 s   arret complet
1,85 s   second elan
2,25 s   LES MAINS AU PLUS HAUT
2,75 s   immobilite
4,50 s   fin
```

**L'astre s'abattait à 1,40 seconde — presque une seconde avant le sommet du
geste**, pendant que le personnage levait encore les bras. Voilà le vrai
désalignement.

Chaque phase est maintenant posée sur un temps fort mesuré, et la scène couvre
les 4,5 secondes entières au lieu de se refermer deux secondes trop tôt.

**Ton animation n'est pas touchée** — ni sa vitesse, ni sa durée.

Une conséquence à trancher : le temps suspendu passe de 0,40 à 0,75 seconde, et
l'invulnérabilité qui lui est liée suit. C'est un effet de l'alignement, pas un
choix d'équilibrage.

---

# Ton découpage de l'ultime — proposition, et trois choses que la mesure corrige

## 1. L'impact frame se déclenche déjà — au mauvais moment

Tu dis qu'elle ne tire pas dans l'ultime. **Elle tire** : je l'ai mesurée en
jeu, elle apparaît à 1,9 seconde. Le problème n'est pas qu'elle manque, c'est
qu'elle est accrochée à **l'explosion** alors que tu la veux au moment où le
personnage **sort sa puissance**.

Tes deux références sont les **deux polarités de la même silhouette** — blanc
sur noir, et noir sur blanc. On utilise la première, c'est le bon choix pour un
ultime.

## 2. Le soleil est déjà à la bonne taille

J'ai mesuré ta promo : le soleil fait **4,5 fois** la hauteur du personnage. Le
nôtre en fait **4,6**.

**Il n'est pas trop petit.** Ce qui manque, c'est le cadrage : ta promo est un
plan serré de face où le soleil remplit le haut de l'image ; chez nous la caméra
est reculée de 14 stud et le soleil est 18 stud plus haut — il est loin, donc
petit à l'écran.

**La réponse est la caméra, pas la taille.** Je retire donc ce que je proposais
ce matin (agrandir l'astre) : on cadre d'abord, on jugera après.

## 3. Les étincelles aux pieds, je les avais retirées

Ta promo montre des étoiles à quatre branches autour des pieds du personnage.
**Ce sont exactement les six satellites que j'ai supprimés ce matin** — je les
avais retirés parce qu'ils étaient collés au soleil, à un stud et demi de sa
surface.

Ils n'étaient pas de trop. Ils étaient au mauvais endroit, et ta promo dit où
ils vont.

## La chronologie proposée

```
 0,00  la camera COUPE vers une vue de face, 7 stud devant lui
 0,50  IL SORT SA PUISSANCE — impact frame + etincelles aux pieds
 0,95  LE SOLEIL NAIT DANS SA MAIN DROITE, petit
 1,85  il monte depuis la main, en grossissant
 2,25  la camera COUPE vers la troisieme personne
 2,60  le soleil s'abat et explose
 3,20  la camera est rendue
 4,50  fin
```

Chaque temps est posé sur un **temps fort mesuré** de ton animation, pas sur une
estimation. Deux coupes franches, pas de mouvement de caméra : un balayage de
180° donne le mal de mer.

## Ce qui coince, et que je ne tranche pas

**Une caméra de face te rend aveugle.** Tu vois ton personnage et ce qu'il y a
derrière lui — donc plus l'arène où l'adversaire bouge. Pendant **2,25
secondes**. Or ton invulnérabilité ne dure que 0,75 seconde.

Tu serais donc aveugle **et** frappable pendant une seconde et demie.

Trois issues : étendre l'invulnérabilité à toute la vue de face, raccourcir la
vue de face (mais on perd le soleil invoqué vu de face, qui est le cœur de
l'image), ou assumer.

**Je recommanderais la première**, bornée : invulnérable tant que tu ne vois
pas, frappable dès que la caméra revient. C'est une règle lisible. Mais c'est
ton jeu.

## Une inconnue honnête

**Un personnage R6 vu de face est plat** — pas d'épaules articulées, pas de cou.
Le plan serré de face est le cadrage le plus exigeant pour ce type de
personnage. Je ne peux pas te garantir que ça rende bien avant de l'avoir posé.
Tu jugeras à l'image.

---

# La scène est construite

Ton découpage, mesuré en jeu, dans ton ordre :

```
+0,21  le bandeau se ferme
+0,40  LA CAMERA COUPE vers le personnage
+0,76  IL SORT SA PUISSANCE — impact frame
+1,21  LE SOLEIL NAIT DANS SA MAIN DROITE, et six etincelles aux pieds
+2,64  RETOUR EN TROISIEME PERSONNE
+2,86  L'EXPLOSION
+3,48  la camera t'est rendue
```

Les cinq temps y sont. Le décalage régulier d'un quart de seconde est le
va-et-vient réseau.

## Ce que j'ai vérifié avant de coder

L'attache de la main droite **existe** sur notre personnage. Je l'ai lue en jeu
plutôt que de la supposer — c'est ce qui autorise l'invocation depuis la main.

## Un défaut que j'ai créé et corrigé dans le même tour

Le retour en troisième personne était **défait deux dixièmes de seconde plus
tard** : le recul de caméra de l'explosion reprenait la main. Mesuré, corrigé —
le recul ne s'applique plus que pendant la phase cadrée.

## Invulnérable tant que tu ne vois pas

De 0 à 2,25 seconde, exactement la durée pendant laquelle la caméra te cache
l'arène. **Tu redeviens frappable à l'instant où tu revois.**

## Le cadrage : trois-quarts

J'ai comparé plein face et trois-quarts au même instant, même distance, même
hauteur — seul l'angle change.

**Je retiens le trois-quarts.** De face, un personnage R6 est un rectangle :
sans épaules articulées ni cou, la silhouette s'aplatit. À trois-quarts le corps
prend du volume et le bras droit — celui qui invoque — se lit.

**Mais je ne surjoue pas** : la différence est réelle et **modeste**, et le
mannequin d'entraînement s'est replacé dans l'un des deux cadres malgré mon
déplacement. C'est un argument, pas une démonstration écrasante. Tu trancheras.

## Ce que je n'ai pas pu confirmer

Les six étincelles aux pieds **sont posées** — je les ai comptées. Mais **je ne
les distingue pas** sur les captures : le personnage et l'interface occupent le
bas du cadre. Elles sont peut-être trop discrètes. À régler si tu ne les vois
pas non plus.

## Deux rappels

**Le contrôle qui revient avant la fin du geste n'est pas un défaut** — c'est la
correction de mardi, intacte, et elle est voulue. Ce que la mesure a trouvé à la
place, c'est du **temps mort** : Jugement te bloque 1,30 seconde pour un geste
de 0,57.

**Les repères d'impact ne sont pas une recopie** : les trois écarts entre valeur
déclarée et pic mesuré sont sous la précision de ma propre mesure. Rien à
recaler.

---

# Le temps mort, les étincelles, et 9 % de serveur récupérés

## L'audit que tu demandais

Durée du geste contre durée du verrouillage, mesurées en jeu :

```
piece    geste   verrou    ecart
M1_1      0,55     0,34    -0,21   interruptible (voulu)
M1_2      0,60     0,39    -0,21   interruptible (voulu)
M1_3      0,65     0,42    -0,23   interruptible (voulu)
M1_4      0,85     0,52    -0,33   interruptible (voulu)
Skill1    0,70     0,55    -0,15   interruptible (voulu)
Skill2    0,83     0,55    -0,28   interruptible (voulu)
Skill3    0,97     1,10    +0,13   un peu long
Skill4    0,57     1,30    +0,73   TEMPS MORT
Ultime    4,50     4,50     0,00   aligne
```

**Sept pièces sur neuf sont saines.** Deux dépassent, une seule gravement.

*(Neuf et non dix : l'aura de cast n'a pas de verrouillage.)*

## L'argument qui tranche

**Jugement a déjà le plus long temps de recharge du kit — 12 secondes.** Le prix
de la compétence est payé là. Les trois quarts de seconde debout par-dessus ne
sont pas de l'engagement : l'engagement se paie en recharge, pas en immobilité.

Un geste qui dure une demi-seconde et bloque une seconde et demie ne pèse pas,
**il traîne**.

## Valeurs proposées — à toi de trancher

Les sept pièces saines ont toutes un rapport verrou/geste entre **0,61 et 0,79**.

```
Marche du Titan   0,97 de geste   1,10 aujourd'hui  ->  0,75
Jugement          0,57 de geste   1,30 aujourd'hui  ->  0,45
```

Je prends le haut de la fourchette : ce sont des compétences lourdes, elles
doivent engager plus qu'un coup rapide. Mais jamais au-delà du geste.

**Si tu veux que Jugement coûte plus cher, augmente sa recharge, pas son temps
mort.**

## Les étincelles : j'ai sur-corrigé, puis encadré

```
faible, tous les effets   ->  invisible
fort,   tous les effets   ->  des PILIERS de lumiere qui avalent le personnage
moyen,  ETOILES SEULES    ->  six eclats nets aux pieds       <- retenu
```

L'encadrement a révélé la cause : chaque satellite porte **une étoile à quatre
branches** — celle de ta promo — **et quatre flammes verticales**. Ce sont les
flammes qui faisaient les piliers. On les écarte.

Correction de ce que j'affirmais hier : les satellites ne **sont** pas les
étincelles de la promo, ils en **contiennent une sur cinq**.

## 9 % de serveur récupérés

```
avec les 19 boucles : 36,2 images/s serveur
sans                : 39,5
```

Neuf pour cent, pour animer une décoration à 875 stud que le jeu n'envoie même
pas aux joueurs. **Désactivées, pas supprimées** — réversible d'un clic.

Attention : c'est une modification de la place, elle attend une sauvegarde.

## Pas fait ce tour

La comparaison des quatre M1 maintenant que M1_2 a sa direction, et le second
passage sur les packs pour le dash. En tête de liste.

---

# Les verrous, les M1, et le dash enfin rouvert

## Ta valeur pour Jugement aurait cassé quelque chose

Tu m'avais dit de vérifier la fenêtre d'enchaînement après coup. Bien vu :

```
Jugement   verrou 0,45   fenetre 0 ms   <<< ETROIT
```

Le repère d'impact de ce coup est à 0,47 seconde — **après** le nouveau verrou.
Le joueur se serait déverrouillé **avant que son propre coup ne porte**.

La cause est structurelle : **le contact de ce geste tombe à 83 % de sa durée**.
Il n'existe donc aucune valeur qui donne à la fois zéro temps mort *et* la
fenêtre confortable des coups rapides. Le maximum disponible est 99 ms.

**Retenu : 0,57** — exactement la durée du geste. Zéro temps mort au lieu de
0,73 seconde, et une fenêtre de 99 ms, la même famille que les deux premières
compétences. C'est le meilleur compromis possible, et il est borné par
l'animation elle-même.

Marche du Titan à 0,75 : appliqué tel quel, rien à signaler. **Balayage final :
aucune alerte sur les neuf pièces.**

## Les quatre M1 : la comparaison donne quelque chose de net

```
coup   formes                 direction  couches  flash
M1_1   eclat                  Couloir       0       —
M1_2   anneau                 ArcSol        0       —
M1_3   croissant, poussiere   —             0       —
M1_4   debris, decharge       —             3     0,21
```

**Le quatrième n'est pas en défaut** : il n'a pas d'élément directionnel mais il
a trois couches de sol et un flash, et sa direction *est* le sol.

**Le troisième est le seul en défaut** — rien ne porte le sens du coup.

**Mais je ne le retouche pas.** C'est un uppercut : sa direction est
**verticale**. Or nos deux éléments directionnels ne savent pas la dire — l'un
court à l'horizontale, l'autre est un éventail au sol. Lui coller l'un des deux
serait retoucher pour retoucher.

Le manque est réel et nommé ; **la pièce qui le comblerait n'existe pas encore**.
C'est un chantier, pas un réglage.

## Le dash : le constat est plus dur que prévu

Il produisait, en tout et pour tout : une image rémanente, une secousse de
caméra, et l'animation. **Aucun effet.** Il n'existe même aucune recette pour
lui — zéro occurrence dans tout le fichier.

**C'est la seule pièce du kit qui n'a jamais eu sa passe d'encre.** Ça explique
enfin, et précisément, pourquoi on la tient pour la plus faible depuis le début.

J'y ai mis deux éléments, dans la grammaire du reste : un couloir le long du
vecteur de dash — le dash *est* une direction — et le trait effilé, une ligne de
vitesse qui était déclarée depuis le début et n'avait jamais servi.

## Mais je ne l'ai pas vu marcher

**Le dash ne s'est pas déclenché du tout** sous mon entrée simulée : ni animation
de dash, ni image rémanente — or l'image rémanente est du code qui existait
avant moi. Ce n'est donc pas ma modification qui échoue, **c'est la touche qui
n'arrive pas**.

Le code compile et le module d'effets se résout bien. **Mais l'effet du dash n'a
jamais été vu.** Je le marque comme non vérifié plutôt que de te le donner pour
acquis.

---

# 3 septembre 2026 (suite) — Le dash tirait depuis le début, et la colonne existe

## Je me suis trompé sur le dash, et voici comment je l'ai su

J'avais écrit : « la touche n'arrive pas ». **C'est faux.**

J'ai posé deux écoutes sur le chemin réel — l'entrée clavier côté joueur, et le
message que le dash envoie au serveur. Résultat : **les deux répondent.** Le
dash se déclenchait bel et bien.

Ce que je prenais pour son absence — le personnage qui passe en marche puis en
repos — était en réalité **sa conséquence** : la poussée du dash fait basculer
le personnage en déplacement. **Je lisais la preuve du dash comme sa
réfutation.**

## Ce qui cassait vraiment : ma propre ligne, écrite dans le mauvais ordre

J'avais passé la couleur là où la fonction attendait une longueur. Comparer une
couleur à un nombre ne renvoie pas « faux » : **ça plante**. L'erreur partait
donc juste avant l'animation — d'où l'animation manquante, que j'avais mise sur
le compte du dash entier.

Trouvée **à la relecture**, pas en jeu : l'essai de la veille ne pouvait rien
dire de cette ligne puisqu'il n'avait rien pu observer. Deux pannes empilées,
dont une seule visible.

**Corrigé, et vu tirer :** le dash a maintenant son couloir et son trait effilé.

## La colonne montante — la forme verticale qui manquait

C'est la pièce que j'avais refusé d'improviser hier. Elle existe.

**Ce qui fait qu'elle « monte » n'est pas une impression, c'est mesuré** : six
étages naissent du bas vers le haut, hauteur strictement croissante, **neuf
studs en 0,215 seconde**. Volontairement plus lent que le couloir du direct :
à la vitesse de celui-ci, la montée passerait en cinq images — trop court pour
se lire comme un trajet, ça redeviendrait une barre.

Elle **remplace** la poussière de M1_3 au lieu de s'y ajouter : le coup léger ne
porte que deux éléments, et un troisième aurait été écarté en silence. C'est
exactement la panne qu'on a déjà eue sur le premier M1 il y a deux jours.

## L'image m'a donné tort deux fois — et c'est elle qui a tranché

**Premier tort, la matière.** J'avais réutilisé le grain commun aux deux autres
formes, pour qu'elles soient de la même famille. Empilé à la verticale, ce grain
donne un **panache de fumée lumineuse**. La colonne montait correctement — et
elle montait en fumée, c'est-à-dire exactement la lueur qu'on retire des M1
depuis deux jours. Le grain commun datait d'avant l'encre ; l'encre prime.

**Second tort, l'orientation.** Quatre essais, comparés à l'image à chaque fois.
Les traits restaient couchés en travers. Le troisième essai m'a appris ce que
j'avais supposé à l'envers : **le trait est déjà debout dans sa propre image** —
c'est pour ça que tout ce que je faisais pour le redresser le couchait.

Le quatrième est le bon : des traits **debout, effilés, étroits en bas et
largement ouverts en haut**. Ça dit « qui monte ».

Planche des trois états : `2026-09-03_colonne-trois-etats.png`.

## Une conséquence que je signale sans y toucher

Si le panache venait du grain partagé, alors **le couloir du premier M1 et
l'éventail du deuxième rendent eux aussi de la lueur, pas de l'encre.** C'est la
suite directe de ce que je viens de mesurer.

**Je n'y touche pas.** Le premier M1 est la pièce que tu juges lisible, et la
rendre mate est une décision de direction artistique — la tienne, pas un
réglage.

## Ce qui reste sur la table

La place n'est **pas sauvegardée** et porte la réorganisation des packs, les
renommages, et les 19 scripts désactivés. Un enregistrement est nécessaire.

---

# 3 septembre 2026 (suite 2) — Le grain devient réglable, et tu tranches

## Ce que tu m'as fait remarquer était le vrai sujet

Si le panache venait du grain partagé, alors la bascule des M1 vers l'encre
**n'a pas complètement abouti** : on a changé les textures et gardé le grain
lumineux dessous. C'est exact.

**Le grain est maintenant réglable, en trois états** — et **rien n'a bougé en
jeu** : le défaut reste l'actuel tant que Milan n'a pas choisi. Un défaut qui
changerait en silence serait exactement ce qu'on lui reproche.

Planche : `2026-09-03_grain-partage-trois-etats.png`. Six panneaux, le couloir
du direct et l'arc du crochet, chacun dans les trois états.

**J'ai jeté deux bancs d'essai avant celui-là.** Au sol, le décor — mannequins,
gravats, une colonne en travers — occupait la moitié du cadre : on aurait
comparé le fond autant que le grain. Le banc final est monté à 30 studs
au-dessus de l'arène, sur ciel. Même caméra, même origine, même direction,
mêmes valeurs de recette : **la seule variable est le grain.**

Ce que la planche montre :

* **actuel** — l'arc est une masse blanche brûlée, sans bord lisible ;
* **mat** — même silhouette, plus de halo, mais **ça reste de la fumée** :
  retirer la lumière ne rend pas graphique une texture de nuage ;
* **encre** — bords hérissés, tons francs, coupe nette. C'est le vocabulaire que
  ces deux recettes portent **déjà par ailleurs**.

**Mon avis si Milan le demande : l'encre**, pour la cohérence. Mais le mat est
sur la planche parce que c'est le changement minimal — une seule variable — et
qu'il a le droit de choisir ça. C'est sa direction, pas la mienne.

J'ai aussi passé la barre lumineuse du couloir sous le même interrupteur : la
laisser brillante au milieu d'un effet mat aurait faussé la comparaison sur la
pièce la plus large de la forme.

## Le dash : l'assemblage sur lequel tu m'interrogeais n'existe plus

`Run` + `Forward Dash` a été remplacé le **1er septembre**, et le remplacement
est mesuré :

```
           appui   poussee   ordre appui-puis-poussee
  ancien    0.42      0.26    NON — le corps partait avant l'appui
  actuel    3.13      1.72    OUI
```

**7,5 fois l'appui, 6,6 fois la poussée**, et l'ordre que la spec demande : le
pied frappe le sol *puis* le corps se projette. Ce passage-là avait déjà élargi
la recherche — le dash n'avait jamais cherché ailleurs que dans 19 clips, alors
qu'un autre pack en contient 210.

**Et les deux packs achetés ne peuvent rien pour ce point** : ce sont des packs
d'effets, pas d'animation. Ce qui manquait au dash, c'étaient ses effets — c'est
fait, et vérifié en jeu aujourd'hui.

## Mais en le vérifiant, j'ai trouvé pire

Le fichier qui fait foi pour les identifiants d'animation **portait la version
précédente pour les cinq pièces les plus jouées du kit** — les quatre M1 et le
dash. Le jeu tournait juste ; c'est le document qui avait décroché, en silence.

C'est exactement le genre de dérive que ce fichier existe pour empêcher.

Corrigé **par la mesure** : chaque animation rechargée sur le personnage réel,
durée lue dans le moteur — pas recopiée d'un journal. Recroisement des 48 slots
après correction : **aucune divergence.**

## Deux pièges notés pour ne plus les repayer

* **Lire la conséquence d'un mécanisme comme sa preuve d'absence** — le dash
  d'hier. Ne jamais conclure depuis l'absence d'une trace attendue : aller
  écouter le point de passage obligé et voir s'il passe.
* **Deux pannes empilées n'en montrent qu'une** — un essai qui n'observe rien ne
  disculpe rien.

## Un rouge de longue date, compris

L'analyseur signale une erreur depuis un moment. Vérifié : elle est
antérieure à tout ce que j'ai fait. Ce n'est pas un défaut de combat — mais en
remontant la piste, **le module qui la porte n'est chargé par rien**. Deux
fichiers morts. Je ne les supprime pas de mon propre chef ; c'est consigné comme
tâche séparée avec l'analyse déjà faite.

---

# 3 septembre 2026 — Note de reprise (pause)

## La divergence des identifiants est close — et voilà pourquoi elle comptait

Le fichier qui fait foi pour les identifiants d'animation portait la version
**précédente** pour les cinq pièces les plus jouées du kit — les quatre M1 et le
dash. Corrigé par la mesure, et recroisement complet : **plus aucune
divergence** sur les 48 emplacements.

Ce qu'il faut retenir, parce que c'est le cœur du problème : **un fichier de
vérité qui ne dit pas ce que le code joue rendait l'hallucination possible au
lieu de l'empêcher.** Quiconque aurait « vérifié » un identifiant dedans aurait
validé un ancien, en toute bonne foi. Le jeu tournait, rien ne levait.

Aucun test ne l'a trouvé. C'est le croisement de deux sources qui ne s'étaient
jamais parlé qui l'a trouvé — **et ce croisement mérite d'être outillé**, c'est
vingt lignes.

**Un résidu que je laisse ouvert et écrit** : le dash porte deux identifiants
différents tous deux décrits comme « la version précédente ». Un retour arrière
écrit aujourd'hui restaurerait probablement la mauvaise. À mesurer avant tout
rollback du dash — je ne tranche pas au jugé.

## Un de mes commits mentait, c'est réparé

Un commit annonçait trois choses et n'en portait qu'une. J'avais indexé les
fichiers, puis fait un aller-retour de remisage pour vérifier qu'un avertissement
était bien antérieur à mon travail — le retour restaure les fichiers **non
indexés**, et je ne l'ai pas revérifié avant de valider. Réparé.

## LA PLACE N'EST TOUJOURS PAS SAUVEGARDÉE — ce qui serait perdu

Relevé **dans la place**, pas de mémoire :

1. **La réorganisation des packs** — 42 émetteurs sortis du dossier « archive »
   vers un dossier de production. Sans elle, 37 de nos 40 émetteurs redeviennent
   tributaires d'un dossier dont le nom invite au ménage.
2. **Les deux renommages** de l'astre et des satellites. Ils lèvent une collision
   de noms où le jeu allait chercher un soleil à 1 émetteur au lieu du nôtre à
   10. **Sans eux, l'astre de l'ultime redevient invisible.**
3. **Le transfert de Milan**, rangé de côté pour éviter les doublons.
4. **Les 19 scripts désactivés** — 9 % de temps serveur récupérés.

Le code est committé et à l'abri. **Ces quatre points-là ne vivent que dans le
fichier de place.**

## Fait, mais que Milan n'a jamais vu

* La **scène de l'ultime en cinq temps** — cadrage frontal, sortie de puissance,
  soleil invoqué à la main droite, retour troisième personne, explosion.
* Le **dash qui tire enfin** — c'était la seule pièce du kit sans effets.
* La **colonne verticale** de M1_3, montée mesurée, en encre mate.
* Les **verrous corrigés** — 0,73 seconde de temps mort supprimée sur une
  compétence, sans refermer la fenêtre d'annulation.
* L'**aura de surcharge** et son geste de montée à 100 de momentum.

## Ce qui l'attend comme décision

1. **Encre contre lueur** sur le couloir du direct et l'arc du crochet. La
   planche est publiée, l'interrupteur est livré, **le défaut n'a pas bougé**.
   Mon avis : l'encre. Le mat est là parce que c'est le changement minimal.
2. **Le cadrage trois-quarts** de la scène d'ultime — retenu faute de mieux,
   jamais validé à l'œil.

## État à la pause

Play arrêté, Studio laissé ouvert en édition. Sondes retirées et vérifié des
trois côtés. Rien ne traîne en scène. Arbre de travail propre, tests au vert.

---

# 3 septembre 2026 (reprise) — La place a tenu

## D'abord la bonne nouvelle : rien n'est perdu

Les quatre points qui n'existaient que dans le fichier de place ont **tous
survécu** : les 42 émetteurs rangés en production, les deux renommages de
l'astre et des satellites, le transfert de Milan mis de côté, les 19 scripts
désactivés.

Et le point critique est vérifié : **il ne reste qu'un seul porteur du nom
`Sun`**, et ce n'est pas le nôtre. La collision ne peut plus se produire,
**l'astre de l'ultime reste visible**. Rien à reconstruire.

## La planche encre contre lueur était déjà faite

Elle date du tour précédent, et elle est bien servie (vérifié). **Trois états et
non deux** : j'ai ajouté l'encre à côté de l'actuel et du mat, parce qu'un choix
entre « lueur brûlée » et « fumée grise » n'aurait pas été un vrai choix. Le
défaut en jeu n'a pas bougé — c'est Milan qui tranche.

## Le piège dans le code était pire que je ne le pensais

Le dash portait deux identifiants décrits tous deux comme « la version
précédente ». Mesurés en moteur et datés :

```
  ACTUEL           0.450  marqueur a 0.179   31 aout
  vraie precedente 0.450  marqueur a 0.204   30 aout
  bloc commente    0.433  AUCUN MARQUEUR     30 aout, le matin
```

Le bloc prêt à décommenter portait le troisième — **deux générations en
arrière**. Son étiquette « version précédente » était vraie le matin du 30 août
et fausse le soir même.

**Et le décommenter n'aurait pas seulement rendu une vieille animation.** Cet
identifiant ne porte aucun marqueur, et le bloc n'en déclarait aucun : le
mécanisme de repli ne se serait pas armé, le signal de poussée n'aurait jamais
été émis, et **le dash aurait joué son animation sans déplacer le corps.** Un
dash qui ne dash pas, sans une seule erreur affichée.

Le bloc est retiré, remplacé par le tableau mesuré, avec la bonne valeur de
marqueur (l'ancienne note se trompait de 19 millièmes).

**Une méthode notée au passage** : les trois identifiants ont d'abord répondu
« vide », et j'ai failli conclure qu'ils étaient morts. C'était le
téléchargement qui n'avait pas eu lieu. Notre règle dit qu'une durée réelle
prouve qu'une animation existe — elle ne dit pas qu'une durée nulle prouve le
contraire.

## Le second passage sur le dash

**Les deux packs achetés ne contiennent aucune animation** — compté, pas
supposé : zéro des deux côtés, contre 2073 et 111 émetteurs. Ils ne pouvaient
rien pour le geste, seulement pour les effets, qui sont faits.

**J'ai vérifié en moteur une comparaison qui n'avait été faite que hors ligne**,
et je ne retrouve pas leurs chiffres — ma mesure n'est pas la leur, je ne la
donne donc ni pour une confirmation ni pour un démenti. Mais elle montre autre
chose :

> **Le buste de la version actuelle part en arrière au milieu du geste**, et ce
> recul est plus ample que la projection finale vers l'avant. C'est cohérent
> avec sa source — un saut stylisé — où le recul est l'anticipation. **Reste à
> juger si un dash doit reculer autant avant de partir.** Je n'y touche pas :
> c'est un jugement à l'œil, et Milan ne l'a jamais vu.

**Et la recherche n'a pas couvert tout ce qui dort dans la place** : 46
animations dont le nom évoque un appui-poussée, dont **15 dans le pack de
movesets anime qui n'a jamais été mesuré**. Un vrai balayage demande la chaîne
de notation ; je ne l'ouvre pas sans accord.

## Les trois interruptions — conception seule

Une seule des trois est vraiment neuve. Le roll cancel et la feinte réutilisent
le mécanisme d'annulation qui existe déjà : la feinte, c'est annuler **avant** le
contact là où le dash annule **après**.

Le clash est le gros morceau, et son vrai problème n'est pas de le détecter :
c'est que **les deux joueurs ont déjà vu leur coup toucher** sur leur écran. Je
recommande de ne pas défaire ce contact mais de superposer le clash par-dessus —
moins pur, mais aucune annulation visible, et c'est le seul point qui compte.

Ordre proposé : roll cancel, puis feinte, puis clash.

## Ce que je n'ai pas obtenu

**Aucune photo exploitable du dash**, après trois tentatives. Le déclenchement
programmé est refusé par le bac à sable, et l'aller-retour jusqu'à la capture
dure deux fois plus longtemps que les effets. Le dash reste vérifié **par le
comptage** sur le vrai chemin — c'est une preuve, mais pas une image. Je le dis
plutôt que de fabriquer une capture qui ne montrerait pas ce qu'elle prétend.

---

# 3 septembre 2026 (suite) — Ton hypothèse sur le dash était la bonne

## Les quinze candidats, mesurés

Rapport complet : `2026-09-03_MESURE_dash_15_candidats.md`.

Tout est mesuré **sur le même mannequin**, un clone monté à 40 studs. Les
animations du pack sont posées article par article et **c'est le moteur qui
calcule le squelette** ; la version actuelle est jouée sur le même mannequin et
balayée. Un seul instrument des deux côtés, sinon la comparaison ne vaut rien.

**Un piège évité de justesse** : les articulations sont **inertes sur un
mannequin entièrement figé**. Vérifié avant de mesurer quoi que ce soit — un bras
tourné de 80° se déplaçait de **zéro**. Il faut ne figer que le bassin. Sans
cette vérification, les quinze candidats auraient rendu des chiffres identiques
et parfaitement crédibles, et j'aurais publié un classement de bruit.

## Ton hypothèse tient, et le défaut est anormal

```
                    appui        poussee       recul
ACTUEL (v2)        2.07 a 67%   +0.43 a 100%   -1.29   <- recule 3x plus qu'il n'avance
FrontDash          1.91 a 48%   +0.79 a  39%   +0.39
AirDashForward2    2.00 a  0%   +0.99 a  40%   -0.00
```

**La version actuelle est la seule animation vers l'avant dont le buste recule
de plus d'un stud.** Tous les autres candidats avant tiennent entre −0,22 et
+0,39. Les deux seuls autres reculs marqués du corpus sont le dash **arrière**
(c'est sa fonction) et une animation qui n'est pas un dash.

Donc ce recul n'est pas une figure normale du dash : **c'est la signature de sa
source**, un saut par-dessus un obstacle où le recul est l'anticipation du saut.
Et il est **trois fois plus ample que la projection finale**.

C'est un très bon candidat pour « ce qui rend le dash faible depuis le premier
jour ».

## Mais aucun candidat n'est meilleur sur tout

`FrontDash` corrige exactement les deux défauts — **poussée doublée, aucun
recul**, appui comparable. Mais il échoue sur le critère qui avait fondé tout le
choix précédent : l'ordre appui-puis-poussée.

**Et je dois une réserve sur ma propre mesure** : ce candidat porte 15 poses sur
0,73 s. L'écart qui le condamne fait **moins de deux poses**. Je ne peux pas
affirmer que son ordre est inversé — seulement que je ne peux pas affirmer qu'il
est correct. Le défaut de la version actuelle, lui, fait 1,29 stud et se voit.

## Ce que je recommande, sans l'avoir fait

**Basculer sur `FrontDash`, retimé à 0,45 s.** Ça demande un upload (gratuit pour
les animations), un retime, et surtout le **bake du marqueur** — sans lui, le
dash joue sans déplacer le corps, exactement le piège refermé ce matin. La
version actuelle est conservée comme retour arrière.

**Et un A/B à l'œil.** Ces trois nombres disent que la version actuelle recule ;
ils ne disent pas laquelle des deux *se joue* mieux. C'est Milan qui tranche,
comme pour le grain.

Je ne recommande **pas** `AirDashForward2` malgré ses meilleurs chiffres bruts :
son appui culmine à la toute première image, donc il n'y a pas d'appui *dans* le
clip — et c'est un dash aérien. On a déjà écarté un saut pour cette raison
exacte ; refaire l'erreur en la connaissant serait pire que l'avoir faite.

---

# 3 septembre 2026 — La feinte et la roulade sont construites

## Le dash : tout est prêt, sauf l'upload — et le blocage est net

Fait et vérifié : `FrontDash` **reconstruit** à partir d'instances neuves,
**retimé de 0,733 à 0,450 s**, **marqueur baké** à 0,2148 s — un vrai marqueur,
pas une image nommée, puisqu'on sait maintenant ce que coûte la confusion.
Exporté, 6567 octets.

**L'upload échoue**, et ce ne sont pas nos données : l'outil d'upload embarque
une bibliothèque trop ancienne pour le format que le Studio actuel écrit. Trois
essais l'établissent — nettoyer les étiquettes ne change rien, reconstruire à
neuf non plus.

Une version corrigée de l'outil existe depuis juillet. **Son installation demande
une confirmation que je ne peux pas donner à ta place :**

```bash
rokit add jacktabscode/asphalt
```

Une fois passée, la bascule est à une commande : brancher l'identifiant, garder
l'actuelle en retour arrière, faire l'A/B.

## La feinte — construite, et vérifiée de bout en bout

**J'avais tort dans ma propre conception, et je l'ai vu en lisant le code avant
d'écrire.** J'annonçais un travail serveur comme « le vrai coût » des trois
mécaniques. C'est faux : sur le chemin réellement branché, **le serveur
n'apprend l'attaque qu'au moment de l'impact**. Avant, il ne sait rien. Donc
feinter ne laisse aucune attaque orpheline et **ne coûte rien au serveur**.

Preuve en jeu :

```
feinte acceptee a 234 ms   (sur un coup dont l'impact tombe a 323 ms)
le serveur a recu : M1_1 -> M1_2 -> M1_3 -> M1_4
                                             ^ le clic APRES la feinte
```

Le coup feinté n'a **rien envoyé**, et le clic suivant a **rejoué le même pas de
chaîne** — donc feinter ne fait pas avancer vers le quatrième coup, exactement
comme prévu.

## La roulade — construite et vérifiée

Touche **C**, 22 de stamina payée **avant** tout effet visible, invulnérabilité
**bornée** de 0,05 à 0,25 s — pas sur tout le geste, sinon elle devient la
réponse à tout. Mesuré : 5,56 stud de déplacement, animation jouée.

**Un conflit corrigé avant l'essai** : j'avais proposé Shift. Or Shift maintenu
est **déjà le sprint** — la roulade serait partie à chaque départ en course.
Relevé en relisant les liaisons existantes, pas après.

## Trois réserves, dites plutôt que tues

* **Le roll cancel n'est pas vérifié en jeu.** La fenêtre dure 200 ms ; les
  outils d'entrée simulée ne descendent pas sous 230 ms, et mesurent **6,5
  secondes** entre un appel souris et un appel clavier. Aucun instrument
  disponible ne peut poser un clic et une touche assez près. Ce qui est établi :
  la roulade tire, et elle emprunte **la même ligne d'octroi** que le dash —
  l'ancienne fonction n'est plus qu'un appel à la nouvelle.
* **Le déplacement vaut la moitié du déclaré** (5,56 pour 11). Le dash a la même
  structure et sûrement le même écart : la constante est une cible, pas une
  distance.
* **L'animation de roulade est empruntée** aux clips de dash directionnels. Un
  vrai clip de roulade existe dans les packs, non uploadé — bloqué par la même
  panne. **La mécanique est complète, sa peau ne l'est pas.**

## Le clash — proposé, pas codé

La construction d'aujourd'hui a **corrigé mon esquisse** : la détection ne peut
pas être « deux fenêtres actives qui se croisent », puisque cet état n'existe
pas — le serveur voit deux **impacts**. Et ma fenêtre de 80 ms est trop courte :
deux joueurs à latence normale voient leurs coups arriver à 120 ms d'écart.

La ligne que tu as validée tient : **on ne défait pas un contact qu'un joueur a
vu atterrir**. On superpose. Trois questions te sont posées plutôt que tranchées.

---

# 3 septembre 2026 — Le clash, tranché sur trois points mesurés

Rien n'est codé. Proposition complète : `2026-09-03_PROPOSITION_clash.md`.

## 1. La superposition ne demande aucune ruse

**Le client n'applique jamais de dégâts** — vérifié, zéro occurrence dans tout
le code client. Les dégâts ne sortent que du serveur.

Donc ce que les deux joueurs ont vu, c'est **une animation, un éclat, un
hitstop — jamais des dégâts**. Le clash n'annule pas un contact : il empêche des
dégâts **qui n'avaient pas encore été appliqués**, et ajoute par-dessus le
contact déjà joué.

Séquence perçue : *mon coup part → mon coup touche → ça se bloque.* Jamais :
*mon coup touche → non, en fait, non.*

C'était l'intuition qu'on partageait, et elle se trouve être **gratuite** : il
n'y a rien à défaire parce qu'il n'y avait rien de fait.

Le seul point à surveiller à l'œil : la barre de vie adverse. Elle est poussée
par le serveur, donc elle ne baisse jamais avant le verdict.

## 2. Le clash est autoritaire

Il change l'issue de l'échange, donc c'est le serveur qui décide — dans le même
endroit qui applique déjà les dégâts, juste avant de les appliquer.

**Serveur** : annulation des dégâts, repoussement, entrée en récupération.
**Client** : l'éclat au point de rencontre, le hitstop, la secousse, le son.

Ça ne baisse pas son coût : la part autoritaire est courte, mais c'est elle qui
doit être juste.

## 3. L'horloge — et pourquoi ma fenêtre était fausse

**Le serveur ignore l'horodatage envoyé par le client** — vérifié, il n'est lu
nulle part. Le seul temps utilisé est celui du serveur, pris **à l'arrivée** de
la requête.

Donc la fenêtre ne compare pas des instants de frappe mais des instants
d'arrivée, et **elle doit absorber l'écart de ping entre les deux joueurs, pas
le ping**. Deux joueurs à 30 et 150 ms qui frappent au même instant réel
arrivent à 120 millièmes d'écart : mes 80 les rataient — et pire, le clash
serait devenu **plus difficile pour le joueur mal connecté**. Exactement
l'injustice à éviter.

**Retenu : horloge du serveur, fenêtre à 150 ms.** Non trichable, aucun champ
nouveau.

**Écarté : faire horodater le client.** Ça supprimerait l'écart de ping — mais
c'est une valeur **fournie par le client**, donc falsifiable, et cette mécanique
**supprime des dégâts**. Un client menteur pourrait annuler les coups qu'il
reçoit. Je ne prends pas ce risque.

## 4. Ce que je ne peux pas vérifier — dit avant de construire

**Je ne peux pas simuler deux joueurs qui frappent en même temps.** Le pont
n'adresse qu'un seul client, et les outils d'entrée simulée plafonnent — mesuré
aujourd'hui — à 230 millièmes entre deux gestes.

**Testable d'ici** : la règle de détection et ses cas limites, le rendu, et la
non-régression (un échange normal ne clashe jamais).

**Pas testable d'ici, et c'est le risque principal** : le repoussement arrive
150 à 250 millièmes après le contact perçu, et je ne peux pas juger seule si ça
se lit comme une **conséquence** ou comme une **correction**. Ni le taux de
déclenchement réel, ni le comportement quand les deux pings diffèrent — c'est-à-
dire précisément ce que la fenêtre est censée couvrir.

**Recommandation** : construire détection et rendu, valider ce qui est
validable, et **laisser le réglage de la fenêtre ouvert** jusqu'à un test à deux
joueurs. La sortir en réglage nommé, et compter les quasi-clashs en jeu pour
lire la vraie distribution avant de figer un chiffre.

---

# 3 septembre 2026 — Le clash est construit

## La règle vit à part, et c'est ce qui la rend vérifiable

La logique du clash ne touche à rien de Roblox : elle ne prend que des nombres.
Ce découpage n'est pas cosmétique, c'est **la seule raison** pour laquelle je
peux vérifier les cas limites sans deux joueurs. Les mécaniques précédentes
avaient leur logique noyée dans du code qu'on ne peut lancer qu'en jeu.

**27 assertions, aucun échec.** La suite passe à 11 tests.

## Les cas limites que tu as demandés — tous couverts

```
ultime contre M1 / competence / ultime      traverse
M1 contre competence                        refuse
attaquant mort / cible morte                refuse
un seul des deux a portee                   refuse
deux joueurs frappant un TROISIEME          refuse
les deux bords de la fenetre                dans les deux sens
double declenchement                        refuse, trois variantes
```

**Le double déclenchement m'a fait déplacer du code.** Le drapeau qui empêche un
impact de re-clasher vivait au mauvais endroit : il n'était **pas testable**. Or
une règle qu'on ne peut pas exercer est une intention, pas une règle. Je l'ai
fait entrer dans la règle elle-même et retiré le doublon.

C'est le cas le plus grave de la liste et le moins visible : sans lui, un seul
échange produirait deux clashs, puis trois — **deux joueurs qui échangent
normalement deviendraient invulnérables l'un à l'autre.**

## J'ai cassé le test exprès, trois fois

Un test vert qui ne peut pas virer au rouge ne vaut rien. Trois sabotages, tous
rattrapés.

**Et l'un des trois m'a appris quelque chose** : désactiver l'exclusion de
l'ultime ne produit **qu'un** échec sur trois, pas trois. Les cas mixtes sont
rattrapés ailleurs ; seul **ultime contre ultime** passerait. Le garde-fou ne
sert donc qu'à un seul cas — mais c'est exactement celui que « il traverse »
interdit. C'est écrit dans le fichier pour que personne ne le retire en le
croyant superflu.

## Le rendu — j'ai dû chercher une forme libre

**Aucun effet des packs n'était disponible.** Relevé dans la place : tous les
effets assez fournis des trois packs sont déjà employés par les 44 recettes. En
reprendre un aurait donné au clash l'allure d'un impact déjà vu — le contraire
de ce que tu demandais.

**Ce qui était libre : l'encre angulaire** du pack combat, déclarée depuis la
bascule et **servie nulle part**. C'est la seule forme du vocabulaire qui
n'appartenait à personne, et sa géométrie brisée dit « rencontre » là où l'éclat
dit « contact ».

Trois couches, une colonne qui monte **du point de rencontre** et pas d'un
corps, une secousse forte, un flash plus long et moins fort que celui du
finisseur — un temps suspendu, pas une détonation.

Vérifié en jeu : 62 tirs produisent exactement le compte attendu. Planche :
`2026-09-03_clash-forme-reservee.png`.

## Non-régression

Un échange normal rend « touché », et le compteur de clashs reste à zéro. La
voie des dégâts est intacte.

*La vie du mannequin ne prouvait rien — il est immortel. J'ai donc regardé la
voie **empruntée**, pas son effet.*

## Ce qui reste ouvert, délibérément

**150 millièmes n'est pas figé** : c'est un réglage nommé, avec le raisonnement
à côté et un compteur qui donnera la distribution réelle des écarts en jeu. On
lira les chiffres avant de trancher.

**Et le risque principal reste entier** : le repoussement arrive un sixième de
seconde après le contact perçu, et je ne peux pas juger seule si ça se lit comme
une conséquence ou comme une correction. Il faut deux vraies connexions.

---

# 3 septembre 2026 — L'inventaire des formes. Rien touché.

Rapport complet : `2026-09-03_INVENTAIRE_formes_vfx.md`. L'outil est dans le
dépôt et se relance quand on veut.

## La plainte de Milan est exacte, et voici le chiffre

```
45 recettes
26 portent la gerbe radiale generique
19 ne portent AUCUNE forme propre
 6 en portent une
```

« Aucune forme propre » veut dire : rien d'autre que la gerbe, la traînée sur le
bras, les lignes de vitesse et l'image rémanente. **Ces quatre-là sont
indifférents au geste** — ils produisent la même chose pour un direct, un
balayage ou une chute.

Dix-neuf pièces sur quarante-cinq ne portent que ça. C'est **littéralement** « la
même gerbe à trois intensités ».

Et le classement est un renversement parfait : les effets indifférents occupent
tout le haut du tableau, ceux qui portent une forme occupent le bas. **L'effet
qui dit « un direct » n'est employé que par une seule pièce.**

## Ce qu'on possède sans le servir

* **une seule forme d'encre est libre** — celle qui dit « retombée », qui vient
  d'être libérée ce matin quand la colonne a pris sa place sur le troisième M1 ;
* **220 effets de packs sur 312 ne sont employés par aucune recette.**

Sur les 220, je pose ma propre réserve : une bonne part appartient à des
**movesets complets** achetés comme des kits — les compter comme « disponibles »
serait exagéré. Mais des familles entières (flammes, brume, foudre, eau : 24
effets) sont là et notre kit n'en tire rien.

## Mon outil a failli publier un faux mort

Première version : il annonçait libre une forme que **le dash emploie déjà**,
parce que je ne balayais que les recettes et que le dash l'appelle directement.

**Un inventaire qui libère une forme déjà prise est pire qu'un inventaire
absent** : il invite à la réutiliser ailleurs et à voler sa signature à une
pièce. Corrigé, et la cause est écrite dans le fichier.

## Le vrai résultat : ce qui MANQUE

Nos formes couvrent quatre directions, dont une sert de fourre-tout :
l'horizontale (le direct), l'éventail au sol (le crochet), la verticale montante
(l'uppercut), et le radial — qui sert **par défaut à tout le reste**.

Ce qu'on n'a pas, et que le kit réclame :

1. **La convergence** — rien ne se contracte vers un point. Une saisie, une
   aspiration, une charge n'ont aucun vocabulaire.
2. **La chute** — rien ne descend. **L'ultime EST une chute, et il joue une
   forme radiale parce que c'est tout ce qu'on a.**
3. **Le balayage en l'air** — celui qu'on a rase le sol par construction. Un
   revers à hauteur de poitrine n'a pas de forme.
4. **Le résidu** — la forme libre dit exactement ça, et les neuf pièces qui
   cassent le sol n'ont rien qui retombe.

## Ce que je propose, sans l'avoir fait

**(a) Redistribuer ce qu'on a déjà.** Dix-neuf recettes sans forme, quatre
formes sous-employées. Aucune primitive nouvelle — seulement ce que chaque
recette déclare. Le plus rentable et le plus sûr.

**(b) Rendre la forme « retombée »** aux pièces qui cassent le sol.

**(c) Construire la chute.** C'est la colonne avec l'axe inversé et la
propagation retournée. La colonne a coûté un après-midi ; celle-ci coûtera
moins, le mécanisme est connu. Et c'est l'ultime qui en a besoin.

**Je ne propose pas de piocher dans les 220 effets inemployés.** La leçon du
grain vaut ici aussi : ajouter des couches de pack ne crée pas de la différence,
ça crée du bruit. La différence vient de la géométrie, et la géométrie est à
nous.

---

# 3 septembre 2026 — Vague 1 : la forme déduite du geste

## D'abord, j'ai corrigé mon propre inventaire

Les « 19 recettes sans forme » comptaient des recettes **mortes** et des
**événements sans geste**. Vérifié avant de toucher quoi que ce soit :

* les quatre compétences **délèguent à un module**, et le routeur retourne avant
  d'atteindre ses propres entrées — celles-ci pointent les **anciennes**
  recettes et ne peuvent jamais tirer. C'est le même défaut que les M1 avaient
  avant leur correction du 30 août ;
* « mort », « KO », « compteur de combo », « confirmation de coup » sont des
  **événements**, pas des gestes. Ils n'ont aucune trajectoire, donc aucune
  forme ne peut en être déduite. Ils gardent la gerbe, et c'est juste.

**Cible réelle : quatre pièces vivantes, pas dix-neuf.**

## Trois métriques, deux jetées — les témoins ont tranché

Les quatre M1 servent de **témoins** : on sait ce qu'ils sont. Une mesure qui ne
les reclasse pas correctement est fausse.

1. **Position du membre** → « latéral 1,5 » pour les cinq pièces. Ce n'était pas
   le geste, **c'était l'épaule**.
2. **Écart à la pose de repos** → le direct sortait « latéral et haut ». Ce
   n'était pas le coup, **c'était la garde** : au repos les bras pendent, donc
   tout coup part déjà haut.
3. **Déplacement pondéré par la vitesse** → retenue. Le direct donne +0,97 vers
   l'avant, le finisseur −0,98 (il descend), et la première compétence +0,82
   latéral pour ce que son propre commentaire appelle « une frappe horizontale
   ample ». **Quatre corroborations indépendantes.**

C'est le piège que j'avais écrit au registre le matin même, rencontré deux fois
en une heure : **un instrument qui répond n'est pas un instrument qui répond à
la bonne question.**

## Ce que j'ai appliqué — et pourquoi pas plus

| pièce | mesure | action |
|---|---|---|
| Frappe Céleste | +0,97 vers l'avant | la gerbe **remplacée** par le couloir |
| Marche du Titan | +0,83 vers l'avant | couloir + la retombée |
| Ultime | la pointe **descend** | la retombée seule |
| Main du Colosse | +0,82 latéral | **inchangée** — plafond plein, forme déjà juste |
| Jugement | **−0,93 : elle recule** | **inchangée** — aucune forme ne dit « qui recule » |

Le plafond de lisibilité est la vraie contrainte, et il est serré : deux des
quatre pièces étaient **pleines**. Le couloir **remplace** la gerbe au lieu de
s'y ajouter, exactement comme sur le premier M1 il y a deux jours.

Vérifié en jeu : les comptes correspondent exactement à la géométrie attendue.

## La mesure contredit une de mes propres décisions

Le troisième M1 porte la **colonne** depuis ce matin. Je la lui avais attribuée
sur l'**intention** — « c'est un uppercut, sa direction est verticale ».

**La mesure dit +0,92 vers l'avant et seulement +0,16 vers le haut.** Son poing
voyage majoritairement en avant. Si la règle « la forme se déduit du geste »
vaut, la colonne n'y est pas justifiée.

**Je ne la retire pas de moi-même** : la pièce vient d'être livrée et Milan ne
l'a jamais vue, l'animation pourrait être ré-autorée pour monter vraiment, et
défaire une décision d'hier sur la foi d'une métrique qui a échoué deux fois le
matin même mérite un avis.

Deux issues, à trancher : rendre le couloir au troisième M1 et garder la colonne
libre pour une pièce qui monte réellement, **ou** ré-autorer l'animation pour
qu'elle fasse ce que son nom promet.

## Le registre des manques s'allonge d'une entrée

Chute, convergence, balayage aérien — et maintenant **le recul**, la forme d'un
geste qui part en arrière, que la contre-attaque réclame.

---

# 3 septembre 2026 — Exploration des packs : la matière, avec son prix

Rapport complet : `2026-09-03_EXPLORATION_packs_matiere.md`. Aucune recette
modifiée.

## Le coût d'abord — parce qu'il change les conclusions

**Je me suis trompée il y a une heure** : j'ai dit que le plafond comptait « les
atomes + la caméra + le flash ». Il compte **aussi les couches de pack**. Ça
change tout le calcul :

```
ajouter une forme au registre de textures    plafond 0   emetteurs 0
la servir dans une recette                   plafond 1   emetteurs 1
REPEINDRE une forme existante                plafond 0   emetteurs 0
prendre une couche de pack entiere           plafond 1   emetteurs 2 a 40
```

**Repeindre est gratuit sur les deux axes.** C'est le résultat principal de
l'exploration, et il sort de la mécanique, pas d'une préférence. Un couloir en
flamme reste un couloir, et il ne coûte **rien de plus** qu'un couloir.

## Un chiffre inquiétant que je refuse de valider

En recomptant couches comprises, **huit recettes du Demi-Dieu sur onze dépassent
leur plafond** — la première compétence déclare huit éléments pour un plafond de
quatre.

**Mais j'ai activé l'audit et tiré cette compétence : il n'a signalé aucun
écartement.** Le tableau est donc dérivé du code et **non confirmé en
exécution**. Je le rapporte comme suspicion, pas comme fait, et **je ne bâtis
rien dessus** avant de l'établir.

## Un outil qui ment, et c'est confirmé

L'audit a crié en gros : *« ATOME MUET — l'éventail au sol a été joué et n'a
produit aucun objet. »*

**C'est faux.** J'ai compté indépendamment sur la même diffusion : **onze objets
créés.** Nos trois formes directionnelles posent leurs éléments **en différé**,
et le détecteur ne compte que ce qui apparaît pendant l'appel. Il est donc
aveugle **précisément aux trois formes qu'on vient de répartir dans le kit**.

Quelqu'un qui suit cette alerte cherche un bug qui n'existe pas. C'est au
registre.

## Le gisement : 61 textures, en pièces détachées

**Il n'est pas dans les gros assemblages** — feu au sol (12 émetteurs), nuage
(12), impact d'eau (8). Ceux-là sont des *compositions*, pas de la matière ; les
prendre entiers coûte une place **et** douze émetteurs pour un geste qui n'est
pas le nôtre.

**Il est dans les vingt-deux porteurs à un seul émetteur** — flamme, brume,
brume qui monte, brume en volute, foudre, trait de foudre, pluie, flamme
dirigée, eau, fumée noire stylisée. Une bibliothèque de textures déjà triée par
ce qu'elle représente, **et la plupart déjà peu lumineuses** — donc proches de
l'encre, sans le halo qu'on passe des semaines à retirer.

**Deux choses qui ne se voyaient qu'en allant regarder :**

* le trait effilé qu'on emploie déjà pour le dash **vient d'un pack d'eau**. On
  puisait dans ces familles sans le savoir ;
* **un identifiant du pack est malformé** (une apostrophe en trop). Il ne peut
  pas charger. Ce n'est pas notre faute et ça ne nous affecte pas — noté pour ne
  pas le recopier.

## Ce que je n'ai pas fait, et pourquoi

**Je n'ai regardé aucune de ces textures à l'image.** Les noms et la luminosité
sont mesurés ; ce qu'elles *montrent* ne l'est pas. Avant d'en servir une, il
faudra la voir et mesurer son découpage — Roblox ne signale rien si le découpage
est faux, les images sont simplement coupées de travers.

**Et je n'ai pas ouvert la piste gratuite.** Elle touche le grain de trois
formes d'un coup, et **Milan n'a pas encore jugé la planche des trois grains qui
l'attend depuis ce matin**. Ouvrir un second axe sur la même fonction avant
qu'il ait tranché le premier rendrait son jugement impossible.

---

# 3 septembre 2026 — Le catalogue, rangé par ce à quoi ça sert

Rapport : `2026-09-03_CATALOGUE_par_fonction.md`. Il **remplace** mon rangement
par famille d'élément d'il y a une heure. Aucune recette modifiée.

## La correction de Milan change l'outil, pas seulement l'étagère

« Flammes / brume / foudre » est un rangement de **vendeur**. La bonne question
est **à quoi sert l'émetteur** — et il se trouve que **c'est mesurable** :
vitesse, traînée, gravité, durée de vie, ouverture, croissance, alignement sur
le déplacement. Ces propriétés disent ce que l'effet fait **voir**, quelle que
soit sa couleur et quel que soit son pack.

Balayage sur **4 800 émetteurs, dix packs, sans frontière de pack.**

## Un piège dès le premier tri

Mon classement remontait des vitesses à 11 000, des tailles à 999, des durées de
50 secondes, des luminosités négatives. **Ce ne sont pas des candidats** : ce
sont des effets réglés pour la scène de démo de leur propre pack, où la taille
du support fait tout le travail.

**Classer sans borner remonte le plus bruyant, pas le plus utilisable.** Une fois
borné à notre échelle : **2 088 sur 4 800 sont exploitables — 44 %.** Plus de la
moitié de ce qui a été acheté est hors d'échelle pour nous. Ce n'est pas un
défaut des packs, c'est qu'ils sont faits pour autre chose.

## Les sept fonctions

```
ce qui dit le DEPLACEMENT D'AIR      240 candidats
ce qui dit la MASSE / le POIDS       163
ce qui dit le RESIDU qui retombe      56
ce qui dit l'INSTANT du contact       10
ce qui dit la TRAJECTOIRE            339
ce qui dit l'ONDE qui s'ouvre         75
matiere MATE (filtre transversal)    758
```

**Deux résultats que le rangement par élément cachait :**

* **L'instant du contact n'a que dix candidats sur deux mille** — et c'est
  précisément la fonction où **nous sommes déjà riches**. Sans cette grille, on
  serait allés piocher là par réflexe, pour remplacer ce qu'on a de mieux.
* **758 effets sont exactement sans lumière**, soit un tiers de ce qui est
  utilisable. En rangeant par élément j'écrivais « la plupart sous 0,40 » ; le
  vrai chiffre est bien meilleur que ça.

## Les pistes, avec leur prix

Les meilleures sont **mates** et sur de **petits supports** :

* **le déplacement d'air** → un effet dont le support ne contient **qu'un seul
  émetteur**. Le prendre entier ou seul revient au même : c'est le moins cher du
  catalogue ;
* **le résidu qui retombe** → deux candidats mats, sur des supports de cinq et
  six émetteurs, avec une gravité et une durée mesurées. **Nos neuf pièces qui
  cassent le sol n'ont rien qui retombe** — ce sont les deux meilleures pistes
  concrètes ;
* **la trajectoire** → un effet mat qui se comporte comme notre trait de dash,
  en plus long et plus lent. La meilleure matière pour une forme qui voyage.

## Ce que ça change pour nos formes

```
peindre le couloir (le direct)     -> deplacement d'air
peindre l'arc au sol (le balayage) -> deplacement d'air + residu
peindre la colonne (l'uppercut)    -> deplacement d'air, axe vertical
donner du residu aux 9 pieces      -> les deux candidats mats
construire la chute (l'ultime)     -> masse + residu
```

**Aucune de ces pistes ne remplace une forme par un effet acheté.** Un couloir
peint reste un couloir : mêmes stations, même propagation, même géométrie. Seule
la matière change — **et repeindre ne coûte aucun émetteur de plus.**

## Une collision de noms m'a piégée pendant la mesure

J'ai demandé un effet nommé « Hit » : il en existe au moins deux dans deux packs
différents, et la recherche a rendu le mauvais. **Le résolveur rend le premier
trouvé** — le même défaut que pour le soleil et le vent, rencontré une troisième
fois. Ici ça n'a coûté qu'une ligne fausse dans un tableau, que je corrige en la
signalant. En production, ça coûte un effet qui n'est pas celui qu'on croit.

## Ce que je n'ai toujours pas fait

**Je n'ai regardé aucune texture à l'image.** Tout est mesuré sur le
**comportement** — ce que l'effet *fait*, pas ce qu'il *montre*. Les deux se
recoupent souvent et les fonctions tiennent sur cette base, mais avant d'en
servir un seul il faudra le voir et mesurer son découpage.

**Et la piste gratuite reste fermée** tant que Milan n'a pas jugé la planche des
trois grains.

---

# 3 septembre 2026 — Point d'arrêt

## Le chiffre que tu as relayé à Milan est juste

Tu me demandais si l'aveuglement du détecteur avait faussé l'inventaire.
**Non.** Et j'ai vérifié avant de répondre, plutôt que de corriger par
précaution.

L'inventaire **ne lit que des fichiers source**. Il ne tourne pas en jeu, ne
consulte aucune donnée d'exécution, et n'utilise pas le détecteur en cause. Il
compte ce que les recettes **déclarent**. Le détecteur d'atome muet, lui, est un
outil d'exécution servant au diagnostic. **Deux instruments différents, une
seule panne.**

Contre-vérifié par une seconde méthode complètement indépendante : concordance
exacte sur les dix effets. **« L'arc au sol : 2 emplois » était juste et reste
juste. Rien à corriger auprès de Milan.**

## Mais les chiffres ont bougé — par le travail, pas par une erreur

```
                publie    aujourd'hui
la gerbe          26          24
le couloir         1           3
l'encre            7           9
l'arc au sol       2           2
```

**La redistribution a déjà déplacé le chiffre principal dans le bon sens.** Le
couloir — l'effet employé par une seule pièce quand j'ai publié l'inventaire —
en sert trois. C'est petit, et c'est mesuré.

**Une réserve qui reste vraie, sans rapport avec le détecteur** : « déclaré »
n'est pas « joué ». Le plafond peut écarter à l'exécution ce qu'une recette
déclare. Le comptage par les sources est donc une **borne haute**. C'est une
autre mesure, à faire.

## Je ne peux pas sauvegarder la place

Deux voies essayées, les deux refusées par le bac à sable. Le bouton
d'enregistrement vit dans une partie de Studio qu'aucun script n'atteint.
**C'est un `Ctrl+S` de Milan**, et voici ce qui disparaît sans lui :

* les deux renommages — **sans eux, l'astre de l'ultime redevient invisible** ;
* les 42 effets sortis du dossier « archive » ;
* le transfert de Milan, rangé ;
* les 19 scripts désactivés (9 % de temps serveur).

## Un nettoyage, et ce qu'il a révélé

Un attribut de déclenchement était resté posé depuis la tentative d'upload. Le
plugin le relisait **à chaque chargement** et retentait l'export, qui échouait —
c'est l'erreur qu'on voyait passer à chaque session sans l'expliquer. Retiré.

**Il avait accumulé une centaine de copies de la même animation** dans le
dossier de travail. Je les signale et **je ne les supprime pas** : c'est un
dossier de travail, supprimer cent instances en fin de session sans accord n'est
pas une décision à prendre seule, et la place n'est de toute façon pas
sauvegardée. Le retrait de l'attribut **arrête l'accumulation**.

---

# 4 septembre 2026 — Les textures ouvertes : deux candidats sur six tombent

## D'abord : la place a bien été sauvegardée

Les six témoins ont survécu à la fermeture — les deux renommages (10 et 5
émetteurs), un seul porteur `Sun` donc **pas de collision, l'astre reste
visible**, les 42 effets rangés, le transfert, les 19 scripts désactivés. Et le
dash retimé attend toujours dans son dossier de travail : ce travail-là n'est
pas à refaire.

**L'upload reste bloqué** — la commande n'est pas passée, l'outil est toujours en
2.0.0. Donc la livraison d'animations n'avance pas ce tour, et je suis passée à
l'étape suivante.

## Ce que voir a corrigé

J'avais écrit moi-même le trou : *« tout est mesuré sur ce que l'émetteur fait,
rien sur ce qu'il montre »*. Il vient de coûter **deux candidats sur six**, dont
le premier de la liste.

**Mon meilleur candidat pour peindre le couloir du direct** — comportement
mesuré : cône étroit, part vite, freine, donc « déplacement d'air ». **Ce que
l'image montre : une étoile à quatre branches avec frange arc-en-ciel. Un reflet
d'objectif.** Le comportement dit « souffle », l'image dit « éclat ». Écarté.

**Le meilleur comportement du catalogue pour une forme qui voyage** — des
griffures **noires**. Et là il y a un piège plus général : la teinte d'un
émetteur **multiplie** sa texture. Une texture noire teintée en blanc **reste
noire**. Toute texture sombre est donc inutilisable dans notre vocabulaire
d'encre blanche, quel que soit son comportement. C'est au registre.

Les quatre autres tiennent, et on connaît maintenant leur découpage.

## La détection automatique de découpage ne marche pas

Trois méthodes essayées, avec la vérité établie **en regardant** pour arbitrer.
Toutes les trois se trompent au moins une fois.

La première suppose que les images se touchent bord à bord — or dans l'une
d'elles chaque motif flotte au milieu de sa case, **la couture passe dans le
vide et ne saute pas**.

Et aucune ne peut réussir sur un anneau : **un anneau centré *est*
géométriquement quatre quarts d'arc identiques.** Ce n'est pas un défaut de
méthode, c'est une ambiguïté réelle.

**Conclusion : ça se lit à l'œil.** Je m'arrête plutôt que de construire un
quatrième détecteur, et c'est écrit pour que personne ne recommence.

## Rien n'a été servi dans une recette

L'étape était d'ouvrir **avant** de servir. Elle vient de payer.

---

# 4 septembre 2026 — L'arbitrage appliqué, et la chute construite

## Ta question : combien de M1 portent le couloir ? **Deux sur quatre**

Le premier et le troisième. Le deuxième garde son éventail au sol, le quatrième
n'a pas d'atome de direction — le sol *est* sa direction. **On n'a donc pas
remplacé « tout est la gerbe » par « tout est le couloir ».**

## Mais ton hypothèse de fond est juste

Les quatre trajectoires, mesurées sur le même instrument :

```
M1_1   avant +0.97   lateral +0.07   haut -0.23    -> AVANT
M1_2   avant +0.85   lateral +0.52   haut -0.07    -> AVANT
M1_3   avant +0.92   lateral +0.35   haut +0.20    -> AVANT
M1_4   avant +0.06   lateral +0.19   haut -0.98    -> BAS
```

**Trois des quatre coups de la chaîne vont droit devant.** Seul le quatrième
fait autre chose : il descend.

**Le vocabulaire des effets est désormais plus différencié que les gestes ne le
sont.** Le problème est remonté d'un cran : il n'est plus dans les VFX, il est
dans **l'animation**. C'est exactement le chantier des variantes directionnelles
qui attend.

## Servi — et seulement où c'était justifié

**Les rochers** (quatre rochers peints, découpage 2×2 lu à l'œil) vont au
quatrième M1 : le seul qui descend, qui casse trois couches de décor, et qui
**n'avait rien qui retombe**.

**Le bloc cerné** devient la matière de la chute. C'est la seule fonction du
catalogue où nous n'avions **aucun candidat mat** — les 163 effets qui disent le
poids sont tous lumineux.

**Les deux autres ne sont pas servis** : ils font doublon avec ce qu'on a déjà.
Deux places vides valent mieux que deux doublons.

## La chute existe

Ce n'est pas la colonne à l'envers. Elle **se resserre** en tombant au lieu de
s'ouvrir — une masse se concentre vers son point d'impact quand une colonne
s'évase — et elle **s'aplatit à l'arrivée**, sans quoi elle traverserait le sol.

Mesuré : neuf étages, hauteur strictement décroissante, **14 studs en 0,209
seconde** — plus vite que la colonne, parce qu'une masse qui tombe accélère.

## Et elle a failli tuer le cratère

Compte avant / après sur la même diffusion :

```
avant : ... EclatTerrain=24 ...
apres : ...                 ... ChuteFX=9
             ^^^^^^^^^^^^^^^ les 24 eclats du cratere, DISPARUS
```

**Le plafond de lisibilité tronque réellement**, et il choisit ce qu'il jette.
Une heure plus tôt j'avais *retiré* cette suspicion parce que « tout tirait » —
mais mon compteur ne regardait qu'un seul endroit, et trois des huit éléments
naissent ailleurs : l'aura sur le personnage, le flash dans l'interface, la
secousse sur la caméra.

**Deux erreurs successives, la seconde commise en corrigeant la première avec un
instrument partiel.** C'est au registre, avec le garde-fou : compter avant *et*
après chaque ajout, et énumérer où chaque élément est censé naître avant de
conclure quoi que ce soit.

Corrigé en relevant le plafond de cette pièce d'un cran — la limite forcée était
antérieure à la chute et ne l'avait pas prévue. **Revérifié : le cratère est
revenu et la chute est là.**

---

# 4 septembre 2026 — Diagnostic de l'ultime, avant la référence

**Aucune mise en scène touchée.** La référence de Milan n'est pas arrivée ; ceci
prépare la comparaison, ça n'y répond pas.

## Le résultat qui change la discussion : l'astre n'est pas trop petit

Calcul avec les valeurs réelles de la scène et le champ de vision mesuré :

```
a l'apogee    l'astre occupe  96 % de la hauteur d'ecran
a la main     il occupe      167 %  —  il DEBORDE du cadre
```

**Donc « pas spectaculaire » n'est pas un problème de taille.** Et ça écarte la
piste que **je** défendais moi-même il y a deux jours — « si Milan le trouve
maigre, j'agrandirais l'astre ». À ne pas rouvrir.

**L'hypothèse qui reste : il est immense et creux.** Sa taille annoncée est la
*portée des particules*, pas un disque plein — et au pic on compte **trente
émetteurs** pour toute la scène. Trente émetteurs étalés sur cette largeur, on
voit à travers. Un soleil de référence est **dense**.

**Quand l'exemple arrivera, ce n'est donc pas la taille qu'il faudra comparer,
c'est la densité.**

## Le précaire : la fin n'est pilotée par personne

La montée fait **deux dixièmes de seconde** — il y a bien une rampe, ce n'est pas
un interrupteur. Mais elle est courte, et surtout **la descente se fait en
marches** : chaque palier correspond à une durée de vie qui expire de son côté.

**Personne ne dirige la fin de l'effet.** Une chose qui s'éteint par épuisement
se lit comme une chose qui s'arrête, pas comme une chose qui retombe. C'est très
probablement une bonne part du « précaire ».

## Le pas-cinéma : 1,3 seconde sans rien

Le dernier temps déclaré de la scène est à **3,20 s**. L'animation de Milan fait
**4,50 s**. Entre les deux : **ni caméra, ni effet, ni son.** Le geste continue à
l'écran pendant que la réalisation a lâché.

## Et une réserve levée, qui contraint la réponse

J'avais dit « mon arithmétique de plafond est fausse ». Vérifié : **le plafond
tronque bel et bien**, et l'ultime est maintenant **à 6 pour un plafond de 6**.
La marge est nulle.

**Donc la réponse au grief ne pourra pas être « empiler davantage »** sans une
décision explicite sur ce nombre. Elle passera plutôt par la **densité** et par
une **fin dirigée** — qui ne coûtent aucune place.

## Ce que je n'ai pas mesuré, et que je ne devine pas

* **le rapport ultime / M1** : l'échantillonneur a capté l'ultime et raté le M1
  trois fois de suite, sans que je comprenne pourquoi. Je préfère ne rien
  publier plutôt qu'un rapport faux ;
* **la fin de la traîne** : ma fenêtre s'est fermée alors qu'il restait encore
  des effets vivants. Ce qui est sûr : environ **trois secondes** de traîne, là
  où la référence du genre en garde quatre à huit.

## Deux erreurs de méthode, toutes deux des récidives

J'ai lu un appel protégé réussi comme « l'ultime a été lancé » — alors que la
fonction rendait « momentum pas prêt » et que **je ne lisais pas sa valeur de
retour**. C'est le piège documenté depuis des mois sur les animations, appliqué
à autre chose donc non reconnu.

Puis, en voulant contourner, j'ai chargé le module depuis mon bac à sable : il
répondait toujours « pas prêt » alors que l'écran affichait le maximum. **Mon
bac à sable a son propre cache** — je mesurais un fantôme. La bonne voie était
la vraie touche, et elle a marché du premier coup.

---

# 4 septembre 2026 — La référence Escanor : le monde répond enfin

## Elle explique ma propre mesure

J'avais trouvé que l'astre occupe **96 % de la hauteur d'écran** et conclu « ce
n'est pas un problème de taille ». La référence dit pourquoi : chez Escanor le
soleil occupe **moins** de cadre que le nôtre — et **il a repeint le monde
entier**.

**Notre astre est un objet lumineux posé dans un monde éclairé normalement. Le
leur est une source qui réclaire tout.** C'est ça, « précaire ».

## Le monde change de lumière — fait, et vérifié

J'ai cherché l'existant d'abord, et il y en avait : le décor pose déjà une
atmosphère, un halo, des rayons de soleil et une correction couleur. **Le
nouveau module n'en crée aucun** — il les retrouve et les pilote. Et il ne
touche pas à l'autre correction couleur, qui appartient à un module qui prévient
lui-même de ne pas y toucher.

**Il restaure ce qu'il a lu**, pas des valeurs écrites en dur : si quelqu'un
change l'éclairage de base demain, la restauration suit.

Vérifié en aller-retour complet — l'état d'après est identique à l'état d'avant.
Planche : `2026-09-04_monde-repeint.png`. Le ciel vire, le lointain se perd dans
la brume, **et le personnage lui-même est doré**.

Et une scène interrompue rend aussi la lumière : sinon le monde resterait orange
pour toujours.

## La contre-plongée : codée, pas encore vue

Le cadrage gagne un angle vertical — la caméra descend **et** son point de visée
monte, sinon elle regarderait les pieds. Déclarée à −18° sur l'ultime. **Je n'ai
pas rejoué la scène de bout en bout ce tour, donc je ne l'ai pas vue.**

## Les braises : présentes, et fausses

Attachées à la **caméra** et non au personnage — la référence montre des points
dans tout le cadre, une aura de corps laisserait le reste vide dès qu'on regarde
ailleurs.

Premier essai : l'émetteur existait et **ne se voyait pas**. Corrigé en densité
et en taille. Second essai : **elles se voient, et elles sont sombres.** Des
points de suie, pas des braises.

**Cause : j'ai réemployé une texture sans l'ouvrir.** Elle est sombre, et la
teinte d'un émetteur **multiplie** — une texture sombre teintée en orange reste
sombre. C'est le piège que j'ai écrit au registre avant-hier, refait deux jours
plus tard.

**Non résolu, et je ne devine pas la remplaçante** : en choisir une sans
l'ouvrir serait refaire l'erreur une troisième fois. La mécanique est bonne, la
matière est à trouver. La texture est enregistrée comme **en échec**, avec la
raison.

---

# 4 septembre 2026 — « Colère du Soleil », et deux erreurs que j'avais commises

## Compter d'abord a payé

Tu m'as dit de compter avant de régler. Le comptage a **écarté les deux causes
probables** :

```
socle a 14 stud DEVANT la camera, au centre    -> pas hors champ
dans le cadre : oui                            -> pas cache
~217 particules en regime                      -> pas une question de densite
```

Il ne restait que la couleur. **Sans ce comptage j'aurais densifié un émetteur
déjà dense.**

## Et j'ai trouvé deux erreurs à moi, de la même cause

**J'avais lu ma propre planche de textures à l'envers.** La caméra regarde vers
l'avant, donc son axe droit est inversé par rapport aux coordonnées : l'ordre à
l'écran est **l'inverse** de l'ordre où j'avais posé les panneaux. Cette fois
j'ai fait dire l'ordre **par le moteur** avant de regarder.

Deux conséquences :

* **la « masse » que je sers depuis hier est un reflet d'objectif** — une étoile
  à quatre branches — et non le bloc cerné que j'avais décrit ;
* **et l'effet que j'avais écarté hier en le croyant un reflet est justement le
  bloc cerné.** J'avais rejeté la bonne matière et servi la mauvaise.

Les deux sont corrigées, et ma note d'hier est corrigée avec.

## Les braises : couleur réglée, distribution encore imparfaite

L'ancienne texture était sombre — réemployée **sans être ouverte**. Remplacée
par un fichier du moteur, **ouvert avant emploi** : chaudes et visibles.

Puis un second défaut est apparu : elles faisaient une **colonne au centre**,
parce qu'elles naissaient d'un point. Corrigé en les faisant naître dans un
volume.

**Mieux, et pas encore l'air chargé de la référence.** Je m'arrête là plutôt que
d'augmenter des nombres à l'aveugle.

## Le carton-titre existait déjà

Rien à construire — bandeaux, titre et fondu étaient là. Deux changements : le
nom de Milan, **« COLÈRE DU SOLEIL »**, et surtout la **tenue** : le titre vivait
les 4,5 secondes de la scène ; il paraît maintenant deux dixièmes après la
bascule et se retire après 1,7 seconde. C'est la fenêtre que donnent **deux
sources indépendantes**.

## Ce que je n'ai pas fait

**La contre-plongée n'a pas été vue** — codée et poussée, mais je n'ai pas
rejoué la scène entière. **La chute n'est pas servie à l'apogée**, seulement à
l'impact.

**Et la planche comparative est impossible en l'état : je n'ai jamais reçu
l'image d'Escanor.** Elle m'a été décrite, pas transmise. Je peux produire notre
côté sur les axes nommés — pour mettre les deux côte à côte, **il me faut le
fichier**.

---

# 2026-09-04 (suite) — la cause arrivait après son effet

## La plus grosse trouvaille : une seconde d'écart entre le soleil et le cratère

Les deux `task.delay` qui font tomber puis éclater l'astre sont **imbriqués**
dans celui de l'invocation, et gardaient des constantes de temps **absolues**.
Ils tombaient donc à 0,95 + 2,25 = 3,20 s et 0,95 + 2,60 = 3,55 s, pendant que
les dégâts partaient, eux, à 2,60 s.

Naissances d'instances datées depuis le début de la scène, avant correction :

```
+2,62 s   le sol se casse — 24 éclats, la fracture, la poussière
+3,20 s   l'astre COMMENCE seulement à tomber
+3,55 s   il éclate
```

**Le sol se cassait une seconde avant que le soleil ne l'atteigne.** À l'œil on
voit une explosion et un cratère, et le cerveau les associe : personne ne
l'aurait vu en regardant. Il fallait dater les naissances.

Le détail qui rend la panne exemplaire : **les tweens du même bloc écrivaient
déjà la forme relative correcte**. Le fichier était à moitié conscient de sa
propre convention.

## La même faute de forme, une seconde fois, dans la caméra

La contre-plongée ne plaçait rien. La caméra montait de 2,2 (hauteur de tête)
puis redescendait de 2,27 par l'inclinaison : **net −0,07**. L'angle était bon,
le placement s'annulait. On regardait vers le haut *depuis la poitrine du
personnage* — d'où un ciel qui remplit le cadre et un personnage qui ne domine
rien.

Deux termes qui se croient indépendants et qui parlent du même nombre. Corrigé
en les séparant. Mesuré :

```
avant :  caméra à  0 / +2,2 stud du personnage,  visée +26,0°
après :  caméra à -0,8 / -2,9 stud,              visée +31,2°
```

## Et ma propre planche mesurait le flash

La planche du matin annonçait **« part sombre 2,6 % chez nous contre 9,2 % dans
la référence — il ne nous reste plus d'ombre »**. J'en ai tiré un réglage de
lumière entier.

**C'était faux.** L'image mesurée était *la plus chaude de la rafale*, donc
celle de l'impact, où le flash et l'astre saturent tout. Mesuré image par image,
sur deux passes complètes :

```
hors du flash    : 17 à 23 % de part sombre  → nous sommes PLUS sombres
                   que la référence (9,2 %), pas moins
pendant le flash : 2,6 %, dans les DEUX versions, quel que soit l'ambiant
```

Diviser l'ambiant par 6 ne déplace pas le chiffre d'un dixième. Le réglage a été
**annulé** — un changement sans bénéfice mesuré, fondé sur une prémisse fausse,
ne reste pas.

J'écrivais le matin même *« une planche est un instrument, et un instrument se
calibre »*. J'avais calibré les seuils et le code, **pas l'instant**. Un
instrument de mesure d'image a deux réglages, et choisir l'image par un extremum
sélectionne par construction le moment où la chose qu'on veut mesurer ne se voit
plus.

**Ce que l'erreur a produit d'utile** : au pic de l'ultime, le cadre est peint
par les particules de l'astre et par le flash d'écran ; l'éclairage du monde n'y
pèse presque rien. Le prochain levier est là.

## L'outil qui criait faux

L'alarme « atome muet » comparait le monde avant et après le *retour* de
l'appel : aveugle par construction à tout effet qui pose ses éléments dans le
temps — c'est-à-dire à toutes nos formes qui se propagent. Deux fausses alertes
de la même cause à une semaine d'écart, deux chasses à un bug inexistant.

Le verdict est maintenant différé d'une demi-seconde et recompté avant de crier.
Pas de liste d'exceptions : une liste se périme, et le prochain cas reproduirait
la panne.

## Ce qui a été servi

La masse qui tombe part désormais **à l'apogée** et non à l'impact : elle
touche à +2,47 s, le sol se casse à +2,61 s. La cause précède l'effet. Elle
quitte aussi la recette d'impact où elle **écrasait le cratère** par le plafond
de lisibilité — j'avais répondu en relevant ce plafond, ce qui était un
pansement sur une erreur de chronologie. Le plafond est revenu à sa valeur
normale et le cratère est de retour.

---

# 2026-09-04 (fin de journée) — nous sommes à l'intérieur du soleil

## Les trois suspects, mesurés dans l'ordre

**Le flash d'écran est écarté par sa propre durée.** Relevé : **0,12 seconde**,
68 % d'opacité au départ, fondu. Douze centièmes ne peuvent pas tenir une
seconde et demie de blanc. Aucun réglage tenté — la mesure suffit.

**L'astre est confirmé, et c'est pire qu'un voile devant l'objectif.** Géométrie
échantillonnée toutes les 5 centièmes :

```
+2,47 s   rayon  8,2   caméra à 20,5   il tombe, 68 % de l'écran
+2,66 s   rayon 12,1   caméra à  6,1   *** LA CAMÉRA EST DEDANS ***
+5,51 s   rayon 19,8   caméra à  6,1   toujours dedans
```

**Il se pose à 6,1 stud de la caméra avec un rayon de 8,2 : l'œil est déjà
dedans en arrivant.** L'impact le gonfle à 19,8 et l'y garde près de trois
secondes. Les particules naissaient donc **de tous les côtés de la caméra**.

**Le personnage est dedans aussi.** Il ne peut pas rester une silhouette devant
le soleil s'il est à l'intérieur.

## Une seule chose changée, et le résultat dit honnêtement

Émission coupée au moment où l'astre gonfle. Ni sa taille ni sa durée touchées —
le geste appartient à Milan.

```
part sombre au pic :  avant 2,6 %   après 3,1 %   référence 9,2 %
```

**Réel mais marginal.** Conservé parce que c'est juste par construction — on
n'émet pas dans l'œil — pas parce que ça règle le grief. Ce n'est pas une
correction et je ne l'appelle pas ainsi.

## Ce que la planche du pic montre, et que les nombres ne disaient pas

Trois vignettes : la référence, notre pic, et **notre propre plan une
demi-seconde plus tôt**. La troisième a un anneau blanc net, des ombres portées,
un ciel qui a une couleur, le carton-titre lisible et le personnage visible.

**Nous avons déjà le plan qui marche. Le pic l'efface pendant une demi-seconde.**
Le problème est *localisé dans le temps*, pas général — c'est une conclusion très
différente de celle de ce matin, et elle change ce qu'il y a à faire.

## Deux règles gravées, valables au-delà de cet incident

**Choisir une image par un extremum sélectionne le moment où la mesure est
aveugle.** Mesurer « l'image la plus chaude » choisit par construction l'instant
où la chaleur écrase tout le reste. Il faut mesurer toute la séquence et
regarder la courbe — et publier au moins deux instants, le pic et un témoin.

**Deux termes qui se croient indépendants et parlent du même nombre.** Le même
piège deux fois dans le même fichier en un jour : la chronologie imbriquée
(0,95 + 2,25 au lieu de 2,25) et la caméra (elle montait de 2,2, l'inclinaison
la redescendait de 2,27, net −0,07). Rien ne lève, rien ne se contredit, et le
résultat est la somme silencieuse.

## Ce qui reste ouvert

La recette d'impact demande encore plus de choses que le plafond n'en accepte,
et **quelle pièce disparaît change d'une passe à l'autre** — une fois l'aura,
une fois le cratère. Deux atomes en sont déjà sortis vers l'apogée. Ce qui reste
est plus lourd à déplacer : trois couches achetées, la secousse de caméra et le
flash.

---

# 2026-09-04 (suite) — le jeu ne tirait plus au sort, et la caméra est sortie du soleil

## D'abord le plus grave, et il dépasse l'ultime

Deux passes du **même** ultime, même code, même place :

```
passe A :  « plafond 6, déjà actifs 2 »  →  l'aura écartée, le cratère joue
passe B :  « plafond 6, déjà actifs 3 »  →  le cratère écarté
```

**Un joueur qui lançait deux fois le même ultime voyait deux choses
différentes.** Deux causes empilées :

**Le budget d'un effet dépendait de l'historique.** Le nombre de places d'un
ultime se calculait en retranchant les effets actifs *de tout le jeu* — donc ce
qui traînait encore d'un coup lancé une demi-seconde plus tôt. Le plafond joue
désormais sur la pièce, pas sur le passé.

**Et le tri n'était pas stable — alors qu'un commentaire affirmait qu'il
l'était.** Deux effets à égalité de priorité : lequel se retrouvait en queue,
donc jeté, se tirait au sort à chaque coup. Corrigé par un rang de déclaration.
Une recette qui dépasse son plafond perd maintenant **toujours la même chose**,
et l'auteur peut le prévoir en lisant sa table de haut en bas.

**La recette peut aussi trancher elle-même.** L'ultime déclare désormais son
sacrifice : le cratère est le geste — « le soleil a cassé le sol » — donc
intouchable ; le flash d'écran est déclassé, parce que la mesure du jour en fait
l'élément le moins porteur de toute la recette.

*Le plafond n'a pas été relevé.* Deux précédents disent maintenant la même
chose : un plafond qui tronque parle de la chronologie, pas du budget.

## La caméra est sortie du soleil

```
avant :  2,9 s à l'intérieur de l'astre (rayon 19,8 — caméra à 6,1)
après :  0 image sur 20, marge la plus serrée +7,5 stud
```

Cadrage d'impact reculé au-delà du rayon final, retour de la caméra au joueur
repoussé après l'éclatement, et l'astre détruit dès qu'il a fini de disparaître —
il laissait jusque-là une bille **invisible** de 40 stud de diamètre posée sur
l'arène pendant une seconde et demie.

**Un test le vérifie sur toute la phase, image par image** : l'astre grossit
pendant que la caméra est posée, donc « dehors au départ » ne prouve rien.
Accord entre le test et le moteur : marge prédite 6,08, mesurée 6,1 puis 7,5.

Trouvé en écrivant ce test : la constante du pack donne un rayon de 11,54 quand
le moteur en rend **8,24** — elle surestime de 40 %. Le rayon est donc écrit
comme une mesure datée, et la distance de caméra en est *dérivée*, jamais
recopiée.

## Le résultat, sans l'embellir

```
part sombre au pic :  3,1 %  →  3,1 %   INCHANGÉE
```

**Je ne dis donc pas que c'est réglé sur cet axe.** Et la réserve qui explique le
chiffre : notre arène est un décor de plein jour, la référence est une
illustration sombre. 9,2 % de noir est une propriété du **niveau**, pas de
l'ultime — cet axe ne pouvait pas être atteint ici.

Ce qui a bougé :

```
amplitude du dégradé   40  →  188      (référence : 165)
part chaude          89,4 % →  55,3 %
caméra dans l'astre   2,9 s →  0,00 s
```

Et surtout l'image : **l'arène existe**, le ciel est bleu en haut, l'explosion a
un cœur sombre et des bords nets, le personnage est visible au centre. Avant :
du brouillard uniforme.

## Ce que cette journée a appris et qui vaut au-delà

**Quand plusieurs réglages d'apparence successifs ne déplacent pas la mesure,
arrêter de régler et vérifier la géométrie.** J'ai réglé la lumière, puis le
flash, puis l'émission — trois passes, aucune ne bougeait le chiffre. Je réglais
la densité d'un nuage en me tenant dedans. La question « dedans ou dehors » est
binaire, se mesure en une ligne, et rendait inutiles des heures de réglage fin.

---

# 2026-09-04 (fin) — le plan corrigé, et le trou mesuré

## L'ultime, vu en entier

Capture du pic avec le nouveau cadrage : le personnage se tient au centre, éclairé
par en dessous, une colonne sombre monte derrière lui, l'anneau blanc traverse le
ciel, les flammes courent au sol, l'arène est visible et le ciel bleu en haut.

C'est le plan que le brouillard effaçait.

## Le trou de 1,90 s : mesuré, plus petit qu'annoncé

```
+3,34 s   la caméra revient au joueur, la lumière repart
+4,05 s   le monde est déjà revenu
+4,50 s   ... et l'animation joue encore
```

**Il n'était pas vide** : la traîne décroît de 67 à 25 objets et la lumière se rend
à travers lui. Ce qui manquait, c'est que tout **finissait tôt** — une demi-seconde
de geste dans un monde qui l'avait déjà oublié.

Corrigé en calant la durée de retour de la lumière sur la fin exacte de
l'animation. Coût : aucun effet supplémentaire.

## Le plafond, après la correction de déterminisme

**L'ultime ne tronque plus rien.** Seul `bris` est écarté, et pour une raison
légitime : aucune pièce cassable à portée — ce n'est pas le plafond.

Les quatre M1, eux, sacrifient toujours la même chose, mais désormais **toujours
la même** : la secousse de caméra. À décider si c'est le bon sacrifice — le flash
d'écran d'un coup léger dure six centièmes de seconde, la secousse est ce qui
vend l'impact. C'est une décision de feel, pas un nombre à relever.

## Deux règles gravées

**Quand plusieurs réglages successifs ne bougent pas la mesure, vérifier la
géométrie.** Trois passes — lumière, flash, émission — n'avaient rien déplacé,
parce que la caméra était à l'intérieur de l'effet. « Dedans ou dehors » se mesure
en une ligne.

**Une constante qui décrit une géométrie mesurable doit être une mesure datée.**
La constante du pack donnait un rayon de 11,54 quand le moteur en rend 8,24.

---

# 2026-09-04 — « l'animation est bug » : 2,74 s n'avaient jamais été vues

Milan a vu la scène et l'a dit sans détour. Il avait raison, et ce n'était pas le
trou de 1,90 s.

## La mesure

Un échantillon toutes les 0,05 s de la position et de la vitesse de la piste :

```
+0,34 s   position 0,48   vitesse 1,0
+0,63 s   position 0,07   vitesse 1,0   ← LA PISTE A RECULÉ
+0,93 s   position 0,22   vitesse 0,0   ← et elle gèle, 1,5 s
...
+4,05 s   position 1,76   vitesse 0,0   ← gel DÉFINITIF
```

**L'animation dure 4,50 s. Elle n'atteignait jamais 1,76.** Les 2,74 dernières
secondes du geste n'ont jamais été vues par personne — ni par nous, ni par Milan,
qui l'a signalé sans pouvoir le nommer.

## Deux causes, dans le même bloc

**Deux systèmes gèlent l'animation à l'impact, chacun de son côté.** L'un la rend
en remettant la vitesse à 1 ; l'autre en restaurant *la vitesse qu'il avait lue
avant*. Quand le second lit pendant que le premier gèle, il lit **zéro** — et
restaure zéro. La piste ne repart plus jamais.

Les deux sont corrects isolément. C'est leur état partagé qui ne l'est pas.

**Et le gel rembobinait la piste.** Sur un geste court c'est invisible ; sur une
cinématique de 4,5 s, l'animation redémarrait au milieu de sa propre mise en
scène. Ça se lit exactement comme « ça bug ».

## Après

```
reculs de la piste            1  →  0
gel                  1,5 s + définitif  →  0,50 s en deux temps voulus
position atteinte      1,76 / 4,50  →  4,08 et elle avance encore
```

**L'animation de Milan n'est pas touchée** — ni sa vitesse, ni sa durée, ni son
contenu. On a seulement arrêté de l'interrompre.

Toutes les pièces du kit qui demandent un arrêt sur image portaient la même panne
latente.

## La règle qui en sort

**Ne jamais mémoriser un état pour le restaurer sans vérifier qu'il n'est pas
déjà l'état de panne.** Une valeur lue « avant » n'est valide que si personne
d'autre ne touche à la même propriété. Quand deux systèmes partagent un état,
restaurer une valeur fixe et connue est plus sûr que restaurer une valeur lue.

---

# 2026-09-04 — je n'ai pas réussi à voir les 2,74 s

Objectif du tour : aller voir la seconde moitié du geste, que personne n'a jamais
vue. **Je n'y suis pas arrivé**, et l'échec mérite d'être écrit — il a pris trois
formes différentes en une heure.

**Une piste arrêtée ignore les commandes.** Une animation non bouclée s'arrête en
atteignant sa fin ; ma propre calibration l'y avait menée. Toutes mes demandes de
pose suivantes étaient sans effet : je photographiais la posture de repos en
croyant photographier le geste.

**Je photographiais le mauvais corps.** Deux mannequins d'une session précédente
se tenaient à moins de cinq mètres du personnage, debout et immobiles, et
remplissaient le cadre serré.

**Et pour finir, la mesure contredit l'image.** Un relevé stable, tenu près de
deux secondes, dit que le torse est à l'horizontale ; une capture large du même
instant montre un personnage parfaitement debout.

**L'image gagne** — c'est la règle : un signal extérieur bat une cohérence
interne. J'ai donc retiré le constat que j'allais publier et supprimé les deux
planches, qui auraient été lues comme des faits. C'est la deuxième fois cette
semaine qu'un verdict faux de ma part a failli être relayé.

## Ce qui reste vrai

La correction du gel tient : elle est mesurée sur la position et la vitesse de la
piste, sans aucune lecture de posture. **L'animation va maintenant jusqu'à 4,08 au
lieu de s'arrêter à 1,76.**

Trois pièces du kit portaient ce défaut, pas seulement l'ultime.

## Ce qui reste inconnu

Ce que le geste fait sur sa seconde moitié. Il faut un instrument valide avant
d'en dire quoi que ce soit.

---

# 2026-09-04 — le geste de l'ultime est planté

Cinquième méthode, et la première qui répond. Plus d'instrument à calibrer :
l'ultime joué **pour de vrai**, caméra fixe et indépendante, enregistrement de
l'écran, une image toutes les huit. Cadrage vérifié **avant** la série, pas après.

## Ce que la bande montre

**Le personnage reste planté et debout du début à la fin.** Pas de bond, pas de
bras levé visible, pas de frappe. Tout ce qui bouge dans le cadre est de l'effet
— l'aura dorée autour de lui, l'anneau qui traverse le ciel. Le corps ne raconte
rien.

Ça déplace le problème, et ça colle à ce que Milan dit depuis trois jours : ce
n'est pas la mise en scène d'un beau geste, c'est **l'habillage d'un geste qui
n'existe presque pas**.

**Réserve** : les vignettes sont vues de dos et mon recadrage coupe la tête. Je
peux affirmer qu'il n'y a pas de grand mouvement ; je ne peux pas décrire les
petits.

## La règle du tour

**L'image gagne sur la mesure.** Quand un relevé numérique et une capture du même
instant se contredisent, la capture gagne — sans attendre d'avoir compris
pourquoi le relevé se trompe.

Et le corollaire, qui a coûté cher : **quand on a cassé trois instruments
d'affilée, le quatrième instrument n'est pas la réponse.** La question n'était
pas « quelles sont les valeurs des membres » mais « à quoi ressemble le geste ».
Le dépôt avait déjà sa réponse : jouer la pièce pour de vrai et regarder.

---

# 2026-09-04 — CORRECTION : « le geste est planté » était faux

**Ce que j'ai écrit dans l'entrée précédente est à retirer.** J'ai dit que le
personnage restait planté pendant tout l'ultime et que le corps ne racontait
rien. C'est faux, et c'est la seule de mes erreurs de la journée qui ait été
publiée avant d'être attrapée.

Mesure sur la même animation, cette fois avec un indicateur qui peut la voir :

```
à la main, hors scène   : 1434° parcourus par le bras droit, écart max 120°
PENDANT LA VRAIE SCÈNE  : 110° d'écart atteints dès les 0,7 premières secondes
```

**L'animation bouge, et elle bouge autant en jeu qu'isolée.**

## Deux erreurs empilées

**Une mesure aveugle à ce qu'elle devait voir.** Je mesurais la *distance* entre
le bras et le tronc : 0,35 stud de variation, « donc le bras ne bouge pas ». Mais
un bras pivote autour de son épaule — **sa distance au tronc est presque
constante quelle que soit la pose**. Cette mesure ne pouvait pas détecter une
rotation, par construction.

**Un point de vue qui cachait le mouvement.** Ma caméra était derrière et à
droite ; le geste balaye vers l'avant, le torse l'occultait. J'avais écrit la
réserve « vue de dos, tête coupée » — mais je l'ai posée comme une précaution de
style au lieu d'en tirer la conséquence, qui était de refaire la prise de profil
avant de conclure. **Une réserve qu'on écrit sans en tirer la conséquence ne
protège de rien.**

## Ce qui reste vrai, et ce qui ne l'est plus

Le gel de la piste était un vrai bug, il est corrigé, et cette mesure-là ne
dépend d'aucune lecture de pose.

**Tout le reste de ce que j'ai dit sur le geste est retiré.** La planche a été
supprimée. Ce que fait l'animation sur sa seconde moitié reste inconnu — et il
faudra une prise de profil pour le dire.

---

# 2026-09-04 — l'ultime, vu en entier pour la première fois

## D'abord l'outil qui l'a permis

Le déclenchement vient maintenant **de l'intérieur du jeu**, par un attribut
surveillé — le motif que le plugin d'export utilise depuis des mois, imité plutôt
que réinventé. Ça lève le goulot qui bloquait toutes nos captures depuis quatre
jours : on ne pouvait pas à la fois lancer un enregistrement et déclencher une
scène de 4,5 secondes.

Deux garde-fous, tous deux payés ce mois-ci : **le déclencheur s'efface dès sa
lecture** (un ancien resté posé avait accumulé 90 copies d'une animation), et
**rien n'agit tant qu'il n'est pas explicitement armé**. Vérifié désarmé après
usage.

Il rapporte aussi ce qu'il a fait — « déclenché » — pour qu'une vidéo vide ne
puisse plus être lue comme « la scène ne rend rien ».

*Piège réintroduit un cran plus haut, et noté : mon premier essai comptait son
délai depuis l'armement et non depuis le début de l'enregistrement. La scène a
joué pendant le trajet entre les deux appels.*

## Et la scène

Première prise de profil complète, caméra fixe, avec toutes les corrections de
la journée :

```
0,50 s   le carton « COLÈRE DU SOLEIL »
0,75 s   l'arrêt sur image manga — noir et blanc inversé, franc
1,25 s   le monde vire à l'orange, l'astre descend
2,75 s   il emplit le cadre juste au-dessus de lui
3,00 s   impact, dégâts, or partout
3,50 s   cratère et flammes au sol, le ciel revient
6,75 s   la traîne finit de s'éteindre
```

Le personnage reste visible et planté face à la chose. **Rien ne se fige, rien ne
recule, rien ne disparaît au hasard** — les trois pannes de la journée sont
absentes de cette prise.

C'est la première fois que quiconque voit l'ultime en entier.

---

# 2026-09-04 — chercher d'abord dans ce qu'on a

Milan : *« problème de mémoire de ce que l'on a, gâchis de ce que l'on possède,
complexité à savoir quoi choisir »*. Le décompte du dépôt donne la cause exacte :

```
6 registres, 5 133 lignes
1 SEUL mécanisme automatique — le crochet de commit
   … qui ne les consultait pas
   … et qui se déclenche APRÈS que la chose est construite
```

**Voilà l'asymétrie.** Ce qui s'exécute tout seul arrive trop tard pour empêcher
de reconstruire ; tout ce qui l'empêcherait est un document qu'il faut penser à
ouvrir. Six fois cette semaine, personne n'y a pensé.

Un septième document n'aurait rien réglé — « complexité à savoir quoi choisir »
est déjà le symptôme de six index dans six formats.

## Ce qui a été construit

Un index **dérivé de la source** — 1 349 capacités : fonctions, modules,
recettes, formes, animations vérifiées — que le crochet consulte sur les
symboles **ajoutés** par le commit. Quand on ajoute quelque chose qui ressemble à
ce qui existe, il l'affiche.

Trois contraintes tenues : **il n'interdit jamais** (un crochet qui refuse est
désarmé au premier faux positif) ; **il est rapide** (+0,84 s, le crochet passe
de 1,0 à 1,8 s, et seulement quand du code est touché) ; **il ne se tient jamais
à la main** — c'est tout l'argument, un document se périme en silence, un index
dérivé ne peut pas mentir.

## L'épreuve a trouvé deux défauts dans l'outil

Validé comme les précédents : par panne délibérée, avec un témoin qui ne devait
rien déclencher.

Elle a montré que l'outil **n'indexait pas les modules**, seulement les fonctions
qu'ils contiennent — alors que « il me faut un système d'arrêt sur image » est
exactement la question qu'on se pose avant d'en réécrire un. Et que les
mots-outils français rapprochaient n'importe quoi. Les deux corrigés, l'épreuve
repassée, le témoin toujours muet.

## Une piste éliminée sur les vidéos de référence

Dans la référence, le personnage est rendu à l'encre **pendant que son
adversaire reste normal, dans la même image**. Ce seul fait élimine le
post-traitement — qui agit sur l'image entière — et le contour lumineux — qui ne
fait qu'un contour. Restent le matériau et le clone.

Deux pistes suivies depuis deux semaines, écartées par une observation.

---

# 2026-09-04 — le coup de base occupe 0,50 % de l'écran

Même instrument des deux côtés — la différence d'une image à la suivante, en part
de la vue 3D, à vingt images par seconde :

```
NOUS       un M1 ordinaire, caméra de jeu   plancher 0,00   médiane 0,00   PIC  0,50 %
RÉFÉRENCE  12 premières secondes            plancher 0,00   médiane 8,46   PIC 70,30 %
```

**Un facteur 140 sur le pic.** La médiane de la référence vaut dix-sept fois
notre pic.

## Ce qui a d'abord été réfuté : mon propre chiffre

L'observation qui a lancé ce tour — « la variante proche à 1 % » — **était du
bruit**. Mesuré sur l'arène **sans aucun effet**, le sable et les planches
donnent déjà 1,3 %. Mon seuil comptait le décor ; notre effet était sous le
plancher de l'instrument.

## Trois instruments, deux mensonges

Une couleur absolue comptait l'arène. Un écart à une image de référence dérivait
avec elle. Seule la troisième version — **chaque image comparée à sa voisine** —
donne un fond parfaitement stable (0,00 %) et fait ressortir un effet bref comme
un pic. Elle n'a besoin d'aucune calibration : c'est ce qui la rend fiable.

## Deux vérifications avant de conclure

**L'effet naît bien** — quatre émetteurs comptés à chaque coup. Ce n'est pas un
câblage cassé, c'est un effet petit. La distinction compte : densifier quelque
chose d'absent n'aurait rien donné.

**Le chemin est le bon** — le déclenchement passe par ce qu'un clic appelle. Ma
première version court-circuitait l'animation du client et ne montrait donc pas
ce que voit un joueur.

## La réserve

La vidéo de référence contient du mouvement de caméra, nous non. Une part de sa
médiane est du déplacement, pas de l'effet. Cela n'explique pas le facteur 140
sur le pic — mais cela interdit de comparer les médianes.

## Ce que ça implique

L'effet d'impact est porté par **26 recettes sur 45**. Si le contact de base se
voit à un demi pour cent de l'écran, la majorité des coups du jeu sont quasi
invisibles — et « c'est très en surface » cesse d'être une impression pour
devenir un chiffre.

C'est aussi l'explication la plus économique de trois semaines de travail sur
les effets : **on cherchait à les rendre plus intéressants alors qu'ils se voient
à peine.**

Aucun réglage n'est proposé ici. La mesure est établie ; la décision suit.

---

# 2026-09-04 (clôture) — l'upload est débloqué

**Quatre jours de blocage pour une commande d'approbation.** `rokit add` refuse
un auteur inconnu et n'a aucun drapeau automatique ; mais `rokit trust` accorde
la confiance sans poser de question, et l'ajout passe ensuite. La commande était
dans l'aide de l'outil, pas dans celle de la sous-commande qui échouait.

Hypothèse fausse qui avait retardé la recherche : « l'auteur est déjà de
confiance puisque son outil est installé ». Non — ce binaire venait d'un **autre
gestionnaire d'outils**, qui ne sait rien du premier.

**Débloqué n'est pas vérifié.** La lecture des fichiers d'animation est prouvée —
190 fichiers, zéro erreur, le défaut qui bloquait l'ancienne version a disparu.
Le chemin de publication, lui, n'a pas pu être essayé : tout l'existant est déjà
publié, il n'y avait rien de neuf. C'est le premier geste de demain.

## Ce qui reste ouvert, et où reprendre

**La mesure du coup de base.** Les deux chiffres qui avaient lancé la piste — 1 %
et 34 % — sont morts tous les deux : ils venaient d'un seuil de couleur qui
comptait le décor de l'arène. Ce qui survit est l'instrument, et il est bon :
**chaque image comparée à sa voisine**, fond parfaitement stable, rien à
calibrer.

Avec lui : notre coup de base pèse **0,50 %** de la vue, la référence **70,30 %**.

Reprendre en refaisant les deux variantes de la Marche du Titan avec cet
instrument — une passe, deux enregistrements. Mais le fond de l'affaire n'en
dépend pas : l'effet d'impact est porté par 26 recettes sur 45.

## Une faille de protocole, notée avec son remplacement

Amener le jeu dans un état par un raccourci est légitime. **Mesurer** par ce même
raccourci ne l'est pas — il sautait l'animation du client, donc ne montrait pas
ce que voit un joueur. Le remplacement est déjà en place : le déclencheur appelle
maintenant ce qu'un clic appelle.

---

# 2026-09-05 — le dash et la roulade sont en jeu

L'outil d'upload est passé de « débloqué » à **vérifié** : deux animations
publiées, relues depuis Roblox, puis câblées et vues jouer en appuyant sur les
touches.

```
dash     Q   0,450 s   marqueur de plantée : tire 3 fois
roulade  C   0,550 s
corps déplacé : 4,5 stud
```

**Le dash** remplace une version qui **reculait du torse de 1,29 stud en plein
clip** — seule animation vers l'avant du corpus dans ce cas. L'arbitrage datait
du 3 septembre ; seul l'upload manquait.

**La roulade** portait jusqu'ici une **peau de dash**, faute de pouvoir publier
autre chose. Elle a maintenant un vrai clip de roulade.

## Une prémisse du dépôt corrigée à sa source

Le code affirmait qu'un vrai clip de roulade arrière existait dans un pack, non
publié. **C'est faux** — ce pack contient tout autre chose, et il n'y a de
roulade arrière nulle part. Cette seule phrase a fait redemander ce clip cinq
tours de suite.

**Et il n'en faut aucun** : le contrôleur applique sa propre vitesse, donc la
direction vient du code. Un seul clip générique sert les quatre sens, là où on
cherchait quatre pistes à publier et entretenir.

## La leçon qui se généralise

En cherchant à lire la direction d'une roulade sur le déplacement de la racine du
clip, les quatre candidats ont rendu zéro. Ce n'était pas un mauvais instrument :
**le mouvement n'est pas dans l'animation, il est dans le code.**

Avant de mesurer une propriété sur un objet, se demander si cet objet est celui
qui la produit. Quand une mesure ne varie pas, la première hypothèse doit être
« je regarde au mauvais endroit ».

## Retours arrière

Une ligne pour revenir, dans les deux cas, écrite à côté du code.

---

# 2026-09-05 — le coup de base, en image

Deux vignettes, même cadrage, même caméra de jeu, même place, à l'instant de
l'impact. Pas un chiffre — la question « est-ce que ça se voit » se tranche à
l'œil.

**La compétence produit une gerbe dorée ample** : étincelles, gravats, poussière.
**Le coup de base produit un filet de fumée et un « 6 ».** C'est celui que le
joueur voit quatre fois par seconde.

Le comptage dit la même chose : quatre émetteurs contre cinquante, et le coup de
base n'émet pas en continu.

## Ce que ça règle

Trois semaines de « les VFX ne sont pas bons » trouvent une cause simple : sur la
pièce la plus vue du jeu, **il n'y a presque rien**. Ce n'était ni une question
de forme, ni de pack, ni de palette.

## La règle la plus coûteuse de la semaine

**Une porte fermée ne se rouvre pas toute seule.** Quand on construit en double,
on s'en aperçoit. Quand on élimine à tort, personne ne revient jamais.

On a écarté une technique en la croyant limitée — alors que notre propre code
l'implémentait depuis trois jours, essai à l'image et coût mesuré inclus. Une
session entière a cherché ce qu'on avait déjà écrit. Deux semaines.

L'index de nos capacités aurait donné la réponse en une commande. Il existait la
veille. Personne ne l'a interrogé, **parce qu'on ne pense à chercher que quand on
va construire**.

---

# 2026-09-05 — le coup de base se voit enfin

Avant : un filet de fumée. Après : une gerbe dorée au point de contact. Même
cadrage, même caméra de jeu, même place.

**Et rien n'a été ajouté.** Les trois premiers coups de base déclaraient quatre
choses pour un plafond de deux : la forme du coup et la secousse de caméra
étaient écrites, entretenues, et **jetées à chaque coup** depuis toujours.
L'audit le criait depuis des semaines. On a arrêté de détruire, c'est tout.

Le quatrième — le finisher — n'a pas été touché : il avait déjà son rang.

## Le régime, mesuré en chaîne

Un coup de base se joue quatre fois par seconde ; une compétence une fois toutes
les quelques secondes. Ce n'est pas le même régime, donc la mesure s'est faite
sur une chaîne complète :

```
huit coups enchaînés   →  60 émetteurs, soit 7,5 par coup (contre 4)
pic d'émetteurs vivants   423
l'arène AU REPOS          404
```

**La chaîne complète n'ajoute que dix-neuf émetteurs au décor.** Le coût n'était
pas le sujet — l'arène en fait déjà quatre cents toute seule.

Et la hiérarchie tient : sept et demi pour un coup de base contre cinquante pour
une compétence. Il se voit, il ne domine pas.

## L'encre, vue

Le monde passe au noir et blanc avec lignes de vitesse, le personnage devient un
aplat noir à trait blanc, le lointain blanchit. Couleur normale deux dixièmes
avant et après : une ponctuation, pas un état.

**Le témoin a trouvé sa propre panne** — l'effet masque tout l'affichage, et le
témoin en faisait partie. Il se supprimait lui-même. Sans ce garde-fou, on
concluait « ça ne rend rien » et on refermait la porte une seconde fois.

## Le plafond comptait le son

Vingt recettes sur quarante-sept jetaient du travail écrit. Après avoir cessé de
compter la secousse de caméra, le flash d'écran et **la pile audio** : cinq.

Aucun palier n'a bougé. La doctrine du 16 mai (commit `aca4a33`) parle de ce
qu'on **voit** — « jamais 10 VFX simultanés ». Une secousse ne se superpose pas à
l'image, elle la bouge ; un flash ne s'ajoute pas aux effets, il les remplace ; un
son ne se voit pas du tout. Le troisième n'était pas dans la piste demandée, je
l'ai inclus par le même raisonnement et signalé plutôt qu'étendu en silence.

**Vérifié à l'œil, pas au compteur.** `DemiDieu_Skill2_Impact` passait de justesse
à deux effets sur quatre, il en laisse cinq maintenant. Une seule gerbe dorée,
lisible, dissipée en 1,1 s. Un coup, pas quatre effets qui se disputent l'image.

La maxime est remise dans `CLAUDE.md` avec sa date et son commit. Elle avait
disparu d'une réécriture : la règle survivait dans le code sans sa justification,
et on a passé une journée à croire ces quatre nombres arbitraires. Une règle sans
son pourquoi finit contournée ou vénérée, jamais comprise.

`Skill1_Impact` est **morte** : citée par un seul script, sa propre déclaration.
Troisième « chose qu'on croit posséder » de la semaine. Non supprimée — c'est une
décision, pas un nettoyage.

## Quatre recettes à tailler — proposition, rien de coupé

Milan ne monte pas les paliers, et il a raison sur l'arithmétique : *Hero(1) +
Supporting(2-3) + Ambient* fait quatre ou cinq. `medium = 4` est la doctrine
écrite en chiffres.

Le tri proposé, pour les quatre pièces au-dessus du plafond :

| pièce | Hero | coupé | pourquoi |
|---|---|---|---|
| Main du Colosse 6→4 | `Impact Burst` | `Dust` + `Wind` | deux atmosphères pour le même nuage |
| Frappe Céleste 5→4 | `GroundSmash` | `Dust` | dure 1,1 s quand le Hero dure 0,7 |
| Marche du Titan 7→6 | `Shockwave Impact V` | `Encre` poussière | doublon de `CraterDust`, et en encre sur une pièce dorée |
| M1_4 5→4 | `GroundSmash` | `CraterDust` | du doré sur la seule pièce volontairement achromatique |

**Quatre des cinq coupes sont de la poussière.** Ce n'est pas un problème de
hiérarchie, c'est une habitude : chaque recette a ajouté un nuage parce qu'un
impact fait de la poussière, sans voir que les débris déjà projetés en font un.

## `Skill1_Impact`, morte et datée

Tuée le 2026-08-27 par `bff2d62`, quand le kit Demi-Dieu a pris sa place sans la
retirer. Marquée dans le fichier et au registre, **pas supprimée** — c'est l'appel
de Milan.

En la marquant j'ai trouvé mieux : elle est **déclarée deux fois sous la même
clé**, la seconde écrasant la première. Même vivante, la moitié n'a jamais joué.

Le compte des « choses qu'on croit posséder » est maintenant tenu au registre,
avec deux formes séparées : celle qu'on possède sans le savoir (coût : du travail
en double) et celle qu'on croit posséder et qui est morte (coût : une fausse
conclusion). Six entrées.

## Les cinq coupes, et la planche qui a failli mentir

Les quatre recettes sont taillées, aucun palier monté. Plus aucune recette du kit
ne tronque.

**La planche montre l'inverse de ce que je craignais** : la matière est toujours
là — les quatorze morceaux de sol volent pareil. Ce qui *apparaît*, c'est le
héros : le cœur orange vif de `Impact Burst` se lit enfin, alors qu'il était noyé
avant. L'ambiance mangeait le coup.

Réserve : une seule prise par colonne, et l'éparpillement des débris varie d'un
cast à l'autre. La planche établit **la lisibilité du héros**, pas un compte.

Trois instruments cassés en route, tous dits dans le commit — dont une rangée
« après » entièrement vide que j'ai failli lire comme « la coupe a tout enlevé ».
C'était `RecipeRegistry.resolve`, qui n'existe pas. Le témoin a prouvé que la
prise était bonne : l'effet était absent, pas la fenêtre.

## L'encre était déjà câblée. En entier.

Les trois déclencheurs que Milan voulait existent, et le verrou aussi :

    ultime            → Ultimate_DescenteDuDemiDieu:460   (polarité « ombre »)
    Jugement réussi   → Skill4_Jugement:225               (« encre »)
    M1_4 palier 2     → CombatService:508                 (« encre »)
    verrou global     → VERROU_S = 7,0 s

Sa fourchette était « 6 à 8 s ». Le verrou vaut 7,0. Personne ne le savait.

**Septième « chose qu'on croit posséder » de la semaine**, et la plus coûteuse :
le prix n'est pas du code en double, c'est une priorité qui occupe la tête de la
liste sans raison. Un seul `grep impactFrame` répondait.

Ce qui n'est **pas** établi : que chacun des trois tire vraiment en jeu. Deux sont
derrière une condition de jeu (palier 2, parade réussie).

## L'encre : les trois tirent. Vérifié en moteur.

Observé sur `Events.Combat.CombatFX` — le remote que le vrai receveur écoute, pas
une copie — chacun déclenché par son vrai chemin :

    ultime          kind=DemiDieu_Ultimate_Puissance  ombre  0,30  pose 0
    Jugement paré   kind=DemiDieu_Skill4_Counter      encre  0,20  pose 0,20
    M1_4 palier 2   kind=DemiDieu_M1_4_Impact         encre  0,22  pose 0,3667

**Et le verrou se voit dans les chiffres** : 2 encres pour 4 M1_4, 1 pour
6 parades. Il ne laisse pas passer les rafales — c'est exactement son travail.

La note « not verified in-engine » que `Skill4_Jugement` portait depuis le
2026-08-27 est remplacée par ce qui a été mesuré. C'était le même genre d'aveu
écrit et jamais relu que le commentaire de `Wind` : une incertitude qui survit
devient une vérité admise.

**La plus vieille demande de Milan est finie.**

Quatre instruments cassés en chemin, tous dits : `require` depuis le bac à sable
rend un `MomentumService` fantôme (mon palier 2 était faux, le vrai montait par
les coups) ; un attribut posé par le client ne remonte pas au serveur ; `Damage`
au lieu de `damage` dans `MoveConfig` ; et l'observateur lui-même, éprouvé sur un
M1 ordinaire avant d'être cru.

## La stamina serveur — la racine était plus bas que le diagnostic

Le constat était « `StaminaService` n'a aucun consommateur vivant ». C'était vrai,
et insuffisant : **il n'était pas chargé du tout.** `ServiceLoader` a été retiré
pour la tranche V1, et tout `src/server/Services/` avec lui. Son `init()` n'était
jamais appelé.

Donc même en câblant les appelants, `Consume` aurait rendu faux pour tout le
monde. On l'a réveillé depuis l'entrée V1 — lui seul, parce que lui seul est
devenu une dépendance réelle.

Les deux consommateurs sont câblés ensemble, dans le même fichier :

    dash double-tap   25   le coût n'existait que dans un commentaire
    roulade           22   prélevé par le CLIENT, donc gratuit en PvP

**Vérifié par l'épreuve de l'attaquant** : on tire sur les remotes comme le
ferait un client modifié, sans rien payer côté client. La stamina serveur descend
(100 → 81,5 → 29,7), et une demande de dash sans le stock revient
`Rejected / no_stamina`.

**Une précaution qui compte** : `Consume` rend faux dans deux cas très différents
— pas assez, ou joueur pas encore suivi. Un appelant qui refuse sur ce faux
casserait le dash à chaque respawn. `IsTracked` sépare les deux, et les appelants
échouent **ouvert** tant que le service ne suit pas.

À signaler à Milan, sans le corriger : la regen vaut 15/s hors combat, une
roulade 22. Le coût est réel mais très clément — il a fallu quatre roulades en
0,08 s pour atteindre le refus.

## L'état de `src/server/Services/` — relevé, rien réveillé

Sur 14 modules, 12 définissent un `init()` et **10 ne le voient jamais appelé.**

Trois sont chargés et utilisés par du code vivant sans que leur `init()` tourne.
Deux sont sans conséquence — celui de `HitboxService` est vide (« pure utility »),
celui de `RemoteGuard` n'écrit qu'un log. **Le troisième compte** :
`CombatStateService.init()` branche le nettoyage au respawn et au départ du
joueur. Il ne tourne pas, donc l'état de combat n'est jamais nettoyé. Non traité.

Six ne sont chargés par personne, dont un îlot mort de trois qui ne se requièrent
qu'entre eux : `M1Service` → `RollbackService` → `SnapshotService`.

**Et le point rassurant, qu'il faut dire aussi** : aucun service non chargé n'est
requis par un chemin vivant. Les morts ne sont référencés que par d'autres morts.
La seule panne silencieuse réelle est ce `init()` manquant.

## Le compte, rangé par forme

Neuf cas en une semaine, quatre formes. Chacune a un coût différent et se
détecte autrement :

| forme | coût | comment on la trouve |
|---|---|---|
| on la possède sans le savoir | travail en double | chercher avant de construire |
| on la croit possédée, elle est morte | une fausse conclusion | chercher l'appelant |
| on l'a déjà faite sans le savoir | la place qu'elle prend | chercher avant d'ouvrir le chantier |
| elle existe mais ne tourne pas | panne silencieuse, et casse quand on la branche | vérifier qu'elle tourne |

**Une règle couvre les quatre** : avant de construire, chercher l'appelant ;
avant de brancher, vérifier que ça tourne.

## `CombatStateService` réparé — et le réveil a trouvé un second défaut

Son `init()` branche le nettoyage de l'état de combat au respawn et au départ du
joueur. Il ne tournait pas : stun, iFrames, hyperarmor et attaque en cours
survivaient à la mort.

**En le relisant avant de l'appeler, j'ai trouvé mieux** : il ne connectait que
`PlayerAdded`. Un joueur **déjà présent** au moment de l'appel n'était jamais
suivi — c'est-à-dire toujours, en Play Solo. Le réveiller tel quel aurait donné
une réparation qui ne répare rien. `StaminaService`, lui, portait cette boucle
depuis le début ; j'ai copié son motif.

Vérifié en moteur : stun et iFrames posés à `true`, respawn par le vrai chemin,
les deux à `false` après.

**Et il faut le dire dans le bon sens** : dix `init()` jamais appelés, ça
ressemble à un incendie. Il y avait **un** vrai cas. Aucun service non chargé
n'est requis par un chemin vivant — les morts ne sont référencés que par
des morts.

L'îlot mort `M1Service` → `RollbackService` → `SnapshotService` est marqué dans
les trois fichiers, pas supprimé : même appel que `Skill1_Impact`.

**Angle mort d'outil noté** : les Skills sont requis dynamiquement, donc
invisibles à tout suivi statique de `require`. C'est ce qui m'a fait déclarer
`CombatStateService` mort à tort. La note est dans `index_capacites.py` pour que
personne n'y ajoute un mode « code mort » qui hériterait du défaut.

## La caméra bloquée après une mort — corrigé, c'était en production

`MiseEnScene` promettait dans son en-tête de rendre la caméra si « le joueur
meurt ». Les autres cas étaient couverts, **celui-là ne l'était pas** : la
promesse était écrite, le code ne la tenait pas.

Mesuré avant : scène de 90 s, mort à 1 s → caméra `Scriptable` encore après le
respawn. Sur l'ultime d'aujourd'hui (4,5 s), un joueur qui meurt dedans
récupérait sa caméra au minuteur, pas à sa réapparition.

Après correction, même épreuve : rendue en **0,4 s**. Deux voies, parce que la
mesure a montré un reste — `CharacterRemoving` ne tire qu'au respawn, donc
`Humanoid.Died` s'y ajoute pour le temps de mort lui-même.

**Et ma première épreuve disait « ça va »** : scène de 6 s, lecture après 15 s.
C'est le minuteur qui avait rendu la caméra. Une épreuve plus longue que le
phénomène teste son extinction, pas le phénomène. Au registre.

## Main du Colosse : la verticalité, étape 1 sur 2

`Colonne` — construite le 3 septembre, jamais utilisée par cette pièce — remplace
`Impact Burst`. On remplace, on n'ajoute pas : le plafond `medium` vaut 4 et la
doctrine dit Hero(1) + Supporting(2) + Ambient(1).

Ce qui est **solide** : la colonne monte à **10,1 stud** au-dessus du point
d'impact, soit deux fois la hauteur du personnage. La planche le montre — un jet
doré traverse le cadre là où il n'y avait qu'une poussière au sol.

Ce qui n'est **pas** établi : le pourcentage d'écran. J'ai cassé trois instruments
en essayant de le chiffrer — un détecteur de pixels dont j'ai raté la fenêtre, un
témoin cyan indiscernable de la barre de stamina, et une boîte englobante qui
mesurait la dispersion des débris (220 % pour l'AVANT, ce qui ne veut rien dire).
Le quatrième n'est pas la réponse : je livre l'image.

**Il reste la largeur.** La colonne est un ruban vertical, pas une masse. La
verticalité était l'étape qui manquait ; l'élargissement est la suivante, et
c'est là que les plafonds d'`ArcSol` et `GroundChunks` entreront en jeu.

Deux erreurs de ma part sur la même racine : j'ai posé le drapeau `ancrage` dans
la branche `Couloir` au lieu de `Colonne` — un `replace` sur une chaîne présente
deux fois. Et j'ai cherché la synchro pendant que le jeu tournait, alors que rojo
alimente le datamodel d'édition : il faut relancer Play pour voir un changement.

## Main du Colosse, étape 2 : la largeur

`ArcSol` passe de 9 à 15 de rayon, `GroundChunks` n'est plus raboté à 8.

**Et je m'étais trompée de plafond.** J'avais annoncé `ArcSol` bridé par un
`math.clamp(…, 4, 9)` : ce clamp appartient à un autre atome (`Impact`), sur un
chemin que cette pièce n'emprunte pas. Son `ArcSol` n'a jamais été raboté — il
était simplement demandé petit. J'ai annulé l'élargissement du mauvais chemin,
qui aurait changé d'autres recettes en douce.

`GroundChunks`, lui, rabotait vraiment : quatre recettes demandaient 10 à 16 et
recevaient 8. La vieille raison écrite — « au-delà on sort du cadre de combat » —
était un jugement ; elle est **remplacée dans le fichier** par la mesure.

**Une autre chose que mes planches précédentes ne montraient pas** : je ne
passais pas de `dir` dans le contexte, et `ArcSol` en exige un. Il n'avait donc
jamais rendu dans aucune de mes prises. En jeu il en reçoit un. Les planches
d'avant comparaient deux pièces amputées de la même façon — la comparaison
tenait, mais l'image ne montrait pas la pièce réelle.

La planche finale est vérifiée sur les **deux** rangées avant publication : la
première tentative avait une rangée « avant » vide, à 613 pixels constants,
c'est-à-dire le décor. L'effet avait tiré avant le début de l'enregistrement.

La raison du magenta est maintenant **à côté de la constante** : j'avais refait
un témoin cyan, et la barre de stamina du HUD est cyan.

## La salve d'encre est câblée, et vue

Un panneau plein écran, deux images rendues, sur le finisher M1_4 au palier
surchargé. La frontière de doctrine est écrite dans le fichier : l'arrêt sur
image garde la 3D lisible et refuse le panneau opaque ; la salve fait disparaître
la 3D entièrement et **le panneau est son mécanisme**. Deux effets, pas deux avis.

Les quatre contrôles de la spec sont passés :

    témoin magenta      présent, PAR-DESSUS le panneau opaque
    couverture          tout le viewport, aucun liseré de jeu
    durée               2 images rendues, comptées côté jeu
    animation après     Speed = 1,00, la position avance

Le piège annoncé était réel et il est évité par un seul nombre : le témoin vit
dans son propre `ScreenGui` à `DisplayOrder = 10000`, le panneau à 50. `ZIndex`
n'ordonne qu'à l'intérieur d'un `ScreenGui`. La raison est maintenant écrite à
côté des deux valeurs.

L'ID `rbxassetid://136441647359118` vient d'un vrai upload asphalt, avec une
entrée `[inputs.planches_encre]` **écrite et éprouvée dans le même tour** — la
spec la proposait sans l'écrire, notant qu'une config non éprouvée est un réglage
mort de plus.

Réserve : l'animation testée était `Idle`. L'interaction avec `HitstopController`
sur un vrai M1_4 reste à voir.

## Le hitstop, mesuré — et il tient à un mot

Ce que le code déclare, sans ambiguïté :

    Light 50 ms   Medium 67   Heavy 83   Ult 133

Un M1 envoie `Light` : **50 ms, soit environ trois images à 60 im/s.** La
référence, elle, ne dépasse jamais **une image**.

Un piège frôlé : les paliers sont écrits en capitale (`Light`) et plusieurs
recettes déclarent leur `tier` en minuscule. `TierDuration("light")` rend
**0,000 s** — pas d'erreur, pas de gel. J'ai vérifié ce que le remote envoie
vraiment sur un M1 : `Light`, avec la capitale. Le câblage tient, mais il tient
à une lettre.

**Ce que je n'établis pas** : mes chronométrages en jeu ont donné 162 à 346 ms,
loin des 50 déclarées, avec un compte d'images incohérent (1 image pour 162 ms).
L'instrument n'est pas fiable — probablement parce qu'une piste peut quitter la
liste des pistes jouées pendant le gel. Je ne cite donc pas ces nombres comme un
fait ; deux candidats à vérifier plus tard : `MangaImpactFrame` gèle aussi, et
`task.delay` a sa granularité.

**Diviser par cinq ne marche pas.** 50/5 = 10 ms, moins d'une image : le hitstop
disparaîtrait au lieu de raccourcir. La cible juste est **une image**, et elle
doit s'écrire en images, pas en secondes — même leçon que `plancheImages`.

**L'arbitrage, et il n'est pas évident.** Le hitstop donne du poids. Chez eux, ce
poids vient d'ailleurs : la caméra défile de 14 à 19 px par image *pendant*
l'impact. Notre caméra, elle, ne bouge pas. **Couper le gel sans ajouter du
mouvement risque de rendre les coups mous, pas plus secs.** Les deux chantiers
sont liés — c'est la caméra qu'on avait mise de côté.
