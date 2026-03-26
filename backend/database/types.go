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
