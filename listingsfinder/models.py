from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
@dataclass
class SearchCriteria:
    original_query:str; industry:str=''; location:str=''; price_min:Optional[float]=None; price_max:Optional[float]=None; revenue_min:Optional[float]=None; revenue_max:Optional[float]=None; keywords:str=''; exclude:str=''
@dataclass
class Listing:
    master_listing_id:str=''; listing_id:str=''; source:str=''; source_url:str=''; listing_title:str=''; company_name:str=''; industry:str=''; location:str=''; asking_price:str=''; revenue:str=''; cash_flow:str=''; ebitda:str=''; description:str=''; contact_name:str=''; contact_email:str=''; contact_phone:str=''; listing_date:str=''; scrape_date:str=''; status:str='New'; notes:str=''
    def to_dict(self): return asdict(self)
