#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
if not (ROOT / "price_targets.json").exists():
    ROOT = ROOT.parent

TARGETS = json.loads((ROOT / "price_targets.json").read_text(encoding="utf-8"))
OUT = ROOT / "prices.json"

BASE = "https://www.sokmarket.com.tr/"
ALLOWED_HOSTS = {"www.sokmarket.com.tr", "sokmarket.com.tr"}
S = requests.Session()
S.headers.update({
    "User-Agent":"Mozilla/5.0 (compatible; AileSofrasiPriceVerifier/0.4.2; +https://fatihmehmetdemir-cyber.github.io/aile-sofrasi/)",
    "Accept-Language":"tr-TR,tr;q=0.9",
    "Accept":"text/html,application/xhtml+xml"
})
MONEY_RX = re.compile(r"(?<!\d)(\d{1,4}(?:\.\d{3})*(?:,\d{2})|\d{1,4}(?:\.\d{2}))\s*₺")
PRODUCT_HREF_RX = re.compile(r"-p-\d+/?(?:$|\?)", re.I)
STOP = {
    "mis","tam","yagli","yağlı","kg","kilogram","g","gr","gram","ml","l","lt","litre",
    "paket","adet","1","2","3","4","5","6","10","15","20","100","120","180","200",
    "250","300","350","400","450","500","600","700","750","900","1000","1500","2000","3000"
}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def parse_money(v):
    if isinstance(v,(int,float)):
        n=float(v); return n if math.isfinite(n) and n>0 else None
    if v is None: return None
    s=re.sub(r"[^\d,.\-]","",str(v).strip())
    if not s: return None
    if "," in s and "." in s: s=s.replace(".","").replace(",",".")
    elif "," in s: s=s.replace(",",".")
    try:
        n=float(s); return n if math.isfinite(n) and n>0 else None
    except ValueError:
        return None

def norm(t):
    t=unicodedata.normalize("NFKD",str(t or "").casefold())
    t="".join(c for c in t if not unicodedata.combining(c))
    t=re.sub(r"[^a-z0-9çğıöşü\s]"," ",t)
    return re.sub(r"\s+"," ",t).strip()

def toks(t):
    return [x for x in norm(t).split() if x]

def safe_url(raw):
    try:
        u=urlparse(urljoin(BASE,raw))
        return u.geturl() if u.scheme=="https" and u.netloc in ALLOWED_HOSTS else None
    except Exception:
        return None

def fetch(url):
    r=S.get(url,timeout=18,allow_redirects=True); r.raise_for_status()
    if urlparse(r.url).netloc not in ALLOWED_HOSTS:
        raise RuntimeError("unexpected redirect")
    return r.text

def jsonld_products(html):
    soup=BeautifulSoup(html,"html.parser"); out=[]
    def walk(x):
        if isinstance(x,list):
            for y in x: walk(y)
        elif isinstance(x,dict):
            typ=x.get("@type"); types=typ if isinstance(typ,list) else [typ]
            if any(str(t).lower()=="product" for t in types): out.append(x)
            for k in ("@graph","itemListElement","item"):
                if k in x: walk(x[k])
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try: walk(json.loads(tag.get_text(strip=True)))
        except Exception: pass
    return out

def product_links(html):
    soup=BeautifulSoup(html,"html.parser"); seen=set(); rows=[]
    for a in soup.find_all("a",href=True):
        u=safe_url(a["href"])
        if not u or not PRODUCT_HREF_RX.search(urlparse(u).path): continue
        title=" ".join(a.stripped_strings).strip()
        if not title:
            img=a.find("img",alt=True); title=str(img.get("alt","")).strip() if img else ""
        if u not in seen:
            seen.add(u); rows.append((u,title))
    return rows

def search(query_text):
    rows=[]
    for u in [f"{BASE}?s={quote(query_text)}",f"{BASE}arama?q={quote(query_text)}"]:
        try: html=fetch(u)
        except Exception: continue
        rows.extend(product_links(html))
        for p in jsonld_products(html):
            pu=safe_url(str(p.get("url") or "")); pt=str(p.get("name") or "")
            if pu: rows.append((pu,pt))
        if rows: break
    seen=set(); out=[]
    for u,t in rows:
        if u not in seen:
            seen.add(u); out.append((u,t))
    return out

def title_from(html):
    soup=BeautifulSoup(html,"html.parser")
    h=soup.find("h1")
    if h: return " ".join(h.stripped_strings)
    return soup.title.get_text(" ",strip=True).split("- Cepte Şok")[0].strip() if soup.title else ""

def package_info(title, requested_unit, mode):
    m=re.search(r"(\d{1,3})\s*(?:['’]\s*)?(?:li|lü|lu|lı)\b",title,re.I)
    if m and requested_unit=="adet":
        return float(m.group(1)),"adet"
    m=re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|kilogram|g|gr|gram|ml|l|lt|litre)\b",title,re.I)
    if m:
        n=parse_money(m.group(1)); u=norm(m.group(2))
        if u in {"kg","kilogram"}: return n*1000,"g"
        if u in {"g","gr","gram"}: return n,"g"
        if u in {"l","lt","litre"}: return n*1000,"ml"
        if u=="ml": return n,"ml"
    if mode=="weight" and re.search(r"\bkg\b",title,re.I):
        return 1000.0,"g"
    return None,None

def offer_price(product):
    offers=product.get("offers")
    offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
    vals=[]
    for o in offers:
        for k in ("price","lowPrice"):
            n=parse_money(o.get(k))
            if n: vals.append(n)
    return min(vals) if vals else None

