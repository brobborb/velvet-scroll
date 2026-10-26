/* Velvet Scroll: the natural voice (Kokoro) runs here, away from the page, so reading and scrolling stay smooth.
   The page tells it where the Kokoro library and the speech engine's files are: packaged with the extension,
   or from jsDelivr for the website. The voice model itself downloads once from Hugging Face and is kept by the browser. */
let tts = null, loading = null;
const send = (m, t) => postMessage(m, t || []);

async function load(d){
  const mod = await import(d.lib);
  if(d.wasm) mod.env.wasmPaths = d.wasm;
  // add up the progress of every file the model needs
  const files = new Map();
  const progress = p => {
    if(!p || !p.file) return;
    if(p.status === 'progress' || p.status === 'done'){
      const f = files.get(p.file) || {loaded:0, total:0};
      if(p.total) f.total = p.total; f.loaded = p.status === 'done' ? (f.total || f.loaded) : (p.loaded || 0);
      files.set(p.file, f);
      let l = 0, t = 0; files.forEach(v => { l += v.loaded; t += v.total; });
      send({type:'progress', loaded:l, total:t});
    }
  };
  tts = await mod.KokoroTTS.from_pretrained(d.model, {dtype:'q8', device:'wasm', progress_callback:progress});
}

onmessage = async e => {
  const d = e.data;
  try{
    if(d.type === 'load'){
      loading ||= load(d);
      await loading;
      send({type:'ready'});
    } else if(d.type === 'gen'){
      if(!tts) throw new Error('not loaded');
      const t0 = performance.now();
      const out = await tts.generate(d.text, {voice:d.voice, speed:d.speed});
      const pcm = out.audio instanceof Float32Array ? out.audio : new Float32Array(out.audio);
      send({type:'audio', id:d.id, pcm, rate:out.sampling_rate, ms:performance.now() - t0}, [pcm.buffer]);
    }
  }catch(err){
    if(d.type === 'load') loading = null;
    send({type:'error', id:d.id, phase:d.type, msg:String(err && err.message || err)});
  }
};
