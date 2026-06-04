import { AuthPanel } from "../features/auth/AuthPanel";
import { Workspace } from "../features/workspace/Workspace";
import { useAuthStore } from "../store/auth";

export function App() {
  const accessToken = useAuthStore((state) => state.accessToken);
  return accessToken ? <Workspace /> : <AuthPanel />;
}

