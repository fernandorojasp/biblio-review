# Search strategy documentation (PRISMA-S)

## 1. Research objectives

# Research objectives

## General objective

Analizar, mediante técnicas bibliométricas, la evolución, estructura y dinámicas de la producción científica en inteligencia artificial multimodal aplicada al diagnóstico médico durante el periodo 2020–2025, con especial atención al impacto de la IA generativa como factor de transformación del campo a partir de 2022–2023.

## Specific objectives

- **OE1.** Caracterizar la dinámica de crecimiento del campo: cuantificar la evolución temporal de las publicaciones y citas, identificar los países, instituciones, autores y revistas más productivos e influyentes, y analizar los patrones de acceso abierto frente a acceso cerrado.

- **OE2.** Mapear la estructura intelectual del campo: identificar las bases de conocimiento fundamentales mediante análisis de co-citación de referencias y autores, detectar los artículos seminales y los puntos de inflexión bibliográficos, y delinear las escuelas de pensamiento que configuran el campo.

- **OE3.** Analizar la estructura social del campo: examinar las redes de coautoría a nivel de autores, instituciones y países para identificar comunidades de investigación, patrones de colaboración internacional y la existencia o ausencia de puentes entre disciplinas (informática, medicina, ingeniería biomédica).

- **OE4.** Cartografiar la estructura conceptual del campo: identificar los temas nucleares, los temas emergentes y los temas en declive mediante análisis de co-ocurrencia de palabras clave, mapas temáticos y análisis de evolución temática, con especial énfasis en detectar la irrupción de términos asociados a la IA generativa y su impacto en la reconfiguración del mapa conceptual.

- **OE5.** Identificar lagunas de investigación y proponer una agenda futura: detectar nichos temáticos desatendidos, áreas con alto potencial de crecimiento y líneas de investigación emergentes que requieren atención prioritaria por parte de la comunidad científica.

## Research questions

- **PI1.** ¿Cómo ha evolucionado el volumen anual de publicaciones sobre IA multimodal en diagnóstico médico entre 2020 y 2025, y se observa un cambio de pendiente estadísticamente significativo en 2022–2023 asociado a la irrupción de la IA generativa y los modelos de lenguaje de gran escala?

- **PI2.** ¿Cuáles son los países, instituciones, autores y revistas que lideran la producción científica en este campo, y cómo se distribuye geográficamente la colaboración internacional?

- **PI3.** ¿Cuáles son los artículos seminales ("landmark papers") que constituyen las bases intelectuales del campo, y han cambiado estos referentes a partir de la irrupción de la IA generativa?

- **PI4.** ¿Cómo se ha transformado la estructura temática del campo entre el periodo pre-generativo (2020–2022) y el periodo post-generativo (2023–2025)? ¿Qué temas han emergido, cuáles han declinado y cuáles han mutado conceptualmente?

- **PI5.** ¿Qué nichos de investigación permanecen desatendidos y qué líneas de trabajo futuro se derivan del análisis bibliométrico?

## Key conceptual domains

1. **Inteligencia artificial y técnicas computacionales** — incluyendo métodos clásicos de aprendizaje automático y profundo (CNN, transformers, mecanismos de atención) y modelos generativos emergentes (LLM, VLM, modelos de difusión, foundation models)
2. **Procesamiento multimodal** — integración de dos o más modalidades de datos (imágenes, texto, señales fisiológicas, datos tabulares, registros clínicos electrónicos)
3. **Diagnóstico médico** — en todas sus especialidades clínicas (radiología, patología, dermatología, oftalmología, etc.)

## Period and scope

- **Period**: 2020–2025
  - Pre-generative (2020–2022): CNN, classical attention, early transformers in medicine
  - Post-generative (2023–2025): LLM, VLM, diffusion models, foundation models
  - Split year: 2023
- **Databases**: Web of Science Core Collection, Scopus
- **Languages**: English
- **Document types**: Articles, Reviews, Conference proceedings

## Preliminary corpus data

- WoS records: 6,612
- Scopus records: 12,137 (12,149 − 12 internal duplicates)
- Total raw: 18,749
- Duplicates removed: 5,887 (31.4%)
- Unique corpus: 12,862
- Temporal distribution: 2020: 631 | 2021: 907 | 2022: 1,245 | 2023: 1,680 | 2024: 2,765 | 2025: 5,416
- CAGR: 53.7%


## 2. Information sources

Databases searched: Web of Science Core Collection, Scopus

## 3. Original search queries

# Current search queries

## Web of Science
TS=(("generative artificial intelligence" OR "generative AI" OR "GenAI" OR "large language model*" OR "LLM" OR "foundation model*" OR "multimodal model*" OR "vision-language model*" OR "GPT" OR "ChatGPT" OR "BERT" OR "transformer*" OR "diffusion model*" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing") AND ("multimodal*" OR "multi-modal*" OR "cross-modal*" OR "data fusion" OR "information fusion" OR "image-text" OR "vision-language" OR "multi-source") AND ("medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "chest X-ray" OR "CT scan" OR "MRI" OR "retinal" OR "dermatolog*" OR "cancer diagnos*" OR "tumor detect*")) AND PY=(2020-2025) AND LA=(English) AND DT=("Article" OR "Review Article" OR "Proceedings Paper")

