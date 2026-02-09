#!/usr/bin/env python3
"""
Parse questions from txt files in txts directory and write to CSV format.
"""

import csv
import re
from pathlib import Path


def extract_category_from_filename(filename):
    """Extract category from filename (e.g., 'Synonyms Test -DB.txt' -> 'Synonyms')."""
    # Remove extension
    name = filename.replace('.txt', '')
    # Remove common suffixes
    for suffix in [' Test -DB', ' Test - DB', ' Test', ' -DB', ' - DB']:
        name = name.replace(suffix, '')
    return name.strip()


def parse_questions_from_file(file_path):
    """Parse questions from a text file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    questions = []

    # Handle files with literal \n escape sequences (single line format)
    # Replace literal \n with actual newlines
    if '\\n' in content and content.count('\n') < 5:
        content = content.replace('\\n', '\n')

    # Remove BOM character if present at the start
    if content.startswith('\ufeff'):
        content = content[1:]

    # Ensure content ends with a newline so the last question is captured
    if not content.endswith('\n'):
        content += '\n'

    # Split by question number pattern (e.g., "1.", "2.", etc.) - look for it at line start
    # or after whitespace to handle various formats
    # Pattern: newline + optional spaces + digit + dot + space
    pattern = r'\n\s*(?=\d+\.\s)'
    parts = re.split(pattern, content)

    # Also handle case where content starts with a question number (no leading newline)
    if parts and parts[0].strip() and not re.match(r'^\d+\.', parts[0].strip()):
        # First part might be content before first question, skip it
        parts = parts[1:]

    for part in parts:
        part = part.strip()
        if not part:
            continue

        question = parse_single_question(part)
        if question:
            questions.append(question)

    return questions


def parse_single_question(content):
    """Parse a single question with its options, answer, and explanation."""

    # Remove the question number prefix (e.g., "1." or "1 ")
    content = re.sub(r'^^\d+\.\s*', '', content, count=1)
    content = re.sub(r'^\d+\.', '', content, count=1)

    lines = content.split('\n')

    question_lines = []
    options = []
    answer_index = 0
    explanation = ''

    i = 0
    # Get question text (everything before "Options:" or first option)
    # Preserve newlines in question text
    while i < len(lines):
        line = lines[i]
        stripped_line = line.strip()
        if stripped_line == 'Options:':
            i += 1
            break
        # Check if this looks like an option line (A., B., C., D.)
        if re.match(r'^[A-D]\.', stripped_line):
            break
        if stripped_line:  # Only add non-empty lines (preserve original with newline)
            question_lines.append(stripped_line)
        i += 1

    # Join question lines with newlines preserved
    question_text = '\n'.join(question_lines)

    # Extract options
    while i < len(lines):
        line = lines[i].strip()
        # Check if this is an option line
        opt_match = re.match(r'^([A-D])\.\s*(.+)', line)
        if opt_match:
            option_text = opt_match.group(2).strip()
            # Check if answer is included in option (e.g., "C. disturbed")
            # Remove the answer part if present
            option_text = re.sub(r'\s*[A-D]\.\s*$', '', option_text)
            options.append(option_text)
        elif line.startswith('Answer') or line.startswith('Explanation'):
            break
        i += 1

    # Find answer and explanation from remaining content
    remaining_content = '\n'.join(lines[i:])

    # Extract answer (looking for "Answer:" or "Answer ")
    # Handle formats: "Answer: A", "Answer: C. disturbed", "Answer : A"
    answer_match = re.search(r'Answer\s*:\s*([A-D])(?:\.\s*\S+)?', remaining_content, re.IGNORECASE)
    if answer_match:
        answer_letter = answer_match.group(1).upper()
        # Map letter to index (A=1, B=2, C=3, D=4)
        answer_index = ord(answer_letter) - ord('A') + 1
    else:
        # Try alternative format - answer might be in a different format
        answer_match = re.search(r'Answer\s*:\s*[A-D]\.\s*(\w+)', remaining_content, re.IGNORECASE)
        if answer_match:
            # Find which option matches this text
            answer_text = answer_match.group(1)
            for idx, opt in enumerate(options):
                if answer_text.lower() in opt.lower():
                    answer_index = idx + 1
                    break

    # Extract explanation
    explanation_match = re.search(r'Explanation\s*:\s*(.*)', remaining_content, re.DOTALL | re.IGNORECASE)
    if explanation_match:
        explanation = explanation_match.group(1).strip()
    else:
        # Try to find any text after Answer line for explanation
        lines_after_answer = remaining_content.split('\n')
        explanation_started = False
        explanation_lines = []
        for line in lines_after_answer:
            stripped_line = line.strip()
            if stripped_line.startswith('Explanation'):
                explanation_started = True
                # Extract text after "Explanation:"
                parts = stripped_line.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    explanation_lines.append(parts[1].strip())
                continue
            if explanation_started:
                # Stop if we hit another question (starts with number)
                if re.match(r'^\d+\.', stripped_line):
                    break
                if stripped_line:
                    explanation_lines.append(stripped_line)
        explanation = '\n'.join(explanation_lines).strip()

    # Clean up explanation (preserve newlines, just normalize multiple spaces)
    explanation = re.sub(r' +', ' ', explanation)

    return {
        'question_type': 'objective',
        'question': question_text.strip(),
        'option_count': len(options),
        'options': options,
        'answer': answer_index,
        'category': None,  # Will be set based on filename
        'difficulty': 'medium',
        'score': 5,
        'tags': None,  # Will be set based on category
        'explanation': explanation
    }


def write_to_csv(questions, output_path, category):
    """Write questions to CSV file in the specified format."""
    # CSV headers with 4 option columns and extra empty columns
    headers = [
        'Question Type', 'Question', 'Option count',
        'Options1', 'Options2', 'Options3', 'Options4',
        'Answer', 'Category', 'Difficulty', 'Score', 'Tags',
        'Answer Explanation', '', '', '', '', ''
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write headers
        writer.writerow(headers)

        # Write each question
        for q in questions:
            # Ensure we have exactly 4 options
            options = q['options'][:4]
            while len(options) < 4:
                options.append('')

            # Set category and tags based on filename
            q_category = q.get('category') or category
            q_tags = q.get('tags') or f'{category}'

            row = [
                q['question_type'],
                q['question'],
                q['option_count'],
                options[0] if len(options) > 0 else '',
                options[1] if len(options) > 1 else '',
                options[2] if len(options) > 2 else '',
                options[3] if len(options) > 3 else '',
                q['answer'],
                q_category,
                q['difficulty'],
                q['score'],
                q_tags,
                q['explanation'],
                '', '', '', '', ''
            ]
            writer.writerow(row)


def main():
    """Main function to process all txt files and create individual CSV files."""
    # Paths
    base_dir = Path('/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib')
    txts_dir = base_dir / 'txts'
    csv_dir = base_dir / 'csv-new'

    # Create csv directory if it doesn't exist
    csv_dir.mkdir(exist_ok=True)

    # Find all txt files
    txt_files = list(txts_dir.glob('*.txt'))

    print(f"Found {len(txt_files)} txt files:")

    # Process each txt file and create a corresponding CSV
    for txt_file in sorted(txt_files):
        print(f"\nProcessing: {txt_file.name}")

        # Extract category from filename
        category = extract_category_from_filename(txt_file.name)
        print(f"  Category: {category}")

        # Parse questions from this file
        questions = parse_questions_from_file(txt_file)
        print(f"  Found {len(questions)} questions")

        # Create output CSV filename (same as txt file but with .csv extension)
        csv_filename = txt_file.stem + '_questions.csv'
        output_csv = csv_dir / csv_filename

        # Write to individual CSV
        print(f"  Writing to: {output_csv}")
        write_to_csv(questions, output_csv, category)

    print(f"\nDone! Created {len(txt_files)} CSV files in {csv_dir}/")


if __name__ == '__main__':
    main()
