import re, hashlib, requests
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from .config import SCRAPEDO_TOKEN
from .models import Listing, now_iso
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'
def fetch_url(url):
    try:
        r=requests.get(url,headers={'User-Agent':UA},timeout=20)
        if r.status_code<400 and len(r.text)>200: return r.text,'direct'
    except Exception: pass
    if SCRAPEDO_TOKEN:
        r=requests.get(f'https://api.scrape.do?token={SCRAPEDO_TOKEN}&url={quote_plus(url)}&render=false',timeout=45)
        if r.status_code<400: return r.text,'scrape.do'
    return '','failed'
def first(text, pats):
    for p in pats:
        m=re.search(p,text or '',re.I)
        if m: return m.group(0)[:150]
    return ''
def scrape_result(result, industry='', location=''):
    html,method=fetch_url(result['url']); soup=BeautifulSoup(html or '', 'lxml')
    title=(soup.find('title').get_text(' ',strip=True) if soup.find('title') else result.get('title',''))[:300]
    meta=soup.find('meta',attrs={'name':'description'}) or soup.find('meta',attrs={'property':'og:description'})
    desc=(meta.get('content','') if meta else '') or result.get('snippet','')
    text=soup.get_text(' ',strip=True)[:8000]
    if not desc: desc=text[:500]
    url=result['url']; domain=urlparse(url).netloc.replace('www.',''); lid=hashlib.sha1(url.encode()).hexdigest()[:12].upper()
    l=Listing(listing_id=f'SRC-{lid}',source=domain,source_url=url,listing_title=title,industry=industry,location=location,asking_price=first(text,[r'(?:asking price|price)[:\s]*\$[0-9,]+(?:\.?[0-9]+)?\s*(?:M|K|million)?',r'\$[0-9][0-9,]+(?:\.?[0-9]+)?\s*(?:M|K|million)?']),revenue=first(text,[r'(?:revenue|sales)[:\s]*\$[0-9,]+(?:\.?[0-9]+)?\s*(?:M|K|million)?']),cash_flow=first(text,[r'(?:cash flow|sde)[:\s]*\$[0-9,]+(?:\.?[0-9]+)?\s*(?:M|K|million)?']),ebitda=first(text,[r'EBITDA[:\s]*\$[0-9,]+(?:\.?[0-9]+)?\s*(?:M|K|million)?']),description=desc[:1000],contact_email=first(text,[r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}']),contact_phone=first(text,[r'(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}']),scrape_date=now_iso(),notes=f'fetch_method={method}; query={result.get("query","")}')
    return l
