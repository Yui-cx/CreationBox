import { useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut, Moon, Sun } from "lucide-react";
import { AdminPage } from "../admin/AdminPage";
import { CreationWorkspace } from "../creation/CreationWorkspace";
import { HistoryPage } from "../history/HistoryPage";
import { ImageWatermarkPage } from "../image-watermark/ImageWatermarkPage";
import { AppNavigation, MobileNavigation } from "../../components/AppNavigation";
import { exportMarkdown, fetchMe, streamGeneration } from "../../lib/api";
import { downloadText } from "../../lib/download";
import { tools } from "../../lib/tools";
import { useAuthStore } from "../../store/auth";
import type { GenerationListItem, GenerationPayload, ToolType } from "../../types";

export function Workspace() {
  const queryClient = useQueryClient();
  const { logout } = useAuthStore();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });
  const [theme, setTheme] = useState<"light" | "dark">(() => (localStorage.getItem("creationbox-theme") as "light" | "dark") || "light");
  const [activeView, setActiveView] = useState<"creation" | "history" | "imageWatermark" | "admin">("creation");
  const [toolId, setToolId] = useState<ToolType>("humanize");
  const tool = tools[toolId];
  const [mode, setMode] = useState(tool.modes[0].id);
  const [inputText, setInputText] = useState("");
  const [isInputEditing, setIsInputEditing] = useState(false);
  const [inputUrl, setInputUrl] = useState("");
  const [topic, setTopic] = useState("");
  const [materials, setMaterials] = useState("");
  const [style, setStyle] = useState(tool.styles[0]);
  const [tone, setTone] = useState(tool.tones[0]);
  const [customStyle, setCustomStyle] = useState("");
  const [customTone, setCustomTone] = useState("");
  const [preserveFormat, setPreserveFormat] = useState(true);
  const [status, setStatus] = useState("结果为真实后端生成，当前无模型密钥时会使用本地 mock provider。");
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState("");
  const [generationId, setGenerationId] = useState<string | null>(null);
  const inputTextAreaRef = useRef<HTMLTextAreaElement | null>(null);

  document.documentElement.dataset.theme = theme;
  localStorage.setItem("creationbox-theme", theme);

  const activeMode = useMemo(() => tool.modes.find((item) => item.id === mode) ?? tool.modes[0], [mode, tool.modes]);
  const charCount = inputText.trim().length;
  const showLink = mode === "link";
  const showTopic = toolId === "generate" && mode === "topic";
  const showText = toolId === "humanize" || toolId === "aigc_reduce";
  const showMaterials = toolId === "generate" && mode === "topic";
  const showConfig = toolId === "generate";
  const showFormatOption = toolId === "humanize" || toolId === "aigc_reduce";
  const showRichResult = showFormatOption || toolId === "generate";
  const effectiveStyle = style === "自定义" ? customStyle.trim() : style;
  const effectiveTone = tone === "自定义" ? customTone.trim() : tone;
  const quotaLabel = me ? (me.quota_total < 0 ? "无限" : `${me.quota_remaining} / ${me.quota_total}`) : "--";

  function switchTool(next: ToolType) {
    const nextTool = tools[next];
    setActiveView("creation");
    setToolId(next);
    setMode(nextTool.modes[0].id);
    setStyle(nextTool.styles[0]);
    setTone(nextTool.tones[0]);
    setCustomStyle("");
    setCustomTone("");
    setResult("");
    setGenerationId(null);
    setError("");
  }

  function validate() {
    if (toolId === "humanize" && !inputText.trim()) return "请输入需要优化的文本。";
    if (toolId === "humanize" && activeMode.limit && charCount > activeMode.limit) return `${activeMode.label}最多支持 ${activeMode.limit} 字。`;
    if (toolId === "aigc_reduce" && !inputText.trim()) return "请输入需要处理的文本。";
    if (toolId === "aigc_reduce" && activeMode.limit && charCount > activeMode.limit) return `输入文本最多支持 ${activeMode.limit} 字。`;
    const hasReferenceLinks = inputUrl.split(/[\n,，;；]+/).some((item) => item.trim());
    if (showLink && !hasReferenceLinks) return "请填写至少一个参考链接。";
    if (showTopic && !topic.trim()) return "请填写文章主题。";
    if (toolId === "generate" && style === "自定义" && !customStyle.trim()) return "请输入自定义内容类型。";
    if (toolId === "generate" && tone === "自定义" && !customTone.trim()) return "请输入自定义文章语气。";
    return "";
  }

  async function startGeneration() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setResult("");
    setGenerationId(null);
    setIsGenerating(true);
    setStatus("正在连接生成流...");
    const payload: GenerationPayload = {
      tool_type: toolId,
      mode,
      input_text: inputText || undefined,
      input_url: inputUrl || undefined,
      topic: topic || undefined,
      materials: materials || undefined,
      config: { style: effectiveStyle, tone: effectiveTone, preserve_format: preserveFormat ? "true" : "false" }
    };
    try {
      await streamGeneration(payload, {
        onMetadata: (data) => {
          setGenerationId(String(data.generation_id));
          setStatus(data.quota_remaining === -1 ? "生成中，当前账号不限次数。" : `生成中，今日剩余 ${data.quota_remaining} 次。`);
          queryClient.invalidateQueries({ queryKey: ["me"] });
        },
        onDelta: (text) => setResult((current) => current + text),
        onDone: (id) => {
          setGenerationId(id);
          setStatus("已生成并保存到历史记录。");
          queryClient.invalidateQueries({ queryKey: ["history"] });
          queryClient.invalidateQueries({ queryKey: ["me"] });
        },
        onError: (message) => {
          setError(message);
          setStatus("生成失败，请调整输入后重试。");
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setStatus("结果已复制。");
  }

  async function exportCurrentMarkdown() {
    if (generationId) {
      const markdown = await exportMarkdown(generationId);
      downloadText(`CreationBox-${generationId}.md`, markdown);
      return;
    }
    downloadText("CreationBox-result.md", result);
  }

  function clearInputs() {
    setInputText("");
    setInputUrl("");
    setTopic("");
    setMaterials("");
    setCustomStyle("");
    setCustomTone("");
    setResult("");
    setGenerationId(null);
    setError("");
    setStatus("输入已清空。");
  }

  function loadHistoryItem(item: GenerationListItem) {
    setActiveView("creation");
    setToolId(item.tool_type);
    setMode(item.mode);
    setResult(item.output_content);
    setGenerationId(item.id);
    setStatus("已载入历史记录。");
  }

  return (
    <div className="app-shell">
      <AppNavigation activeView={activeView} toolId={toolId} me={me} quotaLabel={quotaLabel} onViewChange={setActiveView} onToolChange={switchTool} />

      <main className="main">
        <header className="topbar">
          <div>
            <h1>AI 文本工作台</h1>
            <p>围绕自然表达和文章生成，完成从素材到草稿的工作流。</p>
          </div>
          <div className="top-actions">
            <button className="secondary-button" type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
              {theme === "dark" ? "浅色模式" : "深色模式"}
            </button>
            <button className="secondary-button" type="button" onClick={logout}>
              <LogOut size={18} aria-hidden="true" />
              退出
            </button>
          </div>
        </header>

        <MobileNavigation activeView={activeView} toolId={toolId} me={me} onViewChange={setActiveView} onToolChange={switchTool} />

        <section className="workspace">
          {activeView === "history" ? (
            <HistoryPage onLoad={loadHistoryItem} />
          ) : activeView === "imageWatermark" ? (
            <ImageWatermarkPage />
          ) : activeView === "admin" ? (
            <AdminPage isAdmin={Boolean(me?.is_admin)} />
          ) : (
            <CreationWorkspace
              tool={tool}
              toolId={toolId}
              mode={mode}
              setMode={setMode}
              inputText={inputText}
              setInputText={setInputText}
              isInputEditing={isInputEditing}
              setIsInputEditing={setIsInputEditing}
              inputTextAreaRef={inputTextAreaRef}
              inputUrl={inputUrl}
              setInputUrl={setInputUrl}
              topic={topic}
              setTopic={setTopic}
              materials={materials}
              setMaterials={setMaterials}
              style={style}
              setStyle={setStyle}
              tone={tone}
              setTone={setTone}
              customStyle={customStyle}
              setCustomStyle={setCustomStyle}
              customTone={customTone}
              setCustomTone={setCustomTone}
              preserveFormat={preserveFormat}
              setPreserveFormat={setPreserveFormat}
              status={status}
              setStatus={setStatus}
              error={error}
              setError={setError}
              isGenerating={isGenerating}
              result={result}
              generationId={generationId}
              startGeneration={startGeneration}
              clearInputs={clearInputs}
              copyResult={copyResult}
              exportCurrentMarkdown={exportCurrentMarkdown}
            />          )}
        </section>
      </main>
    </div>
  );
}
