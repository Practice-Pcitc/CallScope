from __future__ import annotations

import hashlib
import html
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.analyzers.call_graph_analyzer import CallGraphResult
from app.analyzers.fastapi_analyzer import AnalyzerIssue, EndpointAnalysisResult

HTTP_ANNOTATIONS = {
    "GetMapping": ["GET"],
    "PostMapping": ["POST"],
    "PutMapping": ["PUT"],
    "DeleteMapping": ["DELETE"],
    "PatchMapping": ["PATCH"],
}
PARAMETER_LOCATIONS = {
    "PathVariable": "PATH",
    "RequestParam": "QUERY",
    "RequestBody": "BODY",
    "RequestHeader": "HEADER",
    "CookieValue": "COOKIE",
    "RequestPart": "FILE",
    "ModelAttribute": "QUERY",
}
CONTROL_CALLS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "throw",
    "new",
    "super",
    "this",
    "synchronized",
    "try",
    "assert",
    "equals",
    "hashCode",
    "toString",
    "getClass",
    "clone",
    "wait",
    "notify",
    "notifyAll",
}
JAVA_MODIFIERS = {
    "public",
    "protected",
    "private",
    "static",
    "final",
    "synchronized",
    "abstract",
    "default",
    "native",
    "strictfp",
}
STRING_LITERAL = re.compile(r'"((?:\\.|[^"\\])*)"')
IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
CLASS_PATTERN = re.compile(
    r"\b(?P<kind>class|interface|enum|record)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)"
)
PACKAGE_PATTERN = re.compile(r"\bpackage\s+([\w.]+)\s*;")
IMPORT_PATTERN = re.compile(r"\bimport\s+(?:static\s+)?([\w.*]+)\s*;")
CALL_PATTERN = re.compile(
    r"(?:(?P<receiver>\b[A-Za-z_$][\w$]*)\s*\.\s*)?"
    r"(?P<method>[A-Za-z_$][\w$]*)\s*\("
)

AnalysisProgress = Callable[[str, int, int], None]


@dataclass(frozen=True, slots=True)
class JavaAnnotation:
    name: str
    arguments: str
    start: int
    end: int


@dataclass(slots=True)
class JavaMethod:
    name: str
    qualified_name: str
    class_name: str
    package_name: str
    file_path: str
    return_type: str | None
    parameters_text: str
    annotations: list[JavaAnnotation]
    start_offset: int
    body_start: int
    body_end: int
    start_line: int
    end_line: int
    signature: str
    source_excerpt: str
    summary: str | None

    @property
    def stable_key(self) -> str:
        return f"java-method:{self.qualified_name}"


@dataclass(slots=True)
class JavaClass:
    name: str
    qualified_name: str
    package_name: str
    file_path: str
    summary: str | None
    annotations: list[JavaAnnotation]
    imports: dict[str, str]
    implements: list[str]
    fields: dict[str, str]
    methods: list[JavaMethod]
    source: str
    structure: str

    @property
    def annotation_names(self) -> set[str]:
        return {annotation.name.rsplit(".", 1)[-1] for annotation in self.annotations}


@dataclass(slots=True)
class JavaSpringAnalysis:
    endpoints: EndpointAnalysisResult = field(default_factory=EndpointAnalysisResult)
    graph: CallGraphResult = field(default_factory=CallGraphResult)


