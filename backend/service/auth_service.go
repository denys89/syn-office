package service

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

// AuthService handles authentication operations
type AuthService struct {
	userRepo   domain.UserRepository
	officeRepo domain.OfficeRepository
	jwtSecret  []byte
}

// NewAuthService creates a new AuthService instance
func NewAuthService(userRepo domain.UserRepository, officeRepo domain.OfficeRepository, jwtSecret string) *AuthService {
	return &AuthService{
		userRepo:   userRepo,
		officeRepo: officeRepo,
		jwtSecret:  []byte(jwtSecret),
	}
}

// RegisterInput contains registration data
type RegisterInput struct {
	Email    string
	Password string
	Name     string
}

// LoginInput contains login data
type LoginInput struct {
	Email    string
	Password string
}

// AuthResponse contains authentication result
type AuthResponse struct {
	User   *domain.User   `json:"user"`
	Office *domain.Office `json:"office"`
	Token  string         `json:"token"`
}

// JWTClaims defines the JWT token claims
type JWTClaims struct {
	UserID   uuid.UUID `json:"user_id"`
	OfficeID uuid.UUID `json:"office_id"`
	Email    string    `json:"email"`
	jwt.RegisteredClaims
}

// Register creates a new user account with a default office
func (s *AuthService) Register(ctx context.Context, input RegisterInput) (*AuthResponse, error) {
	// Check if user already exists
	existing, _ := s.userRepo.GetByEmail(ctx, input.Email)
	if existing != nil {
		return nil, domain.ErrAlreadyExists
	}

	// Hash password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(input.Password), bcrypt.DefaultCost)
	if err != nil {
		return nil, err
	}

	// Create user
	user := &domain.User{
		ID:           uuid.New(),
		Email:        input.Email,
		PasswordHash: string(hashedPassword),
		Name:         input.Name,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, err
	}

	// Create default office
	office := &domain.Office{
		ID:        uuid.New(),
		UserID:    user.ID,
		Name:      user.Name + "'s Office",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := s.officeRepo.Create(ctx, office); err != nil {
		return nil, err
	}

	// Generate JWT token
	token, err := s.generateToken(user, office)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		User:   user,
		Office: office,
		Token:  token,
	}, nil
}

// Login authenticates a user and returns a JWT token
func (s *AuthService) Login(ctx context.Context, input LoginInput) (*AuthResponse, error) {
	// Find user by email
	user, err := s.userRepo.GetByEmail(ctx, input.Email)
	if err != nil {
		return nil, domain.ErrInvalidCredentials
	}

	// Verify password
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(input.Password)); err != nil {
		return nil, domain.ErrInvalidCredentials
	}

	// Get user's office
	offices, err := s.officeRepo.GetByUserID(ctx, user.ID)
	if err != nil || len(offices) == 0 {
		return nil, domain.ErrNotFound
	}

	office := offices[0] // Use first office for now

	// Generate JWT token
	token, err := s.generateToken(user, office)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		User:   user,
		Office: office,
		Token:  token,
	}, nil
}

// ValidateToken validates a JWT token and returns the claims
func (s *AuthService) ValidateToken(tokenString string) (*JWTClaims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &JWTClaims{}, func(token *jwt.Token) (interface{}, error) {
		return s.jwtSecret, nil
	})

	if err != nil {
		return nil, domain.ErrUnauthorized
	}

	claims, ok := token.Claims.(*JWTClaims)
	if !ok || !token.Valid {
		return nil, domain.ErrUnauthorized
	}

	return claims, nil
}

// generateToken creates a new JWT token
func (s *AuthService) generateToken(user *domain.User, office *domain.Office) (string, error) {
	claims := JWTClaims{
		UserID:   user.ID,
		OfficeID: office.ID,
		Email:    user.Email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "synoffice",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(s.jwtSecret)
}
