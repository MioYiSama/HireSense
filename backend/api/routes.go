package api

import (
	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

type Dependencies struct {
	Store            *database.Store
	AuthService      *authpkg.Service
	TokenManager     *authpkg.TokenManager
	PutReportSecret  string
	InterviewService *InterviewService
}

func RegisterRoutes(app *fiber.App, deps Dependencies) {
	apiGroup := app.Group("/api")

	registerAuthRoutes(apiGroup.Group("/auth"), deps)

	userGroup := apiGroup.Group(
		"/user",
		authpkg.RequireAuthenticated(deps.Store, deps.TokenManager),
		authpkg.RequireRoles(database.RoleUser, database.RoleAdmin),
	)
	registerUserRoutes(userGroup, deps)

	interviewHandler := interviewHandler{
		store:            deps.Store,
		putReportSecret:  deps.PutReportSecret,
		interviewService: deps.InterviewService,
	}
	apiGroup.Put("/interview/report", interviewHandler.putReport)

	interviewGroup := apiGroup.Group(
		"/interview",
		authpkg.RequireAuthenticated(deps.Store, deps.TokenManager),
		authpkg.RequireRoles(database.RoleUser, database.RoleAdmin),
	)
	registerInterviewRoutes(interviewGroup, interviewHandler)
}
