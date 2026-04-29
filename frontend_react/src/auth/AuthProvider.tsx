import React, {useEffect, useRef, useState} from "react";
import type {LoginPayload, RegisterPayload, User} from "../api/auth";
import * as authApi from "../api/auth";
import { AuthContext } from "./AuthContext";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_COOKIE = "refresh_token";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

function setRefreshTokenCookie(token: string) {
    document.cookie = `${REFRESH_TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=lax`;
}

function getRefreshTokenCookie() {
    const prefix = `${REFRESH_TOKEN_COOKIE}=`;
    const entry = document.cookie
        .split("; ")
        .find((cookie) => cookie.startsWith(prefix));

    return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

function clearRefreshTokenCookie() {
    document.cookie = `${REFRESH_TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function AuthProvider({children}: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const refreshIntervalRef = useRef<number | null>(null);

    async function refreshSession() {
        const refreshToken = getRefreshTokenCookie();
        if (!refreshToken) return null;

        try {
            const response = await authApi.refreshAccessToken({refresh: refreshToken});
            localStorage.setItem(ACCESS_TOKEN_KEY, response.access);
            return response.access;
        } catch {
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            clearRefreshTokenCookie();
            setUser(null);
            return null;
        }
    }

    function stopRefreshLoop() {
        if (refreshIntervalRef.current !== null) {
            window.clearInterval(refreshIntervalRef.current);
            refreshIntervalRef.current = null;
        }
    }

    function startRefreshLoop() {
        stopRefreshLoop();
        refreshIntervalRef.current = window.setInterval(() => {
            void refreshSession();
        }, REFRESH_INTERVAL_MS);
    }

    // Initialize user
    useEffect(() => {
        async function loadUser() {
            let token = localStorage.getItem(ACCESS_TOKEN_KEY);
            if (!token && getRefreshTokenCookie()) {
                token = await refreshSession();
            }
            // defaults to null if no token present
            if (!token) return;

            try {
                // try to get my Player info
                const me = await authApi.getMe();
                setUser(me);
                startRefreshLoop();
            } catch {
                const refreshedToken = await refreshSession();
                if (!refreshedToken) return;

                try {
                    const me = await authApi.getMe();
                    setUser(me);
                    startRefreshLoop();
                } catch {
                    localStorage.removeItem(ACCESS_TOKEN_KEY);
                    clearRefreshTokenCookie();
                    setUser(null);
                }
            }
        }
        
        void loadUser();

        return () => {
            stopRefreshLoop();
        };
    }, []);
    
    async function login(data: LoginPayload) {
        const res = await authApi.login(data)
        
        localStorage.setItem(ACCESS_TOKEN_KEY, res.access);
        setRefreshTokenCookie(res.refresh);
        
        const me = await authApi.getMe();
        setUser(me);
        startRefreshLoop();
    }

    async function logout() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        clearRefreshTokenCookie();
        stopRefreshLoop();
        setUser(null);
    }
    
    async function register(data: RegisterPayload) {
        await authApi.register(data);
    }

    return <AuthContext.Provider value={{
        user,
        isAuth: !!user,
        login,
        logout,
        register
    }}>{children}</AuthContext.Provider>;
}
