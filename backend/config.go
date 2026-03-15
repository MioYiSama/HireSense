package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Config struct {
	AppAddress      string
	DatabaseURL     string
	JWTIssuer       string
	JWTTTL          time.Duration
	PutReportSecret string
	WhisperURL      string
	AIURL           string
}

func LoadConfig() (Config, error) {
	envPath, found, err := locateEnvFile()
	if err != nil {
		return Config{}, err
	}
	if found {
		if err := loadEnvFile(envPath); err != nil {
			return Config{}, err
		}
	}

	ttl, err := time.ParseDuration(getEnv("JWT_TTL", "24h"))
	if err != nil {
		return Config{}, fmt.Errorf("parse JWT_TTL: %w", err)
	}

	cfg := Config{
		AppAddress:      getEnv("APP_ADDR", ":8080"),
		DatabaseURL:     strings.TrimSpace(os.Getenv("DATABASE_URL")),
		JWTIssuer:       getEnv("JWT_ISSUER", "hiresense-backend"),
		JWTTTL:          ttl,
		PutReportSecret: strings.TrimSpace(os.Getenv("PUT_REPORT_SECRET")),
		WhisperURL:      strings.TrimSpace(os.Getenv("WHISPER_URL")),
		AIURL:           strings.TrimSpace(os.Getenv("AI_URL")),
	}

	switch {
	case cfg.DatabaseURL == "":
		return Config{}, errors.New("DATABASE_URL is required")
	case cfg.PutReportSecret == "":
		return Config{}, errors.New("PUT_REPORT_SECRET is required")
	case cfg.JWTTTL <= 0:
		return Config{}, errors.New("JWT_TTL must be greater than zero")
	}

	return cfg, nil
}

func locateEnvFile() (string, bool, error) {
	candidates := []string{
		".env",
		filepath.Join("backend", ".env"),
	}

	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			absPath, err := filepath.Abs(candidate)
			if err != nil {
				return "", false, fmt.Errorf("resolve env file: %w", err)
			}
			return absPath, true, nil
		} else if !errors.Is(err, os.ErrNotExist) {
			return "", false, fmt.Errorf("stat env file %s: %w", candidate, err)
		}
	}

	return "", false, nil
}

func loadEnvFile(path string) error {
	content, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read env file: %w", err)
	}

	lines := strings.Split(string(content), "\n")
	for idx, rawLine := range lines {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		if strings.HasPrefix(line, "export ") {
			line = strings.TrimSpace(strings.TrimPrefix(line, "export "))
		}

		key, value, ok := strings.Cut(line, "=")
		if !ok {
			return fmt.Errorf("invalid .env line %d", idx+1)
		}

		key = strings.TrimSpace(key)
		value = strings.TrimSpace(value)
		value = strings.Trim(value, `"'`)
		if key == "" {
			return fmt.Errorf("invalid .env line %d", idx+1)
		}

		if err := os.Setenv(key, value); err != nil {
			return fmt.Errorf("set env %s: %w", key, err)
		}
	}

	return nil
}

func getEnv(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}
