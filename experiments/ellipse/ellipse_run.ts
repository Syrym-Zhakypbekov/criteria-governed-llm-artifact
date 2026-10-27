// EXP-ELLIPSE runner (synthetic-free public data, CC BY-NC-SA 4.0). Reads jobs.json, calls the production Gemini wrapper
// (model chosen by GEMINI_CASCADE_ANSWER), 6 calls in parallel, appends one JSON line per job to OUT (resumable).
import { geminiText } from "@/lib/gemini";
import { parseLooseJson } from "@/apps/legal/lib/jrd-extract";
import { readFileSync, appendFileSync, existsSync } from "node:fs";

const JOBS = process.env.JOBS!, OUT = process.env.OUT!, CONC = Number(process.env.CONC || 6);
const { jobs } = JSON.parse(readFileSync(JOBS, "utf8")) as { jobs: { id: string; cfg: string; rep: number; prompt: string }[] };
const done = new Set(existsSync(OUT) ? readFileSync(OUT, "utf8").trim().split("\n").filter(Boolean).map((l) => { const j = JSON.parse(l); return `${j.id}|${j.cfg}|${j.rep}`; }) : []);
const todo = jobs.filter((j) => !done.has(`${j.id}|${j.cfg}|${j.rep}`));
console.log("todo", todo.length, "of", jobs.length);
let i = 0;
async function worker() {
  while (i < todo.length) {
    const j = todo[i++]; const t0 = Date.now();
    try {
      const raw = await geminiText(j.prompt, { tier: "answer", json: true, maxTokens: 1024, caller: "research.ellipse" });
      appendFileSync(OUT, JSON.stringify({ id: j.id, cfg: j.cfg, rep: j.rep, out: parseLooseJson(raw), ms: Date.now() - t0 }) + "\n");
    } catch (e) {
      appendFileSync(OUT, JSON.stringify({ id: j.id, cfg: j.cfg, rep: j.rep, error: String((e as Error).message).slice(0, 200), ms: Date.now() - t0 }) + "\n");
    }
  }
}
Promise.all(Array.from({ length: CONC }, worker)).then(() => console.log("DONE"));
