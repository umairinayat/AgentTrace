/** Zustand global UI state store. */

import { create } from 'zustand';

interface AppState {
  selectedTraceId: string | null;
  selectedSpanId: string | null;
  sidebarOpen: boolean;
  setSelectedTrace: (id: string | null) => void;
  setSelectedSpan: (id: string | null) => void;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedTraceId: null,
  selectedSpanId: null,
  sidebarOpen: true,
  setSelectedTrace: (id) => set({ selectedTraceId: id }),
  setSelectedSpan: (id) => set({ selectedSpanId: id }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
