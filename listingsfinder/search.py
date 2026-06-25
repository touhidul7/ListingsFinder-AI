import re
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .config import SEARCH_PROVIDER, SERPER_API_KEY

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'


def serper_search(query, num=10, gl='ca', hl='en'):
    if not SERPER_API_KEY: return []
    r=requests.post('https://google.serper.dev/search',headers={'X-API-KEY':SERPER_API_KEY,'Content-Type':'application/json'},json={'q':query,'num':num,'gl':gl,'hl':hl},timeout=30)
    r.raise_for_status(); data=r.json(); results=[]
    for item in data.get('organic',[]) or []:
        results.append({'title':item.get('title',''),'url':item.get('link',''),'snippet':item.get('snippet',''),'source':'Google/Serper','query':query})
    return results


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
        timeout=25,
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
        timeout=25,
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


def web_search(query, num=10):
    provider=(SEARCH_PROVIDER or 'auto').lower()
    if provider == 'serper':
        return serper_search(query,num=num)
    if provider == 'duckduckgo':
        return duckduckgo_html_search(query,num=num)

    try:
        results=duckduckgo_html_search(query,num=num)
        if len(results) >= max(1, min(num, 3)):
            return results
    except Exception:
        results=[]
    try:
        yahoo_results=yahoo_search(query,num=num)
        if yahoo_results:
            return yahoo_results
    except Exception:
        pass
    if SERPER_API_KEY:
        try:
            return serper_search(query,num=num)
        except Exception:
            return results
    return results
