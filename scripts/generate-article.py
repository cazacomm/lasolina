#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génération automatique d'un article de blog — La Solina.

Le script :
  1. lit blog-config.json ;
  2. extrait de BLOG_WORKFLOW.md la liste des sujets suggérés et les règles éditoriales ;
  3. scanne /blog/*/index.html pour savoir quels sujets sont déjà traités ;
  4. choisit le prochain sujet non traité (ordre séquentiel) ;
  5. relit l'article de référence pour s'en servir de gabarit HTML ;
  6. appelle l'API OpenAI pour rédiger l'article ;
  7. valide le HTML produit, puis écrit /blog/<slug>/index.html ;
  8. met à jour blog/index.html, sitemap.xml, rss.xml et llms.txt.

Codes de sortie :
   0  succès
   1  erreur (rien n'a été écrit)
  78  aucun nouveau sujet à traiter (EX_CONFIG — arrêt propre)

Options :
  --dry-run   n'écrit aucun fichier, affiche le résultat
  --mock      n'appelle pas l'API (contenu de démonstration) — pour tester la tuyauterie
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "blog-config.json"
WORKFLOW_PATH = ROOT / "BLOG_WORKFLOW.md"
BLOG_DIR = ROOT / "blog"
BLOG_INDEX = BLOG_DIR / "index.html"
SITEMAP = ROOT / "sitemap.xml"
RSS = ROOT / "rss.xml"
LLMS = ROOT / "llms.txt"

EXIT_OK, EXIT_ERROR, EXIT_NOTHING_TODO = 0, 1, 78

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Mots vides écartés de la construction des slugs.
STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "et", "ou", "a", "au",
    "aux", "en", "dans", "sur", "pour", "par", "avec", "sans", "que", "qui", "quoi",
    "ce", "cet", "cette", "ces", "se", "sa", "son", "ses", "nos", "notre", "votre",
    "vos", "est", "ne", "pas", "plus", "tout", "tous", "toute", "toutes", "y", "il",
    "elle", "on", "vraiment", "bien",
}


# ─────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[blog] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[blog][ERREUR] {msg}", file=sys.stderr, flush=True)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def slugify(title: str, max_words: int = 7) -> str:
    """Slug déterministe : même titre => même slug (garantit l'idempotence)."""
    text = strip_accents(title.lower())
    text = text.replace("'", " ").replace("’", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    words = [w for w in text.split() if w and w not in STOPWORDS]
    if not words:
        words = [w for w in text.split() if w]
    return "-".join(words[:max_words])


def word_count(html: str) -> int:
    body = html
    m = re.search(r"<main>(.*?)</main>", html, re.S)
    if m:
        body = m.group(1)
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    return len(re.sub(r"<[^>]+>", " ", body).split())


def fr_date(d: dt.date) -> str:
    return f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}"


def rfc822(d: dt.date, hour: str = "09:00:00") -> str:
    return f"{DAYS_EN[d.weekday()]}, {d.day:02d} {MONTHS_EN[d.month - 1]} {d.year} {hour} +0200"


# ─────────────────────────────────────────────────────────────
# Lecture de la configuration et du workflow
# ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration introuvable : {CONFIG_PATH}")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for key in ("site_name", "site_url", "sector", "location", "author"):
        if not cfg.get(key):
            raise ValueError(f"Clé manquante ou vide dans blog-config.json : {key}")
    cfg["site_url"] = cfg["site_url"].rstrip("/")
    return cfg


def parse_topics(workflow: str) -> list[dict]:
    """Extrait les sujets numérotés de la section « sujets d'articles suggérés »."""
    section = re.split(r"^##\s+\d+\.\s+.*sujets d'articles suggérés.*$",
                       workflow, flags=re.M | re.I)
    if len(section) < 2:
        raise ValueError("Section des sujets suggérés introuvable dans BLOG_WORKFLOW.md")
    block = re.split(r"^##\s", section[1], flags=re.M)[0]

    topics: list[dict] = []
    for num, line in re.findall(r"^(\d+)\.\s+(.*)$", block, flags=re.M):
        title_m = re.search(r"\*\*(.+?)\*\*", line)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        rest = line[title_m.end():].lstrip(" —-–").strip()
        published_m = re.search(r"`([a-z0-9\-]+)`", line)
        topics.append({
            "num": int(num),
            "title": title,
            "brief": re.sub(r"[`*✅]", "", rest).strip(),
            "declared_slug": published_m.group(1) if published_m else None,
            "declared_published": "publié" in line.lower(),
        })
    if not topics:
        raise ValueError("Aucun sujet exploitable trouvé dans BLOG_WORKFLOW.md")
    topics.sort(key=lambda t: t["num"])
    return topics


def parse_editorial_rules(workflow: str) -> str:
    """Récupère la section « Règles éditoriales » pour l'injecter dans le prompt."""
    m = re.search(r"^##\s+\d+\.\s+Règles éditoriales.*?$(.*?)^##\s",
                  workflow, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


# ─────────────────────────────────────────────────────────────
# État du blog
# ─────────────────────────────────────────────────────────────

def scan_blog(marker_prefix: str) -> tuple[set[int], set[str]]:
    """Retourne (numéros de sujets déjà traités, slugs existants)."""
    done_nums: set[int] = set()
    slugs: set[str] = set()
    if not BLOG_DIR.exists():
        return done_nums, slugs
    for path in sorted(BLOG_DIR.glob("*/index.html")):
        slug = path.parent.name
        slugs.add(slug)
        html = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"<!--\s*{re.escape(marker_prefix)}:\s*(\d+)\s*-->", html)
        if m:
            done_nums.add(int(m.group(1)))
    return done_nums, slugs


