"""Run against `python -m http.server 4173` from the repository root.

Requires: pip install playwright && python -m playwright install chromium
Use --baseline to verify that the original deployment fails the regression.
"""
import argparse
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:4173/')
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
baseline = subprocess.check_output(
    ['git', 'show', 'c3fccda:assets/index-r5RRMtiK.js'], cwd=root
) if args.baseline else None


def route_assets(route):
    if baseline and route.request.url.endswith('/assets/index-r5RRMtiK.js'):
        route.fulfill(body=baseline, content_type='text/javascript')
    else:
        # The deployment uses a Pages project prefix; the local server has none.
        route.continue_(url=route.request.url.replace('/luma-learning-site/', '/'))


def open_shelf(page, kind='阅读'):
    page.goto(args.url)
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name=kind, exact=True).click()
    page.locator('.ns-stage').scroll_into_view_if_needed()
    page.locator('.ns-slot').first.wait_for()


def slot_position(slot):
    return slot.evaluate('''e => ({
        x: parseFloat(e.style.getPropertyValue('--slot-x')),
        y: parseFloat(e.style.getPropertyValue('--slot-y'))
    })''')


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1100},
                                  reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(8000)
    page.route('**/luma-learning-site/**', route_assets)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    for kind in ['阅读', '写作']:
        for half in ['bottom', 'top']:
            for dx in [-80, 80]:
                open_shelf(page, kind)
                slots = page.locator('.ns-slot')
                positions = [slot_position(slot) for slot in slots.all()]
                index = (min if half == 'top' else max)(
                    range(len(positions)), key=lambda i: positions[i]['y'])
                slot = slots.nth(index)
                book = slot.locator('.ns-book').bounding_box()
                x, y = book['x'] + book['width'] / 2, book['y'] + book['height'] / 2
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + dx, y, steps=8)
                page.wait_for_function("document.querySelector('.ns-dragging') !== null")
                moved = slot_position(slot)['x'] - positions[index]['x']
                assert moved * dx > 0, (kind, half, dx, moved)
                # Once active, a steep diagonal must still update the shelf.
                before = slot_position(slot)['x']
                page.mouse.move(x + dx * 1.25, y + (220 if half == 'top' else -220))
                assert abs(slot_position(slot)['x'] - before) > 1
                page.mouse.up()
                assert page.locator('.ns-dragging').count() == 0
                assert page.locator('.ns-create').count() == 0
                # Release snaps to a slot; no accidental book opening/creation.
                snapped = slot_position(slot)
                assert abs(snapped['x']) < 0.01 or abs(snapped['y']) < 0.01
                print(f'PASS {kind} {half} dx={dx}: follows pointer, diagonal, snap, no click')

    open_shelf(page)
    stage = page.locator('.ns-stage')
    slot = page.locator('.ns-slot').first
    before = slot_position(slot)
    stage.focus()
    page.keyboard.press('ArrowRight')
    assert slot_position(slot) != before
    before = slot_position(slot)
    page.mouse.move(1100, 500)
    page.mouse.wheel(0, 60)
    page.wait_for_function('''old => parseFloat(document.querySelector('.ns-slot')
        .style.getPropertyValue('--slot-x')) !== old''', arg=before['x'])
    print('PASS keyboard and wheel controls')

    # A captured gesture must end even if capture is lost outside the orbit.
    bounds = page.locator('.ns-orbit').bounding_box()
    x, y = bounds['x'] + 150, bounds['y'] + 100
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y)
    assert page.locator('.ns-dragging').count() == 1
    # Let the browser apply pending pointer capture before releasing it.
    page.mouse.move(x + 45, y)
    page.locator('.ns-orbit').evaluate('e => e.releasePointerCapture(1)')
    page.mouse.move(x + 50, y)
    page.wait_for_function("document.querySelector('.ns-dragging') === null")
    page.mouse.up()
    page.locator('.ns-placeholder').first.click()
    assert page.locator('.ns-create').is_visible()
    page.get_by_role('button', name='取消', exact=True).click()
    page.locator('.ns-book:not(.ns-placeholder)').click()
    print('PASS lost capture cleanup and subsequent book clicks')

    page.set_viewport_size({'width': 700, 'height': 1100})
    open_shelf(page)
    page.get_by_role('button', name='横向书架', exact=True).click()
    orbit = page.locator('.ns-orbit')
    orbit.scroll_into_view_if_needed()
    bounds = orbit.bounding_box()
    x, y = bounds['x'] + bounds['width'] / 2, bounds['y'] + 30
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 100, y, steps=8)
    assert orbit.evaluate('e => e.scrollLeft') > 0
    page.mouse.up()
    print('PASS rail mouse scrolling')

    mobile = browser.new_context(viewport={'width': 390, 'height': 1000},
                                 is_mobile=True, has_touch=True, reduced_motion='reduce')
    touch = mobile.new_page()
    touch.route('**/luma-learning-site/**', route_assets)
    touch.on('pageerror', lambda error: errors.append(str(error)))
    open_shelf(touch)
    cdp = mobile.new_cdp_session(touch)
    for half in ['top', 'bottom']:
        open_shelf(touch)
        slots = touch.locator('.ns-slot')
        positions = [slot_position(slot) for slot in slots.all()]
        index = (min if half == 'top' else max)(
            range(len(positions)), key=lambda i: positions[i]['y'])
        book = slots.nth(index).locator('.ns-book').bounding_box()
        x, y = book['x'] + book['width'] / 2, book['y'] + book['height'] / 2
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
        for dx in [10, 20, 40, 60]:
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + dx, 'y': y}]})
        moved = slot_position(slots.nth(index))['x'] - positions[index]['x']
        assert moved > 0, (half, moved)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        assert touch.locator('.ns-create').count() == 0
        print(f'PASS mobile {half}: real touch drag follows finger')
    assert not errors, errors
    browser.close()
