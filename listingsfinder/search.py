import requests
from .config import SERPER_API_KEY
def serper_search(query, num=10, gl='ca', hl='en'):
    if not SERPER_API_KEY: return []
    r=requests.post('https://google.serper.dev/search',headers={'X-API-KEY':SERPER_API_KEY,'Content-Type':'application/json'},json={'q':query,'num':num,'gl':gl,'hl':hl},timeout=30)
    r.raise_for_status(); data=r.json(); results=[]
    for item in data.get('organic',[]) or []:
        results.append({'title':item.get('title',''),'url':item.get('link',''),'snippet':item.get('snippet',''),'source':'Google/Serper','query':query})
    return results