def pick_topic(topics: list[dict], done_nums: set[int], slugs: set[str]) -> dict | None:
    """Premier sujet non traité, dans l'ordre de la liste."""
    for topic in topics:
        if topic["num"] in done_nums:
            continue
        # Sujet déclaré publié dans BLOG_WORKFLOW.md avec un slug existant.
        if topic["declared_slug"] and topic["declared_slug"] in slugs:
            continue
        slug = slugify(topic["title"])
        if slug in slugs:
            # Le dossier existe déjà : on considère le sujet traité (idempotence).
            continue
        topic["slug"] = slug
        return topic
    return None


def load_reference_article(cfg: dict, slugs: set[str]) -> tuple[str, str]:
    """Relit un article existant : il sert de gabarit (jamais de template en dur)."""
    preferred = cfg.get("reference_article_slug")
    candidates = [preferred] if preferred in slugs else []
    candidates += sorted(s for s in slugs if s != preferred)
    for slug in candidates:
        path = BLOG_DIR / slug / "index.html"
        if path.exists():
            return slug, path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "Aucun article de référence dans /blog/ : impossible de déduire le gabarit.")


# ─────────────────────────────────────────────────────────────
# Génération
# ─────────────────────────────────────────────────────────────

def build_prompt(cfg: dict, topic: dict, reference_html: str,
                 rules: str, today: dict) -> tuple[str, str]:
    marker = f"<!-- {cfg['topic_marker_prefix']}: {topic['num']} -->"
    url = f"{cfg['site_url']}/blog/{topic['slug']}/"

    system = (
        "Tu es rédacteur SEO/GEO senior pour une entreprise locale française. "
        "Tu produis du HTML complet, valide et prêt à publier. "
        "Tu ne renvoies JAMAIS de bloc de code markdown, JAMAIS de commentaire hors HTML : "
        "ta réponse commence par <!DOCTYPE html> et se termine par </html>."
    )

    user = f"""Rédige un nouvel article pour le blog de {cfg['site_name']}.

# GABARIT DE RÉFÉRENCE
Voici, entre les balises <GABARIT>, un article DÉJÀ PUBLIÉ sur ce blog.
Tu dois reproduire EXACTEMENT sa structure : même ordre des balises <head>, mêmes
blocs JSON-LD (Article, BreadcrumbList, FAQPage), même header, même <footer>,
mêmes classes CSS (blog-hero, article, article-wrap, article-lead, article-meta,
callout, spots, faq-block, faq-q, faq-a, article-cta, breadcrumb), même script
de fin de page. Seul le CONTENU change.

<GABARIT>
{reference_html}
</GABARIT>

# SUJET À TRAITER (sujet n°{topic['num']})
Titre de travail : {topic['title']}
Angle : {topic['brief'] or "à développer librement dans le cadre des règles ci-dessous"}

# PARAMÈTRES OBLIGATOIRES
- URL canonique : {url}
- Slug (ne pas changer) : {topic['slug']}
- Date de publication et de modification : {today['iso']}
- Date affichée dans .article-meta : « Publié le {today['fr']} »
- Ancre du fil d'Ariane (3e niveau) : un libellé court tiré du sujet
- og:image et twitter:image : {cfg['site_url']}{cfg['og_image']}
- Longueur : {cfg['target_word_count']} mots environ (entre 1200 et 1500 mots de contenu réel)
- FAQ : exactement {cfg['faq_questions_count']} questions, en fin d'article, dans un
  bloc .faq-block ET reprises À L'IDENTIQUE dans le JSON-LD FAQPage
- Structure : un seul <h1>, plusieurs <h2>, des <h3> à l'intérieur des <h2>
- Le <title> fait 55 à 60 caractères et se termine par « | {cfg['site_name']} »
- La meta description fait STRICTEMENT MOINS DE 155 caractères
- Insère ce commentaire tel quel, juste après la balise <body> :
  {marker}
- Maillage interne : au moins deux liens vers /#distributeurs, /#carte ou /#faq,
  et un lien vers /blog/ ; pas de lien externe autre que ceux déjà dans le gabarit
- Ton : {cfg['tone']}
- Langue : français ({cfg['language']})

# ANCRAGE LOCAL
Secteur : {cfg['sector']}.
Zone : {cfg['location']}.
Mots-clés géographiques à faire vivre naturellement dans le texte (pas de bourrage) :
{', '.join(cfg['geo_keywords'])}.

# RÈGLES ÉDITORIALES — NON NÉGOCIABLES
{rules}

Rappel critique : n'invente AUCUN prix, AUCUN chiffre d'affaires ou de fréquentation,
AUCUN nom de client, AUCUNE date de fondation, AUCUNE norme ou réglementation, AUCUN
label, AUCUN avis client, AUCUN horaire autre que ceux du gabarit. Si une information
te manque, reformule pour t'en passer. Tu peux uniquement réutiliser les faits déjà
présents dans le gabarit de référence.

Renvoie UNIQUEMENT le fichier HTML complet du nouvel article."""

    return system, user


