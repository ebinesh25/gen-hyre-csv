#!/usr/bin/env python3
"""
Parse questions from txt files in docs directory and write to CSV format.
"""

import csv
import re
from pathlib import Path


def parse_questions_from_file(file_path):
    """Parse questions from a text file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    questions = []

    # Split by question number pattern at line start (e.g., "1.", "2.", etc.)
    # Use positive lookbehind to keep the question number with content
    pattern = r'(?m)^(?=\d+\.)'
    parts = re.split(pattern, content)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        question = parse_single_question(part)
        if question:
            questions.append(question)

    return questions


def parse_single_question(content):
    """Parse a single question with its options, answer, and solution."""

    # Extract question text - from the number up to "Options:" or first option
    # First remove the question number prefix
    content = re.sub(r'^\d+\.\s*', '', content, count=1)

    # Split into lines
    lines = content.split('\n')

    # Extract question text (everything before "Options:" or first option)
    question_lines = []
    options = []
    answer_index = 0
    explanation = ''

    i = 0
    # Get question text
    while i < len(lines):
        line = lines[i].strip()
        if line == 'Options:':
            i += 1
            break
        # Check if this looks like an option line
        if re.match(r'^[A-D]\.', line):
            break
        if line:  # Only add non-empty lines
            question_lines.append(line)
        i += 1

    question_text = ' '.join(question_lines)

    # Extract options
    while i < len(lines):
        line = lines[i].strip()
        # Check if this is an option line
        opt_match = re.match(r'^([A-D])\.\s*(.+)', line)
        if opt_match:
            options.append(opt_match.group(2).strip())
        elif line and not line.startswith('Answer') and not line.startswith('Solution'):
            # Continuation of previous option or other content
            if options and not line.startswith('Answer'):
                options[-1] += ' ' + line
        elif line.startswith('Answer') or line.startswith('Solution'):
            break
        i += 1

    # Find answer and solution
    remaining_content = '\n'.join(lines[i:])

    # Extract answer (looking for "Answer:" or "Answer :")
    answer_match = re.search(r'Answer\s*:\s*([A-D])', remaining_content, re.IGNORECASE)
    if answer_match:
        answer_letter = answer_match.group(1).upper()
        # Map letter to index (A=0, B=1, C=2, D=3)
        answer_index = ord(answer_letter) - ord('A')

    # Extract solution/explanation
    solution_match = re.search(r'Solution\s*:\s*(.*)', remaining_content, re.DOTALL | re.IGNORECASE)
    if solution_match:
        explanation = solution_match.group(1).strip()
    else:
        # Try to find any text after Answer
        answer_pos = remaining_content.lower().find('answer')
        if answer_pos != -1:
            explanation = remaining_content[answer_pos:].strip()

    # Clean up explanation (remove extra whitespace)
    explanation = ' '.join(explanation.split())

    return {
        'question_type': 'objective',
        'question': question_text.strip(),
        'option_count': len(options),
        'options': options,
        'answer': answer_index + 1,
        'category': 'Aptitude',
        'difficulty': 'medium',
        'score': 5,
        'tags': 'Aptitude,Numbers',
        'explanation': explanation
    }


def write_to_csv(questions, output_path):
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

            row = [
                q['question_type'],
                q['question'],
                q['option_count'],
                options[0] if len(options) > 0 else '',
                options[1] if len(options) > 1 else '',
                options[2] if len(options) > 2 else '',
                options[3] if len(options) > 3 else '',
                q['answer'],
                q['category'],
                q['difficulty'],
                q['score'],
                q['tags'],
                q['explanation'],
                '', '', '', '', ''
            ]
            writer.writerow(row)


def main():
    """Main function to process all txt files and create individual CSV files."""
    # Paths
    base_dir = Path('/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib')
    docs_dir = base_dir / 'docs'
    csv_dir = base_dir / 'csv'

    # Create csv directory if it doesn't exist
    csv_dir.mkdir(exist_ok=True)

    # Find all txt files
    txt_files = list(docs_dir.glob('*.txt'))

    print(f"Found {len(txt_files)} txt files:")

    # Process each txt file and create a corresponding CSV
    for txt_file in txt_files:
        print(f"\nProcessing: {txt_file.name}")

        # Parse questions from this file
        questions = parse_questions_from_file(txt_file)
        print(f"  Found {len(questions)} questions")

        # Create output CSV filename (same as txt file but with .csv extension)
        csv_filename = txt_file.stem + '.csv'
        output_csv = csv_dir / csv_filename

        # Write to individual CSV
        print(f"  Writing to: {output_csv}")
        write_to_csv(questions, output_csv)

    print(f"\nDone! Created {len(txt_files)} CSV files in {csv_dir}/")


if __name__ == '__main__':
    main()
