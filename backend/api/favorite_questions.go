package api

import (
	"encoding/json"
	"errors"
	"strconv"
	"strings"
	"time"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
)

type addFavoriteQuestionRequest struct {
	InterviewID string `json:"interview_id"`
	ReviewIndex int    `json:"review_index"`
}

type favoriteQuestionResponse struct {
	ID          string                            `json:"id"`
	Question    string                            `json:"question"`
	CreatedAt   time.Time                         `json:"created_at"`
	UpdatedAt   time.Time                         `json:"updated_at"`
	SourceCount int                               `json:"source_count"`
	Sources     []database.FavoriteQuestionSource `json:"sources"`
}

type favoriteReport struct {
	Reviews []favoriteReportReview `json:"reviews"`
}

type favoriteReportReview struct {
	Interviewer     string                   `json:"interviewer"`
	InterviewerRole string                   `json:"interviewer_role"`
	Interviewee     string                   `json:"interviewee"`
	StandardAnswer  string                   `json:"standard_answer"`
	Score           float64                  `json:"score"`
	Advice          string                   `json:"advice"`
	Concept         string                   `json:"concept"`
	DifficultyLabel string                   `json:"difficulty_label"`
	ScoreBreakdown  *database.ScoreBreakdown `json:"score_breakdown"`
	ReasonTags      []string                 `json:"reason_tags"`
	StrengthPoints  []string                 `json:"strength_points"`
	MissingPoints   []string                 `json:"missing_points"`
	ScoreRationale  string                   `json:"score_rationale"`
}

func (h userHandler) listFavoriteQuestions(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	favorites, err := h.store.GetFavoriteQuestions(c.Context(), principal.UserID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respond(c, fiber.StatusOK, "读取收藏题成功", toFavoriteQuestionResponses(favorites))
}

func (h userHandler) addFavoriteQuestion(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	var request addFavoriteQuestionRequest
	if err := c.Bind().Body(&request); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid request body")
	}

	request.InterviewID = strings.TrimSpace(request.InterviewID)
	if _, err := uuid.Parse(request.InterviewID); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid interview id")
	}
	if request.ReviewIndex < 0 {
		return NewError(fiber.StatusBadRequest, "invalid review index")
	}

	interview, err := h.store.GetInterviewByID(c.Context(), request.InterviewID)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "interview not found")
		}
		return err
	}
	if err := ensureInterviewAccess(principal, interview); err != nil {
		return err
	}

	source, err := buildFavoriteQuestionSource(interview, request.ReviewIndex)
	if err != nil {
		return err
	}

	favorite, err := h.store.AddFavoriteQuestionSource(c.Context(), principal.UserID, source)
	if err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "user not found")
		}
		return err
	}

	return respond(c, fiber.StatusOK, "收藏题保存成功", toFavoriteQuestionResponse(favorite))
}

func (h userHandler) removeFavoriteQuestionSource(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	interviewID := strings.TrimSpace(c.Params("interviewID"))
	if _, err := uuid.Parse(interviewID); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid interview id")
	}

	reviewIndex, err := strconv.Atoi(strings.TrimSpace(c.Params("reviewIndex")))
	if err != nil || reviewIndex < 0 {
		return NewError(fiber.StatusBadRequest, "invalid review index")
	}

	if err := h.store.RemoveFavoriteQuestionSource(c.Context(), principal.UserID, interviewID, reviewIndex); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "favorite question source not found")
		}
		return err
	}

	return respondEmpty(c, "收藏来源移除成功")
}

func (h userHandler) removeFavoriteQuestion(c fiber.Ctx) error {
	principal, ok := authpkg.CurrentPrincipal(c)
	if !ok {
		return NewError(fiber.StatusUnauthorized, "authentication required")
	}

	favoriteID := strings.TrimSpace(c.Params("favoriteID"))
	if _, err := uuid.Parse(favoriteID); err != nil {
		return NewError(fiber.StatusBadRequest, "invalid favorite id")
	}

	if err := h.store.RemoveFavoriteQuestion(c.Context(), principal.UserID, favoriteID); err != nil {
		if errors.Is(err, database.ErrNotFound) {
			return NewError(fiber.StatusNotFound, "favorite question not found")
		}
		return err
	}

	return respondEmpty(c, "收藏题移除成功")
}

func buildFavoriteQuestionSource(
	interview database.Interview,
	reviewIndex int,
) (database.FavoriteQuestionSource, error) {
	if len(interview.Report) == 0 {
		return database.FavoriteQuestionSource{}, NewError(fiber.StatusConflict, "report is not available")
	}

	var report favoriteReport
	if err := json.Unmarshal(interview.Report, &report); err != nil {
		return database.FavoriteQuestionSource{}, NewError(fiber.StatusInternalServerError, "invalid stored report")
	}
	if reviewIndex < 0 || reviewIndex >= len(report.Reviews) {
		return database.FavoriteQuestionSource{}, NewError(fiber.StatusBadRequest, "invalid review index")
	}

	review := report.Reviews[reviewIndex]
	if strings.TrimSpace(review.Interviewer) == "" {
		return database.FavoriteQuestionSource{}, NewError(
			fiber.StatusBadRequest,
			"report review does not contain an interviewer question",
		)
	}

	return database.FavoriteQuestionSource{
		InterviewID:        interview.ID,
		ReviewIndex:        reviewIndex,
		InterviewCreatedAt: interview.CreatedAt.UnixMilli(),
		FavoritedAt:        time.Now().UTC(),
		Interviewer:        review.Interviewer,
		InterviewerRole:    review.InterviewerRole,
		Interviewee:        review.Interviewee,
		StandardAnswer:     review.StandardAnswer,
		Score:              review.Score,
		Advice:             review.Advice,
		Concept:            review.Concept,
		DifficultyLabel:    review.DifficultyLabel,
		ScoreBreakdown:     review.ScoreBreakdown,
		ReasonTags:         review.ReasonTags,
		StrengthPoints:     review.StrengthPoints,
		MissingPoints:      review.MissingPoints,
		ScoreRationale:     review.ScoreRationale,
	}, nil
}

func toFavoriteQuestionResponses(favorites []database.FavoriteQuestion) []favoriteQuestionResponse {
	response := make([]favoriteQuestionResponse, 0, len(favorites))
	for _, favorite := range favorites {
		response = append(response, toFavoriteQuestionResponse(favorite))
	}
	return response
}

func toFavoriteQuestionResponse(favorite database.FavoriteQuestion) favoriteQuestionResponse {
	sources := append([]database.FavoriteQuestionSource(nil), favorite.Sources...)
	return favoriteQuestionResponse{
		ID:          favorite.ID,
		Question:    favorite.Question,
		CreatedAt:   favorite.CreatedAt,
		UpdatedAt:   favorite.UpdatedAt,
		SourceCount: len(sources),
		Sources:     sources,
	}
}
