import { History, ImageOff, ShieldCheck } from "lucide-react";
import { iconMap } from "../lib/icons";
import { tools } from "../lib/tools";
import type { Me, ToolType } from "../types";

type ActiveView = "creation" | "history" | "imageWatermark" | "admin";

type NavigationProps = {
  activeView: ActiveView;
  toolId: ToolType;
  me?: Me;
  quotaLabel: string;
  onViewChange: (view: ActiveView) => void;
  onToolChange: (tool: ToolType) => void;
};

export function AppNavigation({ activeView, toolId, me, quotaLabel, onViewChange, onToolChange }: NavigationProps) {
  function switchTool(next: ToolType) {
    onToolChange(next);
  }

  function setActiveView(next: ActiveView) {
    onViewChange(next);
  }

  return (
    <aside className="sidebar" aria-label="CreationBox 工具导航">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">CB</div>
        <div>
          <p className="brand-name">CreationBox</p>
          <p className="brand-subtitle">AI 文本工作台</p>
        </div>
      </div>
      <nav className="sidebar-nav" aria-label="主导航">
        <button className={`nav-button primary-nav ${activeView === "history" ? "active" : ""}`} onClick={() => setActiveView("history")} type="button">
          <History size={18} aria-hidden="true" />
          <span>历史记录</span>
        </button>
        {me?.is_admin && (
          <button className={`nav-button primary-nav ${activeView === "admin" ? "active" : ""}`} onClick={() => setActiveView("admin")} type="button">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>后台管理</span>
          </button>
        )}
        <div className="nav-group">
          <div className="nav-group-title">智能创作</div>
          <div className="tool-nav" aria-label="智能创作">
        {Object.values(tools).map((item) => {
          const Icon = iconMap[item.id];
          return (
            <button key={item.id} className={`nav-button child-nav ${activeView === "creation" && item.id === toolId ? "active" : ""}`} onClick={() => switchTool(item.id)} type="button">
              <Icon size={18} aria-hidden="true" />
              <span>{item.title}</span>
              <small>{item.tag}</small>
            </button>
          );
        })}
          </div>
        </div>
        <div className="nav-group">
          <div className="nav-group-title">辅助工具</div>
          <div className="tool-nav" aria-label="辅助工具">
            <button className={`nav-button child-nav ${activeView === "imageWatermark" ? "active" : ""}`} onClick={() => setActiveView("imageWatermark")} type="button">
              <ImageOff size={18} aria-hidden="true" />
              <span>图片水印去除</span>
              <small>图片</small>
            </button>
          </div>
        </div>
      </nav>
      <div className="quota-card">
        <div>
          <span>使用次数</span>
          <strong>{quotaLabel}</strong>
        </div>
        <div className="quota-bar" aria-hidden="true">
          <span style={{ width: me ? (me.quota_total < 0 ? "100%" : `${(me.quota_remaining / me.quota_total) * 100}%`) : "0%" }} />
        </div>
      </div>
    </aside>
  );
}

export function MobileNavigation({ activeView, toolId, me, onViewChange, onToolChange }: Omit<NavigationProps, "quotaLabel">) {
  function switchTool(next: ToolType) {
    onToolChange(next);
  }

  function setActiveView(next: ActiveView) {
    onViewChange(next);
  }

  return (
    <nav className="mobile-tools" aria-label="移动端工具导航">
      <button className={activeView === "history" ? "active" : ""} onClick={() => setActiveView("history")} type="button">
        历史记录
      </button>
      {me?.is_admin && (
        <button className={activeView === "admin" ? "active" : ""} onClick={() => setActiveView("admin")} type="button">
          后台管理
        </button>
      )}
      {Object.values(tools).map((item) => (
        <button key={item.id} className={activeView === "creation" && item.id === toolId ? "active" : ""} onClick={() => switchTool(item.id)} type="button">
          {item.title}
        </button>
      ))}
      <button className={activeView === "imageWatermark" ? "active" : ""} onClick={() => setActiveView("imageWatermark")} type="button">
        图片水印去除
      </button>
    </nav>
  );
}
