"""Real-browser favorites checks against the running PICKOU web/API servers."""
import json
import os
import tempfile
from playwright.sync_api import sync_playwright, expect

URL=os.environ.get('PICKOU_TEST_URL','http://127.0.0.1:3000')
KEY='pickou.favorites.v1'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    for width,height,label in [(1440,1080,'desktop'),(390,844,'mobile')]:
        context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
        context.route('https://ddragon.leagueoflegends.com/**',lambda route:route.abort())
        page=context.new_page();errors=[];requests=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:requests.append(request.url) if '/counter-guide/counters?' in request.url else None)
        page.goto(URL,wait_until='networkidle')
        add=page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True)
        expect(add).to_be_enabled();add.click()
        expect(page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
        expect(page.locator('.cg-champion-select').first).to_have_attribute('aria-label','다리우스')
        assert requests==[],'Star unexpectedly requested a counter lookup'
        expect(page.locator('.cg-result-title')).to_have_count(0)
        checkbox=page.get_by_role('checkbox',name='즐겨찾기만 보기');checkbox.check()
        expect(page.locator('.cg-champion-select')).to_have_count(1)
        page.get_by_role('button',name='다리우스',exact=True).click()
        expect(page.locator('.cg-result-title')).to_contain_text('다리우스')
        expect(page.locator('.cg-card').first).to_be_visible()
        page.reload(wait_until='networkidle')
        remove=page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)
        expect(remove).to_have_attribute('aria-pressed','true')
        # Both native keyboard activation paths must toggle only the star.
        remove.focus();page.keyboard.press('Enter')
        add=page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True);expect(add).to_be_focused()
        page.keyboard.press('Space');expect(page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)).to_be_focused()
        expect(page.locator('.cg-result-title')).to_have_count(0)
        page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True).click()
        page.get_by_role('checkbox',name='즐겨찾기만 보기').check()
        expect(page.get_by_text('이 포지션에 즐겨찾기한 챔피언이 없습니다.',exact=True)).to_be_visible()
        page.reload(wait_until='networkidle')
        expect(page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True)).to_have_attribute('aria-pressed','false')
        page.get_by_role('button',name='판테온 즐겨찾기 등록',exact=True).click()
        page.get_by_role('button',name='미드',exact=True).click()
        expect(page.get_by_role('button',name='판테온 즐겨찾기 등록',exact=True)).to_have_attribute('aria-pressed','false')
        page.get_by_role('button',name='판테온 즐겨찾기 등록',exact=True).click()
        page.get_by_role('button',name='탑',exact=True).click()
        expect(page.get_by_role('button',name='판테온 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
        page.get_by_role('button',name='판테온 즐겨찾기 해제',exact=True).click()
        page.get_by_role('button',name='미드',exact=True).click()
        expect(page.get_by_role('button',name='판테온 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
        checkbox=page.get_by_role('checkbox',name='즐겨찾기만 보기');checkbox.check()
        search=page.get_by_role('textbox',name='상대 챔피언 검색');search.fill('아우솔')
        expect(page.locator('.cg-champion-select')).to_have_count(0)
        checkbox.uncheck();expect(page.get_by_role('button',name='아우렐리온 솔',exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # Corrupt storage must not break the app or change its counter API.
        page.evaluate('(key)=>localStorage.setItem(key,"{broken")',KEY);page.reload(wait_until='networkidle')
        expect(page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True)).to_be_enabled()
        page.get_by_role('button',name='다리우스',exact=True).click();expect(page.locator('.cg-result-title')).to_contain_text('다리우스')
        assert not errors,errors
        # Close/reopen an actual browser context via serialized persistent storage.
        page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True).click()
        storage=context.storage_state();context.close()
        restored=browser.new_context(storage_state=storage,viewport={'width':width,'height':height})
        restored.route('https://ddragon.leagueoflegends.com/**',lambda route:route.abort())
        tab=restored.new_page();tab.goto(URL,wait_until='networkidle')
        expect(tab.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
        restored.close()
        print(json.dumps({'viewport':label,'save_remove_sort_filter_reload_lane_isolation_keyboard_click_separation_corruption_reopen':'pass','js_errors':errors}))
    denied=browser.new_context()
    denied.add_init_script("Object.defineProperty(Storage.prototype,'getItem',{value(){throw new DOMException('blocked','SecurityError')}});Object.defineProperty(Storage.prototype,'setItem',{value(){throw new DOMException('quota','QuotaExceededError')}});")
    denied.route('https://ddragon.leagueoflegends.com/**',lambda route:route.abort())
    page=denied.new_page();page.goto(URL,wait_until='networkidle')
    page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True).click()
    expect(page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
    expect(page.get_by_text('브라우저에 저장할 수 없어 즐겨찾기가 현재 화면에서만 유지됩니다.',exact=True)).to_be_visible()
    page.get_by_role('button',name='다리우스',exact=True).click();expect(page.locator('.cg-result-title')).to_contain_text('다리우스')
    denied.close();browser.close();print('PASS: unavailable localStorage does not break favorites or counter lookup')
    with tempfile.TemporaryDirectory(prefix='pickou-favorites-profile-') as profile:
        for reopening in (False,True):
            context=p.chromium.launch_persistent_context(profile,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
            context.route('https://ddragon.leagueoflegends.com/**',lambda route:route.abort())
            page=context.new_page();page.goto(URL,wait_until='networkidle')
            if reopening:
                expect(page.get_by_role('button',name='다리우스 즐겨찾기 해제',exact=True)).to_have_attribute('aria-pressed','true')
            else:
                page.get_by_role('button',name='다리우스 즐겨찾기 등록',exact=True).click()
                page.wait_for_function('(key)=>JSON.parse(localStorage.getItem(key)).lanes["탑"].includes("다리우스")',arg=KEY)
            context.close()
    print('PASS: favorite survives actual Chromium process close/relaunch with the same local profile')
