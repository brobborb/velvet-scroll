# Copies the website built on this branch to the beta test site (brobborb.github.io/velvet-scroll-beta)
# and labels it BETA so it can't be mistaken for the real site. Usage: python3 beta.py ../../velvet-scroll-beta "note"
import os, shutil, sys, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
B = os.path.abspath(sys.argv[1]) + '/'
note = sys.argv[2] if len(sys.argv) > 2 else ''
skip = {'.git', 'CNAME', 'source', 'README.md'}
for f in os.listdir(B):
    if f not in ('.git', 'README.md'): (shutil.rmtree if os.path.isdir(B+f) else os.remove)(B+f)
for f in os.listdir(ROOT):
    if f in skip or re.match(r'google[0-9a-f]+\.html$', f): continue
    (shutil.copytree if os.path.isdir(ROOT+f) else shutil.copy)(ROOT+f, B+f)
sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
tag = f'''<div id="betaTag" style="position:fixed;left:50%;transform:translateX(-50%);bottom:4px;z-index:2147483647;pointer-events:none;
font:600 11px/1.6 system-ui,sans-serif;letter-spacing:.06em;padding:0 9px;border-radius:9px;background:#c2410c;color:#fff;opacity:.85">BETA · {sha}</div>
<script>document.title = 'BETA – ' + document.title;</script>
'''
h = open(B+'index.html').read(); h = h.replace('</body>', tag + '</body>', 1); open(B+'index.html', 'w').write(h)
open(B+'.nojekyll', 'w').close()
print('beta ready from', sha, note)
