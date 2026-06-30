import re, hashlib, requests
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from .config import SCRAPEDO_TOKEN
from .models import Listing, now_iso
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'
def fetch_url(url, use_fallback=True):
    try:
        r=requests.get(url,headers={'User-Agent':UA},timeout=12)
        if r.status_code<400 and len(r.text)>200: return r.text,'direct'
    except Exception: pass
    if use_fallback and SCRAPEDO_TOKEN:
        try:
            r=requests.get(f'https://tmcp.vercel.app/api/scrapedo?token={SCRAPEDO_TOKEN}&url={quote_plus(url)}&render=false',timeout=30)
            if r.status_code<400: return r.text,'scrape.do'
        except Exception:
            pass
    return '','failed'
def first(text, pats):
    for p in pats:
        m=re.search(p,text or '',re.I)
        if m: return m.group(0)[:150]
    return ''

SALE_TERMS = (
    "for sale",
    "business for sale",
    "company for sale",
    "business opportunity",
    "acquisition opportunity",
    "asking price",
    "view details",
    "more details",
    "listing",
    "listings",
)

DIRECTORY_TERMS = (
    "/search/",
    "/browse",
    "/marketplace",
    "/listings/",
    "businesses-for-sale-and-investment",
    "/result",
    "category",
    "directory",
    "browse ",
    "search ",
    "commercial listings",
    "buy & sell",
    "currently available",
    "businesses for sale and investment",
)

NON_LISTING_TERMS = (
    "job",
    "jobs",
    "career",
    "careers",
    "linkedin.com/company",
    "college of",
    "ocpinfo.com",
    "canlii.org",
    "reddit.com",
    "linkedin.com",
    "facebook.com/groups",
    "franchise opportunities",
    "blog",
    "news",
    "article",
    "privacy policy",
    "terms of use",
)

NON_LISTING_PATH_PARTS = (
    "/blog",
    "/news",
    "/article",
    "/contact",
    "/login",
    "/sign",
    "/privacy",
    "/terms",
    "shortlist",
    "alert",
    "save=",
)



def _looks_like_listing_path(path):
    path = (path or "").lower()
    return bool(
        re.search(r"/(business|business-opportunity|listing|listings|opportunity|opportunities)/", path)
        or re.search(r"/[a-z0-9-]+-for-sale(?:[/.]|$)", path)
        or re.search(r"/[a-z0-9-]+-[a-z0-9]+/$", path)
    )


def _looks_like_next_page(text, href):
    label = (text or "").strip().lower()
    href_low = (href or "").lower()
    return (
        label in ("next", "next page", ">", ">>")
        or "next" in label
        or re.search(r"[?&](page|p)=\d+", href_low)
        or re.search(r"/(page|p)/\d+", href_low)
    )
def title_from_url(url):
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    slug = re.sub(r"\.(aspx|html?|php)$", "", slug, flags=re.I)
    return re.sub(r"[-_]+", " ", slug).strip().title()


def _industry_tokens(industry):
    return {w for w in re.split(r"[^a-z0-9]+", (industry or "").lower()) if len(w) > 2}


def _location_tokens(location):
    normalized = re.sub(r"\s+", " ", (location or "").strip().lower())
    tokens = {w for w in re.split(r"[^a-z0-9]+", normalized) if len(w) > 2}
    aliases = {
        "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca",
        "colorado": "co", "connecticut": "ct", "delaware": "de", "florida": "fl", "georgia": "ga",
        "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia",
        "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
        "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
        "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv", "hampshire": "nh",
        "ohio": "oh", "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa", "rhode": "ri",
        "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va",
        "washington": "wa", "wisconsin": "wi", "wyoming": "wy",
        "ontario": "on", "quebec": "qc", "alberta": "ab", "manitoba": "mb",
        "saskatchewan": "sk",
        "new york": "ny", "new jersey": "nj", "new mexico": "nm", "north carolina": "nc",
        "south carolina": "sc", "north dakota": "nd", "south dakota": "sd", "new hampshire": "nh",
        "rhode island": "ri", "west virginia": "wv", "british columbia": "bc", "nova scotia": "ns",
        "new brunswick": "nb", "newfoundland": "nl", "newfoundland and labrador": "nl",
        "prince edward island": "pe",
    }
    for name, alias in aliases.items():
        if name == normalized or name in normalized:
            tokens.add(alias)
    return tokens


def is_directory_result(result):
    haystack = " ".join([result.get("title", ""), result.get("url", ""), result.get("snippet", "")]).lower()
    url = (result.get("url", "") or "").lower()
    url_path = urlparse(result.get("url", "")).path.lower()
    title = (result.get("title", "") or "").lower()
    # Search-result pages (e.g. ?q=, ?keyword=, ?search=) are listings indexes,
    # not a single listing -- treat as a directory so they get expanded.
    if re.search(r"[?&](q|query|keyword|keywords|search|term|s)=", url):
        return True
    if re.search(r"\b[a-z0-9 &'-]+s\s+for sale(?:\s+in\b|$)", title):
        return True
    if url_path.rstrip("/") in ("/commercial", "/business-for-sale", "/marketplace"):
        return True
    if url_path in ("", "/") and any(term in haystack for term in ("marketplace", "buy & sell", "for sale canada")):
        return True
    return any(term in haystack for term in DIRECTORY_TERMS)


