"""Helpers for observing browser operations without changing app behavior."""


def track_fullscreen(page):
    # requestFullscreen is asynchronous. Keep its native return value and behavior,
    # but let the resize tests wait for a pending entry before asking to exit.
    page.add_init_script('''(() => {
        const request = Element.prototype.requestFullscreen;
        if (!request) return;
        window.__testFullscreenInstrumented = true;
        Element.prototype.requestFullscreen = function (...args) {
            const pending = request.apply(this, args);
            window.__testFullscreenRequest = Promise.resolve(pending).catch(() => {});
            return pending;
        };
    })();''')


def leave_fullscreen(page):
    assert page.evaluate('() => !Element.prototype.requestFullscreen || window.__testFullscreenInstrumented'), "Fullscreen observer was not installed"
    page.evaluate('''async () => {
        await window.__testFullscreenRequest;
        if (document.fullscreenElement) await document.exitFullscreen();
        await new Promise(requestAnimationFrame);
    }''')
    assert page.evaluate('() => !document.fullscreenElement'), 'Browser did not leave fullscreen'


def show_plan(page):
    open_step(page,'items')
    page.locator('#start').click()
    page.locator('#planContinue').click()


def open_step(page, kind):
    target={'places':0,'transport':1,'people':2,'items':3}[kind]
    page.locator('#planStep').wait_for()
    current=int(page.locator('#planStep').get_attribute('data-step'))
    while current>target:
        candidates=page.locator('[data-edit-step]').all()
        earlier=[button for button in candidates if int(button.get_attribute('data-edit-step'))<=target]
        max(earlier,key=lambda button:int(button.get_attribute('data-edit-step'))).click()
        current=int(page.locator('#planStep').get_attribute('data-step'))
    while current<target:
        if current<3:
            page.locator('#nextStep').click()
        current=int(page.locator('#planStep').get_attribute('data-step'))


def open_add(page, kind):
    base=page.url.split('#')[0].rstrip('/')
    page.goto(base+'/#choose')
    page.reload()
    page.locator('#planStep').wait_for()
    if kind!='places':
        page.locator('[data-kind="places"]').first.click()
        page.locator('#nextStep').click()
    if kind in ['people','items']:
        page.locator('[data-kind="transport"]').first.click()
        page.locator('#nextStep').click()
    if kind=='items':page.locator('#nextStep').click()
    page.locator(f'[data-add-kind="{kind}"]').click()
    page.locator('#uploadDialog').wait_for(state='visible')
    assert page.locator('#uploadForm input[name="kind"]').count()==0


def open_library(page, kind):
    base=page.url.split('#')[0].rstrip('/')
    page.goto(base+'/#settings')
    page.locator(f'[data-tab="{kind}"]').click()
    page.locator('#library').wait_for()


def choose_pair(page, place='Park', transport='Bus'):
    open_step(page,'places')
    for kind,name in [('places',place),('transport',transport)]:
        button=page.get_by_role('button',name=name,exact=True)
        if button.get_attribute('aria-pressed')!='true':button.click()
        page.locator('#nextStep').click()
    page.locator('#nextStep').click()
