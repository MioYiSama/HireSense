<script setup lang="ts">
import type { IDisposable, editor as MonacoEditor } from "monaco-editor";
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import { getCodeLanguageLabel, type CodeLanguage } from "@/lib/codeEditor";
import { getMonaco, HIRE_SENSE_MONACO_THEME } from "@/lib/monaco";

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

let monaco: typeof import("monaco-editor") | null = null;
let editor: MonacoEditor.IStandaloneCodeEditor | null = null;
let contentListener: IDisposable | null = null;

const layoutEditor = () => {
  editor?.layout();
};

const focusEditor = () => {
  window.setTimeout(() => {
    editor?.focus();
  }, 0);
};

const syncEditorValue = (value: string) => {
  if (!editor || editor.getValue() === value) {
    return;
  }

  const selection = editor.getSelection();
  editor.setValue(value);

  if (selection) {
    editor.setSelection(selection);
  }
};

const syncEditorLanguage = (language: CodeLanguage) => {
  const model = editor?.getModel();

  if (!monaco || !model) {
    return;
  }

  monaco.editor.setModelLanguage(model, language);
};

const createEditor = async () => {
  await nextTick();

  if (!editorContainer.value || editor) {
    return;
  }

  monaco = await getMonaco();

  const model = monaco.editor.createModel(props.code, props.language);
  editor = monaco.editor.create(editorContainer.value, {
    model,
    theme: HIRE_SENSE_MONACO_THEME,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: false,
    fontSize: 14,
    tabSize: 2,
    insertSpaces: true,
    wordWrap: "off",
    roundedSelection: false,
    padding: { top: 16, bottom: 16 },
    lineNumbersMinChars: 3,
    overviewRulerBorder: false,
    fixedOverflowWidgets: true,
    renderLineHighlight: "gutter",
  });

  contentListener = editor.onDidChangeModelContent(() => {
    emit("update:code", editor?.getValue() ?? "");
  });

  window.addEventListener("resize", layoutEditor);
  layoutEditor();
  focusEditor();
};

const disposeEditor = () => {
  window.removeEventListener("resize", layoutEditor);
  contentListener?.dispose();
  contentListener = null;

  const model = editor?.getModel();
  if (model) {
    model.dispose();
  }

  editor?.dispose();
  editor = null;
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
  () => props.code,
  (value) => {
    syncEditorValue(value);
  },
);

watch(
  () => props.language,
  (value) => {
    syncEditorLanguage(value);
  },
);

watch(
  () => props.show,
  async (show) => {
    if (!show) {
      return;
    }

    await createEditor();
    await nextTick();
    layoutEditor();
    focusEditor();
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
            可直接发送。
          </p>
        </div>

        <div class="flex items-center gap-3">
          <div
            class="inline-flex items-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-sm font-medium text-cyan-100"
          >
            {{ getCodeLanguageLabel(language) }}
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
