#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
TARGETS=json.loads((ROOT/"price_targets.json").read_text(encoding="utf-8"))
OUT=ROOT/"prices.json"
BASE="https://www.sokmarket.com.tr/"
ALLOWED_HOSTS={"www.sokmarket.com.tr","sokmarket.com.tr"}
S=requests.Session()
S.headers.update({
 "User-Agent":"Mozilla/5.0 (compatible; AileSofrasiPriceVerifier/0.4.1; +https://fatihmehmetdemir-cyber.github.io/aile-sofrasi/)",
 "Accept-Language":"tr-TR,tr;q=0.9","Accept":"text/html,application/xhtml+xml"
})
MONEY_RX=re.compile(r"(?<!\d)(\d{1,4}(?:\.\d{3})*(?:,\d{2})|\d{1,4}(?:\.\d{2}))\s*₺")
PRODUCT_HREF_RX=re.compile(r"-p-\d+/?(?:$|\?)",re.I)

def now_iso():
 return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def parse_money(v):
 if isinstance(v,(int,float)): return float(v) if math.isfinite(float(v)) and float(v)>0 else None
 if v is None:return None
 s=re.sub(r"[^\d,.\-]","",str(v).strip())
 if not s:return None
 if "," in s and "." in s:s=s.replace(".","").replace(",",".")
 elif "," in s:s=s.replace(",",".")
 try:
  n=float(s);return n if math.isfinite(n) and n>0 else None
 except ValueError:return None

def norm(t):
 t=unicodedata.normalize("NFKD",str(t or "").casefold())
 t="".join(c for c in t if not unicodedata.combining(c))
 return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9çğıöşü\s]"," ",t)).strip()

def toks(t):return {x for x in norm(t).split() if len(x)>1}
def sim(a,b):
 A,B=toks(a),toks(b)
 if not A or not B:return 0
 hit=len(A&B);return .7*hit/len(B)+.3*hit/len(A)

def safe_url(raw):
 try:
  u=urlparse(urljoin(BASE,raw))
  return u.geturl() if u.scheme=="https" and u.netloc in ALLOWED_HOSTS else None
 except:return None

def fetch(url):
 r=S.get(url,timeout=18,allow_redirects=True);r.raise_for_status()
 if urlparse(r.url).netloc not in ALLOWED_HOSTS:raise RuntimeError("unexpected redirect")
 return r.text

def jsonld_products(html):
 soup=BeautifulSoup(html,"html.parser");out=[]
 def walk(x):
  if isinstance(x,list):
   for y in x:walk(y)
  elif isinstance(x,dict):
   typ=x.get("@type");types=typ if isinstance(typ,list) else [typ]
   if any(str(t).lower()=="product" for t in types):out.append(x)
   for k in ("@graph","itemListElement","item"):
    if k in x:walk(x[k])
 for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
  try:walk(json.loads(tag.get_text(strip=True)))
  except:pass
 return out

def links(html):
 soup=BeautifulSoup(html,"html.parser");seen=set();rows=[]
 for a in soup.find_all("a",href=True):
  u=safe_url(a["href"])
  if not u or not PRODUCT_HREF_RX.search(urlparse(u).path):continue
  title=" ".join(a.stripped_strings).strip()
  if not title:
   img=a.find("img",alt=True);title=str(img.get("alt","")).strip() if img else ""
  if u not in seen:seen.add(u);rows.append((u,title))
 return rows

def search(query_text):
 rows=[]
 for u in [f"{BASE}?s={quote(query_text)}",f"{BASE}arama?q={quote(query_text)}"]:
  try:html=fetch(u)
  except:continue
  rows.extend(links(html))
  for p in jsonld_products(html):
   pu=safe_url(str(p.get("url") or ""));pt=str(p.get("name") or "")
   if pu:rows.append((pu,pt))
  if rows:break
 seen=set();out=[]
 for u,t in rows:
  if u not in seen:seen.add(u);out.append((u,t))
 return out

def offer_price(product):
 offers=product.get("offers")
 offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
 vals=[]
 for o in offers:
  for k in ("price","lowPrice"):
   n=parse_money(o.get(k))
   if n:vals.append(n)
 return vals[0] if vals else None

def visible_prices(html):
 text=" ".join(BeautifulSoup(html,"html.parser").stripped_strings)
 vals=[]
 for m in MONEY_RX.finditer(text):
  n=parse_money(m.group(1))
  if n and 1<=n<=100000 and n not in vals:vals.append(n)
 return vals[:12]

