import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from "@ant-design/icons";
import { Alert, Button, Popover, Progress, Space, Tag, Typography } from "antd";

import type { ScanTask } from "../../types/scan";

const { Text } = Typography;

const stageNames: Record<string, string> = {
  DISCOVERY: "发现文件",
  VALIDATE: "校验文件",
  PARSE: "解析源代码",
  RESOLVE: "解析接口与调用关系",
  PERSIST: "保存结果",
  COMPLETED: "扫描完成"
};

export function ScanStatusBanner({ task }: { task: ScanTask }) {
  const running = task.status === "PENDING" || task.status === "RUNNING";
  const failed = task.status === "FAILED";

  return (
    <div className="scan-status-banner">
      <div className="scan-status-main">
        <Space>
          {running && <LoadingOutlined spin className="scan-running-icon" />}
          {task.status === "SUCCEEDED" && (
            <CheckCircleOutlined className="scan-success-icon" />
          )}
          {failed && <CloseCircleOutlined className="scan-failed-icon" />}
          <Text strong>{stageNames[task.stage] ?? task.stage}</Text>
          <Tag>{task.progress}%</Tag>
        </Space>
        <Progress
          percent={task.progress}
          showInfo={false}
          status={failed ? "exception" : task.status === "SUCCEEDED" ? "success" : "active"}
          size="small"
        />
      </div>
      <Space size="middle" className="scan-metrics">
        <Text type="secondary">发现 {task.discoveredFiles}</Text>
        <Text type="secondary">处理 {task.processedFiles}</Text>
        <Text type="secondary">跳过 {task.skippedFiles}</Text>
        <Text type={task.failedFiles ? "danger" : "secondary"}>
          失败 {task.failedFiles}
        </Text>
        {task.errors.length > 0 && (
          <Popover
            title={`扫描记录（${task.errors.length}）`}
            content={
              <div className="scan-error-list">
                {task.errors.slice(0, 8).map((error, index) => (
                  <div key={`${error.path}-${error.code}-${index}`}>
                    <Text code>{error.code}</Text>
                    <Text>{error.path || "项目根目录"}</Text>
                    <Text type="secondary">{error.message}</Text>
                  </div>
                ))}
              </div>
            }
          >
            <Button type="link" size="small">
              查看记录
            </Button>
          </Popover>
        )}
      </Space>
      {task.currentFile && (
        <Text type="secondary" ellipsis className="scan-current-file">
          {task.currentFile}
        </Text>
      )}
      {task.errorMessage && (
        <Alert type="error" showIcon message={task.errorMessage} />
      )}
    </div>
  );
}
