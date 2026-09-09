import {
  ApartmentOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  FolderOpenOutlined,
  ImportOutlined,
  SafetyCertificateOutlined,
  ScanOutlined,
} from "@ant-design/icons";
import {
  App,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ProjectImportModal } from "../components/project/ProjectImportModal";
import { useProjectStore } from "../stores/projectStore";
import type { Project, ProjectCreate, ScanStatus } from "../types/project";

const { Paragraph, Text, Title } = Typography;

const features = [
  {
    icon: <FolderOpenOutlined />,
    title: "导入本地项目",
    description: "只读取项目目录，不执行目标代码。",
  },
  {
    icon: <ApartmentOutlined />,
    title: "逐层查看调用",
    description: "从 HTTP 接口进入，按需展开下游节点。",
  },
  {
    icon: <DatabaseOutlined />,
    title: "定位数据访问",
    description: "追踪 Service、Repository 与资源调用。",
  },
  {
    icon: <SafetyCertificateOutlined />,
    title: "保留源码证据",
    description: "每条关系都包含置信度、文件和行号。",
  },
];

const statusConfig: Record<ScanStatus, { color: string; label: string }> = {
  NOT_SCANNED: { color: "default", label: "未扫描" },
  SCANNING: { color: "processing", label: "扫描中" },
  READY: { color: "success", label: "扫描完成" },
  FAILED: { color: "error", label: "扫描失败" },
};

export function ProjectPage() {
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const {
    projects,
    loading,
    error,
    fetchProjects,
    createProject,
    deleteProject,
    startScan,
  } = useProjectStore();
  const [importOpen, setImportOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [scanningId, setScanningId] = useState<string | null>(null);

  useEffect(() => {
    void fetchProjects().catch(() => undefined);
  }, [fetchProjects]);

  const handleImport = async (payload: ProjectCreate) => {
    try {
      const project = await createProject(payload);
      setImportOpen(false);
      try {
        await startScan(project.id);
        message.success("项目已导入，正在自动扫描");
      } catch {
        message.warning("项目已导入，但自动扫描未启动，可在工作台重试");
      }
      navigate(`/projects/${project.id}/graph`);
    } catch {
      message.error(useProjectStore.getState().error ?? "项目导入失败");
    }
  };

  const handleDelete = (project: Project) => {
    modal.confirm({
      title: `删除“${project.name}”？`,
      content: "只删除 CallScope 中的项目记录，不会删除磁盘源码。",
      okText: "删除记录",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteProject(project.id);
          message.success("项目记录已删除");
        } catch {
          message.error("项目删除失败");
        }
      },
    });
  };

  const handleScan = async (project: Project) => {
    setScanningId(project.id);
    try {
      await startScan(project.id);
      navigate(`/projects/${project.id}/graph`);
    } catch {
      message.error("无法启动扫描");
    } finally {
      setScanningId(null);
    }
  };

  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(search.trim().toLowerCase()),
  );

  return (
    <div className="project-page">
      <section className="project-hero compact">
        <Tag color="purple">FastAPI + Spring 静态分析 · MVP</Tag>
        <Title>从接口入口，看清代码如何流动。</Title>
        <Paragraph>
          导入本地 FastAPI 或 Spring Boot 项目，静态识别 HTTP 接口与调用关系。
        </Paragraph>
        <Button
          type="primary"
          size="large"
          icon={<ImportOutlined />}
          onClick={() => setImportOpen(true)}
        >
          导入本地项目
        </Button>
      </section>

      <section className="project-list-section">
        <div className="section-heading">
          <div>
            <Text className="eyebrow">LOCAL PROJECTS</Text>
            <Title level={3}>本地项目</Title>
          </div>
          <Input.Search
            allowClear
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onSearch={(value) => void fetchProjects(value)}
            placeholder="搜索项目名称"
            className="project-search"
          />
        </div>

        {error && projects.length === 0 ? (
          <Empty description={error}>
            <Button onClick={() => void fetchProjects()}>重新加载</Button>
          </Empty>
        ) : (
          <Spin spinning={loading && projects.length === 0}>
            {filteredProjects.length === 0 ? (
              <Empty
                description={
                  projects.length ? "没有匹配的项目" : "还没有导入项目"
                }
              >
                {!projects.length && (
                  <Button type="primary" onClick={() => setImportOpen(true)}>
                    导入第一个项目
                  </Button>
                )}
              </Empty>
            ) : (
              <Row gutter={[16, 16]}>
                {filteredProjects.map((project) => {
                  const status = statusConfig[project.scanStatus];
                  return (
                    <Col xs={24} lg={12} xl={8} key={project.id}>
                      <Card className="project-card">
                        <div className="project-card-heading">
                          <div className="project-card-icon">
                            <FolderOpenOutlined />
                          </div>
                          <div className="project-card-title">
                            <Title level={5} ellipsis>
                              {project.name}
                            </Title>
                            <Tag color={status.color}>{status.label}</Tag>
                          </div>
                        </div>
                        <Tooltip title={project.rootPath}>
                          <Text
                            type="secondary"
                            ellipsis
                            className="project-path"
                          >
                            {project.rootPath}
                          </Text>
                        </Tooltip>
                        <div className="project-stats">
                          <span>
                            <strong>{project.totalFiles}</strong>
                            <Text type="secondary">
                              {project.language === "java"
                                ? " Java 文件"
                                : " Python 文件"}
                            </Text>
                          </span>
                          <span>
                            <strong>{project.totalEndpoints}</strong>
                            <Text type="secondary"> 接口</Text>
                          </span>
                        </div>
                        <Space className="project-actions">
                          <Button
                            type="primary"
                            onClick={() =>
                              navigate(`/projects/${project.id}/graph`)
                            }
                          >
                            打开工作台
                          </Button>
                          <Button
                            icon={<ScanOutlined />}
                            loading={scanningId === project.id}
                            disabled={project.scanStatus === "SCANNING"}
                            onClick={() => void handleScan(project)}
                          >
                            {project.scanStatus === "READY"
                              ? "重新扫描"
                              : "扫描"}
                          </Button>
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            disabled={project.scanStatus === "SCANNING"}
                            onClick={() => handleDelete(project)}
                            aria-label={`删除 ${project.name}`}
                          />
                        </Space>
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            )}
          </Spin>
        )}
      </section>

      {!projects.length && (
        <Row gutter={[16, 16]} className="feature-grid">
          {features.map((feature) => (
            <Col xs={24} md={12} xl={6} key={feature.title}>
              <Card className="feature-card">
                <span className="feature-icon">{feature.icon}</span>
                <Title level={5}>{feature.title}</Title>
                <Text type="secondary">{feature.description}</Text>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <ProjectImportModal
        open={importOpen}
        loading={loading}
        onCancel={() => setImportOpen(false)}
        onSubmit={handleImport}
      />
    </div>
  );
}
