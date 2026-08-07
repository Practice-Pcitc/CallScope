import {
  BranchesOutlined,
  ReloadOutlined,
  RobotOutlined,
  ThunderboltOutlined
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Segmented,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography
} from "antd";
import { useCallback, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { useAIAnalysisStore } from "../../stores/aiAnalysisStore";
import { useEndpointStore } from "../../stores/endpointStore";
import { useGraphStore } from "../../stores/graphStore";
import {
  AnalysisCards,
  type AnalysisCardData,
  type FocusBinding
} from "./AnalysisCards";

const { Paragraph, Text, Title } = Typography;

interface LocatedBinding extends FocusBinding {
  tab: string;
  key: string;
}

const binding = (nodeIds: string[]): FocusBinding => ({
  nodeIds,
  edgeIds: []
});

function DataColumn({
  title,
  items,
  empty
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <div className="ai-data-column">
      <Text strong>{title}</Text>
      {items.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <Text type="secondary">{empty}</Text>
      )}
    </div>
  );
}

export function AIAnalysisPanel() {
  const { projectId } = useParams();
  const selectedIds = useEndpointStore((state) => state.selectedIds);
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  const setAIHighlights = useGraphStore((state) => state.setAIHighlights);
  const clearAIHighlights = useGraphStore((state) => state.clearAIHighlights);
  const selectNode = useGraphStore((state) => state.selectNode);
  const {
    analysis,
    loading,
    error,
    activeTab,
    focusedItemKey,
    analyzeEndpoints,
    analyzeNode,
    regenerate,
    setActiveTab,
    setFocusedItemKey
  } = useAIAnalysisStore();
  const result = analysis?.result;

  const focus = useCallback(
    (key: string, itemBinding: FocusBinding) => {
      setFocusedItemKey(key);
      setAIHighlights(itemBinding.nodeIds, itemBinding.edgeIds);
      if (itemBinding.nodeIds[0]) {
        void selectNode(itemBinding.nodeIds[0]);
      }
    },
    [selectNode, setAIHighlights, setFocusedItemKey]
  );

  const sectionCards = useMemo(() => {
    if (!result) {
      return {
        flow: [] as AnalysisCardData[],
        rules: [] as AnalysisCardData[],
        state: [] as AnalysisCardData[],
        failures: [] as AnalysisCardData[],
        objects: [] as AnalysisCardData[],
        related: [] as AnalysisCardData[],
        risks: [] as AnalysisCardData[]
      };
    }
    return {
      flow: result.businessFlow.map((item, index) => ({
        key: `flow-${index}`,
        title: `${item.step}. ${item.title}`,
        description: item.description,
        meta: item.businessMeaning,
        binding: binding(item.nodeIds)
      })),
      rules: result.businessRules.map((item, index) => ({
        key: `rule-${index}`,
        title: item.rule,
        description: item.reason,
        meta: `不满足时：${item.failureResult}`,
        binding: binding(item.nodeIds)
      })),
      state: result.stateChanges.map((item, index) => ({
        key: `state-${index}`,
        title: item.businessObject,
        description: `执行前：${item.before}`,
        meta: `执行后：${item.after}`,
        binding: binding(item.nodeIds)
      })),
      failures: result.failureFlows.map((item, index) => ({
        key: `failure-${index}`,
        title: item.scenario,
        description: item.reason,
        meta: `业务影响：${item.businessImpact}`,
        binding: binding(item.nodeIds)
      })),
      objects: [
        ...result.coreBusinessObjects.map((item, index) => ({
          key: `object-${index}`,
          title: item.name,
          description: item.role,
          binding: binding([])
        })),
        ...result.keyBusinessNodes.map((item, index) => ({
          key: `key-${index}`,
          title: item.name,
          description: item.businessImportance,
          meta: item.reason,
          binding: binding(item.nodeIds)
        }))
      ],
      related: result.relatedEndpoints.map((item, index) => ({
        key: `related-${index}`,
        title: item.endpointId,
        description: item.relationship,
        meta: item.businessReason,
        binding: binding([])
      })),
      risks: result.businessRisks.map((item, index) => ({
        key: `risk-${index}`,
        title: (
          <>
            {item.title} <Tag color={item.level === "HIGH" ? "red" : "gold"}>{item.level}</Tag>
          </>
        ),
        description: item.description,
        binding: binding(item.nodeIds)
      }))
    };
  }, [result]);

  const locatedBindings = useMemo<LocatedBinding[]>(
    () =>
      Object.entries(sectionCards).flatMap(([tab, cards]) =>
        (cards as AnalysisCardData[]).map((card) => ({
          tab,
          key: card.key,
          nodeIds: card.binding.nodeIds,
          edgeIds: card.binding.edgeIds
        }))
      ),
    [sectionCards]
  );

  useEffect(() => {
    if (!selectedNodeId || !result) {
      return;
    }
    const current = locatedBindings.find(
      (item) => item.key === focusedItemKey
    );
    if (current?.nodeIds.includes(selectedNodeId)) {
      return;
    }
    const located = locatedBindings.find((item) =>
      item.nodeIds.includes(selectedNodeId)
    );
    if (!located) {
      return;
    }
    setActiveTab(located.tab);
    setFocusedItemKey(located.key);
    window.setTimeout(() => {
      document
        .querySelector(`[data-ai-item-key="${located.key}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 60);
  }, [
    focusedItemKey,
    locatedBindings,
    result,
    selectedNodeId,
    setActiveTab,
    setFocusedItemKey
  ]);

  useEffect(() => () => clearAIHighlights(), [clearAIHighlights]);

  const runEndpointAnalysis = () => {
    if (projectId) {
      void analyzeEndpoints(projectId, selectedIds);
    }
  };
  const runNodeAnalysis = () => {
    if (projectId && selectedNodeId) {
      void analyzeNode(projectId, selectedNodeId);
    }
  };
  const cardList = (key: keyof typeof sectionCards, emptyText: string) => (
    <AnalysisCards
      items={sectionCards[key]}
      focusedKey={focusedItemKey}
      emptyText={emptyText}
      onFocus={focus}
    />
  );

  const tabs = result
    ? [
        {
          key: "overview",
          label: "业务概览",
          children: (
            <div className="ai-summary">
              <Alert
                type="info"
                showIcon
                message="这个接口是干什么的"
                description={result.businessSummary}
              />
              <div className="business-logic-card">
                <Text className="ai-section-label">典型使用场景</Text>
                <Paragraph>{result.businessScenario}</Paragraph>
              </div>
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label="流程位置">
                  <Tag>{result.processPosition.position}</Tag>
                  {result.processPosition.description}
                </Descriptions.Item>
              </Descriptions>
              <div className="ai-section-label">正常流程</div>
              <ol className="business-step-list">
                {result.normalFlow.map((item, index) => (
                  <li key={`${item}-${index}`}>
                    <span>{index + 1}</span>
                    <Text>{item}</Text>
                  </li>
                ))}
              </ol>
            </div>
          )
        },
        {
          key: "flow",
          label: "业务流程",
          children: cardList("flow", "没有可展示的业务步骤")
        },
        {
          key: "rules",
          label: "业务规则",
          children: cardList("rules", "当前源码中未识别到明确业务规则")
        },
        {
          key: "state",
          label: "状态变化",
          children: cardList(
            "state",
            "该接口主要用于查询，未发现直接改变核心业务数据的证据"
          )
        },
        {
          key: "data",
          label: "业务数据流",
          children: (
            <div className="ai-data-grid">
              <DataColumn
                title="用户或调用方提供"
                items={result.businessDataFlow.inputs}
                empty="无可识别输入"
              />
              <DataColumn
                title="系统读取"
                items={result.businessDataFlow.reads}
                empty="未识别到明确读取"
              />
              <DataColumn
                title="系统产生或修改"
                items={result.businessDataFlow.changes}
                empty="未发现直接数据变化"
              />
              <DataColumn
                title="最终返回"
                items={result.businessDataFlow.outputs}
                empty="返回内容未声明"
              />
            </div>
          )
        },
        {
          key: "failures",
          label: "失败流程",
          children: cardList("failures", "未发现可证实的失败分支")
        },
        {
          key: "objects",
          label: "业务对象",
          children: cardList("objects", "核心业务对象从当前代码无法确认")
        },
        {
          key: "related",
          label: "关联接口",
          children: cardList("related", "没有发现同一业务分类下的候选接口")
        },
        {
          key: "risks",
          label: "风险与技术",
          children: (
            <div className="ai-tab-stack">
              {cardList("risks", "当前证据不足以确认潜在业务风险")}
              <div className="ai-section-label">技术实现参考</div>
              <div className="business-logic-card">
                <Paragraph>
                  <Text strong>入口：</Text>
                  {result.technicalReference.entry}
                </Paragraph>
                <DataColumn
                  title="核心方法"
                  items={result.technicalReference.coreMethods}
                  empty="无"
                />
                <DataColumn
                  title="数据访问"
                  items={result.technicalReference.dataAccess}
                  empty="无"
                />
                <DataColumn
                  title="关键源码"
                  items={result.technicalReference.sourceFiles}
                  empty="无"
                />
              </div>
            </div>
          )
        }
      ]
    : [];

  return (
    <div className="panel-content ai-analysis-panel">
      <div className="panel-heading">
        <div>
          <Text className="eyebrow">BUSINESS ANALYSIS</Text>
          <Title level={5}>AI 业务链路分析</Title>
        </div>
        <RobotOutlined className="ai-panel-icon" />
      </div>
      <Segmented
        block
        options={[
          {
            label: selectedIds.length > 1 ? `联合分析 ${selectedIds.length}` : "接口业务",
            value: "endpoint",
            icon: <BranchesOutlined />
          },
          {
            label: "节点影响",
            value: "node",
            icon: <ThunderboltOutlined />,
            disabled: !selectedNodeId
          }
        ]}
        value={analysis?.scopeType === "NODE_IMPACT" ? "node" : "endpoint"}
        onChange={(value) =>
          value === "node" ? runNodeAnalysis() : runEndpointAnalysis()
        }
      />
      <Space wrap>
        <Button
          type="primary"
          icon={<RobotOutlined />}
          disabled={!selectedIds.length}
          loading={loading}
          onClick={runEndpointAnalysis}
        >
          {selectedIds.length > 1 ? "还原联合业务流程" : "分析接口业务"}
        </Button>
        {selectedNodeId && (
          <Button
            icon={<ThunderboltOutlined />}
            loading={loading}
            onClick={runNodeAnalysis}
          >
            分析业务影响
          </Button>
        )}
        {analysis && (
          <Button
            type="text"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => void regenerate()}
          >
            重新生成
          </Button>
        )}
      </Space>
      {error && <Alert type="error" showIcon message={error} />}
      <Spin spinning={loading} wrapperClassName="ai-analysis-spinner">
        {!result ? (
          <div className="ai-analysis-empty">
            <Empty
              image={<RobotOutlined className="empty-icon" />}
              description={
                selectedIds.length
                  ? "点击分析，系统将把技术调用链还原为业务流程"
                  : "先从左侧选择接口"
              }
            />
          </div>
        ) : (
          <>
            <div className="ai-analysis-meta">
              <Space size={5} wrap>
                <Tag color="purple">{analysis.provider}</Tag>
                <Tag>{analysis.model}</Tag>
                {analysis.cached && <Tag color="green">缓存命中</Tag>}
                {analysis.stale && <Tag color="gold">扫描后已过期</Tag>}
                {analysis.invalidReferenceCount > 0 && (
                  <Tag color="orange">
                    已过滤 {analysis.invalidReferenceCount} 个无效引用
                  </Tag>
                )}
              </Space>
            </div>
            <Tabs
              className="ai-analysis-tabs"
              size="small"
              activeKey={activeTab}
              items={tabs}
              onChange={setActiveTab}
            />
          </>
        )}
      </Spin>
    </div>
  );
}
