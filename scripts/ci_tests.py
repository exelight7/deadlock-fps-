"""Keep unittest's exit code and attach failure details to the GitHub check."""
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,
                      env=dict(os.environ,PYTHONIOENCODING='utf-8'),stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
sys.stdout.reconfigure(encoding='utf-8')
print(result.stdout,end='')
if result.returncode and os.environ.get('GITHUB_ACTIONS')=='true':
    details=result.stdout[-16000:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    print('::error title=Unit and interface test failure::'+details)
sys.exit(result.returncode)
