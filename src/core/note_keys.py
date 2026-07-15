"""
src/core/note_keys.py
=====================
Shared note-key constants used across the STA pipeline.

The project still uses flexible .notes dictionaries, but constants reduce
silent bugs caused by typos or inconsistent key names.
"""

# Shared preprocessing / evidence
REPRESENTATIVE_VALUES = "representative_values"
DOMINANT_ENTITY_TYPE = "dominant_entity_type"
VALUE_ENRICHMENT_MAP = "value_enrichment_map"
PREFERRED_LOOKUP_VALUE = "preferred_lookup_value"

# Routing
HEADER_IS_WEAK = "header_is_weak"
CELL_STRENGTH = "cell_strength"
CELL_STRENGTH_THRESHOLD = "cell_strength_threshold"

# Topic detection
TOPIC_DETECTION_PROMPT = "topic_detection_prompt"
TOPIC_DETECTION_RAW_ANSWER = "topic_detection_raw_answer"
TOPIC_DETECTION_APPLIED = "topic_detection_applied"

# CEA
CEA_TARGET = "cea_target"
CEA_SKIP_REASON = "cea_skip_reason"
CEA_CANDIDATE_QUERY = "cea_candidate_query"
CEA_CANDIDATE_SOURCE = "cea_candidate_source"
CEA_CANDIDATE_COUNT = "cea_candidate_count"
CEA_CANDIDATE_SKIPPED = "cea_candidate_skipped"
CEA_SELECTION_PROMPT = "cea_selection_prompt"
CEA_SELECTION_RAW_ANSWER = "cea_selection_raw_answer"
FINAL_CELL_ANNOTATION = "final_cell_annotation"

# CEA reuse
CEA_REUSE_APPLIED = "cea_reuse_applied"
CEA_REUSE_MATCHED_VALUE = "cea_reuse_matched_value"
CEA_REUSE_SOURCE_CELL = "cea_reuse_source_cell"

# CTA
CTA_PROMPT = "cta_prompt"
CTA_RAW_ANSWER = "cta_raw_answer"
CTA_PROVIDER = "cta_provider"
CTA_MODEL = "cta_model"
CTA_SOURCE = "cta_source"
CTA_SELECTED_TYPE = "cta_selected_type"
CTA_SELECTED_TYPE_SOURCE = "cta_selected_type_source"
CTA_SELECTED_TYPE_LABEL = "cta_selected_type_label"
