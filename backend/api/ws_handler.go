package api

import (
	"encoding/json"
	"log"
	"sync"

	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/contrib/websocket"
	"github.com/google/uuid"
)

// WSHandler handles WebSocket connections
type WSHandler struct {
	authService *service.AuthService
	clients     map[uuid.UUID]map[*websocket.Conn]bool
	mu          sync.RWMutex
}

// NewWSHandler creates a new WSHandler
func NewWSHandler(authService *service.AuthService) *WSHandler {
	return &WSHandler{
		authService: authService,
		clients:     make(map[uuid.UUID]map[*websocket.Conn]bool),
	}
}

// WSMessage represents a WebSocket message
type WSMessage struct {
	EventID   string         `json:"event_id"`
	EventType string         `json:"event_type"`
	Payload   map[string]any `json:"payload"`
}

// HandleWS handles WebSocket connections
func (h *WSHandler) HandleWS(c *websocket.Conn) {
	// Get token from query parameter
	token := c.Query("token")
	if token == "" {
		c.WriteJSON(WSMessage{
			EventType: "error",
			Payload:   map[string]any{"message": "missing token"},
		})
		c.Close()
		return
	}

	// Validate token
	claims, err := h.authService.ValidateToken(token)
	if err != nil {
		c.WriteJSON(WSMessage{
			EventType: "error",
			Payload:   map[string]any{"message": "invalid token"},
		})
		c.Close()
		return
	}

	officeID := claims.OfficeID

	// Register client
	h.registerClient(officeID, c)
	defer h.unregisterClient(officeID, c)

	// Send connected event
	c.WriteJSON(WSMessage{
		EventID:   uuid.New().String(),
		EventType: "connected",
		Payload: map[string]any{
			"user_id":   claims.UserID.String(),
			"office_id": officeID.String(),
		},
	})

	// Listen for messages
	for {
		_, msg, err := c.ReadMessage()
		if err != nil {
			log.Printf("WebSocket read error: %v", err)
			break
		}

		var wsMsg WSMessage
		if err := json.Unmarshal(msg, &wsMsg); err != nil {
			log.Printf("WebSocket message parse error: %v", err)
			continue
		}

		// Handle different event types
		h.handleMessage(c, officeID, &wsMsg)
	}
}

// handleMessage processes incoming WebSocket messages
func (h *WSHandler) handleMessage(c *websocket.Conn, officeID uuid.UUID, msg *WSMessage) {
	switch msg.EventType {
	case "ping":
		c.WriteJSON(WSMessage{
			EventID:   msg.EventID,
			EventType: "pong",
			Payload:   map[string]any{},
		})
	case "typing":
		// Broadcast typing indicator to other clients
		h.broadcastToOffice(officeID, WSMessage{
			EventID:   uuid.New().String(),
			EventType: "typing",
			Payload:   msg.Payload,
		}, c)
	default:
		log.Printf("Unknown event type: %s", msg.EventType)
	}
}

// registerClient adds a client to the office clients map
func (h *WSHandler) registerClient(officeID uuid.UUID, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.clients[officeID] == nil {
		h.clients[officeID] = make(map[*websocket.Conn]bool)
	}
	h.clients[officeID][c] = true
}

// unregisterClient removes a client from the office clients map
func (h *WSHandler) unregisterClient(officeID uuid.UUID, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.clients[officeID] != nil {
		delete(h.clients[officeID], c)
		if len(h.clients[officeID]) == 0 {
			delete(h.clients, officeID)
		}
	}
}

// BroadcastToOffice sends a message to all clients in an office
func (h *WSHandler) BroadcastToOffice(officeID uuid.UUID, msg WSMessage) {
	h.broadcastToOffice(officeID, msg, nil)
}

// broadcastToOffice sends a message to all clients in an office, optionally excluding one
func (h *WSHandler) broadcastToOffice(officeID uuid.UUID, msg WSMessage, exclude *websocket.Conn) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	clients := h.clients[officeID]
	for client := range clients {
		if client != exclude {
			if err := client.WriteJSON(msg); err != nil {
				log.Printf("WebSocket write error: %v", err)
			}
		}
	}
}
