"use client";

import { useState } from "react";
import { Forest, Heatmap, RateBars, Select, Seg } from "@/components/charts";
import { GOAL_SHORT, LANG_SCRIPT, MODEL_NAMES, pct, study, type Cond, type Pool, type Rule, type Split } from "@/lib/data";

const SPLITS = [{ value: "heldout" as Split, label: "Held-out (sealed)" }, { value: "dev" as Split, label: "Development" }];
const RULES = [{ value: "strict_all" as Rule, label: "Headline rule" }, { value: "all" as Rule, label: "Registered rule" }];
const CONDS = [{ value: "A" as Cond, label: "Without defense (A)" }, { value: "B" as Cond, label: "With defense (B)" }];
const GOALS = study.goals.map((g) => g.label);
const short = (g: string) => GOAL_SHORT[g] ?? g;

export default function Results() {
  const [split, setSplit] = useState<Split>("heldout");
  const [rule, setRule] = useState<Rule>("strict_all");
  return (
    <>
      <div className="controls sticky">
        <Seg label="Which attacks" value={split} options={SPLITS} onChange={setSplit} />
        <Seg label="Scoring" value={rule} options={RULES} onChange={setRule} />
        <span className="small" style={{ maxWidth: "34ch" }}>
          {split === "heldout"
            ? "Families sealed until the defense was frozen: the honest test."
            : "Families the guard was written from: flattering to B."}
        </span>
      </div>
      <Overall split={split} rule={rule} />
      <ByGoal split={split} rule={rule} />
      <Paired split={split} />
      <HeadToHead split={split} />
      <Language rule={rule} />
      <Surface split={split} rule={rule} />
    </>
  );
}

function Overall({ split, rule }: { split: Split; rule: Rule }) {
  const rows = study.overall[`${rule}|${split}`];
  return (
    <>
      <h3 id="overall">Share of attacks that worked, by model</h3>
      <div className="legend"><span><i style={{ background: "var(--a)" }} />Without defense (A)</span><span><i style={{ background: "var(--b)" }} />With defense (B)</span><span>Line: 95% range</span></div>
      <RateBars title="Attack success by model and condition" groups={MODEL_NAMES}
        series={[{ key: "A", label: "Without defense", color: "var(--a)" }, { key: "B", label: "With defense", color: "var(--b)" }]}
        get={(m, c) => rows.find((r) => r.model === m && r.cond === c)} />
      <p className="caption">{rows[0].n} attacks per bar. Lower is better. Every model passed the normal-request bar (at least 27 of 30) before its attack results counted.</p>
    </>
  );
}

