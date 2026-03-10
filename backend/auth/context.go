package auth

import (
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

type principalContextKey struct{}

type Principal struct {
	UserID  string
	Name    string
	Account string
	Role    database.UserRole
	TokenID string
}

func StorePrincipal(c fiber.Ctx, principal Principal) {
	fiber.StoreInContext(c, principalContextKey{}, principal)
}

func CurrentPrincipal(c fiber.Ctx) (Principal, bool) {
	return fiber.ValueFromContext[Principal](c, principalContextKey{})
}
