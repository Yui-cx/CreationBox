import type { Ref, RefObject } from "react";
import { Copy, Download, Eraser, FileText, RefreshCw, Sparkles, Upload, WandSparkles } from "lucide-react";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";
import type { ToolConfig, ToolType } from "../../types";

type CreationWorkspaceProps = {
  tool: ToolConfig;
  toolId: ToolType;
  mode: string;
  setMode: (value: string) => void;
  inputText: string;
  setInputText: (value: string) => void;
  isInputEditing: boolean;
  setIsInputEditing: (value: boolean) => void;
  inputTextAreaRef: RefObject<HTMLTextAreaElement | null>;
  inputUrl: string;
  setInputUrl: (value: string) => void;
  topic: string;
  setTopic: (value: string) => void;
  materials: string;
  setMaterials: (value: string) => void;
  style: string;
  setStyle: (value: string) => void;
  tone: string;
  setTone: (value: string) => void;
  customStyle: string;
  setCustomStyle: (value: string) => void;
  customTone: string;
  setCustomTone: (value: string) => void;
  preserveFormat: boolean;
  setPreserveFormat: (value: boolean) => void;
  status: string;
  error: string;
  isGenerating: boolean;
  result: string;
  generationId: string | null;
  startGeneration: () => Promise<void>;
  clearInputs: () => void;
  copyResult: () => Promise<void>;
  exportCurrentMarkdown: () => Promise<void>;
};

