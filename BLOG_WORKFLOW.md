# Workflow blog SEO/GEO — La Solina

Site statique HTML/CSS hébergé sur GitHub Pages.
Domaine canonique : **https://www.lasolinapizza.fr/** (forme du `CNAME` : `www.lasolinapizza.fr`).

---

## 1. Structure des fichiers

```
/
├── assets/
│   └── blog.css                        ← style du blog (reprend la charte du site)
├── blog/
│   ├── index.html                      ← liste des articles
│   └── <slug>/
│       └── index.html                  ← un article = un dossier + index.html
├── sitemap.xml
├── robots.txt
├── rss.xml
├── llms.txt
└── BLOG_WORKFLOW.md
```

Règle : **un article = un dossier en `kebab-case` + un `index.html`**.
L'URL finit toujours par un slash : `/blog/mon-article/`.
Ne jamais renommer un slug déjà publié (cela casse les liens et l'indexation) ; si c'est indispensable, garder l'ancien dossier avec une redirection `<meta http-equiv="refresh">` + `canonical` vers le nouveau, comme le fait déjà `carte.html`.

---

## 2. Publier un nouvel article — checklist

1. **Créer le dossier** `blog/<slug>/` et copier le `index.html` d'un article existant comme gabarit.
2. **`<title>`** : 55–60 caractères, mot-clé principal + `| La Solina`.
3. **`<meta name="description">`** : **moins de 155 caractères**, contient le mot-clé et une ville.
4. **`<link rel="canonical">`** : `https://www.lasolinapizza.fr/blog/<slug>/` — toujours avec `www.` et le slash final.
5. **Open Graph + Twitter Card** : titre, description, `og:url`, `og:image` (image existante du repo, ex. `/images/photohero.jpeg`).
6. **JSON-LD** : trois blocs à mettre à jour — `Article`, `BreadcrumbList`, `FAQPage`.
   - `datePublished` / `dateModified` au format `AAAA-MM-JJ`.
   - Les questions du `FAQPage` doivent être **strictement identiques** à celles affichées dans le HTML (sinon pénalité Google).
7. **Contenu** : 1200–1500 mots, un seul `<h1>`, des `<h2>`/`<h3>` structurants, ancrage local (Tarbes, Séméac, Orleix, Horgues, Adé, Lourdes, Hautes-Pyrénées).
8. **Maillage interne** : au moins 2 liens vers `/#distributeurs`, `/#carte` ou `/#faq`, plus 1 lien vers un autre article quand il en existe.
9. **Ajouter la carte de l'article** dans `blog/index.html` (bloc `<article class="post-card">`), la plus récente en premier.
10. **Ajouter l'article** dans `blog/index.html` → JSON-LD `Blog.blogPost`.
11. **Ajouter l'URL** dans `sitemap.xml` (`lastmod` = date du jour) et mettre à jour le `lastmod` de `/blog/`.
12. **Ajouter un `<item>`** en haut de `rss.xml` et mettre à jour `lastBuildDate`.
13. **Ajouter la ligne** dans la section « Blog » de `llms.txt`.
14. **Commit** atomique (`Blog : <titre de l'article>`) puis `git push origin main`.
15. **Après mise en ligne** : soumettre l'URL dans Google Search Console et Bing Webmaster Tools.

---

## 3. Règles éditoriales — à ne jamais enfreindre

- **Aucune invention.** Pas de prix, de chiffres de fréquentation, de noms de clients, de dates de fondation, de labels ou de références réglementaires qui ne figurent pas déjà sur le site ou qui ne sont pas confirmés par La Solina.
- Les seuls chiffres validés et réutilisables : **≈ 3 min 30** pour une pizza chaude, **≈ 30 s** pour une pizza froide, **6 distributeurs**, **24h/24 et 7j/7**.
- Les prix sont maintenus **uniquement** dans la carte de `index.html`. Un article ne cite jamais de prix : il renvoie vers `/#carte`.
- Pas de comparaison nominative avec un concurrent local.
- Vocabulaire constant : « pizzas artisanales », « pâte maison », « produits frais », « préparées à la main le matin », « distributeur automatique ». Jamais « surgelé » ni « industriel » autrement que pour dire ce que La Solina ne fait pas.
- Ton : direct, concret, utile. On explique un fonctionnement, on ne vend pas à coups de superlatifs.

---

## 4. NAP — bloc de référence (à recopier tel quel)

```
La Solina
15bis Bd du Général de Lattre de Tassigny
65000 Tarbes
Tél. : 05 62 51 70 17  →  tel:+33562517017
Distributeurs accessibles 24h/24, 7j/7
```

Ce bloc doit rester **identique au caractère près** sur : le pied de page du blog, `llms.txt`, le JSON-LD `PizzaRestaurant` de `index.html`, et toutes les fiches externes (Google Business Profile, Apple Business Connect, Bing Places, Pages Jaunes, Facebook, Instagram). Toute modification d'adresse ou de téléphone doit être propagée partout **en même temps**.

Adresses des distributeurs (source unique de vérité : `index.html`, section `#distributeurs`) :

| Commune | Adresse | CP |
|---|---|---|
| Tarbes | 15bis Bd du Général de Lattre de Tassigny | 65000 |
| Tarbes | 155 Avenue Alsace Lorraine | 65000 |
| Séméac | 111 Av. des Sports | 65600 |
| Orleix | 11 Route de Rabastens | 65800 |
| Horgues | 21 Rue du Pic du Midi | 65310 |
| Adé | 3 Av. des Pyrénées | 65100 |
| Lourdes | 4 Rue Lucien Pourxet | 65100 |

> Point de vigilance : le site public affiche le **05 62 51 70 17**, tandis que les mentions légales affichent le **06 69 55 51 10**. Le blog et le `llms.txt` reprennent le numéro du site public. À trancher avec le client pour aligner les deux.

---

## 5. GEO — être cité par les IA génératives

Le blog est optimisé pour les moteurs de réponse autant que pour Google.

- `robots.txt` autorise explicitement : Googlebot, Bingbot, Applebot, GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-User, Claude-SearchBot, PerplexityBot, Perplexity-User, Google-Extended, Applebot-Extended, CCBot, MistralAI-User, Meta-ExternalAgent, Amazonbot, Bytespider.
- `llms.txt` résume l'entreprise, les emplacements, les horaires et les moyens de paiement en texte brut structuré : c'est le fichier que les IA lisent en priorité. **À mettre à jour dès qu'un distributeur est ajouté ou déplacé.**
- Ce qui se fait citer par une IA : des réponses courtes, factuelles et autonomes. D'où la structure « une question `<h3>` → un paragraphe qui répond entièrement » et le bloc FAQ en fin d'article.
- Chaque article doit pouvoir répondre seul à une question du type « où acheter une pizza la nuit à Tarbes ? » sans que le lecteur ait à consulter une autre page.

---

## 6. Cadence recommandée

1 à 2 articles par mois. Mieux vaut un article utile par mois que quatre articles creux.
Tous les 6 mois : relire les articles publiés, mettre à jour les faits qui ont bougé (adresses, moyens de paiement), et actualiser `dateModified` dans le JSON-LD.

---

## 7. Sujets d'articles suggérés

Tous ancrés local + métier, et tous rédigeables **sans inventer** la moindre donnée.

1. **Où trouver une pizza à Tarbes en pleine nuit ? Le guide des distributeurs 24h/24** — ✅ publié le 14/08/2026 (`pizza-nuit-tarbes-distributeur-24h`).
2. **Distributeur de pizzas : comment ça marche vraiment, étape par étape** — chambre froide, écran, four intégré, chaud/froid. Cible la requête « distributeur pizza comment ça marche ».
3. **Pizza chaude ou pizza froide au distributeur : laquelle choisir ?** — arbitrage selon le temps de trajet, le nombre de convives, l'heure. Sujet très « réponse IA ».
4. **Pâte maison : pourquoi le temps de repos change tout** — article métier pur, pédagogie sur le travail du matin, sans chiffre inventé.
5. **Séméac, Orleix, Horgues : le guide des distributeurs de la couronne tarbaise** — page locale dédiée aux communes hors Tarbes, fort potentiel « pizza + nom de commune ».
6. **Lourdes et Adé : manger une pizza artisanale hors des sentiers touristiques** — angle local spécifique au secteur lourdais.
7. **Soirée match, soirée jeux, soirée film : organiser un dîner pizza sans stress** — article d'usage, maillage naturel vers la carte.
8. **Pourquoi nos distributeurs n'acceptent pas les espèces** — sujet court, transparent, répond à une objection réelle des clients.
9. **« Indisponible » sur l'écran : ce que ça veut dire et quoi faire** — gestion d'attente client, ton honnête, très bien perçu.
10. **Halal, végétarien, sans viande : s'y retrouver dans notre carte** — s'appuie strictement sur les mentions déjà présentes dans la carte du site.
11. **Une journée à La Solina : du pétrissage au distributeur** — coulisses, storytelling métier, excellent support photo pour les réseaux.
12. **Réchauffer une pizza sans la rater : four, poêle, air fryer** — article pratique à fort potentiel de partage, complémentaire de l'option « pizza froide ».
13. **Comment les distributeurs de pizzas sont approvisionnés à Tarbes** — Découvrez le processus logistique derrière nos distributeurs dans le bassin tarbais
14. **Les meilleurs emplacements de distributeurs de pizzas à Aureilhan** — Un guide pour trouver facilement nos distributeurs dans la ville d'Aureilhan
15. **Quels ingrédients locaux sont utilisés dans nos pizzas artisanales ?** — Explorez notre engagement envers les produits frais et locaux dans les Hautes-Pyrénées
16. **Comment la météo influence la consommation de pizzas à Tarbes** — Analyse des tendances de consommation selon les saisons dans la région tarbaise
17. **Ibos : découvrir nos distributeurs de pizzas en famille** — Profitez d'une sortie en famille pour déguster nos pizzas artisanales à Ibos
18. **Comment nos distributeurs de pizzas s'adaptent aux normes sanitaires** — Les mesures prises pour garantir la sécurité alimentaire dans nos distributeurs de Tarbes
19. **Les nouveautés sur notre carte de pizzas artisanales à Tarbes** — Présentation des nouvelles saveurs disponibles dans nos distributeurs du bassin tarbais
20. **Pourquoi choisir une pizza artisanale plutôt qu'une pizza surgelée ?** — Comparaison des avantages des pizzas artisanales de nos distributeurs dans les Hautes-Pyrénées
21. **Comment nos distributeurs de pizzas contribuent à l'économie locale** — Impact économique des distributeurs de pizzas à Tarbes et ses environs
22. **L'histoire de la pizza artisanale dans le bassin tarbais** — Retour sur l'évolution de la pizza artisanale dans notre région
23. **Les avis des clients sur nos distributeurs de pizzas à Horgues** — Recueillir les expériences des clients avec nos distributeurs à Horgues
24. **Comment nos pizzas artisanales respectent les régimes alimentaires** — Options disponibles pour différents régimes alimentaires dans nos distributeurs à Tarbes
25. **Les défis de l'installation d'un distributeur de pizzas à Lourdes** — Les obstacles et solutions lors de l'implantation d'un distributeur de pizzas à Lourdes
26. **Comment choisir la pizza parfaite selon vos goûts à Tarbes** — Guide pour sélectionner la pizza idéale parmi notre offre variée dans le bassin tarbais
27. **Les bienfaits de la pâte maison dans nos pizzas à Orleix** — Pourquoi notre pâte maison fait toute la différence en termes de saveur et de texture
28. **Comment nos distributeurs de pizzas s'intègrent dans le paysage urbain** — L'impact esthétique et fonctionnel des distributeurs de pizzas à Tarbes
29. **Les retours d'expérience des premiers utilisateurs de nos distributeurs à Adé** — Découvrez ce que pensent nos clients des distributeurs à Adé
30. **Nos pizzas artisanales : de la conception à la dégustation** — Un aperçu du processus créatif derrière nos recettes de pizzas à Tarbes
31. **Comprendre l'impact écologique de nos distributeurs de pizzas** — Les initiatives prises pour réduire notre empreinte carbone dans le bassin tarbais
32. **Les secrets d'une garniture parfaite pour nos pizzas à Barbazan-Debat** — Comment nous sélectionnons et préparons les garnitures pour nos pizzas artisanales
33. **Les avantages d'une pizza artisanale pour une pause déjeuner rapide** — Pourquoi nos pizzas sont idéales pour un déjeuner sur le pouce à Tarbes
34. **Comment nos pizzas artisanales s'adaptent aux tendances culinaires** — Exploration des influences culinaires actuelles dans nos recettes de pizzas à Tarbes
35. **Les avis sur nos distributeurs de pizzas à Séméac** — Ce que disent les habitants de Séméac sur leur expérience avec nos pizzas
36. **La Solina : notre engagement envers la qualité à chaque étape** — Détails sur nos standards de qualité dans la production de pizzas artisanales
37. **Comment nos distributeurs de pizzas font face aux pannes techniques** — Les solutions mises en place pour assurer un service continu à Tarbes
38. **Les raisons pour lesquelles nos pizzas sont idéales pour un pique-nique** — Les avantages de nos pizzas à emporter pour vos sorties en plein air dans les Hautes-Pyrénées
39. **Comment nous assurons la fraîcheur des ingrédients dans nos pizzas à Tarbes** — Les techniques utilisées pour garantir la qualité des produits dans nos pizzas
40. **Les spécificités des distributeurs de pizzas en zone rurale autour de Tarbes** — Comment nos distributeurs s'adaptent aux besoins des communes rurales du bassin tarbais
41. **Les meilleures pizzas artisanales pour un déjeuner d'affaires à Tarbes** — Sélection de nos pizzas les plus appréciées pour une pause déjeuner professionnelle
42. **Comment nos distributeurs de pizzas s'alignent sur les attentes des jeunes** — Les préférences des jeunes consommateurs et notre réponse à Tarbes
43. **Les astuces pour bien conserver une pizza artisanale chez soi** — Conseils pour garantir la fraîcheur de nos pizzas une fois ramenées à la maison
44. **Explorer les saveurs italiennes dans nos pizzas à Orleix** — Un tour d'horizon des inspirations italiennes dans nos recettes artisanales
45. **Le rôle des distributeurs automatiques dans la restauration moderne à Tarbes** — Analyse de l'impact des distributeurs sur le paysage culinaire local
46. **Comment nos distributeurs aident à réduire le gaspillage alimentaire** — Initiatives mises en place pour limiter le gaspillage dans nos points de vente à Tarbes
47. **Les préférences de nos clients en matière de pizzas artisanales à Ibos** — Un aperçu des choix les plus populaires parmi notre clientèle d'Ibos
48. **Les défis de la fabrication artisanale de pizzas 24h/24** — Comment nous surmontons les défis de la production continue à Tarbes
49. **Pourquoi nos pizzas sont parfaites pour un dîner romantique à la maison** — Les raisons pour lesquelles nos pizzas artisanales s'adaptent aux dîners en tête-à-tête
50. **Les innovations technologiques dans nos distributeurs de pizzas** — Présentation des technologies utilisées pour améliorer l'expérience client à Tarbes
51. **Comment nos distributeurs de pizzas soutiennent les producteurs locaux** — Partenariats avec les agriculteurs et fournisseurs locaux dans les Hautes-Pyrénées
52. **Les critères pour choisir un bon emplacement de distributeur à Tarbes** — Facteurs considérés lors de la sélection des sites pour nos distributeurs de pizzas

---

## 8. Vérifications avant chaque push

```bash
# Toutes les meta description font-elles moins de 155 caractères ?
grep -rho 'name="description"[^>]*' --include="*.html" . | wc -c

# Aucun lien ou canonical vers la forme sans www ?
grep -rn "https://lasolinapizza.fr" --include="*.html" --include="*.xml" --include="*.txt" .

# Le JSON-LD est-il valide ?
# → https://validator.schema.org/ et https://search.google.com/test/rich-results
```
