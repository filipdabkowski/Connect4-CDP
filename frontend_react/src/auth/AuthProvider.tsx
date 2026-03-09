import React, { useEffect, useState} from "react";
import type {LoginPayload, RegisterPayload, User} from "../api/auth";
import * as authApi from "../api/auth";
import { AuthContext } from "./AuthContext";


export function AuthProvider({children}: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);

    // Initialize user
    useEffect(() => {
        async function loadUser() {
            const token = localStorage.getItem("access_token");
            // defaults to null if no token present
            if (!token) return;
            try {
                // try to get my Player info
                const me = await authApi.getMe();
                setUser(me);
            } catch {
                // Token didn't work, remove from memory
                localStorage.removeItem("access_token");
            }
        }
        
        loadUser();
    }, []);
    
    async function login(data: LoginPayload) {
        const res = await authApi.login(data)
        
        localStorage.setItem("access_token", res.access);
        
        const me = await authApi.getMe();
        setUser(me);
    }

    async function logout() {
        localStorage.removeItem("access_token");
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
