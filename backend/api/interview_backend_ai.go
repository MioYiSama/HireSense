//go:build interview_ai

package api

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

type remoteInterviewBackend struct {
	baseURL string
	client  *http.Client
}

type aiInterviewStartRequest struct {
	ID              string `json:"id"`
	Job             string `json:"job"`
	Resume          string `json:"resume,omitempty"`
	Personalization string `json:"personalization,omitempty"`
}

type aiInterviewReplyRequest struct {
	ID    string `json:"id"`
	Input any    `json:"input"`
}

type aiInterviewReplyTextInput struct {
	Type    string `json:"type"`
	Content string `json:"content"`
}

type aiInterviewReplyTranscriptInput struct {
	Type    string     `json:"type"`
	Content Transcript `json:"content"`
}

type aiInterviewReplyResponse struct {
	Reply  string `json:"reply"`
	Ending bool   `json:"ending"`
}

type aiInterviewStopRequest struct {
	ID string `json:"id"`
}

func newInterviewConversationBackend(cfg InterviewServiceConfig, client *http.Client) (interviewConversationBackend, error) {
	baseURL, err := normalizeURL(cfg.AIURL)
	if err != nil {
		return nil, fmt.Errorf("invalid AI_URL: %w", err)
	}

	return &remoteInterviewBackend{
		baseURL: baseURL,
		client:  client,
	}, nil
}

func (b *remoteInterviewBackend) Start(ctx context.Context, session InterviewSession) error {
	request := aiInterviewStartRequest{
		ID:              session.ID,
		Job:             session.Job,
		Resume:          session.Resume,
		Personalization: session.Personalization,
	}

	if err := b.doJSON(ctx, http.MethodPost, "/api/interview/start", request, nil); err != nil {
		return &InterviewUpstreamError{
			Service: "ai",
			Err:     err,
		}
	}

	return nil
}

func (b *remoteInterviewBackend) Reply(ctx context.Context, payload interviewReplyPayload) (InterviewReplyResult, error) {
	request := aiInterviewReplyRequest{
		ID: payload.InterviewID,
	}
	if payload.Transcript != nil {
		request.Input = aiInterviewReplyTranscriptInput{
			Type:    "transcript",
			Content: *payload.Transcript,
		}
	} else {
		request.Input = aiInterviewReplyTextInput{
			Type:    "text",
			Content: payload.Text,
		}
	}

	var response aiInterviewReplyResponse
	if err := b.doJSON(ctx, http.MethodPost, "/api/interview/reply", request, &response); err != nil {
		return InterviewReplyResult{}, &InterviewUpstreamError{
			Service: "ai",
			Err:     err,
		}
	}

	if response.Reply == "" {
		return InterviewReplyResult{}, &InterviewUpstreamError{
			Service: "ai",
			Err:     fmt.Errorf("empty reply returned"),
		}
	}

	return InterviewReplyResult{
		Reply:  response.Reply,
		Ending: response.Ending,
	}, nil
}

func (b *remoteInterviewBackend) Stop(ctx context.Context, interviewID string) error {
	request := aiInterviewStopRequest{ID: interviewID}
	if err := b.doJSON(ctx, http.MethodPost, "/api/interview/stop", request, nil); err != nil {
		return &InterviewUpstreamError{
			Service: "ai",
			Err:     err,
		}
	}

	return nil
}

func (b *remoteInterviewBackend) doJSON(ctx context.Context, method, endpointPath string, payload any, out any) error {
	endpoint, err := resolveEndpoint(b.baseURL, endpointPath)
	if err != nil {
		return fmt.Errorf("resolve endpoint: %w", err)
	}

	var body bytes.Buffer
	if payload != nil {
		if err := json.NewEncoder(&body).Encode(payload); err != nil {
			return fmt.Errorf("encode request: %w", err)
		}
	}

	req, err := http.NewRequestWithContext(ctx, method, endpoint, &body)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := b.client.Do(req)
	if err != nil {
		return fmt.Errorf("request upstream service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return readHTTPError("ai service", resp)
	}

	if out == nil {
		return nil
	}

	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}

	return nil
}
