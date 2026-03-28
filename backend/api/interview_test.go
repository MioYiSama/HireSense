package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

func TestEnsureInterviewAccess(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		principal  authpkg.Principal
		interview  database.Interview
		wantStatus int
	}{
		{
			name: "admin can access any interview",
			principal: authpkg.Principal{
				UserID: "admin-1",
				Role:   database.RoleAdmin,
			},
			interview: database.Interview{UserID: "user-1"},
		},
		{
			name: "owner can access own interview",
			principal: authpkg.Principal{
				UserID: "user-1",
				Role:   database.RoleUser,
			},
			interview: database.Interview{UserID: "user-1"},
		},
		{
			name: "other users are forbidden",
			principal: authpkg.Principal{
				UserID: "user-2",
				Role:   database.RoleUser,
			},
			interview:  database.Interview{UserID: "user-1"},
			wantStatus: fiber.StatusForbidden,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			err := ensureInterviewAccess(tt.principal, tt.interview)
			if tt.wantStatus == 0 {
				if err != nil {
					t.Fatalf("ensureInterviewAccess() error = %v, want nil", err)
				}
				return
			}

			var httpErr *HTTPError
			if !errors.As(err, &httpErr) {
				t.Fatalf("ensureInterviewAccess() returned %T, want *HTTPError", err)
			}
			if httpErr.Status != tt.wantStatus {
				t.Fatalf("status = %d, want %d", httpErr.Status, tt.wantStatus)
			}
		})
	}
}

func TestRawReportToAny(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		raw  json.RawMessage
		want any
	}{
		{
			name: "empty report",
			raw:  nil,
			want: nil,
		},
		{
			name: "valid json",
			raw:  json.RawMessage(`{"score":5,"tags":["go","fiber"]}`),
			want: map[string]any{
				"score": float64(5),
				"tags":  []any{"go", "fiber"},
			},
		},
		{
			name: "invalid json falls back to raw string",
			raw:  json.RawMessage(`{not-json}`),
			want: "{not-json}",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := rawReportToAny(tt.raw)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("rawReportToAny(%s) = %#v, want %#v", string(tt.raw), got, tt.want)
			}
		})
	}
}

func TestParseRequestMediaType(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		input   string
		want    string
		wantErr bool
	}{
		{name: "empty content type", input: "   ", want: ""},
		{name: "json with charset", input: "Application/JSON; charset=utf-8", want: "application/json"},
		{name: "audio media type", input: "audio/webm", want: "audio/webm"},
		{name: "invalid content type", input: ";", wantErr: true},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := parseRequestMediaType(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("parseRequestMediaType(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
			if got != tt.want {
				t.Fatalf("parseRequestMediaType(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestAudioFilenameForMediaType(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		mediaType string
		want      string
	}{
		{name: "wav", mediaType: "audio/wav", want: "interview-reply.wav"},
		{name: "strip x prefix", mediaType: "audio/x-wav", want: "interview-reply.wav"},
		{name: "missing subtype uses default", mediaType: "audio/", want: defaultInterviewAudioFilename},
		{name: "invalid type uses default", mediaType: "invalid", want: defaultInterviewAudioFilename},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := audioFilenameForMediaType(tt.mediaType); got != tt.want {
				t.Fatalf("audioFilenameForMediaType(%q) = %q, want %q", tt.mediaType, got, tt.want)
			}
		})
	}
}

func TestMapInterviewServiceError(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name        string
		input       error
		wantStatus  int
		wantMessage string
		wantSameErr bool
	}{
		{
			name:        "text required",
			input:       ErrInterviewTextRequired,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "text is required",
		},
		{
			name:        "audio required",
			input:       ErrInterviewAudioRequired,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "audio payload is required",
		},
		{
			name:        "empty transcript",
			input:       ErrInterviewTranscriptEmpty,
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "audio did not contain recognizable speech",
		},
		{
			name:        "whisper upstream failure",
			input:       &InterviewUpstreamError{Service: "whisper", Err: errors.New("down")},
			wantStatus:  fiber.StatusBadGateway,
			wantMessage: "语音转写服务暂时不可用",
		},
		{
			name:        "ai upstream failure",
			input:       &InterviewUpstreamError{Service: "ai", Err: errors.New("down")},
			wantStatus:  fiber.StatusBadGateway,
			wantMessage: "面试服务暂时不可用",
		},
		{
			name:        "tts upstream failure",
			input:       &InterviewUpstreamError{Service: "tts", Err: errors.New("down")},
			wantStatus:  fiber.StatusBadGateway,
			wantMessage: "语音合成服务暂时不可用",
		},
		{
			name:        "unknown error passes through",
			input:       errors.New("boom"),
			wantSameErr: true,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := mapInterviewServiceError(tt.input)
			if tt.wantSameErr {
				if !errors.Is(got, tt.input) {
					t.Fatalf("mapInterviewServiceError(%v) = %v, want original error", tt.input, got)
				}
				return
			}

			var httpErr *HTTPError
			if !errors.As(got, &httpErr) {
				t.Fatalf("mapInterviewServiceError(%v) returned %T, want *HTTPError", tt.input, got)
			}
			if httpErr.Status != tt.wantStatus {
				t.Fatalf("status = %d, want %d", httpErr.Status, tt.wantStatus)
			}
			if httpErr.Message != tt.wantMessage {
				t.Fatalf("message = %q, want %q", httpErr.Message, tt.wantMessage)
			}
		})
	}
}

