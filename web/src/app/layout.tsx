import type { Metadata, Viewport } from "next";
import { Anek_Devanagari, Anek_Latin, Hind } from "next/font/google";
import "./globals.css";

const anek = Anek_Latin({ subsets: ["latin"], variable: "--font-anek", weight: "variable", axes: ["wdth"] });
const deva = Anek_Devanagari({ subsets: ["devanagari"], variable: "--font-deva", weight: "variable", axes: ["wdth"] });
const hind = Hind({ subsets: ["latin", "devanagari"], variable: "--font-hind", weight: ["400", "500", "600"] });

export const metadata: Metadata = {
  title: "Sahayak Bank: prompt injection study",
  description:
    "How often planted text steers an LLM support bot for a fictional Indian bank, and what stops it. 608 attacks, three models, four language variants.",
};

export const viewport: Viewport = { themeColor: "#EDF2EC" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${anek.variable} ${deva.variable} ${hind.variable}`}>
      <body>{children}</body>
    </html>
  );
}
