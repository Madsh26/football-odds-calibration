"""Run checks and retain the verification log; exit nonzero on failure."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
(root/'reports').mkdir(exist_ok=True)
(root/'reports/validation.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
print(result.stdout+result.stderr)
raise SystemExit(result.returncode)
