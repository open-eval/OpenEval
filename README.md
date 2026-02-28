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


## 📋 Schema Reference

<!-- TODO: Add detailed description of the schema fields and structure here -->

TBD; see [`item_schema.json`](item_schema.json) for the full schema specification.

---

## 🎉 Acknowledgements

We sincerely thank Dongyao Zhu from NCSU and Yuzhuo Bai from THU for their significant contributions to data collection during the early stages of OpenEval. Special thanks to Sang Truong from Stanford for the constructive suggestions on the OpenEval schema.