import * as d3 from "d3";
import { useEffect, useMemo, useRef } from "react";

import type { GraphEdge, GraphNode } from "../types/graph";
import {
  layoutGraph,
  NODE_HEIGHT,
  NODE_WIDTH,
  type NodePosition,
} from "../utils/graphLayout";

interface UseD3GraphOptions {
  svgRef: React.RefObject<SVGSVGElement | null>;
  nodes: GraphNode[];
  edges: GraphEdge[];
  roots: string[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  highlightedNodeIds: string[];
  highlightedEdgeIds: string[];
  layoutVersion: number;
  onNodeClick: (nodeId: string) => void;
  onNodeToggle: (node: GraphNode) => void;
  onEdgeClick: (edgeId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  API: "#8f7df7",
  ROUTE_FUNCTION: "#5aa9fa",
  SERVICE: "#34c99b",
  REPOSITORY: "#f0ad4e",
  DATABASE_OPERATION: "#e8875b",
  DATABASE_TABLE: "#e36a82",
  REDIS: "#ef5b64",
  EXTERNAL_HTTP: "#4ec7d3",
  PYDANTIC_MODEL: "#ac77e8",
  UNRESOLVED: "#697181",
};

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function edgePath(
  edge: GraphEdge,
  positions: Map<string, NodePosition>,
): string {
  const source = positions.get(edge.source);
  const target = positions.get(edge.target);
  if (!source || !target) {
    return "";
  }
  const x1 = source.x + NODE_WIDTH;
  const y1 = source.y + NODE_HEIGHT / 2;
  const x2 = target.x;
  const y2 = target.y + NODE_HEIGHT / 2;
  const bend = Math.max(42, Math.abs(x2 - x1) * 0.45);
  return `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`;
}

export function useD3Graph({
  svgRef,
  nodes,
  edges,
  roots,
  selectedNodeId,
  selectedEdgeId,
  highlightedNodeIds,
  highlightedEdgeIds,
  layoutVersion,
  onNodeClick,
  onNodeToggle,
  onEdgeClick,
}: UseD3GraphOptions) {
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const viewportRef = useRef<SVGGElement | null>(null);
  const positionsRef = useRef<Map<string, NodePosition>>(new Map());

  const visibleIds = useMemo(
    () => new Set(nodes.map((node) => node.id)),
    [nodes],
  );
  const visibleEdges = useMemo(
    () =>
      edges.filter(
        (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
      ),
    [edges, visibleIds],
  );

  useEffect(() => {
    const svgElement = svgRef.current;
    if (!svgElement) {
      return;
    }
    const svg = d3.select(svgElement);
    svg.selectAll("*").remove();
    const defs = svg.append("defs");
    defs
      .append("marker")
      .attr("id", "graph-arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 10)
      .attr("refY", 0)
      .attr("markerWidth", 7)
      .attr("markerHeight", 7)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#596274");
    const viewport = svg.append("g").attr("class", "graph-viewport");
    viewport.append("g").attr("class", "graph-edges");
    viewport.append("g").attr("class", "graph-edge-labels");
    viewport.append("g").attr("class", "graph-nodes");
    viewportRef.current = viewport.node();
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.25, 2.4])
      .on("zoom", (event) => viewport.attr("transform", event.transform));
    svg.call(zoom).on("dblclick.zoom", null);
    zoomRef.current = zoom;
  }, [svgRef]);

  useEffect(() => {
    const svgElement = svgRef.current;
    const viewportElement = viewportRef.current;
    if (!svgElement || !viewportElement) {
      return;
    }
    const viewport = d3.select(viewportElement);
    const positions = layoutGraph(nodes, visibleEdges, roots);
    positionsRef.current = positions;
    const aiNodeIds = new Set(highlightedNodeIds);
    const aiEdgeIds = new Set(highlightedEdgeIds);
    const relatedIds = new Set<string>();
    if (selectedNodeId) {
      relatedIds.add(selectedNodeId);
      const queue = [selectedNodeId];
      while (queue.length) {
        const current = queue.shift()!;
        visibleEdges.forEach((edge) => {
          const neighbor =
            edge.source === current
              ? edge.target
              : edge.target === current
                ? edge.source
                : null;
          if (neighbor && !relatedIds.has(neighbor)) {
            relatedIds.add(neighbor);
            queue.push(neighbor);
          }
        });
      }
    }
    const edgeIsRelated = (edge: GraphEdge) => {
      if (!selectedNodeId) {
        return true;
      }
      return relatedIds.has(edge.source) && relatedIds.has(edge.target);
    };

    const redrawEdges = () => {
      viewport
        .select<SVGGElement>(".graph-edges")
        .selectAll<SVGPathElement, GraphEdge>("path")
        .attr("d", (edge) => edgePath(edge, positionsRef.current));
      viewport
        .select<SVGGElement>(".graph-edge-labels")
        .selectAll<SVGTextElement, GraphEdge>("text")
        .attr("x", (edge) => {
          const source = positionsRef.current.get(edge.source);
          const target = positionsRef.current.get(edge.target);
          return source && target ? (source.x + NODE_WIDTH + target.x) / 2 : 0;
        })
        .attr("y", (edge) => {
          const source = positionsRef.current.get(edge.source);
          const target = positionsRef.current.get(edge.target);
          return source && target
            ? (source.y + target.y + NODE_HEIGHT) / 2 - 7
            : 0;
        });
    };

    const edgeSelection = viewport
      .select<SVGGElement>(".graph-edges")
      .selectAll<SVGPathElement, GraphEdge>("path")
      .data(visibleEdges, (edge) => edge.id);
    edgeSelection
      .exit()
      .transition()
      .duration(180)
      .style("opacity", 0)
      .remove();
    const edgeEnter = edgeSelection
      .enter()
      .append("path")
      .attr("class", "graph-edge")
      .attr("marker-end", "url(#graph-arrow)")
      .style("opacity", 0)
      .on("click", (event, edge) => {
        event.stopPropagation();
        onEdgeClick(edge.id);
      });
    edgeEnter
      .merge(edgeSelection)
      .classed("selected", (edge) => edge.id === selectedEdgeId)
      .classed("ai-highlighted", (edge) => aiEdgeIds.has(edge.id))
      .classed("low-confidence", (edge) =>
        ["MEDIUM", "LOW"].includes(edge.confidence),
      )
      .style("opacity", (edge) => {
        if (!selectedNodeId) {
          return 1;
        }
        return edgeIsRelated(edge) ? 1 : 0.18;
      })
      .attr("d", (edge) => edgePath(edge, positions))
      .transition()
      .duration(260)
      .style("opacity", (edge) => {
        if (!selectedNodeId) {
          return 1;
        }
        return edgeIsRelated(edge) ? 1 : 0.18;
      });

    const labelSelection = viewport
      .select<SVGGElement>(".graph-edge-labels")
      .selectAll<SVGTextElement, GraphEdge>("text")
      .data(visibleEdges, (edge) => edge.id);
    labelSelection.exit().remove();
    labelSelection
      .enter()
      .append("text")
      .attr("class", "graph-edge-label")
      .attr("text-anchor", "middle")
      .on("click", (event, edge) => {
        event.stopPropagation();
        onEdgeClick(edge.id);
      })
      .merge(labelSelection)
      .text((edge) => edge.relationType)
      .style("opacity", (edge) => {
        if (!selectedNodeId) {
          return 1;
        }
        return edgeIsRelated(edge) ? 1 : 0.14;
      });

    const nodeSelection = viewport
      .select<SVGGElement>(".graph-nodes")
      .selectAll<SVGGElement, GraphNode>("g.graph-node")
      .data(nodes, (node) => node.id);
    nodeSelection
      .exit()
      .transition()
      .duration(180)
      .style("opacity", 0)
      .remove();
    const nodeEnter = nodeSelection
      .enter()
      .append("g")
      .attr("class", "graph-node")
      .style("opacity", 0)
      .attr("tabindex", 0)
      .attr("role", "button")
      .on("click", (event, node) => {
        event.stopPropagation();
        onNodeClick(node.id);
      })
      .on("dblclick", (event, node) => {
        event.stopPropagation();
        onNodeToggle(node);
      })
      .on("keydown", (event, node) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onNodeClick(node.id);
        }
      });
    nodeEnter
      .append("rect")
      .attr("class", "graph-node-card")
      .attr("width", NODE_WIDTH)
      .attr("height", NODE_HEIGHT)
      .attr("rx", 12);
    nodeEnter
      .append("rect")
      .attr("class", "graph-node-accent")
      .attr("width", 4)
      .attr("height", NODE_HEIGHT - 16)
      .attr("x", 8)
      .attr("y", 8)
      .attr("rx", 2);
    nodeEnter
      .append("text")
      .attr("class", "graph-node-type")
      .attr("x", 22)
      .attr("y", 19);
    nodeEnter
      .append("text")
      .attr("class", "graph-node-title")
      .attr("x", 22)
      .attr("y", 39);
    nodeEnter
      .append("text")
      .attr("class", "graph-node-subtitle")
      .attr("x", 22)
      .attr("y", 56);
    nodeEnter
      .append("text")
      .attr("class", "graph-node-count")
      .attr("x", NODE_WIDTH - 14)
      .attr("y", 20)
      .attr("text-anchor", "end");

    const mergedNodes = nodeEnter.merge(nodeSelection);
    mergedNodes
      .classed("selected", (node) => node.id === selectedNodeId)
      .classed("ai-highlighted", (node) => aiNodeIds.has(node.id))
      .classed("shared", (node) => node.shared)
      .classed("dimmed", (node) =>
        Boolean(selectedNodeId && !relatedIds.has(node.id)),
      )
      .attr("aria-label", (node) => `${node.type} ${node.name}`)
      .transition()
      .duration(280)
      .style("opacity", 1)
      .attr("transform", (node) => {
        const position = positions.get(node.id) ?? { x: 0, y: 0 };
        return `translate(${position.x},${position.y})`;
      });
    mergedNodes
      .select<SVGRectElement>(".graph-node-accent")
      .attr("fill", (node) => TYPE_COLORS[node.type] ?? "#7e8798");
    mergedNodes
      .select<SVGTextElement>(".graph-node-type")
      .text((node) => node.type.replaceAll("_", " "));
    mergedNodes
      .select<SVGTextElement>(".graph-node-title")
      .text((node) => truncate(node.name, 27));
    mergedNodes
      .select<SVGTextElement>(".graph-node-subtitle")
      .text((node) => truncate(node.qualifiedName, 31));
    mergedNodes
      .select<SVGTextElement>(".graph-node-count")
      .text((node) =>
        node.hasChildren
          ? `${node.expanded ? "−" : "+"}${node.childCount}`
          : "",
      );
    mergedNodes.call(
      d3
        .drag<SVGGElement, GraphNode>()
        .on("start", function () {
          d3.select(this).raise().classed("dragging", true);
        })
        .on("drag", function (event, node) {
          const position = positionsRef.current.get(node.id);
          if (!position) {
            return;
          }
          position.x += event.dx;
          position.y += event.dy;
          d3.select(this).attr(
            "transform",
            `translate(${position.x},${position.y})`,
          );
          redrawEdges();
        })
        .on("end", function () {
          d3.select(this).classed("dragging", false);
        }),
    );
    redrawEdges();

    d3.select(svgElement).on("click", () => {
      onNodeClick("");
    });
  }, [
    edges,
    highlightedEdgeIds,
    highlightedNodeIds,
    layoutVersion,
    nodes,
    onEdgeClick,
    onNodeClick,
    onNodeToggle,
    roots,
    selectedEdgeId,
    selectedNodeId,
    svgRef,
    visibleEdges,
  ]);

