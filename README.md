# LLM Agent-Based Semantic Table Annotation Pipeline

A modular Python implementation inspired by the paper **“An LLM Agent-Based Complex Semantic Table Annotation Approach.”**

The project focuses on **Semantic Table Annotation (STA)**, mainly:

- **Cell Entity Annotation (CEA):** linking meaningful table cells to Knowledge Graph entities.
- **Column Type Annotation (CTA):** assigning semantic types or ontology classes to table columns.

The implementation combines preprocessing, workflow routing, Knowledge Graph lookup, and Large Language Model support to annotate complex tabular data.

---

## Project Goal

Real-world tables may contain:

- weak or generic column headers,
- ambiguous cell values,
- abbreviations and spelling errors,
- numeric or coded columns,
- missing semantic information,
- values that require row and column context.

The goal of this project is to transform these tables into semantically richer outputs by combining:

- text cleaning and normalization,
- representative value extraction,
- NER-based semantic hints,
- optional LLM value enrichment,
- explicit workflow routing,
- Knowledge Graph candidate generation,
- LLM-supported CEA and CTA decisions,
- compact TXT reports for manual inspection.

The project does not aim to fully reproduce the official benchmark evaluation of the original paper. Instead, it focuses on implementing the main pipeline behavior and qualitatively inspecting selected benchmark-style and custom examples.

---

## Main Difference from the Paper

The original paper proposes a ReAct-based STA agent in which the LLM dynamically selects tools during execution.

This implementation preserves the main ideas but replaces the fully dynamic ReAct loop with an explicit and deterministic routing module.

The router:

- analyzes column-header strength,
- analyzes cell-value strength,
- selects the appropriate annotation workflow,
- determines which stages should be executed or skipped.

This approach makes the system easier to inspect, debug, explain, and reproduce.

---

## Pipeline Overview

The complete pipeline follows this general structure:

```text
CSV input
  -> table loading
  -> preprocessing
  -> representative value extraction
  -> NER support
  -> optional value enrichment
  -> workflow routing
  -> topic detection
  -> CEA candidate generation
  -> CEA selection
  -> CTA candidate ranking
  -> CTA selection
  -> TXT report
```

Not every stage is executed for every table. The routing module determines the appropriate path.

---

## Workflow Scenarios

The router classifies columns and tables into three main workflow scenarios:

| Scenario | Meaning | Pipeline behavior |
|---|---|---|
| WH-SC | Weak Header + Strong Cells | Run topic detection, CEA, and CTA |
| SH-SC | Strong Header + Strong Cells | Skip topic detection; run CEA and CTA |
| SH-WC | Strong Header + Weak Cells | Skip CEA; perform CTA using header and table context |

Weak-cell cases are prioritized. When a column contains mostly numeric, date-like, identifier-like, empty, repetitive, or coded values, the pipeline avoids forcing Knowledge Graph entity links.

### Example: Weak Header + Strong Cells

```text
col0
Apple
Microsoft
Amazon

-> inferred topic: Company
-> run CEA
-> run CTA
```

### Example: Strong Header + Weak Cells

```text
Year
2015
2016
2017

-> skip CEA
-> infer CTA from header and table context
```

### Example: Strong Header + Strong Cells

```text
Country
Spain
France
Germany

-> run CEA
-> run CTA
```

---

## Repository Structure

```text
llm-semantic-table-annotation/
├── data/
│   ├── biodivtab/
│   ├── experiments/
│   ├── kaggle/
│   ├── toughtables/
│   └── README.md
│
├── docs/
│   ├── semantic-table-annotation-report.pdf
│   └── semantic-table-annotation-presentation.pptx
│
├── logs/
│   ├── runs/
│   ├── available_models.txt
│   └── llm_test_results.txt
│
├── prompts/
│   └── prompts.yaml
│
├── src/
│   ├── core/
│   ├── io/
│   ├── kg/
│   ├── llm/
│   ├── pipeline/
│   ├── preprocessing/
│   ├── routing/
│   ├── tools/
│   ├── utils/
│   ├── __init__.py
│   └── config.py
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

Experiment and dataset-specific details are documented separately in:

```text
data/README.md
```

---

## Documentation

- [Full Project Report](docs/semantic-table-annotation-report.pdf)
- [Project Presentation](docs/semantic-table-annotation-presentation.pptx)

The report contains the complete technical description of the project, including its background, architecture, implementation, experiments, results, limitations, and conclusions.

The presentation provides a concise overview of the architecture, workflow scenarios, implementation, and selected experimental results.

---

## Installation

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd llm-semantic-table-annotation
```

