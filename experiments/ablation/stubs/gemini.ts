// Stub for offline replay: the frozen replay never calls a model. Live extraction needs the production Gemini adapter.
export async function geminiText(..._a: unknown[]): Promise<string> { throw new Error("offline replay: model calls are not available"); }
export async function geminiVisionJson(..._a: unknown[]): Promise<unknown> { throw new Error("offline replay: model calls are not available"); }
