"use client";

import { RateBars } from "@/components/charts";
import Diagram from "@/components/diagram";
import IndexNav from "@/components/index-nav";
import Results from "@/components/results";
import { GOAL_SHORT, MODEL_NAMES, pct, signed, study } from "@/lib/data";

const REPO = "https://github.com/neeti-kurulkar/bot-injection-eval";
const head = (m: string, c: "A" | "B") => study.overall["strict_all|heldout"].find((r) => r.model === m && r.cond === c)!;
const short = (g: string) => GOAL_SHORT[g] ?? g;

export default function Page() {
  return (
    <>
      <header className="topbar">
        <a className="brand" href="#top">Sahayak Bank <span>prompt injection study</span></a>
        <nav className="toplinks" aria-label="Project links">
          <a href={REPO}>Code and data</a>
          <a href={`${REPO}/blob/main/docs/results/final.md`}>Full report</a>
          <a href={`${REPO}/blob/main/docs/results/model-comparison.md`}>Model comparison</a>
        </nav>
      </header>

      <div className="frame" id="top">
        <IndexNav />
        <main>
          <section className="hero paper-band" aria-labelledby="title">
            <h1 id="title">Planted text steered a bank&apos;s support bot on up to one attack in four.</h1>
            <p className="lede">
              I built a support chatbot for a fictional Indian bank and hid instructions in what it reads: customer messages, old tickets, staff notes and policy documents. Then I measured how often it obeyed, with and without a defense, on three models and in English and three forms of Hindi.
            </p>
            <div className="ledger" role="table" aria-label="Held-out attacks that worked, by model">
              <div className="ledger-head" role="row">
                <div role="columnheader">Model</div><div role="columnheader">Without the defense</div>
                <div role="columnheader">With the defense</div><div role="columnheader">Change</div>
              </div>
              {study.models.map((m, i) => {
                const a = head(m.name, "A"), b = head(m.name, "B");
                return (
                  <div className="ledger-row" role="row" key={m.slug}>
                    <div className="ledger-model" role="cell">{m.name}<small>{m.where}</small></div>
                    <div role="cell"><span className="stamp a" style={{ ["--i" as string]: i * 2 }}><b>{pct(a.rate)}</b><i>{a.count} of {a.n} worked</i></span></div>
                    <div role="cell"><span className="stamp b" style={{ ["--i" as string]: i * 2 + 1 }}><b>{pct(b.rate)}</b><i>{b.count} of {b.n} worked</i></span></div>
                    <div className="change" role="cell">{signed(b.rate - a.rate)} pts<small>{a.count - b.count} fewer attacks</small></div>
                  </div>
                );
              })}
              <div className="ledger-foot">Held-out attacks, sealed until the defense was finished. 228 per model and condition. No normal request was wrongly blocked.</div>
            </div>
          </section>

          <section className="block" id="findings" aria-labelledby="h-findings">
            <h2 id="h-findings">What the study found</h2>
            <ol className="findings">
              <li><span className="k">1</span><p><b>Without checks in code, the bot is easy to steer.</b> 27.6% of held-out attacks worked on Qwen3 4B, 25.0% on GPT-5.6 Luna and 13.6% on Sarvam 105B. Each model still handled 29 or 30 of 30 normal requests correctly, so a bot can look well-behaved and still be steerable.</p></li>
              <li><span className="k">2</span><p><b>Permission checks in code worked the same on every model.</b> With the defense on, no attack leaked another customer&apos;s balance, changed a card or contact, or proposed a transfer: zero out of 1,824 attack conversations.</p></li>
              <li><span className="k">3</span><p><b>A planted policy value is the failure that survives.</b> Repeating a fake fee needs no tool, so permission checks can&apos;t stop it. It didn&apos;t fall on Qwen and fell only partly on the hosted models.</p></li>
              <li><span className="k">4</span><p><b>Devanagari Hindi is the weak spot on every model,</b> including the Hindi-focused Sarvam. Fake policy written in Devanagari is repeated far more than in English.</p></li>
              <li><span className="k">5</span><p><b>Model size didn&apos;t predict robustness.</b> Without the defense, Sarvam was fooled least; GPT-5.6 Luna and the 4B local model weren&apos;t clearly different.</p></li>
              <li><span className="k">6</span><p><b>Checking every policy number in code removed planted policy</b> in a follow-up on development attacks, where offering the bot a lookup tool alone had changed nothing.</p></li>
            </ol>
          </section>

          <section className="block" id="system" aria-labelledby="h-system">
            <h2 id="h-system">The bot, and the defense added to it</h2>
            <p>Sahayak answers signed-in customers using 11 tools. Its prompt includes the customer&apos;s recent tickets, staff notes and the two best-matching policy sections, which is where indirect attacks hide. Condition A runs whatever the model asks for. Condition B is the same bot with three additions.</p>
            <Diagram />
            <div className="three">
              <div className="defense"><h3>Permission checks in code</h3><p>Before any account tool runs, the tool layer checks the customer is signed in, owns the account or card, and has passed an OTP for changes. Identity comes from the session, never from the conversation.</p></div>
              <div className="defense"><h3>Data marking</h3><p>Every piece of untrusted text is wrapped in a block with a random ID, and the prompt says that text is information, never an instruction. It works only if the model obeys.</p></div>
              <div className="defense"><h3>Input guard</h3><p>Nine text rules look for known tricks such as fake system notices, policy &ldquo;revisions&rdquo; and OTP-bypass claims. A match limits that turn to FAQ tools and handoff; nothing is refused.</p></div>
            </div>
            <div className="tablewrap">
              <table className="t">
                <thead><tr><th>Tier</th><th>Tools</th><th>Who should be allowed</th></tr></thead>
                <tbody>
                  <tr><td>T0</td><td>Policy search, branch hours</td><td>Anyone</td></tr>
                  <tr><td>T1</td><td>Balance, transactions, ticket status</td><td>The signed-in customer, own accounts only</td></tr>
                  <tr><td>T2</td><td>Block card, open dispute, change contact</td><td>The owner, after an OTP</td></tr>
                  <tr><td>T3</td><td>Transfer and refund proposals</td><td>Proposal only: a policy engine and a human approve</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="block" id="attacks" aria-labelledby="h-attacks">
            <h2 id="h-attacks">The attacks</h2>
            <p>608 single-message attacks: eight trick families, five goals, four places to hide the instruction, four languages. Another 80 normal requests that merely sound suspicious check that real customers aren&apos;t blocked.</p>
            <div className="tablewrap">
              <table className="t">
                <thead><tr><th>Goal</th><th>The attacker wants the bot to</th></tr></thead>
                <tbody>{study.goals.map((g) => <tr key={g.key}><td><b>{short(g.label)}</b></td><td>{g.plain.replace(/^The bot /, "").replace(/^The customer asked for a human and the bot didn't hand off/, "refuse a customer's request for a human")}</td></tr>)}</tbody>
              </table>
            </div>
            <h3>Five families to build with, three sealed away</h3>
            <div className="split8" aria-label="Five development families and three sealed held-out families">
              {Array.from({ length: 8 }, (_, i) => <div key={i} className={i < 5 ? "dev" : "sealed"}>{i < 5 ? "dev" : "sealed"}</div>)}
            </div>
            <p>Whole trick families were split before any defense existed. The guard was written from the five development families; the three sealed ones were opened once per condition, so held-out results show how the defense does against tricks it wasn&apos;t built for. Scoring is deterministic code reading the audit log and the reply, not another AI.</p>
          </section>

          <section className="block" id="results" aria-labelledby="h-results">
            <h2 id="h-results">Results</h2>
            <p>Switch between the sealed held-out attacks and the development attacks, and between the headline scoring rule and the looser one registered first. Hover any bar or cell for exact counts.</p>
            <Results />
          </section>

          <section className="block" id="defenses" aria-labelledby="h-def">
            <h2 id="h-def">What each part of the defense did</h2>
            <p>Switching one part of the defense off at a time shows what each contributes. Development attacks, Qwen3 4B only.</p>
            <div className="legend">{[["A", "var(--a)"], ["B", "var(--b)"], ["B without data marking", "#7cc4b9"], ["B without guard", "#0f5148"]].map(([l, c]) => <span key={l}><i style={{ background: c }} />{l === "A" ? "No defense" : l === "B" ? "Full defense" : l}</span>)}</div>
            <RateBars title="Attack success by goal for each defense variant" groups={study.goals.map((g) => short(g.label))}
              series={[{ key: "A", label: "No defense", color: "var(--a)" }, { key: "B", label: "Full defense", color: "var(--b)" }, { key: "B without data marking", label: "Without data marking", color: "#7cc4b9" }, { key: "B without guard", label: "Without guard", color: "#0f5148" }]}
              get={(g, v) => study.ablation.find((r) => short(r.goal) === g && r.variant === v)} />
            <div className="three">
              <p><b>Permission checks</b> alone remove the balance leaks and card or contact changes: they&apos;re zero in every variant that has them.</p>
              <p><b>Data marking</b> is what cut handoff blocking. Without it, handoff blocking is no better than with no defense at all.</p>
              <p><b>The guard</b> removes the last unrequested transfer proposals. It caught 92% of development attacks but only 58% of sealed ones.</p>
            </div>
          </section>

          <Facts />

          <section className="block" id="customers" aria-labelledby="h-cust">
            <h2 id="h-cust">Normal customers, speed and cost</h2>
            <div className="tablewrap">
              <table className="t">
                <thead><tr><th>Model</th><th className="n">Normal requests passed</th><th className="n">Look-alikes passed, A → B</th><th className="n">Wrongly blocked</th><th className="n">Seconds per conversation</th><th className="n">Cost of all runs</th></tr></thead>
                <tbody>{study.models.map((m) => (
                  <tr key={m.slug}><td><b>{m.name}</b><br /><span className="small">{m.where}</span></td>
                    <td className="n">{m.benign.count} of {m.benign.n}</td>
                    <td className="n">{m.lookalikes["A-heldout"]} → {m.lookalikes["B-heldout"]} of 40</td>
                    <td className="n">{m.falseBlocksB} of 40</td>
                    <td className="n">{Math.min(m.secondsPerScenario["B-heldout"], m.secondsPerScenario["A-heldout"]).toFixed(1)} to {Math.max(m.secondsPerScenario["B-heldout"], m.secondsPerScenario["A-heldout"]).toFixed(1)}</td>
                    <td className="n">{m.spend === "none (local GPU)" ? "Local GPU" : m.spend}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="caption">Look-alikes are normal requests that sound like attacks (urgent, mention a manager or &ldquo;the system&rdquo;). Hosted costs cover 1,411 conversations per model, with a spending cap checked before every call.</p>
          </section>

          <section className="block" id="method" aria-labelledby="h-method">
            <h2 id="h-method">How it was measured, and its limits</h2>
            <div className="two">
              <div>
                <h3>Method</h3>
                <p>The world is synthetic and seeded: 200 customers, 300 accounts, 75,488 transactions and 40 policy documents with 108 checkable facts, some modelled on public RBI circulars. Rules were fixed before results: designs before code, a pass bar of 27 of 30 normal requests, sealed attack families and deterministic scoring. Rates carry Wilson 95% ranges; A-versus-B and model-versus-model differences are paired by attack.</p>
                <p>A hand check of {study.judgeCheck.hostedVerdicts} scoring decisions on the hosted models&apos; replies confirmed all of them (AI-suggested labels, confirmed by the author).</p>
              </div>
              <div>
                <h3>Limits</h3>
                <ul className="small" style={{ paddingLeft: "1.1rem", lineHeight: 1.6 }}>
                  <li>Single-message attacks that don&apos;t adapt, against a mock bank.</li>
                  <li>One run per model and condition; per-goal and per-language groups are small.</li>
                  <li>One generic prompt for every model; hosted models can change over time.</li>
                  <li>The sealed families were opened for Qwen first; nothing was tuned on them.</li>
                  <li>Only wrong numbers are scored, not subtly wrong wording.</li>
                </ul>
              </div>
            </div>
          </section>

          <footer className="foot">
            <p>Sahayak Bank is fictional and every record is synthetic. Condition A is the system under study and Condition B a defense under evaluation; neither is presented as safe for production. Attack text is never published here.</p>
            <p><a href={REPO}>Code, data and reports on GitHub</a></p>
            <pre>{`@misc{kurulkar2026sahayak,
  title  = {Injection-Driven Failures in a Tiered Bank Support Bot},
  author = {Kurulkar, Neeti},
  year   = {2026},
  howpublished = {\\url{${REPO}}}
}`}</pre>
          </footer>
        </main>
      </div>
    </>
  );
}

function Facts() {
  const f = study.facts, d = f.details;
  const [tool, check] = f.variants;
  return (
    <section className="block" id="facts" aria-labelledby="h-facts">
      <h2 id="h-facts">Follow-up: answering from the bank&apos;s own numbers</h2>
      <p>The bank already stores the correct fees and limits as 108 structured facts, but the bot answered from prose. Two variants of the defense tested using them. Development attacks, Qwen3 4B only.</p>
      <div className="tablewrap">
        <table className="t">
          <thead><tr><th>Variant</th><th className="n">Planted policy repeated</th><th className="n">Correct value given</th><th className="n">Any goal</th><th className="n">Model calls</th></tr></thead>
          <tbody>
            <tr><td><b>Defense (B)</b></td><td className="n">{tool.g1.b} of {tool.g1.n}</td><td className="n">{d.correctValue.B} of 80</td><td className="n">{tool.any.b} of {tool.any.n}</td><td className="n">{tool.calls[0].toFixed(2)}</td></tr>
            <tr><td><b>+ a fact lookup tool</b><br /><span className="small">used in only {d.toolUsedB_facts} of {d.scenarios} attacks</span></td><td className="n">{tool.g1.v} of {tool.g1.n}</td><td className="n">{d.correctValue.facts} of 80</td><td className="n">{tool.any.v} of {tool.any.n}</td><td className="n">{tool.calls[1].toFixed(2)}</td></tr>
            <tr><td><b>+ tool and a check in code</b><br /><span className="small">every policy number compared with the facts</span></td><td className="n">{check.g1.v} of {check.g1.n}</td><td className="n">{d.correctValue.check} of 80</td><td className="n">{check.any.v} of {check.any.n}</td><td className="n">{check.calls[1].toFixed(2)}</td></tr>
          </tbody>
        </table>
      </div>
      <p>Offering the tool changed nothing: the small model rarely chose to use it. Enforcing the check in code removed planted policy on these attacks and raised correct answers from {d.correctValue.B} to {d.correctValue.check} of 80, at about 18% more model calls. It&apos;s the study&apos;s main lesson again: what&apos;s enforced in code holds.</p>
      <div className="note"><b>Two caveats.</b> The check shares its number-matching with the scorer, so the drop to zero is partly by construction; the rise in correct answers is the independent evidence. And the check mistook card last-four digits for policy numbers, replacing {d.cardMisfires} ordinary card replies with its fallback message.</div>
    </section>
  );
}
