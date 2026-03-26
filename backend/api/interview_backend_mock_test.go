package api

import (
	"context"
	"testing"
)

func TestMockInterviewBackendAnalyzeResumeFlagsRiskAndStrength(t *testing.T) {
	t.Parallel()

	backend := mockInterviewBackend{}

	result, err := backend.AnalyzeResume(context.Background(), ResumeAnalysisRequest{
		Job: "backend",
		Resume: `
负责支付系统重构，接口成功率提升到 99.98%。

精通高并发系统设计，主导核心链路压测。
`,
	})
	if err != nil {
		t.Fatalf("AnalyzeResume() error = %v", err)
	}

	if result.Job != "backend" {
		t.Fatalf("result.Job = %q, want %q", result.Job, "backend")
	}
	if len(result.Blocks) < 2 {
		t.Fatalf("len(result.Blocks) = %d, want at least 2", len(result.Blocks))
	}
	if result.Blocks[0].Label != "strength" {
		t.Fatalf("result.Blocks[0].Label = %q, want %q", result.Blocks[0].Label, "strength")
	}
	if result.Blocks[1].Label != "risk" {
		t.Fatalf("result.Blocks[1].Label = %q, want %q", result.Blocks[1].Label, "risk")
	}
	if result.Blocks[1].Callout == nil {
		t.Fatal("risk block callout is nil")
	}
}
