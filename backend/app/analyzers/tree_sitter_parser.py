from __future__ import annotations

import tokenize
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree


@dataclass(frozen=True, slots=True)
class ParsedPythonFile:
    path: Path
    source: bytes
    encoding: str
    tree: Tree

    @property
    def root_node(self) -> Node:
        return self.tree.root_node

    def text(self, node: Node) -> str:
        return self.source[node.start_byte : node.end_byte].decode(
            self.encoding,
            errors="replace",
        )


class TreeSitterPythonParser:
    """Tree-sitter Python 解析器；不会 import 或执行目标源码。"""

    def __init__(self) -> None:
        language = Language(tree_sitter_python.language())
        self.parser = Parser(language)

    def parse_file(self, path: Path) -> ParsedPythonFile:
        source = path.read_bytes()
        encoding = self._detect_encoding(source)
        return ParsedPythonFile(
            path=path,
            source=source,
            encoding=encoding,
            tree=self.parser.parse(source),
        )

    @staticmethod
    def _detect_encoding(source: bytes) -> str:
        try:
            encoding, _ = tokenize.detect_encoding(BytesIO(source).readline)
            return encoding
        except (SyntaxError, UnicodeDecodeError):
            return "utf-8"
