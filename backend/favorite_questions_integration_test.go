//go:build integration

package main

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"hire_sense/api"
	"hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
	"github.com/google/uuid"
)

type integrationFavoriteQuestion struct {
	ID          string                            `json:"id"`
	Question    string                            `json:"question"`
	SourceCount int                               `json:"source_count"`
	Sources     []database.FavoriteQuestionSource `json:"sources"`
}

func TestFavoriteQuestionsFlowIntegration(t *testing.T) {
	dbURL := integrationDatabaseURL(t)
	sqlDB := openIntegrationSQLDB(t, dbURL)
	ensureIntegrationSchema(t, sqlDB)

	account := "integration-favorites-" + time.Now().Format("20060102150405.000000000") + "@example.com"
	cleanupIntegrationUser(t, sqlDB, account)
	t.Cleanup(func() {
		cleanupIntegrationUser(t, sqlDB, account)
	})

	store, err := database.Open(dbURL)
	if err != nil {
		t.Fatalf("database.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Fatalf("store.Close() error = %v", err)
		}
	})

	tokenManager, err := auth.NewTokenManager("hiresense-backend-integration", time.Hour)
	if err != nil {
		t.Fatalf("auth.NewTokenManager() error = %v", err)
	}

	app := fiber.New(fiber.Config{
		PassLocalsToContext: true,
		ErrorHandler:        api.ErrorHandler,
	})
	api.RegisterRoutes(app, api.Dependencies{
		Store:           store,
		AuthService:     auth.NewService(store, tokenManager),
		TokenManager:    tokenManager,
		PutReportSecret: "integration-secret",
	})

	token := signUpIntegrationUser(t, app, account, "Favorite Question User")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	user, err := store.GetUserByAccount(ctx, account)
	if err != nil {
		t.Fatalf("store.GetUserByAccount() error = %v", err)
	}

	firstInterview, err := store.CreateInterview(ctx, database.CreateInterviewParams{
		ID:     uuid.NewString(),
		UserID: user.ID,
		Mode:   database.InterviewModeSingle,
	})
	if err != nil {
		t.Fatalf("store.CreateInterview(first) error = %v", err)
	}
	secondInterview, err := store.CreateInterview(ctx, database.CreateInterviewParams{
		ID:     uuid.NewString(),
		UserID: user.ID,
		Mode:   database.InterviewModeSingle,
	})
	if err != nil {
		t.Fatalf("store.CreateInterview(second) error = %v", err)
	}

	if err := store.UpdateInterviewReport(ctx, firstInterview.ID, json.RawMessage(`{
		"job":"backend",
		"mode":"single",
		"score":71,
		"general":{},
		"general_details":{},
		"specific":{},
		"specific_details":{},
		"feedback":"feedback",
		"shortcomings":[],
		"advice":"advice",
		"resources":[],
		"reviews":[
			{
				"interviewer":"什么是幂等？",
				"interviewer_role":"ai",
				"interviewee":"第一次回答",
				"standard_answer":"定义加案例。",
				"score":61.5,
				"advice":"先定义再案例。",
				"concept":"HTTP",
				"difficulty_label":"basic",
				"score_breakdown":{"coverage_score":60,"consistency_score":62,"completeness_score":61},
				"reason_tags":["coverage_partial"],
				"strength_points":["提到了重复请求"],
				"missing_points":["没有举业务案例"],
				"score_rationale":"主线不完整。"
			}
		]
	}`)); err != nil {
		t.Fatalf("store.UpdateInterviewReport(first) error = %v", err)
	}

	if err := store.UpdateInterviewReport(ctx, secondInterview.ID, json.RawMessage(`{
		"job":"backend",
		"mode":"single",
		"score":86,
		"general":{},
		"general_details":{},
		"specific":{},
		"specific_details":{},
		"feedback":"feedback",
		"shortcomings":[],
		"advice":"advice",
		"resources":[],
		"reviews":[
			{
				"interviewer":"  什么是幂等？  ",
				"interviewer_role":"tech_lead",
				"interviewee":"第二次回答",
				"standard_answer":"定义、HTTP 方法、分布式幂等策略。",
				"score":88,
				"advice":"补充 token 和去重表。",
				"concept":"服务设计",
				"difficulty_label":"intermediate",
				"score_breakdown":{"coverage_score":87,"consistency_score":89,"completeness_score":88},
				"reason_tags":["coverage_good"],
				"strength_points":["提到了 PUT 幂等"],
				"missing_points":["没有展开 MQ 场景"],
				"score_rationale":"回答更完整。"
			}
		]
	}`)); err != nil {
		t.Fatalf("store.UpdateInterviewReport(second) error = %v", err)
	}

	addFirst := doJSONRequest(t, app, http.MethodPost, "/api/user/favorite-questions", map[string]any{
		"interview_id": firstInterview.ID,
		"review_index": 0,
	}, token)
	if addFirst.status != http.StatusOK {
		t.Fatalf("addFirst status = %d, want %d (message=%q)", addFirst.status, http.StatusOK, addFirst.body.Message)
	}

	var firstFavorite integrationFavoriteQuestion
	if err := json.Unmarshal(addFirst.body.Data, &firstFavorite); err != nil {
		t.Fatalf("json.Unmarshal(addFirst body) error = %v", err)
	}
	if firstFavorite.SourceCount != 1 {
		t.Fatalf("firstFavorite.SourceCount = %d, want 1", firstFavorite.SourceCount)
	}

	addSecond := doJSONRequest(t, app, http.MethodPost, "/api/user/favorite-questions", map[string]any{
		"interview_id": secondInterview.ID,
		"review_index": 0,
	}, token)
	if addSecond.status != http.StatusOK {
		t.Fatalf(
			"addSecond status = %d, want %d (message=%q)",
			addSecond.status,
			http.StatusOK,
			addSecond.body.Message,
		)
	}

	var mergedFavorite integrationFavoriteQuestion
	if err := json.Unmarshal(addSecond.body.Data, &mergedFavorite); err != nil {
		t.Fatalf("json.Unmarshal(addSecond body) error = %v", err)
	}
	if mergedFavorite.ID != firstFavorite.ID {
		t.Fatalf("merged favorite id = %q, want %q", mergedFavorite.ID, firstFavorite.ID)
	}
	if mergedFavorite.SourceCount != 2 {
		t.Fatalf("mergedFavorite.SourceCount = %d, want 2", mergedFavorite.SourceCount)
	}

	listResponse := doJSONRequest(t, app, http.MethodGet, "/api/user/favorite-questions", nil, token)
	if listResponse.status != http.StatusOK {
		t.Fatalf("list status = %d, want %d (message=%q)", listResponse.status, http.StatusOK, listResponse.body.Message)
	}

	var favorites []integrationFavoriteQuestion
	if err := json.Unmarshal(listResponse.body.Data, &favorites); err != nil {
		t.Fatalf("json.Unmarshal(list body) error = %v", err)
	}
	if len(favorites) != 1 {
		t.Fatalf("favorites len = %d, want 1", len(favorites))
	}
	if favorites[0].SourceCount != 2 {
		t.Fatalf("favorites[0].SourceCount = %d, want 2", favorites[0].SourceCount)
	}
	if got := favorites[0].Sources[0].InterviewID; got != secondInterview.ID {
		t.Fatalf("latest source interview_id = %q, want %q", got, secondInterview.ID)
	}

	removeSource := doJSONRequest(
		t,
		app,
		http.MethodDelete,
		"/api/user/favorite-questions/source/"+secondInterview.ID+"/0",
		nil,
		token,
	)
	if removeSource.status != http.StatusOK {
		t.Fatalf(
			"removeSource status = %d, want %d (message=%q)",
			removeSource.status,
			http.StatusOK,
			removeSource.body.Message,
		)
	}

	listAfterSourceDelete := doJSONRequest(t, app, http.MethodGet, "/api/user/favorite-questions", nil, token)
	if listAfterSourceDelete.status != http.StatusOK {
		t.Fatalf(
			"listAfterSourceDelete status = %d, want %d (message=%q)",
			listAfterSourceDelete.status,
			http.StatusOK,
			listAfterSourceDelete.body.Message,
		)
	}
	if err := json.Unmarshal(listAfterSourceDelete.body.Data, &favorites); err != nil {
		t.Fatalf("json.Unmarshal(listAfterSourceDelete body) error = %v", err)
	}
	if len(favorites) != 1 || favorites[0].SourceCount != 1 {
		t.Fatalf("favorites after source delete = %#v, want one favorite with one source", favorites)
	}

	removeFavorite := doJSONRequest(
		t,
		app,
		http.MethodDelete,
		"/api/user/favorite-questions/"+favorites[0].ID,
		nil,
		token,
	)
	if removeFavorite.status != http.StatusOK {
		t.Fatalf(
			"removeFavorite status = %d, want %d (message=%q)",
			removeFavorite.status,
			http.StatusOK,
			removeFavorite.body.Message,
		)
	}

	listAfterFavoriteDelete := doJSONRequest(t, app, http.MethodGet, "/api/user/favorite-questions", nil, token)
	if listAfterFavoriteDelete.status != http.StatusOK {
		t.Fatalf(
			"listAfterFavoriteDelete status = %d, want %d (message=%q)",
			listAfterFavoriteDelete.status,
			http.StatusOK,
			listAfterFavoriteDelete.body.Message,
		)
	}
	if err := json.Unmarshal(listAfterFavoriteDelete.body.Data, &favorites); err != nil {
		t.Fatalf("json.Unmarshal(listAfterFavoriteDelete body) error = %v", err)
	}
	if len(favorites) != 0 {
		t.Fatalf("favorites len after favorite delete = %d, want 0", len(favorites))
	}
}

func signUpIntegrationUser(t *testing.T, app *fiber.App, account string, name string) string {
	t.Helper()

	signUpResponse := doJSONRequest(t, app, http.MethodPost, "/api/auth/signup", map[string]string{
		"account":  account,
		"name":     name,
		"password": "Passw0rd!",
	}, "")
	if signUpResponse.status != http.StatusOK {
		t.Fatalf(
			"signup status = %d, want %d (message=%q)",
			signUpResponse.status,
			http.StatusOK,
			signUpResponse.body.Message,
		)
	}

	var token string
	if err := json.Unmarshal(signUpResponse.body.Data, &token); err != nil {
		t.Fatalf("json.Unmarshal(signup token) error = %v", err)
	}
	if token == "" {
		t.Fatal("signup token is empty")
	}

	return token
}
