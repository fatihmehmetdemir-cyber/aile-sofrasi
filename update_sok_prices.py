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
    "User-Agent":"Mozilla/5.0 (compatible; AileSofrasiPriceVerifier/0.4.3; +https://fatihmehmetdemir-cyber.github.io/aile-sofrasi/)",
    "Accept-Language":"tr-TR,tr;q=0.9",
    "Accept":"text/html,application/xhtml+xml"
})

MONEY_RX = re.compile(r"(?<!\d)(\d{1,4}(?:\.\d{3})*(?:,\d{2})|\d{1,4}(?:\.\d{2}))\s*₺")
PRODUCT_HREF_RX = re.compile(r"-p-\d+/?(?:$|\?)", re.I)
CACHE = {}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def parse_money(v):
    if isinstance(v,(int,float)):
        n=float(v); return n if math.isfinite(n) and n>0 else None
    if v is None: return None
    s=re.sub(r"[^\d,.\-]","",str(v).strip())
    if not s: return None
    if "," in s and "." in s:
        # Turkish money: 1.250,00
        if s.rfind(",") > s.rfind("."):
            s=s.replace(".","").replace(",",".")
        else:
            s=s.replace(",","")
    elif "," in s:
        s=s.replace(",",".")
    try:
        n=float(s); return n if math.isfinite(n) and n>0 else None
    except ValueError:
        return None

def norm(t):
    t=unicodedata.normalize("NFKD",str(t or "").casefold())
    t="".join(c for c in t if not unicodedata.combining(c))
    t=t.replace("ı","i")
    t=re.sub(r"[^a-z0-9çğıöşü\s]"," ",t)
    return re.sub(r"\s+"," ",t).strip()

def toks(t):
    return [x for x in norm(t).split() if x]

def has_term(words, term):
    term=norm(term)
    if term in words:
        return True
    # Turkish noun/adjective suffixes: reçel->reçeli, salça->salçası, ceviz->cevizi.
    if len(term)>=5:
        return any(w.startswith(term) for w in words)
    # "bal" özel durumu: "balı" kabul, "balık/ballı" reddet.
    if term=="bal":
        return "bali" in words
    return False

def safe_url(raw):
    try:
        u=urlparse(urljoin(BASE,raw))
        return u.geturl() if u.scheme=="https" and u.netloc in ALLOWED_HOSTS else None
    except Exception:
        return None

def fetch(url):
    if url in CACHE:
        return CACHE[url]
    r=S.get(url,timeout=20,allow_redirects=True)
    r.raise_for_status()
    if urlparse(r.url).netloc not in ALLOWED_HOSTS:
        raise RuntimeError("unexpected redirect")
    CACHE[url]=r.text
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

def cleaned_anchor_title(a):
    title=" ".join(a.stripped_strings).strip()
    if not title:
        img=a.find("img",alt=True)
        title=str(img.get("alt","")).strip() if img else ""
    # Remove trailing visible price / win para text from card.
    title=re.sub(r"\s*\d[\d\.,]*\s*₺.*$","",title).strip()
    title=re.sub(r"\+\s*\d+\s*win\s*para.*$","",title,flags=re.I).strip()
    return title

def product_links(html):
    soup=BeautifulSoup(html,"html.parser"); seen=set(); rows=[]
    for a in soup.find_all("a",href=True):
        u=safe_url(a["href"])
        if not u or not PRODUCT_HREF_RX.search(urlparse(u).path): continue
        title=cleaned_anchor_title(a)
        if u not in seen:
            seen.add(u); rows.append((u,title))
    return rows

def search_page(query_text):
    rows=[]
    for u in [f"{BASE}?s={quote(query_text)}",f"{BASE}arama?q={quote(query_text)}"]:
        try: html=fetch(u)
        except Exception: continue
        rows.extend(product_links(html))
        for p in jsonld_products(html):
            pu=safe_url(str(p.get("url") or "")); pt=str(p.get("name") or "")
            if pu: rows.append((pu,pt))
        if rows: break
    return dedupe(rows)

def catalog_candidates(urls):
    rows=[]
    for u in urls or []:
        try:
            rows.extend(product_links(fetch(u)))
        except Exception as exc:
            print(f"catalog warning {u}: {exc}")
    return dedupe(rows)

def dedupe(rows):
    seen=set(); out=[]
    for u,t in rows:
        if not u or u in seen: continue
        seen.add(u); out.append((u,t or ""))
    return out

def title_from(html):
    soup=BeautifulSoup(html,"html.parser")
    h=soup.find("h1")
    if h: return " ".join(h.stripped_strings)
    return soup.title.get_text(" ",strip=True).split("- Cepte Şok")[0].strip() if soup.title else ""

