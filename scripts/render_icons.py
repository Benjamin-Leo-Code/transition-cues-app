"""Export the supplied mitten PNG for web-app installation and Home Assistant."""
import base64
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'transition_cues'
web=root/'transition-cues-web'
source=base64.b64encode((web/'icons/icon-1024.png').read_bytes()).decode()
with sync_playwright() as p:
    options={'headless':True}
    if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
    browser=p.chromium.launch(**options)
    page=browser.new_page()
    encoded=page.evaluate('''async source=>{
      const img=new Image();img.src='data:image/png;base64,'+source;await img.decode();
      const canvas=document.createElement('canvas');canvas.width=250;canvas.height=100;
      const context=canvas.getContext('2d');context.fillStyle='#ded8ca';context.fillRect(0,0,250,100);
      context.drawImage(img,0,0,100,100);
      context.fillStyle='#254d43';context.font='600 22px sans-serif';context.fillText('ReadySteady',104,45);
      context.fillStyle='#5c7662';context.font='14px sans-serif';context.fillText('Transition Cues',104,68);
      return canvas.toDataURL('image/png').split(',')[1];
    }''',source)
    (root/'logo.png').write_bytes(base64.b64decode(encoded))
    browser.close()
