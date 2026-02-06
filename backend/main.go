package main

import (
	"context"
	"log"

	"github.com/denys89/syn-office/backend/api"
	"github.com/denys89/syn-office/backend/config"
	"github.com/denys89/syn-office/backend/repository"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	// Load configuration
	cfg := config.MustLoad()

	// Connect to database
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer pool.Close()

	// Verify database connection
	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Connected to database")

	// Initialize repositories
	userRepo := repository.NewUserRepository(pool)
	officeRepo := repository.NewOfficeRepository(pool)
	agentTemplateRepo := repository.NewAgentTemplateRepository(pool)
	agentRepo := repository.NewAgentRepository(pool, agentTemplateRepo)
	conversationRepo := repository.NewConversationRepository(pool, agentRepo)
	messageRepo := repository.NewMessageRepository(pool)
	taskRepo := repository.NewTaskRepository(pool)
	marketplaceRepo := repository.NewMarketplaceRepository(pool)
	feedbackRepo := repository.NewFeedbackRepository(pool)
	creditRepo := repository.NewCreditRepository(pool)
	subscriptionRepo := repository.NewSubscriptionRepository(pool)
	analyticsRepo := repository.NewAnalyticsRepository(pool)
	earningsRepo := repository.NewEarningsRepository(pool)

	// Initialize services
	authService := service.NewAuthService(userRepo, officeRepo, cfg.JWTSecret)
	agentService := service.NewAgentService(agentRepo, agentTemplateRepo)
	taskService := service.NewTaskService(taskRepo, cfg.OrchestratorURL)
	chatService := service.NewChatService(conversationRepo, messageRepo, agentRepo, taskService)
	marketplaceService := service.NewMarketplaceService(marketplaceRepo)
	feedbackService := service.NewFeedbackService(feedbackRepo, agentRepo, officeRepo)
	creditService := service.NewCreditService(creditRepo, officeRepo)
	subscriptionService := service.NewSubscriptionService(subscriptionRepo, creditRepo, "config/subscription_tiers.yaml")
	analyticsService := service.NewAnalyticsService(analyticsRepo, creditRepo)
	earningsService := service.NewEarningsService(earningsRepo, marketplaceRepo)

	// Initialize handlers
	authHandler := api.NewAuthHandler(authService)
	agentHandler := api.NewAgentHandler(agentService)
	chatHandler := api.NewChatHandler(chatService)
	wsHandler := api.NewWSHandler(authService)
	marketplaceHandler := api.NewMarketplaceHandler(marketplaceService)
	feedbackHandler := api.NewFeedbackHandler(feedbackService)
	internalHandler := api.NewInternalHandler(wsHandler, conversationRepo, creditService)
	creditHandler := api.NewCreditHandler(creditService)
	subscriptionHandler := api.NewSubscriptionHandler(subscriptionService)
	analyticsHandler := api.NewAnalyticsHandler(analyticsService)
	earningsHandler := api.NewEarningsHandler(earningsService)

	router := api.NewRouter(
		authHandler,
		agentHandler,
		chatHandler,
		wsHandler,
		marketplaceHandler,
		feedbackHandler,
		internalHandler,
		creditHandler,
		subscriptionHandler,
		analyticsHandler,
		earningsHandler,
		authService,
		cfg.InternalAPIKey,
	)

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName: "Synoffice API",
	})

	// Setup routes
	router.Setup(app)

	// Start server
	log.Printf("Starting server on port %s", cfg.BackendPort)
	if err := app.Listen(":" + cfg.BackendPort); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