def header_prices(html,title):
    soup=BeautifulSoup(html,"html.parser")
    text=" ".join(soup.stripped_strings)
    nt=title.strip()
    start=text.find(nt) if nt else -1
    if start < 0: start=0
    segment=text[start:start+700]
    end_candidates=[x for x in (segment.find("Ürün Bilgisi"),segment.find("Sepete Ekle"),segment.find("Gelince Haber Ver")) if x>0]
    if end_candidates:
        # Include the price area immediately before first button/section.
        segment=segment[:max(end_candidates)]
    vals=[]
    for m in MONEY_RX.finditer(segment):
        n=parse_money(m.group(1))
        if n and 0.5<=n<=100000 and n not in vals:
            vals.append(n)
    return vals[:4]

def offer_prices(product):
    offers=product.get("offers")
    offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
    vals=[]
    for o in offers:
        for k in ("price","lowPrice","highPrice"):
            n=parse_money(o.get(k))
            if n and n not in vals: vals.append(n)
    return vals

def package_info(title, target):
    requested_unit=target["unit"]; mode=target["pricingMode"]
    m=re.search(r"(\d{1,3})\s*(?:['’]\s*)?(?:li|lü|lu|lı)\b",title,re.I)
    if m and requested_unit=="adet":
        return float(m.group(1)),"adet",False

    m=re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|kilogram|g|gr|gram|ml|l|lt|litre)\b",title,re.I)
    if m:
        n=parse_money(m.group(1)); u=norm(m.group(2))
        if u in {"kg","kilogram"}: return n*1000,"g",False
        if u in {"g","gr","gram"}: return n,"g",False
        if u in {"l","lt","litre"}: return n*1000,"ml",False
        if u=="ml": return n,"ml",False

    if mode=="weight" and re.search(r"\bkg\b",title,re.I):
        return 1000.0,"g",False

    if target.get("implicitOneTargetUnit"):
        return 1.0,requested_unit,False

    return None,None,False

def semantic_ok(target,title):
    words=set(toks(title))
    for bad in target.get("forbidden",[]):
        if has_term(words,bad):
            return False,f"yasak kelime: {bad}"

    groups=target.get("matchGroups") or []
    for group in groups:
        ng=[norm(x) for x in group]
        if not any(has_term(words,x) for x in ng):
            return False,f"eşleşme grubu eksik: {'/'.join(group)}"

    must_all=[norm(x) for x in target.get("requiredAll",[])]
    if must_all and not all(has_term(words,x) for x in must_all):
        return False,"zorunlu ürün kelimesi eksik"

    must_any=[norm(x) for x in target.get("requiredAny",[])]
    if must_any and not any(has_term(words,x) for x in must_any):
        return False,"beklenen ürün ailesi bulunamadı"

    # If explicit groups exist, they are the primary strict gate.
    if groups:
        return True,None

    q=[x for x in toks(target.get("query","")) if len(x)>2 and not x.isdigit()]
    if not q:
        return False,"anlamlı sorgu kelimesi yok"
    hit=sum(1 for x in q if has_term(words,x))
    if hit/max(1,len(q))<0.60:
        return False,"ürün adı eşleşmesi zayıf"
    return True,None

def score_candidate(target,title):
    words=set(toks(title))
    score=0
    for group in target.get("matchGroups",[]):
        if any(has_term(words,x) for x in group): score+=20
    for x in target.get("preferredAny",[]):
        if has_term(words,x): score+=5
    # Prefer package sizes around 500g-1500g and avoid huge foodservice packs where possible.
    m=re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|ml|l|lt)\b",title,re.I)
    if m:
        n=parse_money(m.group(1)) or 0
        u=norm(m.group(2))
        grams=n*1000 if u in {"kg","l","lt"} else n
        if 400<=grams<=1500: score+=3
        if grams>3000: score-=3
    return score

def unit_and_basis(target, amount, pkg_unit, current, regular):
    # Same base unit: direct.
    if target["unit"]==pkg_unit:
        return amount,pkg_unit,current,regular,False

    # Recipe uses g/ml, store package is matching family.
    if target["unit"]=="g" and pkg_unit=="g":
        return amount,pkg_unit,current,regular,False
    if target["unit"]=="ml" and pkg_unit=="ml":
        return amount,pkg_unit,current,regular,False

    # Count-like recipe unit priced from kg/g using known average gram per item.
    conv=target.get("massToTargetUnit")
    if conv and pkg_unit=="g" and target["unit"] in {"adet","diş","demet"}:
        gpu=float(conv.get("gramsPerUnit") or 0)
        if gpu>0 and amount>0:
            unit_price=current*(gpu/amount)
            reg_unit=regular*(gpu/amount)
            return 1.0,target["unit"],round(unit_price,4),round(reg_unit,4),True

    return None,None,None,None,False

def candidate_rows(target):
    rows=[]
    for u in target.get("directUrls",[]):
        su=safe_url(u)
        if su: rows.append((su,""))
    rows.extend(catalog_candidates(target.get("catalogUrls",[])))
    # Search stays as fallback, not primary source.
    rows.extend(search_page(target.get("query","")))
    return dedupe(rows)