function ByGoal({ split, rule }: { split: Split; rule: Rule }) {
  const a = study.byGoal[`${rule}|${split}|A`], b = study.byGoal[`${rule}|${split}|B`];
  return (
    <>
      <h3 id="goals">What the attacker wanted, and what still got through</h3>
      <div className="tablewrap">
        <table className="t matrix">
          <thead><tr><th>Goal</th>{MODEL_NAMES.map((m) => <th key={m} className="n">{m}</th>)}</tr></thead>
          <tbody>
            {study.goals.map((g) => (
              <tr key={g.key}>
                <td><b>{short(g.label)}</b><br /><span className="small">{g.plain}</span></td>
                {MODEL_NAMES.map((m) => {
                  const x = a.find((r) => r.model === m && r.goal === g.label)!, y = b.find((r) => r.model === m && r.goal === g.label)!;
                  return (
                    <td key={m} className="n cellv" title={`${x.count}/${x.n} without, ${y.count}/${y.n} with the defense`}>
                      {x.count} → <span className={y.count === 0 ? "zero" : y.count >= x.count ? "worse" : ""}>{y.count}</span>
                      <span className="small"> /{x.n}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">Attacks that worked without → with the defense. Teal zeros are goals the permission checks in code removed on every model. Violet marks a goal that didn&apos;t fall.</p>
    </>
  );
}

function Paired({ split }: { split: Split }) {
  const [model, setModel] = useState(MODEL_NAMES[0]);
  const rows = study.paired[`${split}|${model}`];
  const any = rows.find((r) => r.key === "ANY")!;
  const att = rows.filter((r) => r.kind === "attack");
  return (
    <>
      <h3 id="paired">Did the defense help? Each attack compared with itself</h3>
      <p>A and B ran on exactly the same attacks, so every attack is either fixed by B, broken by B, or unchanged.</p>
      <div className="controls"><Seg label="Model" value={model} options={MODEL_NAMES.map((m) => ({ value: m, label: m }))} onChange={setModel} /></div>
      <p className="lede" style={{ marginTop: "0.6rem" }}>
        With the defense on, {model} stopped <b>{any.fixed}</b> attacks that had worked before and let through <b>{any.broke}</b> that hadn&apos;t. The success rate fell by {any.diff.toFixed(1)} percentage points (95% range {any.lo.toFixed(1)} to {any.hi.toFixed(1)}).
      </p>
      <Forest title="Change in attack success with the defense, by goal" leftLabel="Fewer attacks worked with B" rightLabel="More attacks worked with B"
        rows={att.map((r) => ({ label: r.key === "ANY" ? "Any goal" : short(r.metric), diff: -r.diff, lo: -r.hi, hi: -r.lo, note: `${r.a} → ${r.b}` }))} />
      <p className="caption">Dot: change in percentage points; line: 95% range. A filled dot means the range doesn&apos;t cross zero.</p>
    </>
  );
}

const H2H = [{ value: "ANY", label: "Any goal" }, ...study.goals.map((g) => ({ value: g.key, label: short(g.label) })), { value: "LOOKALIKE_PASS", label: "Normal look-alikes passed" }];
function HeadToHead({ split }: { split: Split }) {
  const [cond, setCond] = useState<Cond>("A");
  const [metric, setMetric] = useState("ANY");
  const rows = study.headToHead[`${split}|${cond}|${metric}`];
  const higherBetter = metric === "LOOKALIKE_PASS";
  return (
    <>
      <h3 id="h2h">Head to head: which model was fooled less?</h3>
      <div className="controls">
        <Seg label="Condition" value={cond} options={CONDS} onChange={setCond} />
        <Select label="Measure" value={metric} options={H2H} onChange={setMetric} />
      </div>
      <Forest title="Model-versus-model differences" leftLabel={higherBetter ? "Second model passed more" : "First model fooled less"} rightLabel={higherBetter ? "First model passed more" : "Second model fooled less"}
        rows={rows.map((r) => ({ label: r.pair.replace(" vs ", " vs "), diff: r.diff, lo: r.lo, hi: r.hi, note: r.verdict }))} />
      <p className="caption">First model minus second, paired on identical attacks. Not adjusted for multiple comparisons, so treat results marked borderline as suggestive.</p>
    </>
  );
}

function Language({ rule }: { rule: Rule }) {
  const [cond, setCond] = useState<Cond>("B");
  const [metric, setMetric] = useState("ANY");
  const [pool, setPool] = useState<Pool>("both");
  const rows = study.byLanguage[`${rule}|${pool}|${cond}|${metric}`];
  const cols = study.languages.map((l) => l);
  return (
    <>
      <h3 id="language">By language</h3>
      <div className="langs">
        {study.languages.map((l) => <div key={l}><b className={l === "Devanagari Hindi" ? "deva" : ""}>{LANG_SCRIPT[l].native}</b><span>{LANG_SCRIPT[l].note}</span></div>)}
      </div>
      <div className="controls">
        <Seg label="Condition" value={cond} options={CONDS} onChange={setCond} />
        <Select label="Goal" value={metric} options={[{ value: "ANY", label: "Any goal" }, ...study.goals.map((g) => ({ value: g.key, label: short(g.label) }))]} onChange={setMetric} />
        <Select label="Attacks" value={pool} options={[{ value: "both" as Pool, label: "Held-out + development" }, { value: "heldout" as Pool, label: "Held-out only" }, { value: "dev" as Pool, label: "Development only" }]} onChange={setPool} />
      </div>
      <Heatmap title="Attack success by language and model" rows={MODEL_NAMES} cols={cols}
        get={(m, l) => rows.find((r) => r.model === m && r.language === l)} />
      <p className="caption">Darker means more attacks worked. With the defense on, Devanagari Hindi is the weakest variant for every model, mostly because a planted policy value written in it gets repeated (choose &ldquo;Planted wrong policy&rdquo;). Cells are small, so the pattern across all three models matters more than any one cell.</p>
    </>
  );
}

function Surface({ split, rule }: { split: Split; rule: Rule }) {
  const [cond, setCond] = useState<Cond>("A");
  const [model, setModel] = useState(MODEL_NAMES[0]);
  const rows = study.bySurface[`${rule}|${split}|${cond}|${model}`];
  return (
    <>
      <h3 id="surface">Where the instruction was hidden</h3>
      <div className="controls">
        <Seg label="Model" value={model} options={MODEL_NAMES.map((m) => ({ value: m, label: m }))} onChange={setModel} />
        <Seg label="Condition" value={cond} options={CONDS} onChange={setCond} />
      </div>
      <Heatmap title="Attack success by goal and injection surface" rows={GOALS.map(short)} cols={study.surfaces}
        get={(g, s) => rows.find((r) => short(r.goal) === g && r.surface === s)} />
      <p className="caption">The customer&apos;s own message is a direct attack; tickets, notes and policy documents are indirect, read by the bot while an ordinary customer asks an ordinary question. Blocking a handoff isn&apos;t tested from the customer&apos;s own message.</p>
    </>
  );
}
