"""Check follow-up bugs against a local server; --baseline replays 8fc46f4."""
import argparse
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:4173/')
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
old_assets = {
    name: subprocess.check_output(['git', 'show', f'8fc46f4:assets/{name}'], cwd=root)
    for name in ['index-r5RRMtiK.js', 'index-lZhR9QW_.css', 'shelf-drag.js']
} if args.baseline else {}


def route_assets(route):
    name = route.request.url.rsplit('/', 1)[-1]
    if name in old_assets:
        route.fulfill(body=old_assets[name], content_type=(
            'text/css' if name.endswith('.css') else 'text/javascript'))
    else:
        route.continue_(url=route.request.url.replace('/luma-learning-site/', '/'))


def open_shelf(page, kind='阅读'):
    page.goto(args.url)
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name=kind, exact=True).click()
    page.locator('.ns-stage').scroll_into_view_if_needed()


def rail_drag(page):
    page.set_viewport_size({'width': 700, 'height': 1100})
    open_shelf(page)
    page.get_by_role('button', name='横向书架', exact=True).click()
    orbit = page.locator('.ns-orbit')
    orbit.scroll_into_view_if_needed()
    box = orbit.bounding_box()
    x, y = box['x'] + 200, box['y'] + 20
    start = orbit.evaluate('e => e.scrollLeft')
    page.mouse.move(x, y)
    page.mouse.down()
    for dx in [8, 24, 32, 48]:
        page.mouse.move(x - dx, y)
        if dx > 8:
            actual = orbit.evaluate('e => e.scrollLeft')
            assert abs(actual - (start + dx)) < 3, (dx, actual, start)
    page.mouse.up()
    assert orbit.evaluate('e => getComputedStyle(e).scrollSnapType') != 'none'


def keyboard_open(page):
    open_shelf(page)
    content = page.locator('.ns-shelf + *')
    before = content.bounding_box()['y']
    page.locator('.ns-stage').focus()
    page.keyboard.press('Enter')
    assert content.bounding_box()['y'] < before - 100, 'Enter did not open the notebook'


def wheel_units(page):
    for mode, delta in [(1, 3), (2, -1)]:
        open_shelf(page)
        slot = page.locator('.ns-slot').first
        before = slot.get_attribute('style')
        page.locator('.ns-stage').dispatch_event('wheel', {
            'deltaX': 0, 'deltaY': delta, 'deltaMode': mode,
            'bubbles': True, 'cancelable': True,
        })
        assert slot.get_attribute('style') != before, f'wheel deltaMode={mode} was ignored'
        before = slot.get_attribute('style')
        page.locator('.ns-stage').dispatch_event('wheel', {
            'deltaY': 60, 'deltaMode': 0, 'ctrlKey': True,
            'bubbles': True, 'cancelable': True,
        })
        assert slot.get_attribute('style') == before, 'Ctrl+wheel should retain browser zoom'


def empty_draft_save(page):
    open_shelf(page, '写作')
    draft = page.get_by_role('textbox', name='写作草稿', exact=True)
    draft.fill('This text must stay deleted.')
    page.wait_for_function('''() => JSON.parse(localStorage.getItem(
        'luma:learning-workspace:v2')).library.pages.some(p => p.text === 'This text must stay deleted.')''')
    draft.fill('')
    page.wait_for_function('''() => JSON.parse(localStorage.getItem(
        'luma:learning-workspace:v2')).library.pages.every(p => p.text === '')''', timeout=1500)
    # Reopen from persisted state, rather than just checking the current input.
    open_shelf(page, '写作')
    page.locator('.n-writing-pages').wait_for()
    assert draft.input_value() == ''
    page.get_by_role('textbox', name='写作页标题', exact=True).fill('Only a title')
    page.get_by_role('textbox', name='写作修改笔记', exact=True).fill('Only a note')
    page.get_by_role('button', name='新的一页', exact=True).click()
    assert page.locator('.n-writing-pages button').count() == 1
    page.get_by_role('button', name='Only a title', exact=False).click()
    assert page.get_by_role('textbox', name='写作修改笔记', exact=True).input_value() == 'Only a note'


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    failures = []
    for check in [rail_drag, keyboard_open, wheel_units, empty_draft_save]:
        context = browser.new_context(viewport={'width': 1440, 'height': 900},
                                      reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(5000)
        page.route('**/luma-learning-site/**', route_assets)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            check(page)
            assert not errors, errors
            print(f'PASS {check.__name__}', flush=True)
        except Exception as error:
            failures.append(check.__name__)
            print(f'FAIL {check.__name__}: {error}', flush=True)
        finally:
            context.close()
    browser.close()
    assert not failures, failures
