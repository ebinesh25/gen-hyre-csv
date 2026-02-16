"""Answer validator preprocessor - validates answer-option matching."""
import re
from typing import Dict, Any, List, Optional, Tuple

from .base import BasePreprocessor
from ..models.results import PipelineContext
from ..core.exceptions import PreprocessError


class AnswerValidatorPreprocessor(BasePreprocessor):
    """Validates that answers match their corresponding options.

    Checks:
    1. Answer can be matched to an option (by letter, text, partial, or number)
    2. Warns on mismatches
    3. Provides suggestions for corrections

    Does NOT modify the content - only validates and logs warnings.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize answer validator preprocessor.

        Args:
            config: Configuration with options:
                - warn_on_mismatch: Log warnings for mismatches (default: true)
                - suggest_corrections: Suggest corrections for mismatches (default: true)
        """
        super().__init__(config)
        self.warn_on_mismatch = config.get("warn_on_mismatch", True)
        self.suggest_corrections = config.get("suggest_corrections", True)

    async def process(self, content: str, context: PipelineContext) -> str:
        """Validate answer-option matching.

        Args:
            content: Markdown content to validate
            context: Pipeline context

        Returns:
            Original content (validator doesn't modify)

        Raises:
            PreprocessError: If validation fails
        """
        try:
            self._log_debug("Starting answer validation")

            questions = self._parse_questions(content)

            validation_results = []
            for question in questions:
                result = self._validate_question(question)
                if result:
                    validation_results.append(result)

            # Store results in context
            context.metadata['answer_validation'] = validation_results

            # Log warnings
            mismatches = [r for r in validation_results if r['status'] == 'mismatch']
            if mismatches and self.warn_on_mismatch:
                self._log_warning(f"Found {len(mismatches)} answer mismatches")
                for mismatch in mismatches:
                    self._log_warning(
                        f"  Q: {mismatch['question'][:50]}... "
                        f"Answer: {mismatch['answer']} "
                        f"matched: {mismatch.get('matched_option', 'none')}"
                    )

            self._log_info(f"Validated {len(questions)} questions")
            return content

        except Exception as e:
            raise PreprocessError(f"Answer validation failed: {e}") from e

    def _parse_questions(self, content: str) -> List[Dict[str, Any]]:
        """Parse questions with their options and answers.

        Args:
            content: Markdown content

        Returns:
            List of question dictionaries
        """
        questions = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Detect question start (numbered line)
            if re.match(r'^\d+\. ', line) or re.match(r'^\d+\\\.', line):
                question_text = self._clean_question_number(line)

                # Extract options
                options = []
                i += 1
                while i < len(lines):
                    opt_line = lines[i].strip()
                    # Check if this is an option line
                    opt_match = re.match(r'^(\*\*)?([A-Z])[\.\)]\s*(.+)$', opt_line)
                    if opt_match:
                        letter = opt_match.group(2)
                        option_text = opt_match.group(3).strip()
                        options.append({'letter': letter, 'text': option_text})
                        i += 1
                    elif opt_line.startswith("**Answer") or opt_line.startswith("Answer:"):
                        break
                    else:
                        break

                # Extract answer
                answer = None
                answer_number = None
                while i < len(lines):
                    answer_line = lines[i].strip()
                    if answer_line.startswith("**Answer") or answer_line.startswith("Answer:"):
                        answer, answer_number = self._extract_answer(answer_line)
                        i += 1
                        break
                    i += 1

                if options:
                    questions.append({
                        'question': question_text,
                        'options': options,
                        'answer': answer,
                        'answer_number': answer_number,
                        'option_count': len(options)
                    })
                continue

            i += 1

        return questions

    def _clean_question_number(self, line: str) -> str:
        """Remove question number prefix from line.

        Args:
            line: Line with question number (e.g., "1. Question text")

        Returns:
            Question text without number
        """
        # Remove "1. " or "1\. " prefix
        result = re.sub(r'^\d+\\?\.\s+', '', line)
        return result

    def _extract_answer(self, line: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract answer from answer line.

        Args:
            line: Answer line (e.g., "**Answer: B. x = 24**")

        Returns:
            Tuple of (answer_text, answer_number)
        """
        # Remove bold markers and "Answer:" prefix
        cleaned = re.sub(r'\*\*', '', line)
        cleaned = re.sub(r'^Answer\s*:\s*', '', cleaned, flags=re.IGNORECASE)

        # Try to extract letter and text
        # Pattern: "B. x = 24" or "B" or "x = 24"
        letter_match = re.match(r'^([A-Z])\.\s*(.+)?$', cleaned)

        if letter_match:
            letter = letter_match.group(1)
            text = letter_match.group(2) or ''
            # Convert letter to number
            answer_number = ord(letter) - ord('A') + 1
            return text.strip() or letter, answer_number

        # Check if it's just a letter
        if len(cleaned) == 1 and cleaned.isalpha():
            answer_number = ord(cleaned.upper()) - ord('A') + 1
            return cleaned.upper(), answer_number

        # Check if it's just a number
        if cleaned.isdigit():
            return cleaned, int(cleaned)

        # It's text only
        return cleaned.strip(), None

    def _validate_question(self, question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single question's answer.

        Args:
            question: Question dictionary with options and answer

        Returns:
            Validation result dict, or None if validation passed
        """
        answer = question['answer']
        answer_number = question['answer_number']
        options = question['options']

        if not answer:
            return None

        # Priority 1: Direct number match
        if answer_number is not None:
            if 1 <= answer_number <= len(options):
                return None  # Valid

        # Priority 2: Letter match
        if answer and len(answer) == 1 and answer.isalpha():
            letter_num = ord(answer.upper()) - ord('A') + 1
            if 1 <= letter_num <= len(options):
                return None  # Valid

        # Priority 3: Text match
        if answer:
            for i, opt in enumerate(options):
                if opt['text'].lower() == answer.lower():
                    return None  # Valid

            # Priority 4: Partial match
            for i, opt in enumerate(options):
                if answer.lower() in opt['text'].lower() or opt['text'].lower() in answer.lower():
                    return {
                        'status': 'partial_match',
                        'question': question['question'],
                        'answer': answer,
                        'matched_option': opt['text'],
                        'match_position': i + 1
                    }

        # No match found
        return {
            'status': 'mismatch',
            'question': question['question'],
            'answer': answer,
            'answer_number': answer_number,
            'option_count': len(options),
            'options': [opt['text'] for opt in options]
        }
