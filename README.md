# SymOnco demo

This repository contains some of the components built in the preparation for the SymOnco project. They contain the omics pdf report parser, the prompt optimization module used to extract various features from MTB treatment recommendation letters and the python FastAPI microservices used to retrieve data from public APIs.

⚠️  As a big part of our internal codebase (*i.e.* feature extraction validation, test knowledge graph) contains patient-related data, we are not able to release it publicly for the moment. ⚠️

## Components

| Folder | Purpose | Default port |
| --- | --- | ---: |
| [`OmicsReportParser_demo/`](./OmicsReportParser_demo/) | Parse standardized WGS and WES reports into json files. | — |
| [`mipro_v2/`](./mipro_v2/) | Tune and run DSPy MIPROv2 extractors for publications, trials, genes, drugs, and evidence levels | — |
| [`fetch_publications/`](./fetch_publications/) | Resolve PubMed identifiers and fetch metadata, with optional PMC full text | 5170 |
| [`fetch_drugs/`](./fetch_drugs/) | Resolve drug names using the NCI Drug Dictionary | 5171 |
| [`fetch_trials/`](./fetch_trials/) | Normalize NCT identifiers and fetch ClinicalTrials.gov trial records | 5172 |

## References

### Grant proposal references

#### Novelty fo Medical use-case

1. Sung, Hyuna, Adalberto M. Filho, Mathieu Laversanne, et al. 2026. “Global Cancer Statistics 2024: GLOBOCAN Estimates of Incidence and Mortality Worldwide for 34 Cancers in 186 Countries.” CA: A Cancer Journal for Clinicians 76 (4). [https://doi.org/10.3322/caac.70090.](https://doi.org/10.3322/caac.70090.)

#### Technical Novelty 

1. AI in oncology: Improving tumor board workflows - https://diagnostics.roche.com/global/en/healthcare-transformers/article/ai-in-oncology-tumor-boards.html 
2. Digital assistant for cancer treatment - University Medicine Zurich - https://umzh.uzh.ch/en/project/ai-tumorboard 
3. Seshachalam, Arun, K. Niraimathi Anandan, Tamilarasi Dharaniraj, et al. 2026. “The AI Paradox in Precision Oncology: Prospective Blinded Validation of Large Language Models against Molecular Tumor Board.” Journal of Clinical Oncology 44 (16_suppl): 11047–11047. https://doi.org/10.1200/jco.2026.44.16_suppl.11047.
4. The AI-based Tumor Board: A Multi-agent approach to finding cancer treatments with AI. - https://www.ml6.eu/en/blog/the-ai-based-tumor-board-a-multi-agent-approach-to-finding-cancer-treatments-with-ai
5. Chelli, Mikaël, Jules Descamps, Vincent Lavoué, et al. 2024. “Hallucination Rates and Reference Accuracy of ChatGPT and Bard for Systematic Reviews: Comparative Analysis.” Journal of Medical Internet Research 26 (May): e53164. https://doi.org/10.2196/53164. 
6. Hübschmann, Daniel, Simon Kreutzfeldt, Benjamin Roth, et al. 2026. “The Knowledge Connector Decision Support System for Multiomics-Based Precision Oncology.” Nature Communications 17 (1). https://doi.org/10.1038/s41467-026-68333-3.
7. Zhu, Yuqicheng, Nico Potyka, Daniel Hernández, Yuan He, Zifeng Ding, Bo Xiong, Dong Zhou, Evgeny Kharlamov, and Steffen Staab. 2025. "ArgRAG: Explainable Retrieval Augmented Generation using Quantitative Bipolar Argumentation." In Proceedings of the 19th International Conference on Neurosymbolic Learning and Reasoning, 284:1–22. PMLR. https://doi.org/10.48550/arXiv.2508.20131.
8. Chen, Zhongwu, Chengjin Xu, Dingmin Wang, Zhen Huang, Yong Dou, and Jian Guo. 2024. "RuleRAG: Rule-Guided Retrieval-Augmented Generation with Language Models for Question Answering." arXiv preprint arXiv:2410.22353. https://doi.org/10.48550/arXiv.2410.22353. 


### Repository references 
- Opsahl-Ong et al. (2024), “Optimizing Instructions and Demonstrations for
  Multi-Stage Language Model Programs,” [arXiv:2406.11695](https://arxiv.org/abs/2406.11695).
- [DSPy MIPROv2 optimizer documentation](https://dspy.ai/api/optimizers/MIPROv2/).
- [NCBI E-utilities documentation](https://www.ncbi.nlm.nih.gov/books/NBK25501/).
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/) and [PMC BioC API](https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/).
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api).
- [NCI Drug Dictionary](https://www.cancer.gov/publications/dictionaries/cancer-drug) and [NCI API portal](https://api.cancer.gov/).

### Other references

- Institute website - https://www.uniklinik-freiburg.de/institute-of-medical-bioinformatics-and-systems-medicine.html 
- Zentrum für Personalisierte Medizin (ZPM) / Molecular Tumor Board - https://www.uniklinik-freiburg.de/zpm/zpmo.html#MTB
