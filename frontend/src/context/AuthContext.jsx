"use client";
import { createContext, useCallback, useContext, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
const AuthContext = createContext(undefined);
export function AuthProvider({ children }) {
    const user = useAuthStore((state) => state.user);
    const isLoading = useAuthStore((state) => state.isLoading);
    const setUser = useAuthStore((state) => state.setUser);
    const setLoading = useAuthStore((state) => state.setLoading);
    const clear = useAuthStore((state) => state.clear);
    const refreshUser = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.get("/api/auth/me");
            setUser(response.data.user);
        }
        catch {
            setUser(null);
        }
        finally {
            setLoading(false);
        }
    }, [setLoading, setUser]);
    useEffect(() => {
        void refreshUser();
    }, [refreshUser]);
    useEffect(() => {
        const handleAuthExpired = () => clear();
        window.addEventListener("naz:auth-expired", handleAuthExpired);
        return () => window.removeEventListener("naz:auth-expired", handleAuthExpired);
    }, [clear]);
    const login = useCallback(async (credentials) => {
        const response = await api.post("/api/auth/login", credentials);
        setUser(response.data.user);
        setLoading(false);
        return response.data.user;
    }, [setLoading, setUser]);
    const logout = useCallback(async () => {
        await api.post("/api/auth/logout");
        clear();
    }, [clear]);
    const value = useMemo(() => ({
        user,
        isLoading,
        login,
        logout,
        refreshUser,
    }), [isLoading, login, logout, refreshUser, user]);
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuthContext() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuthContext must be used within an AuthProvider");
    }
    return context;
}
