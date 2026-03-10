package api

import (
	"encoding/json"
	"errors"
	"strings"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
)

type interviewHandler struct {
	store           *database.Store
	putReportSecret string
}

type stopInterviewRequest struct {
	ID string `json:"id"`
}

type replyInterviewQuery struct {
	ID string `query:"id"`
}

type replyInterviewRequest struct {
	Text string `json:"text"`
}

type putReportRequest struct {
	Secret string          `json:"secret"`
	ID     string          `json:"id"`
	Report json.RawMessage `json:"report"`
}

func registerInterviewRoutes(router fiber.Router, handler interviewHandler) {
	router.Post("/start", handler.start)
	router.Post("/stop", handler.stop)
	router.Post("/reply", handler.reply)
}

func (h interviewHandler) start(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	interview, err := h.store.CreateInterview(c.Context(), database.CreateInterviewParams{
		ID:     uuid.NewString(),
		UserID: principal.UserID,
	})
	if err != nil {
		return err
	}

	return respond(c, fiber.StatusOK, "AI 面试官已就绪", fiber.Map{
		"id": interview.ID,
	})
}

func (h interviewHandler) stop(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	var request stopInterviewRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}
	if _, err := uuid.Parse(strings.TrimSpace(request.ID)); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid interview id")
	}

	interview, err := h.store.GetInterviewByID(c.Context(), request.ID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}
	if err := ensureInterviewAccess(principal, interview); err != nil {
		return err
	}

	if err := h.store.StopInterview(c.Context(), request.ID); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}

	return respondEmpty(c, "已被强制标记为停止")
}

func (h interviewHandler) reply(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	var query replyInterviewQuery
	if err := c.Bind().Query(&query); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid query parameters")
	}

	if _, err := uuid.Parse(strings.TrimSpace(query.ID)); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid interview id")
	}

	var request replyInterviewRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}
	if strings.TrimSpace(request.Text) == "" {
		return NewError(fiber.StatusBadRequest, "text is required")
	}

	interview, err := h.store.GetInterviewByID(c.Context(), query.ID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}
	if err := ensureInterviewAccess(principal, interview); err != nil {
		return err
	}
	if interview.Status == database.InterviewStopped {
		return NewError(fiber.StatusConflict, "interview already stopped")
	}

	return respond(c, fiber.StatusOK, "交互成功", fiber.Map{
		"reply":  "AI 面试官暂未接入，当前接口已完成鉴权与会话校验。",
		"ending": false,
	})
}

func (h interviewHandler) putReport(c fiber.Ctx) error {
	var request putReportRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	if request.Secret != h.putReportSecret {
		return NewError(fiber.StatusForbidden, "invalid report secret")
	}
	if _, err := uuid.Parse(strings.TrimSpace(request.ID)); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid interview id")
	}
	if len(request.Report) == 0 || string(request.Report) == "null" {
		return NewError(fiber.StatusBadRequest, "report is required")
	}

	if err := h.store.UpdateInterviewReport(c.Context(), request.ID, request.Report); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}

	return respondEmpty(c, "报告归档并生成成功")
}

func ensureInterviewAccess(principal authpkg.Principal, interview database.Interview) error {
	if principal.Role == database.RoleAdmin {
		return nil
	}
	if interview.UserID != principal.UserID {
		return NewError(fiber.StatusForbidden, "insufficient permissions")
	}
	return nil
}

func rawReportToAny(raw json.RawMessage) any {
	if len(raw) == 0 {
		return nil
	}

	var decoded any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return string(raw)
	}
	return decoded
}
