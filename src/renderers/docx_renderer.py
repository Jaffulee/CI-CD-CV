"""DOCX renderer for resolved CV documents.

The renderer writes a small WordprocessingML package directly. This avoids a
runtime dependency on Word, LibreOffice, Pandoc, or python-docx while keeping the
output deterministic from the resolved CV model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from src.resolver.document_resolver import ResolvedDocument, ResolvedEntry
from src.utils.formatting import typographic_date_range
from src.utils.paths import ensure_parent_dir


ACCENT = "1F6F78"
MUTED = "555555"
RULE = "9FB7BC"


@dataclass
class DocxBuilder:
    relationships: list[tuple[str, str, str]] = field(default_factory=list)
    next_relationship_id: int = 1

    def hyperlink_relationship(self, url: str) -> str:
        relationship_id = f"rId{self.next_relationship_id}"
        self.next_relationship_id += 1
        self.relationships.append((relationship_id, url, "External"))
        return relationship_id


def render_docx(document: ResolvedDocument) -> dict[str, str | bytes]:
    builder = DocxBuilder()
    body_parts = [
        _paragraph(document.title or "", style="DocumentTitle") if document.title else "",
        _paragraph(str(document.person.get("display_name") or document.person.get("full_name") or ""), style="Name"),
    ]

    if document.headline:
        body_parts.append(_paragraph(document.headline, style="Headline"))
    if document.contact:
        body_parts.append(_contact_table(document.contact))
    if document.prompt_injection and document.prompt_injection_text:
        body_parts.append(_paragraph("Prompt injection demonstration payload (visible):", style="PromptDemoLabel"))
        body_parts.append(_paragraph(document.prompt_injection_text, style="PromptDemoPayload"))

    for section in document.sections:
        body_parts.append(_paragraph(section.name, style="SectionTitle"))
        for entry in section.entries:
            body_parts.extend(_entry_parts(builder, entry))

    document_xml = _document_xml("".join(body_parts))
    return {
        "[Content_Types].xml": _content_types_xml(),
        "_rels/.rels": _package_relationships_xml(),
        "docProps/core.xml": _core_properties_xml(),
        "docProps/app.xml": _app_properties_xml(),
        "word/document.xml": document_xml,
        "word/styles.xml": _styles_xml(),
        "word/settings.xml": _settings_xml(),
        "word/_rels/document.xml.rels": _document_relationships_xml(builder.relationships),
    }


def write_docx(document: ResolvedDocument, output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    package = render_docx(document)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in package.items():
            if isinstance(content, str):
                archive.writestr(name, content.encode("utf-8"))
            else:
                archive.writestr(name, content)
    return path


def _entry_parts(builder: DocxBuilder, entry: ResolvedEntry) -> list[str]:
    parts: list[str] = []
    if entry.url:
        parts.append(_link_paragraph(builder, entry))
        if entry.description:
            parts.append(_paragraph(entry.description, style="MutedText"))
        return parts

    if not entry.hide_heading:
        parts.append(_entry_heading(entry))
    if entry.text:
        for paragraph in _paragraphs(entry.text):
            parts.append(_paragraph(paragraph, style="BodyText"))
    if entry.tools:
        parts.append(_paragraph(f"Tools used: {entry.tools}", style="ToolsText"))
    for bullet in entry.bullets:
        parts.append(_paragraph(bullet, style="BulletText", bullet=True))
    return parts


def _entry_heading(entry: ResolvedEntry) -> str:
    left_runs = [_run(entry.title, bold=True)]
    if entry.organisation:
        left_runs.append(_run(f", {entry.organisation}", italic=True, color=MUTED))
    date_text = typographic_date_range(entry.display_dates or "")
    runs = "".join(left_runs)
    if date_text:
        runs += '<w:r><w:tab/></w:r>' + _run(date_text, color=MUTED, size=19)
    return _paragraph_from_runs(runs, style="EntryHeading")


def _link_paragraph(builder: DocxBuilder, entry: ResolvedEntry) -> str:
    relationship_id = builder.hyperlink_relationship(entry.url or "")
    runs = _run(f"{entry.title}: ", bold=True, color=ACCENT)
    runs += (
        f'<w:hyperlink r:id="{relationship_id}">'
        f'<w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>{_xml(entry.link_text or entry.url or "")}</w:t></w:r>'
        f"</w:hyperlink>"
    )
    return _paragraph_from_runs(runs, style="BodyText")


def _contact_table(contact: list[tuple[str, str]]) -> str:
    cells = []
    alignments = ["left", "center", "right"]
    for index, (label, value) in enumerate(contact[:3]):
        cells.append(_table_cell(_runs_text(f"{label}: ", bold=True) + _runs_text(value), alignments[min(index, 2)]))
    while len(cells) < 3:
        cells.append(_table_cell("", "left"))
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>'
        '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr><w:tr>"
        + "".join(cells)
        + "</w:tr></w:tbl>"
    )


def _table_cell(runs: str, alignment: str) -> str:
    return (
        '<w:tc><w:tcPr><w:tcW w:w="3120" w:type="dxa"/></w:tcPr>'
        f'<w:p><w:pPr><w:jc w:val="{alignment}"/></w:pPr>{runs}</w:p>'
        "</w:tc>"
    )


def _paragraph(text: str, style: str = "BodyText", bullet: bool = False) -> str:
    return _paragraph_from_runs(_runs_text(text), style=style, bullet=bullet)


def _paragraph_from_runs(runs: str, style: str = "BodyText", bullet: bool = False) -> str:
    bullet_props = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if bullet else ""
    tab_props = (
        '<w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs>'
        if style == "EntryHeading"
        else ""
    )
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{bullet_props}{tab_props}</w:pPr>{runs}</w:p>'


def _runs_text(text: str, bold: bool = False, italic: bool = False, color: str | None = None, size: int | None = None) -> str:
    return _run(text, bold=bold, italic=italic, color=color, size=size)


def _run(text: str, bold: bool = False, italic: bool = False, color: str | None = None, size: int | None = None) -> str:
    properties = []
    if bold:
        properties.append("<w:b/>")
    if italic:
        properties.append("<w:i/>")
    if color:
        properties.append(f'<w:color w:val="{color}"/>')
    if size:
        properties.append(f'<w:sz w:val="{size}"/>')
    properties_xml = f"<w:rPr>{''.join(properties)}</w:rPr>" if properties else ""
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    return f"<w:r>{properties_xml}<w:t{preserve}>{_xml(text)}</w:t></w:r>"


def _paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]


def _xml(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _document_xml(body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1037" w:right="1037" w:bottom="1037" w:left="1037" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''


def _styles_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:after="70"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  {_style("DocumentTitle", size=21, bold=True, color=ACCENT, after=120)}
  {_style("Name", size=32, bold=True, after=20)}
  {_style("Headline", size=20, color=MUTED, after=170)}
  {_style("SectionTitle", size=24, bold=True, color=ACCENT, before=260, after=90, bottom_border=True)}
  {_style("EntryHeading", size=20, after=45)}
  {_style("BodyText", size=20, after=90)}
  {_style("ToolsText", size=19, color=MUTED, after=70)}
  {_style("MutedText", size=19, color=MUTED, after=40)}
  {_style("BulletText", size=20, after=35)}
  {_style("PromptDemoLabel", size=18, bold=True, after=25)}
  {_style("PromptDemoPayload", size=14, color=MUTED, after=120)}
  <w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="{ACCENT}"/><w:u w:val="single"/></w:rPr></w:style>
</w:styles>'''


def _style(
    style_id: str,
    size: int,
    bold: bool = False,
    color: str | None = None,
    before: int = 0,
    after: int = 0,
    bottom_border: bool = False,
) -> str:
    border = f'<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="4" w:color="{RULE}"/></w:pBdr>' if bottom_border else ""
    bold_xml = "<w:b/>" if bold else ""
    color_xml = f'<w:color w:val="{color}"/>' if color else ""
    run_props = f'<w:rPr>{bold_xml}{color_xml}<w:sz w:val="{size}"/></w:rPr>'
    return (
        f'<w:style w:type="paragraph" w:styleId="{style_id}">'
        f'<w:name w:val="{style_id}"/>'
        f'<w:pPr><w:spacing w:before="{before}" w:after="{after}"/>{border}</w:pPr>'
        f"{run_props}</w:style>"
    )


def _document_relationships_xml(relationships: list[tuple[str, str, str]]) -> str:
    link_relationships = "".join(
        f'<Relationship Id="{relationship_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{_xml(target)}" TargetMode="{mode}"/>'
        for relationship_id, target, mode in relationships
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
  {link_relationships}
</Relationships>'''


def _content_types_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''


def _package_relationships_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def _core_properties_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Curriculum Vitae</dc:title>
  <dc:creator>CV CI/CD</dc:creator>
</cp:coreProperties>'''


def _app_properties_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>CV CI/CD</Application>
</Properties>'''


def _settings_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:defaultTabStop w:val="720"/>
</w:settings>'''
