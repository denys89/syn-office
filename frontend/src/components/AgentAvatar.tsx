'use client';

import { Agent } from '@/lib/api';

interface AgentAvatarProps {
    agent: Agent;
    size?: 'sm' | 'md' | 'lg';
    showStatus?: boolean;
    status?: 'online' | 'thinking' | 'working';
}

const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-14 h-14 text-lg',
};

const roleColors: Record<string, string> = {
    Engineer: 'avatar-engineer',
    Analyst: 'avatar-analyst',
    Writer: 'avatar-writer',
    Planner: 'avatar-planner',
};

export function AgentAvatar({ agent, size = 'md', showStatus = false, status = 'online' }: AgentAvatarProps) {
    const name = agent.custom_name || agent.template?.name || 'A';
    const role = agent.template?.role || 'Agent';
    const initial = name.charAt(0).toUpperCase();
    const colorClass = roleColors[role] || 'bg-gradient-to-br from-gray-500 to-gray-700';

    return (
        <div className="relative">
            <div
                className={`${sizeClasses[size]} ${colorClass} rounded-full flex items-center justify-center font-semibold text-white shadow-lg`}
            >
                {initial}
            </div>
            {showStatus && (
                <div
                    className={`absolute -bottom-0.5 -right-0.5 status-dot ${status === 'online' ? 'status-online' : status === 'thinking' ? 'status-thinking' : 'status-working'
                        }`}
                />
            )}
        </div>
    );
}
