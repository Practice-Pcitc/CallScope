import { AimOutlined } from "@ant-design/icons";
import { Empty, Space, Tag, Typography } from "antd";
import type { ReactNode } from "react";

import type { AnalysisBinding } from "../../types/aiAnalysis";

const { Paragraph, Text } = Typography;

export interface FocusBinding {
  nodeIds: string[];
  edgeIds: string[];
  endpointIds?: string[];
  evidenceIds?: string[];
}

export interface AnalysisCardData {
  key: string;
  title: ReactNode;
  description: ReactNode;
  meta?: ReactNode;
  binding: FocusBinding;
  confidence?: AnalysisBinding["confidence"];
  claimType?: AnalysisBinding["claimType"];
}

export function AnalysisCards({
  items,
  focusedKey,
  emptyText,
  onFocus
}: {
  items: AnalysisCardData[];
  focusedKey: string | null;
  emptyText: string;
  onFocus: (key: string, binding: FocusBinding) => void;
}) {
  if (!items.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />;
  }

  return (
    <div className="ai-analysis-list">
      {items.map((item) => (
        <button
          type="button"
          className={`ai-analysis-card${focusedKey === item.key ? " focused" : ""}`}
          data-ai-item-key={item.key}
          key={item.key}
          onClick={() => onFocus(item.key, item.binding)}
        >
          <div className="ai-analysis-card-heading">
            <Text strong>{item.title}</Text>
            <Space size={4}>
              {item.claimType === "INFERENCE" && <Tag color="gold">推断</Tag>}
              {item.confidence && <Tag>{item.confidence}</Tag>}
              {(item.binding.nodeIds.length > 0 ||
                item.binding.edgeIds.length > 0) && <AimOutlined />}
            </Space>
          </div>
          <Paragraph>{item.description}</Paragraph>
          {item.meta && <div className="ai-analysis-card-meta">{item.meta}</div>}
        </button>
      ))}
    </div>
  );
}
