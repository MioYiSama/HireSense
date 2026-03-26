//go:build interview_ai

package api

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRemoteInterviewBackendStartReturnsInitialReply(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "unexpected method", http.StatusMethodNotAllowed)
			return
		}
		if r.URL.Path != "/api/interview/start" {
			http.Error(w, "unexpected path", http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"success":true,"data":{"reply":"请先做一个简短的自我介绍。","mode":"panel_trio","speaker_role":"hr"}}`))
	}))
	defer server.Close()

	backend := &remoteInterviewBackend{
		baseURL: server.URL,
		client:  server.Client(),
	}

	result, err := backend.Start(context.Background(), InterviewSession{
		ID:  "interview-1",
		Job: "backend",
	})
	if err != nil {
		t.Fatalf("Start() error = %v", err)
	}
	if result.Reply != "请先做一个简短的自我介绍。" {
		t.Fatalf("result.Reply = %q, want %q", result.Reply, "请先做一个简短的自我介绍。")
	}
	if result.Mode != "panel_trio" {
		t.Fatalf("result.Mode = %q, want %q", result.Mode, "panel_trio")
	}
	if result.SpeakerRole != "hr" {
		t.Fatalf("result.SpeakerRole = %q, want %q", result.SpeakerRole, "hr")
	}
}

func TestRemoteInterviewBackendStartRejectsEmptyInitialReply(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"success":true,"data":{"reply":""}}`))
	}))
	defer server.Close()

	backend := &remoteInterviewBackend{
		baseURL: server.URL,
		client:  server.Client(),
	}

	_, err := backend.Start(context.Background(), InterviewSession{
		ID:  "interview-1",
		Job: "backend",
	})
	if err == nil {
		t.Fatal("Start() returned nil error")
	}
}

func TestRemoteInterviewBackendReplyParsesEnding(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "unexpected method", http.StatusMethodNotAllowed)
			return
		}
		if r.URL.Path != "/api/interview/reply" {
			http.Error(w, "unexpected path", http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"reply":"感谢你的作答，今天的面试先到这里。","ending":true,"mode":"panel_trio","speaker_role":"executive"}`))
	}))
	defer server.Close()

	backend := &remoteInterviewBackend{
		baseURL: server.URL,
		client:  server.Client(),
	}

	result, err := backend.Reply(context.Background(), interviewReplyPayload{
		InterviewID: "interview-1",
		Text:        "我补充完了。",
	})
	if err != nil {
		t.Fatalf("Reply() error = %v", err)
	}
	if result.Reply != "感谢你的作答，今天的面试先到这里。" {
		t.Fatalf("result.Reply = %q, want %q", result.Reply, "感谢你的作答，今天的面试先到这里。")
	}
	if !result.Ending {
		t.Fatal("result.Ending = false, want true")
	}
	if result.Mode != "panel_trio" {
		t.Fatalf("result.Mode = %q, want %q", result.Mode, "panel_trio")
	}
	if result.SpeakerRole != "executive" {
		t.Fatalf("result.SpeakerRole = %q, want %q", result.SpeakerRole, "executive")
	}
}

func TestRemoteInterviewBackendAnalyzeResumeParsesStructuredResult(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "unexpected method", http.StatusMethodNotAllowed)
			return
		}
		if r.URL.Path != "/api/resume/analyze" {
			http.Error(w, "unexpected path", http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"version":"v1",
			"job":"backend",
			"generated_at":"2026-03-26T12:00:00Z",
			"summary":"命中 1 处高风险措辞。",
			"overall_tone":"sharp",
			"blocks":[
				{
					"id":"block-1",
					"text":"精通高并发系统设计",
					"label":"risk",
					"reason":"措辞过满",
					"highlight_phrases":[{"text":"精通高并发","label":"risk","comment":"会被追问规模"}],
					"callout":{"title":"高危吹牛词","body":"准备挨打"}
				}
			]
		}`))
	}))
	defer server.Close()

	backend := &remoteInterviewBackend{
		baseURL: server.URL,
		client:  server.Client(),
	}

	result, err := backend.AnalyzeResume(context.Background(), ResumeAnalysisRequest{
		Job:    "backend",
		Resume: "精通高并发系统设计",
	})
	if err != nil {
		t.Fatalf("AnalyzeResume() error = %v", err)
	}

	if result.Job != "backend" {
		t.Fatalf("result.Job = %q, want %q", result.Job, "backend")
	}
	if len(result.Blocks) != 1 {
		t.Fatalf("len(result.Blocks) = %d, want 1", len(result.Blocks))
	}
	if result.Blocks[0].Label != "risk" {
		t.Fatalf("result.Blocks[0].Label = %q, want %q", result.Blocks[0].Label, "risk")
	}
	if result.Blocks[0].Callout == nil || result.Blocks[0].Callout.Body == "" {
		t.Fatal("result.Blocks[0].Callout is empty")
	}
}
