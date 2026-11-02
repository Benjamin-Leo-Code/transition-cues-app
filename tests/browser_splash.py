"""Verify the pre-lock splash and browser-local opt-out in Chromium and WebKit."""
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
                page.goto(url)
                page.evaluate("""async()=>{const image='iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAALUlEQVR4nGOcs76DgZaAiaamj1owasGoBaMWjFowasGoBaMWjFowasGoBVQEAKxHAhNnbcHJAAAAAElFTkSuQmCC';for(const [kind,name] of [['places','Park'],['transport','Bus']])await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,image})})}""")
                def choose(target):
                    target.get_by_role('button',name='Park',exact=True).click()
                    target.get_by_role('button',name='Bus',exact=True).click()
                def unlock():
                    for _ in range(5):page.locator('#lockedSurface h1:visible').click()
                    expect(page.locator('#start')).to_be_visible()
                page.reload();choose(page)
                expect(page.get_by_text('The display locks when you start.',exact=False)).not_to_be_visible()
                page.locator('#start').click()
                expect(page.locator('#planDialog')).to_be_visible()
                expect(page.get_by_role('heading',name='A quick note',exact=True)).to_be_visible()
                expect(page.locator('#planBack')).to_have_count(0)
                expect(page.locator('#planHelp br')).to_have_count(1)
                expect(page.locator('#lockedSurface')).to_have_count(0)
                assert page.evaluate("localStorage.getItem('tc-locked-journey')") is None
                assert page.locator('#planForm').evaluate('(f)=>f.scrollWidth<=innerWidth')
                # Dismissing with Escape must not persist a checked preference or start a journey.
                page.locator('#skipPlanIntro').check();page.keyboard.press('Escape')
                expect(page.locator('#planDialog')).not_to_be_visible()
                assert page.evaluate("localStorage.getItem('tc-skip-plan-intro')") is None
                page.locator('#start').click();expect(page.locator('#skipPlanIntro')).not_to_be_checked()
                page.keyboard.press('Escape');expect(page.locator('#planDialog')).not_to_be_visible()
                page.locator('#start').click();page.locator('#planContinue').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                unlock()
                # The unchecked default repeats, including after a reload.
                page.reload();choose(page);page.locator('#start').click()
                expect(page.locator('#planDialog')).to_be_visible()
                page.locator('#skipPlanIntro').check()
                page.screenshot(path=f'/tmp/transition-cues-splash-{engine}.png',full_page=False)
                page.locator('#planContinue').click();expect(page.locator('#lockedSurface')).to_be_visible()
                assert page.evaluate("localStorage.getItem('tc-skip-plan-intro')")=='true'
                # A restored locked plan never shows the splash again.
                page.reload();expect(page.locator('#lockedSurface')).to_be_visible()
                expect(page.locator('#planDialog')).not_to_be_visible()
                unlock();page.reload();choose(page);page.locator('#start').click()
                expect(page.locator('#lockedSurface')).to_be_visible()
                expect(page.locator('#planDialog')).not_to_be_visible()
                # Another device/browser context keeps its own default.
                other=browser.new_context(viewport={'width':1280,'height':900})
                second=other.new_page();second.goto(url);choose(second);second.locator('#start').click()
                expect(second.locator('#planDialog')).to_be_visible()
                expect(second.locator('#skipPlanIntro')).not_to_be_checked()
                assert not errors,errors
                browser.close()
                print(f'PASS ({engine}): pre-lock splash, Escape dismissal, unchecked repeat, persisted skip, reload restore, tap exit and independent device preference.')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium')
    run(parser.parse_args().browser)
