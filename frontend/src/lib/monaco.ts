import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import cssWorker from "monaco-editor/esm/vs/language/css/css.worker?worker";
import htmlWorker from "monaco-editor/esm/vs/language/html/html.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";

type MonacoModule = typeof import("monaco-editor");

type MonacoEnvironmentShape = {
  getWorker: (_workerId: string, label: string) => Worker;
};

const monacoGlobal = globalThis as typeof globalThis & {
  MonacoEnvironment?: MonacoEnvironmentShape;
};

export const HIRE_SENSE_MONACO_THEME = "hire-sense-dark";

let monacoPromise: Promise<MonacoModule> | null = null;

const getMonacoWorker = (_workerId: string, label: string) => {
  switch (label) {
    case "json":
      return new jsonWorker();
    case "css":
    case "scss":
    case "less":
      return new cssWorker();
    case "html":
    case "handlebars":
    case "razor":
      return new htmlWorker();
    case "typescript":
    case "javascript":
      return new tsWorker();
    default:
      return new editorWorker();
  }
};

export const getMonaco = async () => {
  if (!monacoPromise) {
    monacoPromise = import("monaco-editor").then((monaco) => {
      monacoGlobal.MonacoEnvironment = {
        getWorker: getMonacoWorker,
      };

      monaco.editor.defineTheme(HIRE_SENSE_MONACO_THEME, {
        base: "vs-dark",
        inherit: true,
        rules: [],
        colors: {
          "editor.background": "#060b16",
          "editor.foreground": "#d4def3",
          "editor.lineHighlightBackground": "#13203a",
          "editor.selectionBackground": "#264b8c66",
          "editor.inactiveSelectionBackground": "#1a335f55",
          "editorCursor.foreground": "#8dc2ff",
          "editorLineNumber.foreground": "#5e6a83",
          "editorLineNumber.activeForeground": "#d4def3",
        },
      });

      return monaco;
    });
  }

  return monacoPromise;
};
