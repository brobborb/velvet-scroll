VELVET SCROLL — SOURCE
======================

bookroll.html is the master copy of the whole app (layout, styles and code in one file).
Edit that, then run the build to make the extensions and the website:

    python3 build.py 1.20.2        (use the next version number)

It writes:
    velvet-scroll-firefox.zip   upload to addons.mozilla.org
    velvet-scroll-chrome.zip    upload to the Chrome Web Store
    (repo root)                 the website: index.html and piper-worker.js are rebuilt in place
    ext/ and ext-chrome/        unpacked extensions, for testing in the browser

Needs Python 3 and the "zip" command (Linux/Mac, or WSL on Windows).

Other files
    piper-worker.js     natural voices (Piper) worker, used by both the extensions and the website
    clip-core.js, store-core.js, popup.*, background.js   article saving and the toolbar menu (extensions)
    vendor/piper/       ONNX Runtime Web 1.20.1 and the eSpeak NG / piper-phonemize WebAssembly build (unmodified releases; see site/licences.html)
    ext/                Firefox extension template: manifest, icons, fonts and libraries (PDF.js, JSZip, Readability, QR codes)
    ../donate.js        your PayPal link — the build never touches it
    icon-dark/          the dark teal icon set

Version in this copy: 1.20.1
