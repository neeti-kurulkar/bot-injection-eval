import raw from "@/data/study.json";

export type Rule = "strict_all" | "all";
export type Split = "heldout" | "dev";
export type Cond = "A" | "B";
export type Pool = "both" | "heldout" | "dev";

export interface Cell { count: number; n: number; rate: number; lo: number; hi: number }
export interface ModelInfo {
  slug: string; name: string; where: string;
  benign: { count: number; n: number };
  benignByLanguage: Record<string, number>;
  lookalikes: Record<string, number>;
  falseBlocksB: number;
  protocol: Record<string, number>;
  secondsPerScenario: Record<string, number>;
  guardRestricted: Record<string, number>;
  spend: string;
}
export interface PairedRow { key: string; metric: string; a: string; b: string; diff: number; lo: number; hi: number; fixed: number; broke: number; kind: string; reading: string }
export interface H2HRow { pair: string; x: string; y: string; first: string; second: string; diff: number; lo: number; hi: number; onlyFirst: number; onlySecond: number; verdict: string }

interface Study {
  models: ModelInfo[];
  overall: Record<string, (Cell & { model: string; cond: Cond })[]>;
  byGoal: Record<string, (Cell & { model: string; goal: string })[]>;
  byLanguage: Record<string, (Cell & { model: string; language: string })[]>;
  bySurface: Record<string, (Cell & { goal: string; surface: string })[]>;
  paired: Record<string, PairedRow[]>;
  headToHead: Record<string, H2HRow[]>;
  ablation: (Cell & { variant: string; goal: string })[];
  facts: {
    variants: { name: string; g1: { b: number; v: number; n: number }; any: { b: number; v: number; n: number; diff: number; lo: number; hi: number; fixed: number; broke: number }; lookalikes: { b: number; v: number }; calls: [number, number] }[];
    details: { toolUsedB_facts: number; toolUsedCheck: number; scenarios: number; correctValue: { B: number; facts: number; check: number }; g1Flagged: number; g1Fallback: number; cardMisfires: number; cardTriggered: number };
  };
  goals: { key: string; label: string; plain: string }[];
  languages: string[];
  surfaces: string[];
  judgeCheck: { hostedVerdicts: number; hostedCorrect: number; numericFlags: number; numericCorrect: number };
}

export const study = raw as unknown as Study;
export const MODEL_NAMES = study.models.map((m) => m.name);

export const GOAL_SHORT: Record<string, string> = {
  "G1 planted wrong policy": "Planted wrong policy",
  "G2 other customer's balance": "Another customer's balance",
  "G3 handoff blocked": "Handoff blocked",
  "G4 card / contact change": "Card or contact change",
  "G5 unrequested transfer": "Unrequested transfer",
};

export const LANG_SCRIPT: Record<string, { native: string; note: string }> = {
  English: { native: "English", note: "The baseline language" },
  Hinglish: { native: "Hinglish", note: "Hindi and English mixed, Latin letters" },
  "Devanagari Hindi": { native: "हिन्दी", note: "Hindi in Devanagari script" },
  "Romanized Hindi": { native: "Hindi", note: "Hindi in Latin letters" },
};

export const pct = (x: number | null | undefined, d = 1) => (x === null || x === undefined ? "–" : `${x.toFixed(d)}%`);
export const signed = (x: number, d = 1) => `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`;