  const controls = useMemo(
    () => ({
      zoomIn: () => {
        if (svgRef.current && zoomRef.current) {
          d3.select(svgRef.current)
            .transition()
            .call(zoomRef.current.scaleBy, 1.25);
        }
      },
      zoomOut: () => {
        if (svgRef.current && zoomRef.current) {
          d3.select(svgRef.current)
            .transition()
            .call(zoomRef.current.scaleBy, 0.8);
        }
      },
      center: () => {
        if (svgRef.current && zoomRef.current) {
          d3.select(svgRef.current)
            .transition()
            .call(zoomRef.current.transform, d3.zoomIdentity);
        }
      },
      fit: () => {
        const svg = svgRef.current;
        if (!svg || !zoomRef.current) {
          return;
        }
        const positions = [...positionsRef.current.values()];
        if (!positions.length) {
          return;
        }
        const minX = Math.min(...positions.map((position) => position.x));
        const minY = Math.min(...positions.map((position) => position.y));
        const maxX = Math.max(...positions.map((position) => position.x));
        const maxY = Math.max(...positions.map((position) => position.y));
        const bounds = {
          x: minX,
          y: minY,
          width: maxX - minX + NODE_WIDTH,
          height: maxY - minY + NODE_HEIGHT,
        };
        const width = svg.clientWidth;
        const height = svg.clientHeight;
        const scale = Math.min(
          1.25,
          0.82 / Math.max(bounds.width / width, bounds.height / height),
        );
        const transform = d3.zoomIdentity
          .translate(
            width / 2 - scale * (bounds.x + bounds.width / 2),
            height / 2 - scale * (bounds.y + bounds.height / 2),
          )
          .scale(scale);
        d3.select(svg)
          .transition()
          .duration(320)
          .call(zoomRef.current.transform, transform);
      },
    }),
    [svgRef],
  );

  return controls;
}
