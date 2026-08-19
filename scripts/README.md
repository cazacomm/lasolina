# Automatisation du blog — La Solina

Un article de blog est généré et publié automatiquement **chaque lundi à 9h00 UTC**
par le workflow [`.github/workflows/blog-auto.yml`](../.github/workflows/blog-auto.yml).

## 1. Mettre la clé API en place (à faire une seule fois)

1. Créer une clé sur <https://platform.openai.com/api-keys>.
2. Dans le dépôt GitHub : **Settings → Secrets and variables → Actions → New repository secret**.
3. Nom : `OPENAI_API_KEY` — Valeur : la clé (`sk-…`).

En ligne de commande :

```bash
gh secret set OPENAI_API_KEY -R cazacomm/lasolina
```

Sans ce secret, le workflow échoue proprement (code 1) sans rien committer.

## 2. Lancer manuellement

**Depuis GitHub** : onglet *Actions* → *Blog auto — La Solina* → *Run workflow*.
La case **dry_run** génère l'article et affiche le résultat dans les logs **sans rien écrire ni pousser**.

**En local** :

```bash
pip install openai
export OPENAI_API_KEY="sk-..."

python3 scripts/generate-article.py --dry-run   # simulation, aucun fichier touché
python3 scripts/generate-article.py             # génère et écrit (à committer soi-même)
python3 scripts/generate-article.py --mock      # teste la tuyauterie sans appeler l'API
```

`--mock` ne produit **aucun contenu éditorial réel** : il recopie le gabarit pour vérifier
que le choix du sujet, la validation et les mises à jour de fichiers fonctionnent.

## 3. Codes de sortie

| Code | Signification | Effet sur le workflow |
|---|---|---|
| `0` | Article généré et validé | commit + push |
| `78` | Aucun sujet restant dans `BLOG_WORKFLOW.md` | arrêt propre, pas de commit |
| `1` | Erreur (API, validation, fichier manquant) | échec visible, **aucun fichier écrit** |

## 4. Ce que fait le script

1. Lit `blog-config.json`.
2. Extrait de `BLOG_WORKFLOW.md` les 12 sujets suggérés **et** les règles éditoriales,
   qui sont injectées telles quelles dans le prompt.
3. Scanne `/blog/*/index.html` : un article généré porte un marqueur
   `<!-- lasolina-topic: N -->` juste après `<body>`. Un sujet marqué n'est jamais repris.
4. Choisit le premier sujet non traité, dans l'ordre de la liste.
5. **Relit l'article de référence** (`blog/pizza-nuit-tarbes-distributeur-24h/index.html`)
   et s'en sert de gabarit. Aucun template HTML n'est dupliqué dans le script :
   header, footer, favicons, polices, feuille de style et bloc CTA en sont extraits
   à chaque exécution, donc si le gabarit évolue les articles suivants suivent.
6. Appelle OpenAI (`gpt-4o`, `temperature` 0.7, `max_tokens` 9000, réponse forcée
   en `json_object`) et lui demande **uniquement le contenu éditorial** :

   ```json
   {"title": …, "h1": …, "breadcrumb": …, "meta_description": …, "lede": …,
    "sections": [{"h2": …, "content": [{"type": "p|h3|ul|ol|strong", "text": …}]}],
    "faq": [{"question": …, "answer": …}]}
   ```

   Le modèle **n'écrit plus une ligne de HTML**. Auparavant il régénérait la page
   entière : les deux tiers de ses tokens de sortie partaient en balisage
   (`<head>`, JSON-LD, header, footer), ce qui plafonnait le corps rédigé autour
   de 850 mots quelle que soit la consigne — 764, 844, 848 mots sur des runs
   successifs, y compris en demandant 1600. Le prompt est passé de 23 450 à
   ~4 700 caractères.

   Seul balisage autorisé dans les textes : `**gras**` et `[libellé](/chemin)`.
   Les liens sont restreints aux chemins internes, un lien externe est donc
   structurellement impossible. Tout le reste est échappé — le modèle ne peut pas
   injecter de HTML.