def generate_html(cfg: dict, system: str, user: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Le paquet 'openai' n'est pas installé (pip install openai).") from exc

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Variable d'environnement OPENAI_API_KEY absente.")

    client = OpenAI()
    log(f"Appel OpenAI (modèle {cfg['model']}, temperature {cfg['temperature']})…")
    response = client.chat.completions.create(
        model=cfg["model"],
        temperature=cfg["temperature"],
        max_tokens=9000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    usage = getattr(response, "usage", None)
    if usage:
        log(f"Tokens : {usage.prompt_tokens} entrée + "
            f"{usage.completion_tokens} sortie = {usage.total_tokens}")
    return content


def mock_html(cfg: dict, topic: dict, reference_html: str, today: dict) -> str:
    """Rendu de démonstration hors ligne : reprend le gabarit, remplace le contenu.

    Sert uniquement à tester la tuyauterie sans clé API (--mock).
    Le texte produit n'a aucune valeur éditoriale.
    """
    marker = f"<!-- {cfg['topic_marker_prefix']}: {topic['num']} -->"
    url = f"{cfg['site_url']}/blog/{topic['slug']}/"
    title = topic["title"]
    short = title.split(":")[0].strip()
    desc = (f"{short} : le guide {cfg['site_name']} pour "
            f"{cfg['location'].split(',')[0]} et les environs.")[:154]

    html = reference_html
    html = re.sub(r"<title>.*?</title>",
                  f"<title>{short} | {cfg['site_name']}</title>", html, flags=re.S)
    html = re.sub(r'(<meta name="description"\s*\n?\s*content=")[^"]*(")',
                  rf"\g<1>{desc}\g<2>", html)
    html = html.replace(
        f"{cfg['site_url']}/blog/{cfg['reference_article_slug']}/", url)
    html = re.sub(r'(<meta property="article:published_time" content=")[^"]*(")',
                  rf"\g<1>{today['iso']}\g<2>", html)
    html = re.sub(r'(<meta property="article:modified_time" content=")[^"]*(")',
                  rf"\g<1>{today['iso']}\g<2>", html)
    html = re.sub(r'("datePublished":\s*")[^"]*(")', rf"\g<1>{today['iso']}\g<2>", html)
    html = re.sub(r'("dateModified":\s*")[^"]*(")', rf"\g<1>{today['iso']}\g<2>", html)
    html = re.sub(r'("headline":\s*")[^"]*(")',
                  rf"\g<1>{title.replace(chr(34), '')}\g<2>", html)
    html = re.sub(r"<h1>.*?</h1>", f"<h1>{short.upper()}</h1>", html, flags=re.S)
    html = re.sub(r'(<p class="article-meta">)[^<]*(</p>)',
                  rf"\g<1>Publié le {today['fr']} · Distributeurs · Lecture 6 min\g<2>",
                  html)
    html = html.replace("<body>", f"<body>\n{marker}", 1)
    return html


# ─────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────

def clean_output(raw: str) -> str:
    """Retire un éventuel encadrement markdown et tout préambule."""
    text = raw.strip()
    fence = re.match(r"^```[a-zA-Z]*\s*\n(.*?)\n?```$", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.lower().find("<!doctype html")
    if start > 0:
        text = text[start:]
    return text.strip()


def validate(html: str, cfg: dict, topic: dict) -> list[str]:
    """Contrôles bloquants : si la liste retournée n'est pas vide, on n'écrit rien."""
    errors: list[str] = []
    url = f"{cfg['site_url']}/blog/{topic['slug']}/"
    marker = f"{cfg['topic_marker_prefix']}: {topic['num']}"

    if not html.lower().startswith("<!doctype html"):
        errors.append("le document ne commence pas par <!DOCTYPE html>")
    if not html.rstrip().endswith("</html>"):
        errors.append("le document ne se termine pas par </html>")
    if marker not in html:
        errors.append(f"marqueur d'idempotence absent ({marker})")
    if html.count("<h1") != 1:
        errors.append(f"il faut exactement un <h1> (trouvé : {html.count('<h1')})")
    if f'rel="canonical" href="{url}"' not in html:
        errors.append(f"canonical incorrect ou absent (attendu {url})")
    if 'property="og:title"' not in html or 'name="twitter:card"' not in html:
        errors.append("balises Open Graph / Twitter Card incomplètes")
    if '/assets/blog.css' not in html:
        errors.append("feuille de style /assets/blog.css non liée")

    desc = re.search(r'<meta name="description"\s*\n?\s*content="([^"]*)"', html)
    if not desc:
        errors.append("meta description absente")
    elif len(desc.group(1)) >= 155:
        errors.append(f"meta description trop longue ({len(desc.group(1))} caractères)")

    title = re.search(r"<title>(.*?)</title>", html, re.S)
    if not title or not title.group(1).strip():
        errors.append("balise <title> absente ou vide")

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if len(blocks) < 3:
        errors.append(f"il faut 3 blocs JSON-LD (trouvé : {len(blocks)})")
    types = []
    for i, block in enumerate(blocks):
        try:
            types.append(json.loads(block).get("@type"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON-LD n°{i + 1} invalide : {exc}")
    for expected in ("Article", "BreadcrumbList", "FAQPage"):
        if expected not in types:
            errors.append(f"JSON-LD manquant : {expected}")

    faq_html = len(re.findall(r'class="faq-q"', html))
    if faq_html != cfg["faq_questions_count"]:
        errors.append(f"{cfg['faq_questions_count']} questions attendues dans la FAQ "
                      f"(trouvé : {faq_html})")

    wc = word_count(html)
    if not 1000 <= wc <= 1900:
        errors.append(f"volume hors bornes : {wc} mots")

    return errors


def extract(html: str) -> dict:
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description"\s*\n?\s*content="([^"]*)"', html)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    lead = re.search(r'<p class="article-lead">(.*?)</p>', html, re.S)
    headline = re.search(r'"headline":\s*"([^"]*)"', html)
    return {
        "title": (title.group(1).strip() if title else ""),
        "description": (desc.group(1).strip() if desc else ""),
        "h1": re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else "",
        "lead": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lead.group(1))).strip() if lead else "",
        "headline": (headline.group(1).strip() if headline else ""),
        "words": word_count(html),
    }


# ─────────────────────────────────────────────────────────────
# Mises à jour des fichiers annexes
# ─────────────────────────────────────────────────────────────

def update_blog_index(cfg: dict, topic: dict, meta: dict, today: dict) -> str:
    html = BLOG_INDEX.read_text(encoding="utf-8")
    url = f"/blog/{topic['slug']}/"
    if url in html:
        log("blog/index.html contient déjà cet article : pas de doublon ajouté.")
        return html

    headline = meta["headline"] or meta["h1"] or topic["title"]
    teaser = meta["lead"] or meta["description"]
    if len(teaser) > 320:
        teaser = teaser[:317].rsplit(" ", 1)[0] + "…"

    card = f"""
        <article class="post-card">
          <div class="thumb" style="background-image:url('{cfg['og_image']}')" role="img" aria-label="{cfg['site_name']}"></div>
          <div class="body">
            <p class="meta">{today['fr']} · Blog</p>
            <h2><a href="{url}">{headline}</a></h2>
            <p>{teaser}</p>
            <a class="more" href="{url}">Lire l’article ➜</a>
          </div>
        </article>
"""
    anchor = '<div class="post-grid">'
    if anchor not in html:
        raise ValueError("Point d'insertion .post-grid introuvable dans blog/index.html")
    html = html.replace(anchor, anchor + card, 1)

    entry = f"""
    {{
      "@type": "BlogPosting",
      "headline": "{headline.replace('"', "'")}",
      "url": "{cfg['site_url']}{url}",
      "datePublished": "{today['iso']}",
      "author": {{ "@type": "Organization", "name": "{cfg['author']}" }}
    }},"""
    ld_anchor = '"blogPost": ['
    if ld_anchor in html:
        html = html.replace(ld_anchor, ld_anchor + entry, 1)
    else:
        log("Avertissement : tableau blogPost introuvable, JSON-LD de l'index inchangé.")
    return html


def update_sitemap(cfg: dict, topic: dict, today: dict) -> str:
    xml = SITEMAP.read_text(encoding="utf-8")
    loc = f"{cfg['site_url']}/blog/{topic['slug']}/"
    if loc in xml:
        log("sitemap.xml contient déjà cette URL.")
        return xml

    xml = re.sub(
        rf"(<loc>{re.escape(cfg['site_url'])}/blog/</loc>\s*<lastmod>)[^<]*(</lastmod>)",
        rf"\g<1>{today['iso']}\g<2>", xml)

    entry = f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{today['iso']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>"""
    return xml.replace("</urlset>", entry, 1)


def update_rss(cfg: dict, topic: dict, meta: dict, today: dict) -> str:
    xml = RSS.read_text(encoding="utf-8")
    link = f"{cfg['site_url']}/blog/{topic['slug']}/"
    if link in xml:
        log("rss.xml contient déjà cet article.")
        return xml

    def esc(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    headline = meta["headline"] or meta["h1"] or topic["title"]
    teaser = meta["lead"] or meta["description"]
    pub = rfc822(today["date"])

    xml = re.sub(r"<lastBuildDate>[^<]*</lastBuildDate>",
                 f"<lastBuildDate>{pub}</lastBuildDate>", xml, count=1)

    item = f"""    <item>
      <title>{esc(headline)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{pub}</pubDate>
      <category>Blog</category>
      <description>{esc(teaser)}</description>
    </item>

"""
    if "<item>" in xml:
        idx = xml.index("    <item>")
        return xml[:idx] + item + xml[idx:]
    return xml.replace("  </channel>", item + "  </channel>", 1)


def update_llms(cfg: dict, topic: dict, meta: dict) -> str | None:
    if not LLMS.exists():
        return None
    text = LLMS.read_text(encoding="utf-8")
    url = f"{cfg['site_url']}/blog/{topic['slug']}/"
    if url in text:
        log("llms.txt référence déjà cet article.")
        return text
    headline = meta["headline"] or meta["h1"] or topic["title"]
    summary = (meta["description"] or "").rstrip(".")
    line = f"- [{headline}]({url}) : {summary}.\n"
    m = re.search(r"^## Blog\s*$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    if not m:
        log("Avertissement : section « ## Blog » introuvable dans llms.txt.")
        return text
    block = m.group(1).rstrip("\n")
    return text[:m.start(1)] + block + "\n" + line + "\n" + text[m.end(1):]


# ─────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Génère un article de blog La Solina.")
    parser.add_argument("--dry-run", action="store_true",
                        help="n'écrit aucun fichier, affiche le résultat")
    parser.add_argument("--mock", action="store_true",
                        help="n'appelle pas l'API OpenAI (contenu de démonstration)")
    args = parser.parse_args()

    if args.dry_run:
        log("Mode DRY-RUN : aucun fichier ne sera écrit.")

    try:
        cfg = load_config()
        log(f"Site : {cfg['site_name']} — {cfg['site_url']}")

        if not WORKFLOW_PATH.exists():
            fail(f"BLOG_WORKFLOW.md introuvable ({WORKFLOW_PATH}).")
            return EXIT_ERROR
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        topics = parse_topics(workflow)
        rules = parse_editorial_rules(workflow)
        log(f"{len(topics)} sujets listés dans BLOG_WORKFLOW.md.")
        if not rules:
            log("Avertissement : règles éditoriales non trouvées, prompt allégé.")

        done, slugs = scan_blog(cfg["topic_marker_prefix"])
        log(f"Articles déjà en ligne : {len(slugs)} — sujets marqués traités : "
            f"{sorted(done) if done else 'aucun'}")

        topic = pick_topic(topics, done, slugs)
        if topic is None:
            log("Aucun sujet restant à traiter. Ajoutez des sujets dans "
                "BLOG_WORKFLOW.md (section « sujets d'articles suggérés »).")
            return EXIT_NOTHING_TODO

        log(f"Sujet retenu : n°{topic['num']} — {topic['title']}")
        log(f"Slug : {topic['slug']}")

        target_dir = BLOG_DIR / topic["slug"]
        target_file = target_dir / "index.html"
        if target_file.exists():
            fail(f"Le fichier existe déjà : {target_file.relative_to(ROOT)} — "
                 "rien n'est écrasé.")
            return EXIT_NOTHING_TODO

        ref_slug, reference_html = load_reference_article(cfg, slugs)
        log(f"Gabarit relu depuis /blog/{ref_slug}/index.html "
            f"({len(reference_html)} caractères).")

        today_date = dt.date.today()
        today = {"date": today_date, "iso": today_date.isoformat(), "fr": fr_date(today_date)}

        if args.mock:
            log("Mode MOCK : contenu de démonstration, aucun appel API.")
            raw = mock_html(cfg, topic, reference_html, today)
        else:
            system, user = build_prompt(cfg, topic, reference_html, rules, today)
            log(f"Prompt construit ({len(user)} caractères).")
            raw = generate_html(cfg, system, user)

        if not raw:
            fail("Réponse vide du générateur.")
            return EXIT_ERROR

        html = clean_output(raw)
        errors = validate(html, cfg, topic)
        if errors:
            fail("Article rejeté par la validation — aucun fichier écrit :")
            for err in errors:
                fail(f"  · {err}")
            return EXIT_ERROR

        meta = extract(html)
        log("Validation OK.")
        log(f"  Titre       : {meta['title']}")
        log(f"  Description : {meta['description']} ({len(meta['description'])} car.)")
        log(f"  Volume      : {meta['words']} mots")

        if args.dry_run:
            print("\n" + "═" * 70)
            print("APERÇU (aucun fichier écrit)")
            print("═" * 70)
            print(f"Sujet       : n°{topic['num']} — {topic['title']}")
            print(f"Slug        : {topic['slug']}")
            print(f"URL         : {cfg['site_url']}/blog/{topic['slug']}/")
            print(f"Titre       : {meta['title']}")
            print(f"H1          : {meta['h1']}")
            print(f"Description : {meta['description']}")
            print(f"Mots        : {meta['words']}")
            print("-" * 70)
            body = re.sub(r"<script.*?</script>", " ",
                          html.split("<main>")[-1].split("</main>")[0], flags=re.S)
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
            print("200 premiers mots :\n")
            print(" ".join(text.split()[:200]))
            print("═" * 70)
            log("DRY-RUN terminé, rien n'a été modifié.")
            return EXIT_OK

        # ── Écriture (au plus tard possible, une fois tout validé) ──
        blog_index_html = update_blog_index(cfg, topic, meta, today)
        sitemap_xml = update_sitemap(cfg, topic, today)
        rss_xml = update_rss(cfg, topic, meta, today)
        llms_txt = update_llms(cfg, topic, meta)

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(html, encoding="utf-8")
        log(f"Écrit : blog/{topic['slug']}/index.html")

        BLOG_INDEX.write_text(blog_index_html, encoding="utf-8")
        log("Mis à jour : blog/index.html")
        SITEMAP.write_text(sitemap_xml, encoding="utf-8")
        log("Mis à jour : sitemap.xml")
        RSS.write_text(rss_xml, encoding="utf-8")
        log("Mis à jour : rss.xml")
        if llms_txt is not None:
            LLMS.write_text(llms_txt, encoding="utf-8")
            log("Mis à jour : llms.txt")

        log(f"Terminé — article n°{topic['num']} publié : "
            f"{cfg['site_url']}/blog/{topic['slug']}/")
        return EXIT_OK

    except Exception as exc:  # noqa: BLE001 — on veut un exit propre quoi qu'il arrive
        fail(f"{type(exc).__name__} : {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
