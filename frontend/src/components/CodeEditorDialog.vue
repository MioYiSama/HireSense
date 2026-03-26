<script setup lang="ts">
import type { Extension } from "@codemirror/state";
import type { EditorView } from "@codemirror/view";
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import { getCodeLanguageLabel, type CodeLanguage } from "@/lib/codeEditor";

interface Props {
  show?: boolean;
  code?: string;
  language?: CodeLanguage;
  isSubmitting?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  code: "",
  language: "javascript",
  isSubmitting: false,
});

const emit = defineEmits<{
  "update:code": [value: string];
  close: [];
  submit: [];
}>();

const editorContainer = ref<HTMLDivElement | null>(null);
const lineCount = ref(Math.max(1, props.code.split("\n").length));

let editorView: EditorView | null = null;
let codeEditorRuntime: CodeEditorRuntime | null = null;
let languageCompartment: InstanceType<CodeEditorRuntime["Compartment"]> | null = null;

type CodeEditorRuntime = {
  Compartment: typeof import("@codemirror/state").Compartment;
  EditorSelection: typeof import("@codemirror/state").EditorSelection;
  EditorState: typeof import("@codemirror/state").EditorState;
  oneDark: typeof import("@codemirror/theme-one-dark").oneDark;
  EditorView: typeof import("@codemirror/view").EditorView;
  highlightActiveLine: typeof import("@codemirror/view").highlightActiveLine;
  keymap: typeof import("@codemirror/view").keymap;
  lineNumbers: typeof import("@codemirror/view").lineNumbers;
  placeholder: typeof import("@codemirror/view").placeholder;
  minimalSetup: typeof import("codemirror").minimalSetup;
  indentWithTab: typeof import("@codemirror/commands").indentWithTab;
};

let codeEditorRuntimePromise: Promise<CodeEditorRuntime> | null = null;
let languageExtensionPromises: Partial<Record<CodeLanguage, Promise<Extension>>> = {};

const loadCodeEditorRuntime = async () => {
  if (!codeEditorRuntimePromise) {
    codeEditorRuntimePromise = Promise.all([
      import("@codemirror/commands"),
      import("@codemirror/state"),
      import("@codemirror/theme-one-dark"),
      import("@codemirror/view"),
      import("codemirror"),
    ]).then(([commandsModule, stateModule, themeModule, viewModule, codemirrorModule]) => {
      return {
        Compartment: stateModule.Compartment,
        EditorSelection: stateModule.EditorSelection,
        EditorState: stateModule.EditorState,
        oneDark: themeModule.oneDark,
        EditorView: viewModule.EditorView,
        highlightActiveLine: viewModule.highlightActiveLine,
        keymap: viewModule.keymap,
        lineNumbers: viewModule.lineNumbers,
        placeholder: viewModule.placeholder,
        minimalSetup: codemirrorModule.minimalSetup,
        indentWithTab: commandsModule.indentWithTab,
      };
    });
  }

  return codeEditorRuntimePromise;
};

const loadLanguageExtension = async (language: CodeLanguage) => {
  if (!languageExtensionPromises[language]) {
    languageExtensionPromises[language] =
      language === "java"
        ? import("@codemirror/lang-java").then(({ java }) => java())
        : import("@codemirror/lang-javascript").then(({ javascript }) => javascript());
  }

  return languageExtensionPromises[language];
};

const createEditorTheme = (EditorViewCtor: CodeEditorRuntime["EditorView"]) => {
  return EditorViewCtor.theme(
    {
      "&": {
        height: "55vh",
        minHeight: "360px",
        backgroundColor: "#060b16",
        color: "#d4def3",
        fontSize: "13px",
        lineHeight: "1.6",
      },
      ".cm-scroller": {
        overflow: "auto",
        fontFamily:
          "ui-monospace, SFMono-Regular, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      },
      ".cm-content": {
        padding: "16px 0",
        caretColor: "#8dc2ff",
      },
      ".cm-line": {
        padding: "0 20px",
      },
      ".cm-gutters": {
        minHeight: "100%",
        border: "none",
        backgroundColor: "#0b1220",
        color: "#5e6a83",
        padding: "0",
        fontSize: "13px",
      },
      ".cm-lineNumbers .cm-gutterElement": {
        padding: "0 6px 0 8px",
        minWidth: "28px",
      },
      ".cm-activeLine": {
        backgroundColor: "#13203a",
      },
      ".cm-activeLineGutter": {
        backgroundColor: "transparent",
        color: "#d4def3",
      },
      ".cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection": {
        backgroundColor: "#264b8c66",
      },
      ".cm-cursor, .cm-dropCursor": {
        borderLeftColor: "#8dc2ff",
      },
      ".cm-placeholder": {
        color: "#64748b",
        paddingLeft: "20px",
      },
      ".cm-focused": {
        outline: "none",
      },
    },
    { dark: true },
  );
};

const createEditorAttributes = (EditorViewCtor: CodeEditorRuntime["EditorView"]) => {
  return EditorViewCtor.contentAttributes.of({
    spellcheck: "false",
    autocorrect: "off",
    autocapitalize: "off",
  });
};

const updateLineCount = (value: string) => {
  lineCount.value = Math.max(1, value.split("\n").length);
};

const focusEditor = () => {
  window.setTimeout(() => {
    editorView?.focus();
  }, 0);
};

const syncEditorValue = (value: string) => {
  updateLineCount(value);

  if (!editorView || !codeEditorRuntime) {
    return;
  }

  const currentValue = editorView.state.doc.toString();

  if (currentValue === value) {
    return;
  }

  const cursor = Math.min(editorView.state.selection.main.head, value.length);

  editorView.dispatch({
    changes: {
      from: 0,
      to: currentValue.length,
      insert: value,
    },
    selection: codeEditorRuntime.EditorSelection.cursor(cursor),
  });
};

const syncEditorLanguage = async (language: CodeLanguage) => {
  if (!editorView || !languageCompartment) {
    return;
  }

  const languageExtension = await loadLanguageExtension(language);

  editorView.dispatch({
    effects: languageCompartment.reconfigure(languageExtension),
  });
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === "Escape" && !props.isSubmitting) {
    emit("close");
    return;
  }

  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();

    if (!props.isSubmitting && props.code.trim()) {
      emit("submit");
    }
  }
};

