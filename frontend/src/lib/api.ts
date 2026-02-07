// API Configuration
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws';

// API Client
class ApiClient {
    private baseUrl: string;
    private token: string | null = null;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    setToken(token: string) {
        this.token = token;
        if (typeof window !== 'undefined') {
            localStorage.setItem('token', token);
        }
    }

    getToken(): string | null {
        if (this.token) return this.token;
        if (typeof window !== 'undefined') {
            this.token = localStorage.getItem('token');
        }
        return this.token;
    }

    clearToken() {
        this.token = null;
        if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
        }
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}/api/v1${endpoint}`;
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    }

    // Generic POST method
    async post<T>(endpoint: string, data?: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    // Auth
    async register(email: string, password: string, name: string) {
        const data = await this.request<AuthResponse>('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, name }),
        });
        this.setToken(data.token);
        return data;
    }

    async login(email: string, password: string) {
        const data = await this.request<AuthResponse>('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setToken(data.token);
        return data;
    }

    async me() {
        return this.request<{ user_id: string; office_id: string; email: string }>('/auth/me');
    }

    // Agents
    async getAgentTemplates() {
        return this.request<{ templates: AgentTemplate[] }>('/agents/templates');
    }

    async selectAgents(templateIds: string[]) {
        return this.request<{ agents: Agent[] }>('/agents/select-multiple', {
            method: 'POST',
            body: JSON.stringify({ template_ids: templateIds }),
        });
    }

    async getAgents() {
        return this.request<{ agents: Agent[] }>('/agents');
    }

    // Conversations
    async getConversations() {
        return this.request<{ conversations: Conversation[] }>('/conversations');
    }

    async createConversation(type: 'direct' | 'group', agentIds: string[], name?: string) {
        return this.request<Conversation>('/conversations', {
            method: 'POST',
            body: JSON.stringify({ type, agent_ids: agentIds, name }),
        });
    }

    async getMessages(conversationId: string, limit = 50, offset = 0) {
        return this.request<{ messages: Message[] }>(
            `/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`
        );
    }

    async sendMessage(conversationId: string, content: string) {
        return this.request<Message>(`/conversations/${conversationId}/messages`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        });
    }

    // Feedback
    async submitFeedback(messageId: string, feedback: FeedbackRequest) {
        return this.request<AgentFeedback>(`/messages/${messageId}/feedback`, {
            method: 'POST',
            body: JSON.stringify(feedback),
        });
    }

    async getAgentFeedbackSummary(agentId: string) {
        return this.request<FeedbackSummary>(`/agents/${agentId}/feedback-summary`);
    }

    async getAgentMemories(agentId: string, type?: string, limit = 50) {
        const params = new URLSearchParams();
        if (type) params.set('type', type);
        params.set('limit', limit.toString());
        return this.request<{ memories: AgentMemory[]; count: number }>(
            `/agents/${agentId}/memories?${params.toString()}`
        );
    }

    // Credits
    async getWalletBalance() {
        return this.request<Wallet>('/credits/balance');
    }

    async purchaseCredits(amountCents: number, paymentMethodId: string) {
        return this.request<{ transaction_id: string; new_balance: number }>('/credits/purchase', {
            method: 'POST',
            body: JSON.stringify({ amount_cents: amountCents, payment_method_id: paymentMethodId }),
        });
    }

    // Subscriptions
    async getSubscriptionStatus() {
        return this.request<SubscriptionStatus>('/subscription/summary');
    }

    async getTiers() {
        return this.request<{ tiers: Tier[] }>('/subscription/tiers');
    }

    async upgradeTier(tierId: string, paymentMethodId: string) {
        return this.request<{ subscription_id: string }>('/subscription/upgrade', {
            method: 'POST',
            body: JSON.stringify({ tier_id: tierId, payment_method_id: paymentMethodId }),
        });
    }

    // Analytics
    async getUsageSummary(period: '30d' | '7d' | 'today' = '30d') {
        return this.request<UsageSummary>(`/usage/summary?period=${period}`);
    }

    async getUsageBreakdown(days = 30) {
        return this.request<UsageBreakdown>(`/usage/breakdown?days=${days}`);
    }

    async getDailyUsage(days = 30) {
        return this.request<{ daily_usage: UsageDaily[] }>(`/usage/daily?days=${days}`);
    }

    // Earnings
    async getAuthorBalance() {
        return this.request<AuthorBalance>('/author/balance');
    }
}

// Types
export interface AuthResponse {
    user: User;
    office: Office;
    token: string;
}

export interface User {
    id: string;
    email: string;
    name: string;
    created_at: string;
}

export interface Office {
    id: string;
    user_id: string;
    name: string;
    created_at: string;
}

export interface AgentTemplate {
    id: string;
    name: string;
    role: string;
    system_prompt: string;
    avatar_url?: string;
    skill_tags: string[];
    // Marketplace fields
    author_id?: string;
    author_name?: string;
    category?: string;
    description?: string;
    is_featured?: boolean;
    is_public?: boolean;
    is_premium?: boolean;
    price_cents?: number;
    download_count?: number;
    rating_average?: number;
    rating_count?: number;
    version?: string;
    status?: string;
    created_at: string;
    updated_at?: string;
}

export interface Agent {
    id: string;
    office_id: string;
    template_id: string;
    template?: AgentTemplate;
    custom_name?: string;
    is_active: boolean;
    created_at: string;
}

export interface Conversation {
    id: string;
    office_id: string;
    type: 'direct' | 'group';
    name?: string;
    participants?: Agent[];
    created_at: string;
    updated_at: string;
}

export interface Message {
    id: string;
    office_id: string;
    conversation_id: string;
    sender_type: 'user' | 'agent';
    sender_id: string;
    content: string;
    metadata?: Record<string, unknown>;
    created_at: string;
}

// Feedback Types
export interface FeedbackRequest {
    feedback_type: 'positive' | 'negative' | 'correction';
    rating?: number;
    comment?: string;
    correction_content?: string;
}

export interface AgentFeedback {
    id: string;
    office_id: string;
    agent_id: string;
    message_id?: string;
    task_id?: string;
    feedback_type: 'positive' | 'negative' | 'correction';
    rating?: number;
    comment?: string;
    original_content?: string;
    correction_content?: string;
    created_at: string;
}

export interface FeedbackSummary {
    agent_id: string;
    total_feedback: number;
    positive_count: number;
    negative_count: number;
    correction_count: number;
    average_rating: number;
    memory_count: number;
    total_interactions: number;
}

export interface AgentMemory {
    id: string;
    office_id: string;
    agent_id: string;
    key: string;
    value: string;
    vector_id?: string;
    memory_type: 'fact' | 'preference' | 'correction' | 'insight';
    importance_score: number;
    created_at: string;
    updated_at: string;
}

// Credit Types
export interface Wallet {
    id: string;
    office_id: string;
    balance: number;
    currency: string;
    updated_at: string;
}

// Subscription Types
export interface Tier {
    id: string;
    name: string;
    price_monthly_cents: number;
    credits_per_period: number;
    features: string[];
}

export interface SubscriptionStatus {
    subscription: {
        id: string;
        tier_id: string;
        status: string;
        current_period_end: string;
    };
    tier_definition: Tier;
    current_balance: number;
    period_credits_allocated: number;
    period_credits_consumed: number;
    days_remaining: number;
}

// Analytics Types
export interface UsageSummary {
    period: string;
    credits_used: number;
    credits_remaining: number;
    tasks_executed: number;
    tokens_processed: number;
    estimated_cost_usd: number;
    local_model_ratio: number;
}

export interface UsageDaily {
    date: string;
    credits_consumed: number;
    tasks_executed: number;
    local_model_tasks: number;
    paid_model_tasks: number;
}

export interface UsageBreakdown {
    usage_by_model: Array<{
        model: string;
        provider: string;
        total_tasks: number;
        total_credits: number;
        percent_of_usage: number;
    }>;
    usage_by_agent: Array<{
        agent_name: string;
        role: string;
        total_tasks: number;
        total_credits: number;
    }>;
}

// Earnings Types
export interface AuthorBalance {
    author_id: string;
    total_earned_cents: number;
    total_paid_out_cents: number;
    pending_payout_cents: number;
    available_balance_cents: number;
}

// Singleton instance
export const api = new ApiClient(API_URL);

