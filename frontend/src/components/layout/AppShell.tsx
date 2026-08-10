import { ApartmentOutlined, HistoryOutlined } from "@ant-design/icons";
import { Typography } from "antd";
import { Link, Outlet, useLocation } from "react-router-dom";

const { Text, Title } = Typography;

export function AppShell() {
  const location = useLocation();
  const projectMatch = location.pathname.match(/^\/projects\/([^/]+)\/graph/);
  const viewerBase =
    import.meta.env.VITE_PROMPT_VIEWER_URL ?? "http://localhost:5174/prompt-history";
  const promptHistoryUrl = projectMatch
    ? `${viewerBase}?projectId=${encodeURIComponent(projectMatch[1])}`
    : viewerBase;

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/projects" className="brand">
          <span className="brand-mark">
            <ApartmentOutlined />
          </span>
          <span>
            <Title level={4}>CallScope</Title>
            <Text type="secondary">调用视界</Text>
          </span>
        </Link>
        <nav className="header-actions">
          <a href={promptHistoryUrl} className="header-link">
            <HistoryOutlined />
            <span>Prompt History</span>
          </a>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
