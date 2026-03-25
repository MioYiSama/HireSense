export const CODE_LANGUAGE_OPTIONS = [
  { value: "javascript", label: "JavaScript" },
  { value: "java", label: "Java" },
] as const;

export type CodeLanguage = (typeof CODE_LANGUAGE_OPTIONS)[number]["value"];

export type ProfileJob = "frontend" | "backend";

const CODE_LANGUAGE_LABELS = new Map<CodeLanguage, string>(
  CODE_LANGUAGE_OPTIONS.map((option) => [option.value, option.label]),
);

export const getCodeLanguageForJob = (job: string | undefined): CodeLanguage => {
  return job === "backend" ? "java" : "javascript";
};

export const getCodeLanguageLabel = (language: string | undefined) => {
  if (!language) {
    return CODE_LANGUAGE_LABELS.get("javascript") ?? "JavaScript";
  }

  return CODE_LANGUAGE_LABELS.get(language as CodeLanguage) ?? language;
};
