/* Velvet Scroll Plus: licence keys after a Paddle purchase.
   A Cloudflare Worker. After Paddle's checkout completes, the website sends the transaction id here. The Worker asks
   Paddle whether that transaction is really paid and is for Velvet Scroll Plus, then signs a licence key in the
   buyer's name, the same kind of key as source/tools/make_plus_key.py makes, and returns it.

   Settings (Cloudflare → the Worker → Settings → Variables and secrets):
     PRIVATE_KEY     secret  the whole velvet-scroll-plus-PRIVATE.pem text (BEGIN/END lines included)
     PADDLE_API_KEY  secret  a Paddle API key with read access to transactions and customers
     PADDLE_ENV      text    "sandbox" while testing, "live" after launch
     PRICE_IDS       text    the Paddle price id(s) for Plus, comma-separated
     ORIGINS         text    the websites allowed to ask, comma-separated
                             e.g. https://velvetscroll.net,https://brobborb.github.io
   Nothing is stored: the Worker keeps no records of its own; Paddle is the record of every purchase. */

const b64u = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

async function signingKey(pem){
  const der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0));
  return crypto.subtle.importKey('pkcs8', der, {name:'ECDSA', namedCurve:'P-256'}, false, ['sign']);
}

async function makeKey(env, name, txn){
  const payload = {v:1, n:String(name).slice(0, 80), d:new Date().toISOString().slice(0, 10), id:txn.slice(-12), t:txn};
  const body = b64u(new TextEncoder().encode(JSON.stringify(payload)));
  // Web Crypto returns the raw r||s signature, the form Velvet Scroll checks
  const sig = await crypto.subtle.sign({name:'ECDSA', hash:'SHA-256'}, await signingKey(env.PRIVATE_KEY), new TextEncoder().encode(body));
  return `VSP1-${body}.${b64u(sig)}`;
}

async function paddle(env, path){
  const base = env.PADDLE_ENV === 'live' ? 'https://api.paddle.com' : 'https://sandbox-api.paddle.com';
  const r = await fetch(base + path, {headers:{Authorization:`Bearer ${env.PADDLE_API_KEY}`, 'Paddle-Version':'1'}});
  if(!r.ok) throw new Error(`Paddle ${r.status}`);
  return (await r.json()).data;
}

function cors(req, env){
  const o = req.headers.get('Origin') || '', ok = (env.ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
  return ok.includes(o) ? {'Access-Control-Allow-Origin':o, 'Access-Control-Allow-Methods':'POST, OPTIONS', 'Access-Control-Allow-Headers':'Content-Type', Vary:'Origin'} : null;
}
const reply = (data, status, h) => new Response(JSON.stringify(data), {status, headers:{'Content-Type':'application/json', 'Cache-Control':'no-store', ...h}});

export default {
  async fetch(req, env){
    const h = cors(req, env);
    if(req.method === 'OPTIONS') return new Response(null, {status:h ? 204 : 403, headers:h || {}});
    const url = new URL(req.url);
    if(req.method === 'GET' && url.pathname === '/') return new Response('Velvet Scroll licence keys', {headers:{'Content-Type':'text/plain'}});
    if(req.method !== 'POST' || url.pathname !== '/key') return reply({error:'not found'}, 404, h || {});
    if(!h) return reply({error:'origin not allowed'}, 403, {});
    let txn;
    try{ txn = String((await req.json()).transaction || ''); }catch(e){}
    if(!/^txn_[a-z0-9]{10,40}$/.test(txn || '')) return reply({error:'missing transaction'}, 400, h);
    try{
      const t = await paddle(env, `/transactions/${txn}`);
      const prices = (env.PRICE_IDS || '').split(',').map(s => s.trim());
      const forPlus = (t.items || []).some(i => prices.includes(i.price?.id || i.price_id));
      if(!['completed', 'paid'].includes(t.status) || !forPlus) return reply({error:'not a completed Plus purchase'}, 402, h);
      let name = '';
      if(t.customer_id){ const c = await paddle(env, `/customers/${t.customer_id}`); name = c.name || c.email || ''; }
      const key = await makeKey(env, name || 'Velvet Scroll Plus', txn);
      return reply({key, name}, 200, h);
    }catch(e){
      return reply({error:'could not check the purchase, please try again'}, 502, h);
    }
  }
};
