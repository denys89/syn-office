package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/repository"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

type MarketplaceHandler struct {
	marketplaceService *service.MarketplaceService
}

func NewMarketplaceHandler(marketplaceService *service.MarketplaceService) *MarketplaceHandler {
	return &MarketplaceHandler{marketplaceService: marketplaceService}
}

// ListAgents handles GET /marketplace/agents
func (h *MarketplaceHandler) ListAgents(c *fiber.Ctx) error {
	filter := repository.MarketplaceFilter{
		Category: c.Query("category"),
		Search:   c.Query("search"),
		SortBy:   c.Query("sort", "featured"),
	}

	// Parse limit and offset
	if limit, err := strconv.Atoi(c.Query("limit", "20")); err == nil {
		filter.Limit = limit
	}
	if offset, err := strconv.Atoi(c.Query("offset", "0")); err == nil {
		filter.Offset = offset
	}

	// Parse boolean filters
	if featured := c.Query("featured"); featured != "" {
		val := featured == "true"
		filter.IsFeatured = &val
	}
	if premium := c.Query("premium"); premium != "" {
		val := premium == "true"
		filter.IsPremium = &val
	}

	templates, total, err := h.marketplaceService.ListAgents(c.Context(), filter)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(fiber.Map{
		"agents": templates,
		"total":  total,
		"limit":  filter.Limit,
		"offset": filter.Offset,
	})
}

// GetAgentDetails handles GET /marketplace/agents/:id
func (h *MarketplaceHandler) GetAgentDetails(c *fiber.Ctx) error {
	id, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid agent ID"})
	}

	template, err := h.marketplaceService.GetAgentDetails(c.Context(), id)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Agent not found"})
	}

	return c.JSON(template)
}

// GetFeaturedAgents handles GET /marketplace/featured
func (h *MarketplaceHandler) GetFeaturedAgents(c *fiber.Ctx) error {
	templates, err := h.marketplaceService.GetFeaturedAgents(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fiber.Map{"agents": templates})
}

// GetCategories handles GET /marketplace/categories
func (h *MarketplaceHandler) GetCategories(c *fiber.Ctx) error {
	categories, err := h.marketplaceService.GetCategories(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fiber.Map{"categories": categories})
}

// SearchAgents handles GET /marketplace/search
func (h *MarketplaceHandler) SearchAgents(c *fiber.Ctx) error {
	query := c.Query("q")
	if query == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Search query required"})
	}

	limit := 20
	if l, err := strconv.Atoi(c.Query("limit", "20")); err == nil {
		limit = l
	}

	templates, err := h.marketplaceService.SearchAgents(c.Context(), query, limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fiber.Map{"agents": templates})
}

// CreateReview handles POST /marketplace/agents/:id/reviews
func (h *MarketplaceHandler) CreateReview(c *fiber.Ctx) error {
	templateID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid agent ID"})
	}

	// Get user ID from context (set by auth middleware)
	userID, ok := c.Locals("user_id").(uuid.UUID)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	var req struct {
		Rating     int    `json:"rating"`
		Title      string `json:"title"`
		ReviewText string `json:"review_text"`
	}
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request body"})
	}

	if req.Rating < 1 || req.Rating > 5 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Rating must be between 1 and 5"})
	}
	if req.ReviewText == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Review text is required"})
	}

	err = h.marketplaceService.AddReview(c.Context(), userID, templateID, req.Rating, req.Title, req.ReviewText)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	return c.Status(fiber.StatusCreated).JSON(fiber.Map{"message": "Review submitted successfully"})
}

// GetReviews handles GET /marketplace/agents/:id/reviews
func (h *MarketplaceHandler) GetReviews(c *fiber.Ctx) error {
	templateID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid agent ID"})
	}

	limit := 20
	offset := 0
	if l, err := strconv.Atoi(c.Query("limit", "20")); err == nil {
		limit = l
	}
	if o, err := strconv.Atoi(c.Query("offset", "0")); err == nil {
		offset = o
	}

	reviews, err := h.marketplaceService.GetReviews(c.Context(), templateID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(fiber.Map{"reviews": reviews})
}
