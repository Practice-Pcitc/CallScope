import {
  AimOutlined,
  CompressOutlined,
  MinusOutlined,
  PlusOutlined,
  ReloadOutlined
} from "@ant-design/icons";
import { Alert, Button, Empty, Space, Spin, Switch, Tooltip, Typography } from "antd";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useParams } from "react-router-dom";

import { useD3Graph } from "../../hooks/useD3Graph";
import { useEndpointStore } from "../../stores/endpointStore";
import { useGraphStore } from "../../stores/graphStore";
import type { GraphNode } from "../../types/graph";

const { Text, Title } = Typography;

export function GraphCanvas() {
  const { projectId } = useParams();
  const svgRef = useRef<SVGSVGElement>(null);
  const selectedIds = useEndpointStore((state) => state.selectedIds);
  const {
    roots,
    nodesById,
    edgesById,
    visibleNodeIds,
    selectedNodeId,
    selectedEdgeId,
    aiHighlightedNodeIds,
    aiHighlightedEdgeIds,
    loading,
    error,
    includeLowerConfidence,
    layoutVersion,
    loadForEndpoints,
    expandNode,
    collapseNode,
    selectNode,
    selectEdge,
    setIncludeLowerConfidence,
    requestLayout
  } = useGraphStore();

  useEffect(() => {
    if (projectId) {
      void loadForEndpoints(projectId, selectedIds);
    }
  }, [includeLowerConfidence, loadForEndpoints, projectId, selectedIds]);

  const nodes = useMemo(
    () =>
      visibleNodeIds
        .map((id) => nodesById[id])
        .filter((node): node is GraphNode => Boolean(node)),
    [nodesById, visibleNodeIds]
  );
  const visible = useMemo(() => new Set(visibleNodeIds), [visibleNodeIds]);
  const edges = useMemo(
    () =>
      Object.values(edgesById).filter(
        (edge) => visible.has(edge.source) && visible.has(edge.target)
      ),
    [edgesById, visible]
  );
  const handleNodeClick = useCallback(
    (nodeId: string) => void selectNode(nodeId || null),
    [selectNode]
  );
  const handleNodeToggle = useCallback(
    (node: GraphNode) => {
      if (node.expanded) {
        collapseNode(node.id);
      } else {
        void expandNode(node.id);
      }
    },
    [collapseNode, expandNode]
  );
  const handleEdgeClick = useCallback(
    (edgeId: string) => void selectEdge(edgeId),
    [selectEdge]
  );
  const controls = useD3Graph({
    svgRef,
    nodes,
    edges,
    roots,
    selectedNodeId,
    selectedEdgeId,
    highlightedNodeIds: aiHighlightedNodeIds,
    highlightedEdgeIds: aiHighlightedEdgeIds,
    layoutVersion,
    onNodeClick: handleNodeClick,
    onNodeToggle: handleNodeToggle,
    onEdgeClick: handleEdgeClick
  });

  useEffect(() => {
    if (nodes.length) {
      const timer = window.setTimeout(controls.fit, 40);
      return () => window.clearTimeout(timer);
    }
  }, [controls, layoutVersion, nodes.length]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !nodes.length) {
      return;
    }
    let timer: number | undefined;
    const observer = new ResizeObserver(() => {
      if (timer) {
        window.clearTimeout(timer);
      }
      timer = window.setTimeout(controls.fit, 80);
    });
    observer.observe(svg);
    return () => {
      observer.disconnect();
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [controls, nodes.length]);

  return (
    <div className="graph-canvas">
      <div className="graph-toolbar">
        <div>
          <Text className="eyebrow">CALL GRAPH</Text>
          <Title level={5}>接口调用拓扑</Title>
        </div>
        <Space size={4}>
          <Tooltip title="显示 Medium / Low 关系">
            <Space size={5}>
              <Text type="secondary" className="confidence-label">
                全部置信度
              </Text>
              <Switch
                size="small"
                checked={includeLowerConfidence}
                onChange={setIncludeLowerConfidence}
              />
            </Space>
          </Tooltip>
          <Tooltip title="放大">
            <Button type="text" icon={<PlusOutlined />} onClick={controls.zoomIn} />
          </Tooltip>
          <Tooltip title="缩小">
            <Button type="text" icon={<MinusOutlined />} onClick={controls.zoomOut} />
          </Tooltip>
          <Tooltip title="适配画布">
            <Button type="text" icon={<CompressOutlined />} onClick={controls.fit} />
          </Tooltip>
          <Tooltip title="回到原点">
            <Button type="text" icon={<AimOutlined />} onClick={controls.center} />
          </Tooltip>
          <Tooltip title="重新布局">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={requestLayout}
            />
          </Tooltip>
        </Space>
      </div>

      <div className="graph-stage">
        <svg
          ref={svgRef}
          className="graph-svg"
          role="img"
          aria-label="接口调用拓扑图"
        />
        <Spin spinning={loading} className="graph-loading" />
        {error && (
          <Alert
            className="graph-error"
            type="error"
            showIcon
            message="拓扑加载失败"
            description={error}
          />
        )}
        {!loading && nodes.length === 0 && (
          <div className="graph-empty">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                selectedIds.length
                  ? "当前接口没有可展示的拓扑，请重新扫描项目"
                  : "从左侧选择一个或多个接口开始探索"
              }
            />
          </div>
        )}
        {nodes.length > 0 && (
          <div className="graph-legend" aria-label="节点图例">
            <span><i className="legend-api" />API</span>
            <span><i className="legend-service" />Service</span>
            <span><i className="legend-repository" />Repository</span>
            <span><i className="legend-resource" />外部资源</span>
            <Text type="secondary">双击节点展开 / 折叠</Text>
          </div>
        )}
      </div>

      <div className="graph-statusbar">
        <Space split={<span className="status-divider" />}>
          <Text type="secondary">{selectedIds.length} 个接口入口</Text>
          <Text type="secondary">{nodes.length} 个节点</Text>
          <Text type="secondary">{edges.length} 条关系</Text>
        </Space>
        <Text type="secondary">D3.js · SVG · 按需展开</Text>
      </div>
    </div>
  );
}
