//go:build interview_ai

package api

import (
	"context"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestRemoteInterviewBackendLiveRoundTrip(t *testing.T) {
	if os.Getenv("RUN_LIVE_AI_TESTS") != "1" {
		t.Skip("set RUN_LIVE_AI_TESTS=1 to run against the live AI service")
	}

	baseURL := strings.TrimSpace(os.Getenv("AI_URL"))
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8081"
	}

	backend := &remoteInterviewBackend{
		baseURL: baseURL,
		client: &http.Client{
			Timeout: 90 * time.Second,
		},
	}

	sessionID := uuid.NewString()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	startResult, err := backend.Start(ctx, InterviewSession{
		ID:              sessionID,
		Job:             "backend",
		Resume:          "3年后端开发经验，熟悉 Go、MySQL、Redis、Kafka。",
		Personalization: "请保持专业、简洁，重点考察后端基础能力。",
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}
	if strings.TrimSpace(startResult.Reply) == "" {
		t.Fatal("Start() returned empty initial reply")
	}

	t.Cleanup(func() {
		stopCtx, stopCancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer stopCancel()
		if err := backend.Stop(stopCtx, sessionID); err != nil {
			t.Logf("Stop() cleanup error: %v", err)
		}
	})

	replyResult, err := backend.Reply(ctx, interviewReplyPayload{
		InterviewID: sessionID,
		Text:        "我会先从缓存、限流、熔断和降级几个方向来处理高并发场景。",
	})
	if err != nil {
		t.Fatalf("Reply() error = %v", err)
	}
	if strings.TrimSpace(replyResult.Reply) == "" {
		t.Fatal("Reply() returned empty reply")
	}
}
