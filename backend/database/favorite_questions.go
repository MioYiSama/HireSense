package database

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/google/uuid"
)

type sqlQueryer interface {
	QueryRowContext(ctx context.Context, query string, args ...any) *sql.Row
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
}

func (s *Store) GetFavoriteQuestions(ctx context.Context, userID string) ([]FavoriteQuestion, error) {
	return loadFavoriteQuestions(ctx, s.db, userID, false)
}

func (s *Store) AddFavoriteQuestionSource(
	ctx context.Context,
	userID string,
	source FavoriteQuestionSource,
) (FavoriteQuestion, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return FavoriteQuestion{}, fmt.Errorf("begin favorite question transaction: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	favorites, err := loadFavoriteQuestions(ctx, tx, userID, true)
	if err != nil {
		return FavoriteQuestion{}, err
	}

	favorites, favorite := upsertFavoriteQuestion(favorites, source)
	if err := saveFavoriteQuestions(ctx, tx, userID, favorites); err != nil {
		return FavoriteQuestion{}, err
	}
	if err := tx.Commit(); err != nil {
		return FavoriteQuestion{}, fmt.Errorf("commit favorite question transaction: %w", err)
	}

	return favorite, nil
}

func (s *Store) RemoveFavoriteQuestionSource(
	ctx context.Context,
	userID string,
	interviewID string,
	reviewIndex int,
) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin favorite question transaction: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	favorites, err := loadFavoriteQuestions(ctx, tx, userID, true)
	if err != nil {
		return err
	}

	updatedFavorites, removed := removeFavoriteQuestionSource(favorites, interviewID, reviewIndex)
	if !removed {
		return ErrNotFound
	}
	if err := saveFavoriteQuestions(ctx, tx, userID, updatedFavorites); err != nil {
		return err
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit favorite question transaction: %w", err)
	}

	return nil
}

func (s *Store) RemoveFavoriteQuestion(ctx context.Context, userID string, favoriteID string) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin favorite question transaction: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	favorites, err := loadFavoriteQuestions(ctx, tx, userID, true)
	if err != nil {
		return err
	}

	updatedFavorites, removed := removeFavoriteQuestionByID(favorites, favoriteID)
	if !removed {
		return ErrNotFound
	}
	if err := saveFavoriteQuestions(ctx, tx, userID, updatedFavorites); err != nil {
		return err
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit favorite question transaction: %w", err)
	}

	return nil
}

func loadFavoriteQuestions(
	ctx context.Context,
	queryer sqlQueryer,
	userID string,
	forUpdate bool,
) ([]FavoriteQuestion, error) {
	query := `
		SELECT favorite_questions
		FROM "user"
		WHERE id = $1
	`
	if forUpdate {
		query += ` FOR UPDATE`
	}

	var payload []byte
	if err := queryer.QueryRowContext(ctx, query, userID).Scan(&payload); err != nil {
		return nil, classifyError(err)
	}

	if len(payload) == 0 {
		return []FavoriteQuestion{}, nil
	}

	var favorites []FavoriteQuestion
	if err := json.Unmarshal(payload, &favorites); err != nil {
		return nil, fmt.Errorf("decode favorite questions: %w", err)
	}

	return normalizeFavoriteQuestions(favorites), nil
}

