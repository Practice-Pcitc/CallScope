from __future__ import annotations

import json
import re
import time

from app.llm.base import ProviderResult
from app.llm.exceptions import AIAnalysisError
from app.llm.token_budget import TokenBudget

CONTEXT_PATTERN = re.compile(
    r"CONTEXT_JSON_BEGIN\s*(\{.*?\})\s*CONTEXT_JSON_END",
    re.DOTALL,
)


class GroundedLocalProvider:
    """无外部模型时的可运行证据分析 Provider，不生成白名单外关系。"""

    provider_name = "grounded-local"
    model_name = "grounded-local-v1"

    def generate(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        del system_prompt
        started = time.perf_counter()
        match = CONTEXT_PATTERN.search(user_prompt)
        if not match:
            raise AIAnalysisError("本地 Provider 无法读取结构化 Context")
        context = json.loads(match.group(1))
        result = self._analyze(context)
        content = json.dumps(result, ensure_ascii=False)
        return ProviderResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=TokenBudget.estimate_tokens(user_prompt),
            output_tokens=TokenBudget.estimate_tokens(content),
            latency_ms=int((time.perf_counter() - started) * 1000),
            finish_reason="stop",
            metadata={"mode": "deterministic-evidence"},
        )

    def _analyze(self, context: dict) -> dict:
        return self._business_analyze(context)

    def _legacy_analyze(self, context: dict) -> dict:
        endpoints = context.get("endpoints", [])
        nodes = context.get("nodes", [])
        edges = context.get("edges", [])
        snippets = context.get("source_snippets", [])
        conditions = context.get("conditions", [])
        data_ops = context.get("data_operations", [])
        external_calls = context.get("external_calls", [])
        related = context.get("related_endpoint_candidates", [])
        endpoint_ids = [item["id"] for item in endpoints]
        node_by_id = {item["id"]: item for item in nodes}
        evidence_by_node = {item["node_id"]: item["evidence_id"] for item in snippets}
        edge_by_target = {item["target"]: item for item in edges}

        endpoint_labels = [f"{item['http_method']} {item['path']}" for item in endpoints]
        goal_parts = [
            item.get("summary") or item.get("metadata", {}).get("businessLogic")
            for item in endpoints
        ]
        goal_parts = [str(item) for item in goal_parts if item]
        if len(endpoints) == 1:
            summary = (
                goal_parts[0] if goal_parts else f"分析接口 {endpoint_labels[0]} 的静态业务链路。"
            )
        else:
            summary = (
                f"所选 {len(endpoints)} 个接口的联合链路包含 "
                f"{len(nodes)} 个真实节点和 {len(edges)} 条静态关系。"
            )
        business_goal = (
            "；".join(goal_parts[:3])
            if goal_parts
            else "基于已有调用节点解释请求处理、业务协作和结果返回过程。"
        )

        ordered_nodes = self._ordered_nodes(nodes, edges)
        steps = []
        for index, node in enumerate(ordered_nodes[:24], start=1):
            edge = edge_by_target.get(node["id"])
            evidence_id = evidence_by_node.get(node["id"])
            steps.append(
                {
                    "step": index,
                    "description": self._step_description(node, index),
                    "node_ids": [node["id"]],
                    "edge_ids": [edge["id"]] if edge else [],
                    "endpoint_ids": endpoint_ids if node.get("node_type") == "API" else [],
                    "evidence_ids": [evidence_id] if evidence_id else [],
                    "file_path": node.get("file_path"),
                    "line_number": node.get("start_line"),
                    "confidence": "HIGH",
                    "claim_type": "FACT",
                }
            )

        important_types = {
            "API": "接口入口",
            "SERVICE": "承载主要业务协作",
            "REPOSITORY": "连接持久化能力",
            "DATABASE_OPERATION": "执行数据操作",
            "REDIS": "访问缓存资源",
            "EXTERNAL_HTTP": "调用外部 HTTP 服务",
        }
        key_nodes = []
        for node in ordered_nodes:
            reason = important_types.get(node.get("node_type"))
            if not reason:
                continue
            key_nodes.append(
                {
                    "name": node["name"],
                    "reason": reason,
                    "importance": (
                        "HIGH"
                        if node.get("node_type")
                        in {"API", "SERVICE", "REPOSITORY", "DATABASE_OPERATION"}
                        else "MEDIUM"
                    ),
                    **self._binding(node, evidence_by_node),
                }
            )

        condition_items = [
            {
                "condition": item["expression"],
                "result": (
                    "该分支可能提前终止或改变正常执行路径"
                    if item["kind"] == "ERROR_HANDLING"
                    else "根据条件结果选择后续业务路径"
                ),
                "condition_type": item["kind"],
                "evidence": item["expression"],
                "node_ids": [item["node_id"]],
                "edge_ids": [],
                "endpoint_ids": [],
                "evidence_ids": [item["evidence_id"]],
                "file_path": node_by_id.get(item["node_id"], {}).get("file_path"),
                "line_number": item.get("line_number"),
                "confidence": "HIGH",
                "claim_type": "FACT",
            }
            for item in conditions[:30]
        ]
        exception_items = [
            {
                "exception": self._exception_name(item["expression"]),
                "trigger": item["expression"],
                "impact": "当前分支可能终止后续正常链路",
                "node_ids": [item["node_id"]],
                "edge_ids": [],
                "endpoint_ids": [],
                "evidence_ids": [item["evidence_id"]],
                "file_path": node_by_id.get(item["node_id"], {}).get("file_path"),
                "line_number": item.get("line_number"),
                "confidence": "HIGH",
                "claim_type": "FACT",
            }
            for item in conditions
            if item["kind"] == "ERROR_HANDLING"
        ][:20]
        database_operations = [
            {
                "resource": item["resource"],
                "operation": item["operation"],
                "reason": f"静态节点显示调用 {item['method_name']}",
                "repository_method": item["method_name"],
                "node_ids": [item["node_id"]],
                "edge_ids": [],
                "endpoint_ids": [],
                "evidence_ids": (
                    [evidence_by_node[item["node_id"]]]
                    if item["node_id"] in evidence_by_node
                    else []
                ),
                "file_path": node_by_id.get(item["node_id"], {}).get("file_path"),
                "line_number": node_by_id.get(item["node_id"], {}).get("start_line"),
                "confidence": "MEDIUM",
                "claim_type": "FACT",
            }
            for item in data_ops
        ]
        dependencies = [
            {
                "dependency_type": item["dependency_type"],
                "name": item["name"],
                "purpose": "该资源出现在当前静态调用链中",
                **self._binding(node_by_id[item["node_id"]], evidence_by_node),
            }
            for item in external_calls
            if item["node_id"] in node_by_id
        ]
        related_items = [
            {
                "endpoint_id": item["id"],
                "relation": "MEDIUM",
                "reason": "与当前接口属于相同静态业务分类，需结合共享节点进一步确认",
                "node_ids": [],
                "edge_ids": [],
                "endpoint_ids": [item["id"]],
                "evidence_ids": [],
                "file_path": item.get("file_path"),
                "line_number": item.get("start_line"),
                "confidence": "LOW",
                "claim_type": "INFERENCE",
            }
            for item in related[:12]
        ]
        data_flows = [
            {
                "source": ", ".join(
                    parameter.get("name", "request")
                    for endpoint in endpoints
                    for parameter in endpoint.get("parameters", [])
                )
                or "Request",
                "transformations": [f"经过 {node['name']}" for node in ordered_nodes[1:8]],
                "destination": (data_ops[-1]["resource"] if data_ops else "当前调用链返回值"),
                "result": ", ".join(
                    endpoint.get("response_type") or "UNKNOWN" for endpoint in endpoints
                ),
                "node_ids": [node["id"] for node in ordered_nodes[:8]],
                "edge_ids": [edge["id"] for edge in edges[:8]],
                "endpoint_ids": endpoint_ids,
                "evidence_ids": list(evidence_by_node.values())[:8],
                "file_path": endpoints[0].get("file_path") if endpoints else None,
                "line_number": endpoints[0].get("start_line") if endpoints else None,
                "confidence": "MEDIUM",
                "claim_type": "FACT",
            }
        ]
        risks = self._risks(
            ordered_nodes,
            data_ops,
            external_calls,
            evidence_by_node,
        )
        impacts = [
            {
                "target": f"{endpoint['http_method']} {endpoint['path']}",
                "impact_type": "ENTRY_ENDPOINT",
                "description": "该接口入口包含在当前静态调用子图中",
                "node_ids": [
                    node["id"]
                    for node in nodes
                    if endpoint["id"] in node.get("metadata", {}).get("entryEndpointIds", [])
                ],
                "edge_ids": [],
                "endpoint_ids": [endpoint["id"]],
                "evidence_ids": [],
                "file_path": endpoint.get("file_path"),
                "line_number": endpoint.get("start_line"),
                "confidence": "HIGH",
                "claim_type": "FACT",
            }
            for endpoint in endpoints
        ]
        evidence = [
            {
                "evidence_id": item["evidence_id"],
                "description": f"{item.get('file_path') or '源码'} 的静态源码片段",
                "node_id": item["node_id"],
                "edge_id": None,
                "file_path": item.get("file_path"),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
            }
            for item in snippets
        ]
        return {
            "summary": summary[:1200],
            "business_goal": business_goal[:2000],
            "execution_steps": steps,
            "key_nodes": key_nodes[:20],
            "conditions": condition_items,
            "data_flows": data_flows,
            "database_operations": database_operations,
            "exceptions": exception_items,
            "external_dependencies": dependencies,
            "related_endpoints": related_items,
            "risks": risks,
            "impact_analysis": impacts,
            "inferences": [],
            "evidence": evidence,
            "analysis_scope_note": (
                "上下文已按 Token 预算裁剪。"
                if context.get("context_meta", {}).get("truncated")
                else "分析覆盖当前指定深度内的静态调用子图。"
            ),
        }

    def _business_analyze(self, context: dict) -> dict:
        endpoints = context.get("endpoints", [])
        nodes = context.get("nodes", [])
        edges = context.get("edges", [])
        conditions = context.get("conditions", [])
        data_ops = context.get("data_operations", [])
        external_calls = context.get("external_calls", [])
        related = context.get("related_endpoint_candidates", [])
        ordered_nodes = self._ordered_nodes(nodes, edges)

        endpoint_labels = [f"{item['http_method']} {item['path']}" for item in endpoints]
        summaries = []
        for item in endpoints:
            candidate = str(item.get("summary") or "").strip()
            summaries.append(
                candidate
                if candidate and self._looks_like_business_text(candidate)
                else self._business_capability(item)
            )
        if len(endpoints) == 1:
            business_summary = (
                summaries[0]
                if summaries
                else "该接口用于处理当前业务请求，具体业务目的从当前代码无法完全确认。"
            )
        else:
            business_summary = f"所选 {len(endpoints)} 个接口属于一次联合业务分析。" + (
                f" 已知业务作用包括：{'；'.join(summaries[:3])}。"
                if summaries
                else " 从当前代码无法确认它们是否构成固定的先后流程。"
            )

        business_scenario = (
            "典型使用者和界面入口从当前代码无法确认。"
            "当用户或其他系统需要执行上述业务能力时会调用该接口；"
            "调用前置条件以当前源码中识别出的业务规则为准。"
        )

        rule_groups: dict[str, list[dict]] = {}
        for item in conditions:
            rule, reason, failure = self._business_rule(item["expression"])
            key = f"{rule}|{reason}|{failure}"
            rule_groups.setdefault(key, []).append(item)
        business_rules = []
        for key, group in list(rule_groups.items())[:20]:
            rule, reason, failure = key.split("|", 2)
            business_rules.append(
                {
                    "rule": rule,
                    "reason": reason,
                    "failure_result": failure,
                    "node_ids": list(dict.fromkeys(item["node_id"] for item in group)),
                }
            )

        reads = [item for item in data_ops if item["operation"] == "READ"]
        changes = [item for item in data_ops if item["operation"] in {"WRITE", "UPDATE", "DELETE"}]
        flow: list[dict] = []
        entry_node_ids = [item["id"] for item in ordered_nodes if item["node_type"] == "API"]
        flow.append(
            {
                "step": 1,
                "title": "接收业务请求",
                "description": business_summary,
                "business_meaning": "把用户或其他系统的业务意图交给系统处理。",
                "node_ids": entry_node_ids[:10],
            }
        )
        if business_rules:
            flow.append(
                {
                    "step": len(flow) + 1,
                    "title": "检查业务条件",
                    "description": (
                        f"系统按照源码中识别出的 {len(business_rules)} 项条件，"
                        "确认本次操作是否允许继续。"
                    ),
                    "business_meaning": ("避免不满足条件的请求继续改变业务数据或产生错误结果。"),
                    "node_ids": list(
                        dict.fromkeys(
                            node_id for item in business_rules for node_id in item["node_ids"]
                        )
                    )[:20],
                }
            )
        if reads:
            flow.append(
                {
                    "step": len(flow) + 1,
                    "title": "读取业务信息",
                    "description": ("系统读取完成本次业务判断和结果组装所需的数据。"),
                    "business_meaning": "使用现有业务数据确认当前情况。",
                    "node_ids": list(dict.fromkeys(item["node_id"] for item in reads))[:20],
                }
            )
        if changes:
            operations = {item["operation"] for item in changes}
            action = (
                "新增"
                if operations == {"WRITE"}
                else "删除"
                if operations == {"DELETE"}
                else "修改"
            )
            flow.append(
                {
                    "step": len(flow) + 1,
                    "title": f"{action}业务数据",
                    "description": f"校验通过后，系统{action}与本次操作相关的业务数据。",
                    "business_meaning": "这是本接口对业务状态产生实际影响的核心步骤。",
                    "node_ids": list(dict.fromkeys(item["node_id"] for item in changes))[:20],
                }
            )
        if external_calls:
            flow.append(
                {
                    "step": len(flow) + 1,
                    "title": "完成外部协作",
                    "description": (
                        "系统还需要读取缓存、数据资源或调用外部能力；"
                        "其具体业务含义以当前证据能够确认的范围为限。"
                    ),
                    "business_meaning": "借助当前系统之外的资源完成业务处理。",
                    "node_ids": list(dict.fromkeys(item["node_id"] for item in external_calls))[
                        :20
                    ],
                }
            )
        if len(flow) == 1:
            business_node_ids = [
                item["id"]
                for item in ordered_nodes
                if item["node_type"] not in {"API", "ROUTE_FUNCTION"}
            ]
            flow.append(
                {
                    "step": len(flow) + 1,
                    "title": "完成核心业务处理",
                    "description": (
                        "系统根据当前请求完成对应业务处理；"
                        "更具体的业务动作从当前静态证据无法可靠确认。"
                    ),
                    "business_meaning": "将输入转换为可返回的业务结果。",
                    "node_ids": business_node_ids[:20],
                }
            )
        flow.append(
            {
                "step": len(flow) + 1,
                "title": "返回业务结果",
                "description": (
                    "系统向调用方返回本次查询或处理结果，调用方可以据此展示结果或继续后续业务。"
                ),
                "business_meaning": "调用方据此展示结果或继续后续业务。",
                "node_ids": entry_node_ids[:10],
            }
        )

        state_changes = []
        for item in changes:
            operation = item["operation"]
            resource = self._resource_business_name(item["resource"])
            before_after = {
                "WRITE": ("系统中尚无本次新增记录", "新增一份业务记录"),
                "UPDATE": ("保留原有业务状态或内容", "业务状态或内容被更新"),
                "DELETE": ("系统中存在目标业务记录", "目标业务记录被删除"),
            }[operation]
            state_changes.append(
                {
                    "business_object": resource,
                    "before": before_after[0],
                    "after": before_after[1],
                    "node_ids": [item["node_id"]],
                }
            )

        failure_flows = []
        for index, item in enumerate(
            [rule for rule in business_rules if rule["failure_result"]][:15]
        ):
            failure_flows.append(
                {
                    "scenario": f"业务条件未满足 {index + 1}",
                    "reason": item["rule"],
                    "business_impact": item["failure_result"],
                    "node_ids": item["node_ids"],
                }
            )

        raw_inputs = list(
            dict.fromkeys(
                str(parameter.get("name") or "未命名输入")
                for endpoint in endpoints
                for parameter in endpoint.get("parameters", [])
            )
        )
        inputs = list(dict.fromkeys(self._business_input_name(item) for item in raw_inputs))
        outputs = list(dict.fromkeys(self._business_output(endpoint) for endpoint in endpoints))
        data_flow = {
            "inputs": inputs or ["调用方没有提供额外业务信息"],
            "reads": list(
                dict.fromkeys(self._resource_business_name(item["resource"]) for item in reads)
            ),
            "changes": list(
                dict.fromkeys(
                    {
                        "WRITE": "新增",
                        "UPDATE": "修改",
                        "DELETE": "删除",
                    }.get(item["operation"], "处理")
                    + self._resource_business_name(item["resource"])
                    for item in changes
                )
            ),
            "outputs": outputs or ["本次业务处理结果"],
        }

        object_names: list[str] = []
        for endpoint in endpoints:
            object_names.extend(endpoint.get("tags", []))
            module = str(endpoint.get("module_name") or "").strip()
            if module:
                object_names.append(self._business_object_name(module.split(".")[-1]))
        object_names.extend(
            self._resource_business_name(item["resource"])
            for item in data_ops
            if item["resource"] != "UNKNOWN_TABLE"
        )
        core_objects = [
            {
                "name": name,
                "role": "本接口读取、判断或改变的核心业务对象；更具体含义从当前代码无法确认。",
            }
            for name in list(dict.fromkeys(object_names))[:10]
            if name
        ]

        key_nodes = []
        for item in business_rules[:8]:
            key_nodes.append(
                {
                    "name": "业务条件检查",
                    "business_importance": "决定本次业务是否能够继续。",
                    "reason": item["rule"],
                    "node_ids": item["node_ids"],
                }
            )
        for item in changes[:8]:
            key_nodes.append(
                {
                    "name": "业务数据变更",
                    "business_importance": "直接改变系统中的业务结果。",
                    "reason": (f"静态证据显示存在 {item['operation']} 类型的数据操作。"),
                    "node_ids": [item["node_id"]],
                }
            )

        related_endpoints = [
            {
                "endpoint_id": item["id"],
                "relationship": "候选业务关联",
                "business_reason": (
                    "该接口与当前接口属于相同业务分类；当前静态证据不足以确认固定调用顺序。"
                ),
            }
            for item in related[:12]
        ]

        risks = []
        write_nodes = [item["node_id"] for item in changes]
        external_nodes = [
            item["node_id"] for item in external_calls if item["dependency_type"] == "EXTERNAL_API"
        ]
        if write_nodes and external_nodes:
            risks.append(
                {
                    "title": "业务数据变更与外部协作一致性",
                    "description": (
                        "从当前链路来看，系统既会改变业务数据，也会调用外部能力。"
                        "如果外部调用失败，可能出现两边结果不一致，需要关注事务、"
                        "重试或补偿机制；当前代码证据无法确认这些机制是否完整。"
                    ),
                    "level": "MEDIUM",
                    "node_ids": list(dict.fromkeys(write_nodes + external_nodes))[:20],
                }
            )

        source_files = list(
            dict.fromkeys(
                f"{item['file_path']}:{item.get('start_line') or '?'}-{item.get('end_line') or '?'}"
                for item in nodes
                if item.get("file_path")
            )
        )[:20]
        methods = [
            item["qualified_name"]
            for item in ordered_nodes
            if item["node_type"] in {"ROUTE_FUNCTION", "FUNCTION", "METHOD", "SERVICE"}
        ][:20]
        data_access = [item["method_name"] for item in data_ops if item.get("method_name")][:20]
        return {
            "business_summary": business_summary[:1600],
            "business_scenario": business_scenario,
            "business_flow": flow[:10],
            "business_rules": business_rules,
            "state_changes": state_changes,
            "business_data_flow": data_flow,
            "normal_flow": [item["description"] for item in flow],
            "failure_flows": failure_flows,
            "core_business_objects": core_objects,
            "key_business_nodes": key_nodes[:15],
            "process_position": {
                "position": "UNKNOWN",
                "description": (
                    "从当前静态调用链无法可靠确认该接口处于整个产品流程的开始、中间还是结束位置。"
                ),
            },
            "related_endpoints": related_endpoints,
            "business_risks": risks,
            "technical_reference": {
                "entry": "；".join(endpoint_labels),
                "core_methods": methods,
                "data_access": data_access,
                "source_files": source_files,
            },
        }

    @staticmethod
    def _business_rule(expression: str) -> tuple[str, str, str]:
        lowered = expression.lower()
        if any(token in lowered for token in ("permission", "role", "auth")):
            return (
                "当前操作必须通过权限或身份检查。",
                "避免未授权用户执行受限制的业务操作。",
                "系统拒绝本次请求，业务不会继续。",
            )
        if any(token in lowered for token in ("none", "null", "empty", "exists")):
            return (
                "完成业务所需的目标数据必须存在且有效。",
                "缺少必要数据时无法正确完成后续处理。",
                "流程在数据确认阶段停止，不产生预期业务结果。",
            )
        if "status" in lowered or "state" in lowered:
            return (
                "目标业务对象必须处于允许执行当前操作的状态。",
                "防止在错误阶段重复或越序处理业务对象。",
                "系统保持原有状态并终止本次操作。",
            )
        if any(token in lowered for token in ("amount", "quantity", "count", "num")):
            return (
                "数量或金额必须满足源码中规定的业务范围。",
                "避免产生超出允许范围的业务结果。",
                "系统拒绝继续处理，相关业务数据不会按预期生成或修改。",
            )
        if lowered.startswith(("raise", "throw", "except", "catch")):
            return (
                "业务处理出现异常时必须中止正常流程。",
                "避免异常结果被当作成功结果继续传递。",
                "本次处理失败并返回异常结果；是否回滚数据从当前代码无法确认。",
            )
        return (
            "本次操作必须满足源码中定义的业务判断条件。",
            "该条件用于决定业务流程是否可以继续。",
            "条件不满足时，流程会进入其他分支或提前结束；具体业务原因从当前代码无法确认。",
        )

    @staticmethod
    def _looks_like_business_text(value: str) -> bool:
        technical_markers = (
            "()",
            "service",
            "repository",
            "mapper",
            "controller",
            "returnmodel",
            "selectlist",
            "querywrapper",
            "主要协作",
            "<",
            ">",
            "::",
        )
        lowered = value.lower()
        has_method_call = bool(re.search(r"\b[A-Za-z_$][\w$]*\s*\(", value))
        has_qualified_name = bool(re.search(r"\b[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*){2,}", value))
        return (
            not any(marker in lowered for marker in technical_markers)
            and not has_method_call
            and not has_qualified_name
        )

    @classmethod
    def _business_capability(cls, endpoint: dict) -> str:
        path = str(endpoint.get("path") or "")
        function_name = str(endpoint.get("function_name") or "")
        module_name = str(endpoint.get("module_name") or "")
        source = (
            " ".join(item for item in (module_name.split(".")[-1], function_name) if item)
            or path.rstrip("/").split("/")[-1]
        )
        words = cls._name_words(source)
        action_map = {
            "get": "获取",
            "query": "查询",
            "find": "查询",
            "list": "查询",
            "search": "搜索",
            "create": "创建",
            "add": "新增",
            "save": "保存",
            "update": "修改",
            "edit": "修改",
            "delete": "删除",
            "remove": "删除",
            "check": "检查",
            "validate": "校验",
            "export": "导出",
            "import": "导入",
            "upload": "上传",
            "download": "下载",
            "submit": "提交",
            "approve": "审批",
        }
        action = next(
            (action_map[word] for word in words if word in action_map),
            "处理",
        )
        translated = [
            {
                "abnormal": "异常",
                "trading": "交易",
                "material": "物料",
                "category": "分类",
                "tree": "树形",
                "option": "选项",
                "options": "选项",
                "record": "记录",
                "review": "复核",
                "drawing": "图纸",
                "file": "文件",
                "user": "用户",
                "account": "账户",
                "order": "订单",
                "payment": "支付",
                "task": "任务",
                "status": "状态",
                "detail": "详情",
                "info": "信息",
            }.get(word, "")
            for word in words
            if word not in action_map and word not in {"common", "api", "v1", "by", "id"}
        ]
        object_text = "".join(item for item in translated if item)
        if not object_text:
            return "该接口用于处理当前业务请求。更具体的业务目的从当前代码无法可靠确认。"
        return (
            f"该接口用于{action}{object_text}。"
            "系统完成必要检查和数据处理后返回业务结果；"
            "具体使用角色和页面入口从当前代码无法确认。"
        )

    @classmethod
    def _business_object_name(cls, value: str) -> str:
        words = cls._name_words(value)
        mapping = {
            "abnormal": "异常",
            "trading": "交易",
            "material": "物料",
            "category": "分类",
            "record": "记录",
            "review": "复核",
            "drawing": "图纸",
            "file": "文件",
            "user": "用户",
            "account": "账户",
            "order": "订单",
            "payment": "支付",
            "task": "任务",
        }
        translated = "".join(
            mapping.get(word, "")
            for word in words
            if word not in {"common", "controller", "service", "api"}
        )
        return translated or "当前业务对象（具体名称无法确认）"

    @classmethod
    def _resource_business_name(cls, value: str) -> str:
        if not value or value == "UNKNOWN_TABLE":
            return "与本次操作相关的业务数据"
        translated = cls._business_object_name(value)
        return "与本次操作相关的业务数据" if "具体名称无法确认" in translated else translated

    @classmethod
    def _business_input_name(cls, value: str) -> str:
        words = cls._name_words(value)
        word_set = set(words)
        if "ids" in word_set or (
            "id" in word_set and any(word in word_set for word in ("list", "array"))
        ):
            return "待处理业务对象的标识列表"
        if "id" in word_set:
            return "目标业务对象标识"
        if any(word in word_set for word in ("page", "size", "limit", "offset")):
            return "分页查询条件"
        if "status" in word_set or "state" in word_set:
            return "目标业务状态"
        if "code" in word_set:
            return "业务编码"
        if any(word in word_set for word in ("keyword", "search", "query")):
            return "查询条件"
        if any(word in word_set for word in ("request", "payload", "data", "body")):
            return "调用方提交的业务信息"
        return "调用方提交的业务信息"

    @classmethod
    def _business_output(cls, endpoint: dict) -> str:
        words = set(
            cls._name_words(str(endpoint.get("function_name") or endpoint.get("path") or ""))
        )
        if words & {"get", "query", "find", "list", "search"}:
            return "符合条件的业务数据"
        if words & {"create", "add", "save"}:
            return "业务数据创建结果"
        if words & {"update", "edit", "modify"}:
            return "业务数据修改结果"
        if words & {"delete", "remove"}:
            return "业务数据删除结果"
        if words & {"check", "validate"}:
            return "业务检查结果"
        return "本次业务处理结果"

    @staticmethod
    def _name_words(value: str) -> list[str]:
        normalized = re.sub(r"[^A-Za-z0-9]+", " ", value)
        tokens = re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+",
            normalized,
        )
        return [token.lower() for token in tokens]

    @staticmethod
    def _ordered_nodes(nodes: list[dict], edges: list[dict]) -> list[dict]:
        by_id = {item["id"]: item for item in nodes}
        indegree = {item["id"]: 0 for item in nodes}
        outgoing: dict[str, list[str]] = {}
        for edge in edges:
            if edge["source"] not in by_id or edge["target"] not in by_id:
                continue
            outgoing.setdefault(edge["source"], []).append(edge["target"])
            indegree[edge["target"]] += 1
        queue = [item_id for item_id, degree in indegree.items() if degree == 0]
        ordered = []
        visited = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            ordered.append(by_id[current])
            for target in outgoing.get(current, []):
                indegree[target] -= 1
                if indegree[target] <= 0:
                    queue.append(target)
        ordered.extend(item for item in nodes if item["id"] not in visited)
        return ordered

    @staticmethod
    def _step_description(node: dict, index: int) -> str:
        labels = {
            "API": "接收并路由接口请求",
            "ROUTE_FUNCTION": "进入接口处理方法",
            "SERVICE": "执行业务服务处理",
            "REPOSITORY": "访问持久化仓储",
            "DATABASE_OPERATION": "执行数据库操作",
            "REDIS": "访问 Redis 缓存",
            "EXTERNAL_HTTP": "调用外部 HTTP 服务",
        }
        action = labels.get(node.get("node_type"), "调用链路节点")
        return f"{index}. {action}：{node['name']}"

    @staticmethod
    def _binding(node: dict, evidence_by_node: dict[str, str]) -> dict:
        evidence_id = evidence_by_node.get(node["id"])
        return {
            "node_ids": [node["id"]],
            "edge_ids": [],
            "endpoint_ids": [],
            "evidence_ids": [evidence_id] if evidence_id else [],
            "file_path": node.get("file_path"),
            "line_number": node.get("start_line"),
            "confidence": "HIGH",
            "claim_type": "FACT",
        }

    @staticmethod
    def _exception_name(expression: str) -> str:
        match = re.search(r"(?:raise|throw)\s+(?:new\s+)?([\w.]+)", expression)
        return match.group(1) if match else "UNKNOWN_EXCEPTION"

    def _risks(
        self,
        nodes: list[dict],
        data_ops: list[dict],
        external_calls: list[dict],
        evidence_by_node: dict[str, str],
    ) -> list[dict]:
        if not data_ops or not external_calls:
            return []
        write = next(
            (item for item in data_ops if item["operation"] in {"WRITE", "UPDATE", "DELETE"}),
            None,
        )
        external = next(
            (item for item in external_calls if item["dependency_type"] == "EXTERNAL_API"),
            None,
        )
        if not write or not external:
            return []
        ids = [write["node_id"], external["node_id"]]
        node_by_id = {item["id"]: item for item in nodes}
        return [
            {
                "risk_type": "TRANSACTION_RISK",
                "level": "MEDIUM",
                "description": (
                    "Potential Risk：当前链路同时包含数据写操作和外部调用；"
                    "仅凭静态拓扑无法确认事务与补偿策略。"
                ),
                "label": "Potential Risk",
                "node_ids": ids,
                "edge_ids": [],
                "endpoint_ids": [],
                "evidence_ids": [
                    evidence_by_node[node_id] for node_id in ids if node_id in evidence_by_node
                ],
                "file_path": node_by_id.get(write["node_id"], {}).get("file_path"),
                "line_number": node_by_id.get(write["node_id"], {}).get("start_line"),
                "confidence": "LOW",
                "claim_type": "INFERENCE",
            }
        ]
