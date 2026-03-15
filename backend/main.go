package main

import (
	"log"

	"hire_sense/api"
	"hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/middleware/cors"
)

func main() {
	cfg, err := LoadConfig()
	if err != nil {
		log.Fatal(err)
	}

	store, err := database.Open(cfg.DatabaseURL)
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err := store.Close(); err != nil {
			log.Printf("close database: %v", err)
		}
	}()

	tokenManager, err := auth.NewTokenManager(cfg.JWTIssuer, cfg.JWTTTL)
	if err != nil {
		log.Fatal(err)
	}

	interviewService, err := api.NewInterviewService(api.InterviewServiceConfig{
		AIURL:      cfg.AIURL,
		WhisperURL: cfg.WhisperURL,
	})
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New(fiber.Config{
		PassLocalsToContext: true,
		ErrorHandler:        api.ErrorHandler,
	})
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
	})

	log.Printf("backend listening on %s", cfg.AppAddress)
	log.Fatal(app.Listen(cfg.AppAddress, fiber.ListenConfig{
		EnablePrintRoutes: true,
	}))
}
