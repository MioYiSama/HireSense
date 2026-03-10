package database

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/lib/pq"
	_ "github.com/lib/pq"
)

var (
	ErrNotFound = errors.New("database: record not found")
	ErrConflict = errors.New("database: conflict")
)

type Store struct {
	db *sql.DB
}

func Open(databaseURL string) (*Store, error) {
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(25)
	db.SetConnMaxIdleTime(5 * time.Minute)
	db.SetConnMaxLifetime(30 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping database: %w", err)
	}

	return &Store{db: db}, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) CreateUser(ctx context.Context, params CreateUserParams) (User, error) {
	const query = `
		INSERT INTO "user" (id, name, account, password, role, job)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, name, account, password, role, job, resume, personalization
	`

	user, err := scanUser(s.db.QueryRowContext(
		ctx,
		query,
		params.ID,
		params.Name,
		params.Account,
		params.PasswordHash,
		params.Role,
		params.Job,
	))
	if err != nil {
		return User{}, classifyError(err)
	}

	return user, nil
}

func (s *Store) GetUserByAccount(ctx context.Context, account string) (User, error) {
	const query = `
		SELECT id, name, account, password, role, job, resume, personalization
		FROM "user"
		WHERE account = $1
	`

	user, err := scanUser(s.db.QueryRowContext(ctx, query, account))
	if err != nil {
		return User{}, classifyError(err)
	}

	return user, nil
}

func (s *Store) GetUserByID(ctx context.Context, id string) (User, error) {
	const query = `
		SELECT id, name, account, password, role, job, resume, personalization
		FROM "user"
		WHERE id = $1
	`

	user, err := scanUser(s.db.QueryRowContext(ctx, query, id))
	if err != nil {
		return User{}, classifyError(err)
	}

	return user, nil
}

func (s *Store) CreateToken(ctx context.Context, params CreateTokenParams) error {
	const query = `
		INSERT INTO auth_token (id, token_id, user_id, token_hash, expires_at)
		VALUES ($1, $2, $3, $4, $5)
	`

	_, err := s.db.ExecContext(ctx, query, params.ID, params.TokenID, params.UserID, params.TokenHash, params.ExpiresAt)
	return classifyError(err)
}

func (s *Store) GetSessionByToken(ctx context.Context, userID, tokenID, tokenHash string) (Session, error) {
	const query = `
		SELECT u.id, u.name, u.account, u.role, at.token_id
		FROM auth_token AS at
		INNER JOIN "user" AS u ON u.id = at.user_id
		WHERE at.user_id = $1
		  AND at.token_id = $2
		  AND at.token_hash = $3
		  AND at.revoked_at IS NULL
		  AND at.expires_at > NOW()
	`

	var (
		session Session
		role    string
	)
	err := s.db.QueryRowContext(ctx, query, userID, tokenID, tokenHash).Scan(
		&session.UserID,
		&session.Name,
		&session.Account,
		&role,
		&session.TokenID,
	)
	if err != nil {
		return Session{}, classifyError(err)
	}

	session.Role = UserRole(role)
	return session, nil
}

