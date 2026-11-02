"""Cross-check supplied official evidence; static versions never establish launch."""
from urllib.parse import urlparse

def confirm_release(public_patch, region, notes, live):
    def official(url):
        u=urlparse(url or '')
        return u.scheme=='https' and u.hostname in ('www.leagueoflegends.com','leagueoflegends.com')
    notes_ok=(notes.get('patch')==public_patch and official(notes.get('url')) and bool(notes.get('checked_at')) and bool(notes.get('content_digest')))
    live_ok=(live.get('patch')==public_patch and live.get('region')==region and live.get('applied') is True and official(live.get('url')) and bool(live.get('checked_at')))
    return {'status':'confirmed' if notes_ok and live_ok else 'pending','notes_checked':notes_ok,'regional_live_checked':live_ok}

def impact(lanes, champion_names, items, runes, dependencies=None):
    """Unknown dependencies mean broad review, never silently excluding matchups."""
    from scripts.check_patch import make_review_queue
    affected=set(champion_names)
    broad=False
    for kind,ids in (('items',items),('runes',runes)):
        for identifier in ids:
            users=(dependencies or {}).get(kind,{}).get(str(identifier))
            if users is None: broad=True
            else: affected.update(users)
    return make_review_queue(lanes,affected,broad,'pending')