## Scopus  
TITLE-ABS-KEY ( ( "generative artificial intelligence" OR "generative AI" OR "GenAI" OR "large language model*" OR "LLM" OR "foundation model*" OR "multimodal model*" OR "vision-language model*" OR "GPT" OR "ChatGPT" OR "BERT" OR "transformer*" OR "diffusion model*" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing" ) AND ( "multimodal*" OR "multi-modal*" OR "cross-modal*" OR "data fusion" OR "information fusion" OR "image-text" OR "vision-language" OR "multi-source" ) AND ( "medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "chest X-ray" OR "CT scan" OR "MRI" OR "retinal" OR "dermatolog*" OR "cancer diagnos*" OR "tumor detect*" ) ) AND PUBYEAR > 2019 AND PUBYEAR < 2026 AND LANGUAGE ( english ) AND DOCTYPE ( ar OR re OR cp ) AND PUBYEAR > 2019 AND PUBYEAR < 2026

## Search date
2026/03/09

## Results
- WoS: 6,621 records
- Scopus: 12,217 records


## 4. Optimized search queries

### WOS

```
TS=(("generative artificial intelligence" OR "generative AI" OR "large language model*" OR "LLM" OR "MLLM" OR "foundation model*" OR "multimodal large language model*" OR "vision language model*" OR "vision-language model*" OR "GPT" OR "GPT-4V" OR "ChatGPT" OR "BERT" OR "transformer*" OR "vision transformer*" OR "ViT" OR "diffusion model*" OR "stable diffusion" OR "CLIP" OR "LLaVA" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing" OR "attention mechanism*" OR "self-supervised learning" OR "few-shot learning" OR "zero-shot learning") AND ("multimodal*" OR "multi-modal*" OR "cross-modal*" OR "multimodal fusion" OR "multimodal learning" OR "data fusion" OR "information fusion" OR "feature fusion" OR "image-text" OR "vision-language" OR "vision-text" OR "multi-source" OR "joint representation*" OR "multimodal embedding*" OR "cross-modal learning") AND ("medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "clinical imaging" OR "biomedical imaging" OR "medical image analysis" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "medical AI" OR "clinical AI" OR "healthcare AI" OR "chest X-ray" OR "CT scan" OR "MRI" OR "mammography" OR "ultrasound" OR "PET scan" OR "retinal" OR "dermatolog*" OR "ophthalmolog*" OR "cancer diagnos*" OR "tumor detect*" OR "lesion detection" OR "abnormality detection")) AND PY=(2020-2025) AND LA=(English) AND DT=("Article" OR "Review Article" OR "Proceedings Paper")
```

### SCOPUS

```
TITLE-ABS-KEY(("generative artificial intelligence" OR "generative AI" OR "large language model*" OR "LLM" OR "MLLM" OR "foundation model*" OR "multimodal large language model*" OR "vision language model*" OR "vision-language model*" OR "GPT" OR "GPT-4V" OR "ChatGPT" OR "BERT" OR "transformer*" OR "vision transformer*" OR "ViT" OR "diffusion model*" OR "stable diffusion" OR "CLIP" OR "LLaVA" OR "artificial intelligence" OR "deep learning" OR "machine learning" OR "neural network*" OR "computer vision" OR "natural language processing" OR "attention mechanism*" OR "self-supervised learning" OR "few-shot learning" OR "zero-shot learning") AND ("multimodal*" OR "multi-modal*" OR "cross-modal*" OR "multimodal fusion" OR "multimodal learning" OR "data fusion" OR "information fusion" OR "feature fusion" OR "image-text" OR "vision-language" OR "vision-text" OR "multi-source" OR "joint representation*" OR "multimodal embedding*" OR "cross-modal learning") AND ("medical diagnos*" OR "clinical diagnos*" OR "disease detection" OR "medical imaging" OR "clinical imaging" OR "biomedical imaging" OR "medical image analysis" OR "radiology" OR "patholog*" OR "histopatholog*" OR "computer-aided diagnos*" OR "clinical decision support" OR "diagnostic accuracy" OR "electronic health record*" OR "medical AI" OR "clinical AI" OR "healthcare AI" OR "chest X-ray" OR "CT scan" OR "MRI" OR "mammography" OR "ultrasound" OR "PET scan" OR "retinal" OR "dermatolog*" OR "ophthalmolog*" OR "cancer diagnos*" OR "tumor detect*" OR "lesion detection" OR "abnormality detection")) AND PUBYEAR > 2019 AND PUBYEAR < 2026 AND LANGUAGE(english) AND DOCTYPE(ar OR re OR cp)
```

## 5. Filters applied

- **Period**: 2020–2025
- **Language**: english
- **Document types**: article, review, conference paper

## 6. Search date

Date of search execution: [TO BE COMPLETED]

## 7. Search strategy validation

- Strategy reviewed by: [TO BE COMPLETED]
- Peer review of search strategy (PRESS): [TO BE COMPLETED]
- AI-assisted query analysis: Performed via biblio-review v0.1.0 (Claude API)

---
*Generated by biblio-review v0.1.0 on 2026-03-15 15:58 UTC*
