import React, {useEffect, useRef, useState} from "react";
import type {LoginPayload, RegisterPayload, User} from "../api/auth";
import * as authApi from "../api/auth";
import { AuthContext } from "./AuthContext";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_COOKIE = "refresh_token";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Store the refresh token in a same-site cookie.
 *
 * @param token - Refresh token returned by the backend.
 * @returns Nothing.
 */
function setRefreshTokenCookie(token: string) {
    document.cookie = `${REFRESH_TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=lax`;
}

/**
 * Read the refresh token from document.cookie.
 *
 * @returns The decoded refresh token, or null when missing.
 */
function getRefreshTokenCookie() {
    const prefix = `${REFRESH_TOKEN_COOKIE}=`;
    const entry = document.cookie
        .split("; ")
        .find((cookie) => cookie.startsWith(prefix));

    return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

/**
 * Remove the refresh token cookie.
 *
 * @returns Nothing.
 */
function clearRefreshTokenCookie() {
    document.cookie = `${REFRESH_TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

/**
 * Provide authentication state and actions to the React tree.
 *
 * @param children - Components that need access to auth state.
 * @returns An AuthContext provider element.
 */
export function AuthProvider({children}: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const refreshIntervalRef = useRef<number | null>(null);

    /**
     * Refresh the access token from the stored refresh token.
     *
     * @returns The new access token, or null when refresh fails.
     */
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

    /**
     * Stop the scheduled access-token refresh loop.
     *
     * @returns Nothing.
     */
    function stopRefreshLoop() {
        if (refreshIntervalRef.current !== null) {
            window.clearInterval(refreshIntervalRef.current);
            refreshIntervalRef.current = null;
        }
    }

    /**
     * Start a single interval that refreshes the access token.
     *
     * @returns Nothing.
     */
    function startRefreshLoop() {
        stopRefreshLoop();
        refreshIntervalRef.current = window.setInterval(() => {
            void refreshSession();
        }, REFRESH_INTERVAL_MS);
    }

    useEffect(() => {
        /**
         * Restore the current user from existing tokens on page load.
         *
         * @returns Nothing after user state is loaded or cleared.
         */
        async function loadUser() {
            let token = localStorage.getItem(ACCESS_TOKEN_KEY);
            if (!token && getRefreshTokenCookie()) {
                token = await refreshSession();
            }
            // Leaving user as null keeps unauthenticated routes deterministic.
            if (!token) return;

            try {
                // A valid access token should load the player without forcing a refresh.
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
    
    /**
     * Sign in, persist tokens, and load the current player.
     *
     * @param data - Login form credentials.
     * @returns Nothing after auth state is updated.
     */
    async function login(data: LoginPayload) {
        const res = await authApi.login(data)
        
        localStorage.setItem(ACCESS_TOKEN_KEY, res.access);
        setRefreshTokenCookie(res.refresh);
        
        const me = await authApi.getMe();
        setUser(me);
        startRefreshLoop();
    }

    /**
     * Clear local auth state and stop background token refreshes.
     *
     * @returns Nothing.
     */
    async function logout() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        clearRefreshTokenCookie();
        stopRefreshLoop();
        setUser(null);
    }
    
    /**
     * Create a new account without signing in automatically.
     *
     * @param data - Registration form credentials.
     * @returns Nothing after the API accepts the registration.
     */
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
