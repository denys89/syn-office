'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function Home() {
  const { isAuthenticated, isLoading, login, register } = useAuth();
  const router = useRouter();
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/office');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      if (isLoginMode) {
        await login(email, password);
      } else {
        await register(email, password, name);
      }
      router.push('/office');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse-slow text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero Section */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] mb-4">
              <span className="text-3xl">🏢</span>
            </div>
            <h1 className="text-3xl font-bold gradient-text mb-2">Synoffice</h1>
            <p className="text-[var(--muted)]">Your AI-Native Digital Office</p>
          </div>

          {/* Auth Form */}
          <div className="card">
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setIsLoginMode(true)}
                className={`flex-1 py-2 rounded-lg font-medium transition-all ${isLoginMode
                    ? 'bg-[var(--primary)] text-white'
                    : 'text-[var(--muted)] hover:text-white'
                  }`}
              >
                Login
              </button>
              <button
                onClick={() => setIsLoginMode(false)}
                className={`flex-1 py-2 rounded-lg font-medium transition-all ${!isLoginMode
                    ? 'bg-[var(--primary)] text-white'
                    : 'text-[var(--muted)] hover:text-white'
                  }`}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLoginMode && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                    className="input"
                    required={!isLoginMode}
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input"
                  required
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-[var(--error)]/10 border border-[var(--error)]/20 text-[var(--error)] text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary w-full py-3"
              >
                {isSubmitting ? (
                  <span className="animate-pulse">Please wait...</span>
                ) : isLoginMode ? (
                  'Enter Your Office'
                ) : (
                  'Create Your Office'
                )}
              </button>
            </form>
          </div>

          {/* Features */}
          <div className="mt-8 grid grid-cols-2 gap-4">
            {[
              { icon: '👨‍💻', title: 'AI Employees', desc: 'Work with specialized agents' },
              { icon: '💬', title: 'Chat Interface', desc: 'Natural conversations' },
              { icon: '🎯', title: 'Task Execution', desc: 'Get things done' },
              { icon: '🧠', title: 'Memory', desc: 'Context-aware agents' },
            ].map((feature) => (
              <div key={feature.title} className="card card-hover p-4">
                <div className="text-2xl mb-2">{feature.icon}</div>
                <h3 className="font-medium text-sm">{feature.title}</h3>
                <p className="text-xs text-[var(--muted)]">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="p-4 text-center text-[var(--muted)] text-sm border-t border-[var(--border)]">
        Synoffice MVP © {new Date().getFullYear()}
      </footer>
    </div>
  );
}
