#!/usr/bin/env python3
"""
Kulturtag Braunschweig – sammelt Kulturtermine aus mehreren Quellen und baut daraus
eine Tagesansicht (kulturtag.html), die man im Browser öffnet.

Nutzung:
  python3 kulturtag.py                 # alles abrufen (braucht Playwright), Seite bauen und öffnen
  python3 kulturtag.py --tage 14       # Zeitraum ab heute (Standard 21 Tage)
  python3 kulturtag.py --sichtbar      # Browser sichtbar laufen lassen (hilft, falls eine Seite blockt)
  python3 kulturtag.py --nur-mischen RAW --artifact-docs OUT
                                       # (intern) vorhandene Rohdaten zusammenführen, ohne Browser

Läuft rein lokal: Es werden nur öffentliche Veranstaltungsseiten gelesen, nichts wird irgendwohin geschickt.
Die Termine verlinken immer auf die Originalseite – dort gelten die Angaben.
"""
import argparse, datetime as dt, json, os, re, sys, unicodedata, webbrowser
from difflib import SequenceMatcher
from pathlib import Path

HIER = Path(__file__).resolve().parent
EXTRACTORS = HIER / "extractors.js"
TEMPLATE = HIER / "vorlage.html"

# ---------------------------------------------------------------- Einordnung
SPARTEN = [
    ("Kirchenmusik", r"kirche|dom\b|\bst\.|klosterkirche|kapelle|synagoge|orgel|kantate|messe\b|chor"),
    ("Kino", r"filmtheater|kino|film|astor|universum|dokfilm|cin[eé]"),
    ("Kinder & Familie", r"kinder|famil|ab \d+ j|bilderbuch|mitmach|kids|junior|baby-barock|haumi"),
    ("Literatur & Bibliothek", r"lesung|liest|literatur|buch|bibliothek|autor|poetry|erzähl|gedicht"),
    ("Wissenschaft & Vortrag", r"vortrag|vorlesung|ringvorlesung|kolloquium|diskussion|gespräch|akademie|wissenschaft|industriekultur|true crime|reise|archäolog"),
    ("Kleinkunst & Comedy", r"kabarett|kunst gegen bares|impro|comedy|komische nacht|puppen gucken|kleinkunst|zauber|magie|travestie|drag|slam|satire"),
    ("Ausstellung & Führung", r"ausstellung|führung|finissage|vernissage|museum|galerie|kunstverein|kunst\b|stadtspaziergang|rundgang|exponat|kemenate"),
    ("Bühne", r"theater|schauspiel|oper|operette|tanz|musical|bühne|premiere|komödie|figurentheater|fadenschein|kult\b"),
    ("Musik", r"konzert|band|tour|jazz|blues|live|quartett|trio|orchester|klavier|lieder|sänger|musik|singt|rock|pop"),
]
NICHT_KULTUR = re.compile(
    r"kürbisscheune|beratung|hausnotruf|bark date|basketball|eintracht|kicker|krimi-?dinner|3d krimi|dinner-musical|"
    r"barhopping|martinsmarkt|basar|suppentag|\bnlp\b|flickwerkstatt|spieltagscamp|hausautomation|party\b|"
    r"dauerausstellung|stadtrundfahrt|tag der offenen tür|markt der möglichkeiten|telefonberatung|igelschutz|"
    r"tasting|yoga|lampionfahrt|ü30|ü60|festival of lights: ein stadtspaziergang|afterwork-stadtspaziergang|"
    r"stadtspaziergang in der löwenstadt|friedensmeditation|after the lights|ersti session|linux basics|bioinformatics", re.I)
VORRANG = {"Staatstheater": 0, "Brunsviga": 0, "westand": 0, "Schön & Frölich": 0, "Jazz Braunschweig": 0,
           "Kulturkalender Schloss": 0, "Graff": 0, "Das KULT": 0, "HBK": 0, "BIFF": 0, "Raabe-Haus": 0, "Haus der Wissenschaft": 1, "TU-Kalender": 1, "Stadtkalender": 2, "filmstarts.de": 3, "mvp.de": 4}
