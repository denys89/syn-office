'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, Agent, api } from '@/lib/api';
import { wsClient, WSMessage } from '@/lib/websocket';
import { MessageBubble } from './MessageBubble';

interface ChatWindowProps {
    conversationId: string;
    agents: Agent[];
    userId: string;
}

export function ChatWindow({ conversationId, agents, userId }: ChatWindowProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadMessages();

        // Subscribe to new messages from agents
        const unsubMessage = wsClient.on('new_message', (data: WSMessage) => {
            const payload = data.payload as {
                conversation_id: string;
                sender_type: string;
                sender_id: string;
                content: string;
            };

            // Only add messages for this conversation
            if (payload.conversation_id === conversationId) {
                const newMessage: Message = {
                    id: `ws-${Date.now()}`,
                    office_id: '',
                    conversation_id: conversationId,
                    sender_type: payload.sender_type as 'user' | 'agent',
                    sender_id: payload.sender_id,
                    content: payload.content,
                    created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, newMessage]);
            }
        });

        return () => {
            unsubMessage();
        };
    }, [conversationId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const loadMessages = async () => {
        setIsLoading(true);
        try {
            const { messages: loadedMessages } = await api.getMessages(conversationId);
            setMessages(loadedMessages || []);
        } catch (error) {
            console.error('Failed to load messages:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSend = async () => {
        if (!input.trim() || isSending) return;

        const content = input.trim();
        setInput('');
        setIsSending(true);

        // Optimistically add message
        const tempMessage: Message = {
            id: `temp-${Date.now()}`,
            office_id: '',
            conversation_id: conversationId,
            sender_type: 'user',
            sender_id: userId,
            content,
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, tempMessage]);

        try {
            const message = await api.sendMessage(conversationId, content);
            // Replace temp message with real one
            setMessages((prev) => prev.map((m) => (m.id === tempMessage.id ? message : m)));
        } catch (error) {
            console.error('Failed to send message:', error);
            // Remove temp message on error
            setMessages((prev) => prev.filter((m) => m.id !== tempMessage.id));
        } finally {
            setIsSending(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="animate-pulse-slow text-[var(--muted)]">Loading messages...</div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col min-h-0">{/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-[var(--muted)]">
                        <div className="text-4xl mb-4">💬</div>
                        <p>No messages yet. Start the conversation!</p>
                    </div>
                ) : (
                    messages.map((message) => (
                        <MessageBubble
                            key={message.id}
                            message={message}
                            agents={agents}
                            isCurrentUser={message.sender_id === userId}
                        />
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-[var(--border)]">
                <div className="flex gap-3">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type a message... (use @name to mention an agent)"
                        className="input resize-none min-h-[44px] max-h-[120px]"
                        rows={1}
                        disabled={isSending}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isSending}
                        className="btn btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSending ? (
                            <span className="animate-pulse">...</span>
                        ) : (
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                                className="w-5 h-5"
                            >
                                <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
                            </svg>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
