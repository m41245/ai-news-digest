"""
Deterministic benchmark dataset for M80.

Contains a small, representative set of synthetic AI-news-style articles
suitable for evaluating AI provider quality across all supported tasks.

None of the content is copied from copyrighted sources.
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkTask,
)


def _case(
    case_id: str,
    task: BenchmarkTask,
    article_title: str,
    article_content: str,
    **kwargs: Any,
) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        task=task,
        article_title=article_title,
        article_content=article_content,
        **kwargs,
    )


def _s(article_title: str, article_content: str, **kwargs: Any) -> list[BenchmarkCase]:
    """Create cases for all tasks that share the same article."""
    tasks = [
        BenchmarkTask.SUMMARY,
        BenchmarkTask.KEY_TAKEAWAYS,
        BenchmarkTask.WHY_IT_MATTERS,
        BenchmarkTask.CATEGORIES,
        BenchmarkTask.COMPANIES,
        BenchmarkTask.TOPICS,
        BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
    ]
    return [
        _case(
            case_id=(
                f"synthetic_{article_title.lower().replace(' ', '_').replace('-', '_')[:40]}"
                f"_{task.value}"
            ),
            task=task,
            article_title=article_title,
            article_content=article_content,
            **{k: v for k, v in kwargs.items() if k != "task"},
        )
        for task in tasks
    ]


_ARTICLES: list[list[BenchmarkCase]] = [
    _s(
        article_title="OpenAI Releases GPT-5 with Improved Reasoning",
        article_content=(
            "OpenAI announced the release of GPT-5, its latest large language model, "
            "which shows significant improvements in multi-step reasoning and mathematical "
            "problem solving. The model is available through OpenAI's API and will be "
            "integrated into ChatGPT for paid subscribers. OpenAI CEO Sam Altman stated "
            "that GPT-5 achieves state-of-the-art results on standard benchmarks. The "
            "company also introduced new safety fine-tuning techniques. Pricing for API "
            "access remains competitive with existing models. Competitors including "
            "Anthropic and Google DeepMind are expected to respond with their own updates."
        ),
        expected_categories=("ai_models",),
        expected_companies=("OpenAI",),
        expected_topics=("large language models", "reasoning"),
        reference_summary=(
            "OpenAI released GPT-5 with improved multi-step reasoning and "
            "mathematical problem-solving capabilities, available via API and ChatGPT."
        ),
        reference_key_takeaways=(
            "GPT-5 improves multi-step reasoning and math benchmarks.",
            "Available through OpenAI API and ChatGPT paid subscriptions.",
            "OpenAI introduced new safety fine-tuning techniques.",
            "Competitors include Anthropic and Google DeepMind.",
        ),
        reference_why_it_matters=(
            "GPT-5 raises the baseline for commercial LLM capability and "
            "accelerates competitive pressure across the AI industry."
        ),
    ),
    _s(
        article_title="Anthropic Raises $2B for AI Safety Research",
        article_content=(
            "Anthropic secured $2 billion in new funding to expand its AI safety "
            "research programs. The round was led by existing investors with "
            "participation from Google and Microsoft. Anthropic plans to hire "
            "additional safety researchers and build larger alignment evaluation "
            "suites. The company emphasized that the funds will support work on "
            "interpretability and constitutional AI methods. Anthropic's Claude "
            "model family continues to gain adoption among enterprise customers."
        ),
        expected_categories=("ai_business", "ai_safety"),
        expected_companies=("Anthropic", "Google", "Microsoft"),
        expected_topics=("funding", "AI safety", "enterprise AI"),
        reference_summary=(
            "Anthropic raised $2 billion to expand AI safety research, "
            "interpretability, and constitutional AI development."
        ),
        reference_key_takeaways=(
            "Anthropic raised $2 billion for AI safety research.",
            "Google and Microsoft participated in the funding round.",
            "Plans include hiring safety researchers and building alignment suites.",
            "Claude continues to gain enterprise adoption.",
        ),
        reference_why_it_matters=(
            "The funding signals sustained investor confidence in AI safety "
            "as a first-class research priority alongside capability growth."
        ),
    ),
    _s(
        article_title="Google DeepMind Publishes New LLM Scaling Study",
        article_content=(
            "Google DeepMind published a peer-reviewed study on large language model "
            "scaling laws. The paper analyzes how model performance scales with "
            "parameter count, dataset size, and compute budget. Key findings include "
            "diminishing returns beyond certain parameter thresholds for narrow tasks "
            "and continued gains for multi-task performance. The study also highlights "
            "efficiency improvements from mixture-of-experts architectures. Google "
            "DeepMind released the experimental dataset under an open license."
        ),
        expected_categories=("ai_research",),
        expected_companies=("Google",),
        expected_topics=("large language models", "scaling laws", "research"),
        reference_summary=(
            "Google DeepMind published a peer-reviewed study on LLM scaling laws "
            "showing diminishing returns and mixture-of-experts efficiency gains."
        ),
        reference_key_takeaways=(
            "Scaling laws show diminishing returns for narrow tasks.",
            "Multi-task performance continues to improve with scale.",
            "Mixture-of-experts architectures improve efficiency.",
            "Experimental dataset released under an open license.",
        ),
        reference_why_it_matters=(
            "The findings inform how organizations should allocate compute and "
            "data resources when training frontier models."
        ),
    ),
    _s(
        article_title="NVIDIA Announces Next-Generation AI Training Chip",
        article_content=(
            "NVIDIA unveiled its next-generation AI training chip, promising "
            "up to 4x performance improvements over the previous generation. "
            "The chip features improved tensor cores, higher memory bandwidth, "
            "and support for FP8 training. Major cloud providers including AWS, "
            "Google Cloud, and Microsoft Azure have committed to early deployment. "
            "NVIDIA expects the chip to accelerate LLM training and inference "
            "workloads for enterprise customers."
        ),
        expected_categories=("ai_infrastructure",),
        expected_companies=("NVIDIA", "Google", "Microsoft"),
        expected_topics=("chips", "infrastructure", "training"),
        reference_summary=(
            "NVIDIA announced a next-generation AI training chip with up to "
            "4x performance gains and FP8 support."
        ),
        reference_key_takeaways=(
            "New chip delivers up to 4x performance over prior generation.",
            "Features improved tensor cores and higher memory bandwidth.",
            "AWS, Google Cloud, and Microsoft Azure plan early deployment.",
            "Targets LLM training and inference workloads.",
        ),
        reference_why_it_matters=(
            "Faster training silicon reduces both cost and time-to-train for "
            "frontier models, directly impacting AI product roadmaps."
        ),
    ),
    _s(
        article_title="EU Passes Comprehensive AI Regulation Framework",
        article_content=(
            "The European Union passed a comprehensive AI regulation framework "
            "establishing binding rules for high-risk AI systems. The framework "
            "requires transparency obligations for general-purpose AI models, "
            "mandatory risk assessments for biometric identification systems, "
            "and strict data governance requirements. Compliance deadlines begin "
            "in 18 months. Technology industry groups expressed mixed reactions, "
            "with some welcoming clarity and others warning of compliance costs. "
            "The regulation is expected to influence AI policy globally."
        ),
        expected_categories=("ai_policy",),
        expected_companies=(),
        expected_topics=("regulation", "policy", "governance"),
        reference_summary=(
            "The EU passed a comprehensive AI regulation framework imposing "
            "transparency and risk-management obligations on high-risk AI systems."
        ),
        reference_key_takeaways=(
            "New rules apply to high-risk AI systems and general-purpose models.",
            "Transparency and risk-assessment obligations take effect in 18 months.",
            "Industry reaction is mixed between clarity and compliance concerns.",
            "The framework is expected to influence global AI policy.",
        ),
        reference_why_it_matters=(
            "EU AI rules set a de-facto global compliance baseline that affects "
            "model deployment, documentation, and governance investments."
        ),
    ),
    _s(
        article_title="Hugging Face Releases Open-Source Embedding Model",
        article_content=(
            "Hugging Face released an open-source embedding model optimized for "
            "retrieval-augmented generation pipelines. The model achieves competitive "
            "retrieval accuracy on public benchmarks while remaining lightweight "
            "enough to run on consumer GPUs. Hugging Face published training code, "
            "weights, and evaluation scripts under the Apache 2.0 license. Early "
            "community benchmarks show strong performance on technical documentation "
            "retrieval. Mistral announced integration support in its toolchain."
        ),
        expected_categories=("developer_tools",),
        expected_companies=("Hugging Face", "Mistral"),
        expected_topics=("open source", "embeddings", "RAG"),
        reference_summary=(
            "Hugging Face released an open-source embedding model for RAG "
            "pipelines with competitive retrieval accuracy and Apache 2.0 licensing."
        ),
        reference_key_takeaways=(
            "Open-source embedding model optimized for retrieval-augmented generation.",
            "Runs on consumer GPUs with competitive benchmark accuracy.",
            "Training code, weights, and evaluation scripts are Apache 2.0 licensed.",
            "Mistral announced integration support.",
        ),
        reference_why_it_matters=(
            "Open, lightweight embedding models lower the barrier to building "
            "private RAG systems without relying on proprietary APIs."
        ),
    ),
    _s(
        article_title="Meta AI Open-Sources New Computer Vision Architecture",
        article_content=(
            "Meta AI open-sourced a new computer vision architecture designed for "
            "efficient edge inference. The architecture uses a hybrid transformer "
            "and CNN design to reduce latency on mobile devices while maintaining "
            "accuracy on standard vision benchmarks. Meta released pretrained "
            "weights, model definitions, and benchmarking code. The release follows "
            "earlier open-source contributions from Meta in the language-model space. "
            "Researchers noted improvements in low-light object detection."
        ),
        expected_categories=("ai_research", "developer_tools"),
        expected_companies=("Meta",),
        expected_topics=("computer vision", "open source", "edge AI"),
        reference_summary=(
            "Meta AI open-sourced a hybrid transformer-CNN vision architecture "
            "optimized for efficient edge inference."
        ),
        reference_key_takeaways=(
            "Hybrid architecture targets low-latency edge inference.",
            "Maintains accuracy on standard vision benchmarks.",
            "Pretrained weights, definitions, and benchmarks released openly.",
            "Improves low-light object detection.",
        ),
        reference_why_it_matters=(
            "Open, efficient vision models expand on-device AI use cases without "
            "requiring cloud-dependent inference."
        ),
    ),
    _s(
        article_title="xAI Launches Grok-3 API for Developers",
        article_content=(
            "xAI launched a developer API for its Grok-3 model, offering real-time "
            "information retrieval and code generation capabilities. The API supports "
            "streaming responses and structured JSON outputs. Early access pricing is "
            "positioned below competing enterprise APIs. xAI emphasized integrations "
            "with popular developer tools and frameworks. The service is initially "
            "available in selected regions with global rollout planned for next quarter."
        ),
        expected_categories=("ai_products",),
        expected_companies=("xAI",),
        expected_topics=("APIs", "developer tools", "real-time data"),
        reference_summary=(
            "xAI launched a developer API for Grok-3 with real-time retrieval "
            "and structured JSON support."
        ),
        reference_key_takeaways=(
            "Grok-3 API offers real-time information retrieval.",
            "Supports streaming responses and structured JSON outputs.",
            "Pricing is positioned below competing enterprise APIs.",
            "Global rollout is planned for next quarter.",
        ),
        reference_why_it_matters=(
            "Developer access to real-time-grounded models increases competition "
            "in the API layer and reduces reliance on static training data."
        ),
    ),
    _s(
        article_title="OpenAI and Microsoft Expand Enterprise AI Partnership",
        article_content=(
            "OpenAI and Microsoft announced an expanded enterprise partnership "
            "covering Azure OpenAI Service, joint engineering roadmaps, and "
            "co-developed industry solutions. The agreement includes dedicated "
            "Azure capacity for OpenAI model deployments, shared safety research, "
            "and integrated billing. Financial terms were not disclosed. The "
            "partnership reinforces the close relationship between the two companies "
            "as both face increasing regulatory scrutiny in the EU and US."
        ),
        expected_categories=("ai_business",),
        expected_companies=("OpenAI", "Microsoft"),
        expected_topics=("partnerships", "enterprise AI", "regulation"),
        reference_summary=(
            "OpenAI and Microsoft expanded their enterprise AI partnership "
            "with joint roadmaps, dedicated Azure capacity, and shared safety research."
        ),
        reference_key_takeaways=(
            "Partnership covers Azure OpenAI Service and joint engineering.",
            "Includes dedicated Azure capacity and integrated billing.",
            "Shared safety research is part of the agreement.",
            "Both companies face growing regulatory scrutiny.",
        ),
        reference_why_it_matters=(
            "The alliance shapes enterprise AI availability, pricing, and "
            "compliance posture across major cloud markets."
        ),
    ),
]

CASES: tuple[BenchmarkCase, ...] = tuple(
    case for article_cases in _ARTICLES for case in article_cases
)


def load_dataset() -> BenchmarkDataset:
    """Return the built-in deterministic benchmark dataset."""
    return BenchmarkDataset(
        name="ai_news_quality_v1",
        version="2026-09-14",
        cases=CASES,
    )


def get_cases_for_task(task: BenchmarkTask) -> tuple[BenchmarkCase, ...]:
    """Return all benchmark cases for a specific task."""
    return tuple(case for case in CASES if case.task == task)


__all__ = ["CASES", "get_cases_for_task", "load_dataset"]
