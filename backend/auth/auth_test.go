package auth

import (
	"errors"
	"testing"
	"time"

	"hire_sense/database"
)

func TestTokenManagerIssueAndParseTokenRoundTrip(t *testing.T) {
	t.Parallel()

	manager, err := NewTokenManager("hiresense-test", 2*time.Hour)
	if err != nil {
		t.Fatalf("NewTokenManager() error = %v", err)
	}

	issued, err := manager.IssueToken(database.User{
		ID:   "user-1",
		Role: database.RoleAdmin,
	})
	if err != nil {
		t.Fatalf("IssueToken() error = %v", err)
	}

	if issued.Raw == "" {
		t.Fatal("IssueToken() returned an empty raw token")
	}
	if issued.TokenID == "" {
		t.Fatal("IssueToken() returned an empty token id")
	}

	claims, err := manager.ParseToken(issued.Raw)
	if err != nil {
		t.Fatalf("ParseToken() error = %v", err)
	}

	if claims.Subject != "user-1" {
		t.Fatalf("claims.Subject = %q, want %q", claims.Subject, "user-1")
	}
	if claims.Role != string(database.RoleAdmin) {
		t.Fatalf("claims.Role = %q, want %q", claims.Role, database.RoleAdmin)
	}
	if claims.Issuer != "hiresense-test" {
		t.Fatalf("claims.Issuer = %q, want %q", claims.Issuer, "hiresense-test")
	}
	if claims.ID != issued.TokenID {
		t.Fatalf("claims.ID = %q, want %q", claims.ID, issued.TokenID)
	}
	if claims.ExpiresAt == nil {
		t.Fatal("claims.ExpiresAt is nil")
	}

	diff := claims.ExpiresAt.Time.Sub(issued.ExpiresAt)
	if diff < -time.Second || diff > time.Second {
		t.Fatalf("claims.ExpiresAt differs from issued expiry by %v", diff)
	}
}

func TestTokenManagerParseTokenRejectsWrongIssuer(t *testing.T) {
	t.Parallel()

	issuerA, err := NewTokenManager("issuer-a", time.Hour)
	if err != nil {
		t.Fatalf("NewTokenManager() error = %v", err)
	}
	issuerB, err := NewTokenManager("issuer-b", time.Hour)
	if err != nil {
		t.Fatalf("NewTokenManager() error = %v", err)
	}

	issued, err := issuerA.IssueToken(database.User{
		ID:   "user-1",
		Role: database.RoleUser,
	})
	if err != nil {
		t.Fatalf("IssueToken() error = %v", err)
	}

	if _, err := issuerB.ParseToken(issued.Raw); err == nil {
		t.Fatal("ParseToken() unexpectedly accepted a token from a different issuer")
	}
}

func TestHashToken(t *testing.T) {
	t.Parallel()

	first := HashToken("token-1")
	second := HashToken("token-1")
	third := HashToken("token-2")

	if first != second {
		t.Fatalf("HashToken() should be deterministic, got %q and %q", first, second)
	}
	if first == third {
		t.Fatalf("HashToken() should differ for different inputs, got %q", first)
	}
	if len(first) != 64 {
		t.Fatalf("HashToken() length = %d, want 64", len(first))
	}
}

func TestNormalizeAccount(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		account string
		want    string
	}{
		{name: "trim and lowercase", account: "  Alice@Example.COM  ", want: "alice@example.com"},
		{name: "empty after trim", account: "   ", want: ""},
		{name: "preserve internal content", account: "Team Lead", want: "team lead"},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := normalizeAccount(tt.account); got != tt.want {
				t.Fatalf("normalizeAccount(%q) = %q, want %q", tt.account, got, tt.want)
			}
		})
	}
}

func TestValidatePassword(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		password string
		wantErr  error
	}{
		{name: "too short", password: "1234567", wantErr: ErrWeakPassword},
		{name: "spaces only", password: "        ", wantErr: ErrWeakPassword},
		{name: "trimmed length is enough", password: " 12345678 ", wantErr: nil},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			err := validatePassword(tt.password)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("validatePassword(%q) error = %v, want %v", tt.password, err, tt.wantErr)
			}
		})
	}
}
