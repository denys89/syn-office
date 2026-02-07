'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, Conversation, Agent, Wallet } from '@/lib/api';
import { AgentAvatar } from '@/components/AgentAvatar';
import { ChatWindow } from '@/components/ChatWindow';
import { getAgentRoleIcon } from '@/lib/utils';

export default function Office() {
    const { user, isAuthenticated, isLoading, agents, logout, refreshAgents } = useAuth();
    const router = useRouter();
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
    const [showNewChat, setShowNewChat] = useState(false);
    const [loadingConversations, setLoadingConversations] = useState(true);
    const [wallet, setWallet] = useState<Wallet | null>(null);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/');
        }
    }, [isAuthenticated, isLoading, router]);

    useEffect(() => {
        // If no agents, redirect to setup
        if (!isLoading && isAuthenticated && agents.length === 0) {
            router.push('/office/setup');
        }
    }, [agents, isAuthenticated, isLoading, router]);

    useEffect(() => {
        if (isAuthenticated && agents.length > 0) {
            loadConversations();
        }
    }, [isAuthenticated, agents]);

    const loadConversations = async () => {
        try {
            const { conversations: loadedConversations } = await api.getConversations();
            setConversations(loadedConversations || []);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        } finally {
            setLoadingConversations(false);
        }
    };

    useEffect(() => {
        if (isAuthenticated) {
            api.getWalletBalance()
                .then(setWallet)
                .catch((error) => {
                    // Silently fail if credits system isn't set up yet
                    console.warn('Credits not available:', error.message);
                    setWallet(null);
                });
        }
    }, [isAuthenticated]);

    const startDirectChat = async (agent: Agent) => {
        try {
            // Check if conversation already exists
            const existing = conversations.find(
                (c) => c.type === 'direct' && c.participants?.some((p) => p.id === agent.id)
            );

            if (existing) {
                setSelectedConversation(existing);
                return;
            }

            // Create new conversation
            const conversation = await api.createConversation('direct', [agent.id]);
            setConversations((prev) => [conversation, ...prev]);
            setSelectedConversation(conversation);
        } catch (error) {
            console.error('Failed to create conversation:', error);
        }
        setShowNewChat(false);
    };

    const handleLogout = () => {
        logout();
        router.push('/');
    };

    if (isLoading || (isAuthenticated && agents.length === 0)) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse-slow text-[var(--muted)]">Loading your office...</div>
            </div>
        );
    }

    return (
        <div className="h-screen flex overflow-hidden">
            {/* Sidebar */}
            <div className="w-80 border-r border-[var(--border)] flex flex-col bg-[var(--card)]">
                {/* Header */}
                <div className="p-4 border-b border-[var(--border)]">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex flex-col">
                            <h1 className="text-xl font-bold gradient-text leading-none">Synoffice</h1>
                            <div className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] w-fit mt-1 border border-[var(--primary)]/20">
                                💎 {wallet?.balance ?? 0} Credits
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="text-[var(--muted)] hover:text-white transition-colors"
                            title="Logout"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                                />
                            </svg>
                        </button>
                    </div>
                    <button
                        onClick={() => setShowNewChat(true)}
                        className="btn btn-primary w-full"
                    >
                        + New Chat
                    </button>
                </div>

                {/* Conversations List */}
                <div className="flex-1 overflow-y-auto p-2">
                    <div className="text-xs text-[var(--muted)] uppercase tracking-wider px-2 py-2">
                        Conversations
                    </div>
                    {loadingConversations ? (
                        <div className="p-4 text-center text-[var(--muted)] animate-pulse">Loading...</div>
                    ) : conversations.length === 0 ? (
                        <div className="p-4 text-center text-[var(--muted)]">
                            <p className="mb-2">No conversations yet</p>
                            <button
                                onClick={() => setShowNewChat(true)}
                                className="text-[var(--primary)] hover:underline text-sm"
                            >
                                Start a new chat
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {conversations.map((conv) => {
                                const participant = conv.participants?.[0];
                                const isSelected = selectedConversation?.id === conv.id;

                                return (
                                    <button
                                        key={conv.id}
                                        onClick={() => setSelectedConversation(conv)}
                                        className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all text-left ${isSelected
                                            ? 'bg-[var(--primary)]/10 border border-[var(--primary)]/30'
                                            : 'hover:bg-[var(--secondary)]'
                                            }`}
                                    >
                                        {participant && <AgentAvatar agent={participant} size="sm" showStatus />}
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium truncate">
                                                {conv.name ||
                                                    participant?.custom_name ||
                                                    participant?.template?.name ||
                                                    'Chat'}
                                            </div>
                                            <div className="text-xs text-[var(--muted)] truncate">
                                                {participant?.template?.role || 'Agent'}
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Agents Section */}
                <div className="border-t border-[var(--border)] p-2">
                    <div className="text-xs text-[var(--muted)] uppercase tracking-wider px-2 py-2">
                        Your Agents
                    </div>
                    <div className="space-y-1">
                        {agents.map((agent) => (
                            <button
                                key={agent.id}
                                onClick={() => startDirectChat(agent)}
                                className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--secondary)] transition-all text-left"
                            >
                                <AgentAvatar agent={agent} size="sm" showStatus />
                                <div className="flex-1 min-w-0">
                                    <div className="font-medium text-sm truncate">
                                        {agent.custom_name || agent.template?.name}
                                    </div>
                                    <div className="text-xs text-[var(--muted)]">{agent.template?.role}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                    <a
                        href="/marketplace"
                        className="flex items-center gap-2 text-sm text-[var(--primary)] hover:text-white transition-colors px-2 py-2 mt-2"
                    >
                        <span>🛒</span>
                        <span>Browse Marketplace</span>
                    </a>
                    <div className="border-t border-[var(--border)] mt-2 pt-2 space-y-1">
                        <a
                            href="/office/analytics"
                            className="flex items-center gap-2 text-sm text-[var(--muted)] hover:text-white transition-colors px-2 py-2 rounded-lg hover:bg-[var(--secondary)]"
                        >
                            <span>📊</span>
                            <span>Usage Analytics</span>
                        </a>
                        <a
                            href="/office/billing"
                            className="flex items-center gap-2 text-sm text-[var(--muted)] hover:text-white transition-colors px-2 py-2 rounded-lg hover:bg-[var(--secondary)]"
                        >
                            <span>💳</span>
                            <span>Billing & Plans</span>
                        </a>
                        <a
                            href="/office/author"
                            className="flex items-center gap-2 text-sm text-[var(--muted)] hover:text-white transition-colors px-2 py-2 rounded-lg hover:bg-[var(--secondary)]"
                        >
                            <span>💰</span>
                            <span>Author Earnings</span>
                        </a>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {selectedConversation ? (
                    <>
                        {/* Chat Header */}
                        <div className="p-4 border-b border-[var(--border)] flex items-center gap-3 flex-shrink-0">
                            {selectedConversation.participants?.[0] && (
                                <AgentAvatar
                                    agent={selectedConversation.participants[0]}
                                    size="md"
                                    showStatus
                                />
                            )}
                            <div>
                                <h2 className="font-semibold">
                                    {selectedConversation.name ||
                                        selectedConversation.participants?.[0]?.custom_name ||
                                        selectedConversation.participants?.[0]?.template?.name ||
                                        'Chat'}
                                </h2>
                                <p className="text-sm text-[var(--muted)]">
                                    {selectedConversation.participants?.[0]?.template?.role || 'Agent'}
                                </p>
                            </div>
                        </div>

                        {/* Chat Window */}
                        <ChatWindow
                            conversationId={selectedConversation.id}
                            agents={agents}
                            userId={user?.id || ''}
                        />
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-[var(--muted)]">
                        <div className="text-6xl mb-4">🏢</div>
                        <h2 className="text-xl font-semibold mb-2">Welcome to Your Office</h2>
                        <p className="mb-4">Select a conversation or start a new chat</p>
                        <button onClick={() => setShowNewChat(true)} className="btn btn-primary">
                            Start New Chat
                        </button>
                    </div>
                )}
            </div>

            {/* New Chat Modal */}
            {showNewChat && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="card w-full max-w-md m-4 animate-slideIn">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold">Start New Chat</h2>
                            <button
                                onClick={() => setShowNewChat(false)}
                                className="text-[var(--muted)] hover:text-white"
                            >
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </button>
                        </div>
                        <p className="text-[var(--muted)] mb-4">Choose an agent to chat with:</p>
                        <div className="space-y-2">
                            {agents.map((agent) => (
                                <button
                                    key={agent.id}
                                    onClick={() => startDirectChat(agent)}
                                    className="w-full flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] transition-all"
                                >
                                    <div className="text-2xl">{getAgentRoleIcon(agent.template?.role || '')}</div>
                                    <div className="flex-1 text-left">
                                        <div className="font-medium">
                                            {agent.custom_name || agent.template?.name}
                                        </div>
                                        <div className="text-sm text-[var(--muted)]">{agent.template?.role}</div>
                                    </div>
                                    <svg
                                        className="w-5 h-5 text-[var(--muted)]"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M9 5l7 7-7 7"
                                        />
                                    </svg>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
