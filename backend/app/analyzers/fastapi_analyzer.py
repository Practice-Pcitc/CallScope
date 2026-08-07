from __future__ import annotations

import ast
import re
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tree_sitter import Node

from app.analyzers.tree_sitter_parser import (
    ParsedPythonFile,
    TreeSitterPythonParser,
)

HTTP_METHODS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
}
PARAMETER_LOCATIONS = {
    "Query": "QUERY",
    "Path": "PATH",
    "Body": "BODY",
    "Header": "HEADER",
    "Cookie": "COOKIE",
    "Form": "FORM",
    "File": "FILE",
}
PATH_PARAMETER_PATTERN = re.compile(r"\{([^}:]+)(?::[^}]+)?\}")


@dataclass(frozen=True, slots=True)
class ImportReference:
    module: str
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class BindingFact:
    module_name: str
    variable_name: str
    kind: str
    prefix: str
    tags: tuple[str, ...]
    dynamic_prefix: bool

    @property
    def key(self) -> str:
        return f"{self.module_name}:{self.variable_name}"


@dataclass(frozen=True, slots=True)
class IncludeFact:
    module_name: str
    parent_expression: str
    child_expression: str
    prefix: str
    tags: tuple[str, ...]
    dynamic_prefix: bool
    line_number: int


@dataclass(slots=True)
class RouteFact:
    module_name: str
    file_path: str
    receiver_expression: str
    http_methods: list[str]
    path: str
    path_dynamic: bool
    function_name: str
    start_line: int
    end_line: int
    summary: str | None
    docstring: str | None
    route_tags: list[str]
    response_type: str | None
    parameters: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]


@dataclass(slots=True)
class ModuleFacts:
    module_name: str
    file_path: str
    is_package: bool
    parsed: ParsedPythonFile
    imports: dict[str, ImportReference] = field(default_factory=dict)
    constants: dict[str, Any] = field(default_factory=dict)
    class_defaults: dict[str, list[Any]] = field(default_factory=dict)
    bindings: dict[str, BindingFact] = field(default_factory=dict)
    includes: list[IncludeFact] = field(default_factory=list)
    routes: list[RouteFact] = field(default_factory=list)
    pydantic_models: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class AnalyzerIssue:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


@dataclass(slots=True)
class EndpointAnalysisResult:
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    issues: list[AnalyzerIssue] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RouterContext:
    base_prefix: str
    inherited_tags: tuple[str, ...]
    ancestry: frozenset[str]


AnalysisProgress = Callable[[str, int, int], None]


