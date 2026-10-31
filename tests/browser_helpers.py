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


def type_pin(page, selector, digits):
    # Unlike fill() on a text input, keyboard typing does not wait for a hidden
    # custom control to become ready. Click the visible entry before typing.
    field = page.locator(selector)
    field.click()
    page.keyboard.press('Delete')
    page.keyboard.type(digits)


def show_plan(page):
    page.locator('#start').click()
    page.locator('#planContinue').click()
