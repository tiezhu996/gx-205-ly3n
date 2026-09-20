import { create } from 'zustand';
import { api } from '@/api/client';
import type { Dashboard, PaperResult } from '@/types/bank';

// 最近一次试卷与已作答案持久化到 localStorage，刷新页面后可直接回读。
const PAPER_STORAGE_KEY = 'gxlogic:last-paper';
const ANSWERS_STORAGE_KEY = 'gxlogic:last-answers';

type AnswerMap = Record<number, string>;

function readStoredPaper(): PaperResult | null {
  try {
    const raw = localStorage.getItem(PAPER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PaperResult) : null;
  } catch {
    return null;
  }
}

function readStoredAnswers(): AnswerMap {
  try {
    const raw = localStorage.getItem(ANSWERS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AnswerMap) : {};
  } catch {
    return {};
  }
}

function persistPaper(paper: PaperResult | null) {
  try {
    if (paper) {
      localStorage.setItem(PAPER_STORAGE_KEY, JSON.stringify(paper));
    } else {
      localStorage.removeItem(PAPER_STORAGE_KEY);
    }
  } catch {
    // localStorage 不可用（隐私模式等）时退化为仅内存态，不影响答题与提交。
  }
}

function persistAnswers(answers: AnswerMap) {
  try {
    localStorage.setItem(ANSWERS_STORAGE_KEY, JSON.stringify(answers));
  } catch {
    // 同上：持久化失败不阻断主流程。
  }
}

// 仅保留当前试卷题目的作答，更换试卷后自动清掉旧题答案。
function pruneAnswers(answers: AnswerMap, paper: PaperResult | null): AnswerMap {
  if (!paper) {
    return {};
  }
  const ids = new Set(paper.question_ids);
  return Object.fromEntries(
    Object.entries(answers).filter(([id]) => ids.has(Number(id)))
  );
}

interface BankState {
  loading: boolean;
  paperLoading: boolean;
  error: string;
  dashboard: Dashboard | null;
  token: string;
  // 最近一次组卷结果（含实际题数、缺口、复用提示）与当前作答案。
  paper: PaperResult | null;
  answers: AnswerMap;
  readback: boolean;
  loadDashboard: () => Promise<void>;
  generatePaper: (difficulty: string, amount: number) => Promise<void>;
  restoreLastPaper: () => Promise<void>;
  setAnswer: (questionId: number, value: string) => void;
  clearAnswers: () => void;
  demoLogin: () => Promise<void>;
}

export const useBankStore = create<BankState>((set, get) => ({
  loading: false,
  paperLoading: false,
  error: '',
  dashboard: null,
  token: '',
  // 初始化时同步从 localStorage 回读，保证首屏即可展示最近一次试卷。
  paper: readStoredPaper(),
  answers: pruneAnswers(readStoredAnswers(), readStoredPaper()),
  readback: false,
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
  generatePaper: async (difficulty, amount) => {
    set({ paperLoading: true, error: '' });
    try {
      const paper = await api.generatePaper(difficulty, amount);
      persistPaper(paper);
      // 新试卷重置作答，避免把上一份的选择带入新卷。
      persistAnswers({});
      set({ paper, answers: {}, readback: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '组卷失败' });
    } finally {
      set({ paperLoading: false });
    }
  },
  restoreLastPaper: async () => {
    // 本地已有最近一次试卷时直接回读；本地缺失（换设备/清缓存）再向服务端拉取。
    if (get().paper) {
      set({ readback: true });
      return;
    }
    set({ paperLoading: true, error: '' });
    try {
      const result = await api.latestPaper();
      if (result && result.actual_amount && result.actual_amount > 0) {
        const paper = result as PaperResult;
        persistPaper(paper);
        set({ paper, answers: pruneAnswers(readStoredAnswers(), paper), readback: true });
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '最近一次试卷读取失败' });
    } finally {
      set({ paperLoading: false });
    }
  },
  setAnswer: (questionId, value) => {
    const answers = { ...get().answers, [questionId]: value };
    persistAnswers(answers);
    set({ answers });
  },
  clearAnswers: () => {
    persistAnswers({});
    set({ answers: {} });
  },
  demoLogin: async () => {
    const result = await api.demoLogin();
    set({ token: result.access });
  }
}));
