import mammoth from "mammoth";

export interface ParseResult {
  success: boolean;
  text: string;
  error?: string;
}

export async function parseFile(file: File): Promise<ParseResult> {
  const fileType = file.type;
  const fileName = file.name.toLowerCase();

  try {
    if (
      fileType ===
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
      fileName.endsWith(".docx")
    ) {
      return await parseWord(file);
    } else if (fileType === "text/plain" || fileName.endsWith(".txt")) {
      return await parseText(file);
    } else if (fileName.endsWith(".doc")) {
      return {
        success: false,
        text: "",
        error: "不支持旧版 Word 文档格式（.doc），请转换为 .docx 或 .txt 格式",
      };
    } else if (fileName.endsWith(".pdf")) {
      return {
        success: false,
        text: "",
        error: "PDF 格式暂时不支持，请上传 Word（.docx）或 TXT 文件",
      };
    } else {
      return {
        success: false,
        text: "",
        error: "不支持的文件格式，请上传 Word（.docx）或 TXT 文件",
      };
    }
  } catch (error) {
    console.error("文件解析错误:", error);
    return {
      success: false,
      text: "",
      error: "文件解析失败，请检查文件是否损坏",
    };
  }
}

async function parseWord(file: File): Promise<ParseResult> {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });

    if (result.messages.length > 0) {
      console.warn("Word 文件解析警告:", result.messages);
    }

    return {
      success: true,
      text: result.value.trim(),
    };
  } catch (error) {
    console.error("Word 文件解析错误:", error);
    return {
      success: false,
      text: "",
      error: "Word 文件解析失败",
    };
  }
}

async function parseText(file: File): Promise<ParseResult> {
  try {
    const text = await file.text();

    return {
      success: true,
      text: text.trim(),
    };
  } catch (error) {
    console.error("文本文件解析错误:", error);
    return {
      success: false,
      text: "",
      error: "文本文件解析失败",
    };
  }
}

export function getFileExtension(fileName: string): string {
  const parts = fileName.split(".");
  if (parts.length > 1) {
    const extension = parts[parts.length - 1];
    if (extension) {
      return extension.toLowerCase();
    }
  }
  return "";
}