# Spielstätten-Quellen: Sparte, wenn sich aus dem Titel nichts ableiten lässt
STANDARD_SPARTE = {"Brunsviga": "Kleinkunst & Comedy", "westand": "Musik", "Schön & Frölich": "Musik", "Jazz Braunschweig": "Musik",
                   "Graff": "Literatur & Bibliothek", "Raabe-Haus": "Literatur & Bibliothek", "Das KULT": "Bühne",
                   "Haus der Wissenschaft": "Wissenschaft & Vortrag", "HBK": "Ausstellung & Führung"}
GENAUER = {"Kino", "Wissenschaft & Vortrag", "Kinder & Familie", "Ausstellung & Führung", "Literatur & Bibliothek"}
ORT_STOPP = {"braunschweig", "straße", "strasse", "platz", "haus", "kulturzentrum", "zentrum", "event", "theater"}


def sparte_raten(e):
    if e.get("sparte"):
        return e["sparte"]
    # erst nur Titel/Hinweis (der Ort ist oft irreführend, z. B. "Jazz" im "KULT"-Theater), dann mit Ort
    kurz = f'{e.get("titel","")} {e.get("hinweis","")}'.lower()
    ort = e.get("ort", "").lower()
    # Quellen mit eigener Standard-Sparte: Ort nicht heranziehen (sonst wird z. B. jeder Vortrag im Museum zur Ausstellung)
    for text in ((kurz,) if e.get("quelle") in STANDARD_SPARTE else (kurz, kurz + " " + ort)):
        for name, muster in SPARTEN:
            if re.search(muster, text):
                if name == "Musik" and re.search(SPARTEN[0][1], ort):
                    return "Kirchenmusik"
                return name
    if e.get("quelle") in STANDARD_SPARTE:
        e["_geraten"] = True
        return STANDARD_SPARTE[e["quelle"]]
    e["_geraten"] = True
    return "Musik" if e.get("quelle") == "mvp.de" else "Ausstellung & Führung"


def kern(titel):
    t = unicodedata.normalize("NFKD", titel.lower())
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\b(braunschweig|tour|live|konzert|lesung|vortrag|im|in|der|die|das|und|mit)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def gleich(a, b):
    ka, kb = kern(a["titel"]), kern(b["titel"])
    if not ka or not kb:
        return False
    if ka == kb or ka[:22] == kb[:22]:
        return True
    kurz, lang = sorted((ka, kb), key=len)
    if len(kurz) >= 8 and kurz in lang:
        return True
    # unterschiedliche Schreibweisen derselben Veranstaltung (z. B. Tippfehler, Sonderzeichen)
    if len(kurz) >= 12 and SequenceMatcher(None, ka[:28], kb[:28]).ratio() >= 0.8:
        return True
    # gleicher Ort und ein längeres gemeinsames Titelstück (z. B. "Multivisions-Show: X" / "Reinhard Pantke – X")
    if ort_gleich(a, b):
        allg = lambda x: re.sub(r"\b(braunschweiger|braunschweigs|ausstellung|sonderausstellung|zeitgenoessische|zeitgenossische)\b", " ", x)
        pa, pb = allg(kern(re.sub(r"\(.*?\)", " ", a["titel"]))), allg(kern(re.sub(r"\(.*?\)", " ", b["titel"])))
        m = SequenceMatcher(None, pa, pb).find_longest_match(0, len(pa), 0, len(pb))
        return m.size >= 14
    return False


def ort_gleich(a, b):
    w = lambda e: {x for x in re.findall(r"[a-zäöüß]{5,}", e.get("ort", "").lower()) if x not in ORT_STOPP}
    return bool(w(a) & w(b))


