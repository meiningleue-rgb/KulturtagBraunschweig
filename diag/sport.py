"""Heimspiele Braunschweiger Mannschaften: Basketball (Löwen, BBL) und Handball (MTV, 3. Liga).

- Basketball: Spielplan-Tabelle von hessenschau.de (serverseitig gerendert, Daten der ARD-Sportdatenbank).
- Handball: handball.net (DHB) – die Teamseite enthält die kommenden Spiele als JSON im Seitenquelltext.

Teams und Ligen ändern sich zur neuen Saison ggf. – dann hier die Kennungen anpassen.
"""
import html, json, re, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

BASKETBALL_URL = "https://www.hessenschau.de/sport/ergebnisse-tabellen/basketball-1bl100~team_id-151.html"
BASKETBALL_HALLE = "Volkswagen Halle Braunschweig, Europaplatz 1"

HANDBALL_TEAM = "63819"   # MTV Braunschweig, 3. Liga Männer (handball.net, Saison 2026/27)
HANDBALL_URL = f"https://www.handball.net/team/{HANDBALL_TEAM}"
HALLEN = {"alte waage": "Sporthalle Alte Waage, Braunschweig", "volkswagenhalle": "Volkswagen Halle Braunschweig, Europaplatz 1",
          "volkswagen halle": "Volkswagen Halle Braunschweig, Europaplatz 1", "tunica": "Tunicasporthalle, Braunschweig"}


def _holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def basketball(start, ende):
    seite = _holen(BASKETBALL_URL)
    out = []
    for zeile in re.findall(r"<tr\b[^>]*>(.*?)</tr>", seite, re.S):
        d = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", zeile)
        z = re.search(r"-time[^>]*>\s*(\d{1,2}:\d{2})", zeile)
        teams = {}
        for tag in re.findall(r"<abbr\b[^>]*>", zeile):
            kl, ti = re.search(r'class="([^"]*)"', tag), re.search(r'title="([^"]*)"', tag)
            if kl and ti:
                teams["heim" if "-home" in kl.group(1) else "gast" if "-visitor" in kl.group(1) else "x"] = ti.group(1)
        heim, gast = teams.get("heim"), teams.get("gast")
        if not (d and heim and gast) or "Braunschweig" not in heim:
            continue
        datum = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
        if not (start <= datum <= ende):
            continue
        out.append({"datum": datum, "zeit": z.group(1).zfill(5) if z else "",
                    "titel": f"Basketball: {html.unescape(heim)} – {html.unescape(gast)}",
                    "ort": BASKETBALL_HALLE, "sparte": "Sport", "hinweis": "Heimspiel · Basketball-Bundesliga (BBL)", "preis": "",
                    "url": BASKETBALL_URL, "quelle": "Basketball Löwen"})
    if not re.search(r"teamResults", seite):
        raise RuntimeError("Spielplan-Tabelle nicht gefunden")
    return out


def _name(n):
    """„NHV CONCORDIA DELITZSCH“ → „NHV Concordia Delitzsch“ (Kürzel mit Konsonanten bleiben groß)."""
    w = []
    for t in n.split():
        if t.isupper() and not (len(t) <= 3 and re.search(r"[^AEIOUÄÖÜ]", t)):
            t = t.capitalize()
        w.append(t)
    return " ".join(w)


def _halle(name):
    n = (name or "").lower()
    for k, v in HALLEN.items():
        if k in n:
            return v
    return name.title() if name else "Braunschweig"


def handball(start, ende):
    seite = _holen(HANDBALL_URL)
    m = re.search(r'<script id="serverApp-state" type="application/json">(.*?)</script>', seite, re.S)
    if not m:
        raise RuntimeError("Seitendaten (serverApp-state) nicht gefunden")
    daten = json.loads(m.group(1).replace("&q;", '"').replace("&a;", "&").replace("&s;", "'").replace("&l;", "<").replace("&g;", ">"))
    spiele = []
    for v in daten.values():
        if isinstance(v, dict) and str(v.get("u", "")).endswith("/matches") and isinstance(v.get("b", {}).get("data"), list):
            spiele += v["b"]["data"]
    out, gesehen = [], set()
    for s in spiele:
        heim, gast = (s.get("local") or {}).get("name", ""), (s.get("visitor") or {}).get("name", "")
        if "braunschweig" not in heim.lower() or s.get("id") in gesehen:
            continue
        gesehen.add(s.get("id"))
        datum, zeit = s["date"][:10], s["date"][11:16]           # handball.net liefert Ortszeit (trotz „+00:00“)
        if not (start <= datum <= ende):
            continue
        liga = ((s.get("phase") or {}).get("competition") or {}).get("name", "Handball")
        abgesagt = (s.get("status") or {}).get("short_name") in ("SUS", "CAN", "APL")
        out.append({"datum": datum, "zeit": zeit, "titel": f"Handball: {_name(heim)} – {_name(gast)}",
                    "ort": _halle((s.get("field") or {}).get("name")), "sparte": "Sport",
                    "hinweis": "ABGESAGT" if abgesagt else f"Heimspiel · {liga}", "preis": "",
                    "url": HANDBALL_URL, "quelle": "MTV Handball"})
    return out


QUELLEN = (("basketball", "Basketball Löwen (BBL)", basketball), ("handball", "MTV Braunschweig Handball", handball))

if __name__ == "__main__":
    import sys
    s, e = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("2026-01-01", "2027-12-31")
    for _, name, f in QUELLEN:
        try:
            r = f(s, e); print(f"✓ {name}: {len(r)}"); print(json.dumps(r[:5], ensure_ascii=False, indent=1))
        except Exception as ex:
            print(f"✗ {name}: {ex}")
