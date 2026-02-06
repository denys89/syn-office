package config

import (
	"log"

	"github.com/kelseyhightower/envconfig"
)

// Config holds all application configuration
type Config struct {
	// Database
	DatabaseURL string `envconfig:"DATABASE_URL" default:"postgres://synoffice:synoffice_secret@localhost:5432/synoffice?sslmode=disable"`

	// JWT
	JWTSecret string `envconfig:"JWT_SECRET" default:"your-super-secret-jwt-key-change-in-production"`

	// Services
	OrchestratorURL string `envconfig:"ORCHESTRATOR_URL" default:"http://localhost:8000"`

	// Internal API
	InternalAPIKey string `envconfig:"INTERNAL_API_KEY" default:"dev-internal-key-change-in-production"`

	// Server
	BackendPort string `envconfig:"BACKEND_PORT" default:"8080"`
	Environment string `envconfig:"ENVIRONMENT" default:"development"`
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	var cfg Config
	err := envconfig.Process("", &cfg)
	if err != nil {
		return nil, err
	}

	log.Printf("Configuration loaded: Environment=%s, Port=%s", cfg.Environment, cfg.BackendPort)
	log.Printf("Internal API Key: %s... (length: %d)", cfg.InternalAPIKey[:min(10, len(cfg.InternalAPIKey))], len(cfg.InternalAPIKey))
	return &cfg, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// MustLoad loads configuration and panics if it fails
func MustLoad() *Config {
	cfg, err := Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}
	return cfg
}
