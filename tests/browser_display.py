"""Portrait/landscape layouts, long-name geometry, settings navigation and tap-to-exit."""
import argparse
import base64
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
                for width,height in [(320,844),(390,844),(768,1024),(1024,768)]:
                    page.set_viewport_size({'width':width,'height':height})
                    brand=page.locator('.brand').bounding_box();nav=page.locator('.nav').bounding_box()
                    assert brand['x']+brand['width']<=nav['x']+1,(width,brand,nav)
                    assert page.locator('.brand img').bounding_box()['width']>=56
                    assert nav['y']>=brand['y']-1 and nav['y']+nav['height']<=brand['y']+brand['height']+1,(width,brand,nav)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')

                expect(page.get_by_role('link',name='Picture library',exact=True)).to_have_count(0)
                page.get_by_role('link',name='Settings',exact=True).click()
                expect(page.get_by_role('heading',name='Manage photos',exact=True)).to_be_visible()
                expect(page.locator('.intro')).to_have_count(0)
                assert page.get_by_role('link',name='Back to plan',exact=True).inner_text()==''
                assert page.locator('.header-title').bounding_box()['x']>512
                expect(page.locator('#uploadForm')).not_to_be_visible()
                expect(page.locator('#returnForm')).to_have_count(0)
                expect(page.locator('.settings-segments svg')).to_have_count(4)
                expect(page.get_by_role('tab',name='Place',exact=True)).to_have_attribute('aria-selected','true')
                expect(page.locator('#library')).to_be_visible()
                page.get_by_role('tab',name='Place',exact=True).press('ArrowRight')
                expect(page.get_by_role('tab',name='Transport',exact=True)).to_be_focused()
                expect(page.get_by_role('tab',name='Transport',exact=True)).to_have_attribute('aria-selected','true')
                page.get_by_role('tab',name='Transport',exact=True).press('End')
                expect(page.get_by_role('tab',name='People',exact=True)).to_be_focused()
                page.get_by_role('tab',name='People',exact=True).press('Home')
                expect(page.get_by_role('tab',name='Place',exact=True)).to_be_focused()
                page.screenshot(path='/tmp/readysteady-manage-photos.png',full_page=True)
                page.get_by_role('link',name='Back to plan',exact=False).click()
                expect(page.locator('#start')).not_to_be_visible()
                names=[['places','An especially long destination name across several lines'],['transport','Bus'],['people','A person with a much longer name'],['people','Person B'],['items','Headphones with a very long name'],['items','Drink'],['places','Park'],['transport','A much longer name for the way we travel']]
                page.evaluate("""async names=>{for(const [kind,name] of names){const canvas=document.createElement('canvas');canvas.width=canvas.height=400;const ctx=canvas.getContext('2d');ctx.fillStyle={places:'#9caf88',transport:'#ddbd86',people:'#c5b5d3',items:'#a8c5d6'}[kind];ctx.fillRect(0,0,400,400);const image=canvas.toDataURL('image/png').split(',')[1];const r=await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,image})});if(!r.ok)throw Error('Fixture upload failed')}}""",names)
                page.reload()
                expect(page.locator('[data-kind="places"]')).to_have_count(2)
                expect(page.get_by_role('heading',name='Where are we going?',exact=True)).to_be_visible()
                expect(page.locator('#planStep p')).to_have_count(0)
                expect(page.get_by_role('group',name='Number of stops',exact=True)).to_be_visible()
                page.locator('[data-location-count="1"]').press('ArrowRight')
                expect(page.locator('[data-location-count="2"]')).to_have_attribute('aria-pressed','true')
                page.locator('[data-location-count="2"]').press('End')
                expect(page.locator('[data-location-count="3"]')).to_have_attribute('aria-pressed','true')
                page.locator('[data-location-count="3"]').press('Home')
                expect(page.locator('[data-location-count="1"]')).to_have_attribute('aria-pressed','true')

                expect(page.locator('.step-number')).to_have_count(0)
                expect(page.locator('[data-kind="transport"],[data-kind="items"],[data-kind="people"]')).to_have_count(0)
                expect(page.locator('#start')).not_to_be_visible()
                expect(page.locator('[data-choice-group="places"] .picture').last).to_have_attribute('data-add-kind','places')
                page.locator('[data-add-kind="places"]').click()
                expect(page.locator('#uploadForm')).to_be_visible()
                expect(page.locator('#uploadForm input[name="kind"]')).to_have_count(0)
                page.locator('#name').fill('Cancelled upload')
                page.screenshot(path='/tmp/readysteady-add-item.png',full_page=True)
                page.locator('#uploadCancel').click()
                expect(page.locator('#uploadDialog')).not_to_be_visible()
                expect(page.locator('[data-kind="places"]')).to_have_count(2)
                page.evaluate('window.scrollTo(0,0)')
                opening_heading_y=page.locator('#planHeading').bounding_box()['y']
                page.screenshot(path='/tmp/readysteady-step-places.png',full_page=True)
                page.get_by_role('button',name=names[0][1],exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','1')
                expect(page.locator('[data-kind="places"]')).to_have_count(0)
                expect(page.get_by_role('heading',name='How are we travelling',exact=True)).to_be_visible()
                assert abs(page.locator('#planHeading').bounding_box()['y']-opening_heading_y)<1,(opening_heading_y,page.locator('#planHeading').bounding_box(),page.locator('.header').bounding_box())
                expect(page.get_by_role('heading',name='Where are we going?',exact=True)).to_have_count(0)
                expect(page.locator('.plan-thumbnail')).to_have_count(1)
                expect(page.locator('.brand,.nav,#previousStep')).to_have_count(0)
                expect(page.get_by_role('button',name='Reset',exact=True)).to_be_visible()
                expect(page.locator('.header .plan-thumbnails')).to_be_visible()
                page.screenshot(path='/tmp/readysteady-step-transport.png',full_page=True)
                expect(page.locator('#start')).to_be_disabled()
                page.locator('[data-edit-step="0"]').click()
                expect(page.locator('[data-kind="places"][aria-pressed="true"]')).to_have_count(1)
                page.get_by_role('button',name=names[0][1],exact=True).click()
                page.get_by_role('button',name='Bus',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','2')
                expect(page.locator('.plan-thumbnail')).to_have_count(2)
                expect(page.get_by_role('heading',name='Who is coming along?',exact=True)).to_be_visible()
                assert abs(page.locator('#planHeading').bounding_box()['y']-opening_heading_y)<1,(opening_heading_y,page.locator('#planHeading').bounding_box(),page.locator('.header').bounding_box())
                expect(page.get_by_role('heading',name='What is coming with us',exact=True)).to_be_visible()
                expect(page.locator('#planStep .optional-label')).to_have_count(2)
                expect(page.get_by_text('Choose up to 4 items',exact=True)).to_be_visible()
                assert page.locator('[data-choice-group="people"]').bounding_box()['y']<page.locator('[data-choice-group="items"]').bounding_box()['y']
                expect(page.locator('.step-number')).to_have_count(0)
                expect(page.locator('#nextStep')).to_have_count(0)
                page.set_viewport_size({'width':390,'height':600})
                page.evaluate('window.scrollTo(0,0)')
                expect(page.get_by_role('button',name='Scroll to finish',exact=True)).to_be_visible()
                page.locator('#scrollCue').click()
                page.wait_for_function('()=>window.scrollY>0')
                page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                expect(page.locator('#scrollCue')).not_to_be_visible()
                expect(page.locator('#start')).to_be_in_viewport()
                assert page.locator('.wizard-actions').evaluate("el=>getComputedStyle(el).position")=='static'
                assert page.locator('#start').bounding_box()['y']>=page.locator('#planStep').bounding_box()['y']+page.locator('#planStep').bounding_box()['height']
                page.screenshot(path='/tmp/readysteady-plan-bottom.png',full_page=True)

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
                        assert page.locator('[data-kind]').count()==(4 if kind in ['items','people'] else 2)
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
                # Adding within a category retains the plan and returns to its current step.
                page.locator('[data-add-kind="items"]').click()
                page.locator('#name').fill('New item')
                page.locator('#photo').set_input_files({'name':'item.png','mimeType':'image/png','buffer':base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=')})
                page.locator('#uploadButton').click()
                expect(page.locator('#uploadDialog')).not_to_be_visible()
                expect(page.locator('#planStep')).to_have_attribute('data-step','2')
                expect(page.locator('.plan-thumbnail')).to_have_count(6)
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(2)
                expect(page.get_by_role('button',name='New item',exact=True)).to_be_visible()
                expect(page.locator('[data-choice-group="items"] .picture').last).to_have_attribute('data-add-kind','items')
                # Multi-select categories wrap beneath their own glyphs on a narrow phone.
                page.set_viewport_size({'width':320,'height':844})
                expect(page.locator('.plan-category svg')).to_have_count(4)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                assert page.locator('.plan-thumbnails').evaluate('(row) => row.scrollWidth <= row.clientWidth')
                for kind in ['people','items']:
                    group=page.locator(f'[data-selection-group="{kind}"]')
                    icon=group.locator('.plan-category').bounding_box()
                    boxes=[thumb.bounding_box() for thumb in group.locator('.plan-thumbnail').all()]
                    assert boxes[1]['y']>boxes[0]['y'],(kind,boxes,group.bounding_box(),page.locator('.plan-thumbnails').bounding_box())
                    assert all(box['x']>=icon['x']-1 for box in boxes)
                    assert all(box['x']+box['width']<=group.bounding_box()['x']+group.bounding_box()['width']+1 for box in boxes)
                for kind in ['places','transport']:
                    expect(page.locator(f'[data-selection-group="{kind}"] .plan-thumbnail')).to_have_count(1)
                page.locator('[data-edit-kind="items"]').last.click()
                expect(page.locator('#itemsHeading')).to_be_focused()
                page.screenshot(path='/tmp/readysteady-grouped-selections.png',full_page=True)
                page.set_viewport_size({'width':1280,'height':900})
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
                    if page.viewport_size['height']>page.viewport_size['width'] and page.viewport_size['width']<=620:
                        assert groups[1]['y']>=groups[0]['y']+groups[0]['height']
                    else:
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
                expect(page.locator('.journey-content')).to_be_visible()
                expect(page.locator('.orientation-notice')).to_have_count(0)
                assert_aligned()
                page.locator('.bring-card').last.scroll_into_view_if_needed()
                expect(page.locator('.bring-card').last).to_be_in_viewport()
                page.screenshot(path='/tmp/transition-cues-portrait.png',full_page=False)
                page.reload();expect(page.locator('.journey-content')).to_be_visible()
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
                page.get_by_role('button',name='Reset',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','0')
                expect(page.locator('.plan-thumbnail,#resetPlan')).to_have_count(0)
                expect(page.locator('.brand')).to_be_visible()
                expect(page.get_by_role('link',name='Settings',exact=True)).to_be_visible()
                expect(page.locator('#start')).not_to_be_visible()
                page.get_by_role('button',name=names[0][1],exact=True).click()
                page.get_by_role('button',name='Bus',exact=True).click()
                expect(page.locator('[data-kind="items"][aria-pressed="true"],[data-kind="people"][aria-pressed="true"]')).to_have_count(0)
                page.reload();expect(page.locator('#start')).not_to_be_visible()
                # Shared usage ordering and an ordered three-stop journey.
                page.evaluate("""async () => {
                    const image='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=';
                    for(const name of ['Stop C','Stop D','Stop E','Stop F','Stop G']) await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'places',name,image})});
                    const state=await (await fetch('/api/state')).json();
                    for(const name of ['Stop C','Stop C','Stop D','Stop E']) await fetch('/api/usage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({places:[state.places.find(x=>x.name===name).id],transport:[state.transport[0].id]})});
                }""")
                page.reload()
                expect(page.locator('[data-location-count="1"]')).to_have_attribute('aria-pressed','true')
                expect(page.locator('[data-choice-group="places"] .frequent-choices .picture')).to_have_count(3)
                expect(page.locator('[data-choice-group="places"] .other-choices .picture:not(.add-picture)')).to_have_count(4)
                expect(page.locator('.frequent-choices .picture').first.locator('.name')).to_have_text('Stop C')
                page.set_viewport_size({'width':390,'height':844})
                frequent=page.locator('[data-choice-group="places"] .frequent-choices .picture').all()
                other=page.locator('[data-choice-group="places"] .other-choices .picture:not(.add-picture)').all()
                assert len({round(x.bounding_box()['y']) for x in frequent})==1
                assert len({round(x.bounding_box()['y']) for x in other})==1
                assert other[0].bounding_box()['y']>frequent[0].bounding_box()['y']
                page.screenshot(path='/tmp/readysteady-frequent-choices.png',full_page=True)
                page.locator('[data-location-count="3"]').click()
                page.get_by_role('button',name='Stop E',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','0')
                expect(page.locator('#start')).to_be_disabled()
                page.get_by_role('button',name='Stop C',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','0')
                page.get_by_role('button',name='Stop D',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','1')
                expect(page.locator('[data-selection-group="places"] .plan-thumbnail')).to_have_count(3)
                page.get_by_role('button',name='Bus',exact=True).click()
                show_plan(page);leave_fullscreen(page)
                expect(page.locator('.cue-name')).to_have_text(['Stop E','Stop C','Stop D','Bus'])
                expect(page.locator('.cue-label')).to_have_text(['To:','Then:','Then:','By:'])
                for width,height in [(390,844),(1024,768)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    for image in page.locator('.cue-card img').all():
                        box=image.bounding_box();assert abs(box['width']-box['height'])<1
                page.screenshot(path='/tmp/readysteady-multiple-locations.png',full_page=True)
                page.reload()
                expect(page.locator('.cue-name')).to_have_text(['Stop E','Stop C','Stop D','Bus'])
                usage=page.request.get(f'http://127.0.0.1:{server.server_port}/api/state').json()
                assert next(x for x in usage['places'] if x['name']=='Stop C')['usageCount']==3
                for _ in range(5):page.locator('.journey-content>h1').click()
                page.get_by_role('button',name='Reset',exact=True).click()
                expect(page.locator('[data-location-count="1"]')).to_have_attribute('aria-pressed','true')
                # Two stops use the same ordering; deselection and changing the limit trim choices.
                page.locator('[data-location-count="3"]').click()
                page.get_by_role('button',name='Stop C',exact=True).click()
                page.get_by_role('button',name='Stop D',exact=True).click()
                page.get_by_role('button',name='Stop C',exact=True).click()
                expect(page.locator('[data-selection-group="places"] .plan-thumbnail')).to_have_count(1)
                page.locator('[data-location-count="2"]').click()
                page.get_by_role('button',name='Stop E',exact=True).click()
                page.get_by_role('button',name='Bus',exact=True).click()
                show_plan(page);leave_fullscreen(page)
                expect(page.locator('.cue-name')).to_have_text(['Stop D','Stop E','Bus'])
                page.reload();expect(page.locator('.cue-name')).to_have_text(['Stop D','Stop E','Bus'])
                assert not errors,errors
                browser.close()
                print(f'PASS ({engine}): selection-card photo/name alignment at phone/tablet sizes, one-step wizard, thumbnail summary and editing, reset navigation, optional-item skip, conditional start button, accessible navigation, portrait and landscape display, aligned long names and photos, companion groups, snapshot reload, shared frequency ordering, phone three/four-column grids, ordered two/three-location plans and timed five-tap exit.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
