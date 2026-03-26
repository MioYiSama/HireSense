package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"net/textproto"
	"net/url"
	"strings"
	"time"

	"hire_sense/database"
)

const (
	defaultInterviewServiceTimeout = 60 * time.Second
	defaultInterviewAudioFilename  = "interview-reply.wav"
)

var (
	ErrInterviewTextRequired    = errors.New("interview text is required")
	ErrInterviewAudioRequired   = errors.New("interview audio is required")
	ErrInterviewTranscriptEmpty = errors.New("interview transcript is empty")
)

type InterviewUpstreamError struct {
	Service string
	Err     error
}

func (e *InterviewUpstreamError) Error() string {
	return fmt.Sprintf("%s service error: %v", e.Service, e.Err)
}

func (e *InterviewUpstreamError) Unwrap() error {
	return e.Err
}

type InterviewServiceConfig struct {
	AIURL      string
	WhisperURL string
	HTTPClient *http.Client
}

type InterviewSession struct {
	ID              string
	Job             string
	Resume          string
	Personalization string
	Mode            string
}

type InterviewStartResult struct {
	Reply       string
	Mode        string
	SpeakerRole string
}

type InterviewReplyAudio struct {
	Filename    string
	ContentType string
	Data        []byte
}

type InterviewReplyRequestData struct {
	InterviewID string
	Text        string
	Audio       *InterviewReplyAudio
}

type InterviewReplyResult struct {
	Reply       string
	Ending      bool
	Mode        string
	SpeakerRole string
}

type ResumeAnalysisRequest struct {
	Job    string
	Resume string
}

type Transcript struct {
	Duration float64             `json:"duration"`
	Segments []TranscriptSegment `json:"segments"`
	Text     string              `json:"text"`
}

type TranscriptSegment struct {
	Start float64          `json:"start"`
	End   float64          `json:"end"`
	Text  string           `json:"text"`
	Words []TranscriptWord `json:"words"`
}

type TranscriptWord struct {
	Word  string  `json:"word"`
	Start float64 `json:"start"`
	End   float64 `json:"end"`
}

type interviewReplyPayload struct {
	InterviewID string
	Text        string
	Transcript  *Transcript
}

type interviewConversationBackend interface {
	Start(ctx context.Context, session InterviewSession) (InterviewStartResult, error)
	Reply(ctx context.Context, payload interviewReplyPayload) (InterviewReplyResult, error)
	Stop(ctx context.Context, interviewID string) error
	AnalyzeResume(ctx context.Context, request ResumeAnalysisRequest) (database.ResumeAnalysis, error)
}

type InterviewService struct {
	backend interviewConversationBackend
	whisper *whisperClient
}

func NewInterviewService(cfg InterviewServiceConfig) (*InterviewService, error) {
	httpClient := cfg.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: defaultInterviewServiceTimeout}
	}

	whisper, err := newWhisperClient(cfg.WhisperURL, httpClient)
	if err != nil {
		return nil, err
	}

	backend, err := newInterviewConversationBackend(cfg, httpClient)
	if err != nil {
		return nil, err
	}

	return &InterviewService{
		backend: backend,
		whisper: whisper,
	}, nil
}

func (s *InterviewService) Start(ctx context.Context, session InterviewSession) (InterviewStartResult, error) {
	return s.backend.Start(ctx, session)
}

func (s *InterviewService) Reply(ctx context.Context, request InterviewReplyRequestData) (InterviewReplyResult, error) {
	trimmedText := strings.TrimSpace(request.Text)
	payload := interviewReplyPayload{
		InterviewID: request.InterviewID,
		Text:        request.Text,
	}

	if request.Audio != nil {
		if len(request.Audio.Data) == 0 {
			return InterviewReplyResult{}, ErrInterviewAudioRequired
		}

		transcribeStartedAt := time.Now()
		transcript, err := s.whisper.Transcribe(ctx, *request.Audio)
		if err != nil {
			slog.WarnContext(ctx, "interview audio transcription failed",
				"interview_id", request.InterviewID,
				"audio_bytes", len(request.Audio.Data),
				"content_type", request.Audio.ContentType,
				"duration", time.Since(transcribeStartedAt),
				"err", err,
			)
			return InterviewReplyResult{}, &InterviewUpstreamError{
				Service: "whisper",
				Err:     err,
			}
		}

		payload.Transcript = &transcript
		payload.Text = strings.TrimSpace(transcript.Text)
		trimmedText = payload.Text
		slog.InfoContext(ctx, "interview audio transcribed",
			"interview_id", request.InterviewID,
			"audio_bytes", len(request.Audio.Data),
			"content_type", request.Audio.ContentType,
			"duration", time.Since(transcribeStartedAt),
			"transcript_chars", len(payload.Text),
			"segments", len(transcript.Segments),
			"transcript", transcript,
		)
		if payload.Text == "" {
			return InterviewReplyResult{}, ErrInterviewTranscriptEmpty
		}
	}

	if trimmedText == "" {
		return InterviewReplyResult{}, ErrInterviewTextRequired
	}

	return s.backend.Reply(ctx, payload)
}

