import { useState } from "react";
import { Bot, ShieldCheck, Users } from "lucide-react";
import { AdminModelPanel } from "./AdminModelPanel";
import { AdminUsersPanel } from "./AdminUsersPanel";

export function AdminPage({ isAdmin }: { isAdmin: boolean }) {
  const [tab, setTab] = useState<"users" | "model">("users");

  if (!isAdmin) {
    return (
      <section className="history-page" aria-labelledby="admin-denied-title">
        <div className="tool-header">
          <span className="tool-kicker"><ShieldCheck size={16} aria-hidden="true" />后台管理</span>
          <h2 id="admin-denied-title">无权限访问</h2>
          <p>当前账号不是管理员，无法进入后台管理。</p>
        </div>
      </section>
    );
  }

  return (
    <section className="history-page admin-page" aria-labelledby="admin-title">
      <div className="tool-header">
        <span className="tool-kicker"><ShieldCheck size={16} aria-hidden="true" />后台管理</span>
        <h2 id="admin-title">后台管理</h2>
        <p>管理用户使用次数、管理员权限和当前大模型配置。</p>
      </div>
      <div className="mode-tabs admin-tabs" role="tablist" aria-label="后台管理模块">
        <button type="button" className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>
          <Users size={16} aria-hidden="true" />
          用户管理
        </button>
        <button type="button" className={tab === "model" ? "active" : ""} onClick={() => setTab("model")}>
          <Bot size={16} aria-hidden="true" />
          模型管理
        </button>
      </div>
      {tab === "users" ? <AdminUsersPanel /> : <AdminModelPanel />}
    </section>
  );
}

