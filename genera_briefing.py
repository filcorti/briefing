#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERATORE DI BRIEFING GEOPOLITICO QUOTIDIANO v2
=================================================
Fonti organizzate per tema: Ucraina/Russia, Medio Oriente/Hormuz,
Intelligence & Strategia, Think Tank generali.

USO
---
    pip install feedparser anthropic python-dateutil trafilatura requests
    python genera_briefing.py          # briefing di oggi
    python genera_briefing.py --giorni 2   # ultimi 2 giorni
    python genera_briefing.py --esempio    # preview layout, nessuna API
"""

import os, sys, html, datetime, re, time
from dateutil import parser as dateparser

# ------------------------------------------------------------------ #
#  CONFIGURAZIONE FONTI (gruppi tematici)                            #
# ------------------------------------------------------------------ #

GRUPPI = [
    {
        "nome": "🇺🇦 Ucraina / Russia / Spazio post-sovietico",
        "max": 6,
        "fonti": [
            {"nome": "ISW – Institute for the Study of War", "sigla": "ISW",
             "rss": ["https://www.understandingwar.org/rss.xml",
                     "https://understandingwar.org/feed/",
                     "https://www.iswresearch.org/feeds/posts/default?alt=rss"]},
            {"nome": "RUSI", "sigla": "RUSI",
             "rss": ["https://www.rusi.org/rss/latest-commentary.xml",
                     "https://www.rusi.org/rss/latest-publications.xml"]},
            {"nome": "Jamestown – Eurasia Daily Monitor", "sigla": "JAMESTOWN",
             "rss": "https://jamestown.org/feed/"},
            {"nome": "Gian Raffaele Percannella (Telegram COMFOG)", "sigla": "PERCANNELLA",
             "tipo": "telegram", "canale": "comfog",
             "sempre": True},   # mai scartato dalla prioritizzazione
            {"nome": "Carnegie Politika", "sigla": "POLITIKA",
             "rss": ["https://carnegieendowment.org/rss/politika.xml",
                     "https://carnegie.ru/feed",
                     "https://carnegieendowment.org/posts/rss?lang=en&center=russia-eurasia"]},
            {"nome": "Meduza (EN)", "sigla": "MEDUZA",
             "rss": "https://meduza.io/rss/en/all"},
            {"nome": "Kyiv Independent", "sigla": "KYIVIND",
             "rss": "https://kyivindependent.com/news-archive/rss/"},
        ]
    },
    {
        "nome": "🌍 Medio Oriente / Hormuz / Golfo",
        "max": 6,
        "fonti": [
            {"nome": "U.S. Central Command", "sigla": "CENTCOM",
             "rss": ["https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=1076&max=20",
                     "https://www.centcom.mil/RSS/News/"]},
            {"nome": "The Cradle", "sigla": "CRADLE",
             "rss": "https://thecradle.co/feed"},
            {"nome": "MEMRI – Middle East Media Research", "sigla": "MEMRI",
             "rss": "https://www.memri.org/rss/latest"},
            {"nome": "NEST Centre", "sigla": "NEST",
             "rss": "https://nestcentre.org/feed/"},
            {"nome": "Amwaj.media", "sigla": "AMWAJ",
             "rss": "https://amwaj.media/feed.rss"},
            {"nome": "Al-Monitor", "sigla": "ALMONITOR",
             "rss": "https://www.al-monitor.com/rss"},
            {"nome": "Middle East Eye", "sigla": "MEE",
             "rss": "https://www.middleeasteye.net/rss"},
        ]
    },
    {
        "nome": "🔍 Intelligence / OSINT / Spionaggio",
        "max": 5,
        "fonti": [
            {"nome": "Bellingcat", "sigla": "BELLINGCAT",
             "rss": "https://www.bellingcat.com/feed/"},
            {"nome": "Lawfare", "sigla": "LAWFARE",
             "rss": "https://www.lawfaremedia.org/feeds/articles.rss"},
            {"nome": "The Record (cyber-intel)", "sigla": "RECORD",
             "rss": "https://therecord.media/feed"},
            {"nome": "Statewatch", "sigla": "STATEWATCH",
             "rss": "https://www.statewatch.org/rss/"},
        ]
    },
    {
        "nome": "⚔️ Strategia / Dottrina militare",
        "max": 5,
        "fonti": [
            {"nome": "War on the Rocks", "sigla": "WOTR",
             "rss": "https://warontherocks.com/feed/"},
            {"nome": "IISS – International Institute for Strategic Studies", "sigla": "IISS",
             "rss": "https://www.iiss.org/rss"},
            {"nome": "Valdai Club", "sigla": "VALDAI",
             "rss": "https://valdaiclub.com/rss.xml"},
            {"nome": "Geopolitical Futures", "sigla": "GPF",
             "rss": "https://geopoliticalfutures.com/feed/"},
            {"nome": "Inkstick (proliferazione)", "sigla": "INKSTICK",
             "rss": "https://inkstickmedia.com/feed/"},
        ]
    },
    {
        "nome": "🏛️ Think Tank & Analisi generale",
        "max": 5,
        "fonti": [
            {"nome": "Carnegie Endowment", "sigla": "CARNEGIE",
             "rss": ["https://carnegieendowment.org/rss/analysis.xml",
                     "https://carnegieendowment.org/feed",
                     "https://carnegieendowment.org/posts/rss?lang=en"]},
            {"nome": "ISPI", "sigla": "ISPI",
             "rss": "https://www.ispionline.it/it/rss.xml"},
            {"nome": "Limes", "sigla": "LIMES",
             "rss": ["https://www.limesonline.com/feed/",
                     "https://www.limesonline.com/rss",
                     "https://www.limesonline.com/feed/rss"]},
            {"nome": "ECFR", "sigla": "ECFR",
             "rss": "https://ecfr.eu/feed/"},
            {"nome": "Foreign Affairs", "sigla": "FA",
             "rss": "https://www.foreignaffairs.com/rss.xml", "paywall": True},
            {"nome": "Foreign Policy", "sigla": "FP",
             "rss": "https://foreignpolicy.com/feed/", "paywall": True},
        ]
    },
]

GIORNI = 0  # 0 = solo oggi. Cambia con --giorni N

PROMPT_SISTEMA = """Sei un analista geopolitico senior che lavora per un briefing riservato.
Riassumi l'articolo in italiano con un testo denso e tecnico di 3-4 paragrafi.
Non usare elenchi puntati. Usa linguaggio da analisi strategica, non giornalistico.
Includi: contesto, attori chiave, implicazioni operative/strategiche, sviluppi attesi.
Non aggiungere titolo né intestazioni: solo il testo del riassunto."""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ------------------------------------------------------------------ #
#  UTILITÀ                                                           #
# ------------------------------------------------------------------ #

def oggi_utc():
    return datetime.datetime.now(datetime.timezone.utc).date()

def finestra(giorni):
    base = oggi_utc()
    return base - datetime.timedelta(days=giorni)

def normalizza_data(entry):
    """Restituisce un date UTC dall'entry feedparser, o None."""
    for campo in ("published_parsed", "updated_parsed"):
        t = getattr(entry, campo, None)
        if t:
            try:
                return datetime.date(t.tm_year, t.tm_mon, t.tm_mday)
            except Exception:
                pass
    return None

