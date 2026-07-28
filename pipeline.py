#!/usr/bin/env python3
"""
ConStruct Data Pipeline v4.1
Real data sources: GDELT (global events) + FRED (economic indicators)
Fallback: manual input when APIs are unavailable
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ===== GDELT API (free, real-time events) =====

def fetch_gdelt(subject_codes=["USA","CHN","RUS","JPN"], lookback_hours=24):
    """Fetch recent events from GDELT for specified country codes.
    
    GDELT GKG 2.0 API: free, no key required.
    TONE field: positive/negative sentiment score.
    """
    try:
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query=(sourcecountry:{'OR'.join(subject_codes)})&mode=artlist&timespan={lookback_hours}h&format=json&maxrecords=50"
        req = urllib.request.Request(url, headers={"User-Agent": "ConStructEngine/4.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        events = []
        for article in data.get("articles", [])[:50]:
            events.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "tone": float(article.get("tone", 0)),
                "date": article.get("seendate", ""),
                "source_country": article.get("sourcecountry", "")
            })
        
        avg_tone = sum(e["tone"] for e in events) / len(events) if events else 0
        return {
            "count": len(events),
            "avg_tone": round(avg_tone, 2),
            "signal_words": extract_signal_words(events),
            "events": events[:10]
        }
    except Exception as e:
        return {"count": 0, "avg_tone": 0, "signal_words": [], "error": str(e), "source": "gdelt_failed"}


def extract_signal_words(events):
    """Extract keywords from titles that match signal patterns."""
    keywords = []
    patterns = ["war","crisis","sanction","military","invasion","nuclear","tariff","conflict",
                "tension","alliance","missile","provocation","withdrawal","collapse","embargo",
                "blockade","coup","ceasefire","escalation"]
    for e in events:
        title = e.get("title","").lower()
        for p in patterns:
            if p in title and p not in keywords:
                keywords.append(p)
    return keywords[:8]


# ===== FRED API (economic indicators) =====

def fetch_fred(api_key=None, series=["FEDFUNDS","CPIAUCSL","UNRATE","GDP","DGS10"]):
    """Fetch economic data from FRED. 
    Uses FRED API if key provided, otherwise attempts fallback CSV endpoint.
    """
    results = {}
    
    # Try FRED API with key
    for code in series:
        try:
            if api_key:
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={code}&api_key={api_key}&file_type=json&sort_order=desc&limit=1"
                req = urllib.request.Request(url, headers={"User-Agent": "ConStructEngine/4.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                if data.get("observations"):
                    results[code] = float(data["observations"][0]["value"])
            else:
                # Alternative: scrape FRED's public CSV endpoint
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?bgcolor=%23ffffff&chart_type=line&drp=0&fo=open%20sans&graph_bgcolor=%23ffffff&height=200&mode=fred&recession_bars=on&txt_color=%23444444&ts=12&tts=12&width=400&nticks=2&thickness=1&id={code}&cosd=2025-01-01&coed=2026-12-31"
                req = urllib.request.Request(url, headers={"User-Agent": "ConStructEngine/4.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    lines = resp.read().decode().split('\n')
                    if len(lines) > 1:
                        last = lines[-2].split(",")
                        results[code] = float(last[1]) if len(last) > 1 and last[1].strip() else 0
        except:
            pass
    
    return results


# ===== Manual Fallback =====

def manual_input():
    """Fallback: manual data entry when APIs are unavailable."""
    print("\n=== Manual DEL-2 Input (APIs unavailable) ===")
    print("Enter values or press Enter to skip.\n")
    
    del2 = {}
    fields = [("oil_price", "WTI Crude ($/barrel)"), ("inflation", "US CPI (%)"),
              ("interest_rate", "Fed Funds Rate (%)"), ("sanctions", "New sanctions this month"),
              ("gdp_growth", "US GDP Growth (%)")]
    
    for key, label in fields:
        val = input(f"  {label}: ").strip()
        if val:
            del2[key] = float(val)
    
    del3 = {}
    event_count = input("\n  Significant events today (count): ").strip()
    if event_count:
        del3["event_count"] = int(event_count)
    kw = input("  Keywords (comma sep): ").strip()
    if kw:
        del3["signal_words"] = [w.strip() for w in kw.split(",")]
    
    return del2, del3


# ===== Main Pipeline =====

def run():
    print("=" * 50)
    print("  ConStruct Pipeline v4.1 — Data Collection")
    print("=" * 50)
    
    # Try GDELT
    print("\n[GDELT] Fetching global events...")
    fr = os.environ.get("FRED_API_KEY", "")
    gdelt_data = fetch_gdelt()
    
    if gdelt_data.get("count", 0) > 0:
        print(f"  OK: {gdelt_data['count']} articles, avg tone: {gdelt_data['avg_tone']}")
        print(f"  Signals: {gdelt_data.get('signal_words', [])}")
    else:
        print(f"  FAIL: {gdelt_data.get('error', 'unknown')} — using manual input")
    
    # Try FRED
    print("\n[FRED] Fetching economic data...")
    fred_data = fetch_fred(fr)
    if fred_data:
        print(f"  OK: {list(fred_data.keys())}")
    else:
        print("  FAIL — using manual input")
    
    # Build DEL data
    del2 = {}
    if "FEDFUNDS" in fred_data:
        del2["interest_rate"] = fred_data["FEDFUNDS"]
    if "CPIAUCSL" in fred_data:
        del2["inflation"] = round(fred_data["CPIAUCSL"], 1)
    
    del3 = {
        "event_count": gdelt_data.get("count", 0),
        "avg_tone": gdelt_data.get("avg_tone", 0),
        "signal_words": gdelt_data.get("signal_words", []),
        "threshold": 50,
        "last_update": datetime.now().isoformat()
    }
    
    # Fallback: use last saved data if APIs failed
    feed_path = DATA_DIR / "del_feed.json"
    if not del2 or gdelt_data.get("count", 0) == 0:
        if feed_path.exists():
            with open(feed_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if not del2:
                del2 = prev.get("del2", {})
                print("\n[FALLBACK] Loaded last DEL-2 data from cache")
            if gdelt_data.get("count", 0) == 0:
                del3 = prev.get("del3", {"event_count": 0, "signal_words": [], "threshold": 50})
                print("[FALLBACK] Loaded last DEL-3 data from cache")
        
        # If still empty, try interactive mode
        if not del2:
            try:
                del2, del3_manual = manual_input()
                if del3_manual: 
                    del3.update(del3_manual)
            except (EOFError, KeyboardInterrupt):
                del2 = {"oil_price": 82, "inflation": 3.5, "interest_rate": 5.25, "gdp_growth": 1.5}
                print("\n[AUTO] Non-interactive mode - using defaults")
    
    # Save
    output = {
        "last_run": datetime.now().isoformat(),
        "del2": del2,
        "del3": del3,
        "sources": {
            "gdelt": gdelt_data.get("count", 0) > 0,
            "fred": len(fred_data) > 0,
            "manual": len(del2) == 0
        }
    }
    
    feed_path = DATA_DIR / "del_feed.json"
    with open(feed_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n[PIPELINE] Saved → {feed_path}")


if __name__ == "__main__":
    run()
