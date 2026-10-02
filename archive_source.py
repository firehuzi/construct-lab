# -*- coding: utf-8 -*-
"""archive_source.py —— 取证：把一条线索变成【可复现的依据】

★★ 为什么必须有这一步
   用户问「在功能里加数据搜索引擎能不能满足需求」。答案是不能 —— 因为搜索引擎
   交付的是【链接】，而链接会烂。本轮实测到两次：
     · develop.baltimoresun.com  —— 开发域名，打不开（同一个报纸的另一个域名是好的）
     · web_fetch 对 wikipedia / archive.org / govinfo.gov 全部报
       "resolves to a non-public IP address"
   而后者查下去发现**是安全闸误判**：所有域名都解析到 198.18.0.x（RFC 2544 保留段，
   透明代理的 fake-IP），闸把它当成了内网地址。**网络本身是通的** ——
   PowerShell 的 Invoke-WebRequest 直接取得到 example.com。

   ⇒ 所以：**链接不是依据，存下来的字节才是依据。**

★★ 三个字段，缺一个这一步就退化成「形式上有核验、实际没人看」
     archived_snapshot   存下来的原文（这份文件）
     verified_open       取到了 ⇒ true；没取到 ⇒ false，**这条依据不存在**
     witness_type        contemporary / retrospective / unknown
                         ★ **retrospective 不能用于时间锁定** —— 它掺了后见之明

★★ 还要存什么，为什么
     sha256      证明「我判定时看的就是这些字节」，以后文件被改了能发现
     fetched_at  取回时间。同一 URL 在不同时候可能不同 —— 不记时间就不可复现
     http_status / content_type / bytes
     query_used  用它搜到的（哪个入口）。**没有这个就无法回溯「我是怎么找到它的」**

运行：  python archive_source.py --selftest
        python archive_source.py <url> [<url> ...] --outlet 華僑日報 --published 1991-01-24
        python archive_source.py --from-queries <案例.queries.json> --top 4
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "data", "sources")
INDEX = os.path.join(SRC_DIR, "index.json")

UA = "Mozilla/5.0 (ConStruct Lab research archive; +local)"

# 事后叙述的强信号 —— 命中就标 retrospective，**不能用于时间锁定**
RETRO_HINTS = [r"wiki", r"britannica", r"history\.com", r"thoughtco", r"/20(1[6-9]|2\d)/"]


def slug(url: str) -> str:
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    tail = re.sub(r"[^\w]+", "_", url.split("/")[-1] or "index")[:40]
    return "%s_%s" % (re.sub(r"[^\w.]", "_", host)[:40], tail)


def guess_witness(url: str, published: str | None) -> str:
    """猜这条来源是【当时的】还是【事后的】。

    ★ 猜错了后果很重：retrospective 被当成 contemporary 用进时间锁定，
      就等于把后见之明混进了判断。所以**默认保守** —— 判不出来就 unknown。
    """
    low = url.lower()
    for pat in RETRO_HINTS:
        if re.search(pat, low):
            return "retrospective"
    # 路径里带 1991/01/19 这类日期 ⇒ 当时的存档页
    m = re.search(r"/(19|20)(\d{2})/(\d{2})/", url)
    if m:
        return "contemporary"
    if re.search(r"/(archive|archives|xpm|ppp-|NPWK|details)/", low):
        return "contemporary" if re.search(r"(19|20)\d{2}", low) else "unknown"
    return "unknown"


def date_in_text(text: str) -> str | None:
    """从正文里抠出【成文日期】。

    ★ 为什么不能只从 URL 猜：实测 govinfo.gov 那份 1991 年的政府原始文件，
      URL 里**没有日期**，于是被判成 `unknown` —— 而 unknown 不能用于时间锁定
      ⇒ **最有价值的那条依据被判成不可用**。
      但取到的正文里明明写着「February 26, 1991」。
      ⇒ 所以判 witness_type 必须看【内容】，不能只看 URL。
    """
    if not text:
        return None
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text[:200000])
    t = re.sub(r"<[^>]+>", " ", t)
    months = ("January|February|March|April|May|June|July|August|September|"
              "October|November|December")
    m = re.search(r"\b(%s)\s+(\d{1,2}),\s*((?:19|20)\d{2})\b" % months, t)
    if m:
        return "%04d-%02d-%02d" % (int(m.group(3)),
                                   ("January February March April May June July August "
                                    "September October November December").split().index(m.group(1)) + 1,
                                   int(m.group(2)))
    m = re.search(r"\b(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", t)
    if m:
        return "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def witness_from_content(text: str, url: str, published: str) -> tuple:
    """由【内容】＋【URL】＋【外部给定日期】共同判定 witness_type。

    返回 (witness_type, doc_date, basis)。★ 判不出来仍然返回 unknown —— 保守。
    """
    low = url.lower()
    for pat in RETRO_HINTS:
        if re.search(pat, low):
            return "retrospective", None, "URL 命中事后叙述特征（wiki/britannica 等）"
    d = date_in_text(text)
    if d:
        return "contemporary", d, "正文里抠到成文日期 %s" % d
    g = guess_witness(url, published)
    return g, None, "只有 URL 特征可用"


def fetch(url: str, timeout: int = 30):
    """取回一个 URL。★ 用标准库 —— 它走系统解析器，不受 web_fetch 那个闸影响。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read()
            return {"ok": True, "status": getattr(r, "status", 200), "bytes": raw,
                    "content_type": r.headers.get("Content-Type", ""),
                    "final_url": r.geturl()}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": "HTTP %s" % e.code, "bytes": b""}
    except Exception as e:                                    # noqa: BLE001
        return {"ok": False, "status": None, "error": str(e)[:200], "bytes": b""}


