package api

import (
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
)

// Router holds all route handlers
type Router struct {
	authHandler        *AuthHandler
	agentHandler       *AgentHandler
	chatHandler        *ChatHandler
	wsHandler          *WSHandler
	marketplaceHandler *MarketplaceHandler
	feedbackHandler    *FeedbackHandler
	internalHandler    *InternalHandler
	authService        *service.AuthService
	internalAPIKey     string
}

// NewRouter creates a new Router
func NewRouter(
	authHandler *AuthHandler,
	agentHandler *AgentHandler,
	chatHandler *ChatHandler,
	wsHandler *WSHandler,
	marketplaceHandler *MarketplaceHandler,
	feedbackHandler *FeedbackHandler,
	internalHandler *InternalHandler,
	authService *service.AuthService,
	internalAPIKey string,
) *Router {
	return &Router{
		authHandler:        authHandler,
		agentHandler:       agentHandler,
		chatHandler:        chatHandler,
		wsHandler:          wsHandler,
		marketplaceHandler: marketplaceHandler,
		feedbackHandler:    feedbackHandler,
		internalHandler:    internalHandler,
		authService:        authService,
		internalAPIKey:     internalAPIKey,
	}
}

// Setup configures all routes
func (r *Router) Setup(app *fiber.App) {
	// Middleware
	app.Use(logger.New())
	app.Use(recover.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,PUT,PATCH,DELETE,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept,Authorization",
	}))

	// Health check
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	// API v1
	v1 := app.Group("/api/v1")

	// Public routes
	auth := v1.Group("/auth")
	auth.Post("/register", r.authHandler.Register)
	auth.Post("/login", r.authHandler.Login)

	// Marketplace routes (public for browsing)
	marketplace := v1.Group("/marketplace")
	marketplace.Get("/agents", r.marketplaceHandler.ListAgents)
	marketplace.Get("/agents/:id", r.marketplaceHandler.GetAgentDetails)
	marketplace.Get("/agents/:id/reviews", r.marketplaceHandler.GetReviews)
	marketplace.Get("/featured", r.marketplaceHandler.GetFeaturedAgents)
	marketplace.Get("/categories", r.marketplaceHandler.GetCategories)
	marketplace.Get("/search", r.marketplaceHandler.SearchAgents)

	// Internal routes (for service-to-service communication)
	// IMPORTANT: Must be defined BEFORE protected routes to avoid JWT middleware
	internal := v1.Group("/internal")
	internal.Use(InternalAPIKeyMiddleware(r.internalAPIKey))
	internal.Post("/task-complete", r.internalHandler.TaskComplete)

	// Protected routes
	protected := v1.Group("")
	protected.Use(AuthMiddleware(r.authService))

	// Auth routes (protected)
	protected.Get("/auth/me", r.authHandler.Me)

	// Agent routes
	agents := protected.Group("/agents")
	agents.Get("/templates", r.agentHandler.GetTemplates)
	agents.Post("/select", r.agentHandler.SelectAgent)
	agents.Post("/select-multiple", r.agentHandler.SelectMultipleAgents)
	agents.Get("", r.agentHandler.GetAgents)
	agents.Get("/:id", r.agentHandler.GetAgent)
	agents.Get("/:id/feedback-summary", r.feedbackHandler.GetAgentFeedbackSummary)
	agents.Get("/:id/memories", r.feedbackHandler.GetAgentMemories)
	agents.Delete("/:id", r.agentHandler.DeactivateAgent)

	// Conversation routes
	conversations := protected.Group("/conversations")
	conversations.Post("", r.chatHandler.CreateConversation)
	conversations.Get("", r.chatHandler.GetConversations)
	conversations.Get("/:id", r.chatHandler.GetConversation)
	conversations.Post("/:id/messages", r.chatHandler.SendMessage)
	conversations.Get("/:id/messages", r.chatHandler.GetMessages)

	// Message feedback routes
	messages := protected.Group("/messages")
	messages.Post("/:id/feedback", r.feedbackHandler.CreateMessageFeedback)

	// Marketplace routes (protected for reviews)
	protectedMarketplace := protected.Group("/marketplace")
	protectedMarketplace.Post("/agents/:id/reviews", r.marketplaceHandler.CreateReview)

	// WebSocket route (with upgrade middleware)
	app.Use("/ws", func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})
	app.Get("/ws", websocket.New(r.wsHandler.HandleWS))
}
