from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tree_sitter import Node

from app.analyzers.tree_sitter_parser import (
    ParsedPythonFile,
    TreeSitterPythonParser,
)

IGNORED_CALLS = {
    "len",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "print",
    "range",
    "enumerate",
    "zip",
    "isinstance",
    "super",
}
DB_READ_METHODS = {
    "execute",
    "scalar",
    "scalars",
    "query",
    "select",
    "first",
    "all",
    "one",
    "get",
}
DB_WRITE_METHODS = {"add", "add_all", "delete", "commit", "flush", "update", "insert"}
REDIS_METHODS = {
    "get",
    "set",
    "delete",
    "hget",
    "hset",
    "lpush",
    "rpush",
    "publish",
}
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "request"}


@dataclass(frozen=True, slots=True)
class ImportRef:
    module: str
    symbol: str | None = None


@dataclass(slots=True)
class Definition:
    stable_key: str
    qualified_name: str
    name: str
    node_type: str
    module_name: str
    file_path: str
    parsed: ParsedPythonFile
    node: Node
    body: Node | None
    class_name: str | None = None
    return_type: str | None = None
    parameters: Node | None = None


@dataclass(slots=True)
class ModuleIndex:
    module_name: str
    file_path: str
    is_package: bool
    parsed: ParsedPythonFile
    imports: dict[str, ImportRef] = field(default_factory=dict)
    definitions: dict[str, Definition] = field(default_factory=dict)
    classes: dict[str, Definition] = field(default_factory=dict)
    module_variable_types: dict[str, str] = field(default_factory=dict)
    table_by_class: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class CallGraphResult:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    relations: dict[str, dict[str, Any]] = field(default_factory=dict)
    endpoint_api_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    issues: list[dict[str, str]] = field(default_factory=list)


