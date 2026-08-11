import { ApartmentOutlined } from "@ant-design/icons";
import { Typography } from "antd";
import { Link, Outlet } from "react-router-dom";

const { Text, Title } = Typography;

export function AppShell() {
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
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
