"""PIN keypad checks: real button entry, masked values, and unchanged server protection."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'transition_cues'))
from server import make_server
from playwright.sync_api import sync_playwright, expect


def run(engine):
    with tempfile.TemporaryDirectory() as data:
        server=make_server('127.0.0.1',0,data)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if engine=='chromium' and os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
                browser=getattr(p,engine).launch(**options)
                context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
                page=context.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                url=f'http://127.0.0.1:{server.server_port}'
                def tap_pin(target,field,digits):
                    target.locator('#'+field).tap()
                    pad=target.locator('#'+field).locator('xpath=ancestor::form').locator('.pin-keypad')
                    pad.locator('[data-pin-key="clear"]').tap()
                    for digit in digits:pad.locator('[data-pin-key="'+digit+'"]').tap()
                page.goto(url)
                expect(page.locator('#pinDialog')).to_be_visible()
                expect(page.locator('#pinDialog input, #pinDialog [contenteditable]')).to_have_count(0)
                expect(page.locator('#pinSubmit')).to_be_disabled()
                tap_pin(page,'pinInput','001234567')  # Accept 8 digits at most; preserve leading zeroes.
                expect(page.locator('#pinInput')).to_have_attribute('aria-label','Parent PIN, 8 digits entered')
                assert page.locator('#pinInput').inner_text()=='●'*8
                assert '00123456' not in page.locator('#pinDialog').text_content()
                assert page.evaluate("() => [...new FormData(document.querySelector('#pinForm'))].length") == 0
                page.locator('#pinPad [data-pin-key="back"]').tap()
                expect(page.locator('#pinInput')).to_have_attribute('aria-label','Parent PIN, 7 digits entered')
                page.locator('#pinSubmit').tap()
                expect(page.locator('#pinConfirm')).to_have_attribute('aria-pressed','true')
                tap_pin(page,'pinConfirm','00123457')
                page.locator('#pinSubmit').tap()
                expect(page.locator('#pinError')).to_contain_text('do not match')
                expect(page.locator('#pinInput')).to_have_attribute('aria-label','Parent PIN, 0 digits entered')
                # Setup cannot be dismissed with Escape.
                page.keyboard.press('Escape');expect(page.locator('#pinDialog')).to_be_visible()
                tap_pin(page,'pinInput','0123');page.locator('#pinSubmit').tap()
                tap_pin(page,'pinConfirm','0123');page.locator('#pinSubmit').tap()
                expect(page.locator('#pinDialog')).not_to_be_visible()
                expect(page.locator('#pinInput')).to_have_attribute('aria-label','Parent PIN, 0 digits entered')
                # Add a tiny temporary fixture through the same authenticated API.
                page.evaluate("""async()=>{const image='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=';for(const [kind,name] of [['places','Park'],['transport','Bus']])await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,image})})}""")
                page.reload();page.get_by_role('button',name='Park',exact=True).tap();page.get_by_role('button',name='Bus',exact=True).tap();page.locator('#start').tap()
                expect(page.locator('#lockedSurface')).to_be_visible()
                for _ in range(5):page.locator('#lockedSurface h1').tap()
                expect(page.locator('#pinDialog')).to_be_visible()
                page.screenshot(path=f'/tmp/transition-cues-keypad-{engine}.png',full_page=True)
                tap_pin(page,'pinInput','123');expect(page.locator('#pinSubmit')).to_be_disabled()
                tap_pin(page,'pinInput','0000');page.locator('#pinSubmit').tap()
                expect(page.locator('#pinError')).to_contain_text('not recognised')
                expect(page.locator('#lockedSurface')).to_be_visible()
                expect(page.locator('#pinInput')).to_have_attribute('aria-label','Parent PIN, 0 digits entered')
                page.locator('#pinCancel').tap();expect(page.locator('#pinDialog')).not_to_be_visible()
                expect(page.locator('#lockedSurface')).to_be_visible()
                for _ in range(5):page.locator('#lockedSurface h1').tap()
                tap_pin(page,'pinInput','0123');page.locator('#pinSubmit').tap()
                expect(page.locator('#lockedSurface')).to_have_count(0)
                page.get_by_role('link',name='Settings',exact=True).tap()
                expect(page.locator('#changePinForm input, #changePinForm [contenteditable]')).to_have_count(0)
                expect(page.locator('#changePinSubmit')).to_be_disabled()
                tap_pin(page,'oldPin','0123');tap_pin(page,'newPin','00112233');tap_pin(page,'newPinConfirm','00112234')
                page.locator('#changePinSubmit').tap();expect(page.locator('#changeError')).to_contain_text('do not match')
                tap_pin(page,'oldPin','0123');tap_pin(page,'newPin','00112233');tap_pin(page,'newPinConfirm','00112233')
                page.locator('#changePinSubmit').tap();expect(page.locator('#toast')).to_contain_text('PIN changed')
                # A separate device must still authenticate using the new shared PIN.
                other=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
                mobile=other.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)))
                mobile.goto(url+'/#manage');expect(mobile.locator('#pinDialog')).to_be_visible()
                tap_pin(mobile,'pinInput','0123');mobile.locator('#pinSubmit').tap();expect(mobile.locator('#pinError')).to_contain_text('not recognised')
                # Physical keyboard entry stays available without an editable field.
                mobile.locator('#pinInput').click();mobile.keyboard.type('0011223');mobile.keyboard.press('Backspace');mobile.keyboard.type('33');mobile.keyboard.press('Enter')
                expect(mobile.locator('#uploadForm')).to_be_visible()
                expect(mobile.locator('input[type="password"]')).to_have_count(0)
                assert not errors,errors
                browser.close()
                print(f'PASS ({engine}): keypad setup, confirmation, leading zeros, length cap, clear/backspace, PIN change, wrong PIN, lock/cancel, cross-device login and keyboard entry without password fields.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
