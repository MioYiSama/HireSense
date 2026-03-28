package main

import (
	"log/slog"
	"os"

	"hire_sense/api"
	"hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/middleware/cors"
)

func main() {
	initLogger()

	cfg, err := LoadConfig()
	if err != nil {
		slog.Error("load config", "err", err)
		os.Exit(1)
	}
	slog.Info("configuration loaded",
		"app_addr", cfg.AppAddress,
		"jwt_ttl", cfg.JWTTTL,
		"whisper_configured", cfg.WhisperURL != "",
		"ai_configured", cfg.AIURL != "",
	)

	store, err := database.Open(cfg.DatabaseURL)
	if err != nil {
		slog.Error("open database", "err", err)
		os.Exit(1)
	}
	slog.Info("database connection ready")
	defer func() {
		if err := store.Close(); err != nil {
			slog.Warn("close database", "err", err)
		}
	}()

	tokenManager, err := auth.NewTokenManager(cfg.JWTIssuer, cfg.JWTTTL)
	if err != nil {
		slog.Error("initialize token manager", "err", err)
		os.Exit(1)
	}

	interviewService, err := api.NewInterviewService(api.InterviewServiceConfig{
		AIURL:      cfg.AIURL,
		WhisperURL: cfg.WhisperURL,
	})
	if err != nil {
		slog.Error("initialize interview service", "err", err)
		os.Exit(1)
	}

	app := fiber.New(fiber.Config{
		PassLocalsToContext: true,
		ErrorHandler:        api.ErrorHandler,
	})
	app.Use(api.RequestLogger())
	app.Use(cors.New(cors.Config{
		AllowOrigins: []string{"*"},
		AllowMethods: []string{
			fiber.MethodGet,
			fiber.MethodPost,
			fiber.MethodHead,
			fiber.MethodPut,
			fiber.MethodDelete,
			fiber.MethodPatch,
			fiber.MethodOptions,
			fiber.MethodTrace,
			fiber.MethodConnect,
		},
		AllowHeaders:        []string{"*"},
		ExposeHeaders:       []string{"*"},
		AllowPrivateNetwork: true,
		MaxAge:              86400,
	}))

	api.RegisterRoutes(app, api.Dependencies{
		Store:            store,
		AuthService:      auth.NewService(store, tokenManager),
		TokenManager:     tokenManager,
		PutReportSecret:  cfg.PutReportSecret,
		InterviewService: interviewService,
		InterviewTTS:     api.NewInterviewTTSService(),
	})

	slog.Info("backend listening", "address", cfg.AppAddress)
	if err := app.Listen(cfg.AppAddress); err != nil {
		slog.Error("serve backend", "address", cfg.AppAddress, "err", err)
		os.Exit(1)
	}
}

func initLogger() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})))
}
