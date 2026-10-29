/* Velvet Scroll: store a saved article in the library (the same browser storage the reader uses). */
const velvetApi = globalThis.browser || globalThis.chrome;
function velvetDB(){
  return new Promise((res, rej) => {
    const r = indexedDB.open('bookroll', 2);
    r.onupgradeneeded = () => { const d = r.result; for(const n of ['meta','files','progress']) if(!d.objectStoreNames.contains(n)) n === 'meta' ? d.createObjectStore(n, {keyPath:'id'}) : d.createObjectStore(n); };
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  });
}
const velvetReq = r => new Promise((res, rej) => { r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
// the same fingerprint the library uses to recognise a book on another device
async function velvetFingerprint(buf){
  const u = new Uint8Array(buf), head = u.subarray(0, 262144), tail = u.subarray(Math.max(head.length, u.length - 65536));
  const d = new Uint8Array(head.length + tail.length + 8); d.set(head); d.set(tail, head.length);
  new DataView(d.buffer).setFloat64(head.length + tail.length, u.length);
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', d))].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 24);
}
function velvetDataUrlToBuffer(s){
  const m = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(s || ''); if(!m || !m[2]) return null;
  const bin = atob(m[3]), u = new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i] = bin.charCodeAt(i);
  return {buf:u.buffer, type:m[1] || 'image/jpeg'};
}
async function velvetStoreArticle(a){
  const db = await velvetDB();
  try{
    const all = await velvetReq(db.transaction('meta').objectStore('meta').getAll());
    const clean = typeof velvetCleanUrl === 'function' ? velvetCleanUrl : (x => x);
    const same = all.find(m => m.source && clean(m.source) === clean(a.url));
    if(same) return {status:'exists', title:same.title, id:same.id};
    const bytes = new TextEncoder().encode(a.html);
    const id = (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
    const meta = {id, title:a.title, author:a.author || '', year:null, isbn:'', added:Date.now(), upd:Date.now(), shelf:'', file:'article.html',
      size:bytes.byteLength, fp: await velvetFingerprint(bytes.buffer), kind:'article', source:a.url, site:a.site || '', excerpt:a.excerpt || '', looked:true};
    const c = a.cover && velvetDataUrlToBuffer(a.cover);
    if(c){ meta.coverBuf = c.buf; meta.coverType = c.type; meta.coverSrc = 'own'; }
    const tx = db.transaction(['meta','files'], 'readwrite');
    tx.objectStore('files').put(bytes.buffer, id); tx.objectStore('meta').put(meta);
    await new Promise((res, rej) => { tx.oncomplete = res; tx.onerror = () => rej(tx.error); tx.onabort = () => rej(tx.error); });
    try{ const bc = new BroadcastChannel('velvet-scroll'); bc.postMessage({type:'library-changed'}); bc.close(); }catch(e){}
    return {status:'saved', title:a.title, id};
  } finally { db.close(); }
}
// read the article out of a browser tab (the toolbar menu or the right-click menu gives permission for that tab)
async function velvetSaveTab(tabId){
  await velvetApi.scripting.executeScript({target:{tabId}, files:['lib/Readability.js', 'clip-core.js']});
  const [r] = await velvetApi.scripting.executeScript({target:{tabId}, func: () => velvetArticle(document.cloneNode(true), location.href, {live: document})});
  const a = r && r.result;
  if(!a || a.error) return {status: a && a.error === 'noarticle' ? 'noarticle' : 'failed'};
  return velvetStoreArticle(a);
}
