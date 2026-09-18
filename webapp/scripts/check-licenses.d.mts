export interface Verdict {
  ok: boolean;
  kind: string;
  id?: string;
}

export function verdict(expr: unknown): Verdict;
