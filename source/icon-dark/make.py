import asyncio
from playwright.async_api import async_playwright
D='/tmp/claude-0/-home-claude/a58680e1-260d-58bb-8370-b6f61008d1ec/scratchpad/icon-dark/'
# full design (48 px and up): dark tile, soft text lines, a teal guide window holding the line being read
FULL='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="{s}" height="{s}">
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c2629"/><stop offset="1" stop-color="#0c1214"/></linearGradient>
 <linearGradient id="tl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2fd3c0"/><stop offset="1" stop-color="#14a395"/></linearGradient>
 <filter id="gl" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
<rect x="4" y="4" width="120" height="120" rx="27" fill="url(#bg)"/>
<rect x="4.5" y="4.5" width="119" height="119" rx="26.5" fill="none" stroke="#ffffff" stroke-opacity=".07"/>
<g fill="#d7e2e4" stroke="none">
 <rect x="27" y="25" width="70" height="7" rx="3.5" opacity=".38"/>
 <rect x="27" y="39" width="58" height="7" rx="3.5" opacity=".6"/>
 <rect x="27" y="84" width="74" height="7" rx="3.5" opacity=".9"/>
 <rect x="27" y="98" width="48" height="7" rx="3.5" opacity=".9"/>
</g>
<rect x="17" y="54" width="94" height="22" rx="8" fill="#22c3b1" opacity=".45" filter="url(#gl)"/>
<rect x="17" y="54" width="94" height="22" rx="8" fill="url(#tl)"/>
<rect x="27" y="61.5" width="66" height="7" rx="3.5" fill="#062724"/>
</svg>'''
# small sizes: fewer, bolder shapes so it stays readable at 16 and 32 px
SMALL='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="{s}" height="{s}">
<rect x="0.5" y="0.5" width="31" height="31" rx="7" fill="#141c1f"/>
<rect x="7" y="6" width="16" height="3" rx="1.5" fill="#d7e2e4" opacity=".55"/>
<rect x="3.5" y="12" width="25" height="8" rx="2.5" fill="#20bcab"/>
<rect x="7" y="14.5" width="16" height="3" rx="1.5" fill="#062724"/>
<rect x="7" y="23" width="18" height="3" rx="1.5" fill="#d7e2e4" opacity=".9"/>
</svg>'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',args=['--no-sandbox'])
        pg=await b.new_page(device_scale_factor=1)
        for s in [16,32,48,96,128,512]:
            svg=(SMALL if s<=32 else FULL).replace('{s}',str(s))
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await pg.locator('svg').screenshot(path=D+f'icon-{s}.png', omit_background=True)
        open(D+'icon.svg','w').write(FULL.replace('{s}','128'))
        # preview: the icon on light and dark toolbars, at real sizes
        prev='<div style="display:flex;gap:28px;padding:24px;font:14px system-ui">'
        for bg,fg in [('#f1f3f4','#222'),('#202124','#eee')]:
            prev+=f'<div style="background:{bg};color:{fg};padding:18px 22px;border-radius:12px;display:flex;gap:18px;align-items:end">'+''.join(f'<div style="text-align:center"><img src="icon-{s}.png" width="{s}" height="{s}"><div style="margin-top:6px">{s}px</div></div>' for s in [16,32,48,128])+'</div>'
        prev+='</div>'
        open(D+'preview.html','w').write(prev)
        await pg.goto('file://'+D+'preview.html'); await pg.set_viewport_size({'width':900,'height':260})
        await pg.screenshot(path=D+'preview.png', full_page=True)
        await b.close()
asyncio.run(main())
