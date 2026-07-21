import re
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .config import SEARCH_PROVIDER, SERPER_API_KEY

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'


# Consecutive total-failure counter: once the whole rotation pool is out of
# credits every call fails, so stop burning retry latency for the rest of the
# run and let the keyless fallbacks carry it. Reset on any success.
_SERPER_FAILS = {'count': 0}
_SERPER_GIVE_UP = 3


def serper_search(query, num=10, gl='ca', hl='en', retries=3):
    """Search via the tmcp Serper key-rotation proxy (route: /api/serper/search).

    The pool rotates across several serper.dev keys; a request that lands on an
    exhausted key returns 400 'Not enough credits', so retry a couple of times
    to let the rotation move to a live key."""
    if not SERPER_API_KEY: return []
    if _SERPER_FAILS['count'] >= _SERPER_GIVE_UP:
        raise RuntimeError('Serper disabled for this run after repeated credit failures')
    last = ''
    for _ in range(max(1, retries)):
        r=requests.post('https://tmcp.vercel.app/api/serper/search',headers={'X-API-KEY':SERPER_API_KEY,'Content-Type':'application/json'},json={'q':query,'num':num,'gl':gl,'hl':hl},timeout=30)
        if r.status_code==200:
            _SERPER_FAILS['count'] = 0
            data=r.json(); results=[]
            for item in data.get('organic',[]) or []:
                results.append({'title':item.get('title',''),'url':item.get('link',''),'snippet':item.get('snippet',''),'source':'Google/Serper','query':query})
            return results
        last=f'{r.status_code} {r.text[:120]}'
    _SERPER_FAILS['count'] += 1
    raise RuntimeError(f'Serper search failed after {retries} attempts: {last}')


def bing_rss_search(query, num=10, mkt='en-CA', retries=2):
    """No-key fallback via Bing's RSS output (bypasses its JS bot-wall).

    The RSS endpoint intermittently serves cached results for an unrelated
    query, so validate that the results actually mention a query token and
    retry when they do not."""
    qtokens = {w for w in re.split(r"[^a-z0-9]+", query.lower()) if len(w) > 3}
    for _ in range(max(1, retries)):
        try:
            r = requests.get(
                'https://www.bing.com/search',
                params={'q': query, 'format': 'rss', 'count': min(max(num, 10), 20), 'setmkt': mkt, 'setlang': 'en'},
                headers={'User-Agent': UA},
                timeout=12,
            )
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'xml')
            results = []
            for item in soup.find_all('item'):
                link = item.find('link')
                title = item.find('title')
                desc = item.find('description')
                url = link.get_text(strip=True) if link else ''
                if not url.startswith('http'):
                    continue
                results.append({
                    'title': title.get_text(' ', strip=True) if title else '',
                    'url': url,
                    'snippet': desc.get_text(' ', strip=True) if desc else '',
                    'source': 'Bing RSS',
                    'query': query,
                })
            blob = ' '.join(f"{x['title']} {x['snippet']}" for x in results).lower()
            hits = sum(1 for t in qtokens if t in blob)
            if results and hits >= min(2, len(qtokens)):
                return results[:num]
        except Exception:
            pass
    return []


def _clean_ddg_url(url):
    parsed = urlparse(url)
    if parsed.netloc.endswith('duckduckgo.com') and parsed.path.startswith('/l/'):
        qs = dict(part.split('=', 1) for part in parsed.query.split('&') if '=' in part)
        if 'uddg' in qs:
            return unquote(qs['uddg'])
    return url


def duckduckgo_html_search(query, num=10, kl='ca-en'):
    r=requests.post(
        'https://html.duckduckgo.com/html/',
        headers={'User-Agent':UA,'Content-Type':'application/x-www-form-urlencoded'},
        data={'q':query,'kl':kl},
        timeout=12,
    )
    r.raise_for_status()
    soup=BeautifulSoup(r.text,'lxml')
    results=[]
    for item in soup.select('.result'):
        link=item.select_one('a.result__a')
        if not link or not link.get('href'):
            continue
        snippet_el=item.select_one('.result__snippet')
        results.append({
            'title':link.get_text(' ',strip=True),
            'url':_clean_ddg_url(link['href']),
            'snippet':snippet_el.get_text(' ',strip=True) if snippet_el else '',
            'source':'DuckDuckGo HTML',
            'query':query,
        })
        if len(results)>=num:
            break
    return results


