# OpenEval

An open-source, **item-centered evaluation repository** toward **the open science of AI evaluation**.
This GitHub repository is an official resource center for OpenEval, maintained by the [Human-Centered Eval](https://huggingface.co/human-centered-eval) project.

> [🌐 OpenEval Homepage](https://open-eval.github.io/)  |  [🤗 Huggingface Dataset](https://huggingface.co/datasets/human-centered-eval/OpenEval)

## ❓ Why Item-Level Benchmark Data Matters for AI Evaluation Science

AI evaluation suffers from opacity and inconsistency, with results scattered across benchmarks and repositories in incompatible formats. To address this, we propose **OpenEval** — a large-scale, item-centered repository where every evaluation instance is captured in a self-contained schema while remaining connected to the broader experimental context.

Our **position paper** is available in this repository: [Position: Science of AI Evaluation Requires Item-level Benchmark Data](position_paper.pdf). Feel free to take a look!


## 🔍 Want to Explore OpenEval?

Thank you for your interest in OpenEval!

1. **Browse the schema** — refer to [`item_schema.json`](item_schema.json) for the full structure, field requirements, and field descriptions. A comprehensive [Schema Reference](#schema-reference) of the OpenEval schema of the current version (v0.1.0) is provided below.
2. **See our examples** — two example items are provided in [`item_examples.json`](item_examples.json). We are curating more items from different types of AI evaluations.
3. **Access full data** — all data will be shared in our [Huggingface Dataset](https://huggingface.co/datasets/human-centered-eval/OpenEval). We are still formatting the data, so please stay tuned and we appreciate your patience😊.


## ⛽ Interested in Contributing to OpenEval?

Thank you for considering contributing your data to OpenEval!

1. **Convert** your evaluation results into the OpenEval schema according to the schema ([`item_schema.json`](item_schema.json)) and examples ([`item_examples.json`](item_examples.json)) provided. You may also refer to the detailed [Schema Reference](#schema-reference) below for guidance.
2. **Validate** your submission using [`openeval_validator.py`](openeval_validator.py). The `validate_entry` function takes a JSON-formatted data entry as input and outputs:
   - Whether the entry passes validation
   - Which fields/keys need correction (if any)
   - The types of violations found
3. **Submit** a pull request to this repository with your `.json` or `.jsonl` files. We will notify you throughout the review process.
4. **Integration** — once your submission passes review, we will integrate your data into the OpenEval Huggingface dataset and send you a confirmation regarding your contribution.

> If you need any further guidance or assistance, please don't hesitate to [open an issue](../../issues) or [email us](mailto:hjiang66@jh.edu,ziang.xiao@jhu.edu). We are more than happy to help.


## 📋 Schema Reference (v0.1.0)

Each OpenEval item is a self-contained JSON object capturing an evaluation instance, its experimental context, and all associated responses and scores. The schema is organized into four top-level fields:

| Field | Type | Requirement | Description |
|---|---|---|---|
| `item_id` | `str` | auto | Unique identifier for the item, generated automatically at ingestion. |
| `item_metadata` | `object` | — | Ingestion timestamp, contributor info, and benchmark provenance. |
| `item_content` | `object` | — | Original item content from the source benchmark. |
| `responses` | `list[object]` | — | Response(s) produced by model(s) for this item, with scores. |
| `schema_version` | `str` | auto | OpenEval schema version, populated automatically. |

> **Requirement levels:** `auto` = populated automatically (do not fill); `required` = must be provided; `non-empty` = must be provided and non-empty; `optional` = may be omitted.

---

### `item_metadata`

Top-level metadata attached to an item upon ingestion.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `ingestion_time` | `str` | auto | Timestamp of when the item was ingested (ISO 8601 format). |
| `contributor.name` | `str` | optional | Name of the contributor(s), comma-separated. |
| `contributor.email` | `str` | optional | Email address of the contributor(s). |
| `contributor.affiliation` | `str` | optional | Institutional or organizational affiliation of the contributor(s). |
| `source.benchmark_name` | `str` | non-empty | Name of the benchmark or dataset this item originates from. |
| `source.benchmark_version` | `str` | required | Version identifier of the benchmark or dataset. |
| `source.paper_url` | `str` | optional | URL to the paper introducing or describing the benchmark. |
| `source.dataset_url` | `str` | optional | URL to the benchmark dataset (e.g., a Hugging Face dataset page). |
| `source.benchmark_tags` | `list[str]` | optional | Tags or keywords associated with the benchmark (e.g., `["reasoning", "math"]`). |

---

### `item_content`

The original content of the evaluation item as it appears in the source benchmark, before any model-specific adaptation.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `input` | `list[str\|dict]` | non-empty | Content of the item — e.g., a question, a dialogue, or multiple-choice options. Each element may be a plain string or a structured dict. |
| `references` | `list[str\|dict]` | required | Reference answers or artifacts used by the evaluation metric. Each element may be a plain string or a structured dict. |

---

### `responses[]`

An array of response objects, one per model run associated with this item.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `response_id` | `str` | auto | Unique identifier for the response, auto-generated and prefixed with the parent `item_id`. |
| `model` | `object` | — | Identity and configuration of the respondent model. |
| `item_adaptation` | `object` | — | The adapted form of the item as actually presented to the model. |
| `response_content` | `list[str\|dict]` | non-empty | Output produced by the model — e.g., the model's answer or generated text. |
| `scores` | `list[object]` | — | Metric score(s) assigned to this response. |

#### `responses[].model`

| Field | Type | Requirement | Description |
|---|---|---|---|
| `model.name` | `str` | non-empty | Name of the respondent model (e.g., `"gpt-4o"`). |
| `model.size` | `str` | optional | Parameter count or size label of the model (e.g., `"7B"`). |

#### `responses[].model.model_adaptation`

Describes how the model was configured for this response.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `model_adaptation.system_instruction` | `str` | required | System instruction or system prompt used to configure the model. |
| `model_adaptation.generation_parameters.temperature` | `float` | required | Sampling temperature used during generation. |
| `model_adaptation.generation_parameters.do_sample` | `bool` | required | Whether sampling was used; `false` indicates greedy decoding. |
| `model_adaptation.generation_parameters.top_k` | `int` | required | Top-*k* value used for generation. |
| `model_adaptation.generation_parameters.top_p` | `float` | required | Top-*p* (nucleus sampling) value used for generation. |
| `model_adaptation.generation_parameters.max_tokens` | `int` | required | Maximum number of tokens the model was allowed to generate. |
| `model_adaptation.tools` | `list[object]` | — | Tools made available to the model. Each entry has `type` (str, required) and `content` (any, required). |

#### `responses[].item_adaptation`

The item as concretely presented to the model, which may differ from `item_content` due to prompt formatting, few-shot examples, or external resources.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `item_adaptation.request_input` | `list[str\|dict]` | non-empty | Actual input provided to the model — e.g., the formatted prompt with instructions. |
| `item_adaptation.demonstrations` | `list[str]` | optional | Few-shot demonstrations or in-context examples provided to the model. |
| `item_adaptation.external_resources` | `list[object]` | — | External resources from the test environment (e.g., retrieved documents). Each entry has `type` (str, required) and `content` (any, required). |

#### `responses[].scores[]`

Each score object pairs an evaluation metric with its computed value.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `scores[].metric.name` | `str` | non-empty | Name of the evaluation metric (e.g., `"ROUGE-L"`, `"GPT-4 Judge"`). |
| `scores[].metric.models` | `list[str]` | required | Model(s) or algorithm(s) used to compute the metric, if applicable. |
| `scores[].metric.extra_artifacts` | `list[object]` | — | Additional artifacts used for scoring (e.g., rubrics). Each entry has `type` (str, required) and `content` (any, required). |
| `scores[].value` | `int\|float\|bool` | non-empty | Numeric or boolean value of the metric score for this response. |

### Notes on HF Storage Adaptation

When data is pushed to the Hugging Face dataset, the schema undergoes three adaptations:

**1. Table split.** The data are split into three tables for storage efficiency:

| Table | Indexed by | Description |
|---|---|---|
| `bench` | `benchmark_name` | One entry per source benchmark. |
| `item` | `item_id` | One entry per evaluation item; includes `source.benchmark_name` for joining with `bench`. |
| `response` | `response_id` | One entry per model response; `response_id` is prefixed with the corresponding `item_id` for joining with `item`. |

**2. JSON stringification.** Fields that are polymorphic (`str | dict`) or structurally complex are serialized to JSON strings to satisfy the Parquet column schema. When reading from the dataset, these fields must be parsed back with `json.loads()`. Affected fields:

| Field | Stored as |
|---|---|
| `item_content.input[]` | `str` elements kept as-is; `dict` elements → `json.dumps()` |
| `item_content.references[]` | `str` elements kept as-is; `dict` elements → `json.dumps()` |
| `model.model_adaptation.generation_parameters` | Single JSON string (entire object) |
| `model.model_adaptation.tools[].content` | Non-string values → `json.dumps()` |
| `item_adaptation.request_input[]` | `str` elements kept as-is; `dict` elements → `json.dumps()` |
| `item_adaptation.external_resources[].content` | Non-string values → `json.dumps()` |
| `response_content[]` | `str` elements kept as-is; `dict` elements → `json.dumps()` |
| `scores[].metric.extra_artifacts[].content` | Non-string values → `json.dumps()` |

**3. Float conversion.** `scores[].value` is cast to `float64` regardless of its original type (`int`, `float`, or `bool`) to satisfy the Parquet column schema.

---

## 🎉 Acknowledgements

We sincerely thank Dongyao Zhu from NCSU and Yuzhuo Bai from THU for their significant contributions to data collection during the early stages of OpenEval. Special thanks to Sang Truong from Stanford for the constructive suggestions on the OpenEval schema.