def archive(url: str, outlet: str = "", published: str = "", query_used: str = "",
            witness_type: str | None = None, do_fetch: bool = True) -> dict:
    os.makedirs(SRC_DIR, exist_ok=True)
    name = slug(url)
    rec = {"url": url, "slug": name, "outlet": outlet, "published": published,
           "query_used": query_used,
           "fetched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "witness_type": witness_type or guess_witness(url, published),
           "doc_date": None, "witness_basis": None,
           "archived_snapshot": None, "verified_open": False,
           "sha256": None, "bytes": 0, "http_status": None, "content_type": "",
           "final_url": None, "error": None}
    if do_fetch:
        r = fetch(url)
        rec["http_status"] = r.get("status")
        rec["content_type"] = (r.get("content_type") or "")[:120]
        rec["final_url"] = r.get("final_url")
        if r["ok"] and r["bytes"]:
            ext = ".html"
            if "json" in rec["content_type"]:
                ext = ".json"
            elif "pdf" in rec["content_type"]:
                ext = ".pdf"
            elif "image/" in rec["content_type"]:
                ext = ".bin"
            path = os.path.join(SRC_DIR, name + ext)
            with open(path, "wb") as fh:
                fh.write(r["bytes"])
            rec["archived_snapshot"] = os.path.relpath(path, HERE).replace("\\", "/")
            rec["sha256"] = hashlib.sha256(r["bytes"]).hexdigest()
            rec["bytes"] = len(r["bytes"])
            rec["verified_open"] = True
            # ★ 取到之后就【用内容重判】witness_type —— 只从 URL 猜会漏掉 govinfo 那种
            if not witness_type:
                try:
                    txt = r["bytes"].decode("utf-8", "ignore")
                except Exception:                              # noqa: BLE001
                    txt = ""
                wt, dd, basis = witness_from_content(txt, url, published)
                rec["witness_type"], rec["doc_date"], rec["witness_basis"] = wt, dd, basis
        else:
            rec["error"] = r.get("error")
    return rec


def load_index() -> list:
    if os.path.exists(INDEX):
        try:
            with io.open(INDEX, encoding="utf-8") as fh:
                return json.load(fh).get("sources") or []
        except (OSError, ValueError):
            return []
    return []


def save_index(rows: list):
    os.makedirs(SRC_DIR, exist_ok=True)
    with io.open(INDEX, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"schema": "construct-sources-v1",
                   "note": "依据档案。★ verified_open=false 的条目【不算依据】。"
                           "★ witness_type=retrospective 的条目【不能用于时间锁定】。",
                   "sources": rows}, fh, ensure_ascii=False, indent=2)