Replace `<repository-url>` with the actual GitHub repository URL.

Alternatively, download the repository as a ZIP file, extract it, and open a terminal inside the extracted `llm-semantic-table-annotation` folder.

### 2. Create a Python Environment

Using Conda:

```powershell
conda create -n sta-env python=3.12
conda activate sta-env
```

Or using Python `venv`:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install the Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install the English spaCy Model

```powershell
python -m spacy download en_core_web_sm
```

---

## Environment Variables

Create a `.env` file in the project root when using API-based LLM providers.

Example:

```text
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here
OPENAI_API_KEY=your_openai_key_here
```

OpenAI is optional. The project can run with Groq, Google Gemini, OpenAI, or a local Ollama model, depending on the selected configuration.

Do not commit the `.env` file or any API credentials.

---

## Supported LLM Providers

| Provider | Intended use |
|---|---|
| Groq | Fast hosted inference for experiments |
| Google Gemini | API-based model testing and comparison |
| Ollama | Local inference without external API calls |
| OpenAI | Optional hosted inference |

Default provider and model settings are configured in:

```text
src/config.py
```

---

## Knowledge Graph Support

The project includes configurable Knowledge Graph clients for:

- DBpedia
- Wikidata

Knowledge Graph lookup is used to retrieve structured entity and type candidates.

The LLM is then used to select the most suitable candidate based on table context.

The relevant implementation is located in:

```text
src/kg/
```

---

## Optional Model Check

The project includes a utility for checking available LLM models:

```powershell
python -m src.llm.llm_checks
```

The generated files are stored in:

```text
logs/available_models.txt
logs/llm_test_results.txt
```

For Ollama, make sure the local server is running:

```powershell
ollama serve
```

---

## Running the Pipeline

The pipeline can process either:

- one CSV file,
- or a folder containing multiple CSV files.

### Single-File Execution

```powershell
python -m src.pipeline.cli `
  --file path/to/table.csv `
  --dataset-name custom `
  --split experiment `
  --provider groq `
  --llm "model-name" `
  --kg dbpedia `
  --run-until cta
```

### Folder Execution

```powershell
python -m src.pipeline.cli `
  --folder path/to/folder `
  --dataset-name custom `
  --split experiment `
  --provider groq `
  --llm "model-name" `
  --kg dbpedia `
  --run-until cta
```

---

## Example Experiment

The following command runs the pipeline on a selected BiodivTab experiment:

```powershell
python -m src.pipeline.cli `
  --file data/experiments/exp1_bdt/bdt_4.csv `
  --dataset-name biodivtab `
  --split experiment `
  --provider groq `
  --llm "openai/gpt-oss-20b" `
  --kg wikidata `
  --run-until cta `
  --sample-values 5 `
  --kg-candidate-limit 3 `
  --cea-max-rows 5 `
  --cea-max-cells 10 `
  --cta-max-entities 10 `
  --cta-types-per-entity 5 `
  --router-table-weak-ratio 0.70 `
  --reuse-threshold 0.20 `
  --ner true `
  --value-enrichment true `
  --cea-reuse true
```

PowerShell uses the backtick character at the end of each line to continue the command.

Detailed experiment and dataset notes are available in:

```text
data/README.md
```

---

## CLI Parameters