def estrai_testo(url):
    """Scarica il testo dell'articolo con trafilatura; fallback su excerpt RSS."""
    try:
        import trafilatura
        testo = trafilatura.fetch_url(url)
        if testo:
            estratto = trafilatura.extract(testo)
            if estratto and len(estratto) > 200:
                return estratto[:8000]
    except Exception:
        pass
    return None

def riassumi(client, testo, titolo):
    """Chiama l'API Anthropic e restituisce il riassunto."""
    prompt = f"Titolo: {titolo}\n\n---\n\n{testo[:6000]}"
    try:
        risposta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=900,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        return risposta.content[0].text.strip()
    except Exception as e:
        return f"[Errore riassunto: {e}]"

# ------------------------------------------------------------------ #
#  PRIORITIZZAZIONE                                                  #
# ------------------------------------------------------------------ #

PROMPT_TRIAGE = """Sei l'analista che decide cosa entra nel briefing mattutino di un lettore \
esperto di geopolitica. I suoi interessi: guerra in Ucraina, Russia e spazio post-sovietico, \
Stretto di Hormuz e sicurezza energetica del Golfo, intelligence e spionaggio, strategia e \
dottrina militare, diplomazia e negoziati.

Qui sotto ci sono gli articoli candidati per la sezione "{sezione}".
Selezionane al massimo {quanti}, i piu' rilevanti dal punto di vista analitico.

Scarta senza pieta': cronaca ripetitiva, pezzi di opinione generici, contenuti promozionali, \
doppioni della stessa notizia (tieni la versione migliore), articoli fuori tema.
Se meno di {quanti} meritano davvero, selezionane meno. Meglio poco e denso.

Rispondi SOLO con un array JSON, niente backtick, niente testo prima o dopo:
[{{"id": 3, "motivo": "perche' merita, una riga in italiano", "tag": ["Hormuz", "escalation navale"]}}]

CANDIDATI:
{elenco}"""


