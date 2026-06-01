import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import { login } from "../../lib/api";
import { useAuthStore } from "../../store/auth";

export function AuthPanel() {
  const queryClient = useQueryClient();
  const { setTokens } = useAuthStore();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      queryClient.invalidateQueries();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "登录失败")
  });

  return (
    <section className="auth-panel" aria-labelledby="auth-title">
      <div>
        <p className="eyebrow">CreationBox MVP</p>
        <h1 id="auth-title">AI 文本工作台</h1>
        <p className="auth-copy">管理员可进入后台管理，普通用户登录后按每日次数使用智能创作工具。</p>
      </div>
      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          setError("");
          mutation.mutate();
        }}
      >
        <label>
          <span>用户名</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required minLength={3} />
        </label>
        <label>
          <span>密码</span>
          <input value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" type="password" required minLength={1} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={mutation.isPending} type="submit">
          <UserRound size={18} aria-hidden="true" />
          {mutation.isPending ? "处理中..." : "登录工作台"}
        </button>
      </form>
    </section>
  );
}