| Parameter | Description |
|---|---|
| `--file` | Path to one input CSV file |
| `--folder` | Path to a folder containing CSV files |
| `--dataset-name` | Dataset name shown in the generated report |
| `--split` | Experiment or dataset-split label |
| `--provider` | LLM provider such as `groq`, `google`, `ollama`, or `openai` |
| `--llm` | Exact model name |
| `--kg` | Knowledge Graph source, usually `dbpedia` or `wikidata` |
| `--run-until` | Final pipeline stage to execute |
| `--sample-values` | Number of representative values selected per column |
| `--kg-candidate-limit` | Maximum number of KG candidates retrieved per cell |
| `--cea-max-rows` | Maximum number of rows considered during CEA |
| `--cea-max-cells` | Maximum number of cells selected for CEA |
| `--cta-max-entities` | Maximum number of annotated entities used for CTA |
| `--cta-types-per-entity` | Maximum number of type candidates retrieved per entity |
| `--router-table-weak-ratio` | Weak-column ratio used for table-level routing |
| `--reuse-threshold` | Levenshtein similarity threshold for CEA reuse |
| `--ner` | Enable or disable NER support |
| `--value-enrichment` | Enable or disable LLM-based value enrichment |
| `--cea-reuse` | Enable or disable reuse of similar CEA annotations |

---

## Output Reports

Each pipeline run generates a compact TXT report under:

```text
logs/runs/YYYY-MM-DD/
```

The report may include:

- execution configuration,
- loaded table samples,
- preprocessed values,
- representative values,
- NER hints,
- value-enrichment results,
- routing decisions,
- inferred column topics,
- CEA candidates,
- selected cell entities,
- CTA candidates,
- final column types,
- skipped pipeline stages,
- runtime information.

These reports are the main inspection artifacts used during the experiments.

---

## Experiments

The project uses selected examples from benchmark and custom datasets.

| Experiment group | Purpose |
|---|---|
| ToughTables | Testing weak headers, ambiguous entities, and difficult semantic types |
| BiodivTab | Testing biological tables and weak-cell-heavy scenarios |
| Kaggle restaurant data | Testing strong headers and recognizable real-world entities |
| Kaggle e-commerce data | Testing weak headers with meaningful company, founder, and country values |

The results are inspected by comparing selected cells and columns with available ground truth or expected semantic meanings.

The qualitative judgment labels are:

| Label | Meaning |
|---|---|
| Close | Semantically correct or very close |
| Partial | Related, but too broad, too narrow, or not exact |
| Wrong | Semantically incorrect |

---

## Evaluation Approach

The project uses qualitative inspection rather than a complete precision, recall, and F1-score benchmark evaluation.

This approach was selected because:

- the main goal is pipeline implementation and explainability,
- generated reports expose intermediate decisions,
- selected examples can be inspected manually,
- semantic similarity may not always correspond to an exact URI match,
- DBpedia and Wikidata may use different entity or ontology conventions.

The experimental results should therefore be interpreted as evidence of pipeline behavior rather than official benchmark performance.

---

## Main Contributions

- Modular Semantic Table Annotation pipeline.
- Support for CEA and CTA.
- Explicit workflow routing instead of a fully autonomous ReAct loop.
- Internal table, column, and cell data models.
- Preprocessing and representative value extraction.
- NER-based semantic hints.
- Optional LLM value enrichment.
- DBpedia and Wikidata candidate generation.
- LLM-supported topic detection, CEA, and CTA.
- Levenshtein-based CEA annotation reuse.
- Multiple API and local LLM providers.
- Command-line execution for files and folders.
- Compact and inspectable TXT reports.

---

## Limitations

- The project does not reproduce the complete official benchmark evaluation.
- Exact Knowledge Graph URI matching is not always performed.
- Results depend on the quality of Knowledge Graph candidates.
- LLM outputs may vary between providers and models.
- Domain-specific tables may require additional ontology support.
- The qualitative experiments use selected examples and are not statistically complete.

---

## Reference

This project is inspired by:

**Yilin Geng et al. — “An LLM Agent-Based Complex Semantic Table Annotation Approach.”**

---

## License

This project is distributed under the license included in the [LICENSE](LICENSE) file.