import re, subprocess, pathlib, requests
out = pathlib.Path("diag/out"); out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*"): f.unlink()
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept-Language": "de-DE,de;q=0.9"}
log = []
for u in ["https://www.braunschweig.de/literaturzentrum/", "https://www.braunschweig.de/literaturzentrum/programm/", "https://www.braunschweig.de/literaturzentrum/programm/index.php", "https://www.braunschweig.de/raabe-haus", "https://www.braunschweig.de/literaturzentrum/index.php"]:
    try:
        r = requests.get(u, headers=H, timeout=30)
        pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', r.text, re.I)))
        links = sorted(set(re.findall(r'href="(/literaturzentrum/[^"#]+)"', r.text)))[:40]
        log.append(f"{u} -> {r.status_code} {r.url}\n  PDFs: {pdfs}\n  Links: {links}")
    except Exception as e: log.append(f"{u}: {e}")
u = "https://www.braunschweig.de/literaturzentrum/programm/Veranstaltungsblatt-2-26.pdf"
r = requests.get(u, headers=H, timeout=60); log.append(f"{u} -> {r.status_code} {len(r.content)}")
if r.ok:
    f = out / "vb.pdf"; f.write_bytes(r.content)
    subprocess.run(["pdftotext", "-layout", str(f), str(out / "vb_layout.txt")]); subprocess.run(["pdftotext", str(f), str(out / "vb_raw.txt")]); f.unlink()
(out / "log.txt").write_text("\n".join(log), encoding="utf-8"); print("\n".join(log))
