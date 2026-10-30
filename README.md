# Kulturtag Braunschweig

Tagesübersicht kultureller Veranstaltungen in Braunschweig – Theater, Konzerte, Kino, Lesungen, Vorträge, Ausstellungen – aus 15 Quellen zusammengeführt, Dubletten zusammengelegt.

**Seite:** wird über GitHub Pages veröffentlicht (Adresse unter *Settings → Pages*). Auf dem iPhone in Safari öffnen → Teilen → „Zum Home-Bildschirm“, dann verhält sie sich wie eine App. Die Merkliste wird pro Gerät gespeichert.

Alle Angaben ohne Gewähr – jeder Termin verlinkt auf die Originalquelle, dort gilt, was dort steht.

## Wie es läuft

- `.github/workflows/abruf.yml` ruft sonntags und donnerstags alle Quellen ab (headless Chromium über Playwright), baut `index.html` und veröffentlicht sie. Manuell: *Actions → Termine abrufen → Run workflow* (geht auch in der GitHub-App).
- `tools/extractors.js` – eine Auslese-Funktion je Quelle, läuft im Browser auf der jeweiligen Seite.
- `tools/kulturtag.py` – Abruf, Zusammenführen, Dubletten, Sparten; `--github .` schreibt Rohdaten nach `daten/roh/` und die Seite nach `index.html`.
- Scheitert eine Quelle, bleiben ihre Rohdaten vom letzten erfolgreichen Abruf stehen; im Kasten „Abrufstand“ steht dann „älterer Abruf“.

Lokal: `pip install playwright && python -m playwright install chromium`, dann `python tools/kulturtag.py --github .`

## Bekannte Lücken

- Kulturkalender Schloss / Roter Saal gibt es nur als PDF; der Datenstand ist vom 30.10.2026 und wird nicht automatisch erneuert.
- BIFF: Die Ausgabe-Nummer in `extractors.js` (2026 = 40) muss jährlich hochgezählt werden.