def is_relevant_result(result, industry="", location=""):
    haystack = " ".join([result.get("title", ""), result.get("url", ""), result.get("snippet", "")]).lower()
    path = urlparse(result.get("url", "")).path.lower().rstrip("/")
    title = (result.get("title", "") or "").strip().lower()
    if title in ("skip to content", "more details", "view details", "contact seller", "save", "spinner") or title.startswith("all results"):
        return False
    if any(part in path for part in NON_LISTING_PATH_PARTS):
        return False
    # Hard block for editorial/blog content and dated article URLs. Unlike the
    # NON_LISTING_TERMS check below, this cannot be bypassed by a stray price,
    # because blog posts about businesses for sale routinely quote prices.
    if re.search(r"/(blog|news|press|insights?|resources?|articles?|stories|guides?)(/|$)", path):
        return False
    if re.search(r"/(19|20)\d\d/\d{1,2}/", path):
        return False
    if re.search(r"/(businesses-for-sale|business-for-sale|companies-for-sale|listings|search|category|browse)$", path):
        return False
    industry_words = _industry_tokens(industry)
    title_url = " ".join([result.get("title", ""), result.get("url", "")]).lower()
    if industry_words and not any(word in title_url or word in haystack for word in industry_words):
        return False
    has_industry = not industry_words or any(word in haystack for word in industry_words)
    location_words = _location_tokens(location)
    has_location = not location_words or any(word in haystack for word in location_words)
    if not has_location:
        return False
    has_sale = any(term in haystack for term in SALE_TERMS) or bool(re.search(r"\$[0-9][0-9,.]+", haystack))
    if any(term in haystack for term in ("linkedin.com", "facebook.com/groups")):
        return False
    if any(term in haystack for term in NON_LISTING_TERMS) and not ("for sale" in haystack and re.search(r"\$[0-9][0-9,]{2,}|asking price|cash flow|ebitda|annual revenue", haystack)):
        return False
    return bool(has_industry and has_sale)


def _candidate_from_anchor(anchor, page_url, result):
    href = urljoin(page_url, anchor["href"])
    parsed = urlparse(href)
    clean_url = href.split("#")[0]
    text = " ".join(anchor.get_text(" ", strip=True).split())
    parent_text = " ".join((anchor.parent.get_text(" ", strip=True) if anchor.parent else text).split())
    return {
        "title": title_from_url(clean_url) if text.lower().startswith("more detail") else (text or title_from_url(clean_url) or result.get("title", "")),
        "url": clean_url,
        "snippet": parent_text[:700] or result.get("snippet", ""),
        "source": f"{result.get('source', 'Google/Serper')} expanded",
        "query": result.get("query", ""),
        "path": parsed.path.lower(),
        "domain": parsed.netloc.replace("www.", ""),
    }


def discover_listing_links(result, industry="", location="", max_links=25, max_pages=4):
    base_url = result.get("url", "")
    base_domain = urlparse(base_url).netloc.replace("www.", "")
    pages = [base_url]
    visited_pages = set()
    found = []
    seen_urls = set()

    while pages and len(visited_pages) < max_pages and len(found) < max_links:
        page_url = pages.pop(0)
        if page_url in visited_pages:
            continue
        visited_pages.add(page_url)
        html, method = fetch_url(page_url, use_fallback=False)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for anchor in soup.find_all("a", href=True):
            candidate = _candidate_from_anchor(anchor, page_url, result)
            if candidate["domain"] != base_domain:
                continue
            if candidate["path"] in ("", "/"):
                continue
            url = candidate["url"]
            label = anchor.get_text(" ", strip=True)
            if _looks_like_next_page(label, anchor.get("href", "")) and url not in visited_pages and url not in pages:
                pages.append(url)
                continue
            if url in seen_urls:
                continue
            if any(skip in candidate["path"] for skip in NON_LISTING_PATH_PARTS):
                continue
            if is_directory_result(candidate) and not _looks_like_listing_path(candidate["path"]):
                continue
            if is_relevant_result(candidate, industry, location):
                seen_urls.add(url)
                found.append(candidate)
                if len(found) >= max_links:
                    break
    return found


def expand_directory_results(results, industry="", location="", max_links_per_page=25, max_directory_pages=10):
    expanded = []
    seen = set()
    directory_pages = 0
    for result in results:
        is_directory = is_directory_result(result)
        children = []
        if is_directory and directory_pages < max_directory_pages:
            directory_pages += 1
            children = discover_listing_links(result, industry, location, max_links=max_links_per_page)
        candidates = children if children else ([] if is_directory else [result])
        for candidate in candidates:
            url = candidate.get("url", "")
            if url and url not in seen and is_relevant_result(candidate, industry, location):
                seen.add(url)
                expanded.append(candidate)
    return expanded

def is_listing_page(listing, industry="", location=""):
    candidate = {
        "title": listing.listing_title,
        "url": listing.source_url,
        "snippet": listing.description,
        "source": listing.source,
    }
    return (not is_directory_result(candidate)) and is_relevant_result(candidate, industry, location)
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