def visible_prices(html):
    text=" ".join(BeautifulSoup(html,"html.parser").stripped_strings)
    vals=[]
    for m in MONEY_RX.finditer(text):
        n=parse_money(m.group(1))
        if n and 1<=n<=100000 and n not in vals: vals.append(n)
    return vals[:12]

def core_tokens(target):
    if target.get("requiredAll"):
        return [norm(x) for x in target["requiredAll"]]
    return [x for x in toks(target.get("query","")) if x not in STOP and not x.isdigit()]

def unit_compatible(target,pkg_unit):
    req=target.get("expectedUnitFamily")
    if req=="mass": return pkg_unit=="g"
    if req=="volume": return pkg_unit=="ml"
    if req=="adet": return pkg_unit=="adet"
    if req=="demet": return pkg_unit=="demet"
    return True

def semantic_ok(target,title):
    nt=set(toks(title))
    for bad in target.get("forbidden",[]):
        if norm(bad) in nt: return False,f"yasak kelime: {bad}"
    must_all=[norm(x) for x in target.get("requiredAll",[])]
    if must_all and not all(x in nt for x in must_all):
        return False,"zorunlu ürün kelimesi eksik"
    must_any=[norm(x) for x in target.get("requiredAny",[])]
    if must_any and not any(x in nt for x in must_any):
        return False,"beklenen ürün ailesi bulunamadı"
    cores=core_tokens(target)
    if not cores: return False,"anlamlı sorgu kelimesi yok"
    hit=sum(1 for x in cores if x in nt)
    coverage=hit/len(cores)
    if coverage<0.67:
        return False,f"ürün adı eşleşmesi zayıf ({coverage:.0%})"
    return True,None

def resolve(target):
    rows=search(target["query"])
    if not rows: return None,"arama sonucu yok"
    rejected=[]
    for url,hint in rows[:12]:
        try:
            if hint:
                ok,reason=semantic_ok(target,hint)
                if not ok:
                    rejected.append(reason); continue
            html=fetch(url)
            title=title_from(html) or hint
            ok,reason=semantic_ok(target,title)
            if not ok:
                rejected.append(reason); continue
            amount,pkg_unit=package_info(title,target["unit"],target["pricingMode"])
            if not amount or not pkg_unit:
                rejected.append("paket miktarı okunamadı"); continue
            if not unit_compatible(target,pkg_unit):
                rejected.append(f"birim uyumsuz: {pkg_unit}"); continue
            products=jsonld_products(html); structured=None
            if products:
                for p in products:
                    pname=str(p.get("name") or "")
                    ok2,_=semantic_ok(target,pname or title)
                    if ok2:
                        structured=offer_price(p)
                        if structured: break
            visible=visible_prices(html)
            current=structured or (min(visible) if visible else None)
            if not current:
                rejected.append("fiyat okunamadı"); continue
            regular=max([current]+visible) if visible else current
            return {
                "ingredient":target["ingredient"],"unit":target["unit"],
                "provider":"ŞOK / Cepte ŞOK","retailer":"ŞOK","productName":title,
                "currentPrice":round(float(current),2),"regularPrice":round(float(regular),2),
                "price":round(float(current),2),"packageAmount":amount,"packageUnit":pkg_unit,
                "basisAmount":amount,"basisUnit":pkg_unit,"pricingMode":target["pricingMode"],
                "status":"live","observedAt":now_iso(),"sourceUrl":url,
                "locationScope":"cepte-sok-online","matchPolicy":"strict-v0.4.2",
                "note":"Cepte ŞOK çevrimiçi fiyatı; sıkı ürün adı ve paket birimi doğrulamasından geçti."
            },None
        except Exception as exc:
            rejected.append(str(exc)[:80])
    return None,f"güvenli eşleşme bulunamadı: {rejected[-1] if rejected else 'uygun ürün yok'}"

def main():
    old={}
    if OUT.exists():
        try:
            d=json.loads(OUT.read_text(encoding="utf-8"))
            old={(q.get("ingredient"),q.get("unit")):q for q in d.get("quotes",[])}
        except Exception: pass
    quotes=[]; failed=[]
    for idx,target in enumerate(TARGETS,1):
        try:
            q,err=resolve(target)
            if q:
                quotes.append(q)
                print(f"[{idx}/{len(TARGETS)}] OK {target['ingredient']}: {q['currentPrice']} TL — {q['productName']}")
            else:
                prev=old.get((target["ingredient"],target["unit"]))
                if prev: quotes.append(prev)
                failed.append({"ingredient":target["ingredient"],"unit":target["unit"],"reason":err})
                print(f"[{idx}/{len(TARGETS)}] SKIP {target['ingredient']}: {err}")
        except Exception as exc:
            prev=old.get((target["ingredient"],target["unit"]))
            if prev: quotes.append(prev)
            failed.append({"ingredient":target["ingredient"],"unit":target["unit"],"reason":str(exc)[:180]})
            print(f"[{idx}/{len(TARGETS)}] ERR {target['ingredient']}: {exc}")
        time.sleep(1.4)
    OUT.write_text(json.dumps({
        "schemaVersion":2,"retailer":"ŞOK / Cepte ŞOK","generatedAt":now_iso(),
        "locationScope":"cepte-sok-online","quotes":quotes,"failed":failed,"source":BASE,
        "matchPolicy":"strict-v0.4.2",
        "policy":"Yanlış eşleşme riskinde fiyat yazılmaz; eski kayıt korunursa observedAt yenilenmez."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
