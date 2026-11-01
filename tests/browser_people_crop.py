"""Exercise optional people and pixel-checked cropping in tablet/phone browsers."""
import argparse
import base64
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'transition_cues'))
from server import make_server
from playwright.sync_api import sync_playwright, expect
from browser_helpers import track_fullscreen, leave_fullscreen, show_plan, open_step


def run(engine):
    with tempfile.TemporaryDirectory() as data:
        server=make_server('127.0.0.1', 0, data)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if engine=='chromium' and os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
                browser=getattr(p,engine).launch(**options)
                tablet=browser.new_context(viewport={'width':1280,'height':900})
                page=tablet.new_page();track_fullscreen(page);errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                url=f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                expect(page.locator('#start')).to_be_disabled()
                expect(page.locator('footer')).to_have_count(0)
                expect(page.get_by_text('Familiar pictures. A little more certainty.',exact=True)).to_have_count(0)
                phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                mobile=phone.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)))
                mobile.goto(url+'/#settings')
                expect(mobile.locator('#uploadForm')).to_be_visible()
                # Three colour bands make a crop's actual output measurable.
                png=mobile.evaluate('''()=>{const c=document.createElement('canvas');c.width=600;c.height=400;const x=c.getContext('2d');['#d00000','#00b000','#0000d0'].forEach((color,i)=>{x.fillStyle=color;x.fillRect(i*200,0,200,400)});return c.toDataURL('image/png').split(',')[1]}''')
                def dimensions(src):
                    return mobile.evaluate('''async src=>{const i=new Image();i.src=src;await i.decode();return [i.width,i.height]}''',src)
                def upload(kind,name,crop=False):
                    mobile.get_by_role('tab',name='Add photos',exact=True).click()
                    mobile.get_by_role('radio',name={'places':'Place','transport':'Transport','items':'Items','people':'People'}[kind],exact=True).check();mobile.locator('#name').fill(name)
                    mobile.locator('#photo').set_input_files({'name':'test.png','mimeType':'image/png','buffer':base64.b64decode(png)})
                    expect(mobile.locator('#photoPreview')).to_be_visible()
                    preview=mobile.locator('#photoPreview').get_attribute('src')
                    assert dimensions(preview)==[400,400]
                    bounds=mobile.locator('#photoPreview').bounding_box()
                    assert abs(bounds['width']-bounds['height'])<1,bounds
                    if crop:
                        mobile.locator('#cropUpload').click()
                        expect(mobile.locator('#cropDialog')).to_be_visible()
                        expect(mobile.locator('#cropAspect')).to_have_count(0)
                        expect(mobile.locator('#cropBackgroundGroup')).not_to_be_visible()
                        mobile.locator('#cropZoom').fill('2');mobile.locator('#cropX').fill('100')
                        mobile.locator('#cropSave').click()
                        expect(mobile.locator('#cropDialog')).not_to_be_visible()
                    mobile.locator('#uploadButton').click()
                    expect(mobile.locator('#name')).to_have_value('')
                    mobile.get_by_role('tab',name='Manage photos',exact=True).click()
                    expect(mobile.locator('.library-item strong',has_text=name)).to_be_visible()
                    saved=mobile.evaluate('''async ({kind,name})=>{const s=await(await fetch('/api/state')).json();return s[kind].find(i=>i.name===name)}''',{'kind':kind,'name':name})
                    assert dimensions(saved['image'])==([200,200] if crop else [400,400])
                    assert dimensions(saved['originalImage'])==[600,400]
                    for image in mobile.locator('.library-item img').all():
                        bounds=image.bounding_box()
                        assert abs(bounds['width']-bounds['height'])<1,bounds

                upload('places','Park',crop=True)
                uploaded=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.places[0]}")
                assert uploaded['image']!=uploaded['originalImage'], 'Upload crop must retain its original'
                upload('transport','Bus')
                # Fit the entire source inside a square, with saved coloured letterboxing.
                mobile.get_by_role('button',name='Crop Bus',exact=True).click()
                expect(mobile.locator('#cropBackgroundGroup')).not_to_be_visible()
                mobile.locator('#cropFit').click()
                expect(mobile.locator('#cropBackgroundGroup')).to_be_visible()
                mobile.locator('#cropBackground').fill('#2468ac')
                mobile.locator('#cropZoom').fill('2')
                expect(mobile.locator('#cropBackgroundGroup')).not_to_be_visible()
                mobile.locator('#cropFit').click()
                mobile.screenshot(path='/tmp/transition-cues-square-crop.png',full_page=False)
                mobile.locator('#cropSave').click()
                expect(mobile.locator('#cropDialog')).not_to_be_visible()
                bus=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.transport[0]}")
                assert dimensions(bus['image'])==[600,600]
                def pixel(src,x,y):
                    return mobile.evaluate('''async ({src,x,y})=>{const i=new Image();i.src=src;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const ctx=c.getContext('2d');ctx.drawImage(i,0,0);return [...ctx.getImageData(x,y,1,1).data]}''',{'src':src,'x':x,'y':y})
                def assert_background(src,x,y):
                    sample=pixel(src,x,y)
                    assert all(abs(a-b)<5 for a,b in zip(sample,[36,104,172,255])),sample
                assert_background(bus['image'],300,20)
                assert pixel(bus['image'],20,300)[0]>180  # Original left edge still visible.
                assert pixel(bus['image'],580,300)[2]>180  # Original right edge still visible.
                # Full and partial transparency must enable the picker even without zooming out.
                transparent=mobile.evaluate('''()=>{const c=document.createElement('canvas');c.width=600;c.height=400;const x=c.getContext('2d');x.fillStyle='#d00000';x.fillRect(0,0,200,400);x.fillStyle='rgba(255,255,255,.5)';x.fillRect(200,0,200,400);return c.toDataURL('image/png').split(',')[1]}''')
                mobile.get_by_role('tab',name='Add photos',exact=True).click()
                mobile.get_by_role('radio',name='Place',exact=True).check();mobile.locator('#name').fill('Transparent symbol')
                mobile.locator('#photo').set_input_files({'name':'transparent.png','mimeType':'image/png','buffer':base64.b64decode(transparent)})
                mobile.locator('#cropUpload').click()
                expect(mobile.locator('#cropBackgroundGroup')).to_be_visible()
                mobile.locator('#cropBackground').fill('#2468ac');mobile.locator('#cropSave').click()
                mobile.locator('#uploadButton').click()
                expect(mobile.locator('#name')).to_have_value('')
                mobile.get_by_role('tab',name='Manage photos',exact=True).click()
                expect(mobile.locator('.library-item strong',has_text='Transparent symbol')).to_be_visible()
                symbol=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.places.find(i=>i.name==='Transparent symbol')}")
                assert dimensions(symbol['image'])==[400,400]
                assert_background(symbol['image'],350,200)
                assert pixel(symbol['originalImage'],500,200)[3]==0
                assert 120<pixel(symbol['originalImage'],300,200)[3]<135
                mobile.get_by_role('button',name='Crop Transparent symbol',exact=True).click()
                mobile.locator('#cropZoom').fill('4')
                expect(mobile.locator('#cropBackgroundGroup')).to_be_visible()
                mobile.locator('#cropCancel').click()

                # Partial alpha on its own also enables the colour picker at fill zoom.
                mobile.get_by_role('tab',name='Add photos',exact=True).click()
                partial=mobile.evaluate('''()=>{const c=document.createElement('canvas');c.width=c.height=100;const x=c.getContext('2d');x.fillStyle='rgba(255,0,0,.5)';x.fillRect(0,0,100,100);return c.toDataURL('image/png').split(',')[1]}''')
                mobile.locator('#photo').set_input_files({'name':'partial.png','mimeType':'image/png','buffer':base64.b64decode(partial)})
                mobile.locator('#cropUpload').click()
                expect(mobile.locator('#cropBackgroundGroup')).to_be_visible()
                mobile.locator('#cropCancel').click()
                for name in ['Drink','Coat','Toy','Headphones']:upload('items',name)
                upload('people','Person A');upload('people','Person B')
                # Ordering persists, appears in the picker and respects category edges.
                expect(mobile.get_by_role('button',name='Move Person A left',exact=True)).to_be_disabled()
                expect(mobile.get_by_role('button',name='Move Person B right',exact=True)).to_be_disabled()
                mobile.get_by_role('button',name='Move Person B left',exact=True).click()
                expect(mobile.locator('.library-item strong').first).to_have_text('Person B')
                page.reload();page.get_by_role('button',name='Park',exact=True).click();page.get_by_role('button',name='Bus',exact=True).click();open_step(page,'people')
                assert page.locator('[data-kind="people"] .name').all_text_contents()==['Person B','Person A']
                mobile.get_by_role('button',name='Move Person B right',exact=True).click()
                expect(mobile.locator('.library-item strong').first).to_have_text('Person A')
                # A cancelled edit makes no API write and doesn't change the stored URL.
                get_person=lambda:mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.people[0]}")
                person=get_person(); old_image=person['image']
                mobile.get_by_role('button',name='Crop Person A',exact=True).click()
                expect(mobile.locator('#cropAspect')).to_have_count(0)
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
                for image in page.locator('.picture img').all():
                    bounds=image.bounding_box()
                    assert abs(bounds['width']-bounds['height'])<1,bounds
                # Neither People nor bring-along items is required.
                expect(page.locator('#start')).to_be_enabled();show_plan(page)
                expect(page.locator('.journey-people')).to_have_count(0)
                for _ in range(5):page.locator('#lockedSurface h1:visible').click()
                expect(page.locator('#start')).to_be_visible()
                open_step(page,'items')
                for name in ['Drink','Coat','Toy','Headphones']:page.get_by_role('button',name=name,exact=True).click()
                open_step(page,'people')
                for name in ['Person A','Person B']:page.get_by_role('button',name=name,exact=True).click()
                # People can be toggled independently of the four-item cap.
                page.get_by_role('button',name='Person B',exact=True).click()
                expect(page.locator('#peopleCount')).to_contain_text('1 selected')
                page.get_by_role('button',name='Person B',exact=True).click()
                page.screenshot(path='/tmp/transition-cues-picker.png',full_page=True)
                show_plan(page);expect(page.locator('.person-card')).to_have_count(2)
                assert page.locator('.person-card img').first.evaluate("img=>getComputedStyle(img).borderRadius==='50%'")
                # A real fullscreen browser window cannot be resized by Chromium's protocol.
                # Exit browser fullscreen only; the application's journey display must remain active.
                leave_fullscreen(page)
                expect(page.locator('#lockedSurface')).to_be_visible()
                for width,height in [(1280,900),(1024,768),(768,1024),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    expect(page.locator('.journey-content')).to_be_visible()
                    expect(page.locator('.orientation-notice')).to_have_count(0)
                    for photo in page.locator('.cue-card img,.bring-card img').all():
                        bounds=photo.bounding_box()
                        assert abs(bounds['width']-bounds['height'])<1,bounds
                    assert page.locator('.journey-people').evaluate('(s)=>s.getBoundingClientRect().top>=document.querySelector(".cue-pair").getBoundingClientRect().bottom')
                    page.locator('.bring-items').scroll_into_view_if_needed()
                    expect(page.locator('.bring-card').last).to_be_in_viewport()
                    page.locator('#lockedSurface h1:visible').scroll_into_view_if_needed()
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
                # Rename and transfer actions preserve images and existing locked snapshots.
                second=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.people.find(i=>i.name==='Person B')}")
                mobile.get_by_role('button',name='Rename Person B',exact=True).click()
                expect(mobile.locator('#editName')).to_have_value('Person B')
                mobile.locator('#editName').fill('   ');expect(mobile.locator('#editSave')).to_be_disabled()
                mobile.locator('#editCancel').click()
                expect(mobile.locator('.library-item strong',has_text='Person B')).to_be_visible()
                mobile.get_by_role('button',name='Rename Person B',exact=True).click()
                mobile.locator('#editName').fill('Companion B');mobile.locator('#editSave').click()
                expect(mobile.locator('#editDialog')).not_to_be_visible()
                expect(mobile.locator('.library-item strong',has_text='Companion B')).to_be_visible()
                mobile.get_by_role('button',name='Change category for Companion B',exact=True).click()
                expect(mobile.locator('#editSave')).to_be_disabled()
                mobile.locator('#editDialog').get_by_role('radio',name='Items',exact=True).check()
                mobile.locator('#editCancel').click()
                expect(mobile.locator('.library-item strong',has_text='Companion B')).to_be_visible()
                mobile.get_by_role('button',name='Change category for Companion B',exact=True).click()
                mobile.locator('#editDialog').get_by_role('radio',name='Items',exact=True).check()
                mobile.locator('#editSave').click();expect(mobile.locator('#editDialog')).not_to_be_visible()
                expect(mobile.locator('[data-tab="items"]')).to_have_attribute('aria-pressed','true')
                expect(mobile.get_by_role('button',name='Crop Companion B',exact=True)).to_be_visible()
                moved=mobile.evaluate("async()=>{const s=await(await fetch('/api/state')).json();return s.items.find(i=>i.id==='"+second['id']+"')}")
                assert moved==dict(second,name='Companion B')
                page.reload();expect(page.locator('.person-card')).to_have_count(2)
                expect(page.locator('.person-card figcaption').last).to_have_text('Person B')
                assert page.locator('.person-card img').last.get_attribute('src')==second['image']
                mobile.locator('[data-tab="people"]').click()
                # Removing a person doesn't change the locked snapshot.
                mobile.get_by_role('button',name='Remove Person A',exact=True).click();mobile.get_by_role('button',name='Remove',exact=True).click()
                expect(mobile.locator('#deleteDialog')).not_to_be_visible()
                page.reload();expect(page.locator('.person-card')).to_have_count(2)
                for _ in range(5):page.locator('#lockedSurface h1:visible').click()
                # New version can still restore a journey from before the People category existed.
                page.evaluate("async()=>{const s=await(await fetch('/api/state')).json();localStorage.setItem('tc-locked-journey',JSON.stringify({places:s.places[0],transport:s.transport[0]}))}")
                page.reload();expect(page.locator('#lockedSurface')).to_be_visible();expect(page.locator('.journey-people')).to_have_count(0)
                assert not errors,errors
                browser.close()
                print('PASS: footer removal, optional people, circles, responsive layout, square frames, fill and fit, coloured bars, transparency preservation, cancel, pixel-checked saved crop, original recrop, locked snapshot retention, rename, transfer, cancellations, tap exit and legacy journey restore.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
