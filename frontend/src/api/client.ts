import type { Dashboard, PaperResult } from '@/types/bank';

const API_BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health/'),
  dashboard: () => request<Dashboard>('/dashboard/'),
  generatePaper: (difficulty: string, amount: number) =>
    request<PaperResult>('/papers/generate/', {
      method: 'POST',
      body: JSON.stringify({ difficulty, amount })
    }),
  latestPaper: (difficulty?: string) =>
    request<Partial<PaperResult> & { paper: PaperResult['paper'] }>(
      `/papers/latest/${difficulty ? `?difficulty=${encodeURIComponent(difficulty)}` : ''}`
    ),
  submitExam: (answers: Record<number, string>) =>
    request<{ score: number; correct: number; total: number; rank_hint: string; analysis: string[] }>('/exams/submit/', {
      method: 'POST',
      body: JSON.stringify({ answers })
    }),
  demoLogin: () =>
    request<{ access: string; refresh: string }>('/auth/demo-login/', {
      method: 'POST'
    })
};
