'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface FeedbackButtonsProps {
    messageId: string;
    onFeedbackSent?: (type: 'positive' | 'negative') => void;
}

export function FeedbackButtons({ messageId, onFeedbackSent }: FeedbackButtonsProps) {
    const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const [comment, setComment] = useState('');

    const handleFeedback = async (type: 'positive' | 'negative') => {
        if (isSubmitting || feedbackGiven) return;

        setIsSubmitting(true);
        try {
            await api.submitFeedback(messageId, {
                feedback_type: type,
                rating: type === 'positive' ? 5 : 1,
            });
            setFeedbackGiven(type);
            onFeedbackSent?.(type);
        } catch (error) {
            console.error('Failed to submit feedback:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDetailedFeedback = async () => {
        if (!comment.trim() || isSubmitting) return;

        setIsSubmitting(true);
        try {
            await api.submitFeedback(messageId, {
                feedback_type: 'correction',
                comment: comment.trim(),
            });
            setFeedbackGiven('negative');
            setShowDetails(false);
            setComment('');
        } catch (error) {
            console.error('Failed to submit detailed feedback:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (feedbackGiven) {
        return (
            <div className="flex items-center gap-1 text-xs text-[var(--muted)]">
                {feedbackGiven === 'positive' ? (
                    <span className="flex items-center gap-1">
                        <span className="text-green-500">👍</span>
                        Thanks for the feedback!
                    </span>
                ) : (
                    <span className="flex items-center gap-1">
                        <span className="text-orange-500">📝</span>
                        Feedback recorded
                    </span>
                )}
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1">
                <button
                    onClick={() => handleFeedback('positive')}
                    disabled={isSubmitting}
                    className="p-1.5 rounded-full hover:bg-[var(--surface-hover)] transition-colors disabled:opacity-50"
                    title="Helpful response"
                    aria-label="Mark as helpful"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className="w-4 h-4 text-[var(--muted)] hover:text-green-500 transition-colors"
                    >
                        <path d="M1 8.25a1.25 1.25 0 112.5 0v7.5a1.25 1.25 0 11-2.5 0v-7.5zM11 3V1.7c0-.268.14-.526.395-.607A2 2 0 0114 3c0 .995-.182 1.948-.514 2.826-.204.54.166 1.174.744 1.174h2.52c1.243 0 2.261 1.01 2.146 2.247a23.864 23.864 0 01-1.341 5.974 1.999 1.999 0 01-1.9 1.368H9.333a2 2 0 01-1.414-.586l-.858-.858a2 2 0 01-.586-1.414V8c0-.53.211-1.039.586-1.414L10.17 3.47a2.5 2.5 0 01.83-.594z" />
                    </svg>
                </button>
                <button
                    onClick={() => handleFeedback('negative')}
                    disabled={isSubmitting}
                    className="p-1.5 rounded-full hover:bg-[var(--surface-hover)] transition-colors disabled:opacity-50"
                    title="Not helpful"
                    aria-label="Mark as not helpful"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className="w-4 h-4 text-[var(--muted)] hover:text-red-500 transition-colors"
                    >
                        <path d="M19 11.75a1.25 1.25 0 11-2.5 0v-7.5a1.25 1.25 0 112.5 0v7.5zM9 17v1.3c0 .268-.14.526-.395.607A2 2 0 016 17c0-.995.182-1.948.514-2.826.204-.54-.166-1.174-.744-1.174h-2.52c-1.243 0-2.261-1.01-2.146-2.247a23.864 23.864 0 011.341-5.974A1.999 1.999 0 014.345 3.5h6.322a2 2 0 011.414.586l.858.858A2 2 0 0113.525 6.5v5.264c0 .53-.211 1.039-.586 1.414L9.83 16.53a2.5 2.5 0 01-.83.594z" />
                    </svg>
                </button>
                <button
                    onClick={() => setShowDetails(!showDetails)}
                    disabled={isSubmitting}
                    className="p-1.5 rounded-full hover:bg-[var(--surface-hover)] transition-colors disabled:opacity-50"
                    title="Provide detailed feedback"
                    aria-label="Provide detailed feedback"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className="w-4 h-4 text-[var(--muted)] hover:text-[var(--primary)] transition-colors"
                    >
                        <path fillRule="evenodd" d="M2 3.5A1.5 1.5 0 013.5 2h9A1.5 1.5 0 0114 3.5v11.75A2.75 2.75 0 0016.75 18h-12A2.75 2.75 0 012 15.25V3.5zm3.75 7a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-4.5zm0-3a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-4.5z" clipRule="evenodd" />
                    </svg>
                </button>
            </div>

            {showDetails && (
                <div className="flex flex-col gap-2 p-2 bg-[var(--surface-active)] rounded-lg animate-slideIn">
                    <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="What could be improved?"
                        className="input text-sm min-h-[60px] resize-none"
                        rows={2}
                    />
                    <div className="flex justify-end gap-2">
                        <button
                            onClick={() => setShowDetails(false)}
                            className="btn btn-secondary text-xs px-3 py-1"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleDetailedFeedback}
                            disabled={!comment.trim() || isSubmitting}
                            className="btn btn-primary text-xs px-3 py-1 disabled:opacity-50"
                        >
                            {isSubmitting ? 'Sending...' : 'Send Feedback'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
