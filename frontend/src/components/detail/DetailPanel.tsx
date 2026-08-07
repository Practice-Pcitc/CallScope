import {
  CodeOutlined,
  FileTextOutlined,
  LinkOutlined,
  NodeIndexOutlined,
  ProfileOutlined
} from "@ant-design/icons";
import {
  Descriptions,
  Divider,
  Empty,
  Space,
  Spin,
  Tag,
  Typography
} from "antd";

import { useEndpointStore } from "../../stores/endpointStore";
import { useGraphStore } from "../../stores/graphStore";
import type { Endpoint } from "../../types/endpoint";

const { Paragraph, Text, Title } = Typography;

function metadataText(
  metadata: Record<string, unknown>,
  key: string
): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function metadataList(
  metadata: Record<string, unknown>,
  key: string
): string[] {
  const value = metadata[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function BusinessLogic({
  metadata,
  fallback
}: {
  metadata: Record<string, unknown>;
  fallback: string;
}) {
  const logic = metadataText(metadata, "businessLogic") ?? fallback;
  const steps = metadataList(metadata, "businessSteps");

  return (
    <>
      <Divider orientation="left">
        <ProfileOutlined /> 业务逻辑
      </Divider>
      <div className="business-logic-card">
        <Paragraph>{logic}</Paragraph>
        {steps.length > 0 && (
          <ol className="business-step-list">
            {steps.map((step, index) => (
              <li key={`${step}-${index}`}>
                <span>{index + 1}</span>
                <Text>{step}</Text>
              </li>
            ))}
          </ol>
        )}
      </div>
    </>
  );
}

function EndpointDetail({ endpoint }: { endpoint: Endpoint }) {
  const packageName = metadataText(endpoint.metadata, "packageName");
  const controllerClass = metadataText(endpoint.metadata, "controllerClass");
  const framework = metadataText(endpoint.metadata, "framework");

  return (
    <>
      <Space size={8} wrap>
        <Tag color="purple">{endpoint.httpMethod}</Tag>
        {endpoint.tags.map((tag) => (
          <Tag key={tag}>{tag}</Tag>
        ))}
      </Space>
      <Title level={4} className="endpoint-detail-path">
        {endpoint.path}
      </Title>
      <Paragraph type="secondary">
        {endpoint.summary ?? "该接口没有 summary 或 docstring。"}
      </Paragraph>
      <Descriptions column={1} size="small" colon={false}>
        <Descriptions.Item label="业务分类">
          <Tag color="geekblue">{endpoint.moduleName}</Tag>
        </Descriptions.Item>
        {controllerClass && (
          <Descriptions.Item label="Controller">
            <Text copyable>{controllerClass}</Text>
          </Descriptions.Item>
        )}
        {packageName && (
          <Descriptions.Item label="包路径">
            <Text copyable>{packageName}</Text>
          </Descriptions.Item>
        )}
        {framework && (
          <Descriptions.Item label="框架">
            <Tag>{framework}</Tag>
          </Descriptions.Item>
        )}
        <Descriptions.Item label="处理方法">
          <Text code>{endpoint.functionName}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="文件">
          <Text copyable>
            {endpoint.filePath}:{endpoint.startLine}-{endpoint.endLine}
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="返回">
          {endpoint.responseType ?? "未声明"}
        </Descriptions.Item>
      </Descriptions>

      <BusinessLogic
        metadata={endpoint.metadata}
        fallback={
          endpoint.summary
            ? `${endpoint.summary}。`
            : `处理 ${endpoint.moduleName} 相关请求并返回业务结果。`
        }
      />

      <Divider orientation="left">输入参数</Divider>
      {endpoint.parameters.length === 0 ? (
        <Text type="secondary">无参数</Text>
      ) : (
        <div className="parameter-list">
          {endpoint.parameters.map((parameter) => (
            <div key={parameter.name}>
              <div>
                <Text strong>{parameter.name}</Text>
                <Tag>{parameter.location}</Tag>
                {parameter.required && <Tag color="red">必填</Tag>}
              </div>
              <Text type="secondary">{parameter.type ?? "未声明类型"}</Text>
            </div>
          ))}
        </div>
      )}

      <Divider orientation="left">依赖与协作</Divider>
      {endpoint.dependencies.length === 0 ? (
        <Text type="secondary">
          {framework === "spring"
            ? "Spring 下游协作请查看中间调用链与节点详情"
            : "无 Depends 依赖"}
        </Text>
      ) : (
        <div className="dependency-list">
          {endpoint.dependencies.map((dependency, index) => (
            <div key={`${dependency.providerExpression ?? "unknown"}-${index}`}>
              <Text code>
                {dependency.resolvedQualifiedName ??
                  dependency.providerExpression ??
                  "未解析"}
              </Text>
              <Tag color={dependency.confidence === "CONFIRMED" ? "green" : "gold"}>
                {dependency.confidence}
              </Tag>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export function DetailPanel() {
  const endpoints = useEndpointStore((state) => state.endpoints);
  const activeEndpointId = useEndpointStore((state) => state.activeEndpointId);
  const endpoint = endpoints.find((item) => item.id === activeEndpointId);
  const {
    selectedNodeId,
    selectedEdgeId,
    selectedNodeDetail,
    selectedSource,
    selectedRelationDetail,
    detailLoading
  } = useGraphStore();

  const showEndpoint =
    endpoint && (!selectedNodeId || selectedNodeDetail?.type === "API");

  return (
    <div className="panel-content detail-panel">
      <div className="panel-heading">
        <div>
          <Text className="eyebrow">INSPECTOR</Text>
          <Title level={5}>节点与代码证据</Title>
        </div>
        {selectedNodeDetail && <Tag>{selectedNodeDetail.type}</Tag>}
      </div>

      <Spin spinning={detailLoading} wrapperClassName="detail-spinner">
        <div className="endpoint-detail-content">
          {showEndpoint && <EndpointDetail endpoint={endpoint} />}

          {!showEndpoint && selectedNodeDetail && (
            <>
              <Space size={8} wrap>
                <Tag color={selectedNodeDetail.shared ? "magenta" : "blue"}>
                  {selectedNodeDetail.type}
                </Tag>
                {selectedNodeDetail.shared && <Tag color="magenta">公共节点</Tag>}
              </Space>
              <Title level={4} className="endpoint-detail-path">
                {selectedNodeDetail.name}
              </Title>
              <Paragraph type="secondary" copyable>
                {selectedNodeDetail.qualifiedName}
              </Paragraph>
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label="签名">
                  <Text code>{selectedNodeDetail.signature ?? "未声明"}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="文件">
                  <Text copyable>
                    {selectedNodeDetail.filePath ?? "无源码文件"}
                    {selectedNodeDetail.startLine
                      ? `:${selectedNodeDetail.startLine}-${selectedNodeDetail.endLine}`
                      : ""}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="子节点">
                  {selectedNodeDetail.childCount}
                </Descriptions.Item>
              </Descriptions>

              <BusinessLogic
                metadata={selectedNodeDetail.metadata}
                fallback={`${selectedNodeDetail.name} 执行业务处理；可结合下游调用与源码查看完整逻辑。`}
              />

              <Divider orientation="left">
                <NodeIndexOutlined /> 调用关系
              </Divider>
              <div className="relation-summary">
                <div>
                  <Text strong>{selectedNodeDetail.upstream.length}</Text>
                  <Text type="secondary">上游</Text>
                </div>
                <div>
                  <Text strong>{selectedNodeDetail.downstream.length}</Text>
                  <Text type="secondary">下游</Text>
                </div>
              </div>
              {selectedNodeDetail.downstream.length > 0 && (
                <div className="call-step-list">
                  {selectedNodeDetail.downstream.map((edge, index) => (
                    <div key={edge.id}>
                      <span>{index + 1}</span>
                      <div>
                        <Text>{edge.relationType}</Text>
                        <Text type="secondary">
                          {metadataText(edge.metadata, "targetQualifiedName") ??
                            metadataText(edge.metadata, "targetName") ??
                            edge.evidence ??
                            edge.target}
                        </Text>
                        {edge.evidence && (
                          <Text type="secondary" className="call-evidence" ellipsis>
                            {edge.evidence}
                          </Text>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <Divider orientation="left">
                <CodeOutlined /> 源码
              </Divider>
              <div className="source-location">
                <FileTextOutlined />
                <Text copyable>
                  {selectedSource?.filePath ?? "无源码位置"}
                  {selectedSource?.startLine ? `:${selectedSource.startLine}` : ""}
                </Text>
              </div>
              <pre className="source-code">
                <code>
                  {selectedSource?.source ??
                    selectedNodeDetail.sourceExcerpt ??
                    "没有可用源码片段"}
                </code>
              </pre>
            </>
          )}

          {selectedEdgeId && selectedRelationDetail && (
            <>
              <Space size={8}>
                <Tag color="cyan">{selectedRelationDetail.relationType}</Tag>
                <Tag
                  color={
                    selectedRelationDetail.confidence === "CONFIRMED"
                      ? "green"
                      : selectedRelationDetail.confidence === "HIGH"
                        ? "blue"
                        : "gold"
                  }
                >
                  {selectedRelationDetail.confidence}
                </Tag>
              </Space>
              <Title level={4} className="endpoint-detail-path">
                关系证据
              </Title>
              <div className="relation-route">
                <Text>{selectedRelationDetail.sourceNode.name}</Text>
                <LinkOutlined />
                <Text>{selectedRelationDetail.targetNode.name}</Text>
              </div>
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label="文件">
                  <Text copyable>
                    {selectedRelationDetail.filePath ?? "无"}
                    {selectedRelationDetail.lineNumber
                      ? `:${selectedRelationDetail.lineNumber}`
                      : ""}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
              <Divider orientation="left">调用证据</Divider>
              <pre className="source-code">
                <code>{selectedRelationDetail.evidence ?? "没有代码证据"}</code>
              </pre>
            </>
          )}

          {!endpoint && !selectedNodeId && !selectedEdgeId && (
            <div className="detail-empty">
              <Empty
                image={<FileTextOutlined className="empty-icon" />}
                description="选择接口、节点或关系查看详情"
              />
            </div>
          )}
        </div>
      </Spin>
    </div>
  );
}
