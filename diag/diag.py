import pathlib, subprocess, sys
out = pathlib.Path("diag/out"); out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*"): f.unlink()
r = subprocess.run([sys.executable, "diag/sport.py", "2026-10-31", "2027-06-30"], capture_output=True, text=True)
(out / "log.txt").write_text(r.stdout + "\n" + r.stderr[-3000:], encoding="utf-8"); print(r.stdout, r.stderr[-3000:])
