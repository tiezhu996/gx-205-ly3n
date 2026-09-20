import { create } from 'zustand';
import { api } from '@/api/client';
import type { Dashboard, PaperResult, Question } from '@/types/bank';

interface PaperMeta {
  difficulty: string;
  requested: number;
  actual: number;
  reused: number;
  shortage: string | null;
}

interface BankState {
  loading: boolean;
  generating: boolean;
  error: string;
  dashboard: Dashboard | null;
  token: string;
  paper: Question[] | null;
  paperMeta: PaperMeta | null;
  loadDashboard: () => Promise<void>;
  demoLogin: () => Promise<void>;
  generatePaper: (difficulty: string, amount: number) => Promise<void>;
  loadLatestPaper: () => Promise<void>;
}

function toMeta(result: PaperResult): PaperMeta {
  return {
    difficulty: result.difficulty,
    requested: result.requested,
    actual: result.actual,
    reused: result.reused,
    shortage: result.shortage
  };
}

export const useBankStore = create<BankState>((set) => ({
  loading: false,
  generating: false,
  error: '',
  dashboard: null,
  token: '',
  paper: null,
  paperMeta: null,
  loadDashboard: async () => {
    set({ loading: true, error: '' });
    try {
      set({ dashboard: await api.dashboard() });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '数据加载失败' });
    } finally {
      set({ loading: false });
    }
  },
  demoLogin: async () => {
    const result = await api.demoLogin();
    set({ token: result.access });
  },
  generatePaper: async (difficulty, amount) => {
    set({ generating: true, error: '' });
    try {
      const result = await api.generatePaper(difficulty, amount);
      set({ paper: result.paper, paperMeta: toMeta(result) });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '组卷失败' });
    } finally {
      set({ generating: false });
    }
  },
  loadLatestPaper: async () => {
    try {
      const result = await api.latestPaper();
      if (result.paper) {
        set({ paper: result.paper, paperMeta: toMeta(result) });
      }
    } catch {
      // 最近一次试卷不存在或接口异常时，保留 dashboard 默认试卷
    }
  }
}));