def _parse_json_array(testo):
    testo = re.sub(r"```(?:json)?", "", testo).strip()
    i, j = testo.find("["), testo.rfind("]")
    if i == -1 or j == -1:
        return []
    try:
        import json
        return json.loads(testo[i:j + 1])
    except Exception:
        return []


def prioritizza(client, nome_sezione, candidati, quanti):
    """candidati = lista di (fonte, articolo). Ritorna la stessa struttura, filtrata.

    Gli articoli da fonti marcate "sempre": True passano sempre, senza consumare
    quota di selezione."""
    fissi = [(f, a) for f, a in candidati if f.get("sempre")]
    for f, a in fissi:
        a["motivo"] = "Fonte in lista fissa."
    valutabili = [(f, a) for f, a in candidati if not f.get("sempre")]

    if not valutabili:
        return fissi
    if len(valutabili) <= quanti:
        return fissi + valutabili

    elenco = "\n\n".join(
        f"[{i}] {a['titolo']}\nFonte: {f['nome']} | {a['data']}\n{(a.get('excerpt') or '')[:450]}"
        for i, (f, a) in enumerate(valutabili)
    )
    prompt = PROMPT_TRIAGE.format(sezione=nome_sezione, quanti=quanti, elenco=elenco)

    try:
        risposta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        scelte = _parse_json_array(risposta.content[0].text)
    except Exception as e:
        print(f"    ⚠ triage fallito ({e}) — tengo i {quanti} piu' recenti")
        return fissi + valutabili[:quanti]

    selezionati = []
    for s in scelte[:quanti]:
        idx = s.get("id")
        if isinstance(idx, int) and 0 <= idx < len(valutabili):
            f, a = valutabili[idx]
            a["motivo"] = s.get("motivo", "")
            a["tag"] = s.get("tag", [])[:4]
            selezionati.append((f, a))

    if not selezionati:
        selezionati = valutabili[:quanti]
    scartati = len(valutabili) - len(selezionati)
    print(f"    ▸ triage: {len(selezionati)} tenuti, {scartati} scartati")
    return fissi + selezionati

# ------------------------------------------------------------------ #
#  FETCH FEED                                                        #
# ------------------------------------------------------------------ #

