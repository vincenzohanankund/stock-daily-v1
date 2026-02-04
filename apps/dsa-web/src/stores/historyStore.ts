import { create } from 'zustand';
import type { HistoryItem, HistoryFilters, AnalysisReport } from '../types/analysis';
import { getRecentStartDate, toDateInputValue } from '../utils/format';

interface HistoryState {
  // 列表数据
  items: HistoryItem[];
  total: number;

  // 分页
  currentPage: number;
  pageSize: number;

  // 筛选
  filters: HistoryFilters;

  // 加载状态
  isLoading: boolean;
  error: string | null;

  // 选中项
  selectedItem: HistoryItem | null;
  selectedReport: AnalysisReport | null;
  isDrawerOpen: boolean;

  // Actions
  setItems: (items: HistoryItem[], total: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setCurrentPage: (page: number) => void;
  setFilters: (filters: HistoryFilters) => void;
  resetFilters: () => void;
  selectItem: (item: HistoryItem | null) => void;
  setSelectedReport: (report: AnalysisReport | null) => void;
  openDrawer: (item: HistoryItem) => void;
  closeDrawer: () => void;
  reset: () => void;
}

const getDefaultFilters = (): HistoryFilters => ({
  startDate: getRecentStartDate(30),
  endDate: toDateInputValue(new Date()),
});

export const useHistoryStore = create<HistoryState>((set) => ({
  // 初始状态
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 20,
  filters: getDefaultFilters(),
  isLoading: false,
  error: null,
  selectedItem: null,
  selectedReport: null,
  isDrawerOpen: false,

  // Actions
  setItems: (items, total) => set({ items, total }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error, isLoading: false }),

  setCurrentPage: (page) => set({ currentPage: page }),

  setFilters: (filters) => set({ filters }),

  resetFilters: () =>
    set({
      filters: getDefaultFilters(),
      currentPage: 1,
    }),

  selectItem: (item) => set({ selectedItem: item }),

  setSelectedReport: (report) => set({ selectedReport: report }),

  openDrawer: (item) =>
    set({
      selectedItem: item,
      isDrawerOpen: true,
    }),

  closeDrawer: () =>
    set({
      isDrawerOpen: false,
      selectedItem: null,
      selectedReport: null,
    }),

  reset: () =>
    set({
      items: [],
      total: 0,
      currentPage: 1,
      filters: getDefaultFilters(),
      isLoading: false,
      error: null,
      selectedItem: null,
      selectedReport: null,
      isDrawerOpen: false,
    }),
}));
