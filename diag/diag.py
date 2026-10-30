import re, subprocess, pathlib, requests, traceback
out = pathlib.Path("diag/out"); out.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept-Language": "de-DE,de;q=0.9"}
log = []
basis = "https://www.braunschweig.de/kultur/kulturelle_einrichtungen/roter-saal/"
for u in [basis, basis + "index.html", "https://www.braunschweig.de/kultur/kulturelle_einrichtungen/roter-saal.php", "https://www.braunschweig.de/roter-saal"]:
    try:
        r = requests.get(u, headers=H, timeout=30)
        pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', r.text, re.I)))
        log.append(f"{u} -> {r.status_code} {r.url} PDFs: {pdfs[:10]}")
        if r.ok and pdfs: (out / "roter_saal_seite.html").write_text(r.text, encoding="utf-8")
    except Exception as e: log.append(f"{u}: {e}")
for i, u in enumerate([basis + "Kulturkalender_3_2026_WEB.pdf", basis + "Kulturkalender_4_2026_WEB.pdf", basis + "Kulturkalender_1_2027_WEB.pdf"]):
    try:
        r = requests.get(u, headers=H, timeout=60)
        log.append(f"{u} -> {r.status_code} {len(r.content)} Bytes {r.headers.get('content-type')}")
        if r.ok and r.content[:4] == b"%PDF":
            f = out / f"kk_{i}.pdf"; f.write_bytes(r.content)
            subprocess.run(["pdftotext", "-layout", str(f), str(out / f"kk_{i}.txt")]); f.unlink()
    except Exception as e: log.append(f"{u}: {e}")
(out / "log.txt").write_text("\n".join(log), encoding="utf-8"); print("\n".join(log))
