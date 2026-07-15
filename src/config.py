"""
src/config.py
===================
Central configuration for the semantic table annotation pipeline.
"""

# ============================================================
# Dataset defaults
# ============================================================

DEFAULT_DATASET_NAME = "custom" # can be "kaggle", "toughtables", "biodivtab" or "custom"
DEFAULT_DATASET_SPLIT = "experiment" # can be "debug", "test" etc.

DEFAULT_DATASET_PATH = "data/kaggle/brand_ranking_data_2022.csv"
DEFAULT_INPUT_FOLDER = "data/kaggle/*.csv"

# ============================================================
# Pipeline defaults
# ============================================================

PIPELINE_STEPS = [
    "load",
    "preprocess",
    "representative",
    "ner",
    "value_enrichment",
    "routing",
    "topic_detection",
    "cea_candidates",
    "cea",
    "cta",
]

PIPELINE_RUN_UNTIL = "cta"


# ============================================================
# Sampling and evidence settings
# ============================================================

SAMPLE_VALUES_PER_COLUMN = 5


# ============================================================
# LLM settings
# ============================================================

DEFAULT_PROMPT_FILE = "prompts/prompts.yaml"

DEFAULT_LLM_PROVIDER = "groq"

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_GOOGLE_MODEL = "gemini-3.1-flash-lite"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

DEFAULT_LLM_MODEL = DEFAULT_GROQ_MODEL

OLLAMA_BASE_URL = "http://localhost:11434"

LLM_TEMPERATURE = 0
LLM_REQUEST_DELAY_SECONDS = 1.0
LLM_API_TIMEOUT_SECONDS = 180


# ============================================================
# Routing settings
# ============================================================

ROUTER_CELL_STRENGTH_THRESHOLD = 0.85
ROUTER_TABLE_WEAK_CELL_RATIO = 0.70

ROUTER_WEAK_HEADER_MAX_LENGTH = 1

ROUTER_AUTO_GENERATED_HEADER_PATTERNS = [
    r"^col[\s_:\-]*\d+$",
    r"^column[\s_:\-]*\d+$",
    r"^unnamed[\s_:\-]*\d+$",
]


# ============================================================
# Knowledge graph settings
# ============================================================

DEFAULT_KG_SOURCE = "dbpedia"

USER_AGENT = "DS-Project-STA"

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

DBPEDIA_LOOKUP_URL = "https://lookup.dbpedia.org/api/search"
DBPEDIA_SPARQL_URL = "https://dbpedia.org/sparql"

KG_CANDIDATE_LIMIT = 3
KG_REQUEST_DELAY_SECONDS = 0.6
KG_MAX_RETRIES = 3


# ============================================================
# NER and value enrichment
# ============================================================

USE_NER = True
SPACY_MODEL = "en_core_web_sm"
NER_MAX_CELL_ROWS = 10

USE_VALUE_ENRICHMENT = True


# ============================================================
# CEA settings
# ============================================================

CEA_CANDIDATE_LIMIT = KG_CANDIDATE_LIMIT

CEA_MAX_ROWS = 5
CEA_MAX_CELLS = 8

USE_CEA_REUSE = True
LEVENSHTEIN_REUSE_RATIO = 0.2


# ============================================================
# CTA settings
# ============================================================

CTA_MAX_ENTITIES = 10
CTA_TYPES_PER_ENTITY = 5

CTA_USE_KG_CANDIDATES = True
CTA_ALLOW_LLM_FALLBACK = True
CTA_FINAL_SELECTION_MODE = "hybrid"


# ============================================================
# Reporting and logs
# ============================================================

RUNS_LOG_DIR = "logs/runs"

LOG_SAMPLE_ROWS = 5
LOG_MAX_CEA_CELLS = 5

LOG_TABLE_MAX_WIDTH = None
LOG_SUMMARY_MAX_WIDTH = 50

LOG_PROMPTS_AND_ANSWERS = False
REPORT_MODE = "compact"


# ============================================================
# Step logging switches
# ============================================================

LOG_STEP_LOAD = True
LOG_STEP_PREPROCESS = True
LOG_STEP_REPRESENTATIVE = True
LOG_STEP_NER = True
LOG_STEP_VALUE_ENRICHMENT = True
LOG_STEP_ROUTING = True
LOG_STEP_TOPIC_DETECTION = True
LOG_STEP_CEA_CANDIDATES = True
LOG_STEP_CEA = True
LOG_STEP_CTA = True