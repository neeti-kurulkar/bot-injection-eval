/* The system under test, and where each Condition B defense acts. */
export default function Diagram() {
  const box = (x: number, y: number, w: number, h: number, title: string, sub: string, kind: "sys" | "def" = "sys") => (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={6} fill={kind === "def" ? "var(--b-soft)" : "var(--sheet)"} stroke={kind === "def" ? "var(--b)" : "var(--ink)"} strokeWidth={kind === "def" ? 1.5 : 1.2} />
      <text x={x + w / 2} y={y + h / 2 - 2} textAnchor="middle" className="lab" style={{ fontWeight: 600, fontSize: 14 }}>{title}</text>
      <text x={x + w / 2} y={y + h / 2 + 15} textAnchor="middle" className="ax">{sub}</text>
    </g>
  );
  const arrow = (d: string, dashed = false, color = "var(--ink-2)") => (
    <path d={d} fill="none" stroke={color} strokeWidth={1.6} strokeDasharray={dashed ? "5 4" : undefined} markerEnd={dashed ? "url(#ahb)" : "url(#ah)"} />
  );
  return (
    <svg className="chart" viewBox="0 0 760 330" role="img" aria-label="The support bot, and where the three defenses act">
      <title>The support bot, and where the three defenses act</title>
      <defs>
        <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-2)" /></marker>
        <marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--b)" /></marker>
      </defs>
      {box(0, 20, 170, 54, "Customer's message", "where direct attacks sit")}
      {box(0, 100, 170, 66, "Tickets, notes, policies", "where indirect attacks sit")}
      {box(220, 64, 130, 64, "Prompt builder", "role, customer, context")}
      {box(398, 64, 120, 64, "Model", "Qwen, Sarvam or GPT")}
      {box(566, 64, 190, 64, "Tool layer", "11 tools, one audit row each")}
      {box(610, 176, 146, 54, "Mock core bank", "accounts, cards, approvals")}
      {arrow("M170,47 C195,47 195,86 218,90")}
      {arrow("M170,133 C195,133 195,104 218,102")}
      {arrow("M350,96 L396,96")}
      {arrow("M518,88 L564,88")}
      {arrow("M564,106 L520,106")}
      {arrow("M683,128 L683,174")}
      {box(0, 256, 170, 58, "Input guard", "9 rules on untrusted text", "def")}
      {box(212, 256, 160, 58, "Data marking", "untrusted text tagged as data", "def")}
      {box(414, 256, 200, 58, "Permission checks", "owner, sign-in and OTP, in code", "def")}
      {arrow("M85,256 L85,170", true, "var(--b)")}
      {arrow("M292,256 L292,130", true, "var(--b)")}
      {arrow("M540,256 C542,200 585,170 592,132", true, "var(--b)")}
      <text x={756} y={326} textAnchor="end" className="ax">Kept in both conditions: a human approves any money movement, and handoff is always available.</text>
    </svg>
  );
}
