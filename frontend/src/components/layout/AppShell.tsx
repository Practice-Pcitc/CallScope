import {
  ApartmentOutlined,
  BookOutlined,
  GithubOutlined
} from "@ant-design/icons";
import { Button, Space, Tag, Typography } from "antd";
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

        <Space size="middle">
          <Tag color="purple">MVP · 阶段二</Tag>
          <Button type="text" icon={<BookOutlined />}>
            架构说明
          </Button>
          <Button type="text" icon={<GithubOutlined />} disabled>
            本地项目
          </Button>
        </Space>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

