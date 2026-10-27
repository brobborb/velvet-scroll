/* Velvet Scroll: turn a web page into a saved article (uses Mozilla's Readability, the engine behind Firefox Reader View).
   Runs inside the page being saved (from the toolbar menu or right-click) or in the Velvet Scroll library (from a pasted link). */
// the same article shared through different links counts once: drop tracking tags and #anchors
function velvetCleanUrl(u){
  try{ const x = new URL(u); x.hash = '';
    [...x.searchParams.keys()].forEach(k => { if(/^(utm_\w+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref_src|cmpid|ncid|smid|_ga)$/i.test(k)) x.searchParams.delete(k); });
    return x.href; }catch(e){ return u; }
}
async function velvetArticle(doc, url, opts){
  opts = opts || {}; url = velvetCleanUrl(url);
  if(typeof Readability !== 'function') return {error:'nolib'};
  const parsed = new Readability(doc, {charThreshold:300, keepClasses:false}).parse();
  const text = parsed && (parsed.textContent || '').trim();
  if(!parsed || !parsed.content || !text || text.split(/\s+/).length < 60) return {error:'noarticle'};
  const esc = s => String(s || '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  let site = (parsed.siteName || '').trim();
  try{ if(!site) site = new URL(url).hostname.replace(/^www\./, ''); }catch(e){}
  const title = (parsed.title || doc.title || site || 'Untitled article').trim();
  const byline = (parsed.byline || '').replace(/^by\s+/i, '').trim();
  let published = '';
  if(parsed.publishedTime){ const d = new Date(parsed.publishedTime); if(!isNaN(d)) published = d.toLocaleDateString(undefined, {year:'numeric', month:'long', day:'numeric'}); }

  // the article body, with images made absolute and, where the site allows it, copied in for offline reading
  const body = new DOMParser().parseFromString('<div>' + parsed.content + '</div>', 'text/html').body.firstElementChild;
  const abs = u => { try{ return new URL(u, url).href; }catch(e){ return ''; } };
  const toData = async (src, maxBytes) => {
    try{
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);
      const r = await fetch(src, {credentials:'omit', signal:ctl.signal}); clearTimeout(t);
      if(!r.ok) return null; const b = await r.blob();
      if(!/^image\//.test(b.type) || b.size > maxBytes) return null;
      return await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = () => res(null); fr.readAsDataURL(b); });
    }catch(e){ return null; }
  };
  const imgs = [...body.querySelectorAll('img')];
  for(const im of imgs){
    const ss = im.getAttribute('srcset') || im.getAttribute('data-srcset');
    let src = im.getAttribute('data-src') || im.getAttribute('src') || '';
    if(ss){ const best = ss.split(',').map(x => x.trim().split(/\s+/)).map(([u, w]) => [u, parseFloat(w) || 1]).sort((a, b) => b[1] - a[1])[0]; if(best && best[0]) src = best[0]; }
    src = abs(src);
    ['srcset','data-srcset','data-src','sizes','loading','width','height','style'].forEach(a => im.removeAttribute(a));
    if(!/^https?:/i.test(src) && !/^data:image\//i.test(src)){ im.remove(); continue; }
    im.setAttribute('src', src);
  }
  let budget = 12e6, copied = 0;
  for(const im of imgs.slice(0, 40)){
    if(!im.isConnected) continue; const src = im.getAttribute('src');
    if(!/^https?:/i.test(src) || budget <= 0) continue;
    const d = await toData(src, Math.min(3e6, budget));
    if(d){ im.setAttribute('src', d); budget -= d.length * 0.75; copied++; }
  }
  body.querySelectorAll('a[href]').forEach(a => { const h = abs(a.getAttribute('href')); if(h) a.setAttribute('href', h); });
  body.querySelectorAll('script,style,iframe,form,input,button,noscript').forEach(n => n.remove());
  // the byline is shown once at the top, so drop the article's own "By …" line if it repeats it
  if(byline){ const norm = t => t.replace(/^\s*by\s+/i, '').replace(/\s+/g, ' ').trim().toLowerCase();
    [...body.querySelectorAll('p,div,span,address')].slice(0, 6).forEach(n => { const t = n.textContent || ''; if(t.length < 120 && norm(t) === norm(byline) && !n.querySelector('img')) n.remove(); }); }
  // and the title, if the article repeats it as its own first heading
  const h = body.querySelector('h1,h2'); if(h && h.textContent.trim().toLowerCase() === title.toLowerCase() && !h.previousElementSibling?.textContent?.trim()) h.remove();

  // a cover: the page's own preview image if there is one, otherwise the first picture in the article
  let cover = null;
  const og = doc.querySelector && (doc.querySelector('meta[property="og:image"],meta[name="og:image"],meta[name="twitter:image"]') || null);
  const coverSrc = og && og.getAttribute('content') ? abs(og.getAttribute('content')) : (body.querySelector('img') || {}).getAttribute?.('src');
  if(coverSrc) cover = /^data:image\//.test(coverSrc) ? coverSrc : await toData(coverSrc, 2e6);

  const meta = [byline, site, published].filter(Boolean).map(esc).join(' · ');
  const html = '<!doctype html><html lang="' + esc(parsed.lang || doc.documentElement && doc.documentElement.lang || '') + '"><head><meta charset="utf-8">' +
    '<title>' + esc(title) + '</title><meta name="author" content="' + esc(byline || site) + '">' +
    '<meta name="velvet-kind" content="article"><meta name="velvet-source" content="' + esc(url) + '"><meta name="velvet-site" content="' + esc(site) + '">' +
    '</head><body><h1>' + esc(title) + '</h1>' + (meta ? '<p><em>' + meta + '</em></p>' : '') + body.innerHTML +
    '<hr><p><a href="' + esc(url) + '">Read the original on ' + esc(site || 'the web') + '</a></p></body></html>';
  return {html, title, author: byline || site, site, excerpt: (parsed.excerpt || '').slice(0, 300), url, cover, words: text.split(/\s+/).length, copied, images: imgs.length};
}
