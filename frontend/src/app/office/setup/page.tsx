'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, AgentTemplate } from '@/lib/api';
import { getAgentRoleIcon } from '@/lib/utils';

export default function OfficeSetup() {
    const { isAuthenticated, isLoading, agents, refreshAgents } = useAuth();
    const router = useRouter();
    const [templates, setTemplates] = useState<AgentTemplate[]>([]);
    const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [loadingTemplates, setLoadingTemplates] = useState(true);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/');
        }
    }, [isAuthenticated, isLoading, router]);

    useEffect(() => {
        // If user already has agents, redirect to office
        if (!isLoading && agents.length > 0) {
            router.push('/office');
        }
    }, [agents, isLoading, router]);

    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            const { templates: loadedTemplates } = await api.getAgentTemplates();
            setTemplates(loadedTemplates || []);
        } catch (error) {
            console.error('Failed to load templates:', error);
        } finally {
            setLoadingTemplates(false);
        }
    };

    const toggleTemplate = (templateId: string) => {
        setSelectedTemplates((prev) =>
            prev.includes(templateId)
                ? prev.filter((id) => id !== templateId)
                : [...prev, templateId]
        );
    };

    const handleContinue = async () => {
        if (selectedTemplates.length === 0) return;

        setIsSubmitting(true);
        try {
            await api.selectAgents(selectedTemplates);
            await refreshAgents();
            router.push('/office');
        } catch (error) {
            console.error('Failed to select agents:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (isLoading || loadingTemplates) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse-slow text-[var(--muted)]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col">
            <div className="flex-1 flex items-center justify-center p-4">
                <div className="w-full max-w-2xl">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold gradient-text mb-2">Set Up Your Office</h1>
                        <p className="text-[var(--muted)]">
                            Choose the AI employees you want to work with
                        </p>
                    </div>

                    {/* Agent Templates */}
                    <div className="grid gap-4 mb-8">
                        {templates.map((template) => {
                            const isSelected = selectedTemplates.includes(template.id);
                            return (
                                <div
                                    key={template.id}
                                    onClick={() => toggleTemplate(template.id)}
                                    className={`card cursor-pointer transition-all ${isSelected
                                            ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                                            : 'hover:border-[var(--muted)]'
                                        }`}
                                >
                                    <div className="flex items-start gap-4">
                                        <div
                                            className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${isSelected ? 'bg-[var(--primary)]/20' : 'bg-[var(--secondary)]'
                                                }`}
                                        >
                                            {getAgentRoleIcon(template.role)}
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="font-semibold text-lg">{template.name}</h3>
                                                    <span className="text-sm text-[var(--muted)]">{template.role}</span>
                                                </div>
                                                <div
                                                    className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${isSelected
                                                            ? 'border-[var(--primary)] bg-[var(--primary)]'
                                                            : 'border-[var(--border)]'
                                                        }`}
                                                >
                                                    {isSelected && (
                                                        <svg
                                                            className="w-4 h-4 text-white"
                                                            fill="none"
                                                            viewBox="0 0 24 24"
                                                            stroke="currentColor"
                                                        >
                                                            <path
                                                                strokeLinecap="round"
                                                                strokeLinejoin="round"
                                                                strokeWidth={2}
                                                                d="M5 13l4 4L19 7"
                                                            />
                                                        </svg>
                                                    )}
                                                </div>
                                            </div>
                                            <p className="text-sm text-[var(--muted)] mt-2 line-clamp-2">
                                                {template.system_prompt.substring(0, 150)}...
                                            </p>
                                            <div className="flex flex-wrap gap-2 mt-3">
                                                {template.skill_tags.map((tag) => (
                                                    <span
                                                        key={tag}
                                                        className="px-2 py-0.5 text-xs rounded-full bg-[var(--secondary)] text-[var(--muted)]"
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Action Button */}
                    <button
                        onClick={handleContinue}
                        disabled={selectedTemplates.length === 0 || isSubmitting}
                        className="btn btn-primary w-full py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSubmitting ? (
                            <span className="animate-pulse">Setting up your office...</span>
                        ) : selectedTemplates.length === 0 ? (
                            'Select at least one agent'
                        ) : (
                            `Continue with ${selectedTemplates.length} agent${selectedTemplates.length > 1 ? 's' : ''
                            }`
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