def _prova_url(sigla, url_rss, data_limite, silenzioso=False):
    """Prova un singolo URL. Ritorna (articoli, esito, dettaglio)."""
    import feedparser, requests

    try:
        r = requests.get(url_rss, headers=HEADERS, timeout=20, allow_redirects=True)
    except Exception as e:
        return [], "rotto", f"rete: {type(e).__name__}"

    if r.status_code != 200:
        return [], "rotto", f"HTTP {r.status_code}"

    feed = feedparser.parse(r.content)
    totale = len(feed.entries)
    if totale == 0:
        tipo = r.headers.get("Content-Type", "?").split(";")[0]
        return [], "rotto", f"0 voci parsate (Content-Type: {tipo})"

    articoli, piu_recente = [], None
    for entry in feed.entries:
        d = normalizza_data(entry)
        if d is None:
            continue
        if piu_recente is None or d > piu_recente:
            piu_recente = d
        if d < data_limite:
            continue
        excerpt = ""
        for campo in ("summary", "description"):
            raw = getattr(entry, campo, "")
            if raw:
                excerpt = re.sub(r"<[^>]+>", "", raw)[:600]
                break
        articoli.append({
            "titolo": getattr(entry, "title", "(senza titolo)"),
            "url": getattr(entry, "link", ""),
            "data": d,
            "excerpt": excerpt,
        })

    if articoli:
        return articoli, "ok", f"{len(articoli)} in finestra su {totale}"
    nota = f"ultimo del {piu_recente}" if piu_recente else "nessuna data leggibile"
    return [], "muto", f"{totale} voci, {nota}"


