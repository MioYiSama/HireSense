package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	authpkg "hire_sense/auth"
	"hire_sense/database"

	"github.com/gofiber/fiber/v3"
)

type stubInterviewTTSSynthesizer struct {
	audio   []byte
	err     error
	gotText string
}

func (s *stubInterviewTTSSynthesizer) Synthesize(_ context.Context, text string) ([]byte, error) {
	s.gotText = text
	if s.err != nil {
		return nil, s.err
	}

	return append([]byte(nil), s.audio...), nil
}

func TestInterviewHandlerTTS(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name            string
		body            []byte
		synthesizer     *stubInterviewTTSSynthesizer
		wantStatus      int
		wantMessage     string
		wantContentType string
		wantBody        []byte
		wantText        string
	}{
		{
			name: "success",
			body: []byte(`{"text":"你好，请介绍一下你最近负责的项目。"}`),
			synthesizer: &stubInterviewTTSSynthesizer{
				audio: []byte("fake-mp3"),
			},
			wantStatus:      fiber.StatusOK,
			wantContentType: "audio/mpeg",
			wantBody:        []byte("fake-mp3"),
			wantText:        "你好，请介绍一下你最近负责的项目。",
		},
		{
			name: "blank text rejected",
			body: []byte(`{"text":"   "}`),
			synthesizer: &stubInterviewTTSSynthesizer{
				audio: []byte("unused"),
			},
			wantStatus:  fiber.StatusBadRequest,
			wantMessage: "text is required",
		},
		{
			name: "tts upstream error",
			body: []byte(`{"text":"继续回答。"}`),
			synthesizer: &stubInterviewTTSSynthesizer{
				err: &InterviewUpstreamError{Service: "tts", Err: errors.New("down")},
			},
			wantStatus:  fiber.StatusBadGateway,
			wantMessage: "语音合成服务暂时不可用",
			wantText:    "继续回答。",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			app := fiber.New(fiber.Config{ErrorHandler: ErrorHandler})
			handler := interviewHandler{
				interviewTTS: tt.synthesizer,
			}
			app.Post("/", func(c fiber.Ctx) error {
				authpkg.StorePrincipal(c, authpkg.Principal{
					UserID: "user-1",
					Role:   database.RoleUser,
				})
				return handler.tts(c)
			})

			req := httptest.NewRequest(http.MethodPost, "http://example.com/", bytes.NewReader(tt.body))
			req.Header.Set(fiber.HeaderContentType, "application/json")

			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}

			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}

			if tt.wantStatus == fiber.StatusOK {
				if got := resp.Header.Get(fiber.HeaderContentType); !strings.HasPrefix(got, tt.wantContentType) {
					t.Fatalf("content-type = %q, want prefix %q", got, tt.wantContentType)
				}

				body, err := io.ReadAll(resp.Body)
				if err != nil {
					t.Fatalf("ReadAll() error = %v", err)
				}
				if !bytes.Equal(body, tt.wantBody) {
					t.Fatalf("body = %q, want %q", body, tt.wantBody)
				}
			} else {
				var body envelope
				if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
					t.Fatalf("Decode() error = %v", err)
				}
				if body.Message != tt.wantMessage {
					t.Fatalf("message = %q, want %q", body.Message, tt.wantMessage)
				}
			}

			if tt.synthesizer.gotText != tt.wantText {
				t.Fatalf("synthesizer text = %q, want %q", tt.synthesizer.gotText, tt.wantText)
			}
		})
	}
}