class FastAPIProjectAnalyzer:
    """基于 Tree-sitter 事实解析 FastAPI 路由，不执行目标项目。"""

    def __init__(self) -> None:
        self.parser = TreeSitterPythonParser()

    def analyze(
        self,
        *,
        root: Path,
        files: list[str],
        on_progress: AnalysisProgress | None = None,
    ) -> EndpointAnalysisResult:
        result = EndpointAnalysisResult()
        modules: dict[str, ModuleFacts] = {}

        for index, relative_path in enumerate(files, start=1):
            if on_progress:
                on_progress(relative_path, index, len(files))
            try:
                path = root / Path(relative_path)
                parsed = self.parser.parse_file(path)
                module_name, is_package = self._module_name(relative_path)
                facts = ModuleFacts(
                    module_name=module_name,
                    file_path=relative_path,
                    is_package=is_package,
                    parsed=parsed,
                )
                self._collect_module_facts(facts)
                modules[module_name] = facts
                if parsed.root_node.has_error:
                    result.issues.append(
                        AnalyzerIssue(
                            path=relative_path,
                            code="PYTHON_SYNTAX_ERROR",
                            message="Tree-sitter 检测到语法错误，已尽量提取可识别内容",
                        )
                    )
            except (OSError, UnicodeError, ValueError) as exc:
                result.issues.append(
                    AnalyzerIssue(
                        path=relative_path,
                        code="PYTHON_PARSE_FAILED",
                        message=str(exc),
                    )
                )

        result.endpoints = self._build_endpoints(modules, result.issues)
        return result

    def _collect_module_facts(self, facts: ModuleFacts) -> None:
        top_level = facts.parsed.root_node.named_children
        for node in top_level:
            if node.type in {"import_statement", "import_from_statement"}:
                self._collect_import(facts, node)
            elif node.type == "expression_statement":
                self._collect_constant(facts, node)

        for node in top_level:
            if node.type == "expression_statement":
                self._collect_binding_or_include(facts, node)
            elif node.type == "decorated_definition":
                self._collect_routes(facts, node)
            elif node.type == "class_definition":
                self._collect_pydantic_model(facts, node)
                self._collect_class_defaults(facts, node)

    def _collect_import(self, facts: ModuleFacts, node: Node) -> None:
        parsed = facts.parsed
        if node.type == "import_statement":
            for child in self._import_name_nodes(node):
                source_name, alias = self._import_name(parsed, child)
                if source_name:
                    facts.imports[alias or source_name.split(".")[0]] = ImportReference(
                        module=source_name,
                        symbol=None,
                    )
            return

        module_node = node.child_by_field_name("module_name")
        if not module_node:
            return
        imported_module = self._resolve_import_module(
            facts,
            parsed.text(module_node),
        )
        for child in self._import_name_nodes(node, exclude=module_node):
            symbol, alias = self._import_name(parsed, child)
            if symbol and symbol != "*":
                facts.imports[alias or symbol] = ImportReference(
                    module=imported_module,
                    symbol=symbol,
                )

    def _collect_constant(self, facts: ModuleFacts, statement: Node) -> None:
        if not statement.named_children:
            return
        assignment = statement.named_children[0]
        if assignment.type != "assignment":
            return
        left = assignment.child_by_field_name("left")
        right = assignment.child_by_field_name("right")
        if not left or not right or left.type != "identifier":
            return
        value = self._literal_value(facts, right)
        if value is not None:
            facts.constants[facts.parsed.text(left)] = value

    def _collect_binding_or_include(
        self,
        facts: ModuleFacts,
        statement: Node,
    ) -> None:
        if not statement.named_children:
            return
        expression = statement.named_children[0]
        if expression.type == "assignment":
            left = expression.child_by_field_name("left")
            right = expression.child_by_field_name("right")
            if left and right and left.type == "identifier" and right.type == "call":
                constructor = self._call_function_text(facts, right)
                kind = self._fastapi_constructor_kind(facts, constructor)
                if kind:
                    keywords = self._call_keywords(right)
                    prefix, dynamic_prefix = self._string_or_dynamic(
                        facts,
                        keywords.get("prefix"),
                        default="",
                    )
                    tags = self._string_list(facts, keywords.get("tags"))
                    variable_name = facts.parsed.text(left)
                    facts.bindings[variable_name] = BindingFact(
                        module_name=facts.module_name,
                        variable_name=variable_name,
                        kind=kind,
                        prefix=prefix,
                        tags=tuple(tags),
                        dynamic_prefix=dynamic_prefix,
                    )
            return

        if expression.type != "call":
            return
        function = expression.child_by_field_name("function")
        if not function or function.type != "attribute":
            return
        attribute = function.child_by_field_name("attribute")
        parent = function.child_by_field_name("object")
        if (
            not attribute
            or not parent
            or facts.parsed.text(attribute) != "include_router"
        ):
            return
        positional = self._call_positional(expression)
        if not positional:
            return
        keywords = self._call_keywords(expression)
        prefix, dynamic_prefix = self._string_or_dynamic(
            facts,
            keywords.get("prefix"),
            default="",
        )
        facts.includes.append(
            IncludeFact(
                module_name=facts.module_name,
                parent_expression=facts.parsed.text(parent),
                child_expression=facts.parsed.text(positional[0]),
                prefix=prefix,
                tags=tuple(self._string_list(facts, keywords.get("tags"))),
                dynamic_prefix=dynamic_prefix,
                line_number=expression.start_point.row + 1,
            )
        )

    def _collect_routes(self, facts: ModuleFacts, decorated: Node) -> None:
        function = next(
            (
                child
                for child in decorated.named_children
                if child.type == "function_definition"
            ),
            None,
        )
        if not function:
            return
        name_node = function.child_by_field_name("name")
        if not name_node:
            return
        function_name = facts.parsed.text(name_node)
        docstring = self._function_docstring(facts, function)
        return_node = function.child_by_field_name("return_type")
        parameters = self._function_parameters(facts, function)

        for decorator in (
            child for child in decorated.named_children if child.type == "decorator"
        ):
            if not decorator.named_children:
                continue
            call = decorator.named_children[0]
            if call.type != "call":
                continue
            call_function = call.child_by_field_name("function")
            if not call_function or call_function.type != "attribute":
                continue
            receiver = call_function.child_by_field_name("object")
            method_node = call_function.child_by_field_name("attribute")
            if not receiver or not method_node:
                continue
            method_name = facts.parsed.text(method_node)
            if method_name not in HTTP_METHODS and method_name != "api_route":
                continue

            positional = self._call_positional(call)
            keywords = self._call_keywords(call)
            path_node = positional[0] if positional else keywords.get("path")
            path, path_dynamic = self._string_or_dynamic(
                facts,
                path_node,
                default="/",
            )
            if method_name == "api_route":
                methods = [
                    method.upper()
                    for method in self._string_list(facts, keywords.get("methods"))
                    if method.lower() in HTTP_METHODS
                ]
                if not methods:
                    continue
            else:
                methods = [method_name.upper()]

            response_node = keywords.get("response_model") or return_node
            summary_value = self._literal_value(facts, keywords.get("summary"))
            summary = summary_value if isinstance(summary_value, str) else None
            route_dependencies = self._decorator_dependencies(
                facts,
                keywords.get("dependencies"),
            )
            facts.routes.append(
                RouteFact(
                    module_name=facts.module_name,
                    file_path=facts.file_path,
                    receiver_expression=facts.parsed.text(receiver),
                    http_methods=methods,
                    path=path,
                    path_dynamic=path_dynamic,
                    function_name=function_name,
                    start_line=decorator.start_point.row + 1,
                    end_line=function.end_point.row + 1,
                    summary=summary,
                    docstring=docstring,
                    route_tags=self._string_list(facts, keywords.get("tags")),
                    response_type=(
                        facts.parsed.text(response_node) if response_node else None
                    ),
                    parameters=[dict(parameter) for parameter in parameters],
                    dependencies=[
                        *[
                            dict(parameter["dependency"])
                            for parameter in parameters
                            if parameter.get("dependency")
                        ],
                        *route_dependencies,
                    ],
                )
            )

    def _collect_pydantic_model(self, facts: ModuleFacts, node: Node) -> None:
        name_node = node.child_by_field_name("name")
        superclasses = node.child_by_field_name("superclasses")
        if not name_node or not superclasses:
            return
        superclass_names = [
            facts.parsed.text(child) for child in superclasses.named_children
        ]
        for superclass in superclass_names:
            root_name = superclass.split(".")[0]
            imported = facts.imports.get(root_name)
            if superclass.endswith("BaseModel") or (
                imported
                and imported.module == "pydantic"
                and imported.symbol == "BaseModel"
            ):
                facts.pydantic_models.add(facts.parsed.text(name_node))
                return

    def _collect_class_defaults(self, facts: ModuleFacts, node: Node) -> None:
        """提取配置类中的字面量默认值，用于静态还原路由前缀。"""
        body = node.child_by_field_name("body")
        if not body:
            return
        for statement in body.named_children:
            if (
                statement.type != "expression_statement"
                or not statement.named_children
            ):
                continue
            assignment = statement.named_children[0]
            if assignment.type != "assignment":
                continue
            left = assignment.child_by_field_name("left")
            right = assignment.child_by_field_name("right")
            if not left or not right or left.type != "identifier":
                continue
            value = self._literal_value(facts, right)
            if value is not None:
                facts.class_defaults.setdefault(
                    facts.parsed.text(left),
                    [],
                ).append(value)

    def _build_endpoints(
        self,
        modules: dict[str, ModuleFacts],
        issues: list[AnalyzerIssue],
    ) -> list[dict[str, Any]]:
        bindings = {
            binding.key: binding
            for facts in modules.values()
            for binding in facts.bindings.values()
        }
        includes_by_parent: dict[str, list[tuple[IncludeFact, str]]] = defaultdict(list)
        for facts in modules.values():
            for include in facts.includes:
                parent_key = self._resolve_binding_key(
                    modules,
                    facts,
                    include.parent_expression,
                )
                child_key = self._resolve_binding_key(
                    modules,
                    facts,
                    include.child_expression,
                )
                if parent_key and child_key and child_key in bindings:
                    includes_by_parent[parent_key].append((include, child_key))
                else:
                    issues.append(
                        AnalyzerIssue(
                            path=facts.file_path,
                            code="ROUTER_INCLUDE_UNRESOLVED",
                            message=(
                                f"第 {include.line_number} 行 include_router "
                                "无法解析到已知 APIRouter"
                            ),
                        )
                    )

        contexts: dict[str, list[RouterContext]] = defaultdict(list)
        queue: deque[tuple[str, RouterContext]] = deque()
        for key, binding in bindings.items():
            if binding.kind == "APP":
                context = RouterContext("", (), frozenset({key}))
                contexts[key].append(context)
                queue.append((key, context))

        seen_contexts = {
            (key, context.base_prefix, context.inherited_tags)
            for key, values in contexts.items()
            for context in values
        }
        while queue:
            parent_key, context = queue.popleft()
            parent_binding = bindings[parent_key]
            for include, child_key in includes_by_parent.get(parent_key, []):
                if child_key in context.ancestry:
                    issues.append(
                        AnalyzerIssue(
                            path=modules[include.module_name].file_path,
                            code="ROUTER_INCLUDE_CYCLE",
                            message=f"第 {include.line_number} 行形成路由包含循环",
                        )
                    )
                    continue
                child_context = RouterContext(
                    base_prefix=self._join_paths(
                        context.base_prefix,
                        self._resolved_dynamic_string(
                            modules,
                            parent_binding.prefix,
                            parent_binding.dynamic_prefix,
                        ),
                        self._resolved_dynamic_string(
                            modules,
                            include.prefix,
                            include.dynamic_prefix,
                        ),
                    ),
                    inherited_tags=self._deduplicate(
                        [
                            *context.inherited_tags,
                            *parent_binding.tags,
                            *include.tags,
                        ]
                    ),
                    ancestry=context.ancestry | {child_key},
                )
                marker = (
                    child_key,
                    child_context.base_prefix,
                    child_context.inherited_tags,
                )
                if marker in seen_contexts:
                    continue
                seen_contexts.add(marker)
                contexts[child_key].append(child_context)
                queue.append((child_key, child_context))

        endpoints: list[dict[str, Any]] = []
        identities: set[tuple[str, str, str]] = set()
        for facts in modules.values():
            for route in facts.routes:
                binding_key = self._resolve_binding_key(
                    modules,
                    facts,
                    route.receiver_expression,
                )
                if not binding_key or binding_key not in bindings:
                    continue
                binding = bindings[binding_key]
                for context in contexts.get(binding_key, []):
                    final_path = self._join_paths(
                        context.base_prefix,
                        self._resolved_dynamic_string(
                            modules,
                            binding.prefix,
                            binding.dynamic_prefix,
                        ),
                        route.path,
                    )
                    route_parameters = self._classify_parameters(
                        modules,
                        facts,
                        route.parameters,
                        final_path,
                    )
                    dependencies = [
                        self._resolve_dependency(facts, dependency)
                        for dependency in route.dependencies
                    ]
                    qualified_name = f"{facts.module_name}.{route.function_name}"
                    for http_method in route.http_methods:
                        identity = (http_method, final_path, qualified_name)
                        if identity in identities:
                            continue
                        identities.add(identity)
                        endpoints.append(
                            {
                                "http_method": http_method,
                                "path": final_path,
                                "function_name": route.function_name,
                                "qualified_name": qualified_name,
                                "module_name": facts.module_name,
                                "file_path": route.file_path,
                                "start_line": route.start_line,
                                "end_line": route.end_line,
                                "summary": route.summary
                                or self._first_line(route.docstring),
                                "tags": list(
                                    self._deduplicate(
                                        [
                                            *context.inherited_tags,
                                            *binding.tags,
                                            *route.route_tags,
                                        ]
                                    )
                                ),
                                "parameters": route_parameters,
                                "response_type": route.response_type,
                                "dependencies": dependencies,
                                "metadata": {
                                    "router": binding_key,
                                    "pathDynamic": route.path_dynamic,
                                    "prefixDynamic": binding.dynamic_prefix,
                                    "mounted": True,
                                },
                            }
                        )
        endpoints.sort(key=lambda item: (item["path"], item["http_method"]))
        return endpoints

    def _function_parameters(
        self,
        facts: ModuleFacts,
        function: Node,
    ) -> list[dict[str, Any]]:
        parameters_node = function.child_by_field_name("parameters")
        if not parameters_node:
            return []
        parameters: list[dict[str, Any]] = []
        for node in parameters_node.named_children:
            if node.type not in {
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
            }:
                continue
            name_node = node.child_by_field_name("name")
            if not name_node:
                name_node = next(
                    (
                        child
                        for child in node.named_children
                        if child.type == "identifier"
                    ),
                    None,
                )
            if not name_node:
                continue
            name = facts.parsed.text(name_node)
            if name in {"self", "cls"}:
                continue
            type_node = node.child_by_field_name("type")
            value_node = node.child_by_field_name("value")
            dependency = self._dependency_from_value(
                facts,
                parameter_name=name,
                value_node=value_node,
            )
            explicit_location = self._parameter_location(facts, value_node)
            default_value = self._literal_value(facts, value_node)
            parameters.append(
                {
                    "name": name,
                    "location": "DEPENDENCY" if dependency else explicit_location,
                    "type": facts.parsed.text(type_node) if type_node else None,
                    "required": value_node is None,
                    "default": (
                        default_value
                        if self._json_value(default_value)
                        else facts.parsed.text(value_node)
                        if value_node
                        else None
                    ),
                    "dependency": dependency,
                }
            )
        return parameters

    def _classify_parameters(
        self,
        modules: dict[str, ModuleFacts],
        facts: ModuleFacts,
        parameters: list[dict[str, Any]],
        path: str,
    ) -> list[dict[str, Any]]:
        path_names = set(PATH_PARAMETER_PATTERN.findall(path))
        result: list[dict[str, Any]] = []
        for parameter in parameters:
            value = dict(parameter)
            value.pop("dependency", None)
            if value["name"] in path_names:
                value["location"] = "PATH"
            elif value["location"] == "UNKNOWN":
                value["location"] = (
                    "BODY"
                    if self._is_pydantic_type(
                        modules,
                        facts,
                        value.get("type"),
                    )
                    else "QUERY"
                )
            result.append(value)
        return result

    def _dependency_from_value(
        self,
        facts: ModuleFacts,
        *,
        parameter_name: str,
        value_node: Node | None,
    ) -> dict[str, Any] | None:
        if not value_node or value_node.type != "call":
            return None
        call_name = self._call_function_text(facts, value_node)
        if not self._is_fastapi_symbol(facts, call_name, "Depends"):
            return None
        positional = self._call_positional(value_node)
        provider = facts.parsed.text(positional[0]) if positional else None
        return {
            "parameterName": parameter_name,
            "providerExpression": provider,
            "resolvedQualifiedName": None,
            "confidence": "LOW",
        }

    def _decorator_dependencies(
        self,
        facts: ModuleFacts,
        node: Node | None,
    ) -> list[dict[str, Any]]:
        if not node:
            return []
        dependencies: list[dict[str, Any]] = []
        for candidate in self._walk(node):
            if candidate.type != "call":
                continue
            call_name = self._call_function_text(facts, candidate)
            if not self._is_fastapi_symbol(facts, call_name, "Depends"):
                continue
            positional = self._call_positional(candidate)
            provider = facts.parsed.text(positional[0]) if positional else None
            dependencies.append(
                {
                    "parameterName": None,
                    "providerExpression": provider,
                    "resolvedQualifiedName": None,
                    "confidence": "LOW",
                }
            )
        return dependencies

    def _resolve_dependency(
        self,
        facts: ModuleFacts,
        dependency: dict[str, Any],
    ) -> dict[str, Any]:
        value = dict(dependency)
        provider = value.get("providerExpression")
        if not provider:
            return value
        resolved = self._resolve_qualified_symbol(facts, provider)
        value["resolvedQualifiedName"] = resolved
        value["confidence"] = "CONFIRMED" if resolved else "LOW"
        return value

    def _parameter_location(
        self,
        facts: ModuleFacts,
        value_node: Node | None,
    ) -> str:
        if not value_node or value_node.type != "call":
            return "UNKNOWN"
        call_name = self._call_function_text(facts, value_node)
        parts = call_name.split(".")
        imported = facts.imports.get(parts[0])
        resolved_symbol: str | None = None
        if len(parts) == 1 and imported and imported.module == "fastapi":
            resolved_symbol = imported.symbol
        elif (
            len(parts) == 2
            and imported
            and imported.module == "fastapi"
            and imported.symbol is None
        ):
            resolved_symbol = parts[1]
        if resolved_symbol in PARAMETER_LOCATIONS:
            return PARAMETER_LOCATIONS[resolved_symbol]
        return "UNKNOWN"

    def _is_pydantic_type(
        self,
        modules: dict[str, ModuleFacts],
        facts: ModuleFacts,
        type_text: str | None,
    ) -> bool:
        if not type_text:
            return False
        candidates = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", type_text))
        if candidates & facts.pydantic_models:
            return True
        for candidate in candidates:
            imported = facts.imports.get(candidate)
            if not imported or not imported.symbol:
                continue
            target_module = self._match_module_name(
                modules,
                imported.module,
            )
            if (
                target_module
                and imported.symbol
                in modules[target_module].pydantic_models
            ):
                return True
        return False

    def _fastapi_constructor_kind(
        self,
        facts: ModuleFacts,
        expression: str,
    ) -> str | None:
        if self._is_fastapi_symbol(facts, expression, "FastAPI"):
            return "APP"
        if self._is_fastapi_symbol(facts, expression, "APIRouter"):
            return "ROUTER"
        return None

    @staticmethod
    def _is_fastapi_symbol(
        facts: ModuleFacts,
        expression: str,
        expected: str,
    ) -> bool:
        parts = expression.split(".")
        imported = facts.imports.get(parts[0])
        if len(parts) == 1:
            return bool(
                imported
                and imported.module == "fastapi"
                and imported.symbol == expected
            )
        return bool(
            len(parts) == 2
            and parts[1] == expected
            and imported
            and imported.module == "fastapi"
            and imported.symbol is None
        )

    def _resolve_binding_key(
        self,
        modules: dict[str, ModuleFacts],
        facts: ModuleFacts,
        expression: str,
    ) -> str | None:
        if expression in facts.bindings:
            return f"{facts.module_name}:{expression}"
        parts = expression.split(".")
        imported = facts.imports.get(parts[0])
        if not imported:
            return None
        if len(parts) == 1 and imported.symbol:
            target_module = self._match_module_name(modules, imported.module)
            if target_module:
                return f"{target_module}:{imported.symbol}"
        if len(parts) == 2:
            requested_module = imported.module
            if imported.symbol:
                requested_module = f"{requested_module}.{imported.symbol}"
            target_module = self._match_module_name(modules, requested_module)
            if target_module:
                return f"{target_module}:{parts[1]}"
        return None

    @staticmethod
    def _match_module_name(
        modules: dict[str, ModuleFacts],
        requested_module: str,
    ) -> str | None:
        """兼容从仓库根扫描、源码实际位于 backend/app 等子目录的项目。"""
        if requested_module in modules:
            return requested_module
        suffix = f".{requested_module}"
        candidates = [
            module_name
            for module_name in modules
            if module_name.endswith(suffix)
        ]
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _resolved_dynamic_string(
        modules: dict[str, ModuleFacts],
        value: str,
        dynamic: bool,
    ) -> str:
        if not dynamic or not value.startswith("<dynamic:"):
            return value
        expression = value[len("<dynamic:") : -1]
        attribute_name = expression.rsplit(".", 1)[-1]
        candidates = {
            candidate
            for facts in modules.values()
            for candidate in facts.class_defaults.get(attribute_name, [])
            if isinstance(candidate, str)
        }
        return next(iter(candidates)) if len(candidates) == 1 else value

    def _resolve_qualified_symbol(
        self,
        facts: ModuleFacts,
        expression: str,
    ) -> str | None:
        parts = expression.split(".")
        if len(parts) == 1:
            imported = facts.imports.get(parts[0])
            if imported and imported.symbol:
                return f"{imported.module}.{imported.symbol}"
            return f"{facts.module_name}.{expression}"
        imported = facts.imports.get(parts[0])
        if imported and imported.symbol is None:
            return ".".join([imported.module, *parts[1:]])
        return None

    def _collect_potential_call_function(self, call: Node) -> Node | None:
        return call.child_by_field_name("function")

    def _call_function_text(self, facts: ModuleFacts, call: Node) -> str:
        function = self._collect_potential_call_function(call)
        return facts.parsed.text(function) if function else ""

    @staticmethod
    def _call_arguments(call: Node) -> list[Node]:
        arguments = call.child_by_field_name("arguments")
        return list(arguments.named_children) if arguments else []

    def _call_keywords(self, call: Node) -> dict[str, Node]:
        result: dict[str, Node] = {}
        for argument in self._call_arguments(call):
            if argument.type != "keyword_argument":
                continue
            name = argument.child_by_field_name("name")
            value = argument.child_by_field_name("value")
            if name and value:
                result[self._node_raw_text(name)] = value
        return result

    def _call_positional(self, call: Node) -> list[Node]:
        return [
            argument
            for argument in self._call_arguments(call)
            if argument.type
            not in {"keyword_argument", "dictionary_splat", "list_splat"}
        ]

    @staticmethod
    def _node_raw_text(node: Node) -> str:
        return node.text.decode("utf-8", errors="replace")

    def _literal_value(
        self,
        facts: ModuleFacts,
        node: Node | None,
    ) -> Any | None:
        if not node:
            return None
        text = facts.parsed.text(node)
        if node.type == "identifier" and text in facts.constants:
            return facts.constants[text]
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            if node.type == "list":
                values = [
                    self._literal_value(facts, child)
                    for child in node.named_children
                ]
                return values if all(value is not None for value in values) else None
            return None

    def _string_or_dynamic(
        self,
        facts: ModuleFacts,
        node: Node | None,
        *,
        default: str,
    ) -> tuple[str, bool]:
        if not node:
            return default, False
        value = self._literal_value(facts, node)
        if isinstance(value, str):
            return value, False
        return f"<dynamic:{facts.parsed.text(node)}>", True

    def _string_list(
        self,
        facts: ModuleFacts,
        node: Node | None,
    ) -> list[str]:
        value = self._literal_value(facts, node)
        if isinstance(value, (list, tuple)):
            return [item for item in value if isinstance(item, str)]
        return []

    @staticmethod
    def _json_value(value: Any) -> bool:
        return value is None or isinstance(value, (str, int, float, bool, list, dict))

    def _function_docstring(
        self,
        facts: ModuleFacts,
        function: Node,
    ) -> str | None:
        body = function.child_by_field_name("body")
        if not body or not body.named_children:
            return None
        first = body.named_children[0]
        if first.type != "expression_statement" or not first.named_children:
            return None
        value = self._literal_value(facts, first.named_children[0])
        return value if isinstance(value, str) else None

    @staticmethod
    def _first_line(value: str | None) -> str | None:
        if not value:
            return None
        return value.strip().splitlines()[0] or None

    @staticmethod
    def _walk(node: Node) -> Iterable[Node]:
        stack = [node]
        while stack:
            current = stack.pop()
            yield current
            stack.extend(reversed(current.named_children))

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _join_paths(*parts: str) -> str:
        dynamic_parts = [part for part in parts if part.startswith("<dynamic:")]
        trailing_slash = bool(
            parts
            and parts[-1]
            and not parts[-1].startswith("<dynamic:")
            and parts[-1].endswith("/")
        )
        static_parts = [
            part.strip("/") for part in parts if part and not part.startswith("<dynamic:")
        ]
        path = "/" + "/".join(part for part in static_parts if part)
        if trailing_slash and path != "/":
            path = f"{path}/"
        if dynamic_parts:
            suffix = "/".join(dynamic_parts)
            return f"{path.rstrip('/')}/{suffix}" if path != "/" else f"/{suffix}"
        return path

    @staticmethod
    def _module_name(relative_path: str) -> tuple[str, bool]:
        path = Path(relative_path)
        parts = list(path.with_suffix("").parts)
        is_package = bool(parts and parts[-1] == "__init__")
        if is_package:
            parts = parts[:-1]
        module_name = ".".join(parts) or "__root__"
        return module_name, is_package

    @staticmethod
    def _import_name_nodes(
        node: Node,
        *,
        exclude: Node | None = None,
    ) -> list[Node]:
        result: list[Node] = []
        for child in node.named_children:
            if child == exclude:
                continue
            if child.type in {
                "aliased_import",
                "dotted_name",
                "identifier",
                "wildcard_import",
            }:
                result.append(child)
            elif child.type == "import_list":
                result.extend(child.named_children)
        return result

    @staticmethod
    def _import_name(
        parsed: ParsedPythonFile,
        node: Node,
    ) -> tuple[str, str | None]:
        if node.type != "aliased_import":
            return parsed.text(node), None
        name = node.child_by_field_name("name")
        alias = node.child_by_field_name("alias")
        return (
            parsed.text(name) if name else "",
            parsed.text(alias) if alias else None,
        )

    @staticmethod
    def _resolve_import_module(facts: ModuleFacts, module_text: str) -> str:
        if not module_text.startswith("."):
            return module_text
        level = len(module_text) - len(module_text.lstrip("."))
        suffix = module_text[level:]
        package_parts = facts.module_name.split(".")
        if not facts.is_package:
            package_parts = package_parts[:-1]
        ascend = max(level - 1, 0)
        if ascend:
            package_parts = package_parts[: max(len(package_parts) - ascend, 0)]
        if suffix:
            package_parts.extend(suffix.split("."))
        return ".".join(package_parts)
