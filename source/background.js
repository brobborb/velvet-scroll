// Chrome runs this as a service worker and needs the shared code imported; Firefox loads store.js first itself.
if(typeof velvetSaveTab === 'undefined' && typeof importScripts === 'function') importScripts('store.js');
const api = globalThis.browser || chrome;
const MENU = 'velvet-save-page';
function addMenu(){
  if(!api.contextMenus) return;   // not available on Firefox for Android: use the toolbar menu there
  Promise.resolve(api.contextMenus.removeAll()).catch(() => {}).then(() => { try{ api.contextMenus.create({id:MENU, title:'Save page to Velvet Scroll', contexts:['page'], documentUrlPatterns:['http://*/*','https://*/*']}); }catch(e){} });
}
api.runtime.onInstalled.addListener(addMenu);
if(api.runtime.onStartup) api.runtime.onStartup.addListener(addMenu);
function badge(tabId, text, colour){
  try{ api.action.setBadgeBackgroundColor({color:colour, tabId}); api.action.setBadgeText({text, tabId}); setTimeout(() => api.action.setBadgeText({text:'', tabId}), 4000); }catch(e){}
}
if(api.contextMenus) api.contextMenus.onClicked.addListener(async (info, tab) => {
  if(info.menuItemId !== MENU || !tab) return;
  try{
    const r = await velvetSaveTab(tab.id);
    badge(tab.id, r.status === 'saved' || r.status === 'exists' ? '✓' : '!', r.status === 'saved' || r.status === 'exists' ? '#2c6a57' : '#a3392b');
  }catch(e){ badge(tab.id, '!', '#a3392b'); }
});
