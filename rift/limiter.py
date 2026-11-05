"""Single-process serialized Riot client limiter; one worker per API key."""
import threading
import time
from collections import deque

class Limiter:
    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self.clock=clock; self.sleep=sleep; self.requests=deque(); self.blocked=0; self.lock=threading.RLock()
    def wait(self):
        now=self.clock()
        while self.requests and self.requests[0]<=now-120: self.requests.popleft()
        delay=max(0,self.blocked-now, (self.requests[-1]+1.3-now) if self.requests else 0, (self.requests[0]+120-now) if len(self.requests)>=90 else 0)
        if delay: self.sleep(delay)
        self.requests.append(self.clock())
    def observe(self, headers):
        for kind in ('App','Method'):
            try:
                limits={float(w):int(n) for n,w in (s.split(':') for s in headers.get(f'X-{kind}-Rate-Limit','').split(',') if s)}
                for part in headers.get(f'X-{kind}-Rate-Limit-Count','').split(','):
                    if not part: continue
                    n,w=part.split(':'); window=float(w)
                    if int(n)>=limits.get(window,float('inf')): self.blocked=max(self.blocked,self.clock()+window)
            except (ValueError,TypeError): self.blocked=max(self.blocked,self.clock()+120)
RIOT_LIMITER=Limiter()
