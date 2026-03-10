package auth

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"hire_sense/database"

	"github.com/google/uuid"
)

var (
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrInvalidAccount     = errors.New("account is required")
	ErrInvalidName        = errors.New("name is required")
	ErrWeakPassword       = errors.New("password must be at least 8 characters")
)

type Service struct {
	store        *database.Store
	tokenManager *TokenManager
}

type SignUpInput struct {
	Account  string
	Name     string
	Password string
}

type SignInInput struct {
	Account  string
	Password string
}

func NewService(store *database.Store, tokenManager *TokenManager) *Service {
	return &Service{
		store:        store,
		tokenManager: tokenManager,
	}
}

func (s *Service) SignUp(ctx context.Context, input SignUpInput) (string, error) {
	account := normalizeAccount(input.Account)
	name := strings.TrimSpace(input.Name)

	if account == "" {
		return "", ErrInvalidAccount
	}
	if name == "" {
		return "", ErrInvalidName
	}
	if err := validatePassword(input.Password); err != nil {
		return "", err
	}

	passwordHash, err := HashPassword(input.Password)
	if err != nil {
		return "", fmt.Errorf("hash password: %w", err)
	}

	user, err := s.store.CreateUser(ctx, database.CreateUserParams{
		ID:           uuid.NewString(),
		Name:         name,
		Account:      account,
		PasswordHash: passwordHash,
		Role:         database.RoleUser,
		Job:          database.JobFrontend,
	})
	if err != nil {
		return "", err
	}

	return s.issueSession(ctx, user)
}

func (s *Service) SignIn(ctx context.Context, input SignInInput) (string, error) {
	account := normalizeAccount(input.Account)
	if account == "" {
		return "", ErrInvalidAccount
	}

	user, err := s.store.GetUserByAccount(ctx, account)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return "", ErrInvalidCredentials
		}
		return "", err
	}

	if err := ComparePassword(user.PasswordHash, input.Password); err != nil {
		return "", ErrInvalidCredentials
	}

	return s.issueSession(ctx, user)
}

func (s *Service) SignOut(ctx context.Context, principal Principal) error {
	err := s.store.RevokeToken(ctx, principal.UserID, principal.TokenID)
	if errors.Is(err, database.ErrNotFound) {
		return nil
	}
	return err
}

func (s *Service) ChangePassword(ctx context.Context, userID, password string) error {
	if err := validatePassword(password); err != nil {
		return err
	}

	hash, err := HashPassword(password)
	if err != nil {
		return fmt.Errorf("hash password: %w", err)
	}

	if err := s.store.UpdateUserPassword(ctx, userID, hash); err != nil {
		return err
	}

	if err := s.store.RevokeAllTokensForUser(ctx, userID); err != nil {
		return err
	}

	return nil
}

func (s *Service) issueSession(ctx context.Context, user database.User) (string, error) {
	issuedToken, err := s.tokenManager.IssueToken(user)
	if err != nil {
		return "", err
	}

	if err := s.store.CreateToken(ctx, database.CreateTokenParams{
		ID:        uuid.NewString(),
		TokenID:   issuedToken.TokenID,
		UserID:    user.ID,
		TokenHash: HashToken(issuedToken.Raw),
		ExpiresAt: issuedToken.ExpiresAt,
	}); err != nil {
		return "", err
	}

	return issuedToken.Raw, nil
}

func normalizeAccount(account string) string {
	return strings.ToLower(strings.TrimSpace(account))
}

func validatePassword(password string) error {
	if len(strings.TrimSpace(password)) < 8 {
		return ErrWeakPassword
	}
	return nil
}
