package api

import (
	"errors"
	"strings"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

type userHandler struct {
	store            *database.Store
	authService      *authpkg.Service
	interviewService *InterviewService
}

type passwordRequest struct {
	Password string `json:"password"`
}

type profileRequest struct {
	Name            string `json:"name"`
	Job             string `json:"job"`
	Resume          string `json:"resume"`
	Personalization string `json:"personalization"`
}

type interviewResponse struct {
	ID        string `json:"id"`
	Mode      string `json:"mode"`
	Status    string `json:"status"`
	CreatedAt int64  `json:"created_at"`
	Report    any    `json:"report"`
}

type resumeAnalysisLookupResponse struct {
	Analysis *database.ResumeAnalysis `json:"analysis"`
}

func registerUserRoutes(router fiber.Router, deps Dependencies) {
	handler := userHandler{
		store:            deps.Store,
		authService:      deps.AuthService,
		interviewService: deps.InterviewService,
	}

	router.Put("/password", handler.updatePassword)
	router.Get("/profile", handler.getProfile)
	router.Put("/profile", handler.updateProfile)
	router.Get("/resume-analysis", handler.getResumeAnalysis)
	router.Post("/resume-analysis", handler.generateResumeAnalysis)
	router.Get("/interviews", handler.listInterviews)
}

func (h userHandler) updatePassword(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	var request passwordRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	if err := h.authService.ChangePassword(c.Context(), principal.UserID, request.Password); err != nil {
		switch {
		case errors.Is(err, authpkg.ErrWeakPassword):
			return NewError(fiber.StatusBadRequest, err.Error())
		case errors.Is(err, database.ErrNotFound):
			return NewError(fiber.StatusNotFound, "user not found")
		default:
			return err
		}
	}

	return respondEmpty(c, "密码修改成功")
}

func (h userHandler) getProfile(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	profile, err := h.store.GetProfile(c.Context(), principal.UserID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respond(c, fiber.StatusOK, "读取档案成功", profile)
}

func (h userHandler) updateProfile(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	var request profileRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	job := database.UserJob(strings.TrimSpace(request.Job))
	if strings.TrimSpace(request.Name) == "" {
		return NewError(fiber.StatusBadRequest, "name is required")
	}
	if !job.IsValid() {
		return NewError(fiber.StatusBadRequest, "invalid job")
	}

	if err := h.store.UpdateProfile(c.Context(), principal.UserID, database.Profile{
		Name:            strings.TrimSpace(request.Name),
		Job:             job,
		Resume:          strings.TrimSpace(request.Resume),
		Personalization: strings.TrimSpace(request.Personalization),
	}); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respondEmpty(c, "档案覆写成功")
}

func (h userHandler) listInterviews(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	interviews, err := h.store.ListInterviewsByUserID(c.Context(), principal.UserID)
	if err != nil {
		return err
	}

	response := make([]interviewResponse, 0, len(interviews))
	for _, interview := range interviews {
		response = append(response, interviewResponse{
			ID:        interview.ID,
			Mode:      string(interview.Mode),
			Status:    string(interview.Status),
			CreatedAt: interview.CreatedAt.UnixMilli(),
			Report:    rawReportToAny(interview.Report),
		})
	}

	return respond(c, fiber.StatusOK, "拉取面试纪要成功", response)
}

func (h userHandler) getResumeAnalysis(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	analysis, err := h.store.GetResumeAnalysis(c.Context(), principal.UserID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respond(c, fiber.StatusOK, "读取简历分析成功", resumeAnalysisLookupResponse{
		Analysis: analysis,
	})
}

func (h userHandler) generateResumeAnalysis(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	profile, err := h.store.GetProfile(c.Context(), principal.UserID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	if strings.TrimSpace(profile.Resume) == "" {
		return NewError(fiber.StatusBadRequest, "resume is required")
	}

	analysis, err := h.interviewService.AnalyzeResume(c.Context(), ResumeAnalysisRequest{
		Job:    string(profile.Job),
		Resume: profile.Resume,
	})
	if err != nil {
		return mapInterviewServiceError(err)
	}

	if err := h.store.SaveResumeAnalysis(c.Context(), principal.UserID, analysis); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respond(c, fiber.StatusOK, "简历分析生成成功", analysis)
}
