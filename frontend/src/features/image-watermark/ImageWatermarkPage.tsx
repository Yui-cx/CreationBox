import { useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { Download, Eraser, FileText, ImageOff, MousePointer2, Paintbrush, RefreshCw, Upload, WandSparkles } from "lucide-react";
import { inpaintImage } from "../../lib/api";
import { downloadBlob } from "../../lib/download";
import { formatElapsedTime, imageInpaintErrorMessage } from "../../lib/format";

type ImageToolMode = "brush" | "rect";
type ImageMethod = "telea" | "ns";
type ImageEngine = "opencv" | "lama";
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_LAMA_IMAGE_BYTES = 10 * 1024 * 1024;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
const DEFAULT_IMAGE_INPAINT_RADIUS = 5;

export function ImageWatermarkPage() {
  const imageCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const rectStartRef = useRef<{ x: number; y: number } | null>(null);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [resultUrl, setResultUrl] = useState("");
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [engine, setEngine] = useState<ImageEngine>("opencv");
  const [toolMode, setToolMode] = useState<ImageToolMode>("brush");
  const [method, setMethod] = useState<ImageMethod>("telea");
  const [radius, setRadius] = useState(DEFAULT_IMAGE_INPAINT_RADIUS);
  const [brushSize, setBrushSize] = useState(28);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [maskTouched, setMaskTouched] = useState(false);
  const [maskHistory, setMaskHistory] = useState<ImageData[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("上传图片后，使用画笔或矩形标记需要修复的水印区域。");
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const maxUploadBytes = engine === "lama" ? MAX_LAMA_IMAGE_BYTES : MAX_IMAGE_BYTES;
  const maxUploadLabel = "10MB";
  const isSourceTooLarge = Boolean(sourceFile && sourceFile.size > maxUploadBytes);
  const processingStatus = engine === "lama" && isProcessing
    ? `智能修复中，已等待 ${formatElapsedTime(elapsedSeconds)}。首次等待时间较长，CPU 推理期间请保持当前页面打开。`
    : status;

  useEffect(() => () => {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    if (resultUrl) URL.revokeObjectURL(resultUrl);
  }, [imageUrl, resultUrl]);

  useEffect(() => {
    if (!isProcessing || engine !== "lama") {
      if (!isProcessing) setElapsedSeconds(0);
      return;
    }
    setElapsedSeconds(0);
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [engine, isProcessing]);

  useEffect(() => {
    if (!imageUrl) return;
    const image = new Image();
    image.onload = () => {
      const imageCanvas = imageCanvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      if (!imageCanvas || !maskCanvas) return;
      [imageCanvas, maskCanvas].forEach((canvas) => {
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
      });
      const imageContext = imageCanvas.getContext("2d");
      const maskContext = maskCanvas.getContext("2d");
      imageContext?.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
      imageContext?.drawImage(image, 0, 0);
      maskContext?.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
      setMaskHistory([]);
      setMaskTouched(false);
      setStatus("图片已载入。请涂抹或框选水印区域。");
    };
    image.src = imageUrl;
  }, [imageUrl]);

  function handleFile(file?: File) {
    if (!file) return;
    if (!IMAGE_TYPES.includes(file.type)) {
      setError("仅支持 PNG、JPEG、WebP 图片。");
      return;
    }
    if (file.size > maxUploadBytes) {
      setError(`${engine === "lama" ? "智能修复" : "快速修复"}图片大小不能超过 ${maxUploadLabel}。`);
      return;
    }
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    setSourceFile(file);
    setImageUrl(URL.createObjectURL(file));
    setResultUrl("");
    setResultBlob(null);
    setError("");
  }

  function canvasPoint(event: PointerEvent<HTMLCanvasElement>) {
    const canvas = maskCanvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * canvas.width,
      y: ((event.clientY - rect.top) / rect.height) * canvas.height
    };
  }

  function pushMaskHistory() {
    const canvas = maskCanvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    setMaskHistory((current) => [...current.slice(-19), context.getImageData(0, 0, canvas.width, canvas.height)]);
  }

  function drawBrush(point: { x: number; y: number }) {
    const canvas = maskCanvasRef.current;
    const context = canvas?.getContext("2d");
    if (!context) return;
    context.fillStyle = "rgba(255,255,255,0.72)";
    context.beginPath();
    context.arc(point.x, point.y, brushSize / 2, 0, Math.PI * 2);
    context.fill();
    setMaskTouched(true);
  }

  function handlePointerDown(event: PointerEvent<HTMLCanvasElement>) {
    if (!sourceFile) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pushMaskHistory();
    setIsDrawing(true);
    const point = canvasPoint(event);
    if (toolMode === "brush") {
      drawBrush(point);
    } else {
      rectStartRef.current = point;
    }
  }

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    if (!isDrawing || toolMode !== "brush") return;
    drawBrush(canvasPoint(event));
  }

  function handlePointerUp(event: PointerEvent<HTMLCanvasElement>) {
    if (!isDrawing) return;
    if (toolMode === "rect" && rectStartRef.current) {
      const start = rectStartRef.current;
      const end = canvasPoint(event);
      const canvas = maskCanvasRef.current;
      const context = canvas?.getContext("2d");
      if (context) {
        context.fillStyle = "rgba(255,255,255,0.72)";
        context.fillRect(start.x, start.y, end.x - start.x, end.y - start.y);
        setMaskTouched(true);
      }
    }
    rectStartRef.current = null;
    setIsDrawing(false);
  }

  function undoMask() {
    const canvas = maskCanvasRef.current;
    const context = canvas?.getContext("2d");
    const previous = maskHistory[maskHistory.length - 1];
    if (!canvas || !context || !previous) return;
    context.putImageData(previous, 0, 0);
    setMaskHistory((current) => current.slice(0, -1));
    setMaskTouched(maskHistory.length > 1);
  }

  function clearMask() {
    const canvas = maskCanvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    pushMaskHistory();
    context.clearRect(0, 0, canvas.width, canvas.height);
    setMaskTouched(false);
    setStatus("标记已清空。");
  }

  function resetImage() {
    setSourceFile(null);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    setImageUrl("");
    setResultUrl("");
    setResultBlob(null);
    setMaskTouched(false);
    setMaskHistory([]);
    setStatus("上传图片后，使用画笔或矩形标记需要修复的水印区域。");
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function createMaskBlob(): Promise<Blob | null> {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return null;
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = maskCanvas.width;
    exportCanvas.height = maskCanvas.height;
    const exportContext = exportCanvas.getContext("2d");
    const maskContext = maskCanvas.getContext("2d");
    if (!exportContext || !maskContext) return null;
    const imageData = maskContext.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
    const data = imageData.data;
    for (let index = 0; index < data.length; index += 4) {
      const alpha = data[index + 3] > 0 ? 255 : 0;
      data[index] = alpha;
      data[index + 1] = alpha;
      data[index + 2] = alpha;
      data[index + 3] = 255;
    }
    exportContext.putImageData(imageData, 0, 0);
    return new Promise((resolve) => exportCanvas.toBlob(resolve, "image/png"));
  }

  async function processImage() {
    if (!sourceFile) {
      setError("请先上传图片。");
      return;
    }
    if (sourceFile.size > maxUploadBytes) {
      setError(`${engine === "lama" ? "智能修复" : "快速修复"}图片大小不能超过 ${maxUploadLabel}。`);
      return;
    }
    if (!maskTouched) {
      setError("请先标记需要修复的水印区域。");
      return;
    }
    const maskBlob = await createMaskBlob();
    if (!maskBlob) {
      setError("标记区域生成失败，请重试。");
      return;
    }
    setError("");
    setIsProcessing(true);
    setStatus(engine === "lama" ? "智能修复中，已等待 00:00。首次等待时间较长，CPU 推理期间请保持当前页面打开。" : "正在快速修复图片，请稍候...");
    const formData = new FormData();
    formData.append("image", sourceFile);
    formData.append("mask", maskBlob, "mask.png");
    formData.append("engine", engine);
    formData.append("method", method);
    formData.append("radius", String(radius));
    try {
      const blob = await inpaintImage(formData);
      if (resultUrl) URL.revokeObjectURL(resultUrl);
      setResultBlob(blob);
      setResultUrl(URL.createObjectURL(blob));
      setStatus("处理完成，可预览或下载结果。");
    } catch (err) {
      setError(imageInpaintErrorMessage(err instanceof Error ? err.message : "INPAINT_FAILED"));
      setStatus("处理失败，请调整标记区域后重试。");
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <section className="image-tool-page" aria-labelledby="image-tool-title">
      <div className="tool-header">
        <span className="tool-kicker"><ImageOff size={16} aria-hidden="true" />图片修复</span>
        <h2 id="image-tool-title">图片水印去除</h2>
        <p>上传图片后手动标记水印区域，可选择 OpenCV 快速修复，或使用 LaMa CPU 智能修复处理复杂背景。</p>
      </div>

      <div className="notice-banner" role="note">
        <strong>授权提示</strong>
        <span>仅处理本人拥有版权或已获授权的图片，不用于移除第三方平台版权水印。</span>
      </div>

      <div className="image-work-grid">
        <section className="panel image-control-panel" aria-labelledby="image-input-title">
          <div className="panel-heading">
            <div>
              <h2 id="image-input-title">图片上传</h2>
              <p>支持 PNG、JPEG、WebP，当前模式单张最大 {maxUploadLabel}。</p>
            </div>
          </div>

          <div className="repair-mode-switch">
            <span>修复模式</span>
            <div className="segmented compact" role="tablist" aria-label="修复模式">
              <button type="button" className={engine === "opencv" ? "active" : ""} onClick={() => setEngine("opencv")}>
                快速修复
              </button>
              <button type="button" className={engine === "lama" ? "active" : ""} onClick={() => setEngine("lama")}>
                智能修复
              </button>
            </div>
            <small>{engine === "lama" ? "智能修复使用 LaMa CPU 推理，图片需小于 10MB；首次等待时间较长，处理期间请保持页面打开。" : "快速修复使用本地 OpenCV，适合小水印、角落 Logo 和简单背景。"}</small>
          </div>

          <label
            className={`upload-zone ${isDraggingFile ? "drag-over" : ""}`}
            onDragEnter={(event) => {
              event.preventDefault();
              setIsDraggingFile(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = "copy";
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                setIsDraggingFile(false);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              setIsDraggingFile(false);
              handleFile(event.dataTransfer.files?.[0]);
            }}
          >
            <Upload size={24} aria-hidden="true" />
            <span>{sourceFile ? sourceFile.name : "选择图片"}</span>
            <small>点击选择，或直接拖入图片；上传后使用画笔或矩形覆盖水印区域</small>
            <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleFile(event.target.files?.[0])} />
          </label>

          <div className="image-toolbar" aria-label="标记工具">
            <div className="segmented compact" role="tablist" aria-label="标记方式">
              <button type="button" className={toolMode === "brush" ? "active" : ""} onClick={() => setToolMode("brush")}>
                <Paintbrush size={16} aria-hidden="true" />画笔
              </button>
              <button type="button" className={toolMode === "rect" ? "active" : ""} onClick={() => setToolMode("rect")}>
                <MousePointer2 size={16} aria-hidden="true" />矩形
              </button>
            </div>
            <label className="inline-field">
              <span>画笔</span>
              <input type="range" min="8" max="72" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} />
            </label>
          </div>

          <div className="image-canvas-shell">
            {imageUrl ? (
              <div className="canvas-stage">
                <canvas ref={imageCanvasRef} aria-hidden="true" />
                <canvas
                  ref={maskCanvasRef}
                  aria-label="水印区域标记画布"
                  onPointerDown={handlePointerDown}
                  onPointerMove={handlePointerMove}
                  onPointerUp={handlePointerUp}
                  onPointerCancel={() => setIsDrawing(false)}
                />
              </div>
            ) : (
              <div className="empty-state compact-empty">
                <ImageOff size={40} aria-hidden="true" />
                <h3>等待上传图片</h3>
                <p>上传后会在这里显示原图，并可直接涂抹或框选水印区域。</p>
              </div>
            )}
          </div>

          {engine === "opencv" ? (
            <div className="field-row">
              <label className="field">
                <span>修复方式</span>
                <select value={method} onChange={(event) => setMethod(event.target.value as ImageMethod)}>
                  <option value="telea">Telea（默认）</option>
                  <option value="ns">Navier-Stokes</option>
                </select>
                <small>快速修复模式，适合小水印、角落 Logo 和简单背景。</small>
              </label>
              <label className="field">
                <span>修复半径：{radius}</span>
                <input type="range" min="1" max="10" value={radius} onChange={(event) => setRadius(Number(event.target.value))} />
                <small>默认 5，会扩大修复覆盖范围以减少边缘残留。</small>
              </label>
            </div>
          ) : (
            <div className="engine-note" role="note">
              <strong>智能修复</strong>
              <span>使用 LaMa CPU 推理，首次等待时间较长；当前同一时刻只处理 1 个智能修复任务，处理期间请保持当前页面打开。</span>
            </div>
          )}

          {(error || isSourceTooLarge) && (
            <p className="form-error" role="alert">
              {isSourceTooLarge ? `${engine === "lama" ? "智能修复" : "快速修复"}图片大小不能超过 ${maxUploadLabel}。` : error}
            </p>
          )}
          <div className="action-row">
            <button className="primary-button" type="button" disabled={!sourceFile || !maskTouched || isProcessing || isSourceTooLarge} onClick={processImage}>
              <WandSparkles size={18} aria-hidden="true" />
              {isProcessing ? "处理中..." : engine === "lama" ? "开始智能修复" : "开始快速修复"}
            </button>
            <button className="secondary-button" type="button" disabled={!maskTouched} onClick={undoMask}>
              <RefreshCw size={18} aria-hidden="true" />撤销
            </button>
            <button className="secondary-button" type="button" disabled={!sourceFile} onClick={clearMask}>
              <Eraser size={18} aria-hidden="true" />清空标记
            </button>
            <button className="secondary-button" type="button" disabled={!sourceFile} onClick={resetImage}>
              重新上传
            </button>
          </div>
          <p className="status-text">{processingStatus}</p>
        </section>

        <section className="panel image-result-panel" aria-labelledby="image-result-title">
          <div className="result-toolbar">
            <div>
              <h2 id="image-result-title">处理结果</h2>
              <p>结果不会保存到历史记录，下载后请自行留存。</p>
            </div>
            <button className="secondary-button" type="button" disabled={!resultBlob} onClick={() => resultBlob && downloadBlob("CreationBox-inpaint.png", resultBlob)}>
              <Download size={18} aria-hidden="true" />下载结果
            </button>
          </div>
          <div className="image-result-preview">
            {resultUrl ? (
              <img src={resultUrl} alt="水印处理后的图片结果" />
            ) : (
              <div className="empty-state compact-empty">
                <FileText size={40} aria-hidden="true" />
                <h3>结果会出现在这里</h3>
                <p>标记水印区域并点击开始处理后，可在这里查看和下载 PNG 结果。</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}
