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
