import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
Path(os.environ.get('PICKOU_SCREENSHOTS','/tmp/pickou-browser')).mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 for width,height,label in [(1440,1080,'desktop'),(390,844,'mobile')]:
  page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  # Exercise the image failure contract without relying on external network access.
  page.route('https://ddragon.leagueoflegends.com/**',lambda route:route.abort())
  page.goto(os.environ.get('PICKOU_TEST_URL','http://127.0.0.1:3000'),wait_until='networkidle')
  expect(page.get_by_role('button',name='다리우스',exact=True)).to_be_visible()
  page.get_by_role('button',name='다리우스',exact=True).click()
  expect(page.locator('.cg-result-title')).to_contain_text('다리우스')
  expect(page.locator('.cg-card').first).to_be_visible()
  response=page.request.get(os.environ.get('PICKOU_TEST_API','http://127.0.0.1:8000')+'/api/counter-guide/counters',params={'lane':'탑','opponent':'다리우스'}).json()
  expected_rows=sum(response['groups'].values(),[])
  self_cards=page.locator('.cg-group .cg-card')
  assert self_cards.count()==sum(len(response['groups'][k]) for k in ('hard','counter','even'))
  row=next(r for r in expected_rows if r['champion']==self_cards.first.get_attribute('data-champion'))
  assert row['advantage'] in self_cards.first.inner_text() and row['caution'] in self_cards.first.inner_text()
  assert page.locator('.cg-evidence.theoretical').count()>0
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  assert page.locator('.cg-card img').first.get_attribute('src')=='/champion-fallback.svg'
  page.screenshot(path=str(Path(os.environ.get('PICKOU_SCREENSHOTS','/tmp/pickou-browser'))/f'{label}.png'),full_page=False)
  for lane in ['정글','미드','바텀','서폿']:
   page.get_by_role('button',name=lane,exact=False).first.click()
   expect(page.locator('.cg-result-title')).to_have_count(0)
   expect(page.locator('.cg-champion-select').first).to_be_visible()
  page.get_by_role('button',name='바텀',exact=False).first.click()
  search=page.get_by_role('textbox',name='상대 챔피언 검색');search.fill('징키')
  expect(page.locator('.cg-champion-select')).to_have_count(1)
  expect(page.get_by_role('button',name='징크스',exact=True)).to_be_visible()
  search.fill('ㅈㅋㅅ');expect(page.get_by_role('button',name='징크스',exact=True)).to_be_visible()
  page.get_by_role('button',name='징크스',exact=True).click()
  expect(page.locator('.cg-result-title')).to_contain_text('징크스')
  assert not errors,errors
  print(json.dumps({'viewport':label,'direction_and_actual_reasons':'pass','lane_reset':'pass','alias_and_initial_search':'pass','image_failure_fallback':'pass','no_horizontal_overflow':'pass','js_errors':errors}))
  page.close()
 browser.close()