class JavaSpringProjectAnalyzer:
    """Static Java/Spring MVC analyzer; target source is never compiled or executed."""

    def analyze(
        self,
        *,
        root: Path,
        files: list[str],
        on_progress: AnalysisProgress | None = None,
    ) -> JavaSpringAnalysis:
        result = JavaSpringAnalysis()
        classes: list[JavaClass] = []

        for index, relative_path in enumerate(files, start=1):
            if on_progress:
                on_progress(relative_path, index, len(files))
            try:
                source = self._read_source(root / Path(relative_path))
                parsed = self._parse_file(relative_path, source)
                if parsed:
                    classes.append(parsed)
            except (OSError, UnicodeError, ValueError) as exc:
                result.endpoints.issues.append(
                    AnalyzerIssue(
                        path=relative_path,
                        code="JAVA_PARSE_FAILED",
                        message=f"文件处理失败（{type(exc).__name__}），请检查文件格式和读取权限",
                    )
                )

        result.endpoints.endpoints = self._build_endpoints(classes)
        result.graph = self._build_call_graph(
            classes,
            result.endpoints.endpoints,
        )
        return result

    def _parse_file(self, relative_path: str, source: str) -> JavaClass | None:
        comments_removed = _sanitize_java(source, mask_strings=False)
        structure = _sanitize_java(source, mask_strings=True)
        class_match = CLASS_PATTERN.search(structure)
        if not class_match:
            return None

        package_match = PACKAGE_PATTERN.search(comments_removed)
        package_name = package_match.group(1) if package_match else ""
        class_name = class_match.group("name")
        qualified_name = f"{package_name}.{class_name}" if package_name else class_name
        imports = {
            imported.rsplit(".", 1)[-1]: imported
            for imported in IMPORT_PATTERN.findall(comments_removed)
            if not imported.endswith(".*")
        }

        body_start = structure.find("{", class_match.end())
        if body_start < 0:
            return None
        body_end = _matching_delimiter(structure, body_start, "{", "}")
        if body_end < 0:
            body_end = len(structure) - 1

        declaration_start = comments_removed.rfind(";", 0, class_match.start()) + 1
        declaration = comments_removed[declaration_start:body_start]
        class_annotations = _extract_annotations(declaration)
        implements = self._implements(declaration, imports)
        methods = self._parse_methods(
            source=source,
            comments_removed=comments_removed,
            structure=structure,
            body_start=body_start,
            body_end=body_end,
            package_name=package_name,
            class_name=class_name,
            file_path=relative_path,
        )
        method_ranges = [(method.start_offset, method.body_end) for method in methods]
        fields = self._parse_fields(
            comments_removed,
            body_start,
            body_end,
            method_ranges,
            imports,
        )
        return JavaClass(
            name=class_name,
            qualified_name=qualified_name,
            package_name=package_name,
            file_path=relative_path,
            summary=_java_doc_summary(source[declaration_start : class_match.start()]),
            annotations=class_annotations,
            imports=imports,
            implements=implements,
            fields=fields,
            methods=methods,
            source=source,
            structure=structure,
        )

    def _parse_methods(
        self,
        *,
        source: str,
        comments_removed: str,
        structure: str,
        body_start: int,
        body_end: int,
        package_name: str,
        class_name: str,
        file_path: str,
    ) -> list[JavaMethod]:
        methods: list[JavaMethod] = []
        member_start = body_start + 1
        position = body_start + 1
        depth = 1

        while position < body_end:
            character = structure[position]
            if character == "{":
                if depth == 1:
                    segment = comments_removed[member_start:position]
                    parsed_signature = self._method_signature(segment)
                    if parsed_signature:
                        method_end = _matching_delimiter(
                            structure,
                            position,
                            "{",
                            "}",
                        )
                        if method_end < 0:
                            method_end = body_end
                        (
                            name,
                            return_type,
                            parameters_text,
                            annotations,
                            signature_offset,
                            signature,
                        ) = parsed_signature
                        if name != class_name:
                            absolute_start = member_start + signature_offset
                            qualified_name = (
                                f"{package_name}.{class_name}.{name}"
                                if package_name
                                else f"{class_name}.{name}"
                            )
                            methods.append(
                                JavaMethod(
                                    name=name,
                                    qualified_name=qualified_name,
                                    class_name=class_name,
                                    package_name=package_name,
                                    file_path=file_path,
                                    return_type=return_type,
                                    parameters_text=parameters_text,
                                    annotations=annotations,
                                    start_offset=absolute_start,
                                    body_start=position,
                                    body_end=method_end,
                                    start_line=_line_number(source, absolute_start),
                                    end_line=_line_number(source, method_end),
                                    signature=signature.strip(),
                                    source_excerpt=source[absolute_start : method_end + 1][:4000],
                                    summary=_java_doc_summary(source[member_start:absolute_start]),
                                )
                            )
                        position = method_end + 1
                        member_start = position
                        continue
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 1:
                    member_start = position + 1
            elif character == ";" and depth == 1:
                segment = comments_removed[member_start:position]
                parsed_signature = self._method_signature(segment)
                if parsed_signature:
                    (
                        name,
                        return_type,
                        parameters_text,
                        annotations,
                        signature_offset,
                        signature,
                    ) = parsed_signature
                    if name != class_name:
                        absolute_start = member_start + signature_offset
                        qualified_name = (
                            f"{package_name}.{class_name}.{name}"
                            if package_name
                            else f"{class_name}.{name}"
                        )
                        methods.append(
                            JavaMethod(
                                name=name,
                                qualified_name=qualified_name,
                                class_name=class_name,
                                package_name=package_name,
                                file_path=file_path,
                                return_type=return_type,
                                parameters_text=parameters_text,
                                annotations=annotations,
                                start_offset=absolute_start,
                                body_start=position,
                                body_end=position,
                                start_line=_line_number(source, absolute_start),
                                end_line=_line_number(source, position),
                                signature=signature.strip(),
                                source_excerpt=source[absolute_start : position + 1][:4000],
                                summary=_java_doc_summary(source[member_start:absolute_start]),
                            )
                        )
                member_start = position + 1
            position += 1
        return methods

    @staticmethod
    def _method_signature(
        segment: str,
    ) -> tuple[str, str | None, str, list[JavaAnnotation], int, str] | None:
        close_paren = segment.rfind(")")
        if close_paren < 0:
            return None
        open_paren = _matching_delimiter_backward(
            segment,
            close_paren,
            "(",
            ")",
        )
        if open_paren < 0:
            return None
        name_match = re.search(r"([A-Za-z_$][\w$]*)\s*$", segment[:open_paren])
        if not name_match:
            return None
        name = name_match.group(1)
        if name in CONTROL_CALLS:
            return None

        annotations = _extract_annotations(segment)
        signature_start = min(
            (annotation.start for annotation in annotations),
            default=0,
        )
        declaration = _remove_annotation_ranges(segment, annotations)
        declaration_name = re.search(
            rf"\b{re.escape(name)}\s*\(",
            declaration,
        )
        if not declaration_name:
            return None
        prefix = declaration[: declaration_name.start()].strip()
        tokens = prefix.replace("\n", " ").split()
        tokens = [token for token in tokens if token not in JAVA_MODIFIERS]
        if not tokens:
            return None
        return_type = " ".join(tokens).strip() or None
        if return_type and return_type.startswith("<") and ">" in return_type:
            return_type = return_type.split(">", 1)[1].strip() or None
        parameters_text = segment[open_paren + 1 : close_paren]
        signature = segment[signature_start:].strip()
        return (
            name,
            return_type,
            parameters_text,
            annotations,
            signature_start,
            signature,
        )

    @staticmethod
    def _parse_fields(
        source: str,
        body_start: int,
        body_end: int,
        method_ranges: list[tuple[int, int]],
        imports: dict[str, str],
    ) -> dict[str, str]:
        field_pattern = re.compile(
            r"\b(?:public|protected|private)\s+"
            r"(?:(?:static|final|transient|volatile)\s+)*"
            r"(?P<type>[A-Za-z_$][\w$]*(?:\s*<[^;=]+?>)?(?:\[\])?)\s+"
            r"(?P<name>[A-Za-z_$][\w$]*)\s*(?:=[^;]*)?;"
        )
        fields: dict[str, str] = {}
        for match in field_pattern.finditer(source, body_start, body_end):
            if any(start <= match.start() <= end for start, end in method_ranges):
                continue
            type_name = _raw_type(match.group("type"))
            fields[match.group("name")] = imports.get(type_name, type_name)
        return fields

    @staticmethod
    def _implements(declaration: str, imports: dict[str, str]) -> list[str]:
        match = re.search(r"\bimplements\s+([^{]+)", declaration)
        if not match:
            return []
        values = []
        for item in match.group(1).split(","):
            name = _raw_type(item.strip())
            if name:
                values.append(imports.get(name, name))
        return values

    def _build_endpoints(
        self,
        classes: list[JavaClass],
    ) -> list[dict[str, Any]]:
        endpoints: list[dict[str, Any]] = []
        for java_class in classes:
            if not ({"RestController", "Controller"} & java_class.annotation_names):
                continue
            class_paths = self._mapping_paths(java_class.annotations) or [""]
            category = _controller_category(java_class)
            for method in java_class.methods:
                mappings = self._method_mappings(method.annotations)
                business_steps = _business_steps(method, java_class)
                business_logic = _business_logic(
                    method,
                    category=category,
                    steps=business_steps,
                )
                for http_methods, method_paths in mappings:
                    for http_method in http_methods:
                        for class_path in class_paths:
                            for method_path in method_paths or [""]:
                                endpoints.append(
                                    {
                                        "http_method": http_method,
                                        "path": _join_paths(
                                            class_path,
                                            method_path,
                                        ),
                                        "function_name": method.name,
                                        "qualified_name": method.qualified_name,
                                        "module_name": category,
                                        "file_path": method.file_path,
                                        "start_line": method.start_line,
                                        "end_line": method.end_line,
                                        "summary": method.summary,
                                        "tags": [category],
                                        "parameters": self._parameters(method.parameters_text),
                                        "response_type": method.return_type,
                                        "dependencies": [],
                                        "extra_metadata": {
                                            "language": "java",
                                            "framework": "spring",
                                            "controllerClass": (java_class.qualified_name),
                                            "controllerName": java_class.name,
                                            "packageName": java_class.package_name,
                                            "category": category,
                                            "businessLogic": business_logic,
                                            "businessSteps": business_steps,
                                            "sourceSignature": method.signature,
                                            "mappingAnnotations": [
                                                annotation.name
                                                for annotation in method.annotations
                                                if annotation.name.rsplit(".", 1)[-1]
                                                in {
                                                    *HTTP_ANNOTATIONS,
                                                    "RequestMapping",
                                                }
                                            ],
                                        },
                                    }
                                )
        endpoints.sort(
            key=lambda item: (
                item["path"],
                item["http_method"],
                item["qualified_name"],
            )
        )
        unique_endpoints: dict[tuple[str, str, str], dict[str, Any]] = {}
        for endpoint in endpoints:
            identity = (
                endpoint["http_method"],
                endpoint["path"],
                endpoint["qualified_name"],
            )
            unique_endpoints.setdefault(identity, endpoint)
        return list(unique_endpoints.values())

    def _method_mappings(
        self,
        annotations: Iterable[JavaAnnotation],
    ) -> list[tuple[list[str], list[str]]]:
        mappings: list[tuple[list[str], list[str]]] = []
        for annotation in annotations:
            name = annotation.name.rsplit(".", 1)[-1]
            if name in HTTP_ANNOTATIONS:
                mappings.append(
                    (
                        HTTP_ANNOTATIONS[name],
                        _annotation_paths(annotation.arguments) or [""],
                    )
                )
            elif name == "RequestMapping":
                methods = [
                    value.upper()
                    for value in re.findall(
                        r"RequestMethod\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)",
                        annotation.arguments,
                        flags=re.IGNORECASE,
                    )
                ]
                mappings.append(
                    (
                        methods or ["ANY"],
                        _annotation_paths(annotation.arguments) or [""],
                    )
                )
        return mappings

    @staticmethod
    def _mapping_paths(
        annotations: Iterable[JavaAnnotation],
    ) -> list[str]:
        for annotation in annotations:
            if annotation.name.rsplit(".", 1)[-1] == "RequestMapping":
                return _annotation_paths(annotation.arguments)
        return []

    @staticmethod
    def _parameters(parameters_text: str) -> list[dict[str, Any]]:
        parameters: list[dict[str, Any]] = []
        for raw_parameter in _split_top_level(parameters_text, ","):
            value = raw_parameter.strip()
            if not value:
                continue
            annotations = _extract_annotations(value)
            clean = _remove_annotation_ranges(value, annotations)
            clean = re.sub(r"\bfinal\b", "", clean).strip()
            name_match = re.search(r"([A-Za-z_$][\w$]*)\s*$", clean)
            if not name_match:
                continue
            name = name_match.group(1)
            type_name = clean[: name_match.start()].strip() or None
            location = "UNKNOWN"
            required = True
            annotation_name = None
            for annotation in annotations:
                short_name = annotation.name.rsplit(".", 1)[-1]
                if short_name in PARAMETER_LOCATIONS:
                    annotation_name = short_name
                    location = PARAMETER_LOCATIONS[short_name]
                    if re.search(
                        r"\brequired\s*=\s*false\b",
                        annotation.arguments,
                        flags=re.IGNORECASE,
                    ):
                        required = False
                    explicit_name = _annotation_paths(annotation.arguments)
                    if explicit_name:
                        name = explicit_name[0]
                    break
            parameters.append(
                {
                    "name": name,
                    "location": location,
                    "type": type_name,
                    "required": required,
                    "default": None,
                    "annotation": annotation_name,
                }
            )
        return parameters

    def _build_call_graph(
        self,
        classes: list[JavaClass],
        endpoints: list[dict[str, Any]],
    ) -> CallGraphResult:
        result = CallGraphResult()
        endpoint_names = {endpoint["qualified_name"] for endpoint in endpoints}
        class_by_simple = {java_class.name: java_class for java_class in classes}
        implementations: dict[str, list[JavaClass]] = defaultdict(list)
        methods_by_class_and_name: dict[tuple[str, str], list[JavaMethod]] = defaultdict(list)
        methods_by_name: dict[str, list[JavaMethod]] = defaultdict(list)

        for java_class in classes:
            for implemented in java_class.implements:
                implementations[_raw_type(implemented)].append(java_class)
            for method in java_class.methods:
                methods_by_class_and_name[(java_class.name, method.name)].append(method)
                methods_by_name[method.name].append(method)
                self._add_method_node(
                    result,
                    java_class,
                    method,
                    endpoint_names,
                )

        class_for_method = {
            method.qualified_name: java_class
            for java_class in classes
            for method in java_class.methods
        }
        for java_class in classes:
            for method in java_class.methods:
                body = java_class.structure[method.body_start + 1 : method.body_end]
                for call in CALL_PATTERN.finditer(body):
                    called_name = call.group("method")
                    receiver = call.group("receiver")
                    if called_name in CONTROL_CALLS:
                        continue
                    target = self._resolve_call(
                        java_class=java_class,
                        method_name=called_name,
                        receiver=receiver,
                        class_by_simple=class_by_simple,
                        implementations=implementations,
                        methods_by_class_and_name=methods_by_class_and_name,
                        methods_by_name=methods_by_name,
                    )
                    if not target or target.qualified_name == method.qualified_name:
                        continue
                    target_class = class_for_method.get(target.qualified_name)
                    if target_class:
                        self._add_method_node(
                            result,
                            target_class,
                            target,
                            endpoint_names,
                        )
                    absolute_offset = method.body_start + 1 + call.start()
                    line_number = _line_number(java_class.source, absolute_offset)
                    evidence = (
                        java_class.source[
                            absolute_offset : min(
                                method.body_end,
                                absolute_offset + 300,
                            )
                        ]
                        .splitlines()[0]
                        .strip()
                    )
                    _add_relation(
                        result,
                        source_key=method.stable_key,
                        target_key=target.stable_key,
                        relation_type="CALLS",
                        confidence="HIGH" if receiver else "MEDIUM",
                        file_path=method.file_path,
                        line_number=line_number,
                        column_number=1,
                        evidence=evidence,
                        metadata={
                            "language": "java",
                            "receiver": receiver,
                            "sourceName": method.name,
                            "targetName": target.name,
                            "targetQualifiedName": target.qualified_name,
                        },
                    )

        self._add_api_nodes(result, endpoints)
        return result

    @staticmethod
    def _resolve_call(
        *,
        java_class: JavaClass,
        method_name: str,
        receiver: str | None,
        class_by_simple: dict[str, JavaClass],
        implementations: dict[str, list[JavaClass]],
        methods_by_class_and_name: dict[tuple[str, str], list[JavaMethod]],
        methods_by_name: dict[str, list[JavaMethod]],
    ) -> JavaMethod | None:
        candidate_classes: list[JavaClass] = []
        if not receiver or receiver == "this":
            candidate_classes.append(java_class)
        elif receiver in java_class.fields:
            raw_field_type = _raw_type(java_class.fields[receiver])
            direct = class_by_simple.get(raw_field_type)
            candidate_classes.extend(implementations.get(raw_field_type, []))
            if direct:
                candidate_classes.append(direct)
            interface_name = raw_field_type.removeprefix("I")
            candidate_classes.extend(
                candidate
                for candidate in class_by_simple.values()
                if candidate.name
                in {
                    f"{raw_field_type}Impl",
                    f"{interface_name}ServiceImpl",
                    f"{interface_name}Impl",
                }
            )
        elif receiver[:1].isupper():
            direct = class_by_simple.get(receiver)
            if direct:
                candidate_classes.append(direct)

        seen: set[str] = set()
        candidates: list[JavaMethod] = []
        for candidate_class in candidate_classes:
            if candidate_class.qualified_name in seen:
                continue
            seen.add(candidate_class.qualified_name)
            candidates.extend(
                methods_by_class_and_name.get(
                    (candidate_class.name, method_name),
                    [],
                )
            )
        if len(candidates) == 1:
            return candidates[0]
        global_candidates = methods_by_name.get(method_name, [])
        if not receiver and len(global_candidates) == 1:
            return global_candidates[0]
        return candidates[0] if candidates else None

    @staticmethod
    def _add_method_node(
        result: CallGraphResult,
        java_class: JavaClass,
        method: JavaMethod,
        endpoint_names: set[str],
    ) -> None:
        annotations = java_class.annotation_names
        if method.qualified_name in endpoint_names:
            node_type = "ROUTE_FUNCTION"
        elif "Service" in annotations or "Component" in annotations:
            node_type = "SERVICE"
        elif {"Repository", "Mapper"} & annotations or java_class.name.endswith(
            ("Repository", "Mapper")
        ):
            node_type = "REPOSITORY"
        else:
            node_type = "METHOD"
        result.nodes.setdefault(
            method.stable_key,
            {
                "stable_key": method.stable_key,
                "node_type": node_type,
                "name": method.name,
                "qualified_name": method.qualified_name,
                "module_name": method.package_name,
                "file_path": method.file_path,
                "start_line": method.start_line,
                "end_line": method.end_line,
                "signature": method.signature,
                "source_excerpt": method.source_excerpt,
                "extra_metadata": {
                    "language": "java",
                    "className": java_class.name,
                    "classQualifiedName": java_class.qualified_name,
                    "packageName": java_class.package_name,
                    "layer": node_type,
                    "businessLogic": _business_logic(
                        method,
                        category=_class_category(java_class),
                        steps=_business_steps(method, java_class),
                    ),
                    "businessSteps": _business_steps(method, java_class),
                    "returnType": method.return_type,
                    "parameterSummary": method.parameters_text.strip(),
                    "annotations": [
                        annotation.name.rsplit(".", 1)[-1] for annotation in method.annotations
                    ],
                },
            },
        )

    @staticmethod
    def _add_api_nodes(
        result: CallGraphResult,
        endpoints: list[dict[str, Any]],
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
            result.nodes.setdefault(
                api_key,
                {
                    "stable_key": api_key,
                    "node_type": "API",
                    "name": f"{endpoint['http_method']} {endpoint['path']}",
                    "qualified_name": endpoint["qualified_name"],
                    "module_name": endpoint["module_name"],
                    "file_path": endpoint["file_path"],
                    "start_line": endpoint["start_line"],
                    "end_line": endpoint["end_line"],
                    "signature": None,
                    "source_excerpt": None,
                    "extra_metadata": {
                        "language": "java",
                        "framework": "spring",
                        "httpMethod": endpoint["http_method"],
                        "path": endpoint["path"],
                        "tags": endpoint["tags"],
                    },
                },
            )
            route_key = f"java-method:{endpoint['qualified_name']}"
            if route_key in result.nodes:
                _add_relation(
                    result,
                    source_key=api_key,
                    target_key=route_key,
                    relation_type="ROUTES_TO",
                    confidence="CONFIRMED",
                    file_path=endpoint["file_path"],
                    line_number=endpoint["start_line"],
                    column_number=1,
                    evidence=(f"@SpringMapping {endpoint['http_method']} {endpoint['path']}"),
                    metadata={"language": "java", "framework": "spring"},
                )

    @staticmethod
    def _read_source(path: Path) -> str:
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")


def _sanitize_java(source: str, *, mask_strings: bool) -> str:
    output = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if current == "/" and following == "/":
                output[index] = output[index + 1] = " "
                state = "line_comment"
                index += 2
                continue
            if current == "/" and following == "*":
                output[index] = output[index + 1] = " "
                state = "block_comment"
                index += 2
                continue
            if current in {'"', "'"}:
                quote = current
                if mask_strings:
                    output[index] = " "
                state = "string"
        elif state == "line_comment":
            if current == "\n":
                state = "code"
            else:
                output[index] = " "
        elif state == "block_comment":
            if current == "*" and following == "/":
                output[index] = output[index + 1] = " "
                state = "code"
                index += 2
                continue
            if current != "\n":
                output[index] = " "
        elif state == "string":
            if current == "\\":
                if mask_strings:
                    output[index] = " "
                    if index + 1 < len(output) and source[index + 1] != "\n":
                        output[index + 1] = " "
                index += 2
                continue
            if current == quote:
                if mask_strings:
                    output[index] = " "
                state = "code"
            elif mask_strings and current != "\n":
                output[index] = " "
        index += 1
    return "".join(output)


def _extract_annotations(text: str) -> list[JavaAnnotation]:
    annotations: list[JavaAnnotation] = []
    position = 0
    while position < len(text):
        match = re.search(r"@([\w.]+)", text[position:])
        if not match:
            break
        start = position + match.start()
        name = match.group(1)
        end = position + match.end()
        cursor = end
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        arguments = ""
        if cursor < len(text) and text[cursor] == "(":
            close = _matching_delimiter(text, cursor, "(", ")")
            if close < 0:
                close = len(text) - 1
            arguments = text[cursor + 1 : close]
            end = close + 1
        annotations.append(
            JavaAnnotation(
                name=name,
                arguments=arguments,
                start=start,
                end=end,
            )
        )
        position = max(end, start + 1)
    return annotations


def _remove_annotation_ranges(
    text: str,
    annotations: Iterable[JavaAnnotation],
) -> str:
    result = list(text)
    for annotation in annotations:
        for index in range(annotation.start, min(annotation.end, len(result))):
            if result[index] != "\n":
                result[index] = " "
    return "".join(result)


def _matching_delimiter(
    text: str,
    start: int,
    opening: str,
    closing: str,
) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _matching_delimiter_backward(
    text: str,
    end: int,
    opening: str,
    closing: str,
) -> int:
    depth = 0
    for index in range(end, -1, -1):
        if text[index] == closing:
            depth += 1
        elif text[index] == opening:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _split_top_level(text: str, separator: str) -> list[str]:
    values: list[str] = []
    start = 0
    depths = {"(": 0, "[": 0, "{": 0, "<": 0}
    pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
    quote: str | None = None
    escaped = False
    for index, character in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character in depths:
            depths[character] += 1
        elif character in pairs:
            key = pairs[character]
            depths[key] = max(0, depths[key] - 1)
        elif character == separator and not any(depths.values()):
            values.append(text[start:index])
            start = index + 1
    values.append(text[start:])
    return values


def _annotation_paths(arguments: str) -> list[str]:
    if not arguments:
        return []
    path_expression = arguments
    assigned = re.search(
        r"\b(?:value|path|name)\s*=\s*(\{[^}]*\}|\"(?:\\.|[^\"\\])*\")",
        arguments,
        flags=re.DOTALL,
    )
    if assigned:
        path_expression = assigned.group(1)
    paths = []
    for match in STRING_LITERAL.finditer(path_expression):
        value = bytes(match.group(1), "utf-8").decode(
            "unicode_escape",
            errors="replace",
        )
        if value.startswith("/") or len(STRING_LITERAL.findall(arguments)) == 1:
            paths.append(value)
    return list(dict.fromkeys(paths))


def _join_paths(prefix: str, path: str) -> str:
    values = [value.strip("/") for value in (prefix, path) if value.strip("/")]
    return "/" + "/".join(values) if values else "/"


def _raw_type(type_name: str) -> str:
    value = re.sub(r"<.*>", "", type_name).strip()
    value = value.replace("[]", "").strip()
    return value.rsplit(".", 1)[-1]


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, max(0, offset)) + 1


