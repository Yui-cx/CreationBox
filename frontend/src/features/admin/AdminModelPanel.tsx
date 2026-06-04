import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, Save } from "lucide-react";
import { fetchModelConfig, updateModelConfig, validateModelConfig } from "../../lib/api";

export function AdminModelPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["model-config"], queryFn: fetchModelConfig });
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!data) return;
    setProvider(data.provider);
    setModel(data.model);
  }, [data]);

  const selectedOption = data?.options.find((item) => item.provider === provider);
  const saveConfig = useMutation({
    mutationFn: () => updateModelConfig(provider, model),
    onSuccess: () => {
      setMessage("模型配置已保存。");
      queryClient.invalidateQueries({ queryKey: ["model-config"] });
    },
    onError: (err) => setMessage(err instanceof Error ? err.message : "保存失败")
  });
  const validateConfig = useMutation({
    mutationFn: () => validateModelConfig(provider, model),
    onSuccess: () => setMessage("模型验证成功。"),
    onError: (err) => setMessage(err instanceof Error ? err.message : "模型验证失败")
  });

  if (isLoading || !data) return <p className="muted">正在读取模型配置...</p>;

  return (
    <section className="panel admin-model-panel">
      <div className="panel-heading">
        <div>
          <h2>模型管理</h2>
          <p>切换会保存到数据库，API Key 继续从环境变量读取。</p>
        </div>
      </div>
      <div className="model-status-grid">
        {data.options.map((item) => (
          <div className="model-status" key={item.provider}>
            <strong>{item.label}</strong>
            <span className={`status-pill ${item.key_configured ? "success" : "muted-pill"}`}>
              {item.key_configured ? "Key 已配置" : "Key 未配置"}
            </span>
          </div>
        ))}
      </div>
      <div className="admin-form-grid">
        <label className="field">
          <span>服务商</span>
          <select
            value={provider}
            onChange={(event) => {
              const nextProvider = event.target.value;
              const nextOption = data.options.find((item) => item.provider === nextProvider);
              setProvider(nextProvider);
              setModel(nextOption?.models[0] || "");
            }}
          >
            {data.options.map((item) => <option key={item.provider} value={item.provider}>{item.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>模型</span>
          <select value={model} onChange={(event) => setModel(event.target.value)}>
            {(selectedOption?.models || []).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>
      <div className="action-row">
        <button className="primary-button" type="button" disabled={saveConfig.isPending || !provider || !model} onClick={() => saveConfig.mutate()}>
          <Save size={18} aria-hidden="true" />
          保存配置
        </button>
        <button className="secondary-button" type="button" disabled={validateConfig.isPending || !provider || !model} onClick={() => validateConfig.mutate()}>
          {validateConfig.isPending ? <RefreshCw size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
          {validateConfig.isPending ? "验证中..." : "验证模型"}
        </button>
      </div>
      <p className="status-text">{message || `当前配置：${data.provider} / ${data.model}`}</p>
    </section>
  );
}