class CallGraphAnalyzer:
    """提取代码定义与调用事实，并做可解释的基础符号解析。"""

    def __init__(self) -> None:
        self.parser = TreeSitterPythonParser()

    def analyze(
        self,
        *,
        root: Path,
        files: list[str],
        endpoints: list[dict[str, Any]],
    ) -> CallGraphResult:
        result = CallGraphResult()
        modules: dict[str, ModuleIndex] = {}

        for relative_path in files:
            try:
                parsed = self.parser.parse_file(root / Path(relative_path))
                module_name, is_package = self._module_name(relative_path)
                module = ModuleIndex(
                    module_name=module_name,
                    file_path=relative_path,
                    is_package=is_package,
                    parsed=parsed,
                )
                self._collect_imports(module)
                self._collect_definitions(module, result, endpoints)
                modules[module_name] = module
            except (OSError, UnicodeError, ValueError) as exc:
                result.issues.append(
                    {
                        "path": relative_path,
                        "code": "CALL_GRAPH_PARSE_FAILED",
                        "message": f"解析失败（{type(exc).__name__}），请检查文件格式",
                    }
                )

        self._normalize_import_modules(modules)
        for module in modules.values():
            self._collect_module_assignments(module)

        definitions = {
            definition.qualified_name: definition
            for module in modules.values()
            for definition in module.definitions.values()
        }
        method_names: dict[str, list[Definition]] = defaultdict(list)
        for definition in definitions.values():
            method_names[definition.name].append(definition)

        for module in modules.values():
            for definition in module.definitions.values():
                self._extract_definition_relations(
                    result,
                    modules,
                    definitions,
                    method_names,
                    module,
                    definition,
                )

        self._add_api_nodes(result, endpoints, definitions)
        return result

    def _normalize_import_modules(
        self,
        modules: dict[str, ModuleIndex],
    ) -> None:
        """将源码导入路径映射到扫描根目录下的真实模块名。"""
        for module in modules.values():
            for alias, imported in list(module.imports.items()):
                if imported.symbol:
                    imported_submodule = self._match_module_name(
                        modules,
                        f"{imported.module}.{imported.symbol}",
                    )
                    if imported_submodule:
                        module.imports[alias] = ImportRef(imported_submodule)
                        continue
                matched_module = self._match_module_name(
                    modules,
                    imported.module,
                )
                if matched_module:
                    module.imports[alias] = ImportRef(
                        matched_module,
                        imported.symbol,
                    )

    @staticmethod
    def _match_module_name(
        modules: dict[str, ModuleIndex],
        requested_module: str,
    ) -> str | None:
        if requested_module in modules:
            return requested_module
        suffix = f".{requested_module}"
        candidates = [module_name for module_name in modules if module_name.endswith(suffix)]
        return candidates[0] if len(candidates) == 1 else None

    def _collect_imports(self, module: ModuleIndex) -> None:
        for node in module.parsed.root_node.named_children:
            if node.type == "import_statement":
                for child in self._import_nodes(node):
                    name, alias = self._import_name(module.parsed, child)
                    if name:
                        module.imports[alias or name.split(".")[0]] = ImportRef(name)
            elif node.type == "import_from_statement":
                module_node = node.child_by_field_name("module_name")
                if not module_node:
                    continue
                target_module = self._resolve_import_module(
                    module,
                    module.parsed.text(module_node),
                )
                for child in self._import_nodes(node, exclude=module_node):
                    name, alias = self._import_name(module.parsed, child)
                    if name and name != "*":
                        module.imports[alias or name] = ImportRef(target_module, name)

    def _collect_definitions(
        self,
        module: ModuleIndex,
        result: CallGraphResult,
        endpoints: list[dict[str, Any]],
    ) -> None:
        route_names = {
            endpoint["qualified_name"]
            for endpoint in endpoints
            if endpoint["module_name"] == module.module_name
        }
        for top_node in module.parsed.root_node.named_children:
            node = self._unwrap_definition(top_node)
            if not node:
                continue
            if node.type == "function_definition":
                definition = self._make_function_definition(
                    module,
                    node,
                    class_name=None,
                    route_names=route_names,
                )
                module.definitions[definition.qualified_name] = definition
                self._add_definition_node(result, definition)
            elif node.type == "class_definition":
                self._collect_class(module, result, node, route_names)

    def _collect_class(
        self,
        module: ModuleIndex,
        result: CallGraphResult,
        class_node: Node,
        route_names: set[str],
    ) -> None:
        name_node = class_node.child_by_field_name("name")
        body = class_node.child_by_field_name("body")
        if not name_node or not body:
            return
        class_name = module.parsed.text(name_node)
        superclasses = class_node.child_by_field_name("superclasses")
        superclass_text = module.parsed.text(superclasses) if superclasses else ""
        class_type = self._classify_class(module.module_name, class_name, superclass_text)
        qualified_name = f"{module.module_name}.{class_name}"
        class_definition = Definition(
            stable_key=f"class:{qualified_name}",
            qualified_name=qualified_name,
            name=class_name,
            node_type=class_type,
            module_name=module.module_name,
            file_path=module.file_path,
            parsed=module.parsed,
            node=class_node,
            body=body,
        )
        module.classes[class_name] = class_definition
        module.definitions[qualified_name] = class_definition
        self._add_definition_node(result, class_definition)

        table_name = self._class_table_name(module, body)
        if table_name:
            module.table_by_class[class_name] = table_name
            table_key = f"table:{table_name}"
            self._add_node(
                result,
                stable_key=table_key,
                node_type="DATABASE_TABLE",
                name=table_name,
                qualified_name=table_name,
                module_name=module.module_name,
                file_path=module.file_path,
                start_line=class_node.start_point.row + 1,
                end_line=class_node.end_point.row + 1,
                signature=None,
                source_excerpt=None,
                metadata={"modelClass": qualified_name},
            )
            self._add_relation(
                result,
                source_key=class_definition.stable_key,
                target_key=table_key,
                relation_type="CONTAINS",
                confidence="CONFIRMED",
                file_path=module.file_path,
                line_number=class_node.start_point.row + 1,
                column_number=class_node.start_point.column + 1,
                evidence=f"__tablename__ = {table_name!r}",
            )

        for child in body.named_children:
            unwrapped = self._unwrap_definition(child)
            if not unwrapped or unwrapped.type != "function_definition":
                continue
            definition = self._make_function_definition(
                module,
                unwrapped,
                class_name=class_name,
                route_names=route_names,
            )
            if class_type in {"SERVICE", "REPOSITORY"}:
                definition.node_type = class_type
            module.definitions[definition.qualified_name] = definition
            self._add_definition_node(result, definition)
            self._add_relation(
                result,
                source_key=class_definition.stable_key,
                target_key=definition.stable_key,
                relation_type="CONTAINS",
                confidence="CONFIRMED",
                file_path=module.file_path,
                line_number=unwrapped.start_point.row + 1,
                column_number=unwrapped.start_point.column + 1,
                evidence=self._signature(definition),
            )

    def _make_function_definition(
        self,
        module: ModuleIndex,
        node: Node,
        *,
        class_name: str | None,
        route_names: set[str],
    ) -> Definition:
        name_node = node.child_by_field_name("name")
        name = module.parsed.text(name_node) if name_node else "<anonymous>"
        qualified_name = (
            f"{module.module_name}.{class_name}.{name}"
            if class_name
            else f"{module.module_name}.{name}"
        )
        node_type = (
            "ROUTE_FUNCTION"
            if qualified_name in route_names
            else "METHOD"
            if class_name
            else "FUNCTION"
        )
        return_node = node.child_by_field_name("return_type")
        return Definition(
            stable_key=f"{node_type.lower()}:{qualified_name}",
            qualified_name=qualified_name,
            name=name,
            node_type=node_type,
            module_name=module.module_name,
            file_path=module.file_path,
            parsed=module.parsed,
            node=node,
            body=node.child_by_field_name("body"),
            class_name=class_name,
            return_type=module.parsed.text(return_node) if return_node else None,
            parameters=node.child_by_field_name("parameters"),
        )

    def _collect_module_assignments(self, module: ModuleIndex) -> None:
        for node in module.parsed.root_node.named_children:
            if node.type != "expression_statement" or not node.named_children:
                continue
            assignment = node.named_children[0]
            if assignment.type != "assignment":
                continue
            left = assignment.child_by_field_name("left")
            right = assignment.child_by_field_name("right")
            if not left or not right or left.type != "identifier" or right.type != "call":
                continue
            constructor = right.child_by_field_name("function")
            if constructor:
                resolved = self._resolve_type_name(
                    module,
                    module.parsed.text(constructor),
                )
                if resolved:
                    module.module_variable_types[module.parsed.text(left)] = resolved

    def _extract_definition_relations(
        self,
        result: CallGraphResult,
        modules: dict[str, ModuleIndex],
        definitions: dict[str, Definition],
        method_names: dict[str, list[Definition]],
        module: ModuleIndex,
        definition: Definition,
    ) -> None:
        if not definition.body:
            return
        variable_types = dict(module.module_variable_types)
        self._collect_parameter_types(
            module,
            definition,
            variable_types,
            definitions,
        )
        self._collect_local_types(module, definition.body, variable_types)
        self._add_dependency_and_model_relations(
            result,
            module,
            definition,
            definitions,
        )

        for call in self._calls_in_body(definition.body):
            expression_node = call.child_by_field_name("function")
            if not expression_node:
                continue
            expression = module.parsed.text(expression_node)
            if expression.split(".")[-1] in IGNORED_CALLS:
                continue
            if self._add_resource_relation(
                result,
                modules,
                module,
                definition,
                call,
                expression,
                variable_types,
                definitions,
            ):
                continue
            target, confidence = self._resolve_call(
                module,
                definition,
                expression,
                variable_types,
                definitions,
                method_names,
            )
            if target:
                target_key = target.stable_key
            else:
                target_key = (
                    f"unresolved:{module.module_name}:{call.start_point.row + 1}:{expression}"
                )
                self._add_node(
                    result,
                    stable_key=target_key,
                    node_type="UNRESOLVED",
                    name=expression,
                    qualified_name=expression,
                    module_name=module.module_name,
                    file_path=module.file_path,
                    start_line=call.start_point.row + 1,
                    end_line=call.end_point.row + 1,
                    signature=None,
                    source_excerpt=module.parsed.text(call)[:1000],
                    metadata={"expression": expression},
                )
                confidence = "LOW"
            self._add_relation(
                result,
                source_key=definition.stable_key,
                target_key=target_key,
                relation_type="CALLS",
                confidence=confidence,
                file_path=module.file_path,
                line_number=call.start_point.row + 1,
                column_number=call.start_point.column + 1,
                evidence=module.parsed.text(call)[:1000],
            )

    def _collect_parameter_types(
        self,
        module: ModuleIndex,
        definition: Definition,
        variable_types: dict[str, str],
        definitions: dict[str, Definition],
    ) -> None:
        if not definition.parameters:
            return
        for parameter in definition.parameters.named_children:
            name_node = parameter.child_by_field_name("name")
            if not name_node:
                name_node = next(
                    (child for child in parameter.named_children if child.type == "identifier"),
                    None,
                )
            type_node = parameter.child_by_field_name("type")
            if name_node and type_node:
                resolved = self._resolve_type_name(module, module.parsed.text(type_node))
                if resolved:
                    variable_types[module.parsed.text(name_node)] = resolved
            value = parameter.child_by_field_name("value")
            if name_node and value and value.type == "call":
                function = value.child_by_field_name("function")
                if function and module.parsed.text(function).split(".")[-1] == "Depends":
                    args = value.child_by_field_name("arguments")
                    provider_node = args.named_children[0] if args and args.named_children else None
                    if provider_node:
                        provider = self._resolve_symbol(
                            module,
                            module.parsed.text(provider_node),
                        )
                        provider_definition = definitions.get(provider) if provider else None
                        if provider_definition and provider_definition.return_type:
                            resolved = self._resolve_type_name(
                                module=module,
                                expression=provider_definition.return_type,
                            )
                            if resolved:
                                variable_types[module.parsed.text(name_node)] = resolved

    def _collect_local_types(
        self,
        module: ModuleIndex,
        body: Node,
        variable_types: dict[str, str],
    ) -> None:
        for node in self._walk(body):
            if node.type != "assignment":
                continue
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if not left or not right or right.type != "call":
                continue
            function = right.child_by_field_name("function")
            if not function:
                continue
            resolved = self._resolve_type_name(module, module.parsed.text(function))
            if not resolved:
                continue
            left_text = module.parsed.text(left)
            variable_types[left_text] = resolved

    def _add_dependency_and_model_relations(
        self,
        result: CallGraphResult,
        module: ModuleIndex,
        definition: Definition,
        definitions: dict[str, Definition],
    ) -> None:
        if definition.parameters:
            for parameter in definition.parameters.named_children:
                type_node = parameter.child_by_field_name("type")
                if type_node:
                    qualified = self._resolve_type_name(module, module.parsed.text(type_node))
                    target = definitions.get(qualified) if qualified else None
                    if target and target.node_type == "PYDANTIC_MODEL":
                        self._add_relation(
                            result,
                            source_key=definition.stable_key,
                            target_key=target.stable_key,
                            relation_type="VALIDATES",
                            confidence="CONFIRMED",
                            file_path=module.file_path,
                            line_number=parameter.start_point.row + 1,
                            column_number=parameter.start_point.column + 1,
                            evidence=module.parsed.text(parameter),
                        )
                value = parameter.child_by_field_name("value")
                if not value or value.type != "call":
                    continue
                function = value.child_by_field_name("function")
                if not function or module.parsed.text(function).split(".")[-1] != "Depends":
                    continue
                arguments = value.child_by_field_name("arguments")
                provider_node = (
                    arguments.named_children[0] if arguments and arguments.named_children else None
                )
                if not provider_node:
                    continue
                provider_qn = self._resolve_symbol(
                    module,
                    module.parsed.text(provider_node),
                )
                target = definitions.get(provider_qn) if provider_qn else None
                if target:
                    self._add_relation(
                        result,
                        source_key=definition.stable_key,
                        target_key=target.stable_key,
                        relation_type="DEPENDS_ON",
                        confidence="CONFIRMED",
                        file_path=module.file_path,
                        line_number=value.start_point.row + 1,
                        column_number=value.start_point.column + 1,
                        evidence=module.parsed.text(value),
                    )
        if definition.return_type:
            qualified = self._resolve_type_name(module, definition.return_type)
            target = definitions.get(qualified) if qualified else None
            if target and target.node_type == "PYDANTIC_MODEL":
                self._add_relation(
                    result,
                    source_key=definition.stable_key,
                    target_key=target.stable_key,
                    relation_type="RETURNS",
                    confidence="CONFIRMED",
                    file_path=module.file_path,
                    line_number=definition.node.start_point.row + 1,
                    column_number=definition.node.start_point.column + 1,
                    evidence=f"-> {definition.return_type}",
                )

    def _resolve_call(
        self,
        module: ModuleIndex,
        definition: Definition,
        expression: str,
        variable_types: dict[str, str],
        definitions: dict[str, Definition],
        method_names: dict[str, list[Definition]],
    ) -> tuple[Definition | None, str]:
        parts = expression.split(".")
        if len(parts) == 1:
            qualified = self._resolve_symbol(module, expression)
            return definitions.get(qualified) if qualified else None, "CONFIRMED"

        receiver = ".".join(parts[:-1])
        method_name = parts[-1]
        if receiver == "self" and definition.class_name:
            qualified = f"{module.module_name}.{definition.class_name}.{method_name}"
            return definitions.get(qualified), "CONFIRMED"
        if receiver in variable_types:
            qualified = f"{variable_types[receiver]}.{method_name}"
            return definitions.get(qualified), "HIGH"
        if receiver.endswith("()"):
            receiver_type = self._resolve_type_name(module, receiver[:-2])
            if receiver_type:
                qualified = f"{receiver_type}.{method_name}"
                return definitions.get(qualified), "HIGH"
        imported = module.imports.get(parts[0])
        if imported and imported.symbol is None:
            qualified = ".".join([imported.module, *parts[1:]])
            return definitions.get(qualified), "CONFIRMED"
        local_class = module.classes.get(parts[0])
        if local_class:
            return definitions.get(f"{local_class.qualified_name}.{method_name}"), "HIGH"
        candidates = method_names.get(method_name, [])
        if len(candidates) == 1:
            return candidates[0], "MEDIUM"
        return None, "LOW"

    def _add_resource_relation(
        self,
        result: CallGraphResult,
        modules: dict[str, ModuleIndex],
        module: ModuleIndex,
        definition: Definition,
        call: Node,
        expression: str,
        variable_types: dict[str, str],
        definitions: dict[str, Definition],
    ) -> bool:
        parts = expression.split(".")
        method = parts[-1]
        receiver = ".".join(parts[:-1])
        receiver_type = variable_types.get(receiver, "")
        receiver_root = parts[0]
        imported = module.imports.get(receiver_root)

        is_sqlalchemy = method in DB_READ_METHODS | DB_WRITE_METHODS and (
            "Session" in receiver_type
            or receiver_root.lower() in {"db", "session"}
            or (imported and imported.module.startswith("sqlalchemy"))
        )
        is_sql_function = (
            len(parts) == 1
            and method in {"select", "insert", "update", "delete"}
            and (
                module.imports.get(method)
                and module.imports[method].module.startswith("sqlalchemy")
            )
        )
        if is_sqlalchemy or is_sql_function:
            write_methods = DB_WRITE_METHODS | {"insert", "update", "delete"}
            relation_type = "WRITES" if method in write_methods else "QUERIES"
            operation_key = f"dbop:{module.module_name}:{call.start_point.row + 1}:{expression}"
            self._add_node(
                result,
                stable_key=operation_key,
                node_type="DATABASE_OPERATION",
                name=expression,
                qualified_name=expression,
                module_name=module.module_name,
                file_path=module.file_path,
                start_line=call.start_point.row + 1,
                end_line=call.end_point.row + 1,
                signature=None,
                source_excerpt=module.parsed.text(call)[:1000],
                metadata={"operation": method},
            )
            self._add_relation(
                result,
                source_key=definition.stable_key,
                target_key=operation_key,
                relation_type=relation_type,
                confidence="HIGH",
                file_path=module.file_path,
                line_number=call.start_point.row + 1,
                column_number=call.start_point.column + 1,
                evidence=module.parsed.text(call)[:1000],
            )
            arguments = call.child_by_field_name("arguments")
            first_arg = (
                arguments.named_children[0] if arguments and arguments.named_children else None
            )
            if first_arg:
                model_qn = self._resolve_symbol(module, module.parsed.text(first_arg))
                model = definitions.get(model_qn) if model_qn else None
                if model:
                    model_module = modules.get(model.module_name)
                    table_name = (
                        model_module.table_by_class.get(model.name) if model_module else None
                    )
                    if table_name:
                        self._add_relation(
                            result,
                            source_key=operation_key,
                            target_key=f"table:{table_name}",
                            relation_type=relation_type,
                            confidence="CONFIRMED",
                            file_path=module.file_path,
                            line_number=call.start_point.row + 1,
                            column_number=call.start_point.column + 1,
                            evidence=module.parsed.text(call)[:1000],
                        )
            return True

        is_redis = method in REDIS_METHODS and (
            "Redis" in receiver_type or "redis" in receiver.lower()
        )
        if is_redis:
            target_key = f"redis:{receiver or 'redis'}"
            self._add_node(
                result,
                stable_key=target_key,
                node_type="REDIS",
                name=receiver or "Redis",
                qualified_name=receiver or "Redis",
                module_name=module.module_name,
                file_path=module.file_path,
                start_line=call.start_point.row + 1,
                end_line=call.end_point.row + 1,
                signature=None,
                source_excerpt=module.parsed.text(call)[:1000],
                metadata={"operation": method},
            )
            self._add_relation(
                result,
                source_key=definition.stable_key,
                target_key=target_key,
                relation_type="USES_REDIS",
                confidence="HIGH",
                file_path=module.file_path,
                line_number=call.start_point.row + 1,
                column_number=call.start_point.column + 1,
                evidence=module.parsed.text(call)[:1000],
            )
            return True

        is_http = method in HTTP_METHODS and (
            "Client" in receiver_type
            or (imported and imported.module.split(".")[0] in {"httpx", "requests"})
            or receiver_root in {"httpx", "requests"}
        )
        if is_http:
            arguments = call.child_by_field_name("arguments")
            url_node = (
                arguments.named_children[0] if arguments and arguments.named_children else None
            )
            url = module.parsed.text(url_node) if url_node else "<dynamic-url>"
            try:
                literal_url = ast.literal_eval(url)
                if isinstance(literal_url, str):
                    url = literal_url
            except (ValueError, SyntaxError):
                pass
            target_key = f"external:{method}:{url}"
            self._add_node(
                result,
                stable_key=target_key,
                node_type="EXTERNAL_HTTP",
                name=f"{method.upper()} {url}",
                qualified_name=url,
                module_name=module.module_name,
                file_path=module.file_path,
                start_line=call.start_point.row + 1,
                end_line=call.end_point.row + 1,
                signature=None,
                source_excerpt=module.parsed.text(call)[:1000],
                metadata={"httpMethod": method.upper(), "url": url},
            )
            self._add_relation(
                result,
                source_key=definition.stable_key,
                target_key=target_key,
                relation_type="REQUESTS_EXTERNAL_API",
                confidence="HIGH",
                file_path=module.file_path,
                line_number=call.start_point.row + 1,
                column_number=call.start_point.column + 1,
                evidence=module.parsed.text(call)[:1000],
            )
            return True
        return False

    def _add_api_nodes(
        self,
        result: CallGraphResult,
        endpoints: list[dict[str, Any]],
        definitions: dict[str, Definition],
    ) -> None:
        for endpoint in endpoints:
            identity = (
                endpoint["http_method"],
                endpoint["path"],
                endpoint["qualified_name"],
            )
            api_key = (
                f"api:{endpoint['http_method']}:{endpoint['path']}:{endpoint['qualified_name']}"
            )
            result.endpoint_api_keys[identity] = api_key
            self._add_node(
                result,
                stable_key=api_key,
                node_type="API",
                name=f"{endpoint['http_method']} {endpoint['path']}",
                qualified_name=endpoint["qualified_name"],
                module_name=endpoint["module_name"],
                file_path=endpoint["file_path"],
                start_line=endpoint["start_line"],
                end_line=endpoint["end_line"],
                signature=None,
                source_excerpt=None,
                metadata={
                    "httpMethod": endpoint["http_method"],
                    "path": endpoint["path"],
                    "tags": endpoint["tags"],
                },
            )
            route = definitions.get(endpoint["qualified_name"])
            if route:
                self._add_relation(
                    result,
                    source_key=api_key,
                    target_key=route.stable_key,
                    relation_type="ROUTES_TO",
                    confidence="CONFIRMED",
                    file_path=endpoint["file_path"],
                    line_number=endpoint["start_line"],
                    column_number=1,
                    evidence=f"@route {endpoint['http_method']} {endpoint['path']}",
                )

    def _add_definition_node(
        self,
        result: CallGraphResult,
        definition: Definition,
    ) -> None:
        self._add_node(
            result,
            stable_key=definition.stable_key,
            node_type=definition.node_type,
            name=definition.name,
            qualified_name=definition.qualified_name,
            module_name=definition.module_name,
            file_path=definition.file_path,
            start_line=definition.node.start_point.row + 1,
            end_line=definition.node.end_point.row + 1,
            signature=self._signature(definition),
            source_excerpt=definition.parsed.text(definition.node)[:4000],
            metadata={"className": definition.class_name},
        )

    @staticmethod
    def _add_node(
        result: CallGraphResult,
        *,
        stable_key: str,
        node_type: str,
        name: str,
        qualified_name: str,
        module_name: str | None,
        file_path: str | None,
        start_line: int | None,
        end_line: int | None,
        signature: str | None,
        source_excerpt: str | None,
        metadata: dict[str, Any],
    ) -> None:
        result.nodes.setdefault(
            stable_key,
            {
                "stable_key": stable_key,
                "node_type": node_type,
                "name": name,
                "qualified_name": qualified_name,
                "module_name": module_name,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "signature": signature,
                "source_excerpt": source_excerpt,
                "extra_metadata": metadata,
            },
        )

    @staticmethod
    def _add_relation(
        result: CallGraphResult,
        *,
        source_key: str,
        target_key: str,
        relation_type: str,
        confidence: str,
        file_path: str | None,
        line_number: int | None,
        column_number: int | None,
        evidence: str | None,
    ) -> None:
        raw_key = f"{source_key}|{relation_type}|{target_key}|{file_path}|{line_number}|{evidence}"
        stable_key = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()
        result.relations.setdefault(
            stable_key,
            {
                "stable_key": stable_key,
                "source_key": source_key,
                "target_key": target_key,
                "relation_type": relation_type,
                "confidence": confidence,
                "file_path": file_path,
                "line_number": line_number,
                "column_number": column_number,
                "evidence": evidence,
                "extra_metadata": {},
            },
        )

    def _resolve_symbol(self, module: ModuleIndex, expression: str) -> str | None:
        parts = expression.split(".")
        if len(parts) == 1:
            local = f"{module.module_name}.{expression}"
            if local in module.definitions:
                return local
            imported = module.imports.get(expression)
            if imported and imported.symbol:
                return f"{imported.module}.{imported.symbol}"
            return local
        imported = module.imports.get(parts[0])
        if imported and imported.symbol is None:
            return ".".join([imported.module, *parts[1:]])
        return expression

    def _resolve_type_name(
        self,
        module: ModuleIndex,
        expression: str,
    ) -> str | None:
        cleaned = expression.strip()
        for wrapper in ("Optional[", "Annotated[", "list[", "List["):
            if cleaned.startswith(wrapper):
                cleaned = cleaned[len(wrapper) :].split(",", 1)[0].rstrip("]")
        cleaned = cleaned.split("|", 1)[0].strip()
        return self._resolve_symbol(module, cleaned)

    @staticmethod
    def _calls_in_body(body: Node) -> list[Node]:
        result: list[Node] = []
        stack = list(reversed(body.named_children))
        while stack:
            node = stack.pop()
            if node.type == "function_definition":
                continue
            if node.type == "call":
                result.append(node)
            stack.extend(reversed(node.named_children))
        return result

    @staticmethod
    def _walk(node: Node):
        stack = [node]
        while stack:
            current = stack.pop()
            yield current
            stack.extend(reversed(current.named_children))

    @staticmethod
    def _unwrap_definition(node: Node) -> Node | None:
        if node.type in {"function_definition", "class_definition"}:
            return node
        if node.type == "decorated_definition":
            return next(
                (
                    child
                    for child in node.named_children
                    if child.type in {"function_definition", "class_definition"}
                ),
                None,
            )
        return None

    @staticmethod
    def _classify_class(module_name: str, name: str, superclasses: str) -> str:
        del module_name
        normalized_name = name.lower()
        if "basemodel" in superclasses.lower():
            return "PYDANTIC_MODEL"
        if (
            "repository" in normalized_name
            or normalized_name.endswith("repo")
            or normalized_name.endswith("dao")
        ):
            return "REPOSITORY"
        if "service" in normalized_name:
            return "SERVICE"
        return "CLASS"

    def _class_table_name(self, module: ModuleIndex, body: Node) -> str | None:
        for statement in body.named_children:
            if statement.type != "expression_statement" or not statement.named_children:
                continue
            assignment = statement.named_children[0]
            if assignment.type != "assignment":
                continue
            left = assignment.child_by_field_name("left")
            right = assignment.child_by_field_name("right")
            if not left or not right or module.parsed.text(left) != "__tablename__":
                continue
            try:
                value = ast.literal_eval(module.parsed.text(right))
                return value if isinstance(value, str) else None
            except (ValueError, SyntaxError):
                return None
        return None

    @staticmethod
    def _signature(definition: Definition) -> str:
        parameters = (
            definition.parsed.text(definition.parameters) if definition.parameters else "()"
        )
        result = f"{definition.name}{parameters}"
        if definition.return_type:
            result += f" -> {definition.return_type}"
        return result

    @staticmethod
    def _module_name(relative_path: str) -> tuple[str, bool]:
        path = Path(relative_path)
        parts = list(path.with_suffix("").parts)
        is_package = bool(parts and parts[-1] == "__init__")
        if is_package:
            parts.pop()
        return ".".join(parts) or "__root__", is_package

    @staticmethod
    def _import_nodes(node: Node, *, exclude: Node | None = None) -> list[Node]:
        result: list[Node] = []
        for child in node.named_children:
            if child == exclude:
                continue
            if child.type in {"aliased_import", "dotted_name", "identifier"}:
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
    def _resolve_import_module(module: ModuleIndex, text: str) -> str:
        if not text.startswith("."):
            return text
        level = len(text) - len(text.lstrip("."))
        suffix = text[level:]
        parts = module.module_name.split(".")
        if not module.is_package:
            parts.pop()
        ascend = max(level - 1, 0)
        if ascend:
            parts = parts[: max(len(parts) - ascend, 0)]
        if suffix:
            parts.extend(suffix.split("."))
        return ".".join(parts)