def _java_doc_summary(text: str) -> str | None:
    matches = list(re.finditer(r"/\*\*(.*?)\*/", text, flags=re.DOTALL))
    if not matches:
        return None
    body = matches[-1].group(1)
    lines = []
    for line in body.splitlines():
        value = re.sub(r"^\s*\*\s?", "", line).strip()
        if not value or value.startswith("@"):
            continue
        lines.append(value)
    return " ".join(lines)[:1000] or None


def _controller_category(java_class: JavaClass) -> str:
    summary = html.unescape(java_class.summary or "")
    summary = re.sub(r"<[^>]*>", " ", summary)
    summary = re.sub(r"\s+", " ", summary).strip()
    if summary:
        summary = re.sub(
            r"(?:Controller|控制器)\s*$",
            "",
            summary,
            flags=re.IGNORECASE,
        ).strip()
        if summary and len(summary) <= 40:
            return summary
    return re.sub(r"Controller$", "", java_class.name) or java_class.name


def _class_category(java_class: JavaClass) -> str:
    name = java_class.name
    for suffix in (
        "Controller",
        "ServiceImpl",
        "Service",
        "Repository",
        "Mapper",
        "Impl",
    ):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name or java_class.name


def _business_steps(method: JavaMethod, java_class: JavaClass) -> list[str]:
    source = method.source_excerpt
    expected_opening = method.body_start - method.start_offset
    opening = expected_opening if 0 <= expected_opening < len(source) else source.find("{")
    body = source[opening + 1 :] if opening >= 0 else source
    structure = _sanitize_java(body, mask_strings=True)
    steps: list[str] = []

    if re.search(r"\b(if|switch)\s*\(", structure):
        steps.append("根据输入与业务状态执行条件判断")
    if re.search(r"\b(for|while)\s*\(", structure) or ".stream(" in structure:
        steps.append("遍历或聚合业务数据")

    seen_calls: set[str] = set()
    for call in CALL_PATTERN.finditer(structure):
        receiver = call.group("receiver")
        called_name = call.group("method")
        if called_name in CONTROL_CALLS or (
            called_name == method.name and receiver in {None, "this"}
        ):
            continue
        if receiver in {"log", "logger"}:
            continue
        if receiver and receiver in java_class.fields:
            owner = _raw_type(java_class.fields[receiver])
            description = f"调用 {owner}.{called_name}()"
        elif receiver and receiver[:1].isupper():
            description = f"调用 {receiver}.{called_name}() 工具或静态能力"
        elif receiver:
            description = f"调用 {receiver}.{called_name}()"
        else:
            description = f"执行 {called_name}() 处理"
        if description in seen_calls:
            continue
        seen_calls.add(description)
        steps.append(description)
        if len(steps) >= 8:
            break

    if re.search(r"\breturn\b", structure):
        return_type = method.return_type or "结果"
        steps.append(f"组装并返回 {return_type}")
    return steps[:9]


def _business_logic(
    method: JavaMethod,
    *,
    category: str,
    steps: list[str],
) -> str:
    summary = (method.summary or "").strip()
    if not summary:
        summary = f"处理 {category} 的 {method.name} 业务"
    call_steps = [step for step in steps if step.startswith("调用")]
    if call_steps:
        call_summary = "、".join(re.sub(r"^调用\s+", "", step) for step in call_steps[:3])
        summary = f"{summary}。主要协作：{call_summary}"
    if method.return_type and method.return_type != "void":
        summary = f"{summary}；最终返回 {method.return_type}"
    return summary.rstrip("。；") + "。"


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
    metadata: dict[str, Any],
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
            "extra_metadata": metadata,
        },
    )
