# Kulturtag Braunschweig – was hier gebaut wurde

*Stand: 30.10.2026*

Stell dir einen fleißigen Praktikanten vor, der zweimal pro Woche alle Kulturprogramme Braunschweigs abklappert, alles auf einen Zettel schreibt, Doppeltes streicht und den Zettel in einen abgeschlossenen Schaukasten hängt. Genau das passiert hier – nur ohne Kaffeepausen.

## Die Bausteine

### 1. Die Quellen (15)
Stadtkalender (die-region.de), Staatstheater, Kinos (über filmstarts.de: Astor, Universum, Roter Saal, SchunterKino), Filmfestival BIFF, mvp.de, Brunsviga, westand, Schön & Frölich, Initiative Jazz, Das KULT, TU Braunschweig, HBK, Haus der Wissenschaft (Sammelkalender der Forschungseinrichtungen), Kulturkalender Schloss (Roter Saal, Stadtbibliothek, Museen) und Raabe-Haus.

Jede Quelle ist anders aufgebaut, deshalb gibt es für jede ein kleines eigenes Leseprogramm in `tools/extractors.js`. Zwei Quellen gibt es nur als PDF; dafür gibt es eigene PDF-Leser: `tools/roter_saal.py` (Kulturkalender Schloss) und `tools/raabe_haus.py` (Veranstaltungsblatt des Raabe-Hauses).

Nicht dabei: Buchhandlung Graff – ihre Seite ist bewusst gegen automatische Abrufe geschützt.

### 2. Der „Roboter“ (GitHub Actions)
GitHub stellt kostenlos Rechner bereit, die nach Zeitplan Aufgaben erledigen. Unser Zeitplan steht in `.github/workflows/abruf.yml`: **sonntags und donnerstags um 10:43 Uhr** (im Sommer 11:43). Donnerstags, weil die Kinos dann ihre neue Woche veröffentlichen. Kein eigener Rechner muss dafür laufen.

### 3. Der Browser ohne Bildschirm
Viele Programmseiten bauen sich erst im Browser zusammen. Der Roboter startet deshalb einen echten, aber unsichtbaren Chrome-Browser (Chromium), öffnet jede Seite und liest die Termine heraus.

### 4. Das Zusammenführen (`tools/kulturtag.py`)
- **Doppelte erkennen:** Steht dieselbe Veranstaltung z. B. im Stadtkalender *und* beim Staatstheater, wird daraus ein Eintrag mit beiden Quellen als Link.
- **Sparten zuordnen:** Bühne, Musik, Kino, Literatur, Vortrag … – teils aus dem Titel geschätzt.
- **Ausstellungen** erscheinen als „läuft an diesem Tag“ statt täglich neu.
- **Ausfallsicherung:** Fällt eine Quelle aus, wird ihr letzter Stand genommen. Im Kasten „Abrufstand“ steht dann „älterer Abruf“.

### 5. Die Seite
Eine einzige Datei mit Tagesleiste, Suche über mehrere Tage (Stichwort, Ort, Musikrichtung), Sparten- und Zeitfiltern und einer Merkliste. Die Merkliste speichert jedes Gerät für sich.

### 6. Das Schloss (StatiCrypt)
Bevor die Seite online geht, wird sie mit dem Passwort verschlüsselt. Im Netz liegt nur unlesbarer Text plus ein Passwortfeld; erst der Browser entschlüsselt die Seite nach Eingabe des Passworts. „Auf diesem Gerät merken“ hält 90 Tage. Das Passwort liegt als *Geheimnis* bei GitHub und ist dort nicht auslesbar.

Wichtig: Weil sich jeder die verschlüsselte Datei herunterladen und offline raten kann, sollte das Passwort lang sein (ein Satz aus 4–5 Wörtern).

### 7. Die Veröffentlichung (GitHub Pages)
Die verschlüsselte Seite kommt auf `meiningleue-rgb.github.io/KulturtagBraunschweig`. Suchmaschinen werden gebeten, sie nicht aufzunehmen.

### 8. Besucherzähler (GoatCounter)
Ein kleiner, cookiefreier Zähler zählt Aufrufe der *entschlüsselten* Seite – also nur von Leuten mit Passwort. Er zeigt Aufrufe pro Tag, Gerätetyp und ungefähres Land, aber nicht, *wer* zugreift. Eingeschaltet wird er über die Repository-Variable `GOATCOUNTER` (der Name des eigenen GoatCounter-Kontos, z. B. `kulturtag-bs`).

### 9. Lebenszeichen
GitHub schaltet Zeitpläne in öffentlichen Repositories ab, wenn dort 60 Tage nichts passiert. Deshalb schreibt der Roboter einmal im Monat das Datum in `lebenszeichen.txt`.

## Was wo liegt

| Wo | Was |
|---|---|
| Öffentlich im Repository | nur der Bauplan: Leseprogramme, Zeitplan, Seitenvorlage, diese Erklärung |
| Verschlüsselt im Netz | die fertige Seite mit allen Terminen |
| Unsichtbar bei GitHub | Passwort (Geheimnis), Zwischenspeicher der Rohdaten |

## Was kaputtgehen kann

- **Eine Quelle baut ihre Webseite um** → sie liefert nichts mehr, ihr alter Stand läuft langsam aus („älterer Abruf“ im Abrufstand). Dann muss ihr Leseprogramm angepasst werden.
- **Ein neues Programmheft-PDF liegt an anderer Stelle** → dasselbe.
- **BIFF:** Die Ausgabe-Nummer (2026 = 40) in `tools/extractors.js` muss jährlich hochgezählt werden.
- **Ein Lauf schlägt fehl** → GitHub schickt eine Mail; die Seite bleibt mit dem letzten Stand online.

## Was du selbst tun kannst

- **Neu abrufen:** Actions → „Termine abrufen“ → „Workflow ausführen“.
- **Passwort ändern:** Einstellungen → Secrets and variables → Actions → `KULTURTAG_PASSWORT` ändern, dann einmal neu abrufen. Danach brauchen alle das neue Passwort.
- **Besucherzahlen ansehen:** im eigenen GoatCounter-Konto.
- **Alles anhalten:** Actions → „Termine abrufen“ → Workflow deaktivieren. Die Seite bleibt mit dem letzten Stand stehen.
