"use client";

import { useEffect, useState } from "react";

export const SECTIONS = [
  ["findings", "Findings"],
  ["system", "The bot and the defense"],
  ["attacks", "The attacks"],
  ["results", "Results"],
  ["defenses", "What each defense did"],
  ["facts", "Follow-up: structured facts"],
  ["customers", "Normal customers and cost"],
  ["method", "Method and limits"],
] as const;

export default function IndexNav() {
  const [on, setOn] = useState<string>("findings");
  useEffect(() => {
    const els = SECTIONS.map(([id]) => document.getElementById(id)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver((entries) => {
      const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (vis[0]) setOn(vis[0].target.id);
    }, { rootMargin: "-10% 0px -70% 0px" });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return (
    <nav className="index" aria-label="Sections">
      <ol>
        {SECTIONS.map(([id, label]) => (
          <li key={id}><a href={`#${id}`} className={on === id ? "on" : undefined} aria-current={on === id ? "true" : undefined}>{label}</a></li>
        ))}
      </ol>
    </nav>
  );
}
