# Query comparison report

## 1. Summary assessment

The original queries are **reasonably adequate** but have several issues that could impact the comprehensiveness and precision of the corpus. While they capture the core concepts of AI, multimodal processing, and medical diagnosis, they miss important recent terminology related to generative AI and contain some technical inefficiencies. The queries would benefit from optimization to better align with the research objectives, particularly for capturing the evolution from pre-generative to post-generative AI periods.

## 2. Coverage analysis by conceptual block

### Block A: AI and computational techniques
- **Original coverage**: Strong coverage of classical terms ("artificial intelligence", "deep learning", "machine learning", "neural network*", "transformer*") and some generative AI terms ("large language model*", "foundation model*", "diffusion model*", "GPT", "ChatGPT", "BERT")
- **Missing terms**: Key generative AI terms missing: "vision language model*", "multimodal large language model*", "MLLM", "foundation model*" variants, "stable diffusion", "DALL-E", "GPT-4V", "LLaVA", "CLIP", "ViT" (Vision Transformer), "attention mechanism*", "self-supervised learning", "few-shot learning", "zero-shot learning", "prompt engineering"
- **Redundant terms**: "GenAI" is uncommon in academic literature and could be removed

### Block B: Multimodal processing
- **Original coverage**: Good basic coverage with "multimodal*", "multi-modal*", "cross-modal*", "data fusion", "information fusion", "image-text", "vision-language", "multi-source"
- **Missing terms**: Important missing terms: "multimodal fusion", "feature fusion", "modal*" AND "integration", "cross-modal learning", "multimodal learning", "joint representation*", "multimodal embedding*", "vision-text", "audio-visual", "sensor fusion" (for physiological signals)
- **Redundant terms**: None significant

### Block C: Medical diagnosis
- **Original coverage**: Comprehensive coverage of medical imaging modalities ("chest X-ray", "CT scan", "MRI", "retinal") and specialties ("radiology", "patholog*", "dermatolog*")
- **Missing terms**: Missing key terms: "medical AI", "clinical AI", "healthcare AI", "mammography", "ultrasound", "PET scan", "endoscopy", "ophthalmolog*", "cardiology", "ECG", "EEG", "medical image analysis", "clinical imaging", "biomedical imaging", "medical image classification", "lesion detection", "abnormality detection"
- **Redundant terms**: Some overlap between "patholog*" and "histopatholog*" but both should be kept for precision

## 3. Syntax and technical issues

**WoS-specific issues:**
- Correct use of TS= field and Boolean operators
- Proper parentheses nesting
- Correct use of PY= and LA= and DT= filters
- No major syntax errors

**Scopus-specific issues:**
- **Critical error**: Double year filter ("PUBYEAR > 2019 AND PUBYEAR < 2026" appears twice)
- Should use "PUBYEAR > 2019 AND PUBYEAR < 2026" only once
- TITLE-ABS-KEY field is appropriate
- DOCTYPE filter correct (ar OR re OR cp)

**General operator issues:**
- Proper use of AND/OR operators
- Good parentheses grouping
- Truncation (*) used appropriately

## 4. Alignment with research questions

**PI1** (Evolution 2020-2025, generative AI impact): **Partially aligned**. Queries include generative AI terms but miss many important recent models and techniques that would help detect the 2022-2023 inflection point.

**PI2** (Leading countries/institutions/authors/journals): **Well aligned**. Broad queries will capture publications from all major contributors.

**PI3** (Seminal articles, generative AI impact on foundations): **Partially aligned**. Missing some key generative AI terms might cause underrepresentation of recent landmark papers.

**PI4** (Thematic transformation pre/post-generative): **Needs improvement**. Missing terminology could result in incomplete capture of post-generative period innovations.

**PI5** (Research gaps): **Adequate**. Broad coverage should identify most research directions, though some emerging niches might be missed.

## 5. Optimized queries

### Web of Science
```
TS=(("generative artificial intelligence" OR "generative AI" OR "large language model*" OR "LLM" OR "MLLM" OR "foundation model*" OR "multimodal large language model*" OR "vision language model*" OR "vision-language model*" OR "GPT" OR "GPT-4V" OR "ChatGPT" OR "BERT" OR "transformer*" OR "vision transformer*" OR "ViT" OR "diffusion model*" OR "stable diffusion" OR "CLIP" OR "LLaVA" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing" OR "attention mechanism*" OR "self-supervised learning" OR "few-shot learning" OR "zero-shot learning") AND ("multimodal*" OR "multi-modal*" OR "cross-modal*" OR "multimodal fusion" OR "multimodal learning" OR "data fusion" OR "information fusion" OR "feature fusion" OR "image-text" OR "vision-language" OR "vision-text" OR "multi-source" OR "joint representation*" OR "multimodal embedding*" OR "cross-modal learning") AND ("medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "clinical imaging" OR "biomedical imaging" OR "medical image analysis" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "medical AI" OR "clinical AI" OR "healthcare AI" OR "chest X-ray" OR "CT scan" OR "MRI" OR "mammography" OR "ultrasound" OR "PET scan" OR "retinal" OR "dermatolog*" OR "ophthalmolog*" OR "cancer diagnos*" OR "tumor detect*" OR "lesion detection" OR "abnormality detection")) AND PY=(2020-2025) AND LA=(English) AND DT=("Article" OR "Review Article" OR "Proceedings Paper")
```

