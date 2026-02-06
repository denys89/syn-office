'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, AgentTemplate } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

interface Review {
    id: string;
    template_id: string;
    user_id: string;
    rating: number;
    title: string;
    review_text: string;
    created_at: string;
    updated_at: string;
}

interface ReviewsResponse {
    reviews: Review[];
}

const roleColors: Record<string, string> = {
    Engineer: 'from-blue-500 to-cyan-500',
    Analyst: 'from-purple-500 to-pink-500',
    Writer: 'from-green-500 to-emerald-500',
    Planner: 'from-orange-500 to-yellow-500',
    Marketing: 'from-red-500 to-rose-500',
    Design: 'from-indigo-500 to-violet-500',
    Research: 'from-teal-500 to-cyan-500',
    Support: 'from-amber-500 to-orange-500',
};

const roleIcons: Record<string, string> = {
    Engineer: '💻',
    Analyst: '📊',
    Writer: '✍️',
    Planner: '📋',
    Marketing: '📢',
    Design: '🎨',
    Research: '🔍',
    Support: '💬',
};

function RatingStars({ rating, interactive = false, onChange }: {
    rating: number;
    interactive?: boolean;
    onChange?: (rating: number) => void;
}) {
    return (
        <div className="flex">
            {[1, 2, 3, 4, 5].map((star) => (
                <button
                    key={star}
                    onClick={() => interactive && onChange?.(star)}
                    disabled={!interactive}
                    className={`text-2xl transition-colors ${star <= rating ? 'text-yellow-400' : 'text-gray-600'
                        } ${interactive ? 'hover:text-yellow-300 cursor-pointer' : 'cursor-default'}`}
                >
                    ★
                </button>
            ))}
        </div>
    );
}

