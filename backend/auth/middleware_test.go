package auth

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

func TestRequireRoles(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		principal  *Principal
		wantStatus int
	}{
		{
			name:       "missing principal",
			principal:  nil,
			wantStatus: fiber.StatusUnauthorized,
		},
		{
			name: "insufficient permissions",
			principal: &Principal{
				UserID: "user-1",
				Role:   database.RoleUser,
			},
			wantStatus: fiber.StatusForbidden,
		},
		{
			name: "allowed role",
			principal: &Principal{
				UserID: "admin-1",
				Role:   database.RoleAdmin,
			},
			wantStatus: fiber.StatusOK,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			app := fiber.New(fiber.Config{PassLocalsToContext: true})
			app.Get(
				"/admin",
				func(c fiber.Ctx) error {
					if tt.principal != nil {
						StorePrincipal(c, *tt.principal)
					}
					return c.Next()
				},
				RequireRoles(database.RoleAdmin),
				func(c fiber.Ctx) error {
					current, ok := CurrentPrincipal(c)
					if !ok {
						return fiber.NewError(fiber.StatusInternalServerError, "principal missing")
					}
					return c.SendString(current.UserID)
				},
			)

			req := httptest.NewRequest(http.MethodGet, "http://example.com/admin", nil)
			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}

			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}

			if tt.wantStatus == fiber.StatusOK {
				body, err := io.ReadAll(resp.Body)
				if err != nil {
					t.Fatalf("ReadAll() error = %v", err)
				}
				if string(body) != tt.principal.UserID {
					t.Fatalf("body = %q, want %q", string(body), tt.principal.UserID)
				}
			}
		})
	}
}

func TestExtractBearerToken(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		header  string
		want    string
		wantErr bool
	}{
		{name: "valid", header: "Bearer abc.def", want: "abc.def"},
		{name: "case insensitive scheme", header: "bearer abc", want: "abc"},
		{name: "extra spaces", header: "  Bearer    abc  ", want: "abc"},
		{name: "missing token", header: "Bearer", wantErr: true},
		{name: "wrong scheme", header: "Token abc", wantErr: true},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := extractBearerToken(tt.header)
			if (err != nil) != tt.wantErr {
				t.Fatalf("extractBearerToken(%q) error = %v, wantErr %v", tt.header, err, tt.wantErr)
			}
			if got != tt.want {
				t.Fatalf("extractBearerToken(%q) = %q, want %q", tt.header, got, tt.want)
			}
		})
	}
}
