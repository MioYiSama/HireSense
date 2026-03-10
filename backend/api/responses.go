package api

import (
	"errors"

	"github.com/gofiber/fiber/v3"
)

type envelope struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Data    any    `json:"data"`
}

type HTTPError struct {
	Status  int
	Message string
}

func (e *HTTPError) Error() string {
	return e.Message
}

func NewError(status int, message string) error {
	return &HTTPError{
		Status:  status,
		Message: message,
	}
}

func ErrorHandler(c fiber.Ctx, err error) error {
	status := fiber.StatusInternalServerError
	message := "internal server error"

	var httpErr *HTTPError
	switch {
	case errors.As(err, &httpErr):
		status = httpErr.Status
		message = httpErr.Message
	default:
		var fiberErr *fiber.Error
		if errors.As(err, &fiberErr) {
			status = fiberErr.Code
			message = fiberErr.Message
		}
	}

	return c.Status(status).JSON(envelope{
		Success: false,
		Message: message,
		Data:    nil,
	})
}

func respond(c fiber.Ctx, status int, message string, data any) error {
	return c.Status(status).JSON(envelope{
		Success: true,
		Message: message,
		Data:    data,
	})
}

func respondEmpty(c fiber.Ctx, message string) error {
	return respond(c, fiber.StatusOK, message, struct{}{})
}
