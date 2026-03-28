package api

import (
	"encoding/json"
	"errors"
	"testing"
	"time"

	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

func TestBuildFavoriteQuestionSource(t *testing.T) {
	t.Parallel()

	interview := database.Interview{
		ID:        "interview-1",
		CreatedAt: time.Date(2026, 3, 28, 10, 0, 0, 0, time.UTC),
		Report: json.RawMessage(`{
			"reviews": [
				{
					"interviewer": "Redis 为什么快？",
					"interviewer_role": "tech_lead",
					"interviewee": "主要是内存访问快。",
					"standard_answer": "还应覆盖 IO 多路复用、单线程模型和高效数据结构。",
					"score": 61.5,
					"advice": "补充底层原因和边界条件。",
					"concept": "Redis",
					"difficulty_label": "intermediate",
					"score_breakdown": {
						"coverage_score": 60,
						"consistency_score": 62,
						"completeness_score": 61
					},
					"reason_tags": ["coverage_partial"],
					"strength_points": ["提到了内存访问"],
					"missing_points": ["没有解释 IO 模型"],
					"score_rationale": "覆盖到现象，但缺少机制说明。"
				}
			]
		}`),
	}

	source, err := buildFavoriteQuestionSource(interview, 0)
	if err != nil {
		t.Fatalf("buildFavoriteQuestionSource() error = %v", err)
	}
	if source.InterviewID != interview.ID {
		t.Fatalf("source.InterviewID = %q, want %q", source.InterviewID, interview.ID)
	}
	if source.ReviewIndex != 0 {
		t.Fatalf("source.ReviewIndex = %d, want 0", source.ReviewIndex)
	}
	if source.Interviewer != "Redis 为什么快？" {
		t.Fatalf("source.Interviewer = %q, want %q", source.Interviewer, "Redis 为什么快？")
	}
	if source.ScoreBreakdown == nil || source.ScoreBreakdown.CoverageScore != 60 {
		t.Fatalf("source.ScoreBreakdown = %#v, want coverage_score 60", source.ScoreBreakdown)
	}
	if len(source.ReasonTags) != 1 || source.ReasonTags[0] != "coverage_partial" {
		t.Fatalf("source.ReasonTags = %#v, want %#v", source.ReasonTags, []string{"coverage_partial"})
	}
	if source.InterviewCreatedAt != interview.CreatedAt.UnixMilli() {
		t.Fatalf(
			"source.InterviewCreatedAt = %d, want %d",
			source.InterviewCreatedAt,
			interview.CreatedAt.UnixMilli(),
		)
	}
}

func TestBuildFavoriteQuestionSourceRejectsInvalidReviewIndex(t *testing.T) {
	t.Parallel()

	interview := database.Interview{
		ID:        "interview-1",
		CreatedAt: time.Date(2026, 3, 28, 10, 0, 0, 0, time.UTC),
		Report:    json.RawMessage(`{"reviews":[]}`),
	}

	_, err := buildFavoriteQuestionSource(interview, 3)
	if err == nil {
		t.Fatal("buildFavoriteQuestionSource() error = nil, want invalid review index")
	}

	var httpErr *HTTPError
	if !errors.As(err, &httpErr) {
		t.Fatalf("error type = %T, want *HTTPError", err)
	}
	if httpErr.Status != fiber.StatusBadRequest {
		t.Fatalf("httpErr.Status = %d, want %d", httpErr.Status, fiber.StatusBadRequest)
	}
}
