'use client';

import { Message, Agent } from '@/lib/api';
import { AgentAvatar } from './AgentAvatar';
import { FeedbackButtons } from './FeedbackButtons';
import { formatDistanceToNow } from '@/lib/utils';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MessageBubbleProps {
    message: Message;
    agents: Agent[];
    isCurrentUser: boolean;
}

export function MessageBubble({ message, agents, isCurrentUser }: MessageBubbleProps) {
    const isUser = message.sender_type === 'user';
    const agent = !isUser ? agents.find((a) => a.id === message.sender_id) : null;
    const isRealMessage = !message.id.startsWith('temp-') && !message.id.startsWith('ws-');

    const components: Components = {
        code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
                <div className="rounded-md overflow-hidden my-2">
                    <SyntaxHighlighter
                        {...props}
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                    >
                        {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                </div>
            ) : (
                <code
                    {...props}
                    className={`${className} ${isUser ? 'bg-white/20' : 'bg-black/30'} rounded px-1 py-0.5`}
                >
                    {children}
                </code>
            );
        },
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        a: ({ href, children }) => (
            <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={`underline hover:opacity-80 ${isUser ? 'text-white' : 'text-[var(--primary)]'}`}
            >
                {children}
            </a>
        ),
        blockquote: ({ children }) => (
            <blockquote className={`border-l-4 pl-4 italic my-2 ${isUser ? 'border-white/50' : 'border-[var(--primary)] text-[var(--muted)]'}`}>
                {children}
            </blockquote>
        ),
        table: ({ children }) => (
            <div className="overflow-x-auto my-2 rounded border border-[var(--border)]">
                <table className="min-w-full divide-y divide-[var(--border)]">{children}</table>
            </div>
        ),
        th: ({ children }) => (
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider bg-black/20">
                {children}
            </th>
        ),
        td: ({ children }) => (
            <td className="px-3 py-2 text-sm border-t border-[var(--border)] bg-black/5">
                {children}
            </td>
        ),
    };

    return (
        <div className={`flex gap-3 animate-slideIn ${isUser ? 'flex-row-reverse' : ''}`}>
            {!isUser && agent && (
                <div className="flex-shrink-0">
                    <AgentAvatar agent={agent} size="sm" />
                </div>
            )}

            <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%] lg:max-w-[70%]`}>
                {!isUser && agent && (
                    <span className="text-xs text-[var(--muted)] mb-1 ml-1">
                        {agent.custom_name || agent.template?.name}
                    </span>
                )}

                <div className={`px-4 py-2.5 overflow-hidden ${isUser ? 'message-user' : 'message-agent'}`}>
                    <div className="text-sm markdown-content">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={components}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                </div>

                <div className="flex items-center gap-2 mt-1 mx-1">
                    <span className="text-xs text-[var(--muted)]">
                        {formatDistanceToNow(new Date(message.created_at))}
                    </span>

                    {/* Show feedback buttons for agent messages only */}
                    {!isUser && isRealMessage && (
                        <FeedbackButtons messageId={message.id} />
                    )}
                </div>
            </div>
        </div>
    );
}
