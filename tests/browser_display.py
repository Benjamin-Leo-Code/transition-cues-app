"""Landscape gating, stable long-name geometry, navigation and timed tap-to-exit."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'transition_cues'))
from server import make_server
from playwright.sync_api import sync_playwright, expect
from browser_helpers import track_fullscreen, leave_fullscreen, show_plan, open_step


def run(engine):
    with tempfile.TemporaryDirectory() as data:
        server=make_server('127.0.0.1',0,data)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if engine=='chromium' and os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
                browser=getattr(p,engine).launch(**options)
                page=browser.new_page(viewport={'width':1024,'height':768});track_fullscreen(page)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#start')).to_be_disabled()
                expect(page.locator('#pinDialog')).to_have_count(0)
                expect(page.locator('.nav a')).to_have_count(1)
                expect(page.get_by_role('link',name='Picture library',exact=True)).to_have_count(0)
                page.get_by_role('link',name='Settings',exact=True).click()
                expect(page.get_by_role('heading',name='Settings',exact=True)).to_be_visible()
                expect(page.locator('.intro')).to_have_count(0)
                assert page.get_by_role('link',name='Back to plan',exact=True).inner_text()==''
                assert page.locator('.header-title').bounding_box()['x']>512
                expect(page.get_by_role('tab',name='Add photos',exact=True)).to_have_attribute('aria-selected','true')
                expect(page.locator('#uploadForm')).to_be_visible()
                expect(page.locator('#returnForm')).to_have_count(0)
                expect(page.get_by_text('On the tablet',exact=True)).to_have_count(0)
                expect(page.locator('.settings-segments svg')).to_have_count(2)
                page.screenshot(path='/tmp/readysteady-settings-photos.png',full_page=True)
                page.get_by_role('tab',name='More settings',exact=True).click()
                expect(page.get_by_role('tab',name='More settings',exact=True)).to_have_attribute('aria-selected','true')
                expect(page.locator('#uploadForm')).to_have_count(0)
                expect(page.locator('#settingsPanel h2')).to_have_count(1)
                expect(page.locator('#settingsPanel h2')).to_have_text('Back to main screen')
                expect(page.locator('#returnUrl')).to_be_visible()
                page.screenshot(path='/tmp/readysteady-settings-more.png',full_page=True)
                page.get_by_role('tab',name='More settings',exact=True).press('Home')
                expect(page.get_by_role('tab',name='Add photos',exact=True)).to_be_focused()
                expect(page.locator('#uploadForm')).to_be_visible()
                page.get_by_role('tab',name='Add photos',exact=True).press('End')
                expect(page.get_by_role('tab',name='More settings',exact=True)).to_be_focused()
                expect(page.locator('#returnUrl')).to_be_visible()
                page.get_by_role('link',name='Back to plan',exact=False).click()
                expect(page.locator('#start')).not_to_be_visible()
                names=[['places','An especially long destination name across several lines'],['transport','Bus'],['people','A person with a much longer name'],['people','Person B'],['items','Headphones with a very long name'],['items','Drink'],['places','Park'],['transport','A much longer name for the way we travel']]
                page.evaluate("""async names=>{for(const [kind,name] of names){const canvas=document.createElement('canvas');canvas.width=canvas.height=400;const ctx=canvas.getContext('2d');ctx.fillStyle={places:'#9caf88',transport:'#ddbd86',people:'#c5b5d3',items:'#a8c5d6'}[kind];ctx.fillRect(0,0,400,400);const image=canvas.toDataURL('image/png').split(',')[1];const r=await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,image})});if(!r.ok)throw Error('Fixture upload failed')}}""",names)
                page.reload()
                expect(page.locator('[data-kind="places"]')).to_have_count(2)
                expect(page.get_by_role('heading',name='Where are we going?',exact=True)).to_be_visible()
                expect(page.locator('[data-kind="transport"],[data-kind="items"],[data-kind="people"]')).to_have_count(0)
                expect(page.locator('#start')).not_to_be_visible()
                page.screenshot(path='/tmp/readysteady-step-places.png',full_page=True)
                page.get_by_role('button',name=names[0][1],exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','1')
                expect(page.locator('[data-kind="places"]')).to_have_count(0)
                expect(page.get_by_role('heading',name='Where are we going?',exact=True)).to_have_count(0)
                expect(page.locator('.plan-thumbnail')).to_have_count(1)
                page.screenshot(path='/tmp/readysteady-step-transport.png',full_page=True)
                expect(page.locator('#start')).to_be_disabled()
                page.locator('#previousStep').click()
                expect(page.locator('[data-kind="places"][aria-pressed="true"]')).to_have_count(1)
                page.get_by_role('button',name=names[0][1],exact=True).click()
                page.get_by_role('button',name='Bus',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','2')
                expect(page.locator('.plan-thumbnail')).to_have_count(2)
                page.locator('#nextStep').click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','3')
                # Only the current category is rendered; mixed-length card names remain aligned.
                for width,height in [(390,844),(768,1024),(1024,768),(1280,900)]:
                    page.set_viewport_size({'width':width,'height':height})
                    for kind in ['places','transport','items','people']:
                        open_step(page,kind)
                        photos=page.locator(f'[data-kind="{kind}"] img').all()
                        captions=page.locator(f'[data-kind="{kind}"] .name').all()
                        a,b=[photo.bounding_box() for photo in photos]
                        assert abs(a['y']-b['y'])<1,(kind,width,'photo alignment',a,b)
                        assert abs(captions[0].bounding_box()['y']-captions[1].bounding_box()['y'])<1,(kind,width,'name alignment')
                        assert page.locator('[data-kind]').count()==2
                open_step(page,'items')
                page.get_by_role('button',name='Drink',exact=True).click()
                expect(page.locator('.plan-thumbnail')).to_have_count(3)
                expect(page.locator('#planStep')).to_have_attribute('data-step','2')
                page.get_by_role('button',name='Drink',exact=True).click()
                expect(page.locator('.plan-thumbnail')).to_have_count(2)
                for kind in ['items','people']:
                    open_step(page,kind)
                    for item_kind,name in names:
                        if kind==item_kind:page.get_by_role('button',name=name,exact=True).click()
                expect(page.locator('.plan-thumbnail')).to_have_count(6)
                page.locator('[data-edit-step="0"]').click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','0')
                expect(page.locator('[data-kind="places"][aria-pressed="true"]')).to_have_count(1)
                open_step(page,'people')
                page.screenshot(path='/tmp/transition-cues-aligned-picker.png',full_page=True)
                show_plan(page);leave_fullscreen(page)
                def assert_aligned():
                    photos=page.locator('.cue-card img').all()
                    labels=page.locator('.cue-label').all()
                    assert abs(photos[0].bounding_box()['y']-photos[1].bounding_box()['y'])<1
                    assert abs(labels[0].bounding_box()['y']-labels[1].bounding_box()['y'])<1
                    assert page.locator('.cue-name').first.bounding_box()['height']>page.locator('.cue-name').last.bounding_box()['height']
                    pair=page.locator('.cue-pair').bounding_box()
                    groups=[page.locator('.journey-people').bounding_box(),page.locator('.bring-items').bounding_box()]
                    assert abs(groups[0]['y']-groups[1]['y'])<1
                    assert groups[0]['x']+groups[0]['width']<=groups[1]['x']+1
                    assert groups[0]['y']>=pair['y']+pair['height']
                    for selector in ['.person-card img','.bring-card img']:
                        boxes=[image.bounding_box() for image in page.locator(selector).all()]
                        assert abs(boxes[0]['y']-boxes[1]['y'])<1
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                for width,height in [(1024,768),(844,390),(1280,900)]:
                    page.set_viewport_size({'width':width,'height':height});assert_aligned()
                page.screenshot(path='/tmp/transition-cues-landscape.png',full_page=False)
                page.set_viewport_size({'width':390,'height':844})
                expect(page.get_by_role('heading',name='Turn your device')).to_be_visible()
                expect(page.locator('.journey-content')).not_to_be_visible()
                page.screenshot(path='/tmp/transition-cues-portrait.png',full_page=False)
                page.reload();expect(page.get_by_role('heading',name='Turn your device')).to_be_visible()
                page.set_viewport_size({'width':1024,'height':768})
                expect(page.locator('.journey-content')).to_be_visible();assert_aligned()
                # Deterministic time verifies that a fifth late tap cannot exit.
                page.evaluate('window.__tapTime=10000;Date.now=()=>window.__tapTime')
                for _ in range(4):page.locator('.journey-content>h1').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                page.evaluate('window.__tapTime+=3001')
                page.locator('.journey-content>h1').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                for _ in range(4):page.locator('.journey-content>h1').click()
                expect(page.locator('#start')).to_be_visible()
                assert page.evaluate("localStorage.getItem('tc-locked-journey')") is None
                page.reload();expect(page.locator('#start')).not_to_be_visible()
                assert not errors,errors
                browser.close()
                print(f'PASS ({engine}): selection-card photo/name alignment at phone/tablet sizes, one-step wizard, thumbnail summary and editing, back navigation, optional-item skip, conditional start button, accessible navigation, portrait prompt, landscape display, aligned long names and photos, companion groups, snapshot reload and timed five-tap exit.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
