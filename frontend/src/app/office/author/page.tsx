'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, AuthorBalance } from '@/lib/api';

interface AuthorEarning {
    id: string;
    template_id: string;
    template_name: string;
    sale_amount_cents: number;
    author_earning_cents: number;
    created_at: string;
}

interface PayoutRequest {
    id: string;
    amount_cents: number;
    status: string;
    created_at: string;
    processed_at?: string;
}

export default function AuthorDashboard() {
    const { isAuthenticated, isLoading, user } = useAuth();
    const router = useRouter();
    const [balance, setBalance] = useState<AuthorBalance | null>(null);
    const [earnings, setEarnings] = useState<AuthorEarning[]>([]);
    const [payouts, setPayouts] = useState<PayoutRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [showPayoutModal, setShowPayoutModal] = useState(false);
    const [payoutAmount, setPayoutAmount] = useState('');
    const [requesting, setRequesting] = useState(false);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/');
        }
    }, [isAuthenticated, isLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            loadData();
        }
    }, [isAuthenticated]);

    const loadData = async () => {
        setLoading(true);
        try {
            const balanceData = await api.getAuthorBalance();
            setBalance(balanceData);

            // These would be additional API calls in production
            // For now, showing the balance is the key feature
        } catch (error) {
            console.error('Failed to load author data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRequestPayout = async () => {
        const amountCents = Math.floor(parseFloat(payoutAmount) * 100);
        if (isNaN(amountCents) || amountCents < 1000) {
            alert('Minimum payout is $10.00');
            return;
        }
        if (amountCents > (balance?.available_balance_cents || 0)) {
            alert('Insufficient balance');
            return;
        }

        setRequesting(true);
        try {
            await api.post('/author/payout/request', { amount_cents: amountCents });
            setShowPayoutModal(false);
            setPayoutAmount('');
            await loadData();
        } catch (error) {
            console.error('Failed to request payout:', error);
            alert('Failed to request payout. Please try again.');
        } finally {
            setRequesting(false);
        }
    };

    const formatCurrency = (cents: number) => `$${(cents / 100).toFixed(2)}`;

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse-slow text-[var(--muted)]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--background)]">
            {/* Header */}
            <header className="border-b border-[var(--border)] bg-[var(--card)]">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
                    <button
                        onClick={() => router.push('/office')}
                        className="text-[var(--muted)] hover:text-white transition-colors"
                    >
                        ← Back
                    </button>
                    <h1 className="text-2xl font-bold gradient-text">Author Dashboard</h1>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8">
                {loading ? (
                    <div className="text-center py-20 text-[var(--muted)]">
                        <div className="animate-pulse">Loading author data...</div>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {/* Balance Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <BalanceCard
                                icon="💰"
                                label="Total Earned"
                                value={formatCurrency(balance?.total_earned_cents || 0)}
                                color="success"
                            />
                            <BalanceCard
                                icon="✅"
                                label="Paid Out"
                                value={formatCurrency(balance?.total_paid_out_cents || 0)}
                                color="primary"
                            />
                            <BalanceCard
                                icon="⏳"
                                label="Pending"
                                value={formatCurrency(balance?.pending_payout_cents || 0)}
                                color="warning"
                            />
                            <BalanceCard
                                icon="💎"
                                label="Available"
                                value={formatCurrency(balance?.available_balance_cents || 0)}
                                color="accent"
                                highlight
                            />
                        </div>

                        {/* Payout Section */}
                        <div className="card">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-semibold">Request Payout</h2>
                                <button
                                    onClick={() => setShowPayoutModal(true)}
                                    disabled={(balance?.available_balance_cents || 0) < 1000}
                                    className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Request Payout
                                </button>
                            </div>
                            <div className="p-4 rounded-lg bg-[var(--secondary)] border border-[var(--border)]">
                                <div className="flex items-center gap-4">
                                    <div className="text-3xl">🏦</div>
                                    <div>
                                        <div className="font-medium">Stripe Connect</div>
                                        <div className="text-sm text-[var(--muted)]">
                                            Payouts are processed via Stripe. Minimum payout is $10.00.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Commission Info */}
                        <div className="card">
                            <h2 className="text-xl font-semibold mb-4">Commission Structure</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-500/20 to-transparent border border-emerald-500/30">
                                    <div className="text-4xl font-bold text-emerald-400">80%</div>
                                    <div className="text-lg font-medium mt-1">Your Earnings</div>
                                    <div className="text-sm text-[var(--muted)] mt-2">
                                        You keep 80% of every sale from your templates
                                    </div>
                                </div>
                                <div className="p-4 rounded-lg bg-gradient-to-br from-[var(--primary)]/20 to-transparent border border-[var(--primary)]/30">
                                    <div className="text-4xl font-bold text-[var(--primary)]">20%</div>
                                    <div className="text-lg font-medium mt-1">Platform Fee</div>
                                    <div className="text-sm text-[var(--muted)] mt-2">
                                        Platform commission for hosting and distribution
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Pricing Guidelines */}
                        <div className="card">
                            <h2 className="text-xl font-semibold mb-4">Pricing Guidelines</h2>
                            <div className="space-y-4">
                                <div className="flex items-center gap-4 p-3 rounded-lg bg-[var(--secondary)]">
                                    <span className="text-2xl">💵</span>
                                    <div>
                                        <div className="font-medium">Minimum Price: $1.99</div>
                                        <div className="text-sm text-[var(--muted)]">
                                            All premium templates must be priced at $1.99 or higher
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 p-3 rounded-lg bg-[var(--secondary)]">
                                    <span className="text-2xl">📊</span>
                                    <div>
                                        <div className="font-medium">Recommended: $4.99 - $19.99</div>
                                        <div className="text-sm text-[var(--muted)]">
                                            Most successful templates are priced in this range
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 p-3 rounded-lg bg-[var(--secondary)]">
                                    <span className="text-2xl">💳</span>
                                    <div>
                                        <div className="font-medium">Minimum Payout: $10.00</div>
                                        <div className="text-sm text-[var(--muted)]">
                                            Earnings must reach $10.00 before requesting a payout
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Payout Modal */}
            {showPayoutModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="card w-full max-w-md m-4 animate-slideIn">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold">Request Payout</h2>
                            <button
                                onClick={() => setShowPayoutModal(false)}
                                className="text-[var(--muted)] hover:text-white"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1.5">
                                    Available Balance
                                </label>
                                <div className="text-2xl font-bold text-[var(--accent)]">
                                    {formatCurrency(balance?.available_balance_cents || 0)}
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1.5">
                                    Payout Amount (USD)
                                </label>
                                <input
                                    type="number"
                                    min="10"
                                    step="0.01"
                                    value={payoutAmount}
                                    onChange={(e) => setPayoutAmount(e.target.value)}
                                    placeholder="10.00"
                                    className="input"
                                />
                                <div className="text-xs text-[var(--muted)] mt-1">
                                    Minimum: $10.00
                                </div>
                            </div>
                            <button
                                onClick={handleRequestPayout}
                                disabled={requesting}
                                className="btn btn-primary w-full"
                            >
                                {requesting ? 'Processing...' : 'Request Payout'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function BalanceCard({
    icon,
    label,
    value,
    color,
    highlight,
}: {
    icon: string;
    label: string;
    value: string;
    color: 'primary' | 'accent' | 'success' | 'warning';
    highlight?: boolean;
}) {
    const colorClasses = {
        primary: 'from-[var(--primary)]/20 to-transparent border-[var(--primary)]/30',
        accent: 'from-[var(--accent)]/20 to-transparent border-[var(--accent)]/30',
        success: 'from-emerald-500/20 to-transparent border-emerald-500/30',
        warning: 'from-amber-500/20 to-transparent border-amber-500/30',
    };

    return (
        <div
            className={`card bg-gradient-to-br ${colorClasses[color]} border ${highlight ? 'ring-2 ring-[var(--accent)]/50' : ''
                }`}
        >
            <div className="text-2xl mb-2">{icon}</div>
            <div className="text-sm text-[var(--muted)] mb-1">{label}</div>
            <div className={`text-2xl font-bold ${highlight ? 'text-[var(--accent)]' : ''}`}>
                {value}
            </div>
        </div>
    );
}
