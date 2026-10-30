import re, subprocess, pathlib, requests, traceback
out = pathlib.Path("diag/out"); out.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
H = {"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9", "Accept": "text/html,application/xhtml+xml,*/*"}
log = []
# --- Graff mit einfacher HTTP-Anfrage
for url in ["https://www.graff.de/veranstaltung", "https://www.graff.de/rss.xml", "https://www.graff.de/veranstaltung/rss.xml", "https://www.graff.de/sitemap.xml"]:
    try:
        r = requests.get(url, headers=H, timeout=30)
        name = re.sub(r"\W+", "_", url.split("//")[1])
        (out / f"{name}.txt").write_text(r.text[:400000], encoding="utf-8")
        log.append(f"{url}: {r.status_code} {len(r.text)} Zeichen, event-compact: {r.text.count('event-compact')}")
    except Exception as e:
        log.append(f"{url}: FEHLER {e}")
# --- Graff mit Playwright
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-http2"]); pg = b.new_page(user_agent=UA, locale="de-DE")
        r = pg.goto("https://www.graff.de/veranstaltung", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(5000)
        html = pg.content(); (out / "graff_playwright.html").write_text(html, encoding="utf-8")
        log.append(f"graff playwright: {r.status if r else '?'} {len(html)} Zeichen, event-compact: {html.count('event-compact')}, Titel: {pg.title()}")
        b.close()
except Exception:
    log.append("graff playwright: " + traceback.format_exc()[-500:])
# --- Roter Saal: Seite + PDF
try:
    seite = "https://www.braunschweig.de/kultur/kulturelle_einrichtungen/roter-saal/index.php"
    r = requests.get(seite, headers=H, timeout=30)
    (out / "roter_saal_seite.html").write_text(r.text, encoding="utf-8")
    pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', r.text, re.I)))
    log.append(f"roter saal seite: {r.status_code}, PDFs: {pdfs}")
    for i, h in enumerate(pdfs[:4]):
        u = requests.compat.urljoin(seite, h)
        pdf = requests.get(u, headers=H, timeout=60).content
        f = out / f"rs_{i}.pdf"; f.write_bytes(pdf)
        subprocess.run(["pdftotext", "-layout", str(f), str(out / f"rs_{i}.txt")], check=False)
        f.unlink()
        log.append(f"  {u}: {len(pdf)} Bytes")
except Exception:
    log.append("roter saal: " + traceback.format_exc()[-500:])
(out / "log.txt").write_text("\n".join(log), encoding="utf-8"); print("\n".join(log))
