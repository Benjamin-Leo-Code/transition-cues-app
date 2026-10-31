"""Optional end-to-end check using an isolated server and two browser contexts."""
import base64
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'transition_cues'))
from server import make_server
from playwright.sync_api import sync_playwright, expect
from browser_helpers import track_fullscreen, leave_fullscreen, show_plan


def run():
    with tempfile.TemporaryDirectory() as data:
        server = make_server('127.0.0.1', 0, data)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                options = {'headless': True}
                if os.environ.get('CHROMIUM_PATH'):
                    options['executable_path'] = os.environ['CHROMIUM_PATH']
                browser = p.chromium.launch(**options)
                tablet = browser.new_context(viewport={'width':1280,'height':900})
                page = tablet.new_page()
                track_fullscreen(page)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                url = f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                expect(page.locator('#start')).to_be_disabled()
                page.screenshot(path='/tmp/transition-cues-empty.png', full_page=True)
                phone = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
                mobile = phone.new_page()
                mobile.on('pageerror', lambda error: errors.append(str(error)))
                mobile.goto(url + '/#manage')
                expect(mobile.locator('#uploadForm')).to_be_visible()
                # Test images are generated within the browser, never shipped in the real library.
                for kind, name, color in [('places','Park','#9caf88'),('transport','Bus','#ddbd86'),('items','Drink','#a8c5d6'),('items','Headphones','#c5b5d3'),('items','Coat','#d7b4a2'),('items','Toy','#c0cdaa'),('items','Bag','#e0d1a2')]:
                    png = mobile.evaluate('''([name,color]) => {const c=document.createElement('canvas');c.width=500;c.height=320;const x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,500,320);x.fillStyle='#254d43';x.font='32px sans-serif';x.textAlign='center';x.fillText(name,250,170);return c.toDataURL('image/png').split(',')[1];}''', [name,color])
                    mobile.locator('#photo').set_input_files({'name':name+'.png','mimeType':'image/png','buffer':base64.b64decode(png)})
                    mobile.locator('#name').fill(name)
                    mobile.get_by_role('radio',name={'places':'Place','transport':'Transport','items':'Items','people':'People'}[kind],exact=True).check()
                    mobile.locator('#uploadButton').click()
                    expect(mobile.locator('.library-item strong', has_text=name)).to_be_visible()
                mobile.screenshot(path='/tmp/transition-cues-phone.png', full_page=True)
                assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Phone layout overflows'
                page.reload()
                page.get_by_role('button', name='Park').click()
                page.get_by_role('button', name='Bus').click()
                # Bring-along items are optional; old saved journeys still restore.
                expect(page.locator('#start')).to_be_enabled()
                show_plan(page)
                expect(page.locator('.bring-items')).to_have_count(0)
                page.evaluate("const j=JSON.parse(localStorage.getItem('tc-locked-journey'));delete j.items;localStorage.setItem('tc-locked-journey',JSON.stringify(j));")
                page.reload()
                expect(page.locator('#lockedSurface')).to_be_visible()
                expect(page.locator('.bring-items')).to_have_count(0)
                for _ in range(5): page.locator('#lockedSurface h1:visible').click()
                expect(page.locator('#start')).to_be_visible()
                page.get_by_role('button', name='Park').click()
                page.get_by_role('button', name='Bus').click()
                for name in ['Drink','Headphones','Coat','Toy']:
                    page.get_by_role('button', name=name, exact=True).click()
                expect(page.locator('#itemCount')).to_contain_text('4 of 4')
                expect(page.get_by_role('button', name='Bag', exact=True)).to_be_disabled()
                expect(page.locator('[data-kind="items"][aria-pressed="true"]')).to_have_count(4)
                page.get_by_role('button', name='Headphones', exact=True).click()
                expect(page.get_by_role('button', name='Bag', exact=True)).to_be_enabled()
                page.get_by_role('button', name='Bag', exact=True).click()
                expect(page.locator('#itemCount')).to_contain_text('4 of 4')
                page.get_by_role('button', name='Bag', exact=True).click()
                page.get_by_role('button', name='Headphones', exact=True).click()
                page.screenshot(path='/tmp/transition-cues-picker.png', full_page=True)
                show_plan(page)
                expect(page.locator('#lockedSurface')).to_be_visible()
                expect(page.locator('nav')).to_have_count(0)
                expect(page.locator('.bring-card')).to_have_count(4)
                # Restoring a tampered/oversized snapshot must also enforce the cap.
                page.evaluate("const j=JSON.parse(localStorage.getItem('tc-locked-journey'));j.items.push(j.items[0]);localStorage.setItem('tc-locked-journey',JSON.stringify(j));")
                page.reload()
                expect(page.locator('#lockedSurface')).to_be_visible()
                for _ in range(4): page.locator('#lockedSurface h1:visible').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                page.locator('#lockedSurface h1:visible').click()
                expect(page.locator('#start')).to_be_visible()
                show_plan(page)
                expect(page.locator('.bring-card')).to_have_count(4)
                # A real fullscreen browser window cannot be resized by Chromium's protocol.
                # Exit browser fullscreen only; the application's journey display must remain active.
                leave_fullscreen(page)
                expect(page.locator('#lockedSurface')).to_be_visible()
                for width,height in [(1280,900),(1024,768),(768,1024),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Locked layout overflows horizontally'
                    if height>width:
                        expect(page.locator('.orientation-notice')).to_be_visible()
                        expect(page.locator('.cue-pair')).not_to_be_visible()
                        continue
                    assert page.locator('.bring-items').evaluate('(items)=>items.getBoundingClientRect().top >= document.querySelector(".cue-pair").getBoundingClientRect().bottom'), 'Items must be below the main photos'
                page.set_viewport_size({'width':1280,'height':900})
                page.screenshot(path='/tmp/transition-cues-locked.png', full_page=True)
                mobile.locator('[data-tab="items"]').click()
                mobile.get_by_role('button', name='Remove Drink', exact=True).click()
                mobile.get_by_role('button', name='Remove', exact=True).click()
                expect(mobile.locator('#deleteDialog')).not_to_be_visible()
                page.reload()
                expect(page.locator('.bring-card')).to_have_count(4)
                for image in page.locator('.bring-card img').all():
                    expect(image).to_be_visible()
                    assert image.evaluate('(img)=>img.complete && img.naturalWidth>0')
                # Removing a photo from the phone must not remove it from a locked tablet.
                mobile.locator('[data-tab="places"]').click()
                mobile.get_by_role('button', name='Remove Park').click()
                mobile.get_by_role('button', name='Remove', exact=True).click()
                expect(mobile.locator('#deleteDialog')).not_to_be_visible()
                page.reload()
                expect(page.locator('#lockedSurface')).to_be_visible()
                assert page.locator('.cue-card img').first.evaluate('(img)=>img.complete && img.naturalWidth>0')
                for _ in range(5): page.locator('#lockedSurface h1:visible').click()
                expect(page.locator('#start')).not_to_be_visible()
                expect(page.locator('#lockedSurface')).to_have_count(0)
                expect(page.locator('#itemCount')).to_contain_text('0 of 4')
                expect(page.get_by_role('button', name='Drink', exact=True)).to_have_count(0)
                mobile.get_by_role('link', name='Settings', exact=True).click()
                mobile.locator('#returnUrl').fill('http://homeassistant.local:8123/lovelace/0')
                mobile.get_by_role('button', name='Save link').click()
                expect(mobile.get_by_role('link', name='Back to main screen', exact=False)).to_be_visible()
                assert not errors, errors
                browser.close()
                print('PASS: original flows; item uploads, optional selection, four-item cap, deselection, old journey restore, item layout at tablet/phone sizes, item snapshots after refresh and cross-device deletion; no browser errors.')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    run()
