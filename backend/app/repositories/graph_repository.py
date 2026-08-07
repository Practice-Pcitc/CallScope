from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.code_node import CodeNode
from app.models.code_relation import CodeRelation
from app.models.endpoint_node import EndpointNode


class GraphRepository:
    """图数据的持久化与按修订版本查询入口。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_nodes(self, nodes: list[CodeNode]) -> None:
        self.session.add_all(nodes)
        self.session.flush()

    def add_relations(self, relations: list[CodeRelation]) -> None:
        self.session.add_all(relations)
        self.session.flush()

    def add_endpoint_nodes(self, mappings: list[EndpointNode]) -> None:
        self.session.add_all(mappings)
        self.session.flush()

    def get_node(
        self,
        *,
        project_id: str,
        revision_id: str,
        node_id: str,
    ) -> CodeNode | None:
        return self.session.scalar(
            select(CodeNode).where(
                CodeNode.id == node_id,
                CodeNode.project_id == project_id,
                CodeNode.scan_revision_id == revision_id,
            )
        )

    def get_relation(
        self,
        *,
        project_id: str,
        revision_id: str,
        relation_id: str,
    ) -> CodeRelation | None:
        return self.session.scalar(
            select(CodeRelation).where(
                CodeRelation.id == relation_id,
                CodeRelation.project_id == project_id,
                CodeRelation.scan_revision_id == revision_id,
            )
        )

    def endpoint_root(
        self,
        *,
        project_id: str,
        revision_id: str,
        endpoint_id: str,
    ) -> CodeNode | None:
        return self.session.scalar(
            select(CodeNode)
            .join(EndpointNode, EndpointNode.node_id == CodeNode.id)
            .where(
                EndpointNode.endpoint_id == endpoint_id,
                CodeNode.project_id == project_id,
                CodeNode.scan_revision_id == revision_id,
            )
        )

    def endpoint_ids_for_nodes(self, node_ids: set[str]) -> list[str]:
        if not node_ids:
            return []
        return list(
            self.session.scalars(
                select(EndpointNode.endpoint_id).where(
                    EndpointNode.node_id.in_(node_ids)
                )
            )
        )

    def nodes_by_ids(
        self,
        *,
        project_id: str,
        revision_id: str,
        node_ids: set[str],
    ) -> list[CodeNode]:
        if not node_ids:
            return []
        return list(
            self.session.scalars(
                select(CodeNode).where(
                    CodeNode.id.in_(node_ids),
                    CodeNode.project_id == project_id,
                    CodeNode.scan_revision_id == revision_id,
                )
            )
        )

    def outgoing(
        self,
        *,
        project_id: str,
        revision_id: str,
        node_ids: set[str],
        confidences: set[str],
    ) -> list[CodeRelation]:
        if not node_ids:
            return []
        return list(
            self.session.scalars(
                select(CodeRelation).where(
                    CodeRelation.project_id == project_id,
                    CodeRelation.scan_revision_id == revision_id,
                    CodeRelation.source_node_id.in_(node_ids),
                    CodeRelation.confidence.in_(confidences),
                )
            )
        )

    def incoming(
        self,
        *,
        project_id: str,
        revision_id: str,
        node_ids: set[str],
        confidences: set[str],
    ) -> list[CodeRelation]:
        if not node_ids:
            return []
        return list(
            self.session.scalars(
                select(CodeRelation).where(
                    CodeRelation.project_id == project_id,
                    CodeRelation.scan_revision_id == revision_id,
                    CodeRelation.target_node_id.in_(node_ids),
                    CodeRelation.confidence.in_(confidences),
                )
            )
        )

    def related(
        self,
        *,
        project_id: str,
        revision_id: str,
        node_id: str,
        confidences: set[str],
    ) -> list[CodeRelation]:
        return list(
            self.session.scalars(
                select(CodeRelation).where(
                    CodeRelation.project_id == project_id,
                    CodeRelation.scan_revision_id == revision_id,
                    CodeRelation.confidence.in_(confidences),
                    or_(
                        CodeRelation.source_node_id == node_id,
                        CodeRelation.target_node_id == node_id,
                    ),
                )
            )
        )
