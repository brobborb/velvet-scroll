const $ = s => document.querySelector(s);
const readerUrl = velvetApi.runtime.getURL('reader.html');
let tab = null;
async function openLibrary(){
  const tabs = await velvetApi.tabs.query({});
  const open = tabs.find(t => t.url && t.url.startsWith(readerUrl));
  if(open){ await velvetApi.tabs.update(open.id, {active:true}); try{ if(open.windowId != null && velvetApi.windows) await velvetApi.windows.update(open.windowId, {focused:true}); }catch(e){} }
  else await velvetApi.tabs.create({url:readerUrl});
  window.close();
}
function status(text, kind){ const s = $('#status'); s.textContent = text; s.className = kind || ''; }
(async () => {
  [tab] = await velvetApi.tabs.query({active:true, currentWindow:true});
  const ok = tab && /^https?:/i.test(tab.url || '') && !/^https:\/\/(addons\.mozilla\.org|chromewebstore\.google\.com|chrome\.google\.com\/webstore)/.test(tab.url);
  if(!ok){ $('#save').disabled = true; status(tab && tab.url && tab.url.startsWith(readerUrl) ? 'You’re in your library.' : 'This page can’t be saved. Open an article on a website first.'); }
  else { try{ $('#site').textContent = new URL(tab.url).hostname.replace(/^www\./, ''); }catch(e){} }
})();
$('#open').onclick = openLibrary;
$('#save').onclick = async () => {
  $('#save').disabled = true; status('Saving…');
  try{
    const r = await velvetSaveTab(tab.id);
    if(r.status === 'saved'){ status('Saved “' + r.title + '”.', 'ok'); $('#open').textContent = 'Read it now'; }
    else if(r.status === 'exists'){ status('Already in your library.', 'ok'); $('#open').textContent = 'Open library'; }
    else if(r.status === 'noarticle'){ status('Couldn’t find an article on this page. Saving works best on stories, posts and blog articles.', 'bad'); $('#save').disabled = false; }
    else { status('Couldn’t save this page. Try reloading it, then save again.', 'bad'); $('#save').disabled = false; }
  }catch(e){ status('Couldn’t save this page. Some pages, such as browser and store pages, can’t be read by extensions.', 'bad'); $('#save').disabled = false; }
};
