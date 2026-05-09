import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { AuthProvider } from "./stores/auth";
import { ChatProvider } from "./stores/chat";
import ChatPage from "./pages/ChatPage";
import TrendingPage from "./pages/TrendingPage";
import UserInsightsPage from "./pages/UserInsightsPage";
import RecallPage from "./pages/RecallPage";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/trending" element={<TrendingPage />} />
              <Route path="/user-insights" element={<UserInsightsPage />} />
              <Route path="/recall" element={<RecallPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </AuthProvider>
  </React.StrictMode>
);
