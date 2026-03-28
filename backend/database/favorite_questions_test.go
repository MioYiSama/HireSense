package database

import (
	"testing"
	"time"
)

func TestUpsertFavoriteQuestionMergesSameQuestionAcrossReports(t *testing.T) {
	t.Parallel()

	firstTime := time.Date(2026, 3, 28, 9, 0, 0, 0, time.UTC)
	secondTime := firstTime.Add(2 * time.Hour)

	favorites, firstFavorite := upsertFavoriteQuestion(nil, FavoriteQuestionSource{
		InterviewID:        "interview-1",
		ReviewIndex:        0,
		InterviewCreatedAt: 1711616400000,
		FavoritedAt:        firstTime,
		Interviewer:        "什么是幂等？",
		InterviewerRole:    "ai",
		Interviewee:        "第一次回答",
		Advice:             "先给定义再给案例。",
		DifficultyLabel:    "basic",
		ReasonTags:         []string{},
		StrengthPoints:     []string{},
		MissingPoints:      []string{},
	})

	favorites, mergedFavorite := upsertFavoriteQuestion(favorites, FavoriteQuestionSource{
		InterviewID:        "interview-2",
		ReviewIndex:        1,
		InterviewCreatedAt: 1711620000000,
		FavoritedAt:        secondTime,
		Interviewer:        "  什么是幂等？  ",
		InterviewerRole:    "tech_lead",
		Interviewee:        "第二次回答",
		Advice:             "补充 HTTP 方法案例。",
		DifficultyLabel:    "intermediate",
		ReasonTags:         []string{},
		StrengthPoints:     []string{},
		MissingPoints:      []string{},
	})

	if len(favorites) != 1 {
		t.Fatalf("favorites len = %d, want 1", len(favorites))
	}
	if firstFavorite.ID != mergedFavorite.ID {
		t.Fatalf("favorite id changed after merge: %q != %q", firstFavorite.ID, mergedFavorite.ID)
	}
	if got := len(mergedFavorite.Sources); got != 2 {
		t.Fatalf("mergedFavorite sources = %d, want 2", got)
	}
	if got := mergedFavorite.Sources[0].InterviewID; got != "interview-2" {
		t.Fatalf("latest source interview_id = %q, want %q", got, "interview-2")
	}
	if got := mergedFavorite.UpdatedAt; !got.Equal(secondTime) {
		t.Fatalf("updated_at = %v, want %v", got, secondTime)
	}
}

func TestUpsertFavoriteQuestionIsIdempotentForSameSource(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, 3, 28, 9, 0, 0, 0, time.UTC)

	favorites, firstFavorite := upsertFavoriteQuestion(nil, FavoriteQuestionSource{
		InterviewID:        "interview-1",
		ReviewIndex:        0,
		InterviewCreatedAt: 1711616400000,
		FavoritedAt:        now,
		Interviewer:        "Redis 为什么快？",
		InterviewerRole:    "ai",
		Interviewee:        "因为在内存里。",
		Advice:             "补充数据结构和 IO 模型。",
		DifficultyLabel:    "basic",
		ReasonTags:         []string{},
		StrengthPoints:     []string{},
		MissingPoints:      []string{},
	})

	favorites, secondFavorite := upsertFavoriteQuestion(favorites, FavoriteQuestionSource{
		InterviewID:        "interview-1",
		ReviewIndex:        0,
		InterviewCreatedAt: 1711616400000,
		FavoritedAt:        now.Add(time.Hour),
		Interviewer:        "Redis 为什么快？",
		InterviewerRole:    "ai",
		Interviewee:        "因为在内存里。",
		Advice:             "补充数据结构和 IO 模型。",
		DifficultyLabel:    "basic",
		ReasonTags:         []string{},
		StrengthPoints:     []string{},
		MissingPoints:      []string{},
	})

	if len(favorites) != 1 {
		t.Fatalf("favorites len = %d, want 1", len(favorites))
	}
	if got := len(secondFavorite.Sources); got != 1 {
		t.Fatalf("favorite sources = %d, want 1", got)
	}
	if firstFavorite.ID != secondFavorite.ID {
		t.Fatalf("favorite id changed after idempotent add: %q != %q", firstFavorite.ID, secondFavorite.ID)
	}
}

func TestRemoveFavoriteQuestionSourceRemovesFavoriteWhenLastSourceRemoved(t *testing.T) {
	t.Parallel()

	favorites := []FavoriteQuestion{
		{
			ID:          "favorite-1",
			Question:    "MySQL 索引什么时候失效？",
			QuestionKey: normalizeFavoriteQuestionText("MySQL 索引什么时候失效？"),
			CreatedAt:   time.Date(2026, 3, 28, 9, 0, 0, 0, time.UTC),
			UpdatedAt:   time.Date(2026, 3, 28, 9, 0, 0, 0, time.UTC),
			Sources: []FavoriteQuestionSource{
				{
					InterviewID:        "interview-1",
					ReviewIndex:        0,
					InterviewCreatedAt: 1711616400000,
					FavoritedAt:        time.Date(2026, 3, 28, 9, 0, 0, 0, time.UTC),
					Interviewer:        "MySQL 索引什么时候失效？",
					InterviewerRole:    "ai",
					Interviewee:        "类型转换、范围查询等。",
					Advice:             "补充最左前缀原则。",
					DifficultyLabel:    "intermediate",
					ReasonTags:         []string{},
					StrengthPoints:     []string{},
					MissingPoints:      []string{},
				},
			},
		},
	}

	updatedFavorites, removed := removeFavoriteQuestionSource(favorites, "interview-1", 0)
	if !removed {
		t.Fatal("removeFavoriteQuestionSource() removed = false, want true")
	}
	if len(updatedFavorites) != 0 {
		t.Fatalf("updatedFavorites len = %d, want 0", len(updatedFavorites))
	}
}
