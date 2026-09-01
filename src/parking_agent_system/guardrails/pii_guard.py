import logging
logger = logging.getLogger(__name__)

from transformers import pipeline
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_SENSITIVE_ENTITIES = ["CREDIT_CARD", "IBAN_CODE", "US_SSN", "MEDICAL_LICENSE"]

class GuardRails:
    def __init__(self):
        # Initialize PII Engines Presidio
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()

        # 2. Initialize Hugging Face Transformers Pipeline for prompt Injection detection
        logger.info("Loading guardrail model...")
        self._injection_classifier = pipeline(
            "text-classification",
            model="ProtectAI/deberta-v3-base-prompt-injection"
        )
        logger.info("Guardrail model loaded successfully.")

    def check_input(self, text: str) -> tuple[bool, str | None]:
        """
        Returns (is_safe, reason_if_needed)"""
        result = self._injection_classifier(text)[0]
        if result["label"] == "INJECTION" and result["score"] > 0.75:
            return False, "Your message contains restricted content or prompt injection attempts."
        return True, None

    def  scrub_input(self, text: str) -> str:
        """Remove PII from input before it reached the LLM"""
        return self.filter_pii(text) 

    def filter_pii(self, text: str, language: str = "en") -> str:
        """Anonymize sensitive data. Used for both input and output. """
        results = self._analyzer.analyze(
            text=text,
            language=language,
            entities=_SENSITIVE_ENTITIES,
        )

        if not results:
            return text
        return self._anonymizer.anonymize(
            text=text,
            analyzer_results=results
        ).text