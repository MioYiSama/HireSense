//go:build !interview_ai

package api

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"
	"unicode/utf8"

	"hire_sense/database"
)

type mockInterviewBackend struct{}

func newInterviewConversationBackend(InterviewServiceConfig, *http.Client) (interviewConversationBackend, error) {
	return mockInterviewBackend{}, nil
}

func (mockInterviewBackend) Start(_ context.Context, session InterviewSession) (InterviewStartResult, error) {
	mode := session.Mode
	speakerRole := "ai"
	reply := "先做一个简短的自我介绍，并结合最近一段项目经历说明你承担的核心职责。"
	if mode == string(database.InterviewModePanelTrio) {
		speakerRole = "hr"
		reply = "我是本轮群面的 HR。先做个简短自我介绍，再说说你最近一段经历里最值得拿出来讲的项目。"
	}

	return InterviewStartResult{
		Reply:       reply,
		Mode:        mode,
		SpeakerRole: speakerRole,
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
			Reply:       "好的，这轮面试先到这里。我会基于你刚才的回答整理整体反馈与改进建议。",
			Ending:      true,
			Mode:        string(database.InterviewModeSingle),
			SpeakerRole: "ai",
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
		Ending:      false,
		Mode:        string(database.InterviewModeSingle),
		SpeakerRole: "ai",
	}, nil
}

func (mockInterviewBackend) Stop(context.Context, string) error {
	return nil
}

func (mockInterviewBackend) AnalyzeResume(
	_ context.Context,
	request ResumeAnalysisRequest,
) (database.ResumeAnalysis, error) {
	blocksText := splitMockResumeBlocks(request.Resume)
	blocks := make([]database.ResumeAnalysisBlock, 0, len(blocksText))
	strengthCount := 0
	probeCount := 0
	riskCount := 0

	for index, blockText := range blocksText {
		block := database.ResumeAnalysisBlock{
			ID:    fmt.Sprintf("block-%d", index+1),
			Text:  blockText,
			Label: database.ResumeAnalysisLabelNeutral,
		}

		switch {
		case containsAnyFold(blockText, "精通", "高并发", "架构师", "业内领先", "全栈专家", "性能极致"):
			block.Label = database.ResumeAnalysisLabelRisk
			block.Reason = "结论下得过满，但缺少指标、规模或具体边界。"
			block.HighlightPhrases = buildMockHighlights(
				blockText,
				database.ResumeAnalysisLabelRisk,
				"这类词如果没有证据支撑，面试官通常会直接追规模、压测和故障案例。",
				"精通", "高并发", "架构师", "业内领先", "全栈专家", "性能极致",
			)
			block.Callout = &database.ResumeAnalysisCallout{
				Title: "高危吹牛词",
				Body:  "⚠️ 此处措辞过满，系统已锁定为高危吹牛词。下一轮很可能被追问规模、瓶颈、压测结果和翻车案例。",
			}
			riskCount++
		case containsAnyFold(blockText, "参与", "协助", "熟悉", "了解", "接触", "配合"):
			block.Label = database.ResumeAnalysisLabelProbe
			block.Reason = "这里有经验痕迹，但贡献边界和个人 ownership 还不够清楚。"
			block.HighlightPhrases = buildMockHighlights(
				blockText,
				database.ResumeAnalysisLabelProbe,
				"建议补上你亲自负责的决策、指标和结果。",
				"参与", "协助", "熟悉", "了解", "接触", "配合",
			)
			probeCount++
		case containsAnyFold(blockText, "主导", "负责", "设计", "优化", "上线", "落地", "提升", "搭建", "实现"):
			block.Label = database.ResumeAnalysisLabelStrength
			block.Reason = "这段包含明确动作和结果，适合作为面试中的亮点展开。"
			block.HighlightPhrases = buildMockHighlights(
				blockText,
				database.ResumeAnalysisLabelStrength,
				"这类动作词能支撑你的真实贡献。",
				"主导", "负责", "设计", "优化", "上线", "落地", "提升", "搭建", "实现",
			)
			strengthCount++
		}

		blocks = append(blocks, block)
	}

	return database.ResumeAnalysis{
		Version:     "v1",
		Job:         database.UserJob(strings.TrimSpace(request.Job)),
		GeneratedAt: time.Now().UTC(),
		Summary: fmt.Sprintf(
			"共识别 %d 处亮点、%d 处可深挖段落、%d 处高风险措辞。",
			strengthCount,
			probeCount,
			riskCount,
		),
		OverallTone: "mock",
		Blocks:      blocks,
	}, nil
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

func splitMockResumeBlocks(text string) []string {
	normalized := strings.ReplaceAll(text, "\r\n", "\n")
	lines := strings.Split(normalized, "\n")
	blocks := make([]string, 0)
	current := make([]string, 0)

	flush := func() {
		if len(current) == 0 {
			return
		}

		block := strings.TrimSpace(strings.Join(current, "\n"))
		if block != "" {
			blocks = append(blocks, block)
		}
		current = current[:0]
	}

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			flush()
			continue
		}

		if isResumeBulletLine(trimmed) && len(current) > 0 {
			flush()
		}
		current = append(current, trimmed)
	}

	flush()
	if len(blocks) == 0 {
		return []string{strings.TrimSpace(text)}
	}

	return blocks
}

func isResumeBulletLine(line string) bool {
	for _, prefix := range []string{"- ", "* ", "• ", "1.", "2.", "3.", "4.", "5."} {
		if strings.HasPrefix(line, prefix) {
			return true
		}
	}

	return false
}

func containsAnyFold(text string, keywords ...string) bool {
	lowerText := strings.ToLower(text)
	for _, keyword := range keywords {
		if strings.Contains(lowerText, strings.ToLower(keyword)) {
			return true
		}
	}

	return false
}

func buildMockHighlights(
	text string,
	label database.ResumeAnalysisLabel,
	comment string,
	keywords ...string,
) []database.ResumeAnalysisHighlightPhrase {
	highlights := make([]database.ResumeAnalysisHighlightPhrase, 0, 2)
	for _, keyword := range keywords {
		if !strings.Contains(strings.ToLower(text), strings.ToLower(keyword)) {
			continue
		}

		highlights = append(highlights, database.ResumeAnalysisHighlightPhrase{
			Text:    keyword,
			Label:   label,
			Comment: comment,
		})
		if len(highlights) >= 2 {
			break
		}
	}

	return highlights
}
