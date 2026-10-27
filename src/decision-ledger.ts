// ЖУРНАЛ РЕШЕНИЙ ИИ (0740 ai_decision) — общий для всех модулей. Модель главы 2 диссертации владельца:
// критерии q_i (s — оценка, q — качество/достаточность данных, hard — жёсткий), вето (любой жёсткий провален → решение не принимается
// автоматически), агрегат D(x) = Σ w·q·s / Σ w·q по мягким критериям, шлюз (вето | эскалация | предварительное), окончательное
// решение человека (подтвердил | исправил | отклонил) и разница полей «ИИ → человек». Учёт не роняет основной ответ: ошибки глотаем.
import { q } from "@/db/client";

export type Criterion = { code: string; s: number; q?: number; hard?: boolean; w?: number; note?: string };
export type Gate = { sTotal: number | null; veto: boolean; vetoReason: string | null; escalated: boolean; escalateReason: string | null; state: "provisional" | "escalated" | "vetoed" };
export type FieldDiff = { changed: Array<{ field: string; ai: string; human: string }>; kept: number; filled: string[]; cleared: string[]; total: number };

const clamp01 = (x: unknown) => { const n = Number(x); return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0; };

/** Шлюз Π: вето по жёстким критериям (s < 1), агрегат по мягким, эскалация при низкой уверенности модели или низком D. */
export function gate(criteria: Criterion[], opts: { confidence?: number | null; minConfidence?: number; minScore?: number } = {}): Gate {
  const hardFail = criteria.filter((c) => c.hard && clamp01(c.s) < 1);
  const soft = criteria.filter((c) => !c.hard);
  let num = 0, den = 0;
  for (const c of soft) { const w = c.w ?? 1, qq = c.q == null ? 1 : clamp01(c.q); num += w * qq * clamp01(c.s); den += w * qq; }
  const sTotal = den > 0 ? Math.round((num / den) * 10000) / 10000 : null;
  if (hardFail.length) return { sTotal, veto: true, vetoReason: hardFail.map((c) => c.code).join(","), escalated: true, escalateReason: "veto", state: "vetoed" };
  const reasons: string[] = [];
  if (opts.confidence != null && clamp01(opts.confidence) < (opts.minConfidence ?? 0.6)) reasons.push("low_confidence");
  if (sTotal != null && sTotal < (opts.minScore ?? 0.5)) reasons.push("low_score");
  return { sTotal, veto: false, vetoReason: null, escalated: reasons.length > 0, escalateReason: reasons.join(",") || null, state: reasons.length ? "escalated" : "provisional" };
}

const norm = (v: unknown) => String(v ?? "").replace(/\s+/g, " ").trim();

/** Разница «ИИ → человек» по набору полей: изменено (оба непусты и разные), сохранено как у ИИ, дописано человеком, стёрто человеком. */
export function fieldDiff(ai: Record<string, unknown>, human: Record<string, unknown>, fields?: string[]): FieldDiff {
  const keys = fields ?? Array.from(new Set([...Object.keys(ai), ...Object.keys(human)]));
  const out: FieldDiff = { changed: [], kept: 0, filled: [], cleared: [], total: 0 };
  for (const k of keys) {
    const a = norm(ai[k]), h = norm(human[k]);
    if (!a && !h) continue;
    out.total++;
    if (a && !h) out.cleared.push(k);
    else if (!a && h) out.filled.push(k);
    else if (a.toLowerCase() === h.toLowerCase()) out.kept++;
    else out.changed.push({ field: k, ai: a.slice(0, 200), human: h.slice(0, 200) });
  }
  return out;
}

/** Итог человека по разнице: ни одного изменения → confirmed, иначе revised. */
export function humanState(d: FieldDiff): "confirmed" | "revised" {
  return d.changed.length || d.cleared.length ? "revised" : "confirmed";
}

/** Открыть решение (сразу после ответа ИИ). Возвращает id или null, если запись не удалась. */
export async function openDecision(r: { caller: string; criteria: Criterion[]; aiOutput: Record<string, unknown>; confidence?: number | null; model?: string | null;
  criteriaVersion?: string; actorId?: number | null; minConfidence?: number; minScore?: number }): Promise<{ id: number | null; gate: Gate }> {
  const g = gate(r.criteria, { confidence: r.confidence, minConfidence: r.minConfidence, minScore: r.minScore });
  try {
    const [row] = await q<{ id: number }>(`INSERT INTO ai_decision (caller, criteria_version, criteria, s_total, veto, veto_reason, escalated, escalate_reason, confidence, model, state, ai_output, actor_id)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) RETURNING id::int`,
      [r.caller, r.criteriaVersion ?? "v1", JSON.stringify(r.criteria), g.sTotal, g.veto, g.vetoReason, g.escalated, g.escalateReason,
        r.confidence == null ? null : clamp01(r.confidence), r.model ?? null, g.state, JSON.stringify(r.aiOutput), r.actorId ?? null]);
    return { id: row?.id ?? null, gate: g };
  } catch { return { id: null, gate: g }; }
}

/** Закрыть решение: что сохранил человек (поля в тех же ключах, что ai_output) и где лежит итог. Повторное закрытие игнорируется. */
export async function closeDecision(id: number, r: { humanOutput: Record<string, unknown>; entity: string; entityId: string | number; actorId?: number | null;
  fields?: string[]; rejected?: boolean }): Promise<FieldDiff | null> {
  try {
    // чужое решение закрыть нельзя: если решение открыл конкретный человек, закрыть его может только он
    const [d] = await q<{ ai_output: Record<string, unknown> }>(`SELECT ai_output FROM ai_decision WHERE id=$1 AND closed_at IS NULL AND (actor_id IS NULL OR $2::bigint IS NULL OR actor_id=$2::bigint)`, [id, r.actorId ?? null]);
    if (!d) return null;
    const diff = fieldDiff(d.ai_output ?? {}, r.humanOutput, r.fields);
    const state = r.rejected ? "rejected" : humanState(diff);
    await q(`UPDATE ai_decision SET entity=$2, entity_id=$3, human_output=$4, diff=$5, fields_total=$6, fields_changed=$7, state=$8, actor_id=coalesce($9, actor_id), closed_at=now()
      WHERE id=$1 AND closed_at IS NULL`,
      [id, r.entity, String(r.entityId), JSON.stringify(r.humanOutput), JSON.stringify(diff), diff.total, diff.changed.length + diff.cleared.length, state, r.actorId ?? null]);
    return diff;
  } catch { return null; }
}
