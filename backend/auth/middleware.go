package auth

import (
	"errors"
	"strings"

	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

func RequireAuthenticated(store *database.Store, tokenManager *TokenManager) fiber.Handler {
	return func(c fiber.Ctx) error {
		rawToken, err := extractBearerToken(c.Get("Authorization"))
		if err != nil {
			return fiber.NewError(fiber.StatusUnauthorized, "missing or invalid authorization header")
		}

		claims, err := tokenManager.ParseToken(rawToken)
		if err != nil || claims.Subject == "" || claims.ID == "" {
			return fiber.NewError(fiber.StatusUnauthorized, "invalid or expired token")
		}

		session, err := store.GetSessionByToken(c.Context(), claims.Subject, claims.ID, HashToken(rawToken))
		if err != nil {
			if errors.Is(err, database.ErrNotFound) {
				return fiber.NewError(fiber.StatusUnauthorized, "token has been revoked")
			}
			return err
		}

		StorePrincipal(c, Principal{
			UserID:  session.UserID,
			Name:    session.Name,
			Account: session.Account,
			Role:    session.Role,
			TokenID: session.TokenID,
		})

		return c.Next()
	}
}

func RequireRoles(roles ...database.UserRole) fiber.Handler {
	allowed := make(map[database.UserRole]struct{}, len(roles))
	for _, role := range roles {
		allowed[role] = struct{}{}
	}

	return func(c fiber.Ctx) error {
		principal, ok := CurrentPrincipal(c)
		if !ok {
			return fiber.NewError(fiber.StatusUnauthorized, "authentication required")
		}

		if _, exists := allowed[principal.Role]; !exists {
			return fiber.NewError(fiber.StatusForbidden, "insufficient permissions")
		}

		return c.Next()
	}
}

func extractBearerToken(value string) (string, error) {
	parts := strings.Fields(strings.TrimSpace(value))
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
		return "", errors.New("invalid bearer token")
	}
	return parts[1], nil
}
