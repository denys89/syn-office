import { WS_URL, api } from './api';

type EventHandler = (data: WSMessage) => void;

export interface WSMessage {
    event_id: string;
    event_type: string;
    payload: Record<string, unknown>;
}

class WebSocketClient {
    private ws: WebSocket | null = null;
    private handlers: Map<string, Set<EventHandler>> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;

    connect() {
        const token = api.getToken();
        if (!token) {
            console.error('No token available for WebSocket connection');
            return;
        }

        this.ws = new WebSocket(`${WS_URL}?token=${token}`);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.emit('connected', { event_id: '', event_type: 'connected', payload: {} });
        };

        this.ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);
                this.emit(message.event_type, message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit('disconnected', { event_id: '', event_type: 'disconnected', payload: {} });
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    private attemptReconnect() {
        // Don't attempt to reconnect if there's no token
        const token = api.getToken();
        if (!token) {
            console.log('No token available, skipping WebSocket reconnect');
            return;
        }

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`Attempting to reconnect in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        }
    }

    send(eventType: string, payload: Record<string, unknown>) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message: WSMessage = {
                event_id: crypto.randomUUID(),
                event_type: eventType,
                payload,
            };
            this.ws.send(JSON.stringify(message));
        }
    }

    on(eventType: string, handler: EventHandler) {
        if (!this.handlers.has(eventType)) {
            this.handlers.set(eventType, new Set());
        }
        this.handlers.get(eventType)!.add(handler);

        // Return unsubscribe function
        return () => {
            this.handlers.get(eventType)?.delete(handler);
        };
    }

    private emit(eventType: string, message: WSMessage) {
        const handlers = this.handlers.get(eventType);
        if (handlers) {
            handlers.forEach((handler) => handler(message));
        }

        // Also emit to wildcard handlers
        const wildcardHandlers = this.handlers.get('*');
        if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => handler(message));
        }
    }
}

// Singleton instance
export const wsClient = new WebSocketClient();