func TestDecodeInterviewReplyRequest(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name            string
		contentType     string
		body            []byte
		wantStatus      int
		wantText        string
		wantAudioName   string
		wantAudioType   string
		wantAudioLength float64
		wantMessage     string
	}{
		{
			name:        "json body preserves whitespace",
			contentType: "application/json",
			body:        []byte("{\"text\":\"  function solve() {\\n    return 42;\\n  }  \"}"),
			wantStatus:  fiber.StatusOK,
			wantText:    "  function solve() {\n    return 42;\n  }  ",
		},
		{
			name:            "audio body",
			contentType:     "audio/webm",
			body:            []byte("abc"),
			wantStatus:      fiber.StatusOK,
			wantAudioName:   "interview-reply.webm",
			wantAudioType:   "audio/webm",
			wantAudioLength: 3,
		},
		{
			name:        "blank json text",
			contentType: "application/json",
			body:        []byte(`{"text":"   "}`),
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "text is required",
		},
		{
			name:        "unsupported content type",
			contentType: "text/plain",
			body:        []byte("hello"),
			wantStatus:  fiber.StatusUnsupportedMediaType,
			wantMessage: "unsupported content type",
		},
		{
			name:        "invalid content type",
			contentType: ";",
			body:        []byte("hello"),
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "invalid content type",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			app := fiber.New(fiber.Config{ErrorHandler: ErrorHandler})
			app.Post("/", func(c fiber.Ctx) error {
				request, err := decodeInterviewReplyRequest(c, "interview-1")
				if err != nil {
					return err
				}

				response := fiber.Map{
					"interview_id": request.InterviewID,
					"text":         request.Text,
				}
				if request.Audio != nil {
					response["audio_filename"] = request.Audio.Filename
					response["audio_type"] = request.Audio.ContentType
					response["audio_length"] = len(request.Audio.Data)
				}
				return c.JSON(response)
			})

			req := httptest.NewRequest(http.MethodPost, "http://example.com/", bytes.NewReader(tt.body))
			if tt.contentType != "" {
				req.Header.Set(fiber.HeaderContentType, tt.contentType)
			}

			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}

			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}

			if tt.wantStatus == fiber.StatusOK {
				var body map[string]any
				if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
					t.Fatalf("Decode() error = %v", err)
				}

				if got := body["interview_id"]; got != "interview-1" {
					t.Fatalf("interview_id = %#v, want %q", got, "interview-1")
				}
				if got := body["text"]; got != tt.wantText {
					t.Fatalf("text = %#v, want %q", got, tt.wantText)
				}
				if tt.wantAudioName != "" {
					if got := body["audio_filename"]; got != tt.wantAudioName {
						t.Fatalf("audio_filename = %#v, want %q", got, tt.wantAudioName)
					}
					if got := body["audio_type"]; got != tt.wantAudioType {
						t.Fatalf("audio_type = %#v, want %q", got, tt.wantAudioType)
					}
					if got := body["audio_length"]; got != tt.wantAudioLength {
						t.Fatalf("audio_length = %#v, want %v", got, tt.wantAudioLength)
					}
				}
				return
			}

			var body envelope
			if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
				t.Fatalf("Decode() error = %v", err)
			}
			if body.Message != tt.wantMessage {
				t.Fatalf("message = %q, want %q", body.Message, tt.wantMessage)
			}
		})
	}
}

func TestDecodeInterviewStartMode(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name        string
		body        []byte
		contentType string
		wantStatus  int
		wantMode    string
		wantMessage string
	}{
		{
			name:       "empty body defaults to single",
			wantStatus: fiber.StatusOK,
			wantMode:   "single",
		},
		{
			name:        "panel trio body",
			body:        []byte(`{"mode":"panel_trio"}`),
			contentType: "application/json",
			wantStatus:  fiber.StatusOK,
			wantMode:    "panel_trio",
		},
		{
			name:        "blank mode defaults to single",
			body:        []byte(`{"mode":"   "}`),
			contentType: "application/json",
			wantStatus:  fiber.StatusOK,
			wantMode:    "single",
		},
		{
			name:        "invalid mode rejected",
			body:        []byte(`{"mode":"duo"}`),
			contentType: "application/json",
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "invalid interview mode",
		},
		{
			name:        "non json body rejected",
			body:        []byte("mode=panel_trio"),
			contentType: "text/plain",
			wantStatus:  fiber.StatusUnsupportedMediaType,
			wantMessage: "unsupported content type",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			app := fiber.New(fiber.Config{ErrorHandler: ErrorHandler})
			app.Post("/", func(c fiber.Ctx) error {
				mode, err := decodeInterviewStartMode(c)
				if err != nil {
					return err
				}

				return c.JSON(fiber.Map{"mode": string(mode)})
			})

			req := httptest.NewRequest(http.MethodPost, "http://example.com/", bytes.NewReader(tt.body))
			if tt.contentType != "" {
				req.Header.Set(fiber.HeaderContentType, tt.contentType)
			}

			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}

			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}

			if tt.wantStatus == fiber.StatusOK {
				var body map[string]any
				if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
					t.Fatalf("Decode() error = %v", err)
				}
				if got := body["mode"]; got != tt.wantMode {
					t.Fatalf("mode = %#v, want %q", got, tt.wantMode)
				}
				return
			}

			var body envelope
			if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
				t.Fatalf("Decode() error = %v", err)
			}
			if body.Message != tt.wantMessage {
				t.Fatalf("message = %q, want %q", body.Message, tt.wantMessage)
			}
		})
	}
}
