import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { resetAdminUserPassword, updateAdminUser, updateAdminUserQuota } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { AdminUserItem } from "../../types";

export function AdminUserRow({ user }: { user: AdminUserItem }) {
  const queryClient = useQueryClient();
  const [quotaTotal, setQuotaTotal] = useState(user.quota_total > -1 ? String(user.quota_total) : "");
  const [quotaUsed, setQuotaUsed] = useState(user.quota_used > -1 ? String(user.quota_used) : "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setQuotaTotal(user.quota_total > -1 ? String(user.quota_total) : "");
    setQuotaUsed(user.quota_used > -1 ? String(user.quota_used) : "");
  }, [user.quota_total, user.quota_used]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-users"] });
  const updateUser = useMutation({
    mutationFn: (payload: Partial<Pick<AdminUserItem, "email" | "status" | "is_admin">>) => updateAdminUser(user.id, payload),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof Error ? err.message : "更新失败")
  });
  const updateQuota = useMutation({
    mutationFn: () => updateAdminUserQuota(user.id, Number(quotaTotal), Number(quotaUsed)),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof Error ? err.message : "次数更新失败")
  });
  const resetPassword = useMutation({
    mutationFn: () => resetAdminUserPassword(user.id, password),
    onSuccess: () => {
      setPassword("");
      invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "密码重置失败")
  });

  const busy = updateUser.isPending || updateQuota.isPending || resetPassword.isPending;
  const quotaLabel = user.is_admin ? "无限" : `${user.quota_remaining} / ${user.quota_total}`;

  return (
    <tr>
      <td>
        <strong>{user.username}</strong>
        <span>{user.email || "未设置邮箱"}</span>
      </td>
      <td>
        <span className={`status-pill ${user.status === "active" ? "success" : "muted-pill"}`}>{user.status === "active" ? "启用" : "停用"}</span>
      </td>
      <td>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={user.is_admin}
            disabled={busy}
            onChange={(event) => updateUser.mutate({ is_admin: event.target.checked })}
          />
          管理员
        </label>
      </td>
      <td>
        <strong>{quotaLabel}</strong>
        <span>已生成 {user.generation_count} 次</span>
      </td>
      <td className="table-controls">
        <button className="secondary-button compact-button" type="button" disabled={busy} onClick={() => updateUser.mutate({ status: user.status === "active" ? "inactive" : "active" })}>
          {user.status === "active" ? "停用" : "启用"}
        </button>
        {!user.is_admin && (
          <div className="inline-fields">
            <input type="number" min="0" value={quotaTotal} onChange={(event) => setQuotaTotal(event.target.value)} aria-label={`${user.username} 今日总次数`} />
            <input type="number" min="0" value={quotaUsed} onChange={(event) => setQuotaUsed(event.target.value)} aria-label={`${user.username} 今日已用次数`} />
            <button className="secondary-button compact-button" type="button" disabled={busy} onClick={() => updateQuota.mutate()}>
              保存次数
            </button>
          </div>
        )}
        <div className="inline-fields">
          <input type="password" value={password} placeholder="新密码" onChange={(event) => setPassword(event.target.value)} aria-label={`${user.username} 新密码`} />
          <button className="secondary-button compact-button" type="button" disabled={busy || !password} onClick={() => resetPassword.mutate()}>
            重置
          </button>
        </div>
        {error && <span className="danger-text">{error}</span>}
      </td>
      <td>
        <span>{formatDateTime(user.last_login_at)}</span>
      </td>
    </tr>
  );
}