### Scopus
```
TITLE-ABS-KEY(("generative artificial intelligence" OR "generative AI" OR "large language model*" OR "LLM" OR "MLLM" OR "foundation model*" OR "multimodal large language model*" OR "vision language model*" OR "vision-language model*" OR "GPT" OR "GPT-4V" OR "ChatGPT" OR "BERT" OR "transformer*" OR "vision transformer*" OR "ViT" OR "diffusion model*" OR "stable diffusion" OR "CLIP" OR "LLaVA" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing" OR "attention mechanism*" OR "self-supervised learning" OR "few-shot learning" OR "zero-shot learning") AND ("multimodal*" OR "multi-modal*" OR "cross-modal*" OR "multimodal fusion" OR "multimodal learning" OR "data fusion" OR "information fusion" OR "feature fusion" OR "image-text" OR "vision-language" OR "vision-text" OR "multi-source" OR "joint representation*" OR "multimodal embedding*" OR "cross-modal learning") AND ("medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "clinical imaging" OR "biomedical imaging" OR "medical image analysis" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "medical AI" OR "clinical AI" OR "healthcare AI" OR "chest X-ray" OR "CT scan" OR "MRI" OR "mammography" OR "ultrasound" OR "PET scan" OR "retinal" OR "dermatolog*" OR "ophthalmolog*" OR "cancer diagnos*" OR "tumor detect*" OR "lesion detection" OR "abnormality detection")) AND PUBYEAR > 2019 AND PUBYEAR < 2026 AND LANGUAGE(english) AND DOCTYPE(ar OR re OR cp)
```

## 6. Diff summary

| Change | Term(s) | Reason | Affected Objective |
|--------|---------|--------|-----------------|
| Added | "MLLM", "multimodal large language model*" | Common abbreviation and full form for multimodal LLMs | OE4, PI4 |
| Added | "GPT-4V", "LLaVA", "CLIP" | Specific influential vision-language models | OE2, OE4, PI3, PI4 |
| Added | "vision transformer*", "ViT" | Important architecture for medical imaging | OE4, PI4 |
| Added | "stable diffusion" | Key generative model for medical imaging | OE4, PI4 |
| Added | "attention mechanism*", "self-supervised learning" | Fundamental techniques | OE4 |
| Added | "few-shot learning", "zero-shot learning" | Important capabilities in medical AI | OE4, OE5 |
| Added | "multimodal fusion", "multimodal learning", "feature fusion" | Core multimodal processing concepts | OE4 |
| Added | "vision-text", "joint representation*", "multimodal embedding*" | Additional multimodal terms | OE4 |
| Added | "medical AI", "clinical AI", "healthcare AI" | Broader medical AI terminology | OE1, OE4 |
| Added | "mammography", "ultrasound", "PET scan", "ophthalmolog*" | Additional medical imaging modalities | OE4 |
| Added | "clinical imaging", "biomedical imaging", "medical image analysis" | Broader imaging terms | OE4 |
| Added | "lesion detection", "abnormality detection" | Specific diagnostic tasks | OE4 |
| Removed | "GenAI" | Uncommon in academic literature | - |
| Fixed | Duplicate PUBYEAR filter in Scopus | Technical error correction | - |

## 7. Recommendation

**Recommendation: Re-run with optimized queries**

The current corpus is adequate for basic analysis but would benefit significantly from the optimized queries. The additions are particularly important for:
1. Better capturing the generative AI revolution (2022-2023) which is central to PI1 and PI4
2. Identifying recent landmark papers and models (PI3)
3. More comprehensive thematic mapping of the post-generative period (OE4, PI4)

**Estimated impact**: The optimized queries would likely increase the corpus by 15-25%, with the most significant additions being recent papers (2023-2025) focused on vision-language models, multimodal LLMs, and specific generative AI applications in medical diagnosis. This additional coverage is crucial for accurately detecting the thematic transformation that is central to the research objectives.

The technical fix of the duplicate year filter in Scopus is also essential for search reproducibility and reporting compliance with PRISMA-S guidelines.