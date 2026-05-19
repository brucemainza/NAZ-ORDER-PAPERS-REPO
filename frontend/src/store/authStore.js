"use client";
import { create } from "zustand";
export const useAuthStore = create((set) => ({
    user: null,
    isLoading: true,
    setUser: (user) => set({ user }),
    setLoading: (value) => set({ isLoading: value }),
    clear: () => set({ user: null, isLoading: false }),
}));
