import { FormEvent, useEffect, useState } from "react";
import { LogIn, UserPlus, X } from "lucide-react";
import { useAuth } from "../../stores/auth";

interface AuthModalProps {
  open: boolean;
  initialMode: "login" | "register";
  onClose: () => void;
}

export default function AuthModal({ open, initialMode, onClose }: AuthModalProps) {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [identifier, setIdentifier] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [categories, setCategories] = useState("美妆, 收纳");
  const [platforms, setPlatforms] = useState("小红书, 抖音");
  const [businessFocus, setBusinessFocus] = useState("");
  const [adminCode, setAdminCode] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setMode(initialMode);
    }
  }, [initialMode, open]);

  if (user || !open) {
    return null;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "login") {
        await login(identifier, password);
      } else {
        await register({
          display_name: displayName,
          password,
          preferred_categories: splitTags(categories),
          preferred_platforms: splitTags(platforms),
          business_focus: businessFocus,
          admin_invite_code: adminCode || undefined
        });
      }
      clearAndClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  function clearAndClose() {
    setIdentifier("");
    setDisplayName("");
    setPassword("");
    setCategories("");
    setPlatforms("");
    setBusinessFocus("");
    setAdminCode("");
    setError("");
    onClose();
  }

  return (
    <div className="modalLayer">
      <div className="authPanel">
        <button className="ghostIcon closeButton" onClick={clearAndClose} aria-label="关闭登录提示">
          <X size={18} />
        </button>
        <div className="authTabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            <LogIn size={16} /> 登录
          </button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            <UserPlus size={16} /> 注册
          </button>
        </div>
        <form onSubmit={onSubmit} className="formStack">
          {mode === "login" ? (
            <label>
              账号或用户名
              <input value={identifier} onChange={(event) => setIdentifier(event.target.value)} required />
            </label>
          ) : (
            <>
              <label>
                名字
                <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
              </label>
              <label>
                偏好领域
                <input value={categories} onChange={(event) => setCategories(event.target.value)} />
              </label>
              <label>
                常关注平台
                <input value={platforms} onChange={(event) => setPlatforms(event.target.value)} />
              </label>
              <label>
                主要经营方向
                <input value={businessFocus} onChange={(event) => setBusinessFocus(event.target.value)} />
              </label>
              <label>
                Admin 邀请码
                <input value={adminCode} onChange={(event) => setAdminCode(event.target.value)} />
              </label>
            </>
          )}
          <label>
            密码
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} />
          </label>
          {error ? <p className="formError">{error}</p> : null}
          <button className="primaryButton" type="submit">
            {mode === "login" ? "进入工作台" : "创建账号"}
          </button>
        </form>
      </div>
    </div>
  );
}

function splitTags(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