7. **Valide le contenu** avant toute écriture : champs présents, longueur du
   `title` (40–70) et de la `meta_description` (< 155), types de blocs connus,
   exactement 5 questions de FAQ, maillage interne (≥ 2 liens vers
   `/#distributeurs`, `/#carte` ou `/#faq` et ≥ 1 vers `/blog/`), volume entre
   900 et 1900 mots. Le moindre échec ⇒ code 1, **rien n'est écrit**.

   Les contrôles sur le canonical, l'Open Graph, la Twitter Card, le marqueur,
   le `<h1>` unique et la validité des JSON-LD **ont disparu de cette étape** :
   ces éléments sont désormais fabriqués par le script (`json.dumps` pour les
   JSON-LD) et ne peuvent plus être faux. Ils restent vérifiés une fois la page
   assemblée, par `validate_assembled()`, qui contrôle notre propre code et non
   le modèle.

   Le volume se compte sur le **contenu** (`content_word_count()`), pas sur du
   HTML : `lede` + sections, FAQ exclue. Plus de balises ni de boilerplate dans
   le total.

   *Rattrapage :* dès que le corps passe **sous la cible de 1200 mots** — même si
   la validation passerait — le script relance **un unique** appel avec un prompt
   correctif. Il garde ensuite **la meilleure des deux copies** : une version
   valide prime sur une version invalide, puis la plus proche de la cible, et
   chaque reprise repart de la meilleure copie obtenue. Plafond strict :
   **3 appels** (`MAX_CALLS`) — le modèle rend ~600 mots en première passe et
   gagne 60 à 75 % par reprise, deux appels plafonnent vers 1000-1100.
8. **Assemble la page** : `<head>` repris du gabarit avec seulement les champs
   propres à l'article remplacés (title, description, canonical, OG, Twitter,
   dates), les trois blocs JSON-LD sérialisés depuis le contenu, le marqueur
   d'idempotence inséré après `<body>`, le `<main>` construit de toutes pièces,
   header et footer repris tels quels.
9. Écrit `blog/<slug>/index.html`, puis met à jour `blog/index.html` (carte + JSON-LD),
   `sitemap.xml`, `rss.xml` et `llms.txt`.

## 4 bis. Réécrire un article existant

```bash
python scripts/generate-article.py --rewrite <slug>
```

Régénère un article déjà publié et **écrase** son fichier. Le sujet est retrouvé
via le marqueur `<!-- lasolina-topic: N -->` présent dans le fichier, donc aucun
risque de se tromper de sujet. Le teaser de `blog/index.html` et l'entrée
`rss.xml` sont resynchronisés (`refresh_entries()`) : les updaters normaux sont
idempotents par URL et laisseraient sinon le texte de l'ancienne version.

Disponible aussi depuis Actions : champ **rewrite** du `workflow_dispatch`.

## 5. Idempotence

- Le slug est **déterministe** : même titre de sujet ⇒ même slug.
- Si `blog/<slug>/index.html` existe déjà, le script s'arrête en code 78 sans rien écraser.
- Les mises à jour de `blog/index.html`, `sitemap.xml`, `rss.xml` et `llms.txt` vérifient
  d'abord si l'URL est déjà présente : rejouer le workflow ne crée jamais de doublon.
- Aucun article existant n'est jamais modifié ni supprimé.

## 6. Coût estimé

Tarifs OpenAI `gpt-4o-mini` en vigueur à la mise en place — **à revérifier sur
<https://openai.com/api/pricing/>**, ils changent.

Par exécution : environ **7 000 tokens en entrée** (le gabarit complet fait l'essentiel du
prompt) et **5 000 à 7 000 tokens en sortie**.

L'ordre de grandeur est de **quelques centimes d'euro par article**, soit **bien moins d'un
euro par an** pour une publication hebdomadaire. Le poste de coût réel n'est pas l'API mais
la relecture humaine.

Pour vérifier la consommation réelle : les logs du workflow affichent le décompte exact
des tokens de chaque exécution (`[blog] Tokens : … entrée + … sortie = …`).

## 7. Ajouter des sujets

La réserve de sujets est la section **« Douze sujets d'articles suggérés »** de
[`BLOG_WORKFLOW.md`](../BLOG_WORKFLOW.md). Quand elle est épuisée, le workflow sort en
code 78 chaque lundi sans rien casser. Il suffit d'ajouter des lignes numérotées au même
format pour relancer la machine :

```markdown
13. **Titre du sujet** — angle, intention de recherche visée.
```

## 8. Relecture

La génération est automatique, la responsabilité éditoriale ne l'est pas.
Après chaque publication, vérifier au minimum : aucun prix ni chiffre inventé, adresses
exactes, ton conforme. Les règles complètes sont dans `BLOG_WORKFLOW.md`, section
« Règles éditoriales ».
