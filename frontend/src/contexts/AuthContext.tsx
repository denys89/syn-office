'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, User, Office, Agent } from '@/lib/api';
import { wsClient } from '@/lib/websocket';

interface AuthContextType {
    user: User | null;
    office: Office | null;
    agents: Agent[];
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, name: string) => Promise<void>;
    logout: () => void;
    refreshAgents: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [office, setOffice] = useState<Office | null>(null);
    const [agents, setAgents] = useState<Agent[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Check for existing token on mount
        const token = api.getToken();
        if (token) {
            loadUser();
        } else {
            setIsLoading(false);
        }
    }, []);

    const loadUser = async () => {
        try {
            const data = await api.me();
            // Token is valid, but we need full user data
            // For now, we'll just mark as authenticated
            setUser({ id: data.user_id, email: data.email, name: '', created_at: '' });
            setOffice({ id: data.office_id, user_id: data.user_id, name: '', created_at: '' });

            // Load agents
            await refreshAgents();

            // Connect WebSocket
            wsClient.connect();
        } catch (error) {
            console.error('Failed to load user:', error);
            api.clearToken();
        } finally {
            setIsLoading(false);
        }
    };

    const refreshAgents = async () => {
        try {
            const { agents: loadedAgents } = await api.getAgents();
            setAgents(loadedAgents || []);
        } catch (error) {
            console.error('Failed to load agents:', error);
        }
    };

    const login = async (email: string, password: string) => {
        const data = await api.login(email, password);
        setUser(data.user);
        setOffice(data.office);
        await refreshAgents();
        wsClient.connect();
    };

    const register = async (email: string, password: string, name: string) => {
        const data = await api.register(email, password, name);
        setUser(data.user);
        setOffice(data.office);
        wsClient.connect();
    };

    const logout = () => {
        api.clearToken();
        wsClient.disconnect();
        setUser(null);
        setOffice(null);
        setAgents([]);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                office,
                agents,
                isLoading,
                isAuthenticated: !!user,
                login,
                register,
                logout,
                refreshAgents,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