func (s *Store) RevokeToken(ctx context.Context, userID, tokenID string) error {
	const query = `
		UPDATE auth_token
		SET revoked_at = NOW()
		WHERE user_id = $1
		  AND token_id = $2
		  AND revoked_at IS NULL
	`

	result, err := s.db.ExecContext(ctx, query, userID, tokenID)
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

func (s *Store) RevokeAllTokensForUser(ctx context.Context, userID string) error {
	const query = `
		UPDATE auth_token
		SET revoked_at = NOW()
		WHERE user_id = $1
		  AND revoked_at IS NULL
	`

	_, err := s.db.ExecContext(ctx, query, userID)
	return classifyError(err)
}

func (s *Store) UpdateUserPassword(ctx context.Context, userID, passwordHash string) error {
	const query = `
		UPDATE "user"
		SET password = $2
		WHERE id = $1
	`

	result, err := s.db.ExecContext(ctx, query, userID, passwordHash)
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

func (s *Store) GetProfile(ctx context.Context, userID string) (Profile, error) {
	const query = `
		SELECT name, job, resume, personalization
		FROM "user"
		WHERE id = $1
	`

	var (
		profile         Profile
		job             string
		resume          sql.NullString
		personalization sql.NullString
	)
	err := s.db.QueryRowContext(ctx, query, userID).Scan(&profile.Name, &job, &resume, &personalization)
	if err != nil {
		return Profile{}, classifyError(err)
	}

	profile.Job = UserJob(job)
	profile.Resume = nullableString(resume)
	profile.Personalization = nullableString(personalization)
	return profile, nil
}

func (s *Store) UpdateProfile(ctx context.Context, userID string, profile Profile) error {
	const query = `
		UPDATE "user"
		SET name = $2,
		    job = $3,
		    resume = NULLIF($4, ''),
		    personalization = NULLIF($5, '')
		WHERE id = $1
	`

	result, err := s.db.ExecContext(ctx, query, userID, profile.Name, profile.Job, profile.Resume, profile.Personalization)
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

func (s *Store) ListInterviewsByUserID(ctx context.Context, userID string) ([]Interview, error) {
	const query = `
		SELECT id, status, created_at, report, user_id
		FROM interview
		WHERE user_id = $1
		ORDER BY created_at DESC
	`

	rows, err := s.db.QueryContext(ctx, query, userID)
	if err != nil {
		return nil, classifyError(err)
	}
	defer rows.Close()

	interviews := make([]Interview, 0)
	for rows.Next() {
		interview, err := scanInterview(rows)
		if err != nil {
			return nil, err
		}
		interviews = append(interviews, interview)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate interviews: %w", err)
	}

	return interviews, nil
}

func (s *Store) CreateInterview(ctx context.Context, params CreateInterviewParams) (Interview, error) {
	const query = `
		INSERT INTO interview (id, user_id, status)
		VALUES ($1, $2, $3)
		RETURNING id, status, created_at, report, user_id
	`

	interview, err := scanInterview(s.db.QueryRowContext(ctx, query, params.ID, params.UserID, InterviewStarted))
	if err != nil {
		return Interview{}, classifyError(err)
	}

	return interview, nil
}

func (s *Store) GetInterviewByID(ctx context.Context, interviewID string) (Interview, error) {
	const query = `
		SELECT id, status, created_at, report, user_id
		FROM interview
		WHERE id = $1
	`

	interview, err := scanInterview(s.db.QueryRowContext(ctx, query, interviewID))
	if err != nil {
		return Interview{}, classifyError(err)
	}

	return interview, nil
}

func (s *Store) StopInterview(ctx context.Context, interviewID string) error {
	const query = `
		UPDATE interview
		SET status = $2
		WHERE id = $1
	`

	result, err := s.db.ExecContext(ctx, query, interviewID, InterviewStopped)
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

func (s *Store) UpdateInterviewReport(ctx context.Context, interviewID string, report json.RawMessage) error {
	const query = `
		UPDATE interview
		SET report = $2,
		    status = $3
		WHERE id = $1
	`

	result, err := s.db.ExecContext(ctx, query, interviewID, report, InterviewStopped)
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

type scanner interface {
	Scan(dest ...any) error
}

func scanUser(row scanner) (User, error) {
	var (
		user            User
		role            string
		job             string
		resume          sql.NullString
		personalization sql.NullString
	)

	if err := row.Scan(
		&user.ID,
		&user.Name,
		&user.Account,
		&user.PasswordHash,
		&role,
		&job,
		&resume,
		&personalization,
	); err != nil {
		return User{}, err
	}

	user.Role = UserRole(role)
	user.Job = UserJob(job)
	user.Resume = nullableString(resume)
	user.Personalization = nullableString(personalization)
	return user, nil
}

func scanInterview(row scanner) (Interview, error) {
	var (
		interview Interview
		status    string
		report    []byte
	)

	if err := row.Scan(
		&interview.ID,
		&status,
		&interview.CreatedAt,
		&report,
		&interview.UserID,
	); err != nil {
		return Interview{}, err
	}

	interview.Status = InterviewStatus(status)
	if len(report) > 0 {
		interview.Report = json.RawMessage(report)
	}
	return interview, nil
}

func nullableString(value sql.NullString) string {
	if value.Valid {
		return value.String
	}
	return ""
}

func classifyError(err error) error {
	if err == nil {
		return nil
	}
	if errors.Is(err, sql.ErrNoRows) {
		return ErrNotFound
	}

	var pqErr *pq.Error
	if errors.As(err, &pqErr) && pqErr.Code == "23505" {
		return ErrConflict
	}

	return err
}
