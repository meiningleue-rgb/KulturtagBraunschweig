import pathlib, subprocess, sys
out = pathlib.Path("diag/out"); out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*"): f.unlink()
r = subprocess.run([sys.executable, "diag/sport.py", "2026-10-31", "2027-06-30"], capture_output=True, text=True)
(out / "log.txt").write_text(r.stdout + "\n" + r.stderr[-3000:], encoding="utf-8"); print(r.stdout, r.stderr[-3000:])
import re, urllib.request
h = urllib.request.urlopen(urllib.request.Request("https://www.hessenschau.de/sport/ergebnisse-tabellen/basketball-1bl100~team_id-151.html", headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read().decode("utf-8", "replace")
i = h.find("Braunschweig</span>", h.find("teamResults"))
(out / "hs.txt").write_text(f"Länge {len(h)}, teamResults {h.count('teamResults')}, <tr {h.count('<tr')}\n" + h[max(0, i - 2500):i + 500], encoding="utf-8")
