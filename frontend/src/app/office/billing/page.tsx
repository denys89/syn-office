'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, SubscriptionStatus, Tier, Wallet } from '@/lib/api';

export default function Billing() {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
    const [tiers, setTiers] = useState<Tier[]>([]);
    const [wallet, setWallet] = useState<Wallet | null>(null);
    const [loading, setLoading] = useState(true);
    const [upgrading, setUpgrading] = useState<string | null>(null);

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
            const [subData, tierData, walletData] = await Promise.all([
                api.getSubscriptionStatus().catch(() => null),
                api.getTiers().catch(() => ({ tiers: [] })),
                api.getWalletBalance().catch(() => null),
            ]);
            setSubscription(subData);
            setTiers(tierData.tiers || []);
            setWallet(walletData);
        } catch (error) {
            console.error('Failed to load billing data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpgrade = async (tierId: string) => {
        setUpgrading(tierId);
        try {
            // In production, this would integrate with Stripe
            await api.upgradeTier(tierId, 'pm_placeholder');
            await loadData();
        } catch (error) {
            console.error('Failed to upgrade:', error);
            alert('Upgrade failed. Please try again.');
        } finally {
            setUpgrading(null);
        }
    };

    const formatCurrency = (cents: number) => `$${(cents / 100).toFixed(2)}`;
    const formatCredits = (credits: number) => credits.toLocaleString();

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
                    <h1 className="text-2xl font-bold gradient-text">Billing & Subscription</h1>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8">
                {loading ? (
                    <div className="text-center py-20 text-[var(--muted)]">
                        <div className="animate-pulse">Loading billing info...</div>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {/* Current Balance Card */}
                        <div className="card bg-gradient-to-br from-[var(--primary)]/20 to-transparent border border-[var(--primary)]/30">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-sm text-[var(--muted)] mb-1">Current Balance</div>
                                    <div className="text-4xl font-bold">
                                        💎 {formatCredits(wallet?.balance || 0)} Credits
                                    </div>
                                    {subscription && (
                                        <div className="text-sm text-[var(--muted)] mt-2">
                                            {subscription.days_remaining} days until renewal •{' '}
                                            {formatCredits(subscription.period_credits_consumed)} /{' '}
                                            {formatCredits(subscription.period_credits_allocated)} used this period
                                        </div>
                                    )}
                                </div>
                                <button className="btn btn-primary">
                                    + Buy Credits
                                </button>
                            </div>
                        </div>

                        {/* Current Subscription */}
                        {subscription && (
                            <div className="card">
                                <h2 className="text-xl font-semibold mb-4">Current Plan</h2>
                                <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--secondary)] border border-[var(--border)]">
                                    <div>
                                        <div className="text-lg font-bold">{subscription.tier_definition?.name || 'Free'}</div>
                                        <div className="text-[var(--muted)] text-sm">
                                            {formatCredits(subscription.tier_definition?.credits_per_period || 0)} credits/month
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-2xl font-bold">
                                            {formatCurrency(subscription.tier_definition?.price_monthly_cents || 0)}
                                        </div>
                                        <div className="text-[var(--muted)] text-sm">per month</div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Available Plans */}
                        <div>
                            <h2 className="text-xl font-semibold mb-4">Available Plans</h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {tiers.length === 0 ? (
                                    <>
                                        <PlanCard
                                            name="Free"
                                            price={0}
                                            credits={100}
                                            features={['100 credits/month', 'Basic models', 'Community support']}
                                            isCurrent={!subscription}
                                            onSelect={() => { }}
                                            loading={false}
                                        />
                                        <PlanCard
                                            name="Pro"
                                            price={1999}
                                            credits={5000}
                                            features={['5,000 credits/month', 'All models', 'Priority support', 'Analytics dashboard']}
                                            isCurrent={false}
                                            isPopular
                                            onSelect={() => handleUpgrade('pro')}
                                            loading={upgrading === 'pro'}
                                        />
                                        <PlanCard
                                            name="Enterprise"
                                            price={9999}
                                            credits={50000}
                                            features={['50,000 credits/month', 'All models', 'Dedicated support', 'Custom integrations', 'SLA guarantee']}
                                            isCurrent={false}
                                            onSelect={() => handleUpgrade('enterprise')}
                                            loading={upgrading === 'enterprise'}
                                        />
                                    </>
                                ) : (
                                    tiers.map((tier, i) => (
                                        <PlanCard
                                            key={tier.id}
                                            name={tier.name}
                                            price={tier.price_monthly_cents}
                                            credits={tier.credits_per_period}
                                            features={tier.features || []}
                                            isCurrent={subscription?.tier_definition?.id === tier.id}
                                            isPopular={i === 1}
                                            onSelect={() => handleUpgrade(tier.id)}
                                            loading={upgrading === tier.id}
                                        />
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Usage Progress */}
                        {subscription && (
                            <div className="card">
                                <h2 className="text-xl font-semibold mb-4">This Period's Usage</h2>
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>Credits Used</span>
                                        <span>
                                            {formatCredits(subscription.period_credits_consumed)} / {formatCredits(subscription.period_credits_allocated)}
                                        </span>
                                    </div>
                                    <div className="h-4 bg-[var(--secondary)] rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] rounded-full transition-all"
                                            style={{
                                                width: `${Math.min(
                                                    (subscription.period_credits_consumed / Math.max(subscription.period_credits_allocated, 1)) * 100,
                                                    100
                                                )}%`,
                                            }}
                                        />
                                    </div>
                                    <div className="text-xs text-[var(--muted)]">
                                        Resets in {subscription.days_remaining} days
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

function PlanCard({
    name,
    price,
    credits,
    features,
    isCurrent,
    isPopular,
    onSelect,
    loading,
}: {
    name: string;
    price: number;
    credits: number;
    features: string[];
    isCurrent: boolean;
    isPopular?: boolean;
    onSelect: () => void;
    loading: boolean;
}) {
    return (
        <div
            className={`card relative ${isPopular ? 'border-[var(--primary)] shadow-lg shadow-[var(--primary)]/20' : ''
                } ${isCurrent ? 'border-[var(--accent)]' : ''}`}
        >
            {isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-[var(--primary)] text-white text-xs font-bold rounded-full">
                    POPULAR
                </div>
            )}
            {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-[var(--accent)] text-white text-xs font-bold rounded-full">
                    CURRENT
                </div>
            )}
            <div className="text-center pt-4">
                <h3 className="text-xl font-bold">{name}</h3>
                <div className="mt-4">
                    <span className="text-4xl font-bold">${(price / 100).toFixed(0)}</span>
                    <span className="text-[var(--muted)]">/month</span>
                </div>
                <div className="text-sm text-[var(--muted)] mt-1">
                    {credits.toLocaleString()} credits/month
                </div>
            </div>
            <ul className="mt-6 space-y-3">
                {features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                        <span className="text-[var(--primary)]">✓</span>
                        {feature}
                    </li>
                ))}
            </ul>
            <button
                onClick={onSelect}
                disabled={isCurrent || loading}
                className={`btn w-full mt-6 ${isCurrent
                        ? 'bg-[var(--secondary)] text-[var(--muted)] cursor-not-allowed'
                        : isPopular
                            ? 'btn-primary'
                            : 'border border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--primary)]/10'
                    }`}
            >
                {loading ? 'Processing...' : isCurrent ? 'Current Plan' : 'Select Plan'}
            </button>
        </div>
    );
}
