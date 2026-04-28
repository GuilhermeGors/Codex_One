"""
Codex One v2 — PII Scrubber (Privacy by Design)

Uses Microsoft Presidio to detect and anonymize Personally Identifiable Information
(PII) such as Names, Emails, and CPFs in Portuguese before storing them in ChromaDB.
"""

from typing import Optional
import spacy

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
    from presidio_anonymizer import AnonymizerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
except ImportError:
    AnalyzerEngine = None
    print("[PII] Presidio not installed. Run: pip install presidio-analyzer presidio-anonymizer spacy")

# Singletons
_analyzer: Optional[AnalyzerEngine] = None
_anonymizer: Optional[AnonymizerEngine] = None


def get_pii_engines():
    """Lazy-load the Presidio engines to save memory when not in use."""
    global _analyzer, _anonymizer
    
    if AnalyzerEngine is None:
        return None, None

    if _analyzer is None:
        try:
            # Check if Portuguese model is installed
            if not spacy.util.is_package("pt_core_news_sm"):
                print("[PII] Warning: pt_core_news_sm not found. Falling back to English if available.")

            # Configure NLP engine for Portuguese
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "pt", "model_name": "pt_core_news_sm"},
                    {"lang_code": "en", "model_name": "en_core_web_sm"}, # Fallback
                ],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            # Initialize Registry
            registry = RecognizerRegistry()
            registry.supported_languages = ["pt", "en"]
            registry.load_predefined_recognizers(nlp_engine=nlp_engine, languages=["pt", "en"])

            # Add Custom CPF Recognizer for Brazil
            # A simple regex for CPF format: XXX.XXX.XXX-XX or XXXXXXXXXXX
            cpf_pattern = Pattern(
                name="cpf_pattern",
                regex=r"\b([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}\-?[0-9]{2})\b",
                score=0.8
            )
            cpf_recognizer = PatternRecognizer(
                supported_entity="BR_CPF",
                patterns=[cpf_pattern],
                context=["cpf", "documento", "cadastro"],
                supported_language="pt",
            )
            registry.add_recognizer(cpf_recognizer)

            _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry, supported_languages=["pt", "en"])
            _anonymizer = AnonymizerEngine()
            
            print("[PII] Presidio Analyzer initialized successfully for PT/EN.")
        except Exception as e:
            print(f"[PII] Initialization failed: {e}")
            return None, None

    return _analyzer, _anonymizer


def anonymize_text(text: str, language: str = "pt") -> tuple[str, dict[str, int]]:
    """
    Detects and masks PII in the text.
    Returns the scrubbed text and a dictionary of redaction counts.
    """
    if not text:
        return text, {}

    analyzer, anonymizer = get_pii_engines()
    if not analyzer or not anonymizer:
        return text, {} # Return original if tools are missing

    try:
        # We focus on the most critical PII for this demo
        entities = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "BR_CPF", "US_SSN"]
        
        # For the English demo, we use language="en" to ensure Spacy catches English names
        results = analyzer.analyze(text=text, entities=entities, language="en")
        
        if not results:
            return text, {}

        # Anonymize
        anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
        
        # Tally up what was redacted for the audit log
        redaction_counts = {}
        for res in results:
            ent = res.entity_type
            redaction_counts[ent] = redaction_counts.get(ent, 0) + 1

        return anonymized_result.text, redaction_counts

    except Exception as e:
        print(f"[PII] Anonymization error: {e}")
        return text, {}