def _clean_yahoo_url(url):
    parsed = urlparse(url)
    if parsed.netloc.endswith('search.yahoo.com'):
        qs = parse_qs(parsed.path.replace(";", "&") + "&" + parsed.query)
        target = qs.get("RU") or qs.get("/RU")
        if target:
            return unquote(target[0])
        match = re.search(r"/RU=([^/]+)", url)
        if match:
            return unquote(match.group(1))
    return url


def yahoo_search(query, num=10):
    r=requests.get(
        'https://search.yahoo.com/search',
        headers={'User-Agent':UA},
        params={'p':query},
        timeout=12,
    )
    r.raise_for_status()
    soup=BeautifulSoup(r.text,'lxml')
    results=[]
    for item in soup.select('.algo'):
        link=item.select_one('a[href]')
        if not link or not link.get('href'):
            continue
        url=_clean_yahoo_url(link['href'])
        if not url.startswith('http'):
            continue
        text=item.get_text(' ',strip=True)
        title=link.get_text(' ',strip=True) or text[:120]
        results.append({
            'title':title,
            'url':url,
            'snippet':text[:500],
            'source':'Yahoo HTML',
            'query':query,
        })
        if len(results)>=num:
            break
    return results


def _merge_results(results, new, seen):
    for item in new or []:
        url = item.get('url', '')
        if url and url not in seen:
            seen.add(url)
            results.append(item)
    return results


def serper_exhausted():
    """True when the Serper pool failed repeatedly and was disabled this run."""
    return bool(SERPER_API_KEY) and _SERPER_FAILS['count'] >= _SERPER_GIVE_UP


# Consecutive-failure counters for the keyless fallback engines. Some networks
# block DuckDuckGo/Yahoo outright; after 3 consecutive failures an engine is
# skipped for the rest of the run instead of costing its timeout per query.
_ENGINE_FAILS = {'bing': 0, 'yahoo': 0, 'ddg': 0}


def reset_search_state():
    """Reset provider counters for each API search run."""
    _SERPER_FAILS['count'] = 0
    for name in _ENGINE_FAILS:
        _ENGINE_FAILS[name] = 0


def _try_engine(name, fn, results, seen):
    if _ENGINE_FAILS[name] >= 3:
        return
    try:
        hits = fn()
    except Exception:
        hits = []
    if hits:
        _ENGINE_FAILS[name] = 0
        _merge_results(results, hits, seen)
    # Empty is valid for a niche query; it must not disable the engine for all
    # broader queries later in this run (or for later API requests).


def web_search(query, num=10, gl=None):
    """gl: optional Google geo ('us'/'ca') derived from the mandate location so
    e.g. a New York mandate searches google.com, not google.ca."""
    provider=(SEARCH_PROVIDER or 'auto').lower()
    geo = gl or 'ca'
    kl = 'us-en' if geo == 'us' else 'ca-en'
    mkt = 'en-US' if geo == 'us' else 'en-CA'
    if provider == 'serper':
        return serper_search(query,num=num,gl=geo)
    if provider == 'duckduckgo':
        return duckduckgo_html_search(query,num=num,kl=kl)
    if provider == 'bing':
        return bing_rss_search(query,num=num,mkt=mkt)

    # auto: Serper (when keyed) leads -- it is the only consistently reliable
    # engine. The keyless engines (Bing RSS first: it responds even where
    # DuckDuckGo/Yahoo are blocked) run ONLY when Serper produced nothing;
    # topping up partial result sets with them multiplied per-query latency
    # (each fallback can take 10-60s in timeouts) for marginal gain.
    results, seen = [], set()
    if SERPER_API_KEY:
        try:
            _merge_results(results, serper_search(query, num=num, gl=geo), seen)
        except Exception:
            pass
    if not results:
        _try_engine('bing', lambda: bing_rss_search(query, num=num, mkt=mkt), results, seen)
    if not results:
        _try_engine('yahoo', lambda: yahoo_search(query, num=num), results, seen)
    if not results:
        _try_engine('ddg', lambda: duckduckgo_html_search(query, num=num, kl=kl), results, seen)
    return results[:num]
