package api

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type stubInterviewBackend struct {
	replyResult InterviewReplyResult
	replyErr    error
	replyCalls  []interviewReplyPayload
}

func (s *stubInterviewBackend) Start(context.Context, InterviewSession) error {
	return nil
}

func (s *stubInterviewBackend) Reply(_ context.Context, payload interviewReplyPayload) (InterviewReplyResult, error) {
	s.replyCalls = append(s.replyCalls, payload)
	return s.replyResult, s.replyErr
}

func (s *stubInterviewBackend) Stop(context.Context, string) error {
	return nil
}

func TestNormalizeURL(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		input   string
		want    string
		wantErr bool
	}{
		{name: "trimmed absolute url", input: " https://example.com/api ", want: "https://example.com/api"},
		{name: "missing scheme", input: "example.com/api", wantErr: true},
		{name: "blank url", input: "   ", wantErr: true},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := normalizeURL(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("normalizeURL(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
			if got != tt.want {
				t.Fatalf("normalizeURL(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestResolveEndpoint(t *testing.T) {
	t.Parallel()

	got, err := resolveEndpoint("https://example.com/api/", "/v1/interviews")
	if err != nil {
		t.Fatalf("resolveEndpoint() error = %v", err)
	}
	if got != "https://example.com/v1/interviews" {
		t.Fatalf("resolveEndpoint() = %q, want %q", got, "https://example.com/v1/interviews")
	}
}

func TestReadHTTPError(t *testing.T) {
	t.Parallel()

	response := &http.Response{
		Status: "502 Bad Gateway",
		Body:   io.NopCloser(strings.NewReader(" upstream failed ")),
	}

	err := readHTTPError("whisper service", response)
	if err == nil {
		t.Fatal("readHTTPError() returned nil")
	}
	if got, want := err.Error(), "whisper service returned 502 Bad Gateway: upstream failed"; got != want {
		t.Fatalf("readHTTPError() = %q, want %q", got, want)
	}
}

func TestSanitizeAudioFilename(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		filename string
		want     string
	}{
		{name: "trim surrounding spaces", filename: "  clip.wav  ", want: "clip.wav"},
		{name: "drop quotes", filename: `"clip.wav"`, want: "clip.wav"},
		{name: "blank uses default", filename: "   ", want: defaultInterviewAudioFilename},
		{name: "quotes only uses default", filename: `""`, want: defaultInterviewAudioFilename},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := sanitizeAudioFilename(tt.filename); got != tt.want {
				t.Fatalf("sanitizeAudioFilename(%q) = %q, want %q", tt.filename, got, tt.want)
			}
		})
	}
}

func TestInterviewServiceReplyTrimsTextBeforeCallingBackend(t *testing.T) {
	t.Parallel()

	backend := &stubInterviewBackend{
		replyResult: InterviewReplyResult{Reply: "ok", Ending: false},
	}
	service := &InterviewService{
		backend: backend,
	}

	result, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Text:        "  hello world  ",
	})
	if err != nil {
		t.Fatalf("Reply() error = %v", err)
	}
	if result.Reply != "ok" {
		t.Fatalf("result.Reply = %q, want %q", result.Reply, "ok")
	}
	if len(backend.replyCalls) != 1 {
		t.Fatalf("backend reply calls = %d, want 1", len(backend.replyCalls))
	}
	if backend.replyCalls[0].Text != "hello world" {
		t.Fatalf("backend text = %q, want %q", backend.replyCalls[0].Text, "hello world")
	}
	if backend.replyCalls[0].Transcript != nil {
		t.Fatal("backend transcript should be nil for text replies")
	}
}

func TestInterviewServiceReplyRejectsMissingInput(t *testing.T) {
	t.Parallel()

	service := &InterviewService{
		backend: &stubInterviewBackend{},
	}

	if _, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Text:        "   ",
	}); !errors.Is(err, ErrInterviewTextRequired) {
		t.Fatalf("Reply() error = %v, want %v", err, ErrInterviewTextRequired)
	}

	if _, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Audio: &InterviewReplyAudio{
			Filename:    "clip.wav",
			ContentType: "audio/wav",
		},
	}); !errors.Is(err, ErrInterviewAudioRequired) {
		t.Fatalf("Reply() error = %v, want %v", err, ErrInterviewAudioRequired)
	}
}

func TestInterviewServiceReplyTranscribesAudioBeforeCallingBackend(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "unexpected method", http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(Transcript{Text: "  transcribed answer  "}); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	}))
	defer server.Close()

	backend := &stubInterviewBackend{
		replyResult: InterviewReplyResult{Reply: "processed", Ending: false},
	}
	service := &InterviewService{
		backend: backend,
		whisper: &whisperClient{
			endpoint: server.URL,
			client:   server.Client(),
		},
	}

	result, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Audio: &InterviewReplyAudio{
			Filename:    "clip.webm",
			ContentType: "audio/webm",
			Data:        []byte("abc"),
		},
	})
	if err != nil {
		t.Fatalf("Reply() error = %v", err)
	}
	if result.Reply != "processed" {
		t.Fatalf("result.Reply = %q, want %q", result.Reply, "processed")
	}
	if len(backend.replyCalls) != 1 {
		t.Fatalf("backend reply calls = %d, want 1", len(backend.replyCalls))
	}
	payload := backend.replyCalls[0]
	if payload.Text != "transcribed answer" {
		t.Fatalf("backend text = %q, want %q", payload.Text, "transcribed answer")
	}
	if payload.Transcript == nil {
		t.Fatal("backend transcript is nil")
	}
	if payload.Transcript.Text != "transcribed answer" {
		t.Fatalf("transcript text = %q, want %q", payload.Transcript.Text, "transcribed answer")
	}
}

func TestInterviewServiceReplyWrapsWhisperErrors(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "upstream failed", http.StatusBadGateway)
	}))
	defer server.Close()

	service := &InterviewService{
		backend: &stubInterviewBackend{},
		whisper: &whisperClient{
			endpoint: server.URL,
			client:   server.Client(),
		},
	}

	_, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Audio: &InterviewReplyAudio{
			Filename:    "clip.wav",
			ContentType: "audio/wav",
			Data:        []byte("abc"),
		},
	})
	if err == nil {
		t.Fatal("Reply() returned nil error")
	}

	var upstreamErr *InterviewUpstreamError
	if !errors.As(err, &upstreamErr) {
		t.Fatalf("Reply() error = %T, want *InterviewUpstreamError", err)
	}
	if upstreamErr.Service != "whisper" {
		t.Fatalf("upstream service = %q, want %q", upstreamErr.Service, "whisper")
	}
}

func TestInterviewServiceReplyRejectsEmptyTranscript(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(Transcript{Text: "   "}); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	}))
	defer server.Close()

	service := &InterviewService{
		backend: &stubInterviewBackend{},
		whisper: &whisperClient{
			endpoint: server.URL,
			client:   server.Client(),
		},
	}

	_, err := service.Reply(context.Background(), InterviewReplyRequestData{
		InterviewID: "interview-1",
		Audio: &InterviewReplyAudio{
			Filename:    "clip.wav",
			ContentType: "audio/wav",
			Data:        []byte("abc"),
		},
	})
	if !errors.Is(err, ErrInterviewTranscriptEmpty) {
		t.Fatalf("Reply() error = %v, want %v", err, ErrInterviewTranscriptEmpty)
	}
}
