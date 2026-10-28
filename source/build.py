# Builds the Firefox extension, the Chrome extension and the website from bookroll.html
import re, json, shutil, os, sys, subprocess
S=os.path.dirname(os.path.abspath(__file__))+'/'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'   # the website lives at the top of the repo
VERSION=sys.argv[1]
src=open(S+'bookroll.html').read()
style=re.search(r'<style>(.*?)</style>',src,re.S).group(1).strip()+'\n'
script=re.findall(r'<script>(.*?)</script>',src,re.S)[-1].strip()+'\n'
body=src[src.index('</style>')+8:src.rindex('<script>')].strip()
# every id on the page must be unique, or one button can quietly take over another's job
from collections import Counter
dups=[k for k,v in Counter(re.findall(r'\bid="([^"]+)"', body)).items() if v>1]
if dups: sys.exit('Duplicate ids in bookroll.html: ' + ', '.join(dups))
DESC='An ebook reader that scrolls for you, with a reading guide, read aloud and your books kept private on your device.'

def ext_files(E):
    open(E+'app.js','w').write(script); open(E+'reader.css','w').write(style)
    h=open(E+'reader.html').read()
    h=h[:h.index('<body>')+6]+'\n'+body+'\n'+h[h.index('<script src="lib/jszip.min.js">'):]
    if 'clip-core.js' not in h:
        h=h.replace('<script src="app.js"></script>','<script src="lib/Readability.js"></script>\n<script src="clip-core.js"></script>\n<script src="store.js"></script>\n<script src="app.js"></script>')
    open(E+'reader.html','w').write(h)
    # article saving: the toolbar menu, the right-click option and the shared code
    shutil.copy(S+'clip-core.js', E+'clip-core.js'); shutil.copy(S+'store-core.js', E+'store.js')
    for f in ('popup.html','popup.js','background.js'): shutil.copy(S+f, E+f)
    shutil.copy(S+'npmdl/node_modules/@mozilla/readability/Readability.js', E+'lib/Readability.js')
    shutil.copy(ROOT+'lib/qrcode.js', E+'lib/qrcode.js')   # QR codes for sync codes (MIT, Kazuhiko Arase)
    # natural voices (Piper): the worker, ONNX Runtime Web 1.20.1 and the eSpeak NG / piper-phonemize WebAssembly build (unmodified npm releases)
    shutil.copy(S+'piper-worker.js', E+'piper-worker.js')
    shutil.rmtree(E+'lib/piper', ignore_errors=True); shutil.copytree(S+'vendor/piper', E+'lib/piper')
    # recognising text in scanned PDFs: Tesseract.js 7.0.0 and tesseract.js-core 7.0.0 (unmodified npm releases; LSTM builds with and without SIMD)
    shutil.rmtree(E+'lib/tesseract', ignore_errors=True); shutil.copytree(S+'vendor/tesseract', E+'lib/tesseract')
    for f in ('licences.html','LICENSE-GPL-3.0.txt','LICENSE-Apache-2.0.txt'): shutil.copy(ROOT+f, E+f)
    shutil.rmtree(E+'lib/kokoro', ignore_errors=True)
    if os.path.exists(E+'kokoro-worker.js'): os.remove(E+'kokoro-worker.js')

# Firefox
E=S+'ext/'; ext_files(E)
m=json.load(open(E+'manifest.json')); m['version']=VERSION;
for perm in ('activeTab','scripting','contextMenus'):
    if perm not in m['permissions']: m['permissions'].append(perm)
m['action']['default_popup']='popup.html'; m['action']['default_title']='Velvet Scroll'
m['name']='Velvet Scroll – EPUB & Ebook Reader'   # the store name: says what it is, so searches for EPUB or ebook readers find it
m['background']={'scripts':['store.js','background.js']}; hosts=m['optional_host_permissions']; [hosts.append(x) for x in ('https://*/*','http://*/*') if x not in hosts]; m['description']=DESC; m['homepage_url']='https://velvetscroll.net/'
# Firefox for Android only supports the data-collection setting from version 142
m['browser_specific_settings']['gecko_android']={'strict_min_version':'142.0'}
# natural voices run WebAssembly packaged with the extension
m['content_security_policy']={'extension_pages':"script-src 'self' 'wasm-unsafe-eval'; object-src 'self'"}
open(E+'manifest.json','w').write(json.dumps(m,indent=2)+'\n')

# Chrome: same files, Chrome-style background worker and no Firefox-only settings
C=S+'ext-chrome/'
shutil.rmtree(C,ignore_errors=True); shutil.copytree(E,C)
mc={k:v for k,v in m.items() if k not in ('browser_specific_settings','background')}
mc['background']={'service_worker':'background.js'}
mc['minimum_chrome_version']='116'
open(C+'manifest.json','w').write(json.dumps(mc,indent=2)+'\n')
# background.js works for both browsers (it imports store.js itself when Chrome runs it as a service worker)

for d,z in [(E,'velvet-scroll-firefox.zip'),(C,'velvet-scroll-chrome.zip')]:
    if os.path.exists(S+z): os.remove(S+z)
    subprocess.run(['zip','-qr','-X',S+z,'.'],cwd=d,check=True)

# Website
W=ROOT
h=open(W+'index.html').read()
h=re.sub(r'(<style>)(?!\*,)(.*?)(</style>)', lambda mm: mm.group(1)+style+mm.group(3), h, count=1, flags=re.S) if False else h
parts=re.split(r'(<style>.*?</style>)', h, flags=re.S)
# parts: [pre, reset-style, mid, main-style, post]
parts[3]='<style>\n'+style+'</style>'
h=''.join(parts)
h=h[:h.index('<body>')+6]+'\n'+body+'\n'+h[h.index('<script src="donate.js">'):]
h=h[:h.index('<script>',h.index('donate.js'))]+'<script>\n'+script+'</script>\n</body>\n</html>\n'
open(W+'index.html','w').write(h)
if os.path.exists(W+'kokoro-worker.js'): os.remove(W+'kokoro-worker.js')
shutil.copy(S+'piper-worker.js', W+'piper-worker.js')   # the website's natural-voice worker (loads the engine from jsDelivr)
print('built', VERSION)
