# Dataset and Experiment Guide

This folder contains the datasets used by the **LLM Agent-Based Semantic Table Annotation Pipeline**.

The data is organized for two main purposes:

1. Pipeline testing and development.
2. Qualitative experiment runs used in the project report and presentation.

The project does not reproduce the complete official benchmark evaluation of the original paper. Instead, it uses selected benchmark and custom tables for inspectable experiments, where pipeline outputs are compared manually with available ground truth or expected semantic meaning.

For the complete project documentation, see:

- [Main Project README](../README.md)
- [Full Project Report](../docs/semantic-table-annotation-report.pdf)
- [Project Presentation](../docs/semantic-table-annotation-presentation.pptx)

---

## Folder Structure

```text
data/
├── biodivtab/
│   ├── gt/
│   └── tables/
│
├── experiments/
│   ├── exp1_bdt/
│   ├── exp2_tt/
│   ├── exp3_custom/
│   └── exp4_custom/
│
├── kaggle/
├── toughtables/
└── README.md
```

### Folder purposes

| Folder | Purpose |
|---|---|
| `biodivtab/` | Selected BiodivTab tables and reduced ground-truth files |
| `toughtables/` | Selected ToughTables tables and reduced ground-truth files |
| `kaggle/` | Custom and Kaggle-derived datasets used for real-world examples |
| `experiments/` | Exact files grouped by the four main project experiments |

Some files inside `experiments/` are selected copies of files from the dataset folders. This is intentional because it keeps each experiment self-contained and makes the execution commands easier to reproduce.

---

## Experiment 1 — BiodivTab

### Folder

```text
data/experiments/exp1_bdt/
```

This experiment contains selected BiodivTab tables and reduced ground-truth files.

### Main purpose

- Inspect biological and domain-specific tables.
- Test strong-header and weak-cell behavior.
- Examine cases where CEA should be skipped.
- Evaluate CTA using column headers and broader table context.
- Inspect the effect of optional value enrichment.

### Typical workflow

```text
Strong Headers + Weak Cells
→ skip topic detection
→ skip CEA for numeric, coded, or non-entity values
→ perform CTA using header and table context
```

### Main experiment file

```text
data/experiments/exp1_bdt/bdt_4.csv
```

### Final experiment configuration

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `openai/gpt-oss-20b` |
| Knowledge Graph | Wikidata |
| Scenario | Strong Headers + Weak Cells |
| Value enrichment | Enabled |
| Main observation | The table was weak-cell-heavy, CEA was skipped, and CTA produced meaningful column labels |

Examples of inspected CTA outputs include:

```text
Year → Date
Samplenr → Sample ID
Height_P → Plant Height
Biomass_Above → AboveGroundBiomass
```

---

## Experiment 2 — ToughTables

### Folder

```text
data/experiments/exp2_tt/
```

This experiment contains selected ToughTables tables and reduced ground-truth files.

### Main purpose

- Inspect tables with weak or generic headers.
- Test topic detection.
- Test DBpedia-based CEA candidate generation.
- Test context-supported CEA selection.
- Test CTA using selected entities and Knowledge Graph types.
- Inspect ambiguous entity cases.

### Typical workflow

```text
Weak Headers + Strong Cells
→ infer column topics
→ generate CEA candidates
→ select final CEA annotations
→ collect and rank CTA candidates
→ select final CTA labels
```

### Main experiment file

```text
data/experiments/exp2_tt/tt_2.csv
```

### Final experiment configuration

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `openai/gpt-oss-20b` |
| Knowledge Graph | DBpedia |
| Scenario | Weak Headers + Strong Cells |
| Value enrichment | Enabled |
| Main observation | Generic headers were recovered through topic detection and then used during CEA and CTA |

Examples of inspected outputs include:

```text
col0 → Person Name
col3 → U.S. State
Ben Chapman → Ben Chapman (baseball)
```

Some CTA outputs were semantically related but broader than the available ground truth.

---

## Experiment 3 — Custom Restaurant Dataset

### Folder

```text
data/experiments/exp3_custom/
```

This experiment contains a Kaggle-style real-world dataset with meaningful headers.

### Main purpose

- Test a readable real-world table.
- Test strong-header and strong-cell behavior.
- Test restaurant, location, and country annotation.
- Demonstrate the pipeline outside benchmark-style datasets.
- Inspect cases where Knowledge Graph candidates may be noisy.

### Typical workflow

```text
Strong Headers + Strong Cells
→ skip topic detection
→ run CEA for meaningful entity-like cells
→ perform CTA for all selected columns
```

### Main experiment file

```text
data/experiments/exp3_custom/worlds_best_restaurants.csv
```

### Final experiment configuration

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `openai/gpt-oss-20b` |
| Knowledge Graph | DBpedia |
| Scenario | Strong Headers + Strong Cells |
| Value enrichment | Enabled |
| Main observation | Restaurant, location, and country columns produced mostly close semantic annotations |

Examples of inspected outputs include:

```text
Spain → Spain
London → London
country → Country
location → City
lat → Latitude
lng → Longitude
```

---

## Experiment 4 — Custom E-Commerce Dataset

### Folder

```text
data/experiments/exp4_custom/
```

This experiment contains a custom or Kaggle-style table modified to use weak and generic headers.

### Main purpose

- Test weak-header recovery on recognizable entities.
- Test topic detection on columns such as `col_0`, `col_1`, and `col_2`.
- Test CEA on companies, founders, and countries.
- Compare inferred topics with expected human interpretations.

### Typical workflow

```text
Weak Headers + Strong Cells
→ infer column topics from representative values
→ run CEA on entity-like cells
→ perform CTA using selected entities and table context
```

### Main experiment file

```text
data/experiments/exp4_custom/top_ecommerce_brands.csv
```