func saveFavoriteQuestions(
	ctx context.Context,
	queryer sqlQueryer,
	userID string,
	favorites []FavoriteQuestion,
) error {
	normalizedFavorites := normalizeFavoriteQuestions(favorites)

	var payload any
	if len(normalizedFavorites) > 0 {
		raw, err := json.Marshal(normalizedFavorites)
		if err != nil {
			return fmt.Errorf("encode favorite questions: %w", err)
		}
		payload = raw
	}

	result, err := queryer.ExecContext(
		ctx,
		`
			UPDATE "user"
			SET favorite_questions = $2
			WHERE id = $1
		`,
		userID,
		payload,
	)
	if err != nil {
		return classifyError(err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read affected rows: %w", err)
	}
	if rowsAffected == 0 {
		return ErrNotFound
	}

	return nil
}

func upsertFavoriteQuestion(
	favorites []FavoriteQuestion,
	source FavoriteQuestionSource,
) ([]FavoriteQuestion, FavoriteQuestion) {
	source = normalizeFavoriteQuestionSource(source)
	questionKey := normalizeFavoriteQuestionText(source.Interviewer)
	now := source.FavoritedAt
	if now.IsZero() {
		now = time.Now().UTC()
		source.FavoritedAt = now
	}

	for index := range favorites {
		favorite := normalizeFavoriteQuestion(favorites[index])
		if favorite.QuestionKey != questionKey {
			favorites[index] = favorite
			continue
		}

		for _, existingSource := range favorite.Sources {
			if existingSource.InterviewID == source.InterviewID && existingSource.ReviewIndex == source.ReviewIndex {
				favorites[index] = favorite
				normalizedFavorites := normalizeFavoriteQuestions(favorites)
				return normalizedFavorites, findFavoriteQuestionByID(normalizedFavorites, favorite.ID)
			}
		}

		favorite.Sources = append(favorite.Sources, source)
		if strings.TrimSpace(favorite.Question) == "" {
			favorite.Question = source.Interviewer
		}
		if favorite.CreatedAt.IsZero() {
			favorite.CreatedAt = firstFavoritedAt(favorite.Sources)
		}
		favorite.UpdatedAt = latestFavoritedAt(favorite.Sources)
		favorites[index] = favorite

		normalizedFavorites := normalizeFavoriteQuestions(favorites)
		return normalizedFavorites, findFavoriteQuestionByID(normalizedFavorites, favorite.ID)
	}

	favorite := FavoriteQuestion{
		ID:          uuid.NewString(),
		Question:    source.Interviewer,
		QuestionKey: questionKey,
		CreatedAt:   now,
		UpdatedAt:   now,
		Sources:     []FavoriteQuestionSource{source},
	}

	favorites = append(favorites, favorite)
	normalizedFavorites := normalizeFavoriteQuestions(favorites)
	return normalizedFavorites, findFavoriteQuestionByID(normalizedFavorites, favorite.ID)
}

func removeFavoriteQuestionSource(
	favorites []FavoriteQuestion,
	interviewID string,
	reviewIndex int,
) ([]FavoriteQuestion, bool) {
	removed := false
	updatedFavorites := make([]FavoriteQuestion, 0, len(favorites))

	for _, favorite := range favorites {
		favorite = normalizeFavoriteQuestion(favorite)
		if removed {
			updatedFavorites = append(updatedFavorites, favorite)
			continue
		}

		sources := favorite.Sources[:0]
		sourceRemoved := false
		for _, source := range favorite.Sources {
			if !sourceRemoved && source.InterviewID == interviewID && source.ReviewIndex == reviewIndex {
				sourceRemoved = true
				removed = true
				continue
			}
			sources = append(sources, source)
		}

		if !sourceRemoved {
			updatedFavorites = append(updatedFavorites, favorite)
			continue
		}
		if len(sources) == 0 {
			continue
		}

		favorite.Sources = append([]FavoriteQuestionSource(nil), sources...)
		favorite.UpdatedAt = latestFavoritedAt(favorite.Sources)
		if favorite.CreatedAt.IsZero() {
			favorite.CreatedAt = firstFavoritedAt(favorite.Sources)
		}
		updatedFavorites = append(updatedFavorites, favorite)
	}

	return normalizeFavoriteQuestions(updatedFavorites), removed
}

func removeFavoriteQuestionByID(favorites []FavoriteQuestion, favoriteID string) ([]FavoriteQuestion, bool) {
	updatedFavorites := make([]FavoriteQuestion, 0, len(favorites))
	removed := false

	for _, favorite := range favorites {
		if favorite.ID == favoriteID {
			removed = true
			continue
		}
		updatedFavorites = append(updatedFavorites, favorite)
	}

	return normalizeFavoriteQuestions(updatedFavorites), removed
}

func normalizeFavoriteQuestions(favorites []FavoriteQuestion) []FavoriteQuestion {
	normalized := make([]FavoriteQuestion, 0, len(favorites))
	for _, favorite := range favorites {
		favorite = normalizeFavoriteQuestion(favorite)
		if favorite.ID == "" || favorite.QuestionKey == "" || len(favorite.Sources) == 0 {
			continue
		}
		normalized = append(normalized, favorite)
	}

	sort.SliceStable(normalized, func(left, right int) bool {
		if !normalized[left].UpdatedAt.Equal(normalized[right].UpdatedAt) {
			return normalized[left].UpdatedAt.After(normalized[right].UpdatedAt)
		}
		if !normalized[left].CreatedAt.Equal(normalized[right].CreatedAt) {
			return normalized[left].CreatedAt.After(normalized[right].CreatedAt)
		}
		return normalized[left].Question < normalized[right].Question
	})

	return normalized
}

func normalizeFavoriteQuestion(favorite FavoriteQuestion) FavoriteQuestion {
	favorite.Question = strings.TrimSpace(favorite.Question)
	favorite.QuestionKey = normalizeFavoriteQuestionText(firstNonEmpty(favorite.QuestionKey, favorite.Question))
	favorite.Sources = normalizeFavoriteQuestionSources(favorite.Sources)
	if favorite.CreatedAt.IsZero() {
		favorite.CreatedAt = firstFavoritedAt(favorite.Sources)
	}
	if favorite.UpdatedAt.IsZero() {
		favorite.UpdatedAt = latestFavoritedAt(favorite.Sources)
	}
	if favorite.CreatedAt.IsZero() {
		favorite.CreatedAt = favorite.UpdatedAt
	}
	if favorite.UpdatedAt.IsZero() {
		favorite.UpdatedAt = favorite.CreatedAt
	}
	return favorite
}

func normalizeFavoriteQuestionSources(sources []FavoriteQuestionSource) []FavoriteQuestionSource {
	normalized := make([]FavoriteQuestionSource, 0, len(sources))
	for _, source := range sources {
		source = normalizeFavoriteQuestionSource(source)
		if strings.TrimSpace(source.Interviewer) == "" {
			continue
		}
		normalized = append(normalized, source)
	}

	sort.SliceStable(normalized, func(left, right int) bool {
		if !normalized[left].FavoritedAt.Equal(normalized[right].FavoritedAt) {
			return normalized[left].FavoritedAt.After(normalized[right].FavoritedAt)
		}
		if normalized[left].InterviewCreatedAt != normalized[right].InterviewCreatedAt {
			return normalized[left].InterviewCreatedAt > normalized[right].InterviewCreatedAt
		}
		if normalized[left].InterviewID != normalized[right].InterviewID {
			return normalized[left].InterviewID > normalized[right].InterviewID
		}
		return normalized[left].ReviewIndex > normalized[right].ReviewIndex
	})

	return normalized
}

func normalizeFavoriteQuestionSource(source FavoriteQuestionSource) FavoriteQuestionSource {
	source.InterviewID = strings.TrimSpace(source.InterviewID)
	source.Interviewer = strings.TrimSpace(source.Interviewer)
	source.InterviewerRole = strings.TrimSpace(source.InterviewerRole)
	source.Interviewee = strings.TrimSpace(source.Interviewee)
	source.StandardAnswer = strings.TrimSpace(source.StandardAnswer)
	source.Advice = strings.TrimSpace(source.Advice)
	source.Concept = strings.TrimSpace(source.Concept)
	source.DifficultyLabel = strings.TrimSpace(source.DifficultyLabel)
	source.ScoreRationale = strings.TrimSpace(source.ScoreRationale)
	source.ReasonTags = normalizeStringSlice(source.ReasonTags)
	source.StrengthPoints = normalizeStringSlice(source.StrengthPoints)
	source.MissingPoints = normalizeStringSlice(source.MissingPoints)
	if source.FavoritedAt.IsZero() {
		source.FavoritedAt = time.Now().UTC()
	}
	return source
}

func normalizeFavoriteQuestionText(question string) string {
	return strings.ToLower(strings.Join(strings.Fields(question), " "))
}

func normalizeStringSlice(values []string) []string {
	if len(values) == 0 {
		return []string{}
	}

	seen := make(map[string]struct{}, len(values))
	normalized := make([]string, 0, len(values))
	for _, value := range values {
		text := strings.TrimSpace(value)
		if text == "" {
			continue
		}
		if _, exists := seen[text]; exists {
			continue
		}
		seen[text] = struct{}{}
		normalized = append(normalized, text)
	}
	if len(normalized) == 0 {
		return []string{}
	}
	return normalized
}

func latestFavoritedAt(sources []FavoriteQuestionSource) time.Time {
	var latest time.Time
	for _, source := range sources {
		if latest.IsZero() || source.FavoritedAt.After(latest) {
			latest = source.FavoritedAt
		}
	}
	return latest
}

func firstFavoritedAt(sources []FavoriteQuestionSource) time.Time {
	var earliest time.Time
	for _, source := range sources {
		if earliest.IsZero() || source.FavoritedAt.Before(earliest) {
			earliest = source.FavoritedAt
		}
	}
	return earliest
}

func findFavoriteQuestionByID(favorites []FavoriteQuestion, favoriteID string) FavoriteQuestion {
	for _, favorite := range favorites {
		if favorite.ID == favoriteID {
			return favorite
		}
	}
	return FavoriteQuestion{}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}
