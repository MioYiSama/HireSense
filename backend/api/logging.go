package api

import (
	"log/slog"
	"time"

	authpkg "hire_sense/auth"

	"github.com/gofiber/fiber/v3"
)

func RequestLogger() fiber.Handler {
	return func(c fiber.Ctx) error {
		start := time.Now()

		err := c.Next()
		duration := time.Since(start)
		if err != nil {
			status, _ := resolveHTTPError(err)
			logRequest(c, status, duration, err)
			return err
		}

		status := c.Response().StatusCode()
		if status == 0 {
			status = fiber.StatusOK
		}
		logRequest(c, status, duration, nil)
		return nil
	}
}

func logRequest(c fiber.Ctx, status int, duration time.Duration, err error) {
	if c.Method() == fiber.MethodOptions && status < fiber.StatusBadRequest {
		return
	}

	attrs := []slog.Attr{
		slog.String("method", c.Method()),
		slog.String("path", c.Path()),
		slog.Int("status", status),
		slog.Duration("duration", duration),
		slog.String("ip", c.IP()),
	}
	if principal, ok := authpkg.CurrentPrincipal(c); ok {
		attrs = append(attrs,
			slog.String("user_id", principal.UserID),
			slog.String("role", string(principal.Role)),
		)
	}
	if err != nil {
		attrs = append(attrs, slog.Any("err", err))
	}

	level := slog.LevelInfo
	message := "request completed"
	switch {
	case err != nil || status >= fiber.StatusInternalServerError:
		level = slog.LevelError
		message = "request failed"
	case status >= fiber.StatusBadRequest:
		level = slog.LevelWarn
	}

	slog.LogAttrs(c.Context(), level, message, attrs...)
}
