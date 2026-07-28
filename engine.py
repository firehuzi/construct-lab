#!/usr/bin/env python3
"""
ConStruct Engine v4.0 — 实时地缘政治认知引擎
四引擎架构：Identity Interpreter → Signal Detector → Consistency Checker → SUL Scorer
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

BASE = Path(__file__).parent.parent


def load_actors():
    """Load actor database from bridge script output."""
    actors_path = BASE / "actors.json"
    if not actors_path.exists():
        print("[ENGINE] actors.json not found. Run construct_bridge.py export first.")
        return {}
    with open(actors_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_del_data():
    """Load DEL data from pipeline output."""
    del_path = Path(__file__).parent / "data" / "del_feed.json"
    if not del_path.exists():
        return {"last_run": None, "del2": {}, "del3": {}}
    with open(del_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rules(subject_code):
    """Load identity translation rules for a subject."""
    rules_path = Path(__file__).parent / "rules" / f"{subject_code}.json"
    if not rules_path.exists():
        return {}
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ===== ENGINE 1: Identity Interpreter =====

def interpret_identity(subject_code, actor_data, del_data):
    """Translate DEL data through Identity lens.
    
    Returns: {parameter: {value, direction, interpretation}}
    """
    rules = load_rules(subject_code)
    if not rules:
        return {"status": "no_rules", "params": {}}
    
    dna = actor_data.get("dna", {})
    params = {}
    
    translations = rules.get("del_translations", {})
    for param, rule in translations.items():
        del_path = rule.get("del_path", "")
        threshold = rule.get("threshold", 0.05)
        identity_label = rule.get("identity_label", "")
        
        current = del_data.get(param, None)
        if current is None:
            params[param] = {"value": 0, "direction": "→", "interpretation": f"数据缺失: {identity_label}"}
            continue
        
        prev = rule.get("baseline", current)
        change = (current - prev) / prev if prev else 0
        
        direction = "→"
        if abs(change) > threshold:
            direction = "↑" if change > 0 else "↓"
        
        params[param] = {
            "value": current,
            "direction": direction,
            "change_pct": round(change * 100, 1),
            "interpretation": f"{identity_label}: {direction} ({round(change*100,1) or 0}%)"
        }
    
    return {
        "status": "ok",
        "subject": subject_code,
        "dna": dna,
        "params": params
    }


# ===== ENGINE 2: Signal Detector =====

def detect_signals(subject_code, identity_output, del_data):
    """Detect anomalous events that deviate from expected behavior patterns.
    
    Uses two sources:
    1. Rule-based triggers (from rules/{code}.json signal_rules)
    2. GDELT signal words (from del3 data)
    """
    rules = load_rules(subject_code)
    signals = []
    
    # Rule-based triggers
    signal_rules = rules.get("signal_rules", [])
    params = identity_output.get("params", {})
    for sr in signal_rules:
        trigger = sr.get("trigger", "")
        severity = sr.get("severity", "low")
        description = sr.get("description", "")
        
        triggered = False
        if "rate_hike" in trigger:
            ir = params.get("interest_rate", {})
            if ir.get("direction") == "↑" and abs(ir.get("change_pct", 0)) > 3:
                triggered = True
        if "gdp" in trigger and "tech" not in trigger:
            gdp = params.get("gdp_growth", params.get("gdp", {}))
            if gdp.get("direction") == "↓":
                triggered = True
        if "military" in trigger:
            mil = params.get("military", {})
            if mil.get("direction") == "↑":
                triggered = True
        if "tech" in trigger:
            tech = params.get("tech_sanctions", {})
            if tech.get("direction") in ("↑","↓"):
                triggered = True
        if "debt" in trigger:
            ir = params.get("interest_rate", {})
            if ir.get("direction") == "↑" and abs(ir.get("change_pct", 0)) > 10:
                triggered = True
        if "ally" in trigger or "tariff" in trigger or "escalation" in trigger:
            del3 = del_data.get("del3", {})
            words = del3.get("signal_words", [])
            if any(w in words for w in ["alliance","tension","crisis","tariff","sanction"]):
                triggered = True
                severity = "high"
        
        if triggered:
            signals.append({"trigger": trigger, "severity": severity, "description": description,
                          "timestamp": datetime.now().isoformat()})
    
    # GDELT signal words
    del3 = del_data.get("del3", {})
    signal_count = del3.get("event_count", 0)
    signal_words = del3.get("signal_words", [])
    if signal_count > del3.get("threshold", 50):
        signals.append({"trigger": "event_surge", "severity": "medium",
                      "description": f"事件脉冲超阈值: {signal_count}条 > {del3.get('threshold', 50)}条",
                      "keywords": signal_words[:5], "timestamp": datetime.now().isoformat()})
    
    # Tone check: very negative tone = high conflict signal
    avg_tone = del3.get("avg_tone", 0)
    if avg_tone < -3.0:
        signals.append({"trigger": "negative_tone", "severity": "high",
                      "description": f"全球叙事情绪极负面: tone={avg_tone}", "timestamp": datetime.now().isoformat()})
    
    return signals


# ===== ENGINE 3: Consistency Checker =====

def check_consistency(subject_code, identity_output, signals):
    """Check if multiple signals point in the same direction.
    
    Key insight: Multiple anomalies in the same direction = structural symptom.
    Scattered anomalies = independent noise.
    """
    params = identity_output.get("params", {})
    directions = {}
    for k, v in params.items():
        d = v.get("direction", "→")
        if d not in directions:
            directions[d] = []
        directions[d].append(k)
    
    alert_signals = [s for s in signals if s.get("severity") in ("high", "medium")]
    
    consistency = "stable"
    if len(alert_signals) >= 3:
        dirs = set()
        for k, v in params.items():
            if v.get("direction") in ("↑", "↓"):
                dirs.add(v["direction"])
        if len(dirs) == 1 and len(alert_signals) >= 3:
            consistency = "structural_shift"
        elif len(dirs) > 1:
            consistency = "mixed_signals"
    
    return {
        "consistency": consistency,
        "direction_distribution": directions,
        "signal_alignment": len(alert_signals),
        "diagnosis": "多信号同向=结构性变化" if consistency == "structural_shift" else "信号分散=独立噪音" if consistency == "mixed_signals" else "正常波动"
    }


# ===== ENGINE 4: SUL Scorer =====

def score_sul(subject_code, identity_output, signals, consistency_output):
    """Score Strategic Uncertainty Layer dimensions based on engine outputs."""
    params = identity_output.get("params", {})
    
    direction_changes = sum(1 for k, v in params.items() if v.get("direction") in ("↑", "↓"))
    param_count = max(len(params), 1)
    
    intent_uncertainty = min(0.8, 0.4 + direction_changes * 0.05)
    capability_uncertainty = min(0.8, 0.3 if identity_output.get("dna", {}).get("d3") == "高" else 0.6)
    execution_uncertainty = 0.5 + (len(signals) * 0.02)
    reaction_uncertainty = min(0.9, 0.5 + (len(signals) * 0.03))
    opaque_risk = 0.5
    
    confidence = 1 - (intent_uncertainty + capability_uncertainty + execution_uncertainty + reaction_uncertainty + opaque_risk) / 5
    
    return {
        "intent": round(intent_uncertainty, 2),
        "capability": round(capability_uncertainty, 2),
        "execution": round(execution_uncertainty, 2),
        "reaction": round(reaction_uncertainty, 2),
        "opaque": round(opaque_risk, 2),
        "confidence": round(confidence, 2)
    }


# ===== RUN =====

def run_engine(subject_code=None):
    """Main engine runner."""
    actors = load_actors()
    del_data = load_del_data()
    
    if not actors:
        return {"status": "error", "message": "No actor data. Run construct_bridge.py export first."}
    
    targets = [subject_code] if subject_code else list(actors.keys())
    results = {}
    
    for code in targets:
        actor = actors.get(code)
        if not actor:
            continue
        
        sys.stdout.write(f"[ENGINE] Processing {code}...\n")
        
        identity = interpret_identity(code, actor, del_data.get("del2", {}))
        signals = detect_signals(code, identity, del_data)
        consistency = check_consistency(code, identity, signals)
        sul = score_sul(code, identity, signals, consistency)
        
        results[code] = {
            "timestamp": datetime.now().isoformat(),
            "identity": identity,
            "signals": signals,
            "consistency": consistency,
            "sul": sul
        }
    
    output_path = Path(__file__).parent / "data" / "engine_output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, cls=CustomEncoder)
    
    sys.stdout.write(f"[ENGINE] Output → {output_path}\n")
    return results


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else None
    run_engine(code)
