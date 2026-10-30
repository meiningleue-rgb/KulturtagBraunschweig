"""Raabe-Haus:Literaturzentrum Braunschweig – Veranstaltungsblatt (PDF, ca. vier Monate).

Jeder Termin beginnt mit einer Kopfzeile „Mi. 11.11. | 11:00 Uhr | Raabe-Haus“, darunter ggf. die Adresse,
dann der Titel. Enthält auch Termine bei Partnern (z. B. Buchhandlung Bücherwurm, Roter Saal).
"""
import re, subprocess, tempfile, urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

START = "https://www.braunschweig.de/literaturzentrum/programm/index.php"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MON = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}
KOPF = re.compile(r"^\s*(Mo|Di|Mi|Do|Fr|Sa|So)\.?\s+(\d{1,2})\.(\d{1,2})\.\s*\|\s*(\d{1,2})[:.](\d{2})(?:\s*[–-]\s*\d{1,2}[:.]\d{2})?\s*Uhr\s*(?:\|\s*(.*))?$", re.I)
ADRESSE = re.compile(r"\b\d{5}\s+Braunschweig\b")
RAABE = "Raabe-Haus:Literaturzentrum Braunschweig"


def _holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "de-DE"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def pdf_links():
    """PDF-Links auf der Programmseite und den direkt verlinkten Programm-Unterseiten."""
    gefunden, seiten = set(), [START]
    html = _holen(START).decode("utf-8", "replace")
    seiten += [urljoin(START, h) for h in re.findall(r'href="(/literaturzentrum/programm/[^"#]+\.php)"', html)][:8]
    for s in dict.fromkeys(seiten):
        try:
            h = html if s == START else _holen(s).decode("utf-8", "replace")
        except Exception:
            continue
        gefunden |= {urljoin(s, x) for x in re.findall(r'href="([^"]*Veranstaltungsblatt[^"]*\.pdf)"', h, re.I)}
    return sorted(gefunden)


def lesen(text, pdf_url):
    jm = re.search(r"\b(Jan|Feb|Mär|Mar|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)[a-zä]*\.?\s*[–-]\s*(Jan|Feb|Mär|Mar|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)[a-zä]*\.?\s*(20\d\d)", text)
    if jm:
        m0, m1, jahr = MON[jm.group(1).lower()[:3]], MON[jm.group(2).lower()[:3]], int(jm.group(3))
    else:  # ohne Kopf: häufigste Jahreszahl
        jahr = int(Counter(re.findall(r"\b(20\d\d)\b", text)).most_common(1)[0][0]); m0 = m1 = 0
    zeilen = [z.strip() for z in text.splitlines()]
    roh = []
    for i, z in enumerate(zeilen):
        m = KOPF.match(z)
        if not m:
            continue
        _, tag, mon, hh, mm, ort = m.groups()
        rest = [x for x in zeilen[i + 1:i + 6] if x]
        if rest and ADRESSE.search(rest[0]):
            ort = f"{ort}, {rest.pop(0)}" if ort else rest.pop(0)
        if not rest:
            continue
        while len(rest) > 1 and re.search(r"\s(mit|dem|der|den|des|und|von|vom|für|im|in|zur|zum|über|auf)$", rest[0]):
            rest[0:2] = [rest[0] + " " + rest[1]]                 # umbrochener Titel
        mon = int(mon)
        j = jahr - 1 if (m0 > m1 and mon >= m0) else jahr
        roh.append((f"{j}-{mon:02d}-{int(tag):02d}", f"{int(hh):02d}:{mm}", (ort or "").strip(), rest[:2]))
    reihe = Counter(r[3][0] for r in roh)            # wiederkehrende Reihentitel
    out = []
    for datum, zeit, ort, (t1, *t2) in roh:
        titel = t1
        if t2 and reihe[t1] > 1 and not t2[0].endswith(":") and not re.match(r"(In |Mit |mit |Lesekreis|Lesung mit|Spaziergang)", t2[0]):
            titel = f"{t1}: {re.split(r' vorgestellt von', t2[0])[0]}"
        if not ort or ort.startswith("Raabe-Haus"):
            ort = RAABE
        out.append({"datum": datum, "zeit": zeit, "titel": titel, "ort": ort, "sparte": "", "hinweis": "", "preis": "",
                    "url": pdf_url, "quelle": "Raabe-Haus"})
    return out


def abrufen():
    links = pdf_links()
    if not links:
        raise RuntimeError("kein Veranstaltungsblatt-PDF gefunden")
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, url in enumerate(links):
            pdf = Path(tmp) / f"{i}.pdf"
            pdf.write_bytes(_holen(url))
            subprocess.run(["pdftotext", str(pdf), str(pdf.with_suffix(".txt"))], check=True)   # ohne -layout: Spalten nacheinander
            out += lesen(pdf.with_suffix(".txt").read_text(encoding="utf-8", errors="replace"), url)
    return out


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1:
        print(json.dumps(lesen(Path(sys.argv[1]).read_text(encoding="utf-8"), "test.pdf"), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(abrufen(), ensure_ascii=False, indent=1))
