"""Bounded retries without logging URLs, credentials or response bodies."""
import json
import random
import time
import datetime as dt
from email.utils import parsedate_to_datetime
from contextlib import nullcontext
from urllib.parse import urlparse
from rift.limiter import RIOT_LIMITER
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class FetchError(RuntimeError):
    pass

def fetch_json(url, headers=None, attempts=5, opener=urlopen, sleep=time.sleep, observer=None):
    emit=observer or (lambda event: None)
    riot = (urlparse(url).hostname or "").endswith(".api.riotgames.com")
    for attempt in range(attempts):
        try:
            emit('requests')
            with RIOT_LIMITER.lock if riot else nullcontext():
                if riot: RIOT_LIMITER.wait()
                with opener(Request(url,headers=headers or {}),timeout=30) as response:
                    if riot: RIOT_LIMITER.observe(response.headers)
                    value=json.load(response)
                    emit('responses_ok')
                    return value
        except HTTPError as exc:
            emit('http_errors')
            emit('http_'+str(exc.code))
            if riot: RIOT_LIMITER.observe(exc.headers or {})
            if exc.code!=429 and not 500<=exc.code<600:
                raise FetchError(f'HTTP {exc.code}') from None
            delay=2**attempt+random.random()
            retry=exc.headers.get('Retry-After','') if exc.headers else ''
            if retry.isdigit():
                delay=max(delay,int(retry))
            elif retry:
                try:
                    delay=max(delay,(parsedate_to_datetime(retry)-dt.datetime.now(dt.timezone.utc)).total_seconds())
                except (ValueError,TypeError): pass
            if riot and exc.code==429:
                with RIOT_LIMITER.lock:
                    RIOT_LIMITER.blocked=max(RIOT_LIMITER.blocked,RIOT_LIMITER.clock()+delay)
        except (URLError,TimeoutError,OSError,ValueError):
            emit('network_or_decode_errors')
            delay=2**attempt+random.random()
        if attempt+1<attempts:
            emit('retries')
            sleep(delay)
    raise FetchError('request exhausted retries') from None
