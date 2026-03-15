package api

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

func TestErrorHandler(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name        string
		handlerErr  error
		wantStatus  int
		wantMessage string
	}{
		{
			name:        "custom http error",
			handlerErr:  NewError(fiber.StatusTeapot, "short and stout"),
			wantStatus:  fiber.StatusTeapot,
			wantMessage: "short and stout",
		},
		{
			name:        "fiber error",
			handlerErr:  fiber.NewError(fiber.StatusNotFound, "missing"),
			wantStatus:  fiber.StatusNotFound,
			wantMessage: "missing",
		},
		{
			name:        "unexpected error",
			handlerErr:  errors.New("boom"),
			wantStatus:  fiber.StatusInternalServerError,
			wantMessage: "internal server error",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			app := fiber.New(fiber.Config{ErrorHandler: ErrorHandler})
			app.Get("/", func(fiber.Ctx) error {
				return tt.handlerErr
			})

			req := httptest.NewRequest(http.MethodGet, "http://example.com/", nil)
			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}

			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}

			var body envelope
			if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
				t.Fatalf("Decode() error = %v", err)
			}

			if body.Success {
				t.Fatal("response marked success for error case")
			}
			if body.Message != tt.wantMessage {
				t.Fatalf("message = %q, want %q", body.Message, tt.wantMessage)
			}
			if body.Data != nil {
				t.Fatalf("data = %#v, want nil", body.Data)
			}
		})
	}
}

func TestMapAuthError(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name        string
		input       error
		wantStatus  int
		wantMessage string
		wantSameErr bool
	}{
		{
			name:        "invalid credentials",
			input:       authpkg.ErrInvalidCredentials,
			wantStatus:  fiber.StatusUnauthorized,
			wantMessage: "账号或密码错误",
		},
		{
			name:        "invalid account",
			input:       authpkg.ErrInvalidAccount,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: authpkg.ErrInvalidAccount.Error(),
		},
		{
			name:        "invalid name",
			input:       authpkg.ErrInvalidName,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: authpkg.ErrInvalidName.Error(),
		},
		{
			name:        "weak password",
			input:       authpkg.ErrWeakPassword,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: authpkg.ErrWeakPassword.Error(),
		},
		{
			name:        "duplicate account",
			input:       database.ErrConflict,
			wantStatus:  fiber.StatusConflict,
			wantMessage: "账号已存在",
		},
		{
			name:        "unknown error passes through",
			input:       errors.New("boom"),
			wantSameErr: true,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := mapAuthError(tt.input, "fallback")
			if tt.wantSameErr {
				if !errors.Is(got, tt.input) {
					t.Fatalf("mapAuthError(%v) = %v, want original error", tt.input, got)
				}
				return
			}

			var httpErr *HTTPError
			if !errors.As(got, &httpErr) {
				t.Fatalf("mapAuthError(%v) returned %T, want *HTTPError", tt.input, got)
			}
			if httpErr.Status != tt.wantStatus {
				t.Fatalf("status = %d, want %d", httpErr.Status, tt.wantStatus)
			}
			if httpErr.Message != tt.wantMessage {
				t.Fatalf("message = %q, want %q", httpErr.Message, tt.wantMessage)
			}
		})
	}
}
