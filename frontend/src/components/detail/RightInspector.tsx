import { CodeOutlined, RobotOutlined } from "@ant-design/icons";
import { Tabs } from "antd";

import { AIAnalysisPanel } from "../ai-analysis/AIAnalysisPanel";
import { DetailPanel } from "./DetailPanel";

export function RightInspector() {
  return (
    <Tabs
      className="right-inspector-tabs"
      defaultActiveKey="ai"
      items={[
        {
          key: "ai",
          label: (
            <span>
              <RobotOutlined /> AI 分析
            </span>
          ),
          children: <AIAnalysisPanel />
        },
        {
          key: "detail",
          label: (
            <span>
              <CodeOutlined /> 节点详情
            </span>
          ),
          children: <DetailPanel />
        }
      ]}
    />
  );
}
