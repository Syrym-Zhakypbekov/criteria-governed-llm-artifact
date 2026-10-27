// Stub for offline replay: used only by live normalisation of addenda, not by criteria replay.
export function addendumBasis(a: { baseNumber?: string; baseDate?: string }): string { return [a.baseNumber, a.baseDate].filter(Boolean).join(" от "); }