def zusammenfuehren(roh, start, ende):
    termine, laufend = [], []
    for e in roh:
        if not e.get("titel") or NICHT_KULTUR.search(e["titel"] + " " + e.get("ort", "")):
            continue
        e = {k: (v.strip() if isinstance(v, str) else v) for k, v in e.items()}
        e["sparte"] = sparte_raten(e)
        e["quellen"] = [{"name": e.get("quelle", ""), "url": e.get("url", "")}]
        bis = e.get("bis")
        if bis and bis > e["datum"]:
            if bis < start or e["datum"] > ende:
                continue
            laufend.append({"titel": e["titel"], "ort": e.get("ort", ""), "von": e["datum"], "bis": bis,
                            "zeit": e.get("zeit", ""), "sparte": e["sparte"], "preis": "",
                            "quelle": e["quellen"][0]["name"], "quelle_url": e["quellen"][0]["url"]})
            continue
        if not (start <= e["datum"] <= ende):
            continue
        termine.append(e)

    # laufende Angebote: gleiche Ausstellung aus mehreren Quellen nur einmal
    laufend.sort(key=lambda x: VORRANG.get(x["quelle"], 9))
    eindeutig = []
    for x in laufend:
        if any(gleich(y, x) and x["von"] <= y["bis"] and y["von"] <= x["bis"] for y in eindeutig):
            continue
        eindeutig.append(x)
    laufend = eindeutig

    # Dubletten: gleicher Tag + ähnlicher Titel -> zusammenlegen, Quellen sammeln
    termine.sort(key=lambda e: (e["datum"], VORRANG.get(e.get("quelle"), 9)))
    fertig = []
    for e in termine:
        treffer = next((f for f in fertig if f["datum"] == e["datum"] and gleich(f, e)
                        and (not f.get("zeit") or not e.get("zeit") or f["zeit"] == e["zeit"]
                             or e.get("quelle") == "Stadtkalender")), None)
        if treffer:
            if not treffer.get("zeit") and e.get("zeit"):
                treffer["zeit"] = e["zeit"]
            if e.get("hinweis") == "ABGESAGT":
                treffer["hinweis"] = "ABGESAGT"
            # nur geschätzte Sparte? Dann die genauere einer anderen Quelle übernehmen
            if treffer.get("_geraten") and not e.get("_geraten") and (e["sparte"] in GENAUER or (treffer["sparte"] == "Musik" and e["sparte"] in ("Bühne", "Kleinkunst & Comedy"))):
                treffer["sparte"] = e["sparte"]; treffer["_geraten"] = False
            if all(q["name"] != e["quellen"][0]["name"] for q in treffer["quellen"]):
                treffer["quellen"].append(e["quellen"][0])
            continue
        fertig.append(e)
    for e in fertig:
        e["quelle"], e["quelle_url"] = e["quellen"][0]["name"], e["quellen"][0]["url"]
        if e.get("hinweis") == "ABGESAGT":
            e["titel"] = "ABGESAGT: " + e["titel"]
            e["hinweis"] = "laut Quelle abgesagt"
        e.pop("bis", None); e.pop("url", None); e.pop("_geraten", None)
        e.setdefault("preis", "")
    tage = {}
    for e in sorted(fertig, key=lambda e: (e["datum"], e.get("zeit") or "99", e["titel"])):
        tage.setdefault(e["datum"], []).append(e)
    return tage, laufend