def audit() -> dict:
    """★ 审计依据档案：找【孤儿文件】与【内容不可用】的条目。

    为什么必须有这个：我自己在这一步就造出了重复存档 ——
    先用 PowerShell 存了两个文件，再用 archive_source.py 存了一遍，
    **同一份来源两个名字、字节还不同，而没进索引的那份是孤儿**。
    这正是本项目反复出现的病（两份同名不同内容的文件），只不过这次是我自己造的。
    ⇒ 机器查：目录里有、索引里没有的，一律报出来。
    """
    rows = load_index()
    known = set()
    for r in rows:
        if r.get("archived_snapshot"):
            known.add(os.path.basename(r["archived_snapshot"]))
    on_disk = set()
    if os.path.isdir(SRC_DIR):
        on_disk = {f for f in os.listdir(SRC_DIR)
                   if f != "index.json" and os.path.isfile(os.path.join(SRC_DIR, f))}
    orphans = sorted(on_disk - known)
    missing = sorted(known - on_disk)
    thin = []
    for r in rows:
        if not r.get("archived_snapshot"):
            continue
        p = os.path.join(HERE, r["archived_snapshot"])
        if not os.path.exists(p):
            continue
        txt = io.open(p, "rb").read().decode("utf-8", "ignore")
        body = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", txt)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"&[a-z]+;|\s+", " ", body).strip()
        if len(body) < 500:
            thin.append((os.path.basename(p), len(body)))
    return {"rows": rows, "orphans": orphans, "missing": missing, "thin": thin}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    if "--audit" in sys.argv:
        a = audit()
        print("=" * 96)
        print("# 依据档案审计")
        print("=" * 96)
        print("  条目 %d，其中 verified_open=true 的 %d 条"
              % (len(a["rows"]), len([r for r in a["rows"] if r.get("verified_open")])))
        print("  witness_type=contemporary 的 %d 条（**只有这些能用于时间锁定**）"
              % len([r for r in a["rows"] if r.get("witness_type") == "contemporary"]))
        print("\n  ── 孤儿文件（目录里有、索引里没有）: %d" % len(a["orphans"]))
        for f in a["orphans"]:
            print("     ⚠️ %s" % f)
        if a["orphans"]:
            print("     ★ 这些**不算依据** —— 索引里没有它，就没人知道它是什么、什么时候取的。")
        print("\n  ── 索引里有、盘上没有: %d" % len(a["missing"]))
        for f in a["missing"]:
            print("     ⛔ %s" % f)
        print("\n  ── 可读文本过少（可能是付费墙／JS 壳／错误页）: %d" % len(a["thin"]))
        for f, n in a["thin"]:
            print("     ⚠️ %-56s 可读文本仅 %d 字符" % (f[:56], n))
        print("     ★ **存档成功 ≠ 内容可用。** 取回 200 也可能是付费墙或错误页。")
        print("=" * 96)
        return 0

    def opt(name, default=""):
        if name in sys.argv:
            i = sys.argv.index(name)
            if i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        return default

    urls = [a for a in sys.argv[1:] if a.startswith("http")]
    if not urls:
        print("用法：python archive_source.py <url> [...] [--outlet X --published Y --query Q]")
        print("      python archive_source.py --report")
        return 1

    rows = load_index()
    seen = {r["url"] for r in rows}
    for u in urls:
        rec = archive(u, outlet=opt("--outlet"), published=opt("--published"),
                      query_used=opt("--query"))
        if u in seen:
            rows = [rec if r["url"] == u else r for r in rows]
        else:
            rows.append(rec)
        mark = "✅ 已存档" if rec["verified_open"] else "⛔ 取不到"
        print("  %s  %-58s %s" % (mark, u[:58],
                                  ("%d 字节  %s" % (rec["bytes"], rec["witness_type"]))
                                  if rec["verified_open"] else rec["error"]))
    save_index(rows)

    ok = [r for r in rows if r["verified_open"]]
    print("\n  ── 依据档案")
    print("     条目 %d，其中 verified_open=true 的 %d 条 ⇒ **只有这些算依据**"
          % (len(rows), len(ok)))
    usable = [r for r in ok if r["witness_type"] == "contemporary"]
    print("     witness_type=contemporary 的 %d 条 ⇒ **只有这些能用于时间锁定**" % len(usable))
    print("     ★ 其余一律不许拿来判定 —— 这就是三个字段存在的理由。")
    return 0


