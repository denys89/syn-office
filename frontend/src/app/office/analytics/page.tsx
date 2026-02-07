'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, UsageSummary, UsageBreakdown, UsageDaily } from '@/lib/api';

export default function Analytics() {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const [summary, setSummary] = useState<UsageSummary | null>(null);
    const [breakdown, setBreakdown] = useState<UsageBreakdown | null>(null);
    const [dailyUsage, setDailyUsage] = useState<UsageDaily[]>([]);
    const [period, setPeriod] = useState<'30d' | '7d' | 'today'>('30d');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/');
        }
    }, [isAuthenticated, isLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            loadData();
        }
    }, [isAuthenticated, period]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [summaryData, breakdownData, dailyData] = await Promise.all([
                api.getUsageSummary(period),
                api.getUsageBreakdown(period === '30d' ? 30 : period === '7d' ? 7 : 1),
                api.getDailyUsage(period === '30d' ? 30 : period === '7d' ? 7 : 1),
            ]);
            setSummary(summaryData);
            setBreakdown(breakdownData);
            setDailyUsage(dailyData.daily_usage || []);
        } catch (error) {
            console.error('Failed to load analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse-slow text-[var(--muted)]">Loading...</div>
            </div>
        );
    }

    const formatCredits = (credits: number) => credits.toLocaleString();
    const formatCurrency = (usd: number) => `$${usd.toFixed(2)}`;
    const formatPercent = (ratio: number) => `${(ratio * 100).toFixed(1)}%`;

    return (
        <div className="min-h-screen bg-[var(--background)]">
            {/* Header */}
            <header className="border-b border-[var(--border)] bg-[var(--card)]">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => router.push('/office')}
                            className="text-[var(--muted)] hover:text-white transition-colors"
                        >
                            ← Back
                        </button>
                        <h1 className="text-2xl font-bold gradient-text">Usage Analytics</h1>
                    </div>
                    <div className="flex gap-2">
                        {(['today', '7d', '30d'] as const).map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-4 py-2 rounded-lg font-medium transition-all ${period === p
                                        ? 'bg-[var(--primary)] text-white'
                                        : 'text-[var(--muted)] hover:text-white hover:bg-[var(--secondary)]'
                                    }`}
                            >
                                {p === 'today' ? 'Today' : p === '7d' ? '7 Days' : '30 Days'}
                            </button>
                        ))}
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8">
                {loading ? (
                    <div className="text-center py-20 text-[var(--muted)]">
                        <div className="animate-pulse">Loading analytics...</div>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {/* Summary Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <SummaryCard
                                icon="💎"
                                label="Credits Used"
                                value={formatCredits(summary?.credits_used || 0)}
                                subtext={`${formatCredits(summary?.credits_remaining || 0)} remaining`}
                                color="primary"
                            />
                            <SummaryCard
                                icon="⚡"
                                label="Tasks Executed"
                                value={summary?.tasks_executed?.toString() || '0'}
                                subtext={`${formatCredits(summary?.tokens_processed || 0)} tokens`}
                                color="accent"
                            />
                            <SummaryCard
                                icon="💰"
                                label="Estimated Cost"
                                value={formatCurrency(summary?.estimated_cost_usd || 0)}
                                subtext="Based on API pricing"
                                color="success"
                            />
                            <SummaryCard
                                icon="🏠"
                                label="Local Model Usage"
                                value={formatPercent(summary?.local_model_ratio || 0)}
                                subtext="Free local models"
                                color="info"
                            />
                        </div>

                        {/* Charts Row */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Daily Usage Chart */}
                            <div className="card">
                                <h3 className="text-lg font-semibold mb-4">Daily Usage</h3>
                                <div className="h-64 flex items-end gap-1">
                                    {dailyUsage.length === 0 ? (
                                        <div className="flex-1 flex items-center justify-center text-[var(--muted)]">
                                            No usage data yet
                                        </div>
                                    ) : (
                                        dailyUsage.slice(-14).map((day, i) => {
                                            const maxCredits = Math.max(...dailyUsage.map(d => d.credits_consumed), 1);
                                            const height = (day.credits_consumed / maxCredits) * 100;
                                            return (
                                                <div
                                                    key={i}
                                                    className="flex-1 flex flex-col items-center gap-1"
                                                >
                                                    <div
                                                        className="w-full bg-gradient-to-t from-[var(--primary)] to-[var(--accent)] rounded-t-sm transition-all hover:opacity-80"
                                                        style={{ height: `${Math.max(height, 2)}%` }}
                                                        title={`${day.date}: ${day.credits_consumed} credits`}
                                                    />
                                                    <span className="text-[10px] text-[var(--muted)]">
                                                        {new Date(day.date).getDate()}
                                                    </span>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>

                            {/* Model Breakdown */}
                            <div className="card">
                                <h3 className="text-lg font-semibold mb-4">Usage by Model</h3>
                                <div className="space-y-3">
                                    {breakdown?.usage_by_model?.length === 0 ? (
                                        <div className="text-center py-8 text-[var(--muted)]">
                                            No model usage data yet
                                        </div>
                                    ) : (
                                        breakdown?.usage_by_model?.slice(0, 5).map((model, i) => (
                                            <div key={i} className="space-y-1">
                                                <div className="flex justify-between text-sm">
                                                    <span className="font-medium">{model.model}</span>
                                                    <span className="text-[var(--muted)]">
                                                        {formatCredits(model.total_credits)} credits
                                                    </span>
                                                </div>
                                                <div className="h-2 bg-[var(--secondary)] rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] rounded-full"
                                                        style={{ width: `${model.percent_of_usage}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Agent Breakdown */}
                        <div className="card">
                            <h3 className="text-lg font-semibold mb-4">Usage by Agent</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="text-left text-[var(--muted)] text-sm border-b border-[var(--border)]">
                                            <th className="pb-3 font-medium">Agent</th>
                                            <th className="pb-3 font-medium">Role</th>
                                            <th className="pb-3 font-medium text-right">Tasks</th>
                                            <th className="pb-3 font-medium text-right">Credits</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {breakdown?.usage_by_agent?.length === 0 ? (
                                            <tr>
                                                <td colSpan={4} className="py-8 text-center text-[var(--muted)]">
                                                    No agent usage data yet
                                                </td>
                                            </tr>
                                        ) : (
                                            breakdown?.usage_by_agent?.map((agent, i) => (
                                                <tr key={i} className="border-b border-[var(--border)] last:border-0">
                                                    <td className="py-3 font-medium">{agent.agent_name}</td>
                                                    <td className="py-3 text-[var(--muted)]">{agent.role}</td>
                                                    <td className="py-3 text-right">{agent.total_tasks}</td>
                                                    <td className="py-3 text-right font-medium">
                                                        {formatCredits(agent.total_credits)}
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

function SummaryCard({
    icon,
    label,
    value,
    subtext,
    color,
}: {
    icon: string;
    label: string;
    value: string;
    subtext: string;
    color: 'primary' | 'accent' | 'success' | 'info';
}) {
    const colorClasses = {
        primary: 'from-[var(--primary)]/20 to-transparent border-[var(--primary)]/30',
        accent: 'from-[var(--accent)]/20 to-transparent border-[var(--accent)]/30',
        success: 'from-emerald-500/20 to-transparent border-emerald-500/30',
        info: 'from-sky-500/20 to-transparent border-sky-500/30',
    };

    return (
        <div className={`card bg-gradient-to-br ${colorClasses[color]} border`}>
            <div className="text-2xl mb-2">{icon}</div>
            <div className="text-sm text-[var(--muted)] mb-1">{label}</div>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-xs text-[var(--muted)] mt-1">{subtext}</div>
        </div>
    );
}
