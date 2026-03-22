package api

import (
	"encoding/json"
	"errors"
	"log/slog"
	"mime"
	"strings"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
)

type interviewHandler struct {
	store            *database.Store
	putReportSecret  string
	interviewService *InterviewService
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

	profile, err := h.store.GetProfile(c.Context(), principal.UserID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	interviewID := uuid.NewString()
	startResult, err := h.interviewService.Start(c.Context(), InterviewSession{
		ID:              interviewID,
		Job:             string(profile.Job),
		Resume:          profile.Resume,
		Personalization: profile.Personalization,
	})
	if err != nil {
		return mapInterviewServiceError(err)
	}

	interview, err := h.store.CreateInterview(c.Context(), database.CreateInterviewParams{
		ID:     interviewID,
		UserID: principal.UserID,
	})
	if err != nil {
		if stopErr := h.interviewService.Stop(c.Context(), interviewID); stopErr != nil {
			slog.WarnContext(c.Context(), "cleanup upstream interview failed",
				"interview_id", interviewID,
				"user_id", principal.UserID,
				"err", stopErr,
			)
		}
		return err
	}
	slog.InfoContext(c.Context(), "interview started",
		"interview_id", interview.ID,
		"user_id", principal.UserID,
		"job", string(profile.Job),
	)

	return respond(c, fiber.StatusOK, "AI 面试官已就绪", fiber.Map{
		"id":    interview.ID,
		"reply": startResult.Reply,
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

	if interview.Status == database.InterviewStopped {
		return respondEmpty(c, "面试已结束")
	}

	if err := h.interviewService.Stop(c.Context(), request.ID); err != nil {
		return mapInterviewServiceError(err)
	}

	if err := h.store.StopInterview(c.Context(), request.ID); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}
	slog.InfoContext(c.Context(), "interview stopped",
		"interview_id", request.ID,
		"user_id", principal.UserID,
	)

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

	requestData, err := decodeInterviewReplyRequest(c, query.ID)
	if err != nil {
		return err
	}

	result, err := h.interviewService.Reply(c.Context(), requestData)
	if err != nil {
		return mapInterviewServiceError(err)
	}

	if result.Ending {
		if err := h.interviewService.Stop(c.Context(), query.ID); err != nil {
			return mapInterviewServiceError(err)
		}

		if err := h.store.StopInterview(c.Context(), query.ID); err != nil {
			if errors.Is(err, database.ErrNotFound) {
				return NewError(fiber.StatusNotFound, "interview not found")
			}
			return err
		}
	}
	inputType := "text"
	audioBytes := 0
	if requestData.Audio != nil {
		inputType = "audio"
		audioBytes = len(requestData.Audio.Data)
	}
	slog.InfoContext(c.Context(), "interview reply processed",
		"interview_id", query.ID,
		"user_id", principal.UserID,
		"input_type", inputType,
		"audio_bytes", audioBytes,
		"ending", result.Ending,
	)

	return respond(c, fiber.StatusOK, "交互成功", fiber.Map{
		"reply":  result.Reply,
		"ending": result.Ending,
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
	slog.InfoContext(c.Context(), "interview report stored",
		"interview_id", request.ID,
		"report_bytes", len(request.Report),
	)

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

func decodeInterviewReplyRequest(c fiber.Ctx, interviewID string) (InterviewReplyRequestData, error) {
	mediaType, err := parseRequestMediaType(c.Get(fiber.HeaderContentType))
	if err != nil {
		return InterviewReplyRequestData{}, NewError(fiber.StatusBadRequest, "invalid content type")
	}

	switch {
	case mediaType == "" || mediaType == "application/json":
		var request replyInterviewRequest
		if err := c.Bind().Body(&request); err != nil {
			return InterviewReplyRequestData{}, NewError(fiber.StatusBadRequest, "invalid request body")
		}

		text := strings.TrimSpace(request.Text)
		if text == "" {
			return InterviewReplyRequestData{}, NewError(fiber.StatusBadRequest, "text is required")
		}

		return InterviewReplyRequestData{
			InterviewID: interviewID,
			Text:        text,
		}, nil
	case strings.HasPrefix(mediaType, "audio/"):
		audio := append([]byte(nil), c.BodyRaw()...)
		if len(audio) == 0 {
			return InterviewReplyRequestData{}, NewError(fiber.StatusBadRequest, "audio payload is required")
		}

		return InterviewReplyRequestData{
			InterviewID: interviewID,
			Audio: &InterviewReplyAudio{
				Filename:    audioFilenameForMediaType(mediaType),
				ContentType: mediaType,
				Data:        audio,
			},
		}, nil
	default:
		return InterviewReplyRequestData{}, NewError(fiber.StatusUnsupportedMediaType, "unsupported content type")
	}
}

func parseRequestMediaType(contentType string) (string, error) {
	trimmed := strings.TrimSpace(contentType)
	if trimmed == "" {
		return "", nil
	}

	mediaType, _, err := mime.ParseMediaType(trimmed)
	if err != nil {
		return "", err
	}

	return strings.ToLower(mediaType), nil
}

func audioFilenameForMediaType(mediaType string) string {
	_, subtype, ok := strings.Cut(mediaType, "/")
	if !ok || strings.TrimSpace(subtype) == "" {
		return defaultInterviewAudioFilename
	}

	subtype = strings.TrimPrefix(strings.TrimSpace(subtype), "x-")
	if subtype == "" {
		return defaultInterviewAudioFilename
	}

	return "interview-reply." + subtype
}

func mapInterviewServiceError(err error) error {
	switch {
	case errors.Is(err, ErrInterviewTextRequired):
		return NewError(fiber.StatusBadRequest, "text is required")
	case errors.Is(err, ErrInterviewAudioRequired):
		return NewError(fiber.StatusBadRequest, "audio payload is required")
	case errors.Is(err, ErrInterviewTranscriptEmpty):
		return NewError(fiber.StatusBadRequest, "audio did not contain recognizable speech")
	}

	var upstreamErr *InterviewUpstreamError
	if errors.As(err, &upstreamErr) {
		switch upstreamErr.Service {
		case "whisper":
			return NewError(fiber.StatusBadGateway, "语音转写服务暂时不可用")
		case "ai":
			return NewError(fiber.StatusBadGateway, "面试服务暂时不可用")
		}
	}

	return err
}