const createEditor = async () => {
  await nextTick();

  if (!editorContainer.value || editorView) {
    return;
  }

  codeEditorRuntime = await loadCodeEditorRuntime();
  languageCompartment = new codeEditorRuntime.Compartment();
  const languageExtension = await loadLanguageExtension(props.language);

  editorView = new codeEditorRuntime.EditorView({
    state: codeEditorRuntime.EditorState.create({
      doc: props.code,
      extensions: [
        codeEditorRuntime.minimalSetup,
        codeEditorRuntime.lineNumbers(),
        codeEditorRuntime.highlightActiveLine(),
        codeEditorRuntime.keymap.of([codeEditorRuntime.indentWithTab]),
        codeEditorRuntime.oneDark,
        createEditorTheme(codeEditorRuntime.EditorView),
        createEditorAttributes(codeEditorRuntime.EditorView),
        // codeEditorRuntime.placeholder("// 在这里输入代码"),
        languageCompartment.of(languageExtension),
        codeEditorRuntime.EditorView.updateListener.of((update) => {
          if (!update.docChanged) {
            return;
          }

          lineCount.value = update.state.doc.lines;
          emit("update:code", update.state.doc.toString());
        }),
      ],
    }),
    parent: editorContainer.value,
  });

  lineCount.value = editorView.state.doc.lines;
  focusEditor();
};

const disposeEditor = () => {
  editorView?.destroy();
  editorView = null;
  languageCompartment = null;
};

const handleClose = () => {
  if (props.isSubmitting) {
    return;
  }

  emit("close");
};

const handleSubmit = () => {
  if (!props.code.trim() || props.isSubmitting) {
    return;
  }

  emit("submit");
};

watch(
  () => props.show,
  async (show) => {
    if (!show) {
      return;
    }

    await createEditor();
    await nextTick();
    focusEditor();
  },
);

watch(
  () => props.code,
  (value) => {
    syncEditorValue(value);
  },
);

watch(
  () => props.language,
  (value) => {
    void syncEditorLanguage(value);
  },
);

onMounted(() => {
  void createEditor();
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
  disposeEditor();
});
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="handleClose"></div>

    <div
      class="relative w-full max-w-5xl rounded-3xl border border-gray-700/50 bg-gray-900/95 p-5 shadow-2xl shadow-black/40"
    >
      <div class="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 class="text-xl font-semibold text-white">代码编辑器</h3>
          <p class="mt-1 text-sm text-gray-400">
            代码会按文本原样发送到后端。按
            <span class="rounded-md border border-gray-600/80 bg-gray-800/80 px-1.5 py-0.5 text-xs">
              Ctrl / Cmd + Enter
            </span>
            可直接发送，支持
            <span class="rounded-md border border-gray-600/80 bg-gray-800/80 px-1.5 py-0.5 text-xs">
              Tab
            </span>
            缩进。
          </p>
        </div>

        <div class="flex items-center gap-3">
          <div
            class="inline-flex items-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-sm font-medium text-cyan-100"
          >
            {{ getCodeLanguageLabel(language) }}
          </div>
          <div
            class="hidden rounded-xl border border-gray-700/80 bg-gray-800/80 px-3 py-2 text-sm text-gray-300 sm:block"
          >
            {{ lineCount }} 行
          </div>

          <button
            class="rounded-xl border border-gray-700/80 bg-gray-800/90 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:border-gray-600 hover:bg-gray-700/80 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSubmitting"
            @click="handleClose"
          >
            取消
          </button>
          <button
            class="rounded-xl bg-linear-to-r from-blue-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white transition-all hover:from-blue-600 hover:to-cyan-600 disabled:cursor-not-allowed disabled:from-gray-700 disabled:to-gray-700 disabled:text-gray-400"
            :disabled="!code.trim() || isSubmitting"
            @click="handleSubmit"
          >
            {{ isSubmitting ? "发送中..." : "发送代码" }}
          </button>
        </div>
      </div>

      <div class="overflow-hidden rounded-2xl border border-gray-700/60 bg-[#060b16] shadow-inner">
        <div ref="editorContainer" class="h-[55vh] min-h-[360px] w-full"></div>
      </div>
    </div>
  </div>
</template>