function ReviewForm({ templateId, onSubmit }: { templateId: string; onSubmit: () => void }) {
    const [rating, setRating] = useState(0);
    const [title, setTitle] = useState('');
    const [reviewText, setReviewText] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (rating === 0) {
            setError('Please select a rating');
            return;
        }
        if (!reviewText.trim()) {
            setError('Please write a review');
            return;
        }

        setSubmitting(true);
        setError('');

        try {
            await api.post(`/marketplace/agents/${templateId}/reviews`, {
                rating,
                title,
                review_text: reviewText,
            });
            onSubmit();
            setRating(0);
            setTitle('');
            setReviewText('');
        } catch (err) {
            setError('Failed to submit review. You may have already reviewed this agent.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
            <h3 className="text-lg font-semibold text-white mb-4">Write a Review</h3>

            <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">Your Rating</label>
                <RatingStars rating={rating} interactive onChange={setRating} />
            </div>

            <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">Title (optional)</label>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Sum up your experience"
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                />
            </div>

            <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">Your Review</label>
                <textarea
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder="Share your experience with this agent..."
                    rows={4}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 resize-none"
                />
            </div>

            {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

            <button
                type="submit"
                disabled={submitting}
                className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            >
                {submitting ? 'Submitting...' : 'Submit Review'}
            </button>
        </form>
    );
}

export default function AgentDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user, agents } = useAuth();
    const [agent, setAgent] = useState<AgentTemplate | null>(null);
    const [reviews, setReviews] = useState<Review[]>([]);
    const [loading, setLoading] = useState(true);
    const [adding, setAdding] = useState(false);
    const [showReviewForm, setShowReviewForm] = useState(false);

    const agentId = params.id as string;

    useEffect(() => {
        loadAgent();
        loadReviews();
    }, [agentId]);

    const loadAgent = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/marketplace/agents/${agentId}`);
            if (!res.ok) throw new Error('Agent not found');
            const data = await res.json();
            setAgent(data);
        } catch (error) {
            console.error('Failed to load agent:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadReviews = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/marketplace/agents/${agentId}/reviews`);
            const data: ReviewsResponse = await res.json();
            setReviews(data.reviews || []);
        } catch (error) {
            console.error('Failed to load reviews:', error);
        }
    };

    const handleAddToOffice = async () => {
        if (!agent) return;

        setAdding(true);
        try {
            await api.post('/agents/select', { template_id: agent.id });
            router.push('/office');
        } catch (error) {
            console.error('Failed to add agent:', error);
        } finally {
            setAdding(false);
        }
    };

    const isAlreadyInOffice = agents?.some(a => a.template_id === agentId);

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
                <div className="animate-spin text-4xl">⏳</div>
            </div>
        );
    }

    if (!agent) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
                <div className="text-center">
                    <span className="text-6xl mb-4 block">😕</span>
                    <h1 className="text-2xl text-white mb-4">Agent Not Found</h1>
                    <Link href="/marketplace" className="text-purple-400 hover:underline">
                        Back to Marketplace
                    </Link>
                </div>
            </div>
        );
    }

    const gradient = roleColors[agent.role] || 'from-gray-500 to-gray-600';
    const icon = roleIcons[agent.role] || '🤖';

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            {/* Header */}
            <header className="sticky top-0 z-50 backdrop-blur-lg bg-gray-900/80 border-b border-gray-800">
                <div className="max-w-5xl mx-auto px-6 py-4">
                    <Link href="/marketplace" className="text-gray-400 hover:text-white transition-colors">
                        ← Back to Marketplace
                    </Link>
                </div>
            </header>

            <div className="max-w-5xl mx-auto px-6 py-8">
                {/* Hero Section */}
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden mb-8">
                    <div className={`h-32 bg-gradient-to-r ${gradient}`} />

                    <div className="p-6 pt-0">
                        <div className="flex items-end gap-6 -mt-12">
                            <div className={`w-24 h-24 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center text-4xl shadow-xl border-4 border-gray-800`}>
                                {icon}
                            </div>

                            <div className="flex-1 pb-2">
                                <div className="flex items-center gap-3">
                                    <h1 className="text-3xl font-bold text-white">{agent.name}</h1>
                                    {agent.is_featured && (
                                        <span className="bg-gradient-to-r from-yellow-500 to-orange-500 text-xs font-bold px-2 py-1 rounded-full">
                                            ⭐ Featured
                                        </span>
                                    )}
                                    {agent.is_premium && (
                                        <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-xs font-bold px-2 py-1 rounded-full">
                                            💎 Premium
                                        </span>
                                    )}
                                </div>
                                <p className="text-lg text-purple-400">{agent.role}</p>
                            </div>

                            <button
                                onClick={handleAddToOffice}
                                disabled={adding || isAlreadyInOffice}
                                className={`px-6 py-3 rounded-lg font-semibold transition-all ${isAlreadyInOffice
                                        ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90'
                                    }`}
                            >
                                {isAlreadyInOffice ? '✓ In Your Office' : adding ? 'Adding...' : '+ Add to My Office'}
                            </button>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-3 gap-8">
                    {/* Main Content */}
                    <div className="col-span-2 space-y-8">
                        {/* Description */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <h2 className="text-xl font-semibold text-white mb-4">About this Agent</h2>
                            <p className="text-gray-300 leading-relaxed">
                                {agent.description || agent.system_prompt}
                            </p>
                        </div>

                        {/* Skills */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <h2 className="text-xl font-semibold text-white mb-4">Skills & Capabilities</h2>
                            <div className="flex flex-wrap gap-2">
                                {agent.skill_tags?.map((tag) => (
                                    <span
                                        key={tag}
                                        className="bg-purple-500/20 text-purple-300 px-4 py-2 rounded-lg text-sm"
                                    >
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {/* Reviews Section */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-semibold text-white">Reviews</h2>
                                {user && !showReviewForm && (
                                    <button
                                        onClick={() => setShowReviewForm(true)}
                                        className="text-purple-400 hover:text-purple-300 transition-colors"
                                    >
                                        Write a Review
                                    </button>
                                )}
                            </div>

                            {showReviewForm && (
                                <div className="mb-6">
                                    <ReviewForm
                                        templateId={agentId}
                                        onSubmit={() => {
                                            setShowReviewForm(false);
                                            loadReviews();
                                            loadAgent();
                                        }}
                                    />
                                </div>
                            )}

                            {reviews.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">No reviews yet. Be the first to review!</p>
                            ) : (
                                <div className="space-y-4">
                                    {reviews.map((review) => (
                                        <div key={review.id} className="border-b border-gray-700/50 pb-4 last:border-0">
                                            <div className="flex items-center gap-2 mb-2">
                                                <RatingStars rating={review.rating} />
                                                {review.title && <span className="text-white font-medium">• {review.title}</span>}
                                            </div>
                                            <p className="text-gray-300">{review.review_text}</p>
                                            <p className="text-xs text-gray-500 mt-2">
                                                {new Date(review.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">
                        {/* Stats */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Stats</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-400">Rating</span>
                                    <div className="flex items-center gap-2">
                                        <RatingStars rating={agent.rating_average || 0} />
                                        <span className="text-white">{(agent.rating_average || 0).toFixed(1)}</span>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-400">Reviews</span>
                                    <span className="text-white">{agent.rating_count || 0}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-400">Installs</span>
                                    <span className="text-white">{agent.download_count || 0}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-400">Version</span>
                                    <span className="text-white">{agent.version || '1.0.0'}</span>
                                </div>
                            </div>
                        </div>

                        {/* Author */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Author</h3>
                            <p className="text-gray-300">{agent.author_name || 'Synoffice Team'}</p>
                        </div>

                        {/* Category */}
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Category</h3>
                            <Link
                                href={`/marketplace?category=${agent.category}`}
                                className="text-purple-400 hover:underline capitalize"
                            >
                                {agent.category || 'General'}
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
