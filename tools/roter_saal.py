"""Kulturkalender Schloss (Roter Saal, Stadtbibliothek, Stadtarchiv, Schlossmuseum, Städtisches Museum).

Die Stadt veröffentlicht das Programm nur als PDF. Am Ende jedes Hefts steht ein „TERMINKALENDER“ mit einer
Zeile je Termin und eine „AUSSTELLUNGSÜBERSICHT“ – beide werden hier mit pdftotext (poppler-utils) gelesen.
"""
import re, subprocess, tempfile, urllib.request
from pathlib import Path
from urllib.parse import urljoin

SEITE = "https://www.braunschweig.de/roter-saal"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MONATE = ["JANUAR", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI", "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]
ORTE = {"Roter Saal": "Roter Saal im Schloss, Schlossplatz 1", "Stadtbibliothek": "Stadtbibliothek Braunschweig, Schlossplatz 2",
        "Stadtarchiv": "Stadtarchiv Braunschweig, Schlossplatz 1", "Schlossmuseum": "Schlossmuseum Braunschweig, Schlossplatz 1",
        "halle267": "halle267 – städtische galerie braunschweig, Hamburger Straße 267"}
TERMIN = re.compile(r"\b(MO|DI|MI|DO|FR|SA|SO)\s+(\d{1,2})\.(\d{1,2})\.\s+(.+?)\s{2,}(?:(\d{1,2})[:.](\d{2})\s*Uhr)?\s*(.*?)\s{2,}\d{1,3}(?:/\d+)?\b")
AUSST = re.compile(r"(?:NOCH BIS|(\d{2})\.(\d{2})\.(\d{2}) BIS) (\d{2})\.(\d{2})\.(\d{2})\s+(.+?)\s{2,}(.+?)\s{2,}\d")


def _holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "de-DE"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def lesen(text, pdf_url):
    """Termine und Ausstellungen aus dem pdftotext-Text eines Hefts."""
    kopf = re.search(r"([A-ZÄ]+) BIS ([A-ZÄ]+) (\d{4})", text)
    if not kopf or kopf.group(1) not in MONATE:
        return []
    m0, m1, jahr = MONATE.index(kopf.group(1)) + 1, MONATE.index(kopf.group(2)) + 1, int(kopf.group(3))
    jahr_von = jahr - 1 if m0 > m1 else jahr                     # Heft über den Jahreswechsel
    teil = text[text.find("\nTERMINKALENDER"):]
    out = []
    for zeile in teil.splitlines():
        for m in TERMIN.finditer(zeile):
            _, tag, mon, titel, hh, mm, ort = m.groups()
            if titel.startswith("BIS "):                           # mehrtägiges (z. B. Filmfestival) – kommt aus eigener Quelle
                continue
            mon = int(mon)
            j = jahr_von if (m0 > m1 and mon >= m0) else jahr
            ort = ort.strip()
            out.append({"datum": f"{j}-{mon:02d}-{int(tag):02d}", "zeit": f"{int(hh):02d}:{mm}" if hh else "",
                        "titel": titel.strip(), "ort": ORTE.get(ort, ort), "sparte": "", "hinweis": "", "preis": "",
                        "url": pdf_url, "quelle": "Kulturkalender Schloss"})
        for m in AUSST.finditer(zeile):
            vt, vm, vj, bt, bm, bj, titel, ort = m.groups()
            von = f"20{vj}-{vm}-{vt}" if vt else f"{jahr_von}-{m0:02d}-01"
            out.append({"datum": von, "bis": f"20{bj}-{bm}-{bt}", "zeit": "", "titel": titel.strip(),
                        "ort": ORTE.get(ort.strip(), ort.strip()), "sparte": "Ausstellung & Führung", "hinweis": "", "preis": "",
                        "url": pdf_url, "quelle": "Kulturkalender Schloss"})
    return out


def abrufen():
    seite = _holen(SEITE).decode("utf-8", "replace")
    pdfs = sorted({urljoin(SEITE, h) for h in re.findall(r'href="([^"]*Kulturkalender[^"]*\.pdf)"', seite, re.I)})
    if not pdfs:
        raise RuntimeError("kein Kulturkalender-PDF auf der Seite gefunden")
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, url in enumerate(pdfs):
            pdf = Path(tmp) / f"{i}.pdf"
            pdf.write_bytes(_holen(url))
            subprocess.run(["pdftotext", "-layout", str(pdf), str(pdf.with_suffix(".txt"))], check=True)
            out += lesen(pdf.with_suffix(".txt").read_text(encoding="utf-8", errors="replace"), url)
    return out


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1:   # Test mit vorhandener Textdatei
        print(json.dumps(lesen(Path(sys.argv[1]).read_text(encoding="utf-8"), "test.pdf"), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(abrufen(), ensure_ascii=False, indent=1))
