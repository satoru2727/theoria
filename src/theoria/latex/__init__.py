from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LatexLabel:
    name: str
    line: int
    file: Path


@dataclass
class LatexRef:
    name: str
    line: int
    file: Path
    ref_type: str


@dataclass
class LatexSection:
    level: str
    title: str
    line: int
    file: Path
    label: str | None = None


@dataclass
class LatexInclude:
    path: str
    line: int
    file: Path
    include_type: str
    resolved_path: Path | None = None


@dataclass
class DocumentStructure:
    document_class: str | None = None
    packages: list[str] = field(default_factory=list)
    sections: list[LatexSection] = field(default_factory=list)
    labels: list[LatexLabel] = field(default_factory=list)
    refs: list[LatexRef] = field(default_factory=list)
    includes: list[LatexInclude] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)


SECTION_LEVELS = [
    "part",
    "chapter",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
]

REF_COMMANDS = ["ref", "eqref", "pageref", "autoref", "cref", "Cref", "vref", "nameref"]


class LatexParser:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._parsed_files: set[Path] = set()

    def parse(self, entry_file: Path | None = None) -> DocumentStructure:
        if entry_file is None:
            entry_file = self._find_main_file()
            if entry_file is None:
                return DocumentStructure()

        entry_file = entry_file.resolve()
        structure = DocumentStructure()
        self._parsed_files.clear()
        self._parse_file(entry_file, structure)
        return structure

    def _find_main_file(self) -> Path | None:
        tex_files = list(self.root.glob("*.tex"))
        for f in tex_files:
            if f.name.lower() in ("main.tex", "root.tex", "document.tex"):
                return f

        for f in tex_files:
            content = f.read_text(errors="ignore")
            if r"\documentclass" in content and r"\begin{document}" in content:
                return f

        return tex_files[0] if tex_files else None

    def _parse_file(self, file_path: Path, structure: DocumentStructure) -> None:
        if file_path in self._parsed_files:
            return
        self._parsed_files.add(file_path)
        structure.files.append(file_path)

        try:
            content = file_path.read_text(errors="ignore")
        except OSError:
            return

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.split("%")[0]
            self._parse_line(stripped, line_num, file_path, structure)

    def _parse_line(
        self, stripped: str, line_num: int, file_path: Path, structure: DocumentStructure
    ) -> None:
        if structure.document_class is None:
            match = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", stripped)
            if match:
                structure.document_class = match.group(1)

        for match in re.finditer(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", stripped):
            packages = [p.strip() for p in match.group(1).split(",")]
            structure.packages.extend(packages)

        self._parse_sections(stripped, line_num, file_path, structure)
        self._parse_labels_and_refs(stripped, line_num, file_path, structure)
        self._parse_includes(stripped, line_num, file_path, structure)

    def _parse_sections(
        self, stripped: str, line_num: int, file_path: Path, structure: DocumentStructure
    ) -> None:
        for level in SECTION_LEVELS:
            pattern = rf"\\{level}\*?\{{([^}}]+)\}}"
            match = re.search(pattern, stripped)
            if match:
                section = LatexSection(
                    level=level,
                    title=match.group(1),
                    line=line_num,
                    file=file_path,
                )
                label_match = re.search(r"\\label\{([^}]+)\}", stripped[match.end() :])
                if label_match:
                    section.label = label_match.group(1)
                structure.sections.append(section)

    def _parse_labels_and_refs(
        self, stripped: str, line_num: int, file_path: Path, structure: DocumentStructure
    ) -> None:
        for match in re.finditer(r"\\label\{([^}]+)\}", stripped):
            structure.labels.append(LatexLabel(name=match.group(1), line=line_num, file=file_path))

        for ref_cmd in REF_COMMANDS:
            for match in re.finditer(rf"\\{ref_cmd}\{{([^}}]+)\}}", stripped):
                structure.refs.append(
                    LatexRef(
                        name=match.group(1),
                        line=line_num,
                        file=file_path,
                        ref_type=ref_cmd,
                    )
                )

    def _parse_includes(
        self, stripped: str, line_num: int, file_path: Path, structure: DocumentStructure
    ) -> None:
        for match in re.finditer(r"\\(input|include|subfile)\{([^}]+)\}", stripped):
            inc_type = match.group(1)
            inc_path = match.group(2)
            include = LatexInclude(
                path=inc_path,
                line=line_num,
                file=file_path,
                include_type=inc_type,
            )

            resolved = self._resolve_include(file_path, inc_path)
            include.resolved_path = resolved
            structure.includes.append(include)

            if resolved and resolved.exists():
                self._parse_file(resolved, structure)

    def _resolve_include(self, from_file: Path, include_path: str) -> Path | None:
        if not include_path.endswith(".tex"):
            include_path = include_path + ".tex"

        base_dir = from_file.parent

        candidates = [
            base_dir / include_path,
            self.root / include_path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        return None


def resolve_includes(entry_file: Path) -> str:
    parser = LatexParser(entry_file.parent)
    structure = parser.parse(entry_file)

    content = entry_file.read_text(errors="ignore")

    for include in reversed(structure.includes):
        if include.file != entry_file:
            continue
        if include.resolved_path and include.resolved_path.exists():
            included_content = include.resolved_path.read_text(errors="ignore")
            pattern = rf"\\{include.include_type}\{{{re.escape(include.path)}\}}"
            content = re.sub(pattern, included_content, content, count=1)

    return content


@dataclass
class RefIssue:
    issue_type: str
    name: str
    locations: list[tuple[Path, int]]


def check_label_ref_integrity(structure: DocumentStructure) -> list[RefIssue]:
    issues: list[RefIssue] = []

    label_names = {label.name for label in structure.labels}
    label_locations: dict[str, list[tuple[Path, int]]] = {}
    for label in structure.labels:
        if label.name not in label_locations:
            label_locations[label.name] = []
        label_locations[label.name].append((label.file, label.line))

    ref_names = {ref.name for ref in structure.refs}
    ref_locations: dict[str, list[tuple[Path, int]]] = {}
    for ref in structure.refs:
        if ref.name not in ref_locations:
            ref_locations[ref.name] = []
        ref_locations[ref.name].append((ref.file, ref.line))

    for ref_name in ref_names:
        if ref_name not in label_names:
            issues.append(
                RefIssue(
                    issue_type="undefined",
                    name=ref_name,
                    locations=ref_locations[ref_name],
                )
            )

    for label_name, locs in label_locations.items():
        if len(locs) > 1:
            issues.append(
                RefIssue(
                    issue_type="duplicate",
                    name=label_name,
                    locations=locs,
                )
            )

    for label_name in label_names:
        if label_name not in ref_names:
            issues.append(
                RefIssue(
                    issue_type="unused",
                    name=label_name,
                    locations=label_locations[label_name],
                )
            )

    return issues


def parse_document(entry_file: Path) -> DocumentStructure:
    parser = LatexParser(entry_file.parent)
    return parser.parse(entry_file)
