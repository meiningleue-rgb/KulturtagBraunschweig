# Kulturtag Braunschweig

Tagesübersicht kultureller Veranstaltungen in Braunschweig – Theater, Konzerte, Kino, Lesungen, Vorträge, Ausstellungen, dazu Heimspiele von Basketball Löwen (BBL) und MTV Braunschweig Handball (3. Liga) – aus 17 Quellen zusammengeführt, Dubletten zusammengelegt.

**Seite:** wird über GitHub Pages veröffentlicht (Adresse unter *Settings → Pages*) und ist mit einem Passwort geschützt (StatiCrypt; „Auf diesem Gerät merken“ ist vorbelegt, in der entschlüsselten Seite gibt es außerdem einen „Zugangslink“, der ohne Passworteingabe öffnet). Das Passwort steht als Repository-Geheimnis `KULTURTAG_PASSWORT` unter *Settings → Secrets and variables → Actions*; nach einer Änderung einmal „Run workflow“ ausführen. Auf dem iPhone in Safari öffnen → Teilen → „Zum Home-Bildschirm“, dann verhält sie sich wie eine App. Die Merkliste wird pro Gerät gespeichert.

Ausführliche Erklärung für Nicht-Programmierer: [ERKLAERUNG.md](ERKLAERUNG.md)

Alle Angaben ohne Gewähr – jeder Termin verlinkt auf die Originalquelle, dort gilt, was dort steht.

## Wie es läuft

- `.github/workflows/abruf.yml` ruft sonntags und donnerstags alle Quellen ab (headless Chromium über Playwright), baut `index.html` und veröffentlicht sie. Manuell: *Actions → Termine abrufen → Run workflow* (geht auch in der GitHub-App).
- `tools/extractors.js` – eine Auslese-Funktion je Quelle, läuft im Browser auf der jeweiligen Seite.
- `tools/kulturtag.py` – Abruf, Zusammenführen, Dubletten, Sparten; `--github .` schreibt Rohdaten nach `daten/roh/` und die Seite nach `index.html`.
- Termine und Rohdaten liegen nicht im Repository, nur verschlüsselt auf der Seite. Die Rohdaten werden zwischen den Läufen im Actions-Zwischenspeicher gehalten: scheitert eine Quelle, bleibt ihr letzter Stand stehen („älterer Abruf“).

Lokal: `pip install playwright && python -m playwright install chromium`, dann `python tools/kulturtag.py --github .`

## Bekannte Lücken

- Kulturkalender Schloss / Roter Saal: nur als PDF, wird mit `tools/roter_saal.py` (pdftotext) aus dem Terminkalender am Heftende gelesen.
- Raabe-Haus: Veranstaltungsblatt (PDF) von braunschweig.de/literaturzentrum, gelesen mit `tools/raabe_haus.py`; enthält auch Lesungen bei Partnern (z. B. Buchhandlung Bücherwurm).
- Buchhandlung Graff ist nicht dabei: ihre Seite ist gegen automatische Abrufe geschützt (Anubis).
- Sport (`tools/sport.py`): Basketball über die Spielplan-Tabelle von hessenschau.de, Handball über handball.net (Team-Kennung `63819` = Saison 2026/27). Andere Sportquellen (z. B. Basketball/Handball im Stadtkalender) werden aussortiert, damit nichts doppelt erscheint. Zur neuen Saison Kennungen prüfen.
- BIFF: Die Ausgabe-Nummer in `extractors.js` (2026 = 40) muss jährlich hochgezählt werden.
