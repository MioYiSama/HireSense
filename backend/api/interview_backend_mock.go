//go:build !interview_ai

package api

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"unicode/utf8"
)

type mockInterviewBackend struct{}

func newInterviewConversationBackend(InterviewServiceConfig, *http.Client) (interviewConversationBackend, error) {
	return mockInterviewBackend{}, nil
}

func (mockInterviewBackend) Start(context.Context, InterviewSession) (InterviewStartResult, error) {
	return InterviewStartResult{
		Reply: "先做一个简短的自我介绍，并结合最近一段项目经历说明你承担的核心职责。",
	}, nil
}

func (mockInterviewBackend) Reply(_ context.Context, payload interviewReplyPayload) (InterviewReplyResult, error) {
	text := strings.TrimSpace(payload.Text)
	if text == "" {
		return InterviewReplyResult{}, ErrInterviewTextRequired
	}

	ending := shouldEndMockInterview(text)
	if ending {
		return InterviewReplyResult{
			Reply:  "好的，这轮面试先到这里。我会基于你刚才的回答整理整体反馈与改进建议。",
			Ending: true,
		}, nil
	}

	prefix := "我收到了你的回答"
	if payload.Transcript != nil {
		prefix = "我已经完成语音转写，并收到了你的回答"
	}

	return InterviewReplyResult{
		Reply: fmt.Sprintf(
			"%s：%s。接下来请你聚焦一个最关键的实现细节，继续说明你的设计取舍和可能的风险点。",
			prefix,
			summarizeMockReply(text, 72),
		),
		Ending: false,
	}, nil
}

func (mockInterviewBackend) Stop(context.Context, string) error {
	return nil
}

func shouldEndMockInterview(text string) bool {
	normalized := strings.ToLower(text)
	keywords := []string{
		"结束",
		"没有了",
		"以上",
		"谢谢",
		"that's all",
		"no more",
	}

	for _, keyword := range keywords {
		if strings.Contains(normalized, strings.ToLower(keyword)) {
			return true
		}
	}
	return false
}

func summarizeMockReply(text string, limit int) string {
	trimmed := strings.TrimSpace(text)
	if utf8.RuneCountInString(trimmed) <= limit {
		return trimmed
	}

	runes := []rune(trimmed)
	return strings.TrimSpace(string(runes[:limit])) + "..."
}
