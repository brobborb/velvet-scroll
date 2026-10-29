/* Velvet Scroll: turn a web page into a saved article (uses Mozilla's Readability, the engine behind Firefox Reader View).
   Runs inside the page being saved (from the toolbar menu or right-click) or in the Velvet Scroll library (from a pasted link). */
// the same article shared through different links counts once: drop tracking tags and #anchors
function velvetCleanUrl(u){
  try{ const x = new URL(u); x.hash = '';
    [...x.searchParams.keys()].forEach(k => { if(/^(utm_\w+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref_src|cmpid|ncid|smid|_ga)$/i.test(k)) x.searchParams.delete(k); });
    return x.href; }catch(e){ return u; }
}
// the best address for a picture: the largest in its srcset, lazy-loading attributes, or a <picture> source
function velvetImgSrc(im, base){
  const abs = u => { try{ return new URL(u, base).href; }catch(e){ return ''; } };
  const real = u => u && !/^data:/i.test(u) || (u && /^data:image\//i.test(u) && u.length > 400);   // tiny data: images are lazy-loading placeholders
  let ss = im.getAttribute('srcset') || im.getAttribute('data-srcset') || im.getAttribute('data-lazy-srcset') || '';
  const pic = im.parentElement && im.parentElement.tagName === 'PICTURE' ? im.parentElement : null;
  if(!ss && pic){ const so = [...pic.querySelectorAll('source[srcset],source[data-srcset]')].find(x => !/avif|jxl/i.test(x.getAttribute('type') || '')); if(so) ss = so.getAttribute('srcset') || so.getAttribute('data-srcset'); }
  let src = [im.getAttribute('data-src'), im.getAttribute('data-lazy-src'), im.getAttribute('data-original'), im.getAttribute('src')].find(real) || '';
  if(ss){ const best = ss.split(/,\s+(?=\S)/).map(x => x.trim().split(/\s+/)).filter(([u]) => real(u)).map(([u, w]) => [u, parseFloat(w) || 1]).sort((a, b) => b[1] - a[1])[0]; if(best && best[0]) src = best[0]; }
  return src ? (/^data:/i.test(src) ? src : abs(src)) : '';
}
// the article's lead picture: Readability keeps only the text's own block, so a picture shown above the text
// (the usual "featured image" under the headline) is lost. Find it before the first long paragraph, skipping
// navigation, logos, avatars, adverts and "related" thumbnails, and small images.
function velvetLead(doc, url, live){
  const BAD = /(^|[\s_-])(nav|navbar|menu|footer|sidebar|related|recommend(ed|ations)?|promo|newsletter|subscribe|share|sharing|social|author|byline|avatar|logo|advert|ad|ads|sponsor(ed)?|comments?|widget|breadcrumbs?|popup|modal)([\s_-]|$)/i;
  const imgs = [...doc.querySelectorAll('img')], limgs = live ? [...live.querySelectorAll('img')] : [];
  const firstP = [...doc.querySelectorAll('p')].find(p => (p.textContent || '').trim().length > 200);
  for(let i = 0; i < imgs.length && i < 60; i++){
    const im = imgs[i];
    if(firstP && (firstP.compareDocumentPosition(im) & 4)) break;   // pictures after the text starts are the article's own
    let bad = false;
    for(let a = im; a && a !== doc.body; a = a.parentElement){
      const cls = typeof a.className === 'string' ? a.className : (a.getAttribute && a.getAttribute('class')) || '';
      if(/^(NAV|FOOTER|ASIDE|FORM|BUTTON|A)$/.test(a.tagName) && a !== im && !(a.tagName === 'A' && a.querySelector('img') === im && /\.(jpe?g|png|webp|gif)(\?|$)/i.test(a.getAttribute('href') || '')) ? true : BAD.test(cls) || BAD.test(a.id || '')){ bad = true; break; }
    }
    if(bad) continue;
    const src = velvetImgSrc(im, url); if(!src || /\.svg(\?|#|$)/i.test(src) || /(logo|icon|sprite|avatar|gravatar|pixel|spacer|blank)\b/i.test(src)) continue;
    const L = limgs[i];
    let w = 0; if(L){ const r = L.getBoundingClientRect(); w = Math.max(r.width, L.naturalWidth || 0); }
    const aw = Math.max(+im.getAttribute('width') || 0, +im.getAttribute('data-width') || 0);
    if((L && w > 0 && w < 300) || (aw && aw < 280)) continue;
    const fig = im.closest('figure'), cap = fig && fig.querySelector('figcaption');
    return {src, alt: im.getAttribute('alt') || '', caption: cap ? cap.textContent.replace(/\s+/g, ' ').trim() : ''};
  }
  // a title picture drawn as a CSS background (common for full-width banners)
  if(live){
    const lfirst = [...live.querySelectorAll('p')].find(p => (p.textContent || '').trim().length > 200);
    for(const el of [...live.body.querySelectorAll('*')].slice(0, 3000)){
      if(lfirst && (lfirst.compareDocumentPosition(el) & 4)) break;
      let bg = ''; try{ bg = getComputedStyle(el).backgroundImage || ''; }catch(e){}
      const m = /url\(["']?([^"')]+)["']?\)/.exec(bg); if(!m || /gradient/.test(bg) && !m) continue;
      const r = el.getBoundingClientRect(); if(r.width < 300 || r.height < 150) continue;
      let bad = false; for(let a = el; a && a !== live.body; a = a.parentElement){ const cls = typeof a.className === 'string' ? a.className : ''; if(/^(NAV|FOOTER|ASIDE)$/.test(a.tagName) || BAD.test(cls) || BAD.test(a.id || '')){ bad = true; break; } }
      if(bad) continue;
      let src = ''; try{ src = new URL(m[1], url).href; }catch(e){}
      if(src && !/\.svg(\?|#|$)/i.test(src) && !/(logo|icon|sprite|pattern|texture)\b/i.test(src)) return {src, alt: '', caption: ''};
    }
  }
  return null;
}
const velvetImgKey = u => { try{ const x = new URL(u); return (x.pathname.split('/').pop() || '').replace(/-\d+x\d+(?=\.\w+$)/, '').replace(/@\dx(?=\.\w+$)/, '').toLowerCase(); }catch(e){ return ''; } };
async function velvetArticle(doc, url, opts){
  opts = opts || {}; url = velvetCleanUrl(url);
  if(typeof Readability !== 'function') return {error:'nolib'};
  let lead = null; try{ lead = velvetLead(doc, url, opts.live); }catch(e){}   // before Readability, which reshapes the page
  const ogEl = doc.querySelector && doc.querySelector('meta[property="og:image"],meta[name="og:image"],meta[name="twitter:image"]');
  const ogSrc = ogEl && ogEl.getAttribute('content') || '';
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
  let imgs = [...body.querySelectorAll('img')];
  for(const im of imgs){
    const src = velvetImgSrc(im, url);
    ['srcset','data-srcset','data-lazy-srcset','data-src','data-lazy-src','data-original','sizes','loading','width','height','style'].forEach(a => im.removeAttribute(a));
    const pic = im.parentElement && im.parentElement.tagName === 'PICTURE' ? im.parentElement : null;
    if(pic) pic.querySelectorAll('source').forEach(x => x.remove());
    if(!/^https?:/i.test(src) && !/^data:image\//i.test(src)){ im.remove(); continue; }
    im.setAttribute('src', src);
  }
  // put back the lead picture if the text lost it; failing that, the page's own preview picture when the article has none
  imgs = imgs.filter(im => im.isConnected);
  const have = new Set(imgs.map(im => velvetImgKey(im.getAttribute('src'))));
  // no picture above the text: the page's own preview picture is almost always the article's title picture
  const ogLead = ogSrc && !/(logo|default|placeholder|icon|fallback)/i.test(ogSrc) ? {src: abs(ogSrc), alt: '', caption: ''} : null;
  // does the article itself open with a picture (fewer than 200 characters of text before its first one)?
  let opensWithPicture = false;
  { const first = body.querySelector('img'); if(first){ let n = 0; const w = body.ownerDocument.createTreeWalker(body, 4); let t;
      while((t = w.nextNode()) && (first.compareDocumentPosition(t) & 2)){ n += t.data.trim().length; if(n >= 200) break; } opensWithPicture = n < 200; } }
  const pick = lead || (opensWithPicture ? null : ogLead);
  let add = pick && !have.has(velvetImgKey(pick.src)) ? pick : null;
  if(add){
    const fig = body.ownerDocument.createElement('figure'), im = body.ownerDocument.createElement('img');
    im.setAttribute('src', add.src); im.setAttribute('alt', add.alt || ''); fig.append(im);
    if(add.caption){ const fc = body.ownerDocument.createElement('figcaption'); fc.textContent = add.caption; fig.append(fc); }
    body.prepend(fig); imgs.unshift(im);
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