def title_from(html):
 soup=BeautifulSoup(html,"html.parser")
 h=soup.find("h1")
 if h:return " ".join(h.stripped_strings)
 return soup.title.get_text(" ",strip=True).split("- Cepte Şok")[0].strip() if soup.title else ""

def package_info(title,req_unit,mode):
 m=re.search(r"(\d{1,3})\s*(?:['’]\s*)?(?:li|lü|lu|lı)\b",title,re.I)
 if m and req_unit=="adet":return float(m.group(1)),"adet"
 m=re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|kilogram|g|gr|gram|ml|l|lt|litre)\b",title,re.I)
 if m:
  n=parse_money(m.group(1));u=m.group(2).casefold()
  if u in {"kg","kilogram"}:return n*1000,"g"
  if u in {"g","gr","gram"}:return n,"g"
  if u in {"l","lt","litre"}:return n*1000,"ml"
  if u=="ml":return n,"ml"
 if mode=="weight" and re.search(r"\bkg\b",title,re.I):return 1000.0,"g"
 if req_unit=="demet":return 1.0,"demet"
 return 1.0,req_unit

def resolve(t):
 rows=search(t["query"])
 scored=sorted(((sim(title,t["query"]),url,title) for url,title in rows[:30]),reverse=True)
 if not scored or scored[0][0]<.28:return None,"eşleşen ürün bulunamadı"
 _,url,hint=scored[0]
 html=fetch(url);title=title_from(html) or hint or t["query"]
 products=jsonld_products(html);structured=None
 if products:
  products.sort(key=lambda p:sim(str(p.get("name") or ""),t["query"]),reverse=True)
  structured=offer_price(products[0])
 visible=visible_prices(html)
 current=structured or (visible[-1] if visible else None)
 if not current:return None,"fiyat okunamadı"
 regular=max([current]+visible) if visible else current
 amount,unit=package_info(title,t["unit"],t["pricingMode"])
 return {
  "ingredient":t["ingredient"],"unit":t["unit"],"provider":"ŞOK / Cepte ŞOK","retailer":"ŞOK",
  "productName":title,"currentPrice":round(float(current),2),"regularPrice":round(float(regular),2),
  "price":round(float(current),2),"packageAmount":amount,"packageUnit":unit,
  "basisAmount":amount,"basisUnit":unit,"pricingMode":t["pricingMode"],"status":"live",
  "observedAt":now_iso(),"sourceUrl":url,"locationScope":"cepte-sok-online",
  "note":"Cepte ŞOK çevrimiçi fiyatı; stok, fiyat ve kampanya teslimat bölgesine göre değişebilir."
 },None

def main():
 old={}
 if OUT.exists():
  try:
   d=json.loads(OUT.read_text(encoding="utf-8"))
   old={(q.get("ingredient"),q.get("unit")):q for q in d.get("quotes",[])}
  except:pass
 quotes=[];failed=[]
 for idx,t in enumerate(TARGETS,1):
  try:
   q,err=resolve(t)
   if q:
    quotes.append(q);print(f"[{idx}/{len(TARGETS)}] OK {t['ingredient']}: {q['currentPrice']} TL — {q['productName']}")
   else:
    prev=old.get((t["ingredient"],t["unit"]))
    if prev:quotes.append(prev)
    failed.append({"ingredient":t["ingredient"],"unit":t["unit"],"reason":err})
    print(f"[{idx}/{len(TARGETS)}] SKIP {t['ingredient']}: {err}")
  except Exception as exc:
   prev=old.get((t["ingredient"],t["unit"]))
   if prev:quotes.append(prev)
   failed.append({"ingredient":t["ingredient"],"unit":t["unit"],"reason":str(exc)[:180]})
   print(f"[{idx}/{len(TARGETS)}] ERR {t['ingredient']}: {exc}")
  time.sleep(1.4)
 OUT.write_text(json.dumps({
  "schemaVersion":1,"retailer":"ŞOK / Cepte ŞOK","generatedAt":now_iso(),
  "locationScope":"cepte-sok-online","quotes":quotes,"failed":failed,"source":BASE,
  "policy":"Only successfully parsed products receive a new observedAt; failed products retain their old timestamp."
 },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"prices.json: {len(quotes)} kayıt, {len(failed)} başarısız/eşleşmeyen")

if __name__=="__main__":main()
