import { App, Breadcrumb, Button, Space, Spin, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { DetailPanel } from "../components/detail/DetailPanel";
import { EndpointList } from "../components/endpoint/EndpointList";
import { GraphCanvas } from "../components/graph/GraphCanvas";
import { ThreeColumnLayout } from "../components/layout/ThreeColumnLayout";
import { ScanStatusBanner } from "../components/project/ScanStatusBanner";
import { useScanPolling } from "../hooks/useScanPolling";
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
    startScan
  } = useProjectStore();
  const resetEndpoints = useEndpointStore((state) => state.reset);
  const resetGraph = useGraphStore((state) => state.reset);
  const [startingScan, setStartingScan] = useState(false);

  useEffect(() => {
    if (!projectId) {
      return;
    }
    resetEndpoints();
    resetGraph();
    void fetchProject(projectId).catch(() => message.error("项目加载失败"));
    void refreshScan(projectId).catch(() => undefined);
  }, [
    fetchProject,
    message,
    projectId,
    refreshScan,
    resetEndpoints,
    resetGraph
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
          <Breadcrumb
            items={[
              { title: <Link to="/projects">项目</Link> },
              { title: activeProject?.name ?? projectId }
            ]}
          />
          <Space>
            <Text type="secondary">
              {scanRunning
                ? "扫描中"
                : activeProject?.scanStatus === "READY"
                  ? "扫描完成"
                  : "尚未扫描"}
            </Text>
            <Tag>{activeProject?.totalFiles ?? 0} 个文件</Tag>
            <Tag>{activeProject?.totalEndpoints ?? 0} 个接口</Tag>
            <Button
              type="primary"
              loading={startingScan}
              disabled={scanRunning}
              onClick={() => void handleScan()}
            >
              {activeProject?.scanStatus === "READY" ? "重新扫描" : "开始扫描"}
            </Button>
          </Space>
        </div>

        {activeScan && <ScanStatusBanner task={activeScan} />}

        <ThreeColumnLayout
          left={<EndpointList />}
          center={<GraphCanvas />}
          right={<DetailPanel />}
        />
      </div>
    </>
  );
}
