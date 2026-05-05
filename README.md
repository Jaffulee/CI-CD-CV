## Visit my website: [https://jaffulee.github.io/Jaffulee/](https://jaffulee.github.io/Jaffulee/)

# CV CI/CD

This repository generates CV documents from structured YAML. It separates reusable content, document assembly, and rendering so several CV variants can be produced from the same source data without manually copying text between documents.

Generated files are outputs only. Edit YAML, templates, or renderer code, then regenerate the documents.

<img width="1446" height="929" alt="image" src="https://github.com/user-attachments/assets/4b6055ec-06c7-40f0-b609-7ca839c12548" />

## Quick Start

From a fresh clone:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.main --no-pdf
```

This validates the YAML and generates all non-PDF outputs:

- `output/markdown/`
- `output/latex/`
- `output/html/`
- `output/docx/`

Use `--no-pdf` when you do not need PDF files or do not have a LaTeX toolchain installed.

## What To Edit

Most CV updates happen in `data/content/`.

- `details.yml`: name, contact details, address, and headline variants.
- `experience.yml`: work experience, sales roles, software engineering roles, management responsibilities, and related role entries.
- `education.yml`: education entries.
- `certifications.yml`: certifications and awards.
- `research.yml`: papers, preprints, and research entries.
- `projects.yml`: portfolio/project entries.
- `talks.yml`: talks, workshops, and speaking entries.
- `skills.yml`: individual skills and skill groups.
- `links.yml`: links rendered in CVs.
- `hobbies.yml`: hobbies or personal interests.

Document composition happens in `data/documents/`.

Edit these files when a CV variant needs a different structure, order, entry selection, or rendering mode. A document file chooses which content entries to include and whether each one is rendered as prose, bullets, labels, or links.

The example dataset is anonymised around `Mr Your Name`, a sales professional who transitioned into software engineering. The configured CV outputs are:

- `cv_full`: complete CV.
- `cv_sales`: sales-focused CV.
- `cv_software_engineering`: software engineering-focused CV.
- `cv_manager`: management-focused CV.

Each has a matching `_b` document variant that demonstrates the prompt-injection awareness payload used by this repository.

Do not manually edit files under `output/`; they are regenerated.

## Repository Structure

```text
data/
  content/       Reusable source content and metadata
  documents/     CV assembly definitions
  unstructured_docs/
src/
  parser/        YAML loading and validation
  resolver/      Resolves document references into render-ready content
  renderers/     Markdown, LaTeX, HTML, and DOCX renderers
  utils/
styles/
  markdown/      Markdown templates
  latex/         LaTeX preamble, macros, and templates
  html/          HTML templates and CSS
output/          Generated files
tests/
```

The build path is deterministic. It does not call an LLM or infer missing content.

## Content Model

Content entries are reusable across CV variants. Common fields include:

- `id`: stable identifier referenced by document YAML.
- `type`: loose category such as `role`, `client_project`, `university_talk`, or `certification`.
- `title`: rendered entry title.
- `organisation`: rendered organisation.
- `start`, `end`, `display_dates`: date metadata and rendered date text.
- `tools`: rendered only when a document entry enables `show_tools`.
- `domains`, `themes`, `profiles`: metadata for grouping, filtering, and future automation.
- `variants`: prose versions such as `one_line`, `short`, or `full`.
- `bullets`: named bullet sets such as `short`, `full`, or `impact`.
- `priority`: controls bullet ordering and document-level limits.

Example content entry:

```yaml
talks:
  - id: example-university-talk-2026
    type: university_talk
    title: Customer Conversations as an Engineering Skill
    organisation: Example Tech Meetup
    start: 2026-04
    end: 2026-04
    display_dates: "April 2026"

    tools: []

    domains:
      - software-engineering
      - career-transition

    themes:
      - meetup-talk
      - technical-communication

    profiles:
      - software-engineering

    variants:
      short: |
        Delivered a lightning talk on how sales discovery skills can improve software requirements.

      full: |
        Delivered a lightning talk on how sales discovery skills can improve software requirements, product decisions, and customer-facing engineering work.

    bullets:
      short:
        - text: Delivered a talk on using sales discovery skills to improve software requirements
          priority: 10
```

## Document Model

Document YAML controls what appears in each CV.

Example document section:

```yaml
sections:
  - name: Talks
    source: talks
    entries:
      - id: example-university-talk-2026
        mode: variant
        variant: short
```

Supported entry modes:

- `variant`: render prose from a named text variant.
- `bullets`: render a named bullet set, optionally limited by `max_bullets`.
- `label`: render a simple label entry, mainly for skills.
- `link`: render a clickable link with optional display text and description.

Use `source: mixed` for sections that combine entries from different content files:

```yaml
  - name: Education and Research
    source: mixed
    entries:
      - source: education
        id: software-engineering-diploma-2024
        mode: variant
        variant: short

      - source: research
        id: graphs-equal-girth-circumference-2022
        mode: variant
        variant: full
