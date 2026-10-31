"""Exercise optional people and pixel-checked cropping in tablet/phone browsers."""
import base64
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'transition_cues'))
from server import make_server
from playwright.sync_api import sync_playwright, expect
from browser_helpers import track_fullscreen, leave_fullscreen, type_pin, show_plan


def run():
    with tempfile.TemporaryDirectory() as data:
        server=make_server('127.0.0.1', 0, data)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
                browser=p.chromium.launch(**options)
                tablet=browser.new_context(viewport={'width':1280,'height':900})
                page=tablet.new_page();track_fullscreen(page);errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                url=f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                type_pin(page, '#pinInput', '1234');type_pin(page, '#pinConfirm', '1234');page.locator('#pinSubmit').click()
                expect(page.locator('#start')).to_be_disabled()
                expect(page.locator('footer')).to_have_count(0)
                expect(page.get_by_text('Familiar pictures. A little more certainty.',exact=True)).to_have_count(0)
                phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                mobile=phone.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)))
                mobile.goto(url+'/#manage');type_pin(mobile, '#pinInput', '1234');mobile.locator('#pinSubmit').click()
                expect(mobile.locator('#uploadForm')).to_be_visible()
                # Three colour bands make a crop's actual output measurable.
                png=mobile.evaluate('''()=>{const c=document.createElement('canvas');c.width=600;c.height=400;const x=c.getContext('2d');['#d00000','#00b000','#0000d0'].forEach((color,i)=>{x.fillStyle=color;x.fillRect(i*200,0,200,400)});return c.toDataURL('image/png').split(',')[1]}''')
                def dimensions(src):
                    return mobile.evaluate('''async src=>{const i=new Image();i.src=src;await i.decode();return [i.width,i.height]}''',src)
                def upload(kind,name,crop=False):
                    mobile.locator('#kind').select_option(kind);mobile.locator('#name').fill(name)
                    mobile.locator('#photo').set_input_files({'name':'test.png','mimeType':'image/png','buffer':base64.b64decode(png)})
                    expect(mobile.locator('#photoPreview')).to_be_visible()
                    preview=mobile.locator('#photoPreview').get_attribute('src')
                    assert dimensions(preview)==([400,400] if kind=='people' else [533,400])
                    if crop:
                        mobile.locator('#cropUpload').click()
                        expect(mobile.locator('#cropDialog')).to_be_visible()
                        expect(mobile.locator('#cropAspect')).to_have_value('1.3333333333')
                        assert mobile.locator('#cropAspect option').all_text_contents()==['Landscape · 4:3','Square','Original proportions']
                        mobile.locator('#cropAspect').select_option('1')
                        mobile.locator('#cropZoom').fill('2');mobile.locator('#cropX').fill('100')
                        mobile.locator('#cropSave').click()
                        expect(mobile.locator('#cropDialog')).not_to_be_visible()
                    mobile.locator('#uploadButton').click()
                    expect(mobile.locator('.library-item strong',has_text=name)).to_be_visible()
                    saved=mobile.evaluate('''async ({kind,name})=>{const s=await(await fetch('/api/state')).json();return s[kind].find(i=>i.name===name)}''',{'kind':kind,'name':name})
                    assert dimensions(saved['image'])==([200,200] if crop else [400,400] if kind=='people' else [533,400])
                    assert dimensions(saved['originalImage'])==[600,400]

                upload('places','Park',crop=True)
                uploaded=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.places[0]}")
                assert uploaded['image']!=uploaded['originalImage'], 'Upload crop must retain its original'
                upload('transport','Bus')
                # Original proportions can restore all of the retained source photo.
                mobile.get_by_role('button',name='Crop Bus',exact=True).click()
                expect(mobile.locator('#cropAspect')).to_have_value('1.3333333333')
                mobile.locator('#cropAspect').select_option('original')
                mobile.locator('#cropSave').click()
                expect(mobile.locator('#cropDialog')).not_to_be_visible()
                bus=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.transport[0]}")
                assert dimensions(bus['image'])==[600,400]

                for name in ['Drink','Coat','Toy','Headphones']:upload('items',name)
                upload('people','Person A');upload('people','Person B')
                # A cancelled edit makes no API write and doesn't change the stored URL.
                get_person=lambda:mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.people[0]}")
                person=get_person(); old_image=person['image']
                mobile.get_by_role('button',name='Crop Person A',exact=True).click()
                expect(mobile.locator('#cropAspect')).to_be_disabled()
                expect(mobile.locator('#cropCanvas')).to_have_class('round')
                mobile.locator('#cropZoom').fill('2')
                canvas=mobile.locator('#cropCanvas');canvas.scroll_into_view_if_needed();bounds=canvas.bounding_box()
                mobile.mouse.move(bounds['x']+bounds['width']/2,bounds['y']+bounds['height']/2)
                mobile.mouse.down();mobile.mouse.move(bounds['x']+bounds['width']/2+25,bounds['y']+bounds['height']/2,steps=5);mobile.mouse.up()
                assert float(mobile.locator('#cropX').input_value())<50, 'Dragging must reposition the crop'
                mobile.locator('#cropX').fill('100')
                mobile.locator('#cropCancel').click()
                assert get_person()['image']==old_image
                page.reload();page.get_by_role('button',name='Park',exact=True).click();page.get_by_role('button',name='Bus',exact=True).click()
                # Neither People nor bring-along items is required.
                expect(page.locator('#start')).to_be_enabled();show_plan(page)
                expect(page.locator('.journey-people')).to_have_count(0)
                for _ in range(5):page.locator('#lockedSurface h1').click()
                type_pin(page, '#pinInput', '1234');page.locator('#pinSubmit').click()
                expect(page.locator('#start')).to_be_visible()
                for name in ['Drink','Coat','Toy','Headphones','Person A','Person B']:page.get_by_role('button',name=name,exact=True).click()
                # People can be toggled independently of the four-item cap.
                page.get_by_role('button',name='Person B',exact=True).click()
                expect(page.locator('#peopleCount')).to_contain_text('1 selected')
                page.get_by_role('button',name='Person B',exact=True).click()
                page.screenshot(path='/tmp/transition-cues-picker.png',full_page=True)
                show_plan(page);expect(page.locator('.person-card')).to_have_count(2)
                assert page.locator('.person-card img').first.evaluate("img=>getComputedStyle(img).borderRadius==='50%'")
                # A real fullscreen browser window cannot be resized by Chromium's protocol.
                # Exit browser fullscreen only; the application's PIN lock must remain active.
                leave_fullscreen(page)
                expect(page.locator('#lockedSurface')).to_be_visible()
                for width,height in [(1280,900),(1024,768),(768,1024),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert page.locator('.journey-people').evaluate('(s)=>s.getBoundingClientRect().top>=document.querySelector(".cue-pair").getBoundingClientRect().bottom')
                    page.locator('.bring-items').scroll_into_view_if_needed()
                    expect(page.locator('.bring-card').last).to_be_in_viewport()
                    page.locator('#lockedSurface h1').scroll_into_view_if_needed()
                page.set_viewport_size({'width':1280,'height':900})
                page.screenshot(path='/tmp/transition-cues-locked.png',full_page=True)
                # Crop an existing person while that same person's old picture is locked.
                mobile.get_by_role('button',name='Crop Person A',exact=True).click()
                mobile.locator('#cropZoom').fill('2');mobile.locator('#cropX').fill('100')
                mobile.screenshot(path='/tmp/transition-cues-crop.png',full_page=True)
                assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
                mobile.locator('#cropSave').click();expect(mobile.locator('#cropDialog')).not_to_be_visible()
                cropped=get_person();assert cropped['id']==person['id'] and cropped['image']!=old_image
                # Rightmost square at 2x zoom contains only the blue band (lossy JPEG tolerances).
                sample=mobile.evaluate('''async src=>{const i=new Image();i.src=src;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const x=c.getContext('2d');x.drawImage(i,0,0);return {w:i.width,h:i.height,pixel:[...x.getImageData(i.width/2,i.height/2,1,1).data]}}''',cropped['image'])
                assert sample['w']==sample['h']==200,sample
                assert sample['pixel'][2]>150 and sample['pixel'][0]<30 and sample['pixel'][1]<30,sample
                page.reload();expect(page.locator('.person-card')).to_have_count(2)
                assert page.locator('.person-card img').first.get_attribute('src')==old_image
                assert page.locator('.person-card img').first.evaluate('i=>i.complete&&i.naturalWidth>0')
                # Recropping starts from the retained original, rather than the previous small crop.
                mobile.get_by_role('button',name='Crop Person A',exact=True).click()
                mobile.locator('#cropSave').click();expect(mobile.locator('#cropDialog')).not_to_be_visible()
                restored=get_person()
                size=mobile.evaluate('''async src=>{const i=new Image();i.src=src;await i.decode();return [i.width,i.height]}''',restored['image'])
                assert size==[400,400],size
                mobile.screenshot(path='/tmp/transition-cues-phone.png',full_page=True)
                # Removing a person doesn't change the locked snapshot or require a PIN bypass.
                mobile.get_by_role('button',name='Remove Person A',exact=True).click();mobile.get_by_role('button',name='Remove',exact=True).click()
                expect(mobile.locator('#deleteDialog')).not_to_be_visible()
                page.reload();expect(page.locator('.person-card')).to_have_count(2)
                for _ in range(5):page.locator('#lockedSurface h1').click()
                type_pin(page, '#pinInput', '0000');page.locator('#pinSubmit').click();expect(page.locator('#pinError')).to_contain_text('not recognised')
                type_pin(page, '#pinInput', '1234');page.locator('#pinSubmit').click();expect(page.locator('#start')).to_be_visible()
                # New version can still restore a journey from before the People category existed.
                page.evaluate("async()=>{const s=await(await fetch('/api/state')).json();localStorage.setItem('tc-locked-journey',JSON.stringify({places:s.places[0],transport:s.transport[0]}))}")
                page.reload();expect(page.locator('#lockedSurface')).to_be_visible();expect(page.locator('.journey-people')).to_have_count(0)
                assert not errors,errors
                browser.close()
                print('PASS: footer removal, optional people, circles, responsive layout, upload crop, cancel, pixel-checked saved crop, original recrop, locked snapshot retention, PIN and legacy journey restore.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':run()
