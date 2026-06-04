import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { createAdminUser, fetchAdminUsers } from "../../lib/api";
import { AdminUserRow } from "./AdminUserRow";

export function AdminUsersPanel() {
  const queryClient = useQueryClient();
  const { data = [], isLoading } = useQuery({ queryKey: ["admin-users"], queryFn: fetchAdminUsers });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [dailyQuota, setDailyQuota] = useState("5");
  const [error, setError] = useState("");

  const createUser = useMutation({
    mutationFn: () => createAdminUser({
      username,
      password,
      email: email || undefined,
      is_admin: isAdmin,
      daily_quota_total: isAdmin ? undefined : Number(dailyQuota)
    }),
    onSuccess: () => {
      setUsername("");
      setPassword("");
      setEmail("");
      setIsAdmin(false);
      setDailyQuota("5");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "用户创建失败")
  });

  return (
    <div className="admin-stack">
      <section className="panel admin-create-panel">
        <div className="panel-heading">
          <div>
            <h2>添加用户</h2>
            <p>普通用户按每日次数使用，管理员不限次数并可进入后台。</p>
          </div>
        </div>
        <div className="admin-form-grid">
          <label className="field">
            <span>用户名</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="field">
            <span>密码</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label className="field">
            <span>邮箱</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="field">
            <span>今日次数</span>
            <input type="number" min="0" disabled={isAdmin} value={dailyQuota} onChange={(event) => setDailyQuota(event.target.value)} />
          </label>
          <label className="inline-check">
            <input type="checkbox" checked={isAdmin} onChange={(event) => setIsAdmin(event.target.checked)} />
            设置为管理员
          </label>
          <button className="primary-button" type="button" disabled={createUser.isPending || !username || !password} onClick={() => createUser.mutate()}>
            <Users size={18} aria-hidden="true" />
            添加用户
          </button>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>

      <section className="panel admin-table-panel">
        <div className="panel-heading">
          <div>
            <h2>用户列表</h2>
            <p>当前 {data.length} 个用户，管理员用户显示无限次数。</p>
          </div>
        </div>
        {isLoading ? (
          <p className="muted">正在读取用户...</p>
        ) : (
          <div className="table-scroll">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>用户</th>
                  <th>状态</th>
                  <th>权限</th>
                  <th>次数</th>
                  <th>管理</th>
                  <th>最后登录</th>
                </tr>
              </thead>
              <tbody>
                {data.map((item) => <AdminUserRow key={item.id} user={item} />)}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

