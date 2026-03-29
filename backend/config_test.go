package main

import "testing"

func TestGetEnvAsPositiveIntUsesFallbackWhenUnset(t *testing.T) {
	t.Setenv("APP_BODY_LIMIT_BYTES", "")

	got, err := getEnvAsPositiveInt("APP_BODY_LIMIT_BYTES", 123)
	if err != nil {
		t.Fatalf("getEnvAsPositiveInt returned error: %v", err)
	}
	if got != 123 {
		t.Fatalf("getEnvAsPositiveInt returned %d, want %d", got, 123)
	}
}

func TestGetEnvAsPositiveIntRejectsInvalidValue(t *testing.T) {
	t.Setenv("APP_BODY_LIMIT_BYTES", "0")

	if _, err := getEnvAsPositiveInt("APP_BODY_LIMIT_BYTES", 123); err == nil {
		t.Fatal("getEnvAsPositiveInt returned nil error, want error")
	}
}

func TestGetEnvAsPositiveIntParsesConfiguredValue(t *testing.T) {
	t.Setenv("APP_BODY_LIMIT_BYTES", "107374182400")

	got, err := getEnvAsPositiveInt("APP_BODY_LIMIT_BYTES", 123)
	if err != nil {
		t.Fatalf("getEnvAsPositiveInt returned error: %v", err)
	}
	if got != 107374182400 {
		t.Fatalf("getEnvAsPositiveInt returned %d, want %d", got, 107374182400)
	}
}