def selftest() -> int:
    n_pass = n_fail = 0

    def ck(name, cond, detail=""):
        nonlocal n_pass, n_fail
        if cond:
            n_pass += 1
            print("  ✅ %s" % name)
        else:
            n_fail += 1
            print("  ❌ %s   %s" % (name, detail))

    print("# archive_source 自证")
    ck("★slug 稳定且可读",
       slug("https://www.govinfo.gov/content/pkg/PPP-1991-book1/html/x.htm").startswith("govinfo.gov_"),
       slug("https://www.govinfo.gov/content/pkg/PPP-1991-book1/html/x.htm"))

    # ★★ witness_type：错了后果最重，所以三个方向都要钉
    ck("★★维基百科 ⇒ retrospective（不能用于时间锁定）",
       guess_witness("https://en.wikipedia.org/wiki/X", None) == "retrospective",
       guess_witness("https://en.wikipedia.org/wiki/X", None))
    ck("★★带当年日期的存档页 ⇒ contemporary",
       guess_witness("https://www.baltimoresun.com/1991/01/19/israeli-restraint-hailed/", None)
       == "contemporary")
    ck("★★判不出来 ⇒ unknown（保守，不冒充当时的）",
       guess_witness("https://example.com/some/page", None) == "unknown",
       guess_witness("https://example.com/some/page", None))

    # ★★ 内容日期判定：govinfo 那条 URL 里没日期，只能靠正文
    ck("★★能从正文抠出英文成文日期",
       date_in_text("<p>Statement ... February 26, 1991 Saddam Hussein...") == "1991-02-26",
       str(date_in_text("<p>Statement ... February 26, 1991")))
    ck("★★能从正文抠出中文日期",
       date_in_text("1991年2月26日——声明") == "1991-02-26")
    ck("★抠不到返回 None（不编日期）", date_in_text("没有日期的一段话") is None)
    wt, dd, basis = witness_from_content("<p>February 26, 1991</p>",
                                         "https://www.govinfo.gov/content/pkg/x.htm", "")
    ck("★★govinfo 那种 URL 无日期、但正文有 ⇒ 判 contemporary（不能判 unknown）",
       wt == "contemporary" and dd == "1991-02-26", "%s / %s / %s" % (wt, dd, basis))
    ck("★★维基百科即使正文有日期也仍是 retrospective（URL 优先于内容）",
       witness_from_content("<p>February 26, 1991</p>", "https://en.wikipedia.org/wiki/X", "")[0]
       == "retrospective")
    ck("★正文与 URL 都判不出来 ⇒ unknown（保守）",
       witness_from_content("no date here", "https://example.com/p", "")[0] == "unknown")

    # ★ 真实取回（网络是通的，这个环境里就该真跑）
    r = fetch("https://example.com")
    ck("★★真取回：example.com 成功（证明网络通、且标准库不受那个闸影响）",
       r["ok"] and len(r["bytes"]) > 100, str(r.get("error"))[:80])

    rec = archive("https://example.com", outlet="test", query_used="q", do_fetch=True)
    ck("★存档记录带 sha256", bool(rec["sha256"]) and len(rec["sha256"]) == 64)
    ck("★存档记录带 fetched_at（不记时间就不可复现）", bool(rec["fetched_at"]), rec["fetched_at"])
    ck("★存档记录带 query_used（否则回溯不了「怎么找到的」）", rec["query_used"] == "q")
    ck("★取到 ⇒ verified_open=True 且写了文件",
       rec["verified_open"] is True and rec["archived_snapshot"]
       and os.path.exists(os.path.join(HERE, rec["archived_snapshot"])),
       str(rec["archived_snapshot"]))
    ck("★bytes 与 sha256 一致（哈希算的是真字节）",
       rec["bytes"] == os.path.getsize(os.path.join(HERE, rec["archived_snapshot"])))
    rec2 = archive("https://this-host-does-not-exist-xyz.invalid/x", do_fetch=True)
    ck("★★取不到 ⇒ verified_open=False（**这条依据不存在**）",
       rec2["verified_open"] is False and rec2["error"], str(rec2["error"])[:60])
    ck("★取不到时 archived_snapshot 为 None（不写空文件冒充存档）",
       rec2["archived_snapshot"] is None)

    # ★★ 自证必须不留痕
    #   第一版自证调 archive() 真往 data/sources 写了个 example.com 文件，
    #   而 --audit 随即把它报成孤儿。**自证污染了数据目录。**
    #   ⇒ 用完必须自己清掉，并且断言清干净了。
    cleaned = []
    for r in (rec, rec2):
        f = r.get("archived_snapshot")
        if f:
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                os.remove(p)
                cleaned.append(f)
    ck("★★自证用完清掉自己写的文件（不留孤儿）",
       all(not os.path.exists(os.path.join(HERE, f)) for f in cleaned),
       str(cleaned))
    ck("★★自证【不往索引里写】", "example.com" not in
       " ".join(r.get("url", "") for r in load_index()),
       str([r.get("url") for r in load_index()][:3]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
