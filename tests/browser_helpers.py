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
    page.locator('#start').click()
    page.locator('#planContinue').click()
