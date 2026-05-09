import { useState } from "react";
import { BarChart3, BotMessageSquare, Flame, LogIn, LogOut, RotateCcw, UserPlus, UsersRound } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import AuthModal from "../auth/AuthModal";
import { useAuth } from "../../stores/auth";

const navItems = [
  { to: "/chat", label: "智能运营台", icon: BotMessageSquare, adminOnly: false },
  { to: "/trending", label: "最新爆品", icon: Flame, adminOnly: false },
  { to: "/user-insights", label: "用户洞察", icon: UsersRound, adminOnly: true },
  { to: "/recall", label: "一键召回", icon: RotateCcw, adminOnly: true }
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [authOpen, setAuthOpen] = useState(true);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  function openAuth(mode: "login" | "register") {
    setAuthMode(mode);
    setAuthOpen(true);
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <BarChart3 size={24} />
          <div>
            <strong>TrendLogic</strong>
            <span>AI 电商运营助手</span>
          </div>
        </div>
        <nav>
          {navItems
            .filter((item) => !item.adminOnly || user?.role === "admin")
            .map((item) => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "navItem active" : "navItem")}>
                  <Icon size={18} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <strong>{user ? user.display_name : "未登录访客"}</strong>
            <span>{user ? `${user.account_id} · ${user.role}` : "登录后可使用核心功能"}</span>
          </div>
          {user ? (
            <button className="ghostButton" onClick={logout}>
              <LogOut size={16} /> 退出
            </button>
          ) : (
            <div className="topbarActions">
              <button className="ghostButton" onClick={() => openAuth("login")}>
                <LogIn size={16} /> 登录
              </button>
              <button className="primaryButton" onClick={() => openAuth("register")}>
                <UserPlus size={16} /> 注册
              </button>
            </div>
          )}
        </header>
        <Outlet />
      </main>
      <AuthModal open={authOpen} initialMode={authMode} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
