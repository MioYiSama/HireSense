package api

import (
	"errors"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

type authHandler struct {
	service      *authpkg.Service
	store        *database.Store
	tokenManager *authpkg.TokenManager
}

type signInRequest struct {
	Account  string `json:"account"`
	Password string `json:"password"`
}

type signUpRequest struct {
	Account  string `json:"account"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

func registerAuthRoutes(router fiber.Router, deps Dependencies) {
	handler := authHandler{
		service:      deps.AuthService,
		store:        deps.Store,
		tokenManager: deps.TokenManager,
	}

	router.Post("/signin", handler.signIn)
	router.Post("/signup", handler.signUp)
	router.Post(
		"/signout",
		authpkg.RequireAuthenticated(deps.Store, deps.TokenManager),
		authpkg.RequireRoles(database.RoleUser, database.RoleAdmin),
		handler.signOut,
	)
}

func (h authHandler) signIn(c fiber.Ctx) error {
	var request signInRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	token, err := h.service.SignIn(c.Context(), authpkg.SignInInput{
		Account:  request.Account,
		Password: request.Password,
	})
	if err != nil {
		return mapAuthError(err, "登录失败")
	}

	return respond(c, fiber.StatusOK, "登录成功", token)
}

func (h authHandler) signUp(c fiber.Ctx) error {
	var request signUpRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	token, err := h.service.SignUp(c.Context(), authpkg.SignUpInput{
		Account:  request.Account,
		Name:     request.Name,
		Password: request.Password,
	})
	if err != nil {
		return mapAuthError(err, "注册失败")
	}

	return respond(c, fiber.StatusOK, "注册成功", token)
}

func (h authHandler) signOut(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	if err := h.service.SignOut(c.Context(), principal); err != nil {
		return err
	}

	return respondEmpty(c, "注销成功")
}

func mapAuthError(err error, fallbackMessage string) error {
	switch {
	case errors.Is(err, authpkg.ErrInvalidCredentials):
		return NewError(fiber.StatusUnauthorized, "账号或密码错误")
	case errors.Is(err, authpkg.ErrInvalidAccount),
		errors.Is(err, authpkg.ErrInvalidName),
		errors.Is(err, authpkg.ErrWeakPassword):
		return NewError(fiber.StatusBadRequest, err.Error())
	case errors.Is(err, database.ErrConflict):
		return NewError(fiber.StatusConflict, "账号已存在")
	default:
		return err
	}
}
