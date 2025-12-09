# SchemaLink/core_logic/synthesis_module.py
import re
import json
from typing import List, Dict
import logging

from config.settings import LLM_MODEL_NAME
from config.prompts import (
    SYNTHESIS_PROMPT_TEMPLATE, 
    EMPTY_RESULT_PROMPT_TEMPLATE
)
from core_logic.llm_agent import MockLLMClient # Reusing the mock client for synthesis

synthesis_logger = logging.getLogger('SchemaLink.Synthesis')
synthesis_logger.setLevel(logging.INFO)


class PostQueryScrubber:
    """
    Implements the Post-Query PII Scrubbing Layer (LLD Requirement).
    Sanitizes the result set before passing it to the final LLM for synthesis.
    """
    def __init__(self):
        # Regex patterns for common PII types (emails, phone numbers, common names placeholder)
        self.pii_patterns = {
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "PHONE": r"(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{7})",
        }

    def _mask_value(self, value: str) -> str:
        """Applies masking to a single string value."""
        text = str(value)
        masked_text = text
        
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                synthesis_logger.warning(f"PII detected and masked: {pii_type}")
                # Simple replacement for demonstration
                masked_text = re.sub(pattern, f"[MASKED_{pii_type}]", masked_text)
        
        # Simple masking for names/addresses (often needed but harder via regex alone)
        if "address" in text.lower() or "name" in text.lower():
             return text.replace("John Doe", "[MASKED_NAME]")

        return masked_text

    def scrub_results(self, result_set: List[Dict]) -> List[Dict]:
        """Iterates through all rows and columns to mask PII."""
        scrubbed_results = []
        for row in result_set:
            new_row = {}
            for key, value in row.items():
                if isinstance(value, str):
                    new_row[key] = self._mask_value(value)
                else:
                    new_row[key] = value
            scrubbed_results.append(new_row)
            
        return scrubbed_results


class SynthesisLLM:
    """
    Handles the final LLM interpretation and applies the Grounding Constraint.
    """
    def __init__(self):
        self.llm_client = MockLLMClient(LLM_MODEL_NAME)
        self.scrubber = PostQueryScrubber()

    def synthesize_answer(self, user_question: str, result_set: List[Dict]) -> str:
        """
        Synthesizes the final answer using the LLM, applying all output guardrails.
        """
        # 1. PII Scrubbing (LLD Requirement)
        scrubbed_results = self.scrubber.scrub_results(result_set)
        
        # 2. Empty Result Handling (LLD Requirement)
        if not scrubbed_results:
            synthesis_logger.info("Handling empty result set.")
            prompt = EMPTY_RESULT_PROMPT_TEMPLATE.format(user_question=user_question)
        else:
            # 3. Result Interpretation & Grounding Constraint
            result_json = json.dumps(scrubbed_results, indent=2)
            
            # The prompt contains the 'Extremist Grounding Constraint'
            prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
                user_question=user_question,
                result_set_json=result_json
            )
            synthesis_logger.info("Synthesizing answer from scrubbed results.")

        # Simulate the final LLM generation
        # NOTE: The MockLLMClient here would typically need to be more sophisticated 
        # to generate a grounded NL answer based on the input JSON.
        
        # For demonstration, we simply wrap the input JSON for success case
        if scrubbed_results:
            # Placeholder for actual LLM synthesis
            return f"Answer successfully synthesized. The query results were:\n```json\n{result_json}\n```"
        else:
            # Placeholder for actual LLM empty result handling
            return f"**No Results Found:** {prompt.split('Example:')[1].strip()}"