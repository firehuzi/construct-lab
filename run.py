#!/usr/bin/env python3
"""
ConStruct Engine v4.0 — Master Runner
Usage:
  python run.py full       → pipeline + engine + report
  python run.py engine     → engine only (on existing data)
  python run.py radar      → generate radar data for dashboard
  python run.py watch      → check for signal alerts
"""

import subprocess
import sys
import json
from pathlib import Path
BASE = Path(__file__).parent


def run_pipeline():
    """Run data collection pipeline."""
    print("=" * 50)
    print("  STEP 1: Data Pipeline (DEL-2 + DEL-3)")
    print("=" * 50)
    subprocess.run([sys.executable, str(BASE / "pipeline.py")], check=False)


def run_engine(subject=None):
    """Run analysis engine."""
    print("\n" + "=" * 50)
    print("  STEP 2: Analysis Engine")
    print("=" * 50)
    engine_path = str(BASE / "engine.py")
    cmd = [sys.executable, engine_path]
    if subject:
        cmd.append(subject)
    subprocess.run(cmd, check=False)


def generate_radar():
    """Generate radar dashboard data."""
    engine_out = BASE / "data" / "engine_output.json"
    if not engine_out.exists():
        print("[RADAR] No engine output found. Run 'engine' first.")
        return
    
    with open(engine_out, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    radar_data = []
    for code, data in results.items():
        identity = data.get("identity", {})
        sul = data.get("sul", {})
        consistency = data.get("consistency", {})
        signals = data.get("signals", [])
        
        radar_data.append({
            "code": code,
            "direction": sum(1 for k, v in identity.get("params", {}).items() if v.get("direction") == "↑"),
            "direction_down": sum(1 for k, v in identity.get("params", {}).items() if v.get("direction") == "↓"),
            "signals": len(signals),
            "signal_high": len([s for s in signals if s.get("severity") in ("critical", "high")]),
            "sul_confidence": sul.get("confidence", 0),
            "consistency": consistency.get("consistency", "stable"),
            "timestamp": data.get("timestamp", "")
        })
    
    radar_path = BASE / "data" / "radar_data.json"
    with open(radar_path, "w", encoding="utf-8") as f:
        json.dump(radar_data, f, ensure_ascii=False, indent=2)
    
    print(f"[RADAR] Generated → {radar_path} ({len(radar_data)} subjects)")


def print_report():
    """Print a readable report."""
    engine_out = BASE / "data" / "engine_output.json"
    if not engine_out.exists():
        print("No engine output found.")
        return
    
    with open(engine_out, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    print("\n" + "=" * 60)
    print("  ConStruct Engine v4.0 — System Report")
    print("=" * 60)
    
    for code, data in results.items():
        identity = data.get("identity", {})
        sul = data.get("sul", {})
        consistency = data.get("consistency", {})
        signals = data.get("signals", [])
        
        print(f"\n--- {code}: {identity.get('dna', {}).get('d1', '?')} ---")
        print(f"  DNA: {identity.get('dna', {})}")
        print(f"  Consistency: {consistency.get('consistency', '?')} ({consistency.get('diagnosis', '')})")
        print(f"  Signals: {len(signals)} ({len([s for s in signals if s.get('severity') in ('critical','high')])} high/critical)")
        print(f"  SUL Confidence: {sul.get('confidence', '?')}")
        print(f"  Params:")
        for k, v in identity.get("params", {}).items():
            print(f"    {k}: {v.get('value', 0):.1f} {v.get('direction', '→')} ({v.get('change_pct', 0)}%)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "full":
        run_pipeline()
        run_engine()
        generate_radar()
        print_report()
    elif cmd == "engine":
        subject = sys.argv[2] if len(sys.argv) > 2 else None
        run_engine(subject)
        generate_radar()
        print_report()
    elif cmd == "radar":
        generate_radar()
    elif cmd == "report":
        print_report()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
