import type { GraphEdge, GraphNode } from "../types/graph";

export interface NodePosition {
  x: number;
  y: number;
}

export const NODE_WIDTH = 204;
export const NODE_HEIGHT = 66;

export function layoutGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  roots: string[]
): Map<string, NodePosition> {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const ranks = new Map<string, number>();
  const outgoing = new Map<string, string[]>();
  for (const edge of edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      continue;
    }
    outgoing.set(edge.source, [...(outgoing.get(edge.source) ?? []), edge.target]);
  }
  const queue: Array<[string, number]> = roots
    .filter((id) => nodeIds.has(id))
    .map((id) => [id, 0]);
  while (queue.length) {
    const [id, rank] = queue.shift()!;
    if ((ranks.get(id) ?? -1) >= rank) {
      continue;
    }
    ranks.set(id, rank);
    for (const target of outgoing.get(id) ?? []) {
      queue.push([target, Math.min(rank + 1, 8)]);
    }
  }
  nodes.forEach((node) => {
    if (!ranks.has(node.id)) {
      ranks.set(node.id, Math.max(node.depth, 0));
    }
  });
  const columns = new Map<number, GraphNode[]>();
  for (const node of nodes) {
    const rank = ranks.get(node.id) ?? 0;
    columns.set(rank, [...(columns.get(rank) ?? []), node]);
  }
  const positions = new Map<string, NodePosition>();
  for (const [rank, column] of columns) {
    column
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((node, index) => {
        positions.set(node.id, {
          x: 48 + rank * 282,
          y: 48 + index * 106
        });
      });
  }
  return positions;
}
