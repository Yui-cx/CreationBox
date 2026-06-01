export function formatElapsedTime(seconds: number) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

export function imageInpaintErrorMessage(message: string) {
  if (message === "LAMA_BUSY") return "智能修复任务正在处理中，请稍后重试。";
  if (message === "LAMA_UNAVAILABLE") return "智能修复暂不可用，请检查 LaMa 模型和依赖配置。";
  if (message === "IMAGE_TOO_LARGE") return "图片超过当前修复模式的大小限制。";
  if (message === "INVALID_MASK") return "标记区域无效，请重新涂抹或框选水印区域。";
  if (message === "UNSUPPORTED_IMAGE_TYPE") return "仅支持 PNG、JPEG、WebP 图片。";
  return message || "INPAINT_FAILED";
}

export function formatDateTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