func (s *InterviewService) Stop(ctx context.Context, interviewID string) error {
	return s.backend.Stop(ctx, interviewID)
}

func (s *InterviewService) AnalyzeResume(
	ctx context.Context,
	request ResumeAnalysisRequest,
) (database.ResumeAnalysis, error) {
	if strings.TrimSpace(request.Resume) == "" {
		return database.ResumeAnalysis{}, errors.New("resume is required")
	}

	return s.backend.AnalyzeResume(ctx, request)
}

type whisperClient struct {
	endpoint string
	client   *http.Client
}

func newWhisperClient(rawURL string, client *http.Client) (*whisperClient, error) {
	endpoint, err := normalizeURL(rawURL)
	if err != nil {
		return nil, fmt.Errorf("invalid WHISPER_URL: %w", err)
	}

	return &whisperClient{
		endpoint: endpoint,
		client:   client,
	}, nil
}

func (c *whisperClient) Transcribe(ctx context.Context, audio InterviewReplyAudio) (Transcript, error) {
	filename := sanitizeAudioFilename(audio.Filename)
	contentType := strings.TrimSpace(audio.ContentType)
	if contentType == "" {
		contentType = "audio/wav"
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)

	partHeader := textproto.MIMEHeader{}
	partHeader.Set(
		"Content-Disposition",
		fmt.Sprintf(`form-data; name="file"; filename="%s"`, filename),
	)
	partHeader.Set("Content-Type", contentType)

	part, err := writer.CreatePart(partHeader)
	if err != nil {
		return Transcript{}, fmt.Errorf("create file part: %w", err)
	}
	if _, err := part.Write(audio.Data); err != nil {
		return Transcript{}, fmt.Errorf("write audio payload: %w", err)
	}
	if err := writer.WriteField("response_format", "verbose_json"); err != nil {
		return Transcript{}, fmt.Errorf("write response format: %w", err)
	}
	if err := writer.Close(); err != nil {
		return Transcript{}, fmt.Errorf("close multipart payload: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, &body)
	if err != nil {
		return Transcript{}, fmt.Errorf("build whisper request: %w", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Accept", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return Transcript{}, fmt.Errorf("request whisper service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return Transcript{}, readHTTPError("whisper service", resp)
	}

	var transcript Transcript
	if err := json.NewDecoder(resp.Body).Decode(&transcript); err != nil {
		return Transcript{}, fmt.Errorf("decode whisper response: %w", err)
	}

	transcript.Text = strings.TrimSpace(transcript.Text)
	return transcript, nil
}

func normalizeURL(rawURL string) (string, error) {
	trimmed := strings.TrimSpace(rawURL)
	if trimmed == "" {
		return "", errors.New("value is required")
	}

	parsed, err := url.Parse(trimmed)
	if err != nil {
		return "", err
	}
	if parsed.Scheme == "" || parsed.Host == "" {
		return "", errors.New("absolute URL is required")
	}

	return parsed.String(), nil
}

func resolveEndpoint(baseURL, endpointPath string) (string, error) {
	base, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}
	ref, err := url.Parse(endpointPath)
	if err != nil {
		return "", err
	}
	return base.ResolveReference(ref).String(), nil
}

func readHTTPError(service string, response *http.Response) error {
	message, err := io.ReadAll(io.LimitReader(response.Body, 2048))
	if err != nil {
		return fmt.Errorf("%s returned %s", service, response.Status)
	}

	trimmed := strings.TrimSpace(string(message))
	if trimmed == "" {
		return fmt.Errorf("%s returned %s", service, response.Status)
	}
	return fmt.Errorf("%s returned %s: %s", service, response.Status, trimmed)
}

func sanitizeAudioFilename(filename string) string {
	trimmed := strings.TrimSpace(filename)
	if trimmed == "" {
		return defaultInterviewAudioFilename
	}

	trimmed = strings.ReplaceAll(trimmed, `"`, "")
	if trimmed == "" {
		return defaultInterviewAudioFilename
	}

	return trimmed
}
