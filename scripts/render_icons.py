"""Export the existing SVG logo for web-app installation and Home Assistant."""
import base64
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'transition_cues'
web=root/'transition-cues-web'
svg=(web/'icon.svg').read_text()
with sync_playwright() as p:
    options={'headless':True}
    if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
    browser=p.chromium.launch(**options)
    page=browser.new_page()
    def render(size,background=True,logo=False):
        encoded=page.evaluate('''async ({svg,size,background,logo})=>{
          const img=new Image();img.src='data:image/svg+xml;base64,'+btoa(svg);await img.decode();
          const c=document.createElement('canvas');c.width=logo?250:size;c.height=logo?100:size;
          const x=c.getContext('2d');
          if(background){x.fillStyle='#254d43';x.fillRect(0,0,c.width,c.height)}
          if(logo){x.drawImage(img,0,0,100,100);x.fillStyle='#ffffff';x.font='600 22px sans-serif';x.fillText('ReadySteady',104,45);x.fillStyle='#dbe6d3';x.font='14px sans-serif';x.fillText('Transition Cues',104,68)}
          else x.drawImage(img,0,0,size,size);
          return c.toDataURL('image/png').split(',')[1];
        }''',{'svg':svg,'size':size,'background':background,'logo':logo})
        return base64.b64decode(encoded)
    (web/'icons').mkdir(exist_ok=True)
    for size in [192,512,1024]:
        (web/'icons'/f'icon-{size}.png').write_bytes(render(size))
    (web/'icons'/'maskable-512.png').write_bytes(render(512))
    (web/'apple-touch-icon.png').write_bytes(render(180))
    (web/'favicon-32.png').write_bytes(render(32))
    (root/'icon.png').write_bytes(render(128,background=False))
    (root/'logo.png').write_bytes(render(250,logo=True))
    browser.close()
