/* Velvet Scroll: downloading free books for the website.
   A Cloudflare Worker. Browsers only let a website download a file from another site if that site allows it, and
   Project Gutenberg, arXiv and similar free libraries don't. So for these few public libraries only, the Velvet Scroll
   website asks this Worker, which downloads the book and passes it straight back.
   (The browser extensions don't need this: they can download from any site you allow.)

   It only fetches from the libraries listed in HOSTS, only for velvetscroll.net and the beta site, only GET, and
   only files up to 300 MB. Nothing is stored or logged by the Worker: the book passes straight through.

   Setting it up (no settings needed): Cloudflare → Workers & Pages → Create → Create Worker → name it
   velvet-scroll-fetch → Deploy → Edit code → replace everything with this file → Deploy.
   Then its address (https://velvet-scroll-fetch.NAME.workers.dev) goes in FETCHER in source/bookroll.html. */

const ORIGINS = ['https://velvetscroll.net', 'https://www.velvetscroll.net', 'https://brobborb.github.io'];
const HOSTS = ['gutenberg.org', 'gutenberg.net.au', 'e-book.au', 'arxiv.org', 'fadedpage.com', 'wikisource.org',
  'ws-export.wmcloud.org', 'archive.org'];
const MAX = 300 * 1024 * 1024;
const allowedHost = h => HOSTS.some(d => h === d || h.endsWith('.' + d));

function headers(origin){
  return {'Access-Control-Allow-Origin':origin, 'Access-Control-Allow-Methods':'GET, OPTIONS', Vary:'Origin',
    'Access-Control-Expose-Headers':'Content-Length, Content-Type, Content-Disposition, X-Final-URL'};
}

export default {
  async fetch(req){
    const origin = req.headers.get('Origin') || '';
    if(!ORIGINS.includes(origin)) return new Response('Velvet Scroll book downloads', {status: origin ? 403 : 200});
    const h = headers(origin);
    if(req.method === 'OPTIONS') return new Response(null, {status:204, headers:h});
    if(req.method !== 'GET') return new Response('GET only', {status:405, headers:h});
    let target;
    try{ target = new URL(new URL(req.url).searchParams.get('url') || ''); }catch(e){ return new Response('Bad address', {status:400, headers:h}); }
    // follow redirects ourselves, so every step stays within the listed libraries
    for(let hop = 0; hop < 6; hop++){
      if(target.protocol !== 'https:' && target.protocol !== 'http:' || !allowedHost(target.hostname)) return new Response('Not a supported library', {status:403, headers:h});
      const r = await fetch(target.href, {redirect:'manual', headers:{'User-Agent':'VelvetScroll/1.0 (+https://velvetscroll.net; one book for one reader)', Accept:'*/*'}});
      if(r.status >= 300 && r.status < 400 && r.headers.get('Location')){ target = new URL(r.headers.get('Location'), target); continue; }
      const len = +r.headers.get('Content-Length') || 0;
      if(len > MAX) return new Response('Too large', {status:413, headers:h});
      const out = new Headers(h);
      for(const k of ['Content-Type', 'Content-Length', 'Content-Disposition']) if(r.headers.get(k)) out.set(k, r.headers.get(k));
      out.set('X-Final-URL', target.href); out.set('Cache-Control', 'no-store');
      return new Response(r.body, {status:r.status, headers:out});
    }
    return new Response('Too many redirects', {status:508, headers:h});
  }
};
