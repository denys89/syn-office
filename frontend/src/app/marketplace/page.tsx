'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api, AgentTemplate } from '@/lib/api';

interface Category {
    id: string;
    name: string;
    slug: string;
    description: string;
    icon: string;
    display_order: number;
}

interface MarketplaceResponse {
    agents: AgentTemplate[];
    total: number;
    limit: number;
    offset: number;
}

interface CategoriesResponse {
    categories: Category[];
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

function RatingStars({ rating, count }: { rating: number; count: number }) {
    return (
        <div className="flex items-center gap-1">
            <div className="flex">
                {[1, 2, 3, 4, 5].map((star) => (
                    <span
                        key={star}
                        className={`text-sm ${star <= Math.round(rating) ? 'text-yellow-400' : 'text-gray-600'}`}
                    >
                        ★
                    </span>
                ))}
            </div>
            <span className="text-xs text-gray-400">({count})</span>
        </div>
    );
}

function AgentCard({ agent }: { agent: AgentTemplate }) {
    const gradient = roleColors[agent.role] || 'from-gray-500 to-gray-600';
    const icon = roleIcons[agent.role] || '🤖';

    return (
        <Link href={`/marketplace/${agent.id}`}>
            <div className="group relative bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden hover:border-purple-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10">
                {/* Featured Badge */}
                {agent.is_featured && (
                    <div className="absolute top-2 right-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-xs font-bold px-2 py-1 rounded-full">
                        ⭐ Featured
                    </div>
                )}

                {/* Premium Badge */}
                {agent.is_premium && (
                    <div className="absolute top-2 left-2 bg-gradient-to-r from-purple-500 to-pink-500 text-xs font-bold px-2 py-1 rounded-full">
                        💎 Premium
                    </div>
                )}

                {/* Header with gradient */}
                <div className={`h-20 bg-gradient-to-r ${gradient} opacity-80`} />

                {/* Avatar */}
                <div className="relative -mt-10 px-4">
                    <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-2xl shadow-lg border-4 border-gray-800`}>
                        {icon}
                    </div>
                </div>

                {/* Content */}
                <div className="p-4 pt-3">
                    <h3 className="text-lg font-bold text-white group-hover:text-purple-400 transition-colors">
                        {agent.name}
                    </h3>
                    <p className="text-sm text-purple-400 mb-2">{agent.role}</p>
                    <p className="text-xs text-gray-400 line-clamp-2 mb-3">
                        {agent.description || agent.system_prompt?.substring(0, 100) + '...'}
                    </p>

                    {/* Skill Tags */}
                    <div className="flex flex-wrap gap-1 mb-3">
                        {agent.skill_tags?.slice(0, 3).map((tag) => (
                            <span
                                key={tag}
                                className="text-xs bg-gray-700/50 text-gray-300 px-2 py-0.5 rounded-full"
                            >
                                {tag}
                            </span>
                        ))}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between border-t border-gray-700/50 pt-3">
                        <RatingStars rating={agent.rating_average || 0} count={agent.rating_count || 0} />
                        <span className="text-xs text-gray-500">
                            {agent.download_count || 0} installs
                        </span>
                    </div>
                </div>
            </div>
        </Link>
    );
}

export default function MarketplacePage() {
    const [agents, setAgents] = useState<AgentTemplate[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState('featured');
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        loadCategories();
    }, []);

    useEffect(() => {
        loadAgents();
    }, [selectedCategory, sortBy]);

    const loadCategories = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/marketplace/categories`);
            const data: CategoriesResponse = await res.json();
            setCategories(data.categories || []);
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    };

    const loadAgents = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (selectedCategory) params.set('category', selectedCategory);
            if (sortBy) params.set('sort', sortBy);
            params.set('limit', '20');

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/marketplace/agents?${params}`);
            const data: MarketplaceResponse = await res.json();
            setAgents(data.agents || []);
            setTotal(data.total || 0);
        } catch (error) {
            console.error('Failed to load agents:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            loadAgents();
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/marketplace/search?q=${encodeURIComponent(searchQuery)}`);
            const data = await res.json();
            setAgents(data.agents || []);
            setTotal(data.agents?.length || 0);
        } catch (error) {
            console.error('Failed to search agents:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            {/* Header */}
            <header className="sticky top-0 z-50 backdrop-blur-lg bg-gray-900/80 border-b border-gray-800">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Link href="/office" className="text-gray-400 hover:text-white transition-colors">
                                ← Back to Office
                            </Link>
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                                Agent Marketplace
                            </h1>
                        </div>
                        <div className="flex items-center gap-4">
                            {/* Search */}
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="Search agents..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                    className="w-64 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 pl-10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                                />
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">🔍</span>
                            </div>
                            {/* Sort */}
                            <select
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value)}
                                className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                            >
                                <option value="featured">Featured</option>
                                <option value="popular">Most Popular</option>
                                <option value="rating">Top Rated</option>
                                <option value="newest">Newest</option>
                            </select>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-6 py-8">
                <div className="flex gap-8">
                    {/* Sidebar - Categories */}
                    <aside className="w-64 flex-shrink-0">
                        <div className="sticky top-28 bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4">
                            <h2 className="text-lg font-semibold text-white mb-4">Categories</h2>
                            <ul className="space-y-1">
                                <li>
                                    <button
                                        onClick={() => setSelectedCategory('')}
                                        className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${selectedCategory === '' ? 'bg-purple-500/20 text-purple-400' : 'text-gray-400 hover:bg-gray-700/50'
                                            }`}
                                    >
                                        All Agents
                                    </button>
                                </li>
                                {categories.map((cat) => (
                                    <li key={cat.id}>
                                        <button
                                            onClick={() => setSelectedCategory(cat.slug)}
                                            className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center gap-2 ${selectedCategory === cat.slug ? 'bg-purple-500/20 text-purple-400' : 'text-gray-400 hover:bg-gray-700/50'
                                                }`}
                                        >
                                            <span>{cat.icon}</span>
                                            <span>{cat.name}</span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </aside>

                    {/* Main Content */}
                    <main className="flex-1">
                        {/* Results header */}
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedCategory ? categories.find(c => c.slug === selectedCategory)?.name : 'All Agents'}
                                <span className="text-sm text-gray-500 ml-2">({total} agents)</span>
                            </h2>
                        </div>

                        {/* Loading State */}
                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {[1, 2, 3, 4, 5, 6].map((i) => (
                                    <div key={i} className="bg-gray-800/50 rounded-xl h-64 animate-pulse" />
                                ))}
                            </div>
                        ) : agents.length === 0 ? (
                            <div className="text-center py-16">
                                <span className="text-6xl mb-4 block">🔍</span>
                                <h3 className="text-xl text-white mb-2">No agents found</h3>
                                <p className="text-gray-400">Try a different search or category</p>
                            </div>
                        ) : (
                            /* Agent Grid */
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {agents.map((agent) => (
                                    <AgentCard key={agent.id} agent={agent} />
                                ))}
                            </div>
                        )}
                    </main>
                </div>
            </div>
        </div>
    );
}