```

## Usage

You can generate CV files locally by running the main Python entry point. Local generation writes files into the `output/` folder on your machine.

Generate every configured document in every available format:

```powershell
python -m src.main
```

Generate all non-PDF outputs:

```powershell
python -m src.main --no-pdf
```

Generate one document by document ID or output name:

```powershell
python -m src.main --document cv_software_engineering
python -m src.main --document cv-software-engineering
```

Generate one format:

```powershell
python -m src.main --format markdown
python -m src.main --format latex
python -m src.main --format html
python -m src.main --format docx
python -m src.main --format pdf
```

Generate one document in one format:

```powershell
python -m src.main --document cv_software_engineering --format docx
```

Multiple `--document` and `--format` flags can be passed:

```powershell
python -m src.main --document cv_software_engineering --document cv_full --format markdown --format docx
```

After running any of these commands, open the generated files from:

- `output/markdown/`
- `output/latex/`
- `output/html/`
- `output/docx/`

The `output/` folder is ignored by Git because these files are reproducible build outputs. Local files in `output/` are for inspection, sharing, or manual download from your own machine; CI-generated files are available as GitHub Actions artifacts.

## Output Formats

Markdown output is plain and review-friendly.

LaTeX output is designed for clean PDF generation and copy-pasteable text. The templates avoid unusual glyphs and disable common ligatures so extracted text remains readable by humans and automated tools.

PDF output is compiled from generated LaTeX. PDF files are written beside `.tex` files in `output/latex/`.

HTML output is static, uses local CSS copied into `output/html/`, and preserves paragraph breaks from multiline YAML text.

DOCX output is generated directly from the resolved CV model using native WordprocessingML. It does not convert from LaTeX, Markdown, or HTML, and it does not require Word, LibreOffice, Pandoc, or `python-docx`. The DOCX renderer approximates the LaTeX design with matching margins, heading colour, section rules, right-aligned dates, compact contact details, and similar text hierarchy.

If a `.docx` file is open in Word, generation may fail with `PermissionError` because Word locks the file. Close the document and rerun the command.

## Formatting And Templates

Most formatting changes can be made in the `styles/` folder.

- `styles/markdown/cv.md.j2` controls Markdown structure.
- `styles/latex/cv.tex.j2` controls LaTeX document structure.
- `styles/latex/macros.tex` defines reusable LaTeX formatting commands such as headings, contact rows, links, tools, and bullets.
- `styles/latex/preamble_default.tex` controls LaTeX packages, page size, margins, colours, section spacing, and global typography.
- `styles/html/cv.html.j2` controls HTML structure.
- `styles/html/cv.css` and `styles/html/print.css` control screen and print styling for HTML.

The Markdown, LaTeX, and HTML renderers use Jinja templates. The Python resolver prepares a render-ready document, then each Jinja template decides how that document is written for its format. For example, changing how entry headings are laid out in LaTeX usually means editing `styles/latex/cv.tex.j2` or `styles/latex/macros.tex`, not editing the source YAML.

DOCX is the exception: it is generated directly in Python by `src/renderers/docx_renderer.py` using WordprocessingML. If LaTeX styling changes significantly, the DOCX renderer may need a matching update to keep the Word output visually aligned.

## LaTeX And PDF Requirements

Generating `.tex` files does not require LaTeX to be installed.

Generating PDFs requires a TeX command-line tool on `PATH`. The generator tries:

1. `latexmk`
2. `pdflatex`

These are usually provided by:

- MiKTeX on Windows.
- TeX Live on Windows, macOS, or Linux.
- MacTeX on macOS.

Recommended workflow:

```powershell
python -m src.main --no-pdf
```

Then, when the YAML and non-PDF outputs are valid:

```powershell
python -m src.main --format pdf
```

If PDF compilation fails:

- Check that `latexmk` or `pdflatex` is available on `PATH`.
- On MiKTeX, allow missing packages to be installed.
- Inspect the `.log` file in `output/latex/` for the actual LaTeX error.
- Use `--no-pdf` while editing content if you do not need final PDFs.

## Validation

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

Compile-check Python files:

```powershell
python -m compileall src tests
```

Recommended pre-commit check:

```powershell
python -m src.main --no-pdf
python -m unittest discover -s tests
python -m compileall src tests
```

Validation covers:

- YAML parsing.
- Duplicate content IDs.
- Missing document references.
- Missing variants.
- Missing bullet sets.
- Missing contact and headline variants.
- Missing renderer templates, stylesheets, and scripts.
- Missing skill IDs in skill groups.
- Rendering sanity checks for Markdown, LaTeX, HTML, and DOCX.

## Automating Generation

A minimal CI job should install dependencies, run tests, and generate outputs:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m compileall src tests
python -m src.main --no-pdf
```

PDF generation can be added when the CI environment has LaTeX installed:

```powershell
python -m src.main --format pdf
```

This repository includes a GitHub Actions workflow at `.github/workflows/generate-cv.yml`. It has two paths:

1. Fast push-to-main generation.
2. Manual generation with PDFs.

On every push to `main`, the workflow:

1. Checks out the repository.
2. Installs Python dependencies.
3. Runs the test suite.
4. Compile-checks Python files.
5. Generates all non-PDF outputs with `python -m src.main --no-pdf`.
6. Uploads the generated deliverables as a workflow artifact named `generated-cvs`.

This keeps normal CV updates fast because it does not install LaTeX.

To generate PDFs in GitHub Actions:

1. Open the repository on GitHub.
2. Go to the **Actions** tab.
3. Select **Generate CV Artifacts**.
4. Click **Run workflow**.
5. Set **Install LaTeX and compile PDF outputs** to `true`.
6. Run the workflow.

Manual PDF runs install a LaTeX toolchain and then run:

```powershell
python -m src.main
```

The uploaded artifact includes Markdown, HTML, DOCX, and LaTeX `.tex` files on every run. PDF files are included when the manual PDF option is enabled. HTML assets such as `cv.css` and `print.css` are included because the generated HTML files depend on them.

Artifacts are retained for 14 days. GitHub Actions does not automatically delete the previous artifact just because a newer run exists, so explicit retention is the simplest reliable cleanup policy. For this repository, short retention is usually better than long retention because the generated CV files are reproducible from the current source.

Generated files under `output/` are ignored by Git because they are reproducible build artifacts. Download them from the workflow run artifacts instead of committing them to the repository.

The important rule is that published files should come from the pipeline rather than manual edits to generated output.
