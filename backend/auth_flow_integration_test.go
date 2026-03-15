//go:build integration

package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"hire_sense/api"
	"hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	_ "github.com/lib/pq"
)

type integrationEnvelope struct {
	Success bool            `json:"success"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

func TestAuthSignUpAndSignOutFlowIntegration(t *testing.T) {
	dbURL := integrationDatabaseURL(t)
	sqlDB := openIntegrationSQLDB(t, dbURL)
	ensureIntegrationSchema(t, sqlDB)

	expectedAccount := fmt.Sprintf("integration-auth-%d@example.com", time.Now().UnixNano())
	signUpAccount := "  " + strings.ToUpper(expectedAccount) + "  "
	expectedName := "Integration User"

	cleanupIntegrationUser(t, sqlDB, expectedAccount)
	t.Cleanup(func() {
		cleanupIntegrationUser(t, sqlDB, expectedAccount)
	})

	store, err := database.Open(dbURL)
	if err != nil {
		t.Fatalf("database.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Fatalf("store.Close() error = %v", err)
		}
	})

	tokenManager, err := auth.NewTokenManager("hiresense-backend-integration", time.Hour)
	if err != nil {
		t.Fatalf("auth.NewTokenManager() error = %v", err)
	}

	app := fiber.New(fiber.Config{
		PassLocalsToContext: true,
		ErrorHandler:        api.ErrorHandler,
	})
	api.RegisterRoutes(app, api.Dependencies{
		Store:           store,
		AuthService:     auth.NewService(store, tokenManager),
		TokenManager:    tokenManager,
		PutReportSecret: "integration-secret",
	})

	signUpResponse := doJSONRequest(t, app, http.MethodPost, "/api/auth/signup", map[string]string{
		"account":  signUpAccount,
		"name":     "  " + expectedName + "  ",
		"password": "Passw0rd!",
	}, "")
	if signUpResponse.status != http.StatusOK {
		t.Fatalf("signup status = %d, want %d (message=%q)", signUpResponse.status, http.StatusOK, signUpResponse.body.Message)
	}
	if !signUpResponse.body.Success {
		t.Fatalf("signup success = false, message = %q", signUpResponse.body.Message)
	}
	if signUpResponse.body.Message != "注册成功" {
		t.Fatalf("signup message = %q, want %q", signUpResponse.body.Message, "注册成功")
	}

	var token string
	if err := json.Unmarshal(signUpResponse.body.Data, &token); err != nil {
		t.Fatalf("json.Unmarshal(signup token) error = %v", err)
	}
	if token == "" {
		t.Fatal("signup token is empty")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	user, err := store.GetUserByAccount(ctx, expectedAccount)
	if err != nil {
		t.Fatalf("store.GetUserByAccount() error = %v", err)
	}
	if user.Account != expectedAccount {
		t.Fatalf("user.Account = %q, want %q", user.Account, expectedAccount)
	}
	if user.Name != expectedName {
		t.Fatalf("user.Name = %q, want %q", user.Name, expectedName)
	}
	if user.Role != database.RoleUser {
		t.Fatalf("user.Role = %q, want %q", user.Role, database.RoleUser)
	}
	if user.Job != database.JobFrontend {
		t.Fatalf("user.Job = %q, want %q", user.Job, database.JobFrontend)
	}

	claims, err := tokenManager.ParseToken(token)
	if err != nil {
		t.Fatalf("tokenManager.ParseToken() error = %v", err)
	}
	if claims.Subject != user.ID {
		t.Fatalf("claims.Subject = %q, want %q", claims.Subject, user.ID)
	}

	session, err := store.GetSessionByToken(ctx, claims.Subject, claims.ID, auth.HashToken(token))
	if err != nil {
		t.Fatalf("store.GetSessionByToken() error = %v", err)
	}
	if session.UserID != user.ID {
		t.Fatalf("session.UserID = %q, want %q", session.UserID, user.ID)
	}

	signOutResponse := doJSONRequest(t, app, http.MethodPost, "/api/auth/signout", nil, token)
	if signOutResponse.status != http.StatusOK {
		t.Fatalf("signout status = %d, want %d (message=%q)", signOutResponse.status, http.StatusOK, signOutResponse.body.Message)
	}
	if signOutResponse.body.Message != "注销成功" {
		t.Fatalf("signout message = %q, want %q", signOutResponse.body.Message, "注销成功")
	}

	if _, err := store.GetSessionByToken(ctx, claims.Subject, claims.ID, auth.HashToken(token)); !errors.Is(err, database.ErrNotFound) {
		t.Fatalf("session after signout error = %v, want %v", err, database.ErrNotFound)
	}

	revokedResponse := doJSONRequest(t, app, http.MethodPost, "/api/auth/signout", nil, token)
	if revokedResponse.status != http.StatusUnauthorized {
		t.Fatalf("revoked signout status = %d, want %d (message=%q)", revokedResponse.status, http.StatusUnauthorized, revokedResponse.body.Message)
	}
	if revokedResponse.body.Message != "token has been revoked" {
		t.Fatalf("revoked signout message = %q, want %q", revokedResponse.body.Message, "token has been revoked")
	}
}

type integrationHTTPResponse struct {
	status int
	body   integrationEnvelope
}

func doJSONRequest(t *testing.T, app *fiber.App, method, path string, payload any, token string) integrationHTTPResponse {
	t.Helper()

	var bodyBytes []byte
	if payload != nil {
		var err error
		bodyBytes, err = json.Marshal(payload)
		if err != nil {
			t.Fatalf("json.Marshal() error = %v", err)
		}
	}

	req := httptest.NewRequest(method, "http://example.com"+path, bytes.NewReader(bodyBytes))
	if payload != nil {
		req.Header.Set(fiber.HeaderContentType, "application/json")
	}
	if token != "" {
		req.Header.Set(fiber.HeaderAuthorization, "Bearer "+token)
	}

	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("app.Test() error = %v", err)
	}
	defer resp.Body.Close()

	var envelope integrationEnvelope
	if err := json.NewDecoder(resp.Body).Decode(&envelope); err != nil {
		t.Fatalf("json.Decode() error = %v", err)
	}

	return integrationHTTPResponse{
		status: resp.StatusCode,
		body:   envelope,
	}
}

func integrationDatabaseURL(t *testing.T) string {
	t.Helper()

	for _, key := range []string{"BACKEND_INTEGRATION_DATABASE_URL", "DATABASE_URL"} {
		if value := strings.TrimSpace(os.Getenv(key)); value != "" {
			return value
		}
	}

	envPath, found, err := locateEnvFile()
	if err != nil {
		t.Fatalf("locateEnvFile() error = %v", err)
	}
	if found {
		if err := loadEnvFile(envPath); err != nil {
			t.Fatalf("loadEnvFile(%q) error = %v", envPath, err)
		}
	}

	for _, key := range []string{"BACKEND_INTEGRATION_DATABASE_URL", "DATABASE_URL"} {
		if value := strings.TrimSpace(os.Getenv(key)); value != "" {
			return value
		}
	}

	t.Skip("integration database is not configured; set BACKEND_INTEGRATION_DATABASE_URL or DATABASE_URL")
	return ""
}

func openIntegrationSQLDB(t *testing.T, dbURL string) *sql.DB {
	t.Helper()

	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Fatalf("db.Close() error = %v", err)
		}
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		t.Fatalf("db.PingContext() error = %v", err)
	}

	return db
}

func ensureIntegrationSchema(t *testing.T, db *sql.DB) {
	t.Helper()

	schema, err := os.ReadFile("database/schema.sql")
	if err != nil {
		t.Fatalf("os.ReadFile(schema.sql) error = %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if _, err := db.ExecContext(ctx, string(schema)); err != nil {
		t.Fatalf("db.ExecContext(schema) error = %v", err)
	}
}

func cleanupIntegrationUser(t *testing.T, db *sql.DB, account string) {
	t.Helper()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if _, err := db.ExecContext(ctx, `DELETE FROM "user" WHERE account = $1`, account); err != nil {
		t.Fatalf("cleanup user %q: %v", account, err)
	}
}
