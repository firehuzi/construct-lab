# -*- coding: utf-8 -*-
"""fill_evidence.py —— 把【已存档的依据】填进案例的判断里

★ 一次性脚本（不是常驻工具），但它做的事定义了记录的第三个形态：

   ① 机器自动判     source = "UCDP:dyad_present(...)"     ← 数据层直接判
   ② 人判＋依据可核 evidence = {slug, observed, quote}     ← 人看过存档后判（本次新增）
   ③ 待人工        两者都没有                             ← 进队列

  ★★ ②与①【不能混】。它们的可信度来源不同：
     ① 的可信度来自数据，
     ② 的可信度来自【一个能被别人打开核对的存档】。
     所以读数必须三分，不是二分 —— 否则「搜索这条路解决了多少」就看不出来。

  ★★ 而②要能成立，依据必须过【三道机器检查】（写在 case_check.py 里）：
       · slug 在 data/sources/index.json 里
       · verified_open == True      （取不到 ⇒ 这条依据不存在）
       · witness_type == contemporary（事后的不能用于时间锁定）
     缺任何一道 ⇒ 该判断【退回待人工】。**这是让「填了依据」不等于「过了」的机制。**
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(HERE, "data", "cases", "filled", "IQ-KW-1991.json")

# 每条：judgment_id → (slug, observed, quote, note)
EV = {
    "IQ-KW@1991-P03/oracle": None,       # 占位，下面按 stage 名匹配
}

BY_STAGE = {
    # ── P03① 宣布撤军 ──
    ("IQ-KW@1991-P03", "宣布撤军"): {
        "slug": "govinfo.gov_PPP_1991_book1_doc_pg176_htm.html",
        "observed": False,
        "quote": "Saddam Hussein's radio statement last night contained the same diatribe as "
                 "previous comments, with no commitment to complying with the 12 United Nations "
                 "resolutions. His speech changes nothing.",
        "note": "★ 照实记：这份依据【只覆盖了 2 月 26 日那次声明】，而窗口问的是"
                "【最后期限（1 月 15 日）之前】。它证明「2 月那次不算撤军」，"
                "但【没有独立证明 1 月 15 日之前也没有宣布】。"
                "所以 observed=False 的依据强度是【部分】的，不是完整的。",
    },
    # ── P03② 联军收手 ──
    ("IQ-KW@1991-P03", "联军收手"): {
        "slug": "govinfo.gov_PPP_1991_book1_doc_pg187_htm.html",
        "observed": True,
        "quote": "Address to the Nation on the Suspension of Allied Offensive Combat Operations "
                 "in the Persian Gulf — George H. W. Bush, February 27, 1991",
        "note": "★ 这是【总统原始文件】，它就是「暂停进攻作战」那道命令本身。"
                "★ 但注意一个缺口：P03 的假设是「伊拉克撤军 ⇒ 联军收手」，"
                "而实际原因【不是撤军，是伊拉克战败】。⇒ 阶段被确认了，"
                "**因果链没有被验证**。这个缺口目前没有任何东西能查。",
    },
    # ── P04① 以色列还击 ──
    ("IQ-KW@1991-P04", "以色列还击"): {
        "slug": "jta.org_schools_closed_streets_were_empty_as_isr.html",
        "observed": False,
        "quote": "Schools Closed, Streets Were Empty As Israel Awaited Military Action — "
                 "January 17, 1991. The Education Ministry ordered Israeli schools closed "
                 "Wednesday after consultations with the...",
        "note": "★ 两个独立来源互相印证：JTA（1991-01-17）「Israel Awaited」＋ "
                "Baltimore Sun（1991-01-19）「Israeli 'restraint' hailed, but action now more "
                "likely」。⇒ 「以色列没有还击」这件事，拿到的是【当时还在等待／克制】的"
                "正面证据，而不是「搜不到」。",
    },
    # ── P05② 地面僵持 ──
    ("IQ-KW@1991-P05", "地面僵持"): {
        "slug": "news.bbc.co.uk_2515289_stm.html",
        "observed": False,
        "quote": "BBC ON THIS DAY | 28 February 1991: Jubilation follows Gulf War ceasefire",
        "note": "★ 地面战 2 月 24 日开始、2 月 28 日停火 —— 【100 小时】，"
                "与「持续超过 3 个月」相差两个数量级。依据是停火当天的报道。",
    },
}


def main() -> int:
    with io.open(CASE, encoding="utf-8") as fh:
        case = json.load(fh)

    idxp = os.path.join(HERE, "data", "sources", "index.json")
    with io.open(idxp, encoding="utf-8") as fh:
        index = {r["archived_snapshot"].split("/")[-1]: r for r in json.load(fh)["sources"]}

    filled = 0
    for p in case.get("paths", []):
        for st in p.get("stages", []):
            key = (p.get("id"), st.get("stage"))
            if key not in BY_STAGE:
                continue
            ev = dict(BY_STAGE[key])
            rec = index.get(ev["slug"])
            ev["witness_type"] = rec["witness_type"] if rec else None
            ev["published"] = rec.get("published") if rec else None
            ev["url"] = rec["url"] if rec else None
            ev["verified_open"] = rec.get("verified_open") if rec else False
            st["evidence"] = ev
            filled += 1

    with io.open(CASE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(case, fh, ensure_ascii=False, indent=2)

    print("填了 %d 条依据：" % filled)
    for p in case.get("paths", []):
        for st in p.get("stages", []):
            if "evidence" in st:
                e = st["evidence"]
                print("  %-22s observed=%-5s %s (%s)" %
                      ("%s/%s" % (p["id"].split("@")[-1], st["stage"]),
                       e["observed"], e["witness_type"], e["slug"][:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
