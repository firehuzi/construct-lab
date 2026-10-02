CEF Lab v3（Vite + React + D3 完整模板）
🚀 技术栈
Vite（构建）
React（UI & 控制层）
Zustand（状态系统）
D3.js（网络/结构可视化）
TypeScript（推荐）
📁 1. 项目结构
cef-lab-v3/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
│
└── src/
    ├── main.tsx
    ├── App.tsx
    │
    ├── core/
    │   ├── cefModel.ts        # 数学模型核心
    │   ├── shockEngine.ts     # 冲击系统
    │   ├── optimizer.ts       # 政策优化
    │   └── forecast.ts       # 预测引擎
    │
    ├── store/
    │   └── useCEFStore.ts     # Zustand状态
    │
    ├── components/
    │   ├── ControlPanel.tsx
    │   ├── MetricsPanel.tsx
    │   └── ShockPanel.tsx
    │
    ├── viz/
    │   └── CEFGraph.tsx       # D3可视化
    │
    └── styles.css
⚙️ 2. package.json
{
  "name": "cef-lab-v3",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^4.5.0",
    "d3": "^7.9.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
⚙️ 3. vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()]
});
🧠 4. CEF 核心模型（纯数学）
export type CountryState = {
  lambda: number;
  f: number;
  k: number;
  shock: number;
};

export function D(s: CountryState) {
  const lambdaEff = s.lambda + s.shock * 0.4;
  return (lambdaEff * (1 + s.k)) / (s.f + 0.1);
}

export function globalD(states: Record<string, CountryState>) {
  return Object.values(states)
    .map(D)
    .reduce((a, b) => a + b, 0) / 3;
}
⚡ 5. Zustand 状态系统
import { create } from "zustand";

type State = {
  time: number;
  speed: number;
  paused: boolean;

  US: any;
  EU: any;
  CN: any;

  tick: () => void;
  toggle: () => void;
  injectShock: (target: string, value: number) => void;
};

export const useCEFStore = create<State>((set, get) => ({
  time: 0,
  speed: 0.3,
  paused: false,

  US: { lambda: 0.75, f: 0.45, k: 0.85, shock: 0 },
  EU: { lambda: 0.65, f: 0.60, k: 0.75, shock: 0 },
  CN: { lambda: 0.55, f: 0.75, k: 0.65, shock: 0 },

  tick: () =>
    set((s) => ({ time: s.time + s.speed })),

  toggle: () =>
    set((s) => ({ paused: !s.paused })),

  injectShock: (target, value) =>
    set((s) => ({
      [target]: {
        ...s[target],
        shock: s[target].shock + value
      }
    }))
}));
🧩 6. React入口
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <App />
);
🧠 7. App 主结构
import { useEffect } from "react";
import { useCEFStore } from "./store/useCEFStore";
import { ControlPanel } from "./components/ControlPanel";
import { MetricsPanel } from "./components/MetricsPanel";
import { CEFGraph } from "./viz/CEFGraph";

export default function App() {
  const { paused, tick } = useCEFStore();

  useEffect(() => {
    const id = setInterval(() => {
      if (!paused) tick();
    }, 30);

    return () => clearInterval(id);
  }, [paused]);

  return (
    <div style={{ display: "flex", gap: 20 }}>
      <ControlPanel />
      <CEFGraph />
      <MetricsPanel />
    </div>
  );
}
🎛️ 8. 控制面板
import { useCEFStore } from "../store/useCEFStore";

export function ControlPanel() {
  const { toggle, injectShock } = useCEFStore();

  return (
    <div style={{ width: 250 }}>
      <h3>CEF Control</h3>

      <button onClick={toggle}>Play / Pause</button>

      <button onClick={() => injectShock("US", 0.3)}>
        US Shock
      </button>

      <button onClick={() => injectShock("EU", 0.3)}>
        EU Shock
      </button>

      <button onClick={() => injectShock("CN", 0.3)}>
        CN Shock
      </button>
    </div>
  );
}
📊 9. D3 网络可视化（核心）
import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { useCEFStore } from "../store/useCEFStore";
import { D } from "../core/cefModel";

export function CEFGraph() {
  const ref = useRef<SVGSVGElement>(null);
  const state = useCEFStore();

  useEffect(() => {
    if (!ref.current) return;

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();

    const nodes = [
      { id: "US", x: 100, y: 200, s: state.US },
      { id: "EU", x: 300, y: 150, s: state.EU },
      { id: "CN", x: 500, y: 250, s: state.CN }
    ];

    svg
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("cx", d => d.x)
      .attr("cy", d => d.y)
      .attr("r", d => 10 + d.s.shock * 5)
      .attr("fill", "#7CFF6B");

    svg
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .attr("x", d => d.x + 10)
      .attr("y", d => d.y)
      .text(d => `${d.id} D:${D(d.s).toFixed(2)}`)
      .attr("fill", "#fff");

  }, [state]);

  return <svg ref={ref} width={600} height={400} />;
}
📈 10. Metrics 面板
import { useCEFStore } from "../store/useCEFStore";
import { D, globalD } from "../core/cefModel";

export function MetricsPanel() {
  const state = useCEFStore();

  return (
    <div style={{ width: 200 }}>
      <h3>Metrics</h3>

      <div>US: {D(state.US).toFixed(2)}</div>
      <div>EU: {D(state.EU).toFixed(2)}</div>
      <div>CN: {D(state.CN).toFixed(2)}</div>

      <hr />

      <div>
        Global: {globalD({
          US: state.US,
          EU: state.EU,
          CN: state.CN
        }).toFixed(2)}
      </div>
    </div>
  );
}
🚀 11. 启动方式
npm install
npm run dev