import { ArrowLeftOutlined } from "@ant-design/icons";
import { App, Button, Space, Spin, Typography } from "antd";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { RightInspector } from "../components/detail/RightInspector";
import { EndpointList } from "../components/endpoint/EndpointList";
import { GraphCanvas } from "../components/graph/GraphCanvas";
import { ThreeColumnLayout } from "../components/layout/ThreeColumnLayout";
import { ScanStatusBanner } from "../components/project/ScanStatusBanner";
import { useScanPolling } from "../hooks/useScanPolling";
import { useAIAnalysisStore } from "../stores/aiAnalysisStore";
import { useEndpointStore } from "../stores/endpointStore";
import { useGraphStore } from "../stores/graphStore";
import { useProjectStore } from "../stores/projectStore";

const { Text } = Typography;

export function GraphPage() {
  const { projectId } = useParams();
  const { message } = App.useApp();
  const {
    activeProject,
    activeScan,
    loading,
    fetchProject,
    refreshScan,
    startScan,
  } = useProjectStore();
  const resetEndpoints = useEndpointStore((state) => state.reset);
  const resetGraph = useGraphStore((state) => state.reset);
  const resetAI = useAIAnalysisStore((state) => state.reset);
  const [startingScan, setStartingScan] = useState(false);

  useEffect(() => {
    if (!projectId) {
      return;
    }
    resetEndpoints();
    resetGraph();
    resetAI();
    void fetchProject(projectId).catch(() => message.error("项目加载失败"));
    void refreshScan(projectId).catch(() => undefined);
  }, [
    fetchProject,
    message,
    projectId,
    refreshScan,
    resetAI,
    resetEndpoints,
    resetGraph,
  ]);

  useScanPolling(projectId);

  const handleScan = async () => {
    if (!projectId) {
      return;
    }
    setStartingScan(true);
    try {
      await startScan(projectId);
      message.success("扫描任务已启动");
    } catch {
      message.error("无法启动扫描任务");
    } finally {
      setStartingScan(false);
    }
  };

  const scanRunning =
    activeScan?.status === "PENDING" || activeScan?.status === "RUNNING";

  return (
    <>
      <Spin spinning={loading && !activeProject} fullscreen />
      <div className="graph-page">
        <div className="workspace-bar">
          <Space size={8} className="workspace-project">
            <Link to="/projects" aria-label="返回项目列表">
              <ArrowLeftOutlined />
            </Link>
            <Text strong>{activeProject?.name ?? projectId}</Text>
          </Space>
          <Space size={10}>
            <Text type="secondary" className="workspace-stats">
              {scanRunning
                ? "扫描中"
                : `${activeProject?.totalFiles ?? 0} 文件 · ${
                    activeProject?.totalEndpoints ?? 0
                  } 接口`}
            </Text>
            <Button
              type="primary"
              size="small"
              loading={startingScan}
              disabled={scanRunning}
              onClick={() => void handleScan()}
            >
              {activeProject?.scanStatus === "READY" ? "重新扫描" : "开始扫描"}
            </Button>
          </Space>
        </div>

        {activeScan && activeScan.status !== "SUCCEEDED" && (
          <ScanStatusBanner task={activeScan} />
        )}

        <ThreeColumnLayout
          left={<EndpointList />}
          center={<GraphCanvas />}
          right={<RightInspector />}
        />
      </div>
    </>
  );
}
