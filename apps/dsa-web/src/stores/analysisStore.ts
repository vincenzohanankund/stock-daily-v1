import { create } from 'zustand';
import type { AnalysisResult } from '../types/analysis';

interface AnalysisState {
  isLoading: boolean;
  result: AnalysisResult | null;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setResult: (result: AnalysisResult | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  isLoading: false,
  result: null,
  error: null,
  setLoading: (loading) => set({ isLoading: loading }),
  setResult: (result) => set({ result, error: null }),
  setError: (error) => set({ error, isLoading: false }),
  reset: () => set({ isLoading: false, result: null, error: null }),
}));