def resolve(target):
    rows=candidate_rows(target)
    if not rows:
        return None,"aday ürün bulunamadı"

    # Rank catalog hints before opening product pages.
    ranked=[]
    for url,hint in rows:
        if hint:
            ok,reason=semantic_ok(target,hint)
            if not ok:
                continue
            ranked.append((score_candidate(target,hint),url,hint))
        else:
            ranked.append((0,url,hint))
    ranked.sort(key=lambda x:x[0],reverse=True)

    rejected=[]
    for _,url,hint in ranked[:18]:
        try:
            html=fetch(url)
            title=title_from(html) or hint
            ok,reason=semantic_ok(target,title)
            if not ok:
                rejected.append(reason); continue

            amount,pkg_unit,_=package_info(title,target)
            if not amount or not pkg_unit:
                rejected.append("paket/birim bilgisi okunamadı"); continue

            price_candidates=[]
            for p in jsonld_products(html):
                pname=str(p.get("name") or "")
                ok2,_=semantic_ok(target,pname or title)
                if ok2:
                    price_candidates.extend(offer_prices(p))
            price_candidates.extend(header_prices(html,title))
            price_candidates=[x for x in price_candidates if x and 0.5<=x<=100000]
            # Preserve order but unique.
            uniq=[]
            for x in price_candidates:
                if x not in uniq: uniq.append(x)
            if not uniq:
                rejected.append("ürün başlık alanında fiyat okunamadı"); continue

            current=min(uniq[:3])
            regular=max(uniq[:3])
            basis_amount,basis_unit,current_norm,regular_norm,estimated=unit_and_basis(
                target,amount,pkg_unit,current,regular
            )
            if not basis_amount:
                rejected.append(f"birim uyumsuz: ürün {pkg_unit}, tarif {target['unit']}"); continue

            return {
                "ingredient":target["ingredient"],
                "unit":target["unit"],
                "provider":"ŞOK / Cepte ŞOK",
                "retailer":"ŞOK",
                "productName":title,
                "currentPrice":round(float(current_norm),4),
                "regularPrice":round(float(regular_norm),4),
                "price":round(float(current_norm),4),
                "packageAmount":basis_amount,
                "packageUnit":basis_unit,
                "basisAmount":basis_amount,
                "basisUnit":basis_unit,
                "storePackageAmount":amount,
                "storePackageUnit":pkg_unit,
                "storePackagePrice":round(float(current),2),
                "pricingMode":target["pricingMode"],
                "status":"live-estimate" if estimated else "live",
                "observedAt":now_iso(),
                "sourceUrl":url,
                "locationScope":"cepte-sok-online",
                "matchPolicy":"catalog-strict-v0.4.3",
                "note":(
                    "Cepte ŞOK resmi ürün sayfasından doğrulandı; adet/diş maliyeti kg fiyatından ortalama ağırlıkla hesaplandı."
                    if estimated else
                    "Cepte ŞOK resmi ürün sayfasından; kategori + ürün adı + paket birimi birlikte doğrulandı."
                )
            },None
        except Exception as exc:
            rejected.append(str(exc)[:100])

    return None,f"güvenli eşleşme bulunamadı: {rejected[-1] if rejected else 'uygun ürün yok'}"

def main():
    old={}
    if OUT.exists():
        try:
            d=json.loads(OUT.read_text(encoding="utf-8"))
            old={(q.get("ingredient"),q.get("unit")):q for q in d.get("quotes",[])}
        except Exception:
            pass

    quotes=[]; failed=[]
    for idx,target in enumerate(TARGETS,1):
        q,err=resolve(target)
        if q:
            quotes.append(q)
            print(f"[{idx}/{len(TARGETS)}] OK {target['ingredient']}: {q['currentPrice']} TL/{q['packageAmount']} {q['packageUnit']} — {q['productName']}")
        else:
            prev=old.get((target["ingredient"],target["unit"]))
            if prev:
                quotes.append(prev)
            failed.append({"ingredient":target["ingredient"],"unit":target["unit"],"reason":err})
            print(f"[{idx}/{len(TARGETS)}] SKIP {target['ingredient']}: {err}")
        time.sleep(0.45)

    live=[q for q in quotes if q.get("status") in {"live","live-estimate"}]
    last_success=max((q.get("observedAt","") for q in live),default=None)

    OUT.write_text(json.dumps({
        "schemaVersion":3,
        "retailer":"ŞOK / Cepte ŞOK",
        "generatedAt":now_iso(),
        "lastSuccessfulAt":last_success,
        "locationScope":"cepte-sok-online",
        "quotes":quotes,
        "failed":failed,
        "source":BASE,
        "matchPolicy":"catalog-strict-v0.4.3",
        "liveCount":len(live),
        "failedCount":len(failed),
        "policy":"Önce resmi ŞOK kategori sayfalarından aday bulur; sonra ürün detay sayfasında ad, paket birimi ve fiyatı doğrular. Emin değilse eski kayıt korunur."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
