package database

import (
	"encoding/json"
	"time"
)

type UserRole string

const (
	RoleAdmin UserRole = "admin"
	RoleUser  UserRole = "user"
)

func (r UserRole) IsValid() bool {
	switch r {
	case RoleAdmin, RoleUser:
		return true
	default:
		return false
	}
}

type UserJob string

const (
	JobFrontend UserJob = "frontend"
	JobBackend  UserJob = "backend"
)

func (j UserJob) IsValid() bool {
	switch j {
	case JobFrontend, JobBackend:
		return true
	default:
		return false
	}
}

type InterviewStatus string

const (
	InterviewStarted InterviewStatus = "started"
	InterviewStopped InterviewStatus = "stopped"
)

type InterviewMode string

const (
	InterviewModeSingle    InterviewMode = "single"
	InterviewModePanelTrio InterviewMode = "panel_trio"
)

func (m InterviewMode) IsValid() bool {
	switch m {
	case InterviewModeSingle, InterviewModePanelTrio:
		return true
	default:
		return false
	}
}

type User struct {
	ID              string
	Name            string
	Account         string
	PasswordHash    string
	Role            UserRole
	Job             UserJob
	Resume          string
	Personalization string
}

type Profile struct {
	Name            string  `json:"name"`
	Job             UserJob `json:"job"`
	Resume          string  `json:"resume,omitempty"`
	Personalization string  `json:"personalization,omitempty"`
}

type ScoreBreakdown struct {
	CoverageScore     float64 `json:"coverage_score"`
	ConsistencyScore  float64 `json:"consistency_score"`
	CompletenessScore float64 `json:"completeness_score"`
}

type FavoriteQuestionSource struct {
	InterviewID        string          `json:"interview_id"`
	ReviewIndex        int             `json:"review_index"`
	InterviewCreatedAt int64           `json:"interview_created_at"`
	FavoritedAt        time.Time       `json:"favorited_at"`
	Interviewer        string          `json:"interviewer"`
	InterviewerRole    string          `json:"interviewer_role"`
	Interviewee        string          `json:"interviewee"`
	StandardAnswer     string          `json:"standard_answer,omitempty"`
	Score              float64         `json:"score"`
	Advice             string          `json:"advice"`
	Concept            string          `json:"concept,omitempty"`
	DifficultyLabel    string          `json:"difficulty_label"`
	ScoreBreakdown     *ScoreBreakdown `json:"score_breakdown,omitempty"`
	ReasonTags         []string        `json:"reason_tags"`
	StrengthPoints     []string        `json:"strength_points"`
	MissingPoints      []string        `json:"missing_points"`
	ScoreRationale     string          `json:"score_rationale,omitempty"`
}

type FavoriteQuestion struct {
	ID          string                   `json:"id"`
	Question    string                   `json:"question"`
	QuestionKey string                   `json:"question_key"`
	CreatedAt   time.Time                `json:"created_at"`
	UpdatedAt   time.Time                `json:"updated_at"`
	Sources     []FavoriteQuestionSource `json:"sources"`
}

type ResumeAnalysisLabel string

const (
	ResumeAnalysisLabelStrength ResumeAnalysisLabel = "strength"
	ResumeAnalysisLabelProbe    ResumeAnalysisLabel = "probe"
	ResumeAnalysisLabelRisk     ResumeAnalysisLabel = "risk"
	ResumeAnalysisLabelNeutral  ResumeAnalysisLabel = "neutral"
)

func (l ResumeAnalysisLabel) IsValid() bool {
	switch l {
	case ResumeAnalysisLabelStrength, ResumeAnalysisLabelProbe, ResumeAnalysisLabelRisk, ResumeAnalysisLabelNeutral:
		return true
	default:
		return false
	}
}

type ResumeAnalysisHighlightPhrase struct {
	Text    string              `json:"text"`
	Label   ResumeAnalysisLabel `json:"label"`
	Comment string              `json:"comment,omitempty"`
}

type ResumeAnalysisCallout struct {
	Title string `json:"title,omitempty"`
	Body  string `json:"body"`
}

type ResumeAnalysisBlock struct {
	ID               string                          `json:"id"`
	Text             string                          `json:"text"`
	Label            ResumeAnalysisLabel             `json:"label"`
	Reason           string                          `json:"reason,omitempty"`
	HighlightPhrases []ResumeAnalysisHighlightPhrase `json:"highlight_phrases,omitempty"`
	Callout          *ResumeAnalysisCallout          `json:"callout,omitempty"`
}

type ResumeAnalysis struct {
	Version     string                `json:"version"`
	Job         UserJob               `json:"job"`
	GeneratedAt time.Time             `json:"generated_at"`
	Summary     string                `json:"summary"`
	OverallTone string                `json:"overall_tone,omitempty"`
	Blocks      []ResumeAnalysisBlock `json:"blocks"`
}

type Session struct {
	UserID  string
	Name    string
	Account string
	Role    UserRole
	TokenID string
}

type Interview struct {
	ID        string
	Mode      InterviewMode
	Status    InterviewStatus
	CreatedAt time.Time
	Report    json.RawMessage
	UserID    string
}

type CreateUserParams struct {
	ID           string
	Name         string
	Account      string
	PasswordHash string
	Role         UserRole
	Job          UserJob
}

type CreateTokenParams struct {
	ID        string
	TokenID   string
	UserID    string
	TokenHash string
	ExpiresAt time.Time
}

type CreateInterviewParams struct {
	ID     string
	UserID string
	Mode   InterviewMode
}