def _fetch_telegram(fonte, data_limite):
    """Legge un canale Telegram pubblico dalla pagina di anteprima t.me/s/<canale>.

    Non serve account ne' API: la pagina e' HTML pubblico. Ogni post diventa
    un "articolo" con titolo (prima riga), url (link permanente al post),
    data e testo completo come excerpt.
    """
    import requests
    from bs4 import BeautifulSoup

    sigla = fonte["sigla"]
    canale = fonte["canale"]
    url = f"https://t.me/s/{canale}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"  [{sigla}] TELEGRAM ROTTO — rete: {type(e).__name__}")
        return []

    if r.status_code != 200:
        print(f"  [{sigla}] TELEGRAM ROTTO — HTTP {r.status_code} su {url}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    blocchi = soup.select("div.tgme_widget_message")
    if not blocchi:
        print(f"  [{sigla}] TELEGRAM ROTTO — nessun post nella pagina. "
              f"Il canale e' privato o il nome e' sbagliato?")
        return []

    articoli, piu_recente = [], None
    for b in blocchi:
        tag_testo = b.select_one("div.tgme_widget_message_text")
        testo = tag_testo.get_text("\n", strip=True) if tag_testo else ""
        if len(testo) < 40:          # scarta post di sole immagini o reazioni
            continue

        tag_data = b.select_one("time[datetime]")
        if not tag_data:
            continue
        try:
            d = dateparser.parse(tag_data["datetime"]).date()
        except Exception:
            continue

        if piu_recente is None or d > piu_recente:
            piu_recente = d
        if d < data_limite:
            continue

        link = ""
        tag_link = b.select_one("a.tgme_widget_message_date")
        if tag_link and tag_link.get("href"):
            link = tag_link["href"]

        # il titolo e' la prima riga significativa, il resto resta nel corpo
        righe = [r_.strip() for r_ in testo.split("\n") if r_.strip()]
        titolo = righe[0][:180] if righe else "(post senza testo)"

        articoli.append({
            "titolo": titolo,
            "url": link,
            "data": d,
            "excerpt": testo[:1500],
            "telegram": True,          # segnala che il testo e' gia' completo
        })

    if articoli:
        print(f"  [{sigla}] {len(articoli)} post in finestra (su {len(blocchi)} nella pagina)")
    else:
        nota = f"ultimo del {piu_recente}" if piu_recente else "nessuna data leggibile"
        print(f"  [{sigla}] NIENTE NUOVO — canale ok, {len(blocchi)} post, {nota}")
    return articoli


def fetch_articoli(fonte, data_limite):
    """Ritorna gli articoli della fonte in finestra.

    Il campo "rss" puo' essere una stringa o una lista di URL candidati:
    vengono provati in ordine e si tiene il primo che funziona.
    Se la fonte ha "tipo": "telegram", legge invece il canale via t.me/s/.
    """
    if fonte.get("tipo") == "telegram":
        return _fetch_telegram(fonte, data_limite)

    sigla = fonte["sigla"]
    candidati = fonte["rss"]
    if isinstance(candidati, str):
        candidati = [candidati]

    fallimenti = []
    for i, url_rss in enumerate(candidati):
        articoli, esito, dettaglio = _prova_url(sigla, url_rss, data_limite)

        if esito == "ok":
            marca = "" if i == 0 else f"  [via candidato #{i+1}: {url_rss}]"
            print(f"  [{sigla}] {dettaglio}{marca}")
            return articoli

        if esito == "muto":
            print(f"  [{sigla}] NIENTE NUOVO — feed ok, {dettaglio}")
            if i > 0:
                print(f"           URL buono: {url_rss}")
            return []

        fallimenti.append(f"{url_rss} -> {dettaglio}")

    print(f"  [{sigla}] FEED ROTTO — {len(fallimenti)} candidato/i falliti:")
    for f in fallimenti:
        print(f"           {f}")
    return []

# ------------------------------------------------------------------ #
#  RENDER HTML                                                       #
# ------------------------------------------------------------------ #

CSS = """
:root {
  --bg: #0e1117; --panel: #161b22; --border: #30363d;
  --accent: #58a6ff; --text: #e6edf3; --muted: #8b949e;
  --tag-bg: #1f2937; --tag-text: #93c5fd;
  --grp1: #1e3a5f; --grp2: #3b1f2b; --grp3: #1a3326; --grp4: #2e2418;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'Georgia', serif; line-height: 1.7; }
header { background: var(--panel); border-bottom: 1px solid var(--border);
  padding: 1.8rem 2rem; display: flex; align-items: baseline; gap: 1.2rem; }
header h1 { font-size: 1.4rem; font-weight: 700; color: var(--accent); letter-spacing: .03em; }
header .data { color: var(--muted); font-size: .9rem; font-family: monospace; }
.toc { background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  margin: 1.5rem 2rem; padding: 1rem 1.4rem; max-width: 900px; }
.toc h2 { font-size: .85rem; color: var(--muted); text-transform: uppercase;
  letter-spacing: .1em; margin-bottom: .6rem; }
.toc a { color: var(--accent); font-size: .9rem; text-decoration: none; display: block;
  padding: .15rem 0; }
.toc a:hover { text-decoration: underline; }
.gruppo { margin: 1.5rem 2rem 2rem; max-width: 900px; }
.gruppo-header { padding: .6rem 1rem; border-radius: 6px 6px 0 0;
  font-size: 1rem; font-weight: 700; letter-spacing: .02em; }
.g0 { background: var(--grp1); } .g1 { background: var(--grp2); }
.g2 { background: var(--grp3); } .g3 { background: var(--grp4); }
.articolo { background: var(--panel); border: 1px solid var(--border);
  border-top: none; padding: 1.3rem 1.5rem; }
.articolo + .articolo { border-top: 1px solid var(--border); }
.articolo:last-child { border-radius: 0 0 6px 6px; }
.art-header { display: flex; align-items: flex-start; gap: .8rem; margin-bottom: .7rem; }
.sigla { background: var(--tag-bg); color: var(--tag-text);
  font-size: .72rem; font-family: monospace; font-weight: 700;
  padding: .2rem .55rem; border-radius: 4px; white-space: nowrap; flex-shrink: 0; margin-top: .15rem; }
.art-header h3 { font-size: 1rem; font-weight: 700; }
.art-header h3 a { color: var(--text); text-decoration: none; }
.art-header h3 a:hover { color: var(--accent); }
.data-art { font-size: .78rem; color: var(--muted); margin-bottom: .5rem; }
.paywall { font-size: .72rem; color: #f0883e;
  background: rgba(240,136,62,.1); border-radius: 4px; padding: .1rem .4rem; }
.tags { margin-bottom: .5rem; }
.tag { display: inline-block; background: var(--tag-bg); color: var(--tag-text);
  font-size: .7rem; font-family: monospace; letter-spacing: .03em;
  padding: .12rem .5rem; border-radius: 3px; margin: 0 .35rem .3rem 0; }
.motivo { font-size: .82rem; color: var(--muted); font-style: italic;
  border-left: 2px solid var(--border); padding-left: .8rem; margin-bottom: .7rem; }
.riassunto { font-size: .92rem; color: var(--text); line-height: 1.75; }
.excerpt { font-size: .88rem; color: var(--muted); font-style: italic;
  border-left: 3px solid var(--border); padding-left: .9rem; }
.vuoto { background: var(--panel); border: 1px solid var(--border);
  border-top: none; border-radius: 0 0 6px 6px;
  padding: .9rem 1.5rem; color: var(--muted); font-size: .88rem; font-style: italic; }
footer { text-align: center; padding: 2rem; color: var(--muted); font-size: .8rem;
  border-top: 1px solid var(--border); margin-top: 2rem; }
"""

def render_html(gruppi_dati, data_briefing):
    e = html.escape
    righe = [f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Briefing Geopolitico – {data_briefing}</title>
<style>{CSS}</style></head><body>
<header>
  <h1>⬡ BRIEFING GEOPOLITICO</h1>
  <span class="data">{data_briefing} — generato {datetime.datetime.now().strftime('%H:%M')}</span>
</header>"""]

    # TOC
    righe.append('<nav class="toc"><h2>Indice</h2>')
    for gi, (gruppo, _) in enumerate(gruppi_dati):
        righe.append(f'<a href="#g{gi}">{e(gruppo["nome"])}</a>')
    righe.append('</nav>')

    # Gruppi
    for gi, (gruppo, articoli_per_fonte) in enumerate(gruppi_dati):
        righe.append(f'<section class="gruppo" id="g{gi}">')
        righe.append(f'<div class="gruppo-header g{gi % 4}">{e(gruppo["nome"])}</div>')

        ha_contenuto = False
        for fonte, articoli in articoli_per_fonte:
            for art in articoli:
                ha_contenuto = True
                pw = '<span class="paywall">PAYWALL</span>' if fonte.get("paywall") else ""
                righe.append(f"""<div class="articolo">
  <div class="art-header">
    <span class="sigla">{e(fonte["sigla"])}</span>
    <h3><a href="{e(art['url'])}" target="_blank">{e(art['titolo'])}</a> {pw}</h3>
  </div>
  <div class="data-art">{e(fonte["nome"])} · {art['data']}</div>""")
                if art.get("tag"):
                    tag_html = "".join(f'<span class="tag">{e(str(t))}</span>' for t in art["tag"])
                    righe.append(f'<div class="tags">{tag_html}</div>')
                if art.get("motivo"):
                    righe.append(f'<p class="motivo">{e(art["motivo"])}</p>')
                if art.get("riassunto"):
                    righe.append(f'<p class="riassunto">{e(art["riassunto"])}</p>')
                elif art.get("excerpt"):
                    righe.append(f'<p class="excerpt">{e(art["excerpt"])}</p>')
                righe.append("</div>")

        if not ha_contenuto:
            righe.append('<div class="vuoto">Nessun articolo in questa finestra temporale.</div>')
        righe.append("</section>")

    righe.append(f'<footer>genera_briefing.py v2 · {data_briefing}</footer></body></html>')
    return "\n".join(righe)

# ------------------------------------------------------------------ #
#  MAIN                                                              #
# ------------------------------------------------------------------ #

def main():
    global GIORNI
    esempio = "--esempio" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--giorni" and i + 1 < len(sys.argv):
            try:
                GIORNI = int(sys.argv[i + 1])
            except ValueError:
                pass

    data_oggi = oggi_utc()
    data_limite = finestra(GIORNI)
    nome_file = f"briefing_{data_oggi}.html"

    # --- MODALITÀ TEST FEED (no API, solo rete) ---
    if "--test-feed" in sys.argv:
        print(f"Verifica feed — finestra: dal {data_limite}\n")
        vivi = []
        for gruppo in GRUPPI:
            print(f"\n{gruppo['nome']}")
            for fonte in gruppo["fonti"]:
                if fetch_articoli(fonte, data_limite):
                    vivi.append(fonte["sigla"])
        totale = sum(len(g["fonti"]) for g in GRUPPI)
        print("\n" + "=" * 58)
        print(f"  {len(vivi)}/{totale} feed hanno prodotto articoli")
        print(f"  {', '.join(vivi) if vivi else 'nessuno'}")
        print("=" * 58)
        print("\nCorreggi in GRUPPI gli URL delle righe FEED ROTTO qui sopra.")
        return

    # --- MODALITÀ ESEMPIO (no API, no rete) ---
    if esempio:
        import random
        gruppi_dati = []
        for gruppo in GRUPPI:
            apf = []
            for fonte in gruppo["fonti"]:
                art = {
                    "titolo": f"[ESEMPIO] Sviluppi strategici – {fonte['sigla']}",
                    "url": "#",
                    "data": data_oggi,
                    "excerpt": "",
                    "riassunto": (
                        f"Questo è un riassunto di esempio per la fonte {fonte['nome']}. "
                        "Nell'output reale questo paragrafo contiene l'analisi tecnica dell'articolo "
                        "in italiano: contesto geopolitico, attori coinvolti, implicazioni operative "
                        "e sviluppi attesi. Il tono è quello di un briefing riservato."
                    ),
                }
                apf.append((fonte, [art]))
            gruppi_dati.append((gruppo, apf))
        html_out = render_html(gruppi_dati, data_oggi)
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"[ESEMPIO] Scritto: {nome_file}")
        return

    # --- MODALITÀ REALE ---
    # Chiave API
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        import getpass
        print("Incolla la tua chiave API Anthropic (sk-ant-...) e premi Invio.")
        print("Non comparirà a schermo: è normale.")
        api_key = getpass.getpass("Chiave API: ").strip()
    if not api_key:
        sys.exit("ERRORE: nessuna chiave API fornita.")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    gruppi_dati = []
    for gruppo in GRUPPI:
        print(f"\n{'='*50}")
        print(f"  {gruppo['nome']}")
        print(f"{'='*50}")

        # --- FASE 1: raccolta di tutto il gruppo ---
        candidati = []
        for fonte in gruppo["fonti"]:
            print(f"\n  [{fonte['sigla']}]")
            for art in fetch_articoli(fonte, data_limite):
                candidati.append((fonte, art))

        if not candidati:
            gruppi_dati.append((gruppo, []))
            continue

        # --- FASE 2: prioritizzazione ---
        print(f"\n  Triage su {len(candidati)} candidati...")
        selezionati = prioritizza(client, gruppo["nome"], candidati, gruppo.get("max", 5))

        # --- FASE 3: sintesi solo dei selezionati ---
        for fonte, art in selezionati:
            print(f"    → {art['titolo'][:70]}...")
            if art.get("telegram"):
                testo = art["excerpt"]          # il post e' gia' il testo completo
            elif fonte.get("paywall"):
                testo = None
            else:
                testo = estrai_testo(art["url"])
            if not testo:
                testo = art["excerpt"]
            if testo and len(testo) > 80:
                art["riassunto"] = riassumi(client, testo, art["titolo"])
                print(f"      ✓ riassunto ({len(art['riassunto'])} car.)")
            else:
                art["riassunto"] = ""
                print(f"      ⚠ testo insufficiente, solo excerpt")
            time.sleep(0.4)

        # raggruppo per fonte, mantenendo l'ordine di selezione
        per_fonte, ordine = {}, []
        for fonte, art in selezionati:
            k = fonte["sigla"]
            if k not in per_fonte:
                per_fonte[k] = (fonte, [])
                ordine.append(k)
            per_fonte[k][1].append(art)
        gruppi_dati.append((gruppo, [per_fonte[k] for k in ordine]))

    html_out = render_html(gruppi_dati, data_oggi)
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"\n✅ Scritto: {nome_file}")

if __name__ == "__main__":
    main()
