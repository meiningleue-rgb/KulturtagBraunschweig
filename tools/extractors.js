// Kulturtag Braunschweig – Auslese-Bausteine
// Jede Quelle: eine Start-URL und eine Funktion, die IM BROWSER auf dieser Seite läuft
// und eine Liste von Terminen zurückgibt:
//   { datum:"JJJJ-MM-TT", zeit:"HH:MM"|"", bis:"JJJJ-MM-TT"|undefined, titel, ort, sparte, hinweis, url, quelle }
// Dieselben Funktionen nutzt das Python-Skript (über Playwright) und der wöchentliche Claude-Lauf (über Chrome).

const KULTURTAG_QUELLEN = [
  {
    id: "stadtkalender",
    name: "Stadtkalender (die-region.de)",
    startUrl: ({ start, end }) =>
      `https://braunschweig.die-region.de/?keyWord=&eventtype=&city=&startdate=${start}&enddate=${end}`,
    extract: async ({ start, end }) => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      // alle Seiten nachladen
      let prev = -1;
      for (let i = 0; i < 80; i++) {
        const n = document.querySelectorAll(".event-list__content").length;
        const b = document.querySelector("#event-loadmore");
        if (!b || !b.offsetParent || n === prev) break;
        prev = n; b.click(); await sleep(1200);
      }
      const MON = { januar:1, februar:2, "märz":3, maerz:3, april:4, mai:5, juni:6, juli:7, august:8, september:9, oktober:10, november:11, dezember:12 };
      const y0 = +start.slice(0, 4), m0 = +start.slice(5, 7);
      const toIso = (d, mName) => {
        const m = MON[mName.toLowerCase()]; if (!m) return null;
        const y = m < m0 ? y0 + 1 : y0;
        return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      };
      const t = el => (el?.innerText || "").replace(/\s+/g, " ").trim();
      const out = [];
      document.querySelectorAll(".event-list__content").forEach(c => {
        const a = c.querySelector("a");
        const dTxt = t(c.querySelector(".event-list__date"));
        const titel = t(c.querySelector("h2,h3,h4"));
        let rest = t(c).replace(t(c.querySelector(".Copyright-Image-Wrapper")), "").replace(dTxt, "").replace(titel, "").trim();
        const ds = [...dTxt.matchAll(/(\d{1,2})\.\s*([A-Za-zäÄ]+)/g)].map(m => toIso(m[1], m[2])).filter(Boolean);
        if (!ds.length) return;
        const tm = rest.match(/(\d{1,2}:\d{2})(?:\s*-\s*(\d{1,2}:\d{2}))?(?:\s*Uhr)?\s*$/);
        const zeit = tm ? tm[1].padStart(5, "0") : "";
        const ort = (tm ? rest.slice(0, tm.index) : rest).trim().replace(/,\s*\d{5}\s+Braunschweig$/, "");
        const abgesagt = /entf[äa]llt|abgesagt/i.test(titel);
        out.push({
          datum: ds[0], bis: ds[1] && ds[1] !== ds[0] ? ds[1] : undefined, zeit,
          titel: titel.replace(/^(ENTFÄLLT!?|Abgesagt!?)\s*/i, ""), ort, sparte: "",
          hinweis: abgesagt ? "ABGESAGT" : "", url: a ? a.href : location.href, quelle: "Stadtkalender",
        });
      });
      return out;
    },
  },
  {
    id: "tu",
    name: "TU Braunschweig (iCal)",
    startUrl: () => "https://magazin.tu-braunschweig.de/veranstaltungen/",
    extract: async ({ start, end }) => {
      const raw = await fetch("https://magazin.tu-braunschweig.de/tu-braunschweig-kalender.ics").then(r => r.text());
      const txt = raw.replace(/\r?\n[ \t]/g, "");
      const s0 = start.replace(/-/g, ""), s1 = end.replace(/-/g, "");
      // interne/organisatorische Formate ausfiltern
      const INTERN = /ersti|sprachtandem|lunch break|stammtisch|job-?expo|karriere|bewerb|nebenjob|zotero|webex|workshop|impulsh|lehrende|lehrpreis|matching|student quest|discover|volleyball|preschool|weiterbildung|netzwerk|open class|informationsveranstaltung|exkursion|kolloquium|tagung|symposium|conference|methodenwerkstatt|kids@campus|studierendennetzwerk|selbst- und zeitmanagement|literaturrecherche|eLabFTW|gruppenprozesse|nachhaltige entwicklung durch lehre/i;
      const clean = s => s.replace(/\\,/g, ",").replace(/\\;/g, ";").replace(/\\n/g, " ").replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
      return txt.split("BEGIN:VEVENT").slice(1).map(b => {
        const g = k => { const m = b.match(new RegExp("^" + k + "[^:\\n]*:(.*)$", "m")); return m ? clean(m[1]) : ""; };
        const ds = g("DTSTART"), titel = g("SUMMARY"), ort = g("LOCATION"), url = g("URL");
        return { ds, titel, ort, url };
      }).filter(e => e.ds.slice(0, 8) >= s0 && e.ds.slice(0, 8) <= s1)
        .filter(e => !/online|webex/i.test(e.ort) && !INTERN.test(e.titel))
        .map(e => ({
          datum: `${e.ds.slice(0, 4)}-${e.ds.slice(4, 6)}-${e.ds.slice(6, 8)}`,
          zeit: e.ds.length > 9 ? `${e.ds.slice(9, 11)}:${e.ds.slice(11, 13)}` : "",
          titel: e.titel.replace(/^Der Vortrag fällt leider aus!\s*/i, ""), ort: e.ort,
          sparte: "Wissenschaft & Vortrag",
          hinweis: /fällt .*aus|abgesagt/i.test(e.titel) ? "ABGESAGT" : "",
          url: e.url || "https://magazin.tu-braunschweig.de/veranstaltungen/", quelle: "TU-Kalender",
        }));
    },
  },
  {
    id: "staatstheater",
    name: "Staatstheater Braunschweig",
    startUrl: () => "https://staatstheater-braunschweig.de/programm/spielplan",
    extract: async ({ start, end }) => {
      const y0 = +start.slice(0, 4), m0 = +start.slice(5, 7);
      const out = [];
      document.querySelectorAll(".event-list-day").forEach(day => {
        const m = (day.querySelector(".event-list-day-date")?.textContent || "").match(/(\d{1,2})\.(\d{1,2})\./);
        if (!m) return;
        const mm = +m[2], y = mm < m0 ? y0 + 1 : y0;
        const datum = `${y}-${String(mm).padStart(2, "0")}-${m[1].padStart(2, "0")}`;
        if (datum < start || datum > end) return;
        day.querySelectorAll(".event-list-item-row").forEach(r => {
          const a = r.querySelector("a.event-list-item");
          const parts = (r.querySelector(".event-list-item-time")?.innerText || "").split("\n").map(s => s.trim()).filter(Boolean);
          const sp = (r.querySelector("p.bold")?.textContent || "").trim();
          const sub = (r.querySelector(".event-list-item-subtitle")?.textContent || "").replace(/\s+/g, " ").trim();
          const titel = (r.querySelector("h3")?.textContent || "").trim();
          if (/nur für Lehrkräfte|Lehrkräftefortbildung|Termin vergeben/i.test(sub + titel)) return;
          out.push({
            datum, zeit: parts[0] || "", ort: "Staatstheater, " + (parts[1] || ""), titel,
            sparte: /Staatsorchester|Konzert/i.test(sp + titel) ? "Musik" : /Junges/i.test(sp) ? "Kinder & Familie" : "Bühne",
            hinweis: [sp, sub].filter(Boolean).join(" · "),
            url: a ? a.href.split("?")[0] : location.href, quelle: "Staatstheater",
          });
        });
      });
      return out;
    },
  },
  {
    id: "mvp",
    name: "mvp.de",
    startUrl: () => "https://www.mvp.de/braunschweig/veranstaltungen/",
    extract: async ({ start, end }) => {
      const MON = { januar:1, februar:2, "märz":3, april:4, mai:5, juni:6, juli:7, august:8, september:9, oktober:10, november:11, dezember:12 };
      const iso = (d, m, y) => `${y}-${String(MON[m.toLowerCase()]).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const AUS = /Aktiv|Natur|Sport|Party|Clubbing|Electro|Techno|Messe|Markt|Essen|Dinner|Kulinar/i;
      const out = [];
      for (let from = 0; from <= 400; from += 40) {
        const h = await fetch(`/braunschweig/veranstaltungen/?from=${from}`).then(r => r.text());
        const doc = new DOMParser().parseFromString(h, "text/html");
        const cards = [...doc.querySelectorAll(".abl-card-body")];
        if (!cards.length) break;
        let beyond = 0;
        for (const c of cards) {
          const a = c.querySelector("h2 a, .abl-entry-name a");
          const spans = [...c.querySelectorAll("span")].map(s => s.textContent.trim()).filter(Boolean);
          const desc = (c.querySelector("p.description")?.textContent || "").replace(/\s+/g, " ").trim();
          const m = desc.match(/^(bis )?\w+, (\d{1,2})\. (\w+) (\d{4})/);
          if (!a || !m) continue;
          const datum = iso(m[2], m[3], m[4]);
          if (m[1]) continue; // "bis …": Dauerangebote überspringen
          if (datum > end) { beyond++; continue; }
          if (datum < start) continue;
          const kat = spans[0] || "";
          if (AUS.test(kat)) continue;
          const bisM = desc.match(/ bis \w+, (\d{1,2})\. (\w+) (\d{4})/);
          out.push({
            datum, bis: bisM ? iso(bisM[1], bisM[2], bisM[3]) : undefined, zeit: "",
            titel: a.textContent.trim().replace(/\s+-\s+BRAUNSCHWEIG$/i, "").replace(/\s+-\s+Braunschweig$/, ""),
            ort: (spans[1] || "").replace(/,\s*BRAUNSCHWEIG$/i, "").replace(/,\s*Braunschweig$/, ""),
            sparte: /^Kino/i.test(kat) ? "Kino" : /^Konzert/i.test(kat) ? "Musik" : /Kinder/i.test(kat) ? "Kinder & Familie" : /Kunst|Ausstellung/i.test(kat) ? "Ausstellung & Führung" : /Lesung|Vortr/i.test(kat) ? "Wissenschaft & Vortrag" : /Theater|Musical|Bühne|Comedy/i.test(kat) ? "Bühne" : "",
            hinweis: kat, url: new URL(a.getAttribute("href"), "https://www.mvp.de").href, quelle: "mvp.de",
          });
        }
        if (beyond > cards.length / 2) break;
      }
      return out;
    },
  },
  {
    id: "kinos",
    name: "Kinos (filmstarts.de)",
    startUrl: () => "https://www.filmstarts.de/kinoprogramm/kino/A1240/",
    extract: async ({ start, end }) => {
      const K = { A0284: "Astor Filmtheater", A1240: "Universum Filmtheater", A2389: "Roter Saal im Schloss", A2745: "SchunterKino" };
      const VER = { original: "OV", original_st: "OmU", original_sme: "OmU" };
      const days = [];
      for (let d = new Date(start + "T12:00:00"); d <= new Date(end + "T12:00:00"); d.setDate(d.getDate() + 1)) days.push(d.toISOString().slice(0, 10));
      const out = [];
      for (const id in K) for (const day of days) {
        let j; try { j = await fetch(`/_/showtimes/theater-${id}/d-${day}/`).then(r => r.json()); } catch (e) { continue; }
        for (const r of (j.results || [])) {
          const times = [], ov = new Set();
          for (const k in (r.showtimes || {})) for (const s of (r.showtimes[k] || []))
            if (s.startsAt && s.startsAt.startsWith(day)) { times.push(s.startsAt.slice(11, 16)); if (VER[k]) ov.add(VER[k]); }
          if (!times.length || !r.movie?.title) continue;
          times.sort();
          out.push({
            datum: day, zeit: times[0], titel: r.movie.title, ort: K[id], sparte: "Kino",
            hinweis: [[...ov].join("/"), times.length > 1 ? "Vorstellungen: " + times.join(", ") : ""].filter(Boolean).join(" · "),
            url: `https://www.filmstarts.de/kinoprogramm/kino/${id}/#shwt_date=${day}`, quelle: "filmstarts.de",
          });
        }
      }
      return out;
    },
  },
  {
    id: "biff",
    name: "Braunschweig International Film Festival (BIFF)",
    startUrl: () => "https://vp.eventival.com/biff/40/film-schedule",   // Ausgabe 40 = 2026; jährlich anpassen
    extract: async ({ start, end }) => {
      const t = el => (el?.textContent || "").replace(/\s+/g, " ").trim();
      const days = [];
      for (let d = new Date(start + "T12:00:00"); d <= new Date(end + "T12:00:00"); d.setDate(d.getDate() + 1)) days.push(d.toISOString().slice(0, 10));
      const out = [];
      for (const day of days) {
        let doc; try { doc = new DOMParser().parseFromString(await fetch(location.pathname + "?day=" + day).then(r => r.text()), "text/html"); } catch (e) { continue; }
        doc.querySelectorAll(".d-block.d-sm-none .schedule-card").forEach(c => {       // mobile Ansicht: jede Vorführung genau einmal
          const typ = t(c.querySelector(".screening-type")), titel = t(c.querySelector(".title")), ort = t(c.querySelector(".venue-name"));
          if (!titel || /Akkreditierte|Schulklassen/.test(typ) || /Ticketvorverkauf/i.test(titel) || /Wolfsburg/.test(ort)) return;
          const pop = /^BIFF Pop Up/i.test(titel);
          out.push({
            datum: day, zeit: t(c.querySelector(".time")), titel: pop ? titel.replace(" - ", ": ") : "BIFF: " + titel,
            ort: ort.replace(/^Astor Filmtheater, ASTOR (\d)/, "Astor Filmtheater (ASTOR $1)").replace(/^Universum Filmtheater, Universum (\d)/, "Universum Filmtheater (Saal $1)") || "BIFF Pop Up Space",
            sparte: pop ? "" : /im gespräch|werkstattgespräch/i.test(titel) ? "Wissenschaft & Vortrag" : "Kino",
            hinweis: ["Braunschweig International Film Festival", typ, t(c.querySelector(".duration"))].filter(Boolean).join(" · "),
            url: "https://vp.eventival.com" + location.pathname + "?day=" + day, quelle: "BIFF",
          });
        });
      }
      return out;
    },
  },
  // ---------------------------------------------------------------- Spielstätten direkt
  {
    id: "brunsviga",
    name: "Brunsviga (Programm)",
    startUrl: () => "https://www.brunsviga-kulturzentrum.de/programm/",
    extract: async ({ start, end }) => {
      const MON = { januar:1, februar:2, "märz":3, april:4, mai:5, juni:6, juli:7, august:8, september:9, oktober:10, november:11, dezember:12 };
      const t = el => (el?.textContent || "").replace(/\s+/g, " ").trim();
      const out = [], seen = new Set();
      document.querySelectorAll(".article.articletype-0").forEach(art => {
        const a = art.querySelector('a[href*="veranstaltungsdetails"]'); if (!a) return;
        const dm = t(art.querySelector(".datetime .date")).match(/(\d{1,2})\.\s*([A-Za-zäÄ]+)\s+(\d{4})/); if (!dm) return;
        const mo = MON[dm[2].toLowerCase()]; if (!mo) return;
        const datum = `${dm[3]}-${String(mo).padStart(2, "0")}-${dm[1].padStart(2, "0")}`;
        if (datum < start || datum > end || art.classList.contains("postponed")) return;   // verlegt -> nicht an diesem Tag
        const zm = t(art.querySelector(".datetime .time")).match(/(\d{1,2}):(\d{2})/);
        const kopf = t(art.querySelector(".header h2")), unter = t(art.querySelector(".header h3"));
        if (!kopf) return;
        const titel = unter ? `${kopf} – ${unter}` : kopf;
        if (seen.has(datum + titel)) return; seen.add(datum + titel);
        out.push({
          datum, zeit: zm ? `${zm[1].padStart(2, "0")}:${zm[2]}` : "", titel, ort: "Brunsviga, Karlstraße 35", sparte: "",
          hinweis: art.classList.contains("cancled") ? "ABGESAGT" : art.classList.contains("soldout") ? "Ausverkauft" : "",
          url: a.href.split("?")[0], quelle: "Brunsviga",
        });
      });
      return out;
    },
  },
  {
    id: "westand",
    name: "westand (Programm)",
    startUrl: () => "https://westand.net/aktuelles-programm/",
    extract: async ({ start, end }) => {
      // Programm wird per Skript nachgeladen: kurz warten, bis die Einträge da sind
      for (let i = 0; i < 20 && !document.querySelector(".programmevents a.event"); i++) await new Promise(r => setTimeout(r, 500));
      const t = el => (el?.innerText || "").replace(/\s+/g, " ").trim();
      const out = [];
      document.querySelectorAll(".programmevents a.event").forEach(a => {
        const dz = t(a.querySelector(".eventdatumuhrzeit"));            // "08.11.2026 | 16:00 & 18:30 Uhr"
        const m = dz.match(/(\d{1,2})\.(\d{1,2})\.(\d{4})/); if (!m) return;
        const datum = `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
        if (datum < start || datum > end) return;
        const zeiten = [...dz.replace(/^[^|]*\|/, "").matchAll(/(\d{1,2})[:.](\d{2})/g)].map(x => x[1].padStart(2, "0") + ":" + x[2]);
        const kopf = t(a.querySelector(".eventueberschrift")), unter = t(a.querySelector(".eventuntertitel"));
        const besch = t(a.querySelector(".eventbeschreibung")), preis = t(a.querySelector(".eventpreis"));
        if (!kopf) return;
        const alles = [unter, besch, preis].join(" ");
        const abgesagt = /abgesagt|fällt aus|entfällt/i.test(alles);
        out.push({
          datum, zeit: zeiten[0] || "",
          titel: unter && !/^(abgesagt|ausverkauft)!?$/i.test(unter) ? `${kopf} – ${unter}` : kopf,
          ort: "westand, Westbahnhof 13", sparte: "",
          hinweis: abgesagt ? "ABGESAGT" : [zeiten.length > 1 ? "Vorstellungen: " + zeiten.join(", ") : "",
            /ausverkauft/i.test(alles) ? "Ausverkauft" : "", besch.length > 3 ? besch : ""].filter(Boolean).join(" · "),
          preis: /€/.test(preis) ? preis : "", url: a.href, quelle: "westand",
        });
      });
      return out;
    },
  },
  {
    id: "schoenfroelich",
    name: "Schön & Frölich (Programm)",
    startUrl: () => "https://www.xn--schnfrlich-gcbd.de/",
    extract: async ({ start, end }) => {
      const t = el => (el?.textContent || "").replace(/\s+/g, " ").trim();
      const out = [];
      document.querySelectorAll(".events-grid .event-item").forEach(it => {
        const card = it.querySelector(".event-card"); if (!card) return;
        if (card.classList.contains("card-style-party")) return;               // Partyreihen auslassen
        const titel = t(card.querySelector(".event-info h2"));
        const dm = t(card.querySelector(".event-info p")).match(/(\d{1,2})\.(\d{1,2})\.(\d{4})/);
        if (!titel || !dm) return;
        const datum = `${dm[3]}-${dm[2].padStart(2, "0")}-${dm[1].padStart(2, "0")}`;
        if (datum < start || datum > end) return;
        const info = t(it.querySelector(".info-panel-content"));               // ausgeklappter Infotext (versteckt)
        const zm = info.match(/Beginn\D{0,12}(\d{1,2})[:.](\d{2})/i) || info.match(/(\d{1,2})[:.](\d{2})\s*Uhr/);
        const em = info.match(/Einlass\D{0,12}(\d{1,2})[:.](\d{2})/i);
        const ticket = card.querySelector(".event-buttons a[href]");
        out.push({
          datum, zeit: zm ? `${zm[1].padStart(2, "0")}:${zm[2]}` : "", titel, ort: "Schön & Frölich, Broitzemer Straße 220", sparte: "",
          hinweis: /abgesagt|fällt aus|entfällt/i.test(info + titel) ? "ABGESAGT" : [em ? `Einlass ${em[1].padStart(2, "0")}:${em[2]}` : "", /ausverkauft/i.test(info) ? "Ausverkauft" : ""].filter(Boolean).join(" · "),
          url: ticket ? ticket.href : location.href, quelle: "Schön & Frölich",
        });
      });
      return out;
    },
  },
  {
    id: "jazzbs",
    name: "Initiative Jazz Braunschweig",
    startUrl: () => "https://www.jazzbs.de/category/konzerte/?future=true",
    extract: async ({ start, end }) => {
      const out = [];
      document.querySelectorAll("article.category-konzerte").forEach(art => {
        const tm = art.querySelector("time[datetime]"); const h = art.querySelector(".entry-title");
        if (!tm || !h) return;
        const dt = tm.getAttribute("datetime"), datum = dt.slice(0, 10);
        if (datum < start || datum > end) return;
        const titel = h.innerText.split("\n").map(s => s.trim()).filter(Boolean).join(" – ");
        const ortLink = art.querySelector(".entry-content a");
        const ort = (ortLink?.textContent || "").replace(/,\s*\d{5}\s+Braunschweig$/, "").trim() || "Roter Saal im Schloss, Schlossplatz 1";
        out.push({
          datum, zeit: dt.slice(11, 16), titel, ort, sparte: "Musik",
          hinweis: /abgesagt|fällt aus|entfällt/i.test(art.textContent) ? "ABGESAGT" : "Jazz",
          url: (art.querySelector(".entry-title a")?.href || location.href).replace(/&future=true/, ""), quelle: "Jazz Braunschweig",
        });
      });
      return out;
    },
  },
  {
    id: "graff",
    name: "Buchhandlung Graff",
    startUrl: () => "https://www.graff.de/veranstaltung",
    extract: async ({ start, end }) => {
      const MON = { januar:1, februar:2, "märz":3, april:4, mai:5, juni:6, juli:7, august:8, september:9, oktober:10, november:11, dezember:12 };
      const y0 = +start.slice(0, 4), m0 = +start.slice(5, 7);
      const t = el => (el?.innerText || el?.textContent || "").replace(/\s+/g, " ").trim();
      for (let i = 0; i < 30 && !document.querySelector(".event-compact"); i++) await new Promise(r => setTimeout(r, 500));   // Liste kommt verzögert
      const out = [];
      document.querySelectorAll(".event-compact").forEach(ev => {
        const dm = t(ev.querySelector(".field--name-field-datum")).match(/(\d{1,2})\.\s*([A-Za-zäÄ]+)/); if (!dm) return;
        const mo = MON[dm[2].toLowerCase()]; if (!mo) return;
        const datum = `${mo < m0 ? y0 + 1 : y0}-${String(mo).padStart(2, "0")}-${dm[1].padStart(2, "0")}`;
        if (datum < start || datum > end) return;
        const zm = t(ev.querySelector(".orange-banner")).match(/(\d{1,2}):(\d{2})/);
        const kopf = t(ev.querySelector("h2.event-headline")), unter = t(ev.querySelector(".field--name-field-subtitle"));
        if (!kopf) return;
        const a = ev.querySelector('a[href*="/veranstaltung/"]');
        out.push({
          datum, zeit: zm ? `${zm[1].padStart(2, "0")}:${zm[2]}` : "", titel: unter ? `${kopf} – ${unter}` : kopf,
          ort: "Buchhandlung Graff", sparte: /kinder|vorlesen|lesen vor/i.test(kopf + unter) ? "Kinder & Familie" : "Literatur & Bibliothek",
          hinweis: /ausverkauft/i.test(t(ev)) ? "Ausverkauft" : "", url: a ? a.href.split("?")[0] : location.href, quelle: "Graff",
        });
      });
      return out;
    },
  },
  {
    id: "daskult",
    name: "Das KULT (Programm)",
    startUrl: () => "https://www.daskult-theater.de/demn%C3%A4chst.html",
    extract: async ({ start, end }) => {
      // Programm ist Fließtext: Zeilen wie "Freitag 06.11. I 20 Uhr I JAZZ-Freitag …" oder
      // "So. 01./Mo. 02./Di.03. jeweils 19:30 Werkschau …"; Monatsüberschriften "November 2026" liefern das Jahr.
      const MON = { januar:1, februar:2, "märz":3, april:4, mai:5, juni:6, juli:7, august:8, september:9, oktober:10, november:11, dezember:12 };
      const WT = /^(Mo|Di|Mi|Do|Fr|Sa|So)[a-z]*\.?\s*\d/i;
      const AUS = /3 Gänge Menü|Karaoke|Menü-ticket/i;
      const lines = document.body.innerText.split("\n").map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean);
      let curM = 0, curY = +start.slice(0, 4), last = "";
      const out = [], seen = new Set();
      for (const line of lines) {
        const mh = line.match(/^(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(20\d\d)$/i);
        if (mh) { curM = MON[mh[1].toLowerCase()]; curY = +mh[2]; continue; }
        if (!WT.test(line) || !curM) continue;
        const dRe = /\b(\d{1,2})\.(?:(\d{1,2})\.?(?:(\d{2,4}))?)?(?=[\s\/,I|]|$)/g;
        // Datumsteil = alles vor der Uhrzeit
        const zeitM = line.match(/(?:^|[\sI|])(\d{1,2})(?:[:.](\d{2}))?\s*Uhr/i) || line.match(/(?:^|\s)(\d{1,2}):(\d{2})(?!\d)/);
        const cut = zeitM ? line.indexOf(zeitM[0]) : line.length;
        const kopfTeil = line.slice(0, cut);
        const daten = [...kopfTeil.matchAll(dRe)].map(m => {
          const mo = m[2] ? +m[2] : curM; const y = m[3] ? (+m[3] < 100 ? 2000 + +m[3] : +m[3]) : (mo < curM ? curY + 1 : curY);
          return `${y}-${String(mo).padStart(2, "0")}-${m[1].padStart(2, "0")}`;
        });
        if (!daten.length) continue;
        let titel = (zeitM ? line.slice(cut + zeitM[0].length) : "").replace(/^[\sI|:–-]+/, "").replace(/^(Uhr)\s*/i, "").replace(/^[\sI|:–-]+/, "").trim();
        if (!titel || /^(Premiere|Aufführung|Vorstellung)/i.test(titel)) titel = last ? last + (/Premiere/i.test(titel) ? " (Premiere)" : "") : titel;
        else last = titel.replace(/\s*\(Premiere\)$/, "");
        if (!titel || AUS.test(titel)) continue;
        const zeit = zeitM ? `${zeitM[1].padStart(2, "0")}:${zeitM[2] || "00"}` : "";
        for (const datum of daten) {
          if (datum < start || datum > end) continue;
          const k = datum + "|" + titel.replace(/\s*\(Premiere\)$/, "").toLowerCase();
          if (seen.has(k)) continue; seen.add(k);
          out.push({ datum, zeit, titel: titel.replace(/^"(.*)"$/, "$1"), ort: "Das KULT, Hamburger Straße 273 (Eingang C2)", sparte: "",
            hinweis: /hutkasse/i.test(titel) ? "Hutkasse" : "", url: location.href.split("?")[0], quelle: "Das KULT" });
        }
      }
      return out;
    },
  },
  {
    // Sammelkalender „ForschungRegion Braunschweig“: PTB, DLR, HZI, GEI, Thünen, JKI, Fraunhofer, BWG, TU, HBK, Ostfalia, Museen …
    id: "hausderwissenschaft",
    name: "Haus der Wissenschaft (Forschungsregion)",
    startUrl: () => "https://www.hausderwissenschaft.org/veranstaltungskalender.html",
    extract: async ({ start, end }) => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      const t = el => (el?.textContent || "").replace(/\s+/g, " ").trim();
      for (let i = 0; i < 40 && !document.querySelector(".terminitem"); i++) await sleep(250);   // Liste kommt per Ajax
      const lies = doc => [...doc.querySelectorAll(".terminitem")].map(it => {
        const sd = it.querySelector('[itemprop="startDate"]')?.getAttribute("content") || "";
        const unter = [...it.querySelectorAll(".col-xs-10 > *")].find(x => x.tagName !== "H5" && !x.querySelector('[class*="dfx-datum"]')
          && !x.matches('[itemprop="location"]') && !x.matches("a.detaillink"));
        return { sd, titel: t(it.querySelector('[itemprop="name"]')), unter: t(unter), lokal: t(it.querySelector('[class*="dfx-lokal"]')),
                 stadt: t(it.querySelector('[itemprop="addressLocality"]')), zeitTxt: t(it.querySelector('[class*="dfx-zeit"]')) };
      });
      // Seiten 2 ff. werden in unsichtbaren Rahmen geladen (gleiche Seite mit ?dfxp=N)
      const alle = [];
      for (let p = 1; p <= 15; p++) {
        let doc = document;
        if (p > 1) {
          const f = document.createElement("iframe"); f.style.display = "none";
          f.src = location.pathname + "?dfxp=" + p; document.body.appendChild(f);
          for (let i = 0; i < 40 && !f.contentDocument?.querySelector(".terminitem"); i++) await sleep(250);
          doc = f.contentDocument;
        }
        const neu = doc ? lies(doc) : [];
        if (!neu.length) break;
        alle.push(...neu);
        if (neu[neu.length - 1].sd.slice(0, 10) > end) break;
      }
      const roh = alle.filter(e => e.sd && e.titel && e.sd.slice(0, 10) >= start && e.sd.slice(0, 10) <= end
        && (!e.stadt || /braunschweig/i.test(e.stadt)));                                            // nur Braunschweig
      // Ausstellungen erscheinen als tägliche Öffnungszeiten -> zu einem laufenden Angebot zusammenfassen
      const nTitel = {}; roh.forEach(e => nTitel[e.titel] = (nTitel[e.titel] || 0) + 1);
      const out = [], lauf = {};
      for (const e of roh) {
        const datum = e.sd.slice(0, 10), zeit = e.sd.slice(11, 16);
        const ort = e.lokal;
        if (nTitel[e.titel] >= 4) {
          const l = lauf[e.titel] || (lauf[e.titel] = { datum, bis: datum, zeit: "", titel: e.titel, ort, sparte: "Ausstellung & Führung",
            hinweis: "Öffnungszeiten u. a. " + e.zeitTxt.replace(/^\|\s*/, ""), url: location.href.split("?")[0], quelle: "Haus der Wissenschaft" });
          if (datum > l.bis) l.bis = datum;
          continue;
        }
        out.push({ datum, zeit, titel: e.unter && e.unter.length < 90 ? `${e.titel} – ${e.unter}` : e.titel, ort, sparte: "",
          hinweis: /abgesagt|entfällt|fällt aus/i.test(e.titel + e.unter) ? "ABGESAGT" : "", url: location.href.split("?")[0], quelle: "Haus der Wissenschaft" });
      }
      return out.concat(Object.values(lauf));
    },
  },
  {
    id: "hbk",
    name: "HBK Braunschweig (Veranstaltungen)",
    startUrl: () => "https://www.hbk-bs.de/aktuelles/veranstaltungen/",
    extract: async ({ start, end }) => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      const t = el => (el?.textContent || "").replace(/\s+/g, " ").trim();
      const y0 = +start.slice(0, 4), m0 = +start.slice(5, 7);
      const iso = s => { const m = (s || "").match(/(\d{1,2})\.(\d{1,2})\.(\d{4})?/); if (!m) return "";
        const mo = +m[2], y = m[3] ? +m[3] : (mo < m0 - 4 ? y0 + 1 : y0); return `${y}-${String(mo).padStart(2, "0")}-${m[1].padStart(2, "0")}`; };
      // Liste ist nach Beginn sortiert: „Mehr laden“ klicken, bis Einträge hinter dem Zeitraum beginnen
      for (let i = 0; i < 15; i++) {
        const items = document.querySelectorAll(".c-events-list__item");
        const lastStart = iso(t(items[items.length - 1]?.querySelector(".c-events-list__start")));
        const btn = [...document.querySelectorAll("button")].find(b => /mehr laden/i.test(b.textContent) && b.offsetParent);
        if (!btn || (lastStart && lastStart > end)) break;
        const n = items.length; btn.click();
        for (let k = 0; k < 20 && document.querySelectorAll(".c-events-list__item").length === n; k++) await sleep(300);
      }
      const WTAGE = { montag: 1, dienstag: 2, mittwoch: 3, donnerstag: 4, freitag: 5, samstag: 6, sonntag: 0 };
      const out = [];
      document.querySelectorAll(".c-events-list__item").forEach(it => {
        const von = iso(t(it.querySelector(".c-events-list__start"))), bis = iso(t(it.querySelector(".c-events-list__end"))) || von;
        if (!von || von > end || bis < start) return;
        const titel = t(it.querySelector(".c-events-list__header h3")), kat = t(it.querySelector(".c-events-list__category"));
        const teaser = t(it.querySelector(".c-events-list__teaser"));
        const a = it.querySelector(".c-events-list__header a"); const url = a ? a.href.split("?")[0] : location.href;
        if (!titel) return;
        if (/Berlin|Hamburg|Hannover|Leipzig|Saarbrücken|Wolfsburg|Kassel|München|Köln/.test(teaser) && !/Braunschweig/.test(teaser)) return;  // auswärts
        const zm = teaser.match(/(\d{1,2})(?:[:.](\d{2}))?\s*Uhr/);
        const zeit = zm ? `${zm[1].padStart(2, "0")}:${zm[2] || "00"}` : "";
        const base = { titel, ort: "HBK Braunschweig, Johannes-Selenka-Platz 1", sparte: /film/i.test(kat + titel) ? "Kino" : /ausstellung/i.test(kat) ? "Ausstellung & Führung" : "",
                       hinweis: kat, url, quelle: "HBK" };
        if (/Externe/i.test(kat)) {                                      // externer Ort: nur, wenn in Braunschweig
          if (!/Braunschweig/.test(teaser)) return;
          const om = teaser.match(/(?:im|in der|in den)\s+((?:Städtischen\s+)?[A-ZÄÖÜ][\wäöüß-]*(?:\s+[A-ZÄÖÜ][\wäöüß-]*){0,3})/);
          base.ort = om ? om[1].replace(/^Städtischen/, "Städtisches") : "Braunschweig";
        }
        const wt = teaser.toLowerCase().match(/(?:immer\s+)?(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)s/);
        if (bis > von && wt && zeit) {                                   // Reihe: wöchentliche Einzeltermine
          for (let d = new Date((von > start ? von : start) + "T12:00:00"); d.toISOString().slice(0, 10) <= (bis < end ? bis : end); d.setDate(d.getDate() + 1))
            if (d.getDay() === WTAGE[wt[1]]) out.push({ ...base, datum: d.toISOString().slice(0, 10), zeit });
        } else if (bis > von) out.push({ ...base, datum: von, bis, zeit: "" });
        else out.push({ ...base, datum: von, zeit });
      });
      return out;
    },
  },
];

if (typeof module !== "undefined") module.exports = { KULTURTAG_QUELLEN };
