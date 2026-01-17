from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING

from pybtex.database import BibliographyData, Entry
from pybtex.database.input import bibtex as bibtex_input
from pybtex.database.output import bibtex as bibtex_output

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass
class BibEntry:
    key: str
    entry_type: str
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def author(self) -> str:
        return self.fields.get("author", "")

    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def year(self) -> str:
        return self.fields.get("year", "")

    def to_bibtex(self) -> str:
        entry = Entry(self.entry_type, fields=self.fields)
        bib_data = BibliographyData(entries={self.key: entry})
        output = StringIO()
        writer = bibtex_output.Writer()
        writer.write_stream(bib_data, output)
        return output.getvalue().strip()

    @classmethod
    def from_pybtex(cls, key: str, entry: Entry) -> BibEntry:
        fields: dict[str, str] = {}

        for field_name, field_value in entry.fields.items():
            fields[field_name.lower()] = str(field_value)

        if "author" in entry.persons:
            authors = entry.persons["author"]
            author_strs = [_format_person(p) for p in authors]
            fields["author"] = " and ".join(author_strs)

        if "editor" in entry.persons:
            editors = entry.persons["editor"]
            editor_strs = [_format_person(p) for p in editors]
            fields["editor"] = " and ".join(editor_strs)

        return cls(key=key, entry_type=entry.type, fields=fields)


def _format_person(person: object) -> str:
    last = " ".join(getattr(person, "last_names", []))
    first = " ".join(getattr(person, "first_names", []))
    if last and first:
        return f"{last}, {first}"
    return last or first


def parse_bibtex(content: str) -> list[BibEntry]:
    parser = bibtex_input.Parser()
    bib_data = parser.parse_string(content)
    return [BibEntry.from_pybtex(key, entry) for key, entry in bib_data.entries.items()]


def parse_bibtex_file(path: Path) -> list[BibEntry]:
    parser = bibtex_input.Parser()
    bib_data = parser.parse_file(str(path))
    return [BibEntry.from_pybtex(key, entry) for key, entry in bib_data.entries.items()]


def generate_citation_key(author: str, year: str, existing_keys: set[str] | None = None) -> str:
    existing = existing_keys or set()

    author_part = ""
    if author:
        first_author = author.split(" and ")[0].strip()
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            parts = first_author.split()
            last_name = parts[-1] if parts else ""

        last_name = re.sub(r"[^a-zA-Z]", "", last_name).lower()
        author_part = last_name[:10] if last_name else "unknown"

    year_part = year if year else "nd"
    base_key = f"{author_part}{year_part}"

    if base_key not in existing:
        return base_key

    suffix = ord("a")
    while f"{base_key}{chr(suffix)}" in existing and suffix <= ord("z"):
        suffix += 1

    return f"{base_key}{chr(suffix)}"


def find_duplicates(entries: Sequence[BibEntry]) -> list[tuple[BibEntry, BibEntry]]:
    duplicates: list[tuple[BibEntry, BibEntry]] = []
    entries_list = list(entries)

    for i, e1 in enumerate(entries_list):
        for e2 in entries_list[i + 1 :]:
            if e1.key.lower() == e2.key.lower():
                duplicates.append((e1, e2))
                continue

            t1 = _normalize_title(e1.title)
            t2 = _normalize_title(e2.title)
            if t1 and t2 and t1 == t2:
                duplicates.append((e1, e2))
                continue

            if e1.year == e2.year and e1.year:
                a1 = _normalize_authors(e1.author)
                a2 = _normalize_authors(e2.author)
                if a1 and a2 and a1 == a2:
                    duplicates.append((e1, e2))

    return duplicates


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _normalize_authors(authors: str) -> str:
    authors = authors.lower()
    authors = re.sub(r"[^a-z\s,]", "", authors)
    authors = re.sub(r"\s+", " ", authors).strip()
    return authors


def merge_entries(existing: list[BibEntry], new: list[BibEntry]) -> list[BibEntry]:
    existing_keys = {e.key.lower() for e in existing}
    existing_titles = {_normalize_title(e.title) for e in existing if e.title}

    result = list(existing)
    added_keys: set[str] = set()

    for entry in new:
        normalized_title = _normalize_title(entry.title)

        if entry.key.lower() in existing_keys:
            continue
        if normalized_title and normalized_title in existing_titles:
            continue

        if entry.key.lower() in added_keys:
            new_key = generate_citation_key(entry.author, entry.year, existing_keys | added_keys)
            updated_entry = BibEntry(key=new_key, entry_type=entry.entry_type, fields=entry.fields)
        else:
            updated_entry = entry

        result.append(updated_entry)
        added_keys.add(updated_entry.key.lower())
        if normalized_title:
            existing_titles.add(normalized_title)

    return result


def write_bibtex_file(path: Path, entries: Sequence[BibEntry]) -> None:
    bib_data = BibliographyData()
    for entry in entries:
        pybtex_entry = Entry(entry.entry_type, fields=entry.fields)
        bib_data.entries[entry.key] = pybtex_entry

    writer = bibtex_output.Writer()
    writer.write_file(bib_data, str(path))


class BibManager:
    def __init__(self, bib_path: Path | None = None) -> None:
        self.bib_path = bib_path
        self._entries: list[BibEntry] = []
        if bib_path and bib_path.exists():
            self._entries = parse_bibtex_file(bib_path)

    @property
    def entries(self) -> list[BibEntry]:
        return self._entries

    def get_keys(self) -> list[str]:
        return [e.key for e in self._entries]

    def get(self, key: str) -> BibEntry | None:
        key_lower = key.lower()
        for entry in self._entries:
            if entry.key.lower() == key_lower:
                return entry
        return None

    def search(self, query: str) -> list[BibEntry]:
        query_lower = query.lower()
        results: list[BibEntry] = []

        for entry in self._entries:
            if query_lower in entry.key.lower():
                results.append(entry)
                continue
            if query_lower in entry.title.lower():
                results.append(entry)
                continue
            if query_lower in entry.author.lower():
                results.append(entry)

        return results

    def add(self, entry: BibEntry) -> bool:
        if self.get(entry.key):
            return False

        self._entries.append(entry)
        return True

    def add_many(self, entries: list[BibEntry]) -> int:
        merged = merge_entries(self._entries, entries)
        added = len(merged) - len(self._entries)
        self._entries = merged
        return added

    def find_duplicates(self) -> list[tuple[BibEntry, BibEntry]]:
        return find_duplicates(self._entries)

    def save(self, path: Path | None = None) -> None:
        target = path or self.bib_path
        if target is None:
            msg = "No path specified for saving"
            raise ValueError(msg)
        write_bibtex_file(target, self._entries)
