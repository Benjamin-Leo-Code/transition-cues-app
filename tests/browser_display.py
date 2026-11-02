"""Responsive multi-select planning, floating actions, library tabs and saved journeys."""
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

PNG='iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAALUlEQVR4nGOcs76DgZaAiaamj1owasGoBaMWjFowasGoBaMWjFowasGoBVQEAKxHAhNnbcHJAAAAAElFTkSuQmCC'
LONG='An especially long destination name across several lines'


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
                url=f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                expect(page.locator('.plan-fab:visible')).to_have_count(0)
                for width,height in [(320,844),(390,844),(768,1024),(1024,768)]:
                    page.set_viewport_size({'width':width,'height':height})
                    brand=page.locator('.brand').bounding_box();nav=page.locator('.nav').bounding_box()
                    assert brand['x']+brand['width']<=nav['x']+1
                    assert abs(nav['y']+nav['height']/2-brand['y']-brand['height']/2)<1
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.get_by_role('link',name='Settings',exact=True).click()
                expect(page.get_by_role('heading',name='Manage photos',exact=True)).to_be_visible()
                expect(page.locator('.settings-segments svg')).to_have_count(4)
                expect(page.locator('#uploadForm')).not_to_be_visible()
                page.get_by_role('tab',name='Places',exact=True).press('ArrowRight')
                expect(page.get_by_role('tab',name='Transport',exact=True)).to_be_focused()
                page.get_by_role('tab',name='Transport',exact=True).press('End')
                expect(page.get_by_role('tab',name='People',exact=True)).to_be_focused()
                page.get_by_role('tab',name='People',exact=True).press('Home')
                expect(page.get_by_role('tab',name='Places',exact=True)).to_be_focused()
                page.screenshot(path='/tmp/readysteady-manage-photos.png',full_page=True)
                page.get_by_role('link',name='Back to plan',exact=True).click()
                names=[['places',LONG],['places','Park'],['places','Stop C'],['places','Stop D'],['places','Stop E'],['places','Stop F'],['places','Stop G'],['transport','Bus'],['transport','Train'],['transport','Walking'],['people','A person with a much longer name'],['people','Person B']]+[['items',name] for name in ['Headphones with a very long name','Drink','Coat','Toy','Bag','Book']]
                page.evaluate("""async names=>{for(const [kind,name] of names){const c=document.createElement('canvas');c.width=c.height=400;const x=c.getContext('2d');x.fillStyle={places:'#9caf88',transport:'#ddbd86',people:'#c5b5d3',items:'#a8c5d6'}[kind];x.fillRect(0,0,400,400);const r=await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,image:c.toDataURL('image/png').split(',')[1]})});if(!r.ok)throw Error('Fixture upload failed')}}""",names)
                page.reload()
                expect(page.locator('.location-count,[data-location-count]')).to_have_count(0)
                expect(page.locator('#nextStep')).not_to_be_visible()
                expect(page.locator('[data-choice-group="places"] .frequent-choices .picture')).to_have_count(3)
                expect(page.locator('[data-choice-group="places"] .other-choices .picture:not(.add-picture)')).to_have_count(4)
                page.screenshot(path='/tmp/readysteady-step-places.png',full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                frequent=page.locator('.frequent-choices .picture').all();other=page.locator('.other-choices .picture:not(.add-picture)').all()
                assert len({round(x.bounding_box()['y']) for x in frequent})==1
                assert len({round(x.bounding_box()['y']) for x in other})==1
                page.screenshot(path='/tmp/readysteady-frequent-choices.png',full_page=True)
                page.set_viewport_size({'width':1024,'height':768})
                opening_y=page.locator('#planHeading').bounding_box()['y']
                page.get_by_role('button',name=LONG,exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','0')
                expect(page.locator('#nextStep')).to_be_visible()
                page.get_by_role('button',name='Park',exact=True).click()
                expect(page.locator('[data-kind="places"][aria-pressed="true"]')).to_have_count(2)
                page.get_by_role('button',name='Park',exact=True).click()
                page.locator('#nextStep').click()
                expect(page.locator('#planHeading')).to_have_text('How are we travelling?')
                assert abs(page.locator('#planHeading').bounding_box()['y']-opening_y)<1
                expect(page.locator('#nextStep')).not_to_be_visible()
                expect(page.locator('.brand,.nav')).to_have_count(0)
                page.get_by_role('button',name='Bus',exact=True).click()
                page.get_by_role('button',name='Train',exact=True).click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','1')
                expect(page.locator('[data-kind="transport"][aria-pressed="true"]')).to_have_count(2)
                page.screenshot(path='/tmp/readysteady-step-transport.png',full_page=True)
                next_box=page.locator('#nextStep').bounding_box()
                assert abs(next_box['width']-next_box['height'])<1
                page.locator('#nextStep').click()
                expect(page.locator('#planHeading')).to_have_text('Who is coming along?')
                expect(page.locator('[data-kind="items"],[data-add-kind="items"]')).to_have_count(0)
                expect(page.locator('#start')).not_to_be_visible()
                expect(page.locator('#nextStep')).to_be_visible()
                assert abs(page.locator('#planHeading').bounding_box()['y']-opening_y)<1
                page.screenshot(path='/tmp/readysteady-people-page.png',full_page=True)
                page.locator('#nextStep').click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','3')
                expect(page.locator('#planHeading')).to_have_text('What is coming with us?')
                expect(page.locator('[data-kind="people"],[data-add-kind="people"]')).to_have_count(0)
                expect(page.locator('#start')).to_be_enabled()
                expect(page.locator('#nextStep')).not_to_be_visible()
                start_box=page.locator('#start').bounding_box()
                assert abs(start_box['x']-next_box['x'])<1 and abs(start_box['y']-next_box['y'])<1
                page.screenshot(path='/tmp/readysteady-items-page.png',full_page=True)
                expect(page.locator('#itemCount,.items-guidance')).to_have_count(0)
                # Names grow downwards; first-row photos stay aligned at each viewport.
                for width,height in [(390,844),(768,1024),(1024,768)]:
                    page.set_viewport_size({'width':width,'height':height})
                    for kind in ['places','transport','people','items']:
                        open_step(page,kind)
                        photos=page.locator(f'[data-kind="{kind}"] img').all()
                        captions=page.locator(f'[data-kind="{kind}"] .name').all()
                        assert abs(photos[0].bounding_box()['y']-photos[1].bounding_box()['y'])<1
                        assert abs(captions[0].bounding_box()['y']-captions[1].bounding_box()['y'])<1
                # More than three locations, multiple transports, and more than four items.
                open_step(page,'places')
                for name in ['Park','Stop C','Stop D']:page.get_by_role('button',name=name,exact=True).click()
                expect(page.locator('[data-kind="places"][aria-pressed="true"]')).to_have_count(4)
                page.locator('#nextStep').click()
                page.get_by_role('button',name='Walking',exact=True).click()
                page.locator('#nextStep').click()
                for kind,name in names:
                    if kind in ['items','people']:
                        open_step(page,kind)
                        page.get_by_role('button',name=name,exact=True).click()
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(6)
                page.get_by_role('button',name='Book',exact=True).click()
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(5)
                page.get_by_role('button',name='Book',exact=True).click()
                # Add a picture without changing the plan, and retain category-specific upload.
                page.locator('[data-add-kind="items"]').click()
                expect(page.locator('#uploadForm input[name="kind"]')).to_have_count(0)
                page.locator('#name').fill('New item')
                page.locator('#photo').set_input_files({'name':'item.png','mimeType':'image/png','buffer':base64.b64decode(PNG)})
                page.screenshot(path='/tmp/readysteady-add-item.png',full_page=True)
                page.locator('#uploadButton').click()
                expect(page.locator('#uploadDialog')).not_to_be_visible()
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(6)
                expect(page.get_by_role('button',name='New item',exact=True)).to_be_visible()
                page.locator('[data-edit-kind="people"]').first.click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','2')
                expect(page.locator('[data-kind="items"]')).to_have_count(0)
                page.locator('[data-edit-kind="items"]').first.click()
                expect(page.locator('#planStep')).to_have_attribute('data-step','3')
                expect(page.locator('[data-kind="people"]')).to_have_count(0)
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(6)

                page.set_viewport_size({'width':320,'height':600});page.evaluate('window.scrollTo(0,0)')
                expect(page.locator('#scrollCue')).to_be_visible()
                expect(page.locator('#start')).to_be_in_viewport()
                assert page.locator('#start').evaluate("el=>getComputedStyle(el).position")=='fixed'
                cue=page.locator('#scrollCue').bounding_box();action=page.locator('#start').bounding_box()
                assert cue['x']+cue['width']<=action['x']
                for kind in ['places','transport','people','items']:
                    group=page.locator(f'[data-selection-group="{kind}"]');icon=group.locator('.plan-category').bounding_box()
                    assert all(x.bounding_box()['x']>=icon['x']-1 for x in group.locator('.plan-thumbnail').all())
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path='/tmp/readysteady-floating-plan.png',full_page=True)
                page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                expect(page.locator('#scrollCue')).not_to_be_visible()
                page.set_viewport_size({'width':1024,'height':768})
                page.screenshot(path='/tmp/transition-cues-aligned-picker.png',full_page=True)
                show_plan(page);leave_fullscreen(page)
                expected=[LONG,'Park','Stop C','Stop D','Bus','Train','Walking']
                expect(page.locator('.cue-name')).to_have_text(expected)
                expect(page.locator('.cue-label')).to_have_text(['To:','Then:','Then:','Then:','By:','Then:','Then:'])
                expect(page.locator('.bring-card')).to_have_count(6)
                expect(page.locator('.person-card')).to_have_count(2)
                for width,height in [(1024,768),(844,390),(1280,900),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    photos=page.locator('.cue-card img').all();labels=page.locator('.cue-label').all()
                    assert abs(photos[0].bounding_box()['y']-photos[1].bounding_box()['y'])<1
                    assert abs(labels[0].bounding_box()['y']-labels[1].bounding_box()['y'])<1
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    for image in photos:
                        box=image.bounding_box();assert abs(box['width']-box['height'])<1
                    page.locator('.bring-card').last.scroll_into_view_if_needed()
                page.locator('.locked').evaluate('el=>el.scrollTop=0')
                page.screenshot(path='/tmp/transition-cues-portrait.png',full_page=True)
                page.set_viewport_size({'width':1024,'height':768})
                page.locator('.locked').evaluate('el=>el.scrollTop=0')
                page.screenshot(path='/tmp/transition-cues-landscape.png',full_page=True)
                page.screenshot(path='/tmp/readysteady-multiple-locations.png',full_page=True)
                page.reload();expect(page.locator('.cue-name')).to_have_text(expected)
                expect(page.locator('.bring-card')).to_have_count(6)
                usage=page.request.get(url+'/api/state').json()
                assert next(x for x in usage['places'] if x['name']==LONG)['usageCount']==1
                # A snapshot remains visible if a selected record is removed elsewhere.
                victim=next(x for x in usage['items'] if x['name']=='Book')
                page.request.post(url+'/api/delete',data={'kind':'items','id':victim['id']})
                page.reload();expect(page.locator('.bring-card')).to_have_count(6)
                # Five taps must still fall within three seconds.
                page.evaluate('window.__tapTime=10000;Date.now=()=>window.__tapTime')
                for _ in range(4):page.locator('.journey-content>h1').click()
                page.evaluate('window.__tapTime+=3001');page.locator('.journey-content>h1').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                for _ in range(4):page.locator('.journey-content>h1').click()
                expect(page.locator('#nextStep')).to_be_visible()
                page.get_by_role('button',name='Reset',exact=True).click()
                expect(page.locator('.plan-thumbnail')).to_have_count(0)
                expect(page.locator('.plan-fab:visible')).to_have_count(0)
                # Earlier single-location/single-transport snapshots remain compatible.
                page.evaluate("""async()=>{const s=await(await fetch('/api/state')).json();localStorage.setItem('tc-locked-journey',JSON.stringify({places:s.places[0],transport:s.transport[0],items:s.items}))}""")
                page.reload();expect(page.locator('.cue-card')).to_have_count(2)
                expect(page.locator('.bring-card')).to_have_count(6)
                assert not errors,errors
                browser.close()
                print(f'PASS ({engine}): responsive headers and photos, category tabs, multi-select locations/transports, explicit floating Next and Show the plan, unlimited items, inline upload retention, category wrapping, ordered display, legacy snapshots, usage persistence and timed tap exit.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