### Final experiment configuration

| Item | Value |
|---|---|
| Provider | Google |
| Model | `gemini-3.1-flash-lite` |
| Knowledge Graph | DBpedia |
| Scenario | Weak Headers + Strong Cells |
| Value enrichment | Disabled |
| Main observation | Generic headers were recovered as company, year, founder, and country-related columns |

Examples of inspected outputs include:

```text
col_0 → E-commerce Companies
col_2 → Business Founders
Amazon → Amazon (company)
Alibaba → Alibaba Group
USA → United States
```

---

## Ground-Truth Files

The benchmark folders contain reduced ground-truth files for qualitative inspection.

Typical formats include:

```text
CEA:
table_id,row_index,column_index,entity
```

```text
CTA:
table_id,column_index,type
```

For example, the BiodivTab ground-truth folder contains files such as:

```text
data/biodivtab/gt/bdt_cea_gt.csv
data/biodivtab/gt/bdt_cta_gt.csv
```

The ToughTables experiment folders also include reduced CEA and CTA ground-truth files.

These files are used for manual comparison only. The current project does not calculate complete benchmark precision, recall, or F1 scores.

---

## Main Experiment Summary

| Experiment | Main file | Scenario | Provider | KG | Value enrichment |
|---|---|---|---|---|---|
| BiodivTab | `experiments/exp1_bdt/bdt_4.csv` | Strong Headers + Weak Cells | Groq | Wikidata | Enabled |
| ToughTables | `experiments/exp2_tt/tt_2.csv` | Weak Headers + Strong Cells | Groq | DBpedia | Enabled |
| Custom Restaurants | `experiments/exp3_custom/worlds_best_restaurants.csv` | Strong Headers + Strong Cells | Groq | DBpedia | Enabled |
| Custom E-Commerce | `experiments/exp4_custom/top_ecommerce_brands.csv` | Weak Headers + Strong Cells | Google | DBpedia | Disabled |

All paths in this table are relative to the `data/` folder.

---

## Important Pipeline Behavior

The complete input CSV is loaded and preprocessed.

However, the number of cells processed during CEA can be limited through CLI parameters.

| Setting | Meaning |
|---|---|
| `--cea-max-rows` | Maximum number of initial rows considered during CEA candidate generation |
| `--cea-max-cells` | Maximum number of cells selected for final CEA |
| `--sample-values` | Number of representative values selected per column |
| `LOG_SAMPLE_ROWS` | Number of rows displayed in report previews |

Therefore:

```text
--cea-max-rows does not limit CSV loading or preprocessing.
```

It only limits the rows considered by the CEA stage.

The router also prioritizes weak-cell behavior. If a column contains mostly numeric, identifier-like, date-like, empty, repetitive, or coded values, the pipeline avoids forcing entity linking and performs CTA using the available header and table context.

---

## Qualitative Evaluation Method

The experiments use manual and visual inspection rather than complete benchmark scoring.

For selected cells and columns, the project compares:

```text
input evidence
expected semantic meaning or ground truth
pipeline output
qualitative judgment
```

The judgment labels are:

| Label | Meaning |
|---|---|
| Close | The result has the same or a very similar semantic meaning |
| Partial | The result is related but too broad, too narrow, or not exact |
| Wrong | The result has an incorrect semantic meaning |

This evaluation approach was selected because the project focuses on:

- pipeline implementation,
- workflow explainability,
- routing behavior,
- intermediate decisions,
- candidate inspection,
- semantic closeness.

The results should not be interpreted as official benchmark performance.

---

## Generated Reports

Each pipeline execution creates a TXT report under:

```text
logs/runs/YYYY-MM-DD/
```

The reports may contain:

- execution configuration,
- input table previews,
- preprocessed values,
- representative values,
- NER hints,
- value-enrichment outputs,
- routing decisions,
- inferred column topics,
- CEA candidates,
- selected CEA entities,
- CTA candidates,
- final column types,
- skipped stages,
- runtime information.

The generated reports are the main inspection artifacts used in the report and presentation.

---

## Data Sources

The project uses selected or reduced files from benchmark and public dataset sources.

### Benchmark-style datasets

#### ToughTables

Used for:

- weak-header examples,
- ambiguous entities,
- difficult semantic types,
- DBpedia-style CEA and CTA inspection.

#### BiodivTab

Used for:

- biological and domain-specific tables,
- weak-cell-heavy scenarios,
- CTA fallback behavior,
- value-enrichment inspection.

### Kaggle and custom datasets

#### Worldwide Travel Cities Ratings and Climate

Used as a real-world dataset containing travel cities, ratings, climate information, countries, and location-related attributes.

#### World’s Best Restaurants

Used as a dataset containing restaurant names, cities, countries, years, and geographic coordinates.

#### Top 100 Global Brands by Brandirectory 2022

Used as a business and brand dataset containing recognizable company and brand entities.

#### Global E-Commerce Leaders Founding Snapshot

Used as a weak-header experiment containing e-commerce companies, founding years, founders, and countries.

The original public datasets may contain more rows and columns than the versions included here. The project uses selected or reduced copies for demonstration, inspection, and reproducibility.

---

## Running an Experiment

Run commands from the repository root, not from inside the `data/` folder.

Example BiodivTab execution:

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

Additional installation and CLI instructions are available in the [main project README](../README.md).

---

## Notes for Future Runs

Before running an experiment:

1. Activate the Python environment.
2. Install all dependencies from `requirements.txt`.
3. Install the required spaCy model.
4. Check the `.env` API keys when using hosted LLM providers.
5. Make sure the Ollama server is running when using local models.
6. Run commands from the repository root.
7. Inspect the generated files under `logs/runs/`.
8. Compare routing, CEA, and CTA results with the available ground truth or expected semantic meaning.