export function CreationWorkspace({
  tool,
  toolId,
  mode,
  setMode,
  inputText,
  setInputText,
  isInputEditing,
  setIsInputEditing,
  inputTextAreaRef,
  inputUrl,
  setInputUrl,
  topic,
  setTopic,
  materials,
  setMaterials,
  style,
  setStyle,
  tone,
  setTone,
  customStyle,
  setCustomStyle,
  customTone,
  setCustomTone,
  preserveFormat,
  setPreserveFormat,
  status,
  error,
  isGenerating,
  result,
  generationId,
  startGeneration,
  clearInputs,
  copyResult,
  exportCurrentMarkdown,
}: CreationWorkspaceProps) {
  const activeMode = tool.modes.find((item) => item.id === mode) ?? tool.modes[0];
  const charCount = inputText.trim().length;
  const showLink = mode === "link";
  const showTopic = toolId === "generate" && mode === "topic";
  const showText = toolId === "humanize" || toolId === "aigc_reduce";
  const showMaterials = toolId === "generate" && mode === "topic";
  const showConfig = toolId === "generate";
  const showFormatOption = toolId === "humanize" || toolId === "aigc_reduce";
  const showRichResult = showFormatOption || toolId === "generate";

  return (
    <>
      <div className="tool-header">
        <span className="tool-kicker"><Sparkles size={16} aria-hidden="true" />{tool.kicker}</span>
        <h2>{tool.title}</h2>
        <p>{tool.description}</p>
      </div>

      <div className="work-grid">
        <section className="panel input-panel" aria-labelledby="input-title">
          <div className="panel-heading">
            <div>
              <h2 id="input-title">输入内容</h2>
              <p>{tool.sourceHelper}</p>
            </div>
          </div>
          {tool.modes.length > 1 && (
            <div className="mode-tabs" role="tablist" aria-label="输入模式">
              {tool.modes.map((item) => (
                <button key={item.id} className={mode === item.id ? "active" : ""} type="button" onClick={() => setMode(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>
          )}
          {showLink && (
            <label className="field">
              <span>参考链接</span>
              <textarea value={inputUrl} placeholder={tool.linkPlaceholder} onChange={(event) => setInputUrl(event.target.value)} />
              <small>{tool.linkHelper}</small>
            </label>
          )}
          {showTopic && (
            <label className="field">
              <span>文章主题</span>
              <input value={topic} placeholder="例如：本地咖啡品牌如何用社群提升复购" onChange={(event) => setTopic(event.target.value)} />
            </label>
          )}
          {showText && (
            <label className="field">
              <span>{tool.sourceLabel}</span>
              {showFormatOption ? (
                <div
                  className={`rich-input ${inputText.trim() && !isInputEditing ? "is-rendered" : ""}`}
                  onClick={() => {
                    setIsInputEditing(true);
                    window.setTimeout(() => inputTextAreaRef.current?.focus(), 0);
                  }}
                >
                  <textarea
                        ref={inputTextAreaRef as Ref<HTMLTextAreaElement>}
                    className="rich-input-editor"
                    value={inputText}
                    placeholder={tool.textPlaceholder}
                    onChange={(event) => setInputText(event.target.value)}
                    onFocus={() => setIsInputEditing(true)}
                    onBlur={() => setIsInputEditing(false)}
                  />
                  {inputText.trim() && !isInputEditing && (
                    <div className="rich-input-rendered" aria-label="输入内容">
                      <MarkdownRenderer markdown={inputText} />
                    </div>
                  )}
                </div>
              ) : (
                <textarea value={inputText} placeholder={tool.textPlaceholder} onChange={(event) => setInputText(event.target.value)} />
              )}
              <small className={activeMode.limit && charCount > activeMode.limit ? "danger-text" : ""}>
                {activeMode.limit ? `${charCount} / ${activeMode.limit} 字` : `${charCount} 字`}
              </small>
            </label>
          )}
          {toolId === "aigc_reduce" && (
            <div className="upload-zone disabled-upload" aria-disabled="true">
              <Upload size={24} aria-hidden="true" />
              <span>文件读取即将支持</span>
              <small>后续将支持 markdown、txt、word 文件；当前请先粘贴文本。</small>
            </div>
          )}
          {showFormatOption && (
            <div className="field">
              <span>格式处理</span>
              <div className="segmented compact" role="tablist" aria-label="格式处理">
                <button type="button" className={preserveFormat ? "active" : ""} onClick={() => setPreserveFormat(true)}>
                  保留格式
                </button>
                <button type="button" className={!preserveFormat ? "active" : ""} onClick={() => setPreserveFormat(false)}>
                  不保留格式
                </button>
              </div>
              <small>{preserveFormat ? "保留原文结构，包括标题、段落、列表、引用和代码块。" : "去掉格式限制，整理成自然顺畅的正文。"}</small>
            </div>
          )}
          {showMaterials && (
            <label className="field">
              <span>补充素材</span>
              <textarea value={materials} placeholder={tool.textPlaceholder} onChange={(event) => setMaterials(event.target.value)} />
            </label>
          )}
          {showConfig && (
            <div className="field-row">
              <label className="field">
                <span>{tool.styleLabel}</span>
                <select
                  value={style}
                  onChange={(event) => {
                    setStyle(event.target.value);
                    if (event.target.value !== "自定义") setCustomStyle("");
                  }}
                >
                  {tool.styles.map((item) => <option key={item}>{item}</option>)}
                </select>
                {style === "自定义" && (
                  <input value={customStyle} placeholder="输入自定义内容类型" onChange={(event) => setCustomStyle(event.target.value)} />
                )}
              </label>
              <label className="field">
                <span>{tool.toneLabel}</span>
                <select
                  value={tone}
                  onChange={(event) => {
                    setTone(event.target.value);
                    if (event.target.value !== "自定义") setCustomTone("");
                  }}
                >
                  {tool.tones.map((item) => <option key={item}>{item}</option>)}
                </select>
                {tone === "自定义" && (
                  <input value={customTone} placeholder="输入自定义文章语气" onChange={(event) => setCustomTone(event.target.value)} />
                )}
              </label>
            </div>
          )}
          <div className="quick-chips">
            {tool.examples.map((example) => (
              <button key={example} type="button" onClick={() => {
                if (example.startsWith("http")) {
                  setMode("link");
                  setInputUrl(example);
                } else if (toolId === "generate") {
                  setMode("topic");
                  setTopic(example);
                } else {
                  setInputText(example);
                }
              }}>
                {example.startsWith("http") ? "参考链接示例" : example.slice(0, 18)}
              </button>
            ))}
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="action-row">
            <button className="primary-button" type="button" disabled={isGenerating} onClick={startGeneration}>
              <WandSparkles size={18} aria-hidden="true" />
              {isGenerating ? "生成中..." : tool.generateLabel}
            </button>
            <button className="secondary-button" type="button" onClick={clearInputs}>
              <Eraser size={18} aria-hidden="true" />
              清空输入
            </button>
          </div>
          <p className="status-text">{status}</p>
        </section>

        <section className="panel result-panel" aria-labelledby="result-title">
          <div className="result-toolbar">
            <div>
              <h2 id="result-title">生成结果</h2>
              <p>{generationId ? `记录 ID：${generationId}` : "结果会自动保存到历史记录。"}</p>
            </div>
            <div className="result-actions">
              <button className="secondary-button" type="button" disabled={!result} onClick={copyResult}>
                <Copy size={18} aria-hidden="true" />复制
              </button>
              <button className="secondary-button" type="button" disabled={!result} onClick={exportCurrentMarkdown}>
                <Download size={18} aria-hidden="true" />导出
              </button>
              <button className="secondary-button" type="button" disabled={!result || isGenerating} onClick={startGeneration}>
                <RefreshCw size={18} aria-hidden="true" />重新生成
              </button>
            </div>
          </div>
          <div className="result-body">
            {!result && !isGenerating && (
              <div className="empty-state">
                <FileText size={42} aria-hidden="true" />
                <h3>你的结果会出现在这里</h3>
                <p>先选择工具并填写内容。系统会以流式方式输出结果。</p>
              </div>
            )}
            {isGenerating && !result && <div className="loading-state">正在生成，请稍候...</div>}
            {result && (
              <div className={showRichResult ? "result-rich-text" : "result-copy"}>
                {showRichResult ? <MarkdownRenderer markdown={result} /> : result}
              </div>
            )}
          </div>
        </section>

      </div>

    </>
  );
}
