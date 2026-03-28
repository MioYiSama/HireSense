package api

import (
	"bytes"
	"context"
	"errors"
	"strings"

	edge_tts "github.com/bytectlgo/edge-tts/pkg/edge_tts"
)

const defaultInterviewTTSVoice = "zh-CN-YunyangNeural"

var ErrInterviewTTSTextRequired = errors.New("interview tts text is required")

type interviewTTSSynthesizer interface {
	Synthesize(ctx context.Context, text string) ([]byte, error)
}

type InterviewTTSService struct {
	voice string
}

func NewInterviewTTSService() *InterviewTTSService {
	return &InterviewTTSService{
		voice: defaultInterviewTTSVoice,
	}
}

func (s *InterviewTTSService) Synthesize(ctx context.Context, text string) ([]byte, error) {
	trimmedText := strings.TrimSpace(text)
	if trimmedText == "" {
		return nil, ErrInterviewTTSTextRequired
	}

	stream, err := edge_tts.NewCommunicate(trimmedText, s.voice).Stream(ctx)
	if err != nil {
		return nil, &InterviewUpstreamError{
			Service: "tts",
			Err:     err,
		}
	}

	var audio bytes.Buffer
	audioReceived := false

	for chunk := range stream {
		switch chunk.Type {
		case "error":
			message := strings.TrimSpace(string(chunk.Data))
			if message == "" {
				message = "unknown tts stream error"
			}

			return nil, &InterviewUpstreamError{
				Service: "tts",
				Err:     errors.New(message),
			}
		case "audio":
			if len(chunk.Data) == 0 {
				continue
			}

			audioReceived = true
			_, _ = audio.Write(chunk.Data)
		}
	}

	if !audioReceived {
		return nil, &InterviewUpstreamError{
			Service: "tts",
			Err:     errors.New("no audio received"),
		}
	}

	return audio.Bytes(), nil
}
