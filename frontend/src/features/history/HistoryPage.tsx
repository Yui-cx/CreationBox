import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, History, Trash2 } from "lucide-react";
import { useState } from "react";
import { deleteHistoryItem, exportMarkdown, fetchHistory } from "../../lib/api";
import { downloadText } from "../../lib/download";
import { iconMap } from "../../lib/icons";
import { tools } from "../../lib/tools";
import type { GenerationListItem } from "../../types";

export function HistoryPage({ onLoad }: { onLoad: (item: GenerationListItem) => void }) {
  const queryClient = useQueryClient();
  const { data = [], isLoading } = useQuery({ queryKey: ["history"], queryFn: fetchHistory });
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => new Set());
  const remove = useMutation({
    mutationFn: deleteHistoryItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["history"] })
  });
  const exportItem = useMutation({
    mutationFn: async (item: GenerationListItem) => {
      const markdown = await exportMarkdown(item.id);
      downloadText(`CreationBox-${item.id}.md`, markdown);
    }
  });

  function toggleGroup(toolId: string) {
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  }

  return (
    <section className="history-page" aria-labelledby="history-title">
      <div className="tool-header">
        <span className="tool-kicker"><History size={16} aria-hidden="true" />历史记录</span>
        <h2 id="history-title">历史记录</h2>
        <p>最多保留 10 条智能创作记录，方便回看、导出或继续编辑。</p>
      </div>

      <div className="panel history-page-panel">
        <div className="panel-heading">
          <div>
            <h2>全部历史</h2>
            <p>最多显示最近 10 条记录，当前 {data.length} 条</p>
          </div>
        </div>
        {isLoading && <p className="muted">正在读取历史...</p>}
        {!isLoading && data.length === 0 && <p className="muted">生成成功后会自动保存到这里。</p>}

        <div className="history-category-list">
          {Object.values(tools).map((tool) => {
            const items = data.filter((item) => item.tool_type === tool.id);
            const isExpanded = expandedGroups.has(tool.id);
            const ToolIcon = iconMap[tool.id];
            return (
              <section className="history-category" key={tool.id} aria-labelledby={`history-${tool.id}`}>
                <button
                  className={`history-category-header ${isExpanded ? "expanded" : ""}`}
                  type="button"
                  aria-expanded={isExpanded}
                  aria-controls={`history-list-${tool.id}`}
                  onClick={() => toggleGroup(tool.id)}
                >
                  <span className="history-category-title">
                    <span className="history-category-icon"><ToolIcon size={18} aria-hidden="true" /></span>
                    <span>
                      <h3 id={`history-${tool.id}`}>{tool.title}</h3>
                      <small>{tool.kicker}</small>
                    </span>
                  </span>
                  <span className="history-category-meta">
                    <strong>{items.length}</strong>
                    <span>条</span>
                    <ChevronDown size={18} aria-hidden="true" />
                  </span>
                </button>
                {isExpanded && (
                  <div className="history-category-body" id={`history-list-${tool.id}`}>
                    {items.length === 0 && <p className="muted">暂无记录。</p>}
                    <div className="history-list">
                      {items.map((item) => (
                        <article className="history-item" key={item.id}>
                          <button type="button" onClick={() => onLoad(item)}>
                            <strong>{item.output_content.split("\n")[0]?.replace(/#/g, "").trim() || tools[item.tool_type]?.title}</strong>
                            <span>{item.output_content.replace(/\s+/g, " ").slice(0, 120) || item.status}</span>
                          </button>
                          <div className="history-actions">
                            <button className="icon-button" type="button" aria-label="导出历史记录" onClick={() => exportItem.mutate(item)}>
                              <Download size={16} aria-hidden="true" />
                            </button>
                            <button className="icon-button danger" type="button" aria-label="删除历史记录" onClick={() => remove.mutate(item.id)}>
                              <Trash2 size={16} aria-hidden="true" />
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </section>
  );
}