# ---------------------------------------------------------------- Abruf (Playwright)
def abrufen(start, ende, sichtbar=False):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright fehlt. Einmalig installieren:\n  pip3 install playwright && python3 -m playwright install chromium")
    js = EXTRACTORS.read_text(encoding="utf-8")
    roh, gelesen, offen, je_quelle = [], [], [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not sichtbar, args=["--disable-http2"])  # manche Server (z. B. graff.de) brechen HTTP/2 von Rechenzentren ab
        ctx = browser.new_context(locale="de-DE", bypass_csp=True, user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"))
        page = ctx.new_page()
        page.set_content("<html></html>")
        page.add_script_tag(content=js)
        quellen = page.evaluate("KULTURTAG_QUELLEN.map(q => ({id:q.id, name:q.name}))")
        for q in quellen:
            try:
                page.add_script_tag(content=js)
                url = page.evaluate("([id,a]) => KULTURTAG_QUELLEN.find(q=>q.id===id).startUrl(a)",
                                    [q["id"], {"start": start, "end": ende}])
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                for versuch in range(3):  # Seiten, die nach dem Laden noch umleiten (z. B. Das KULT): kurz warten, nochmal
                    try:
                        page.add_script_tag(content=js)
                        daten = page.evaluate("async ([id,a]) => await KULTURTAG_QUELLEN.find(q=>q.id===id).extract(a)",
                                              [q["id"], {"start": start, "end": ende}])
                        break
                    except Exception as ex:
                        if versuch == 2 or "context was destroyed" not in str(ex):
                            raise
                        page.wait_for_load_state("load", timeout=30000)
                        page.wait_for_timeout(3000)
                roh += daten
                je_quelle[q["id"]] = (q["name"], daten)
                gelesen.append(f'{q["name"]} ({len(daten)})')
                print(f'  ✓ {q["name"]}: {len(daten)} Einträge')
            except Exception as ex:  # eine Quelle darf scheitern, der Rest läuft weiter
                offen.append(q["name"])
                je_quelle[q["id"]] = (q["name"], None)
                print(f'  ✗ {q["name"]}: {str(ex).splitlines()[0][:120]}')
        browser.close()
    abrufen.je_quelle = je_quelle
    return roh, gelesen, offen


# ---------------------------------------------------------------- Ausgabe
def seite_bauen(tage, laufend, stand, ziel):
    vorlage = TEMPLATE.read_text(encoding="utf-8")
    daten = json.dumps({"tage": tage, "laufend": laufend, "stand": stand}, ensure_ascii=False)
    html = ("<!doctype html><html lang=de><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name=robots content='noindex,nofollow'>"
            "<meta name=apple-mobile-web-app-capable content=yes>"
            "<meta name=apple-mobile-web-app-title content='Kulturtag'>"
            "<meta name=theme-color content='#a3241c'>"
            "<link rel=apple-touch-icon href='apple-touch-icon.png'>"
            "<link rel=icon href='apple-touch-icon.png'>"
            "<style>[hidden]{display:none!important}body{margin:0}</style></head><body>"
            f"<script>window.KT_DATA={daten};</script>\n{vorlage}</body></html>")
    ziel.write_text(html, encoding="utf-8")


QUELLNAMEN = {"stadtkalender": "Stadtkalender", "tu": "TU Braunschweig", "staatstheater": "Staatstheater", "mvp": "mvp.de",
              "kinos": "Kinos (filmstarts.de)", "biff": "BIFF – Filmfestival", "brunsviga": "Brunsviga", "westand": "westand",
              "schoenfroelich": "Schön & Frölich", "jazzbs": "Initiative Jazz", "daskult": "Das KULT",
              "hausderwissenschaft": "Haus der Wissenschaft", "hbk": "HBK", "kulturkalender-schloss": "Kulturkalender Schloss (PDF)", "raabe-haus": "Raabe-Haus (PDF)"}


def github_lauf(repo, start, ende, stand, sichtbar=False, ohne_abruf=False):
    """Ruft alle Quellen ab. Scheitert eine Quelle (oder liefert nichts), bleiben ihre Rohdaten vom
    letzten erfolgreichen Abruf stehen, damit die Seite nicht plötzlich leer ist."""
    rohdir = repo / "daten" / "roh"; rohdir.mkdir(parents=True, exist_ok=True)
    namen, gelesen, offen = {}, [], []
    if not ohne_abruf:
        abrufen(start, ende, sichtbar)
        for qid, (name, daten) in abrufen.je_quelle.items():
            namen[qid] = name
            if daten:
                (rohdir / f"{qid}.json").write_text(json.dumps(daten, ensure_ascii=False, indent=0), encoding="utf-8")
    # Quellen, die es nur als PDF gibt: eigene Leser (brauchen pdftotext)
    if not ohne_abruf:
        import roter_saal, raabe_haus
        for qid, name, modul in (("kulturkalender-schloss", "Kulturkalender Schloss", roter_saal), ("raabe-haus", "Raabe-Haus", raabe_haus)):
            try:
                daten = modul.abrufen()
                if daten:
                    (rohdir / f"{qid}.json").write_text(json.dumps(daten, ensure_ascii=False, indent=0), encoding="utf-8")
                abrufen.je_quelle[qid] = (name, daten or None)
                print(f"  ✓ {name} (PDF): {len(daten)} Einträge")
            except Exception as ex:
                abrufen.je_quelle[qid] = (name, None)
                namen[qid] = name
                print(f"  ✗ {name} (PDF): {str(ex)[:120]}")
    roh = []
    heute_abgerufen = set() if ohne_abruf else {q for q, (_, d) in abrufen.je_quelle.items() if d}
    for f in sorted(rohdir.glob("*.json")):
        daten = json.loads(f.read_text(encoding="utf-8"))
        roh += daten
        name = QUELLNAMEN.get(f.stem, namen.get(f.stem, f.stem))
        if f.stem in heute_abgerufen:
            gelesen.append(f"{name}: {len(daten)} Einträge")
        else:
            gelesen.append(f"{name}: {len(daten)} Einträge (älterer Abruf)")
            if f.stem in namen:
                offen.append(name)
    offen += [n for q, n in namen.items() if not (rohdir / f"{q}.json").exists()]
    tage, laufend = zusammenfuehren(roh, start, ende)
    stand.update({"gelesen": gelesen, "offen": offen, "anzahl": sum(map(len, tage.values()))})
    (repo / "daten" / "stand.json").write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")
    seite_bauen(tage, laufend, stand, repo / "index.html")
    print(f"{stand['anzahl']} Termine an {len(tage)} Tagen, {len(laufend)} laufend → {repo / 'index.html'}")


def main():
    ap = argparse.ArgumentParser(description="Kulturtag Braunschweig")
    ap.add_argument("--tage", type=int, default=21)
    ap.add_argument("--sichtbar", action="store_true")
    ap.add_argument("--ausgabe", default=str(Path.home() / "Kulturtag"))
    ap.add_argument("--nicht-oeffnen", action="store_true")
    ap.add_argument("--nur-mischen", metavar="RAWDIR")
    ap.add_argument("--artifact-docs", metavar="OUTDIR")
    ap.add_argument("--github", metavar="REPO", help="Abruf für die GitHub-Seite: Rohdaten je Quelle in REPO/daten/roh, Seite nach REPO/index.html")
    ap.add_argument("--ohne-abruf", action="store_true", help="mit --github: nur aus vorhandenen Rohdaten bauen")
    a = ap.parse_args()

    heute = dt.date.today()
    start, ende = heute.isoformat(), (heute + dt.timedelta(days=a.tage)).isoformat()
    stand = {"stand": dt.datetime.now().astimezone().isoformat(timespec="minutes"), "zeitraum_bis": ende}

    if a.github:
        github_lauf(Path(a.github), start, ende, stand, a.sichtbar, a.ohne_abruf)
        return

    if a.nur_mischen:
        roh, gelesen = [], []
        for f in sorted(Path(a.nur_mischen).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            roh += d; gelesen.append(f"{f.stem} ({len(d)})")
        offen = []
    else:
        print(f"Kulturtag Braunschweig – Abruf {start} bis {ende}")
        roh, gelesen, offen = abrufen(start, ende, a.sichtbar)

    tage, laufend = zusammenfuehren(roh, start, ende)
    stand.update({"gelesen": gelesen, "offen": offen, "anzahl": sum(map(len, tage.values()))})

    if a.artifact_docs:  # Format der Claude-Seite: ein Dokument je Tag
        out = Path(a.artifact_docs); out.mkdir(parents=True, exist_ok=True)
        for d, lst in tage.items():
            (out / f"{d}.json").write_text(json.dumps({"datum": d, "termine": lst}, ensure_ascii=False), encoding="utf-8")
        (out / "laufend.json").write_text(json.dumps({"eintraege": laufend}, ensure_ascii=False), encoding="utf-8")
        (out / "stand.json").write_text(json.dumps(stand, ensure_ascii=False), encoding="utf-8")
        print(f"{stand['anzahl']} Termine an {len(tage)} Tagen, {len(laufend)} laufend → {out}")
        return

    ziel_dir = Path(a.ausgabe); ziel_dir.mkdir(parents=True, exist_ok=True)
    ziel = ziel_dir / "kulturtag.html"
    seite_bauen(tage, laufend, stand, ziel)
    print(f"\n{stand['anzahl']} Termine, {len(laufend)} laufende Angebote → {ziel}")
    if not a.nicht_oeffnen:
        webbrowser.open(ziel.as_uri())


if __name__ == "__main__":
    main()
