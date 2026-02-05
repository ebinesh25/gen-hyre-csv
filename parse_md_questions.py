#!/usr/bin/env python3
"""
Parse questions from markdown files in md directory and write to CSV format.
"""

import csv
import re
from pathlib import Path
from base_img_s3 import upload_base64_image_to_s3

def parse_questions_from_file(file_path):
    """Parse questions from a markdown file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    questions = []

    # Unescape any escaped dots in the content (markdown escaping like "2\." -> "2.")
    # This is needed because some markdown files escape question numbers
    content = content.replace(r'\.', '.')

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


def remove_markdown_formatting(text):
    """Remove markdown formatting from text."""
    # Remove bold markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove italic markers
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # # Remove image tags ![alt](url)
    # text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    # Remove links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text


def process_base64_images(text):
    """
    Find all base64 images in text, upload them to S3,
    and replace with signed URIs.
    """
    # Pattern to match markdown images with base64 data URLs
    # Matches: ![alt](data:image/...;base64,...)
    pattern = r'!\[([^\]]*)\]\((data:image/[^)]+)\)'

    def replace_base64_with_s3(match):
        """Replace a single base64 image with S3 URL."""
        alt_text = match.group(1)
        base64_url = match.group(2)

        try:
            # Upload to S3 and get signed URL
            signed_url = upload_base64_image_to_s3(base64_url)
            return f'![{alt_text}]({signed_url})'
        except Exception as e:
            # If upload fails, keep original or remove image
            print(f"Warning: Failed to upload image to S3: {e}")
            # Return empty string to remove failed images
            return ''

    # Replace all base64 images with S3 URLs
    return re.sub(pattern, replace_base64_with_s3, text)
    # return re.sub(pattern, "IMAGE_URL", text)


def parse_single_question(content):
    """Parse a single question with its options, answer, and solution."""

    # Extract question text - from the number up to "**Options:**" or first option
    # First remove the question number prefix
    content = re.sub(r'^\d+\.\s*', '', content, count=1)

    # Split into lines
    lines = content.split('\n')

    # Extract question text (everything before "**Options:**" or first option)
    question_lines = []
    options = []
    answer_index = 0
    explanation = ''

    i = 0
    # Get question text
    while i < len(lines):
        line = lines[i].strip()
        # Check for "**Options:**" header
        if re.match(r'^\*\*Options:\*\*$', line) or re.match(r'^\*\*\s*Options\s*:\*\*$', line, re.IGNORECASE):
            i += 1
            break
        # Check if this looks like an option line
        if re.match(r'^[A-D]\.', line) or re.match(r'^\*\*[A-D]\.', line):
            break
        if line:  # Only add non-empty lines
            question_lines.append(line)
        i += 1

    question_text = ' '.join(question_lines)
    # Process base64 images in question text
    question_text = process_base64_images(question_text)
    # Remove markdown formatting from question
    question_text = remove_markdown_formatting(question_text)

    # Extract options
    while i < len(lines):
        line = lines[i].strip()

        # Check if line starts with **Answer or **Solution
        if re.search(r'^\*\*\s*Answer', line, re.IGNORECASE) or re.search(r'^\*\*\s*Solution', line, re.IGNORECASE):
            break

        # Check for bold option markers like **A.**
        opt_match_bold = re.match(r'^\*\*([A-D])\.\s*\*\*(.+)', line)
        # Check for regular option markers like A.
        opt_match = re.match(r'^([A-D])\.\s*(.+)', line)

        if opt_match_bold:
            option_text = process_base64_images(opt_match_bold.group(2))
            option_text = remove_markdown_formatting(option_text).strip()
            options.append(option_text)
            i += 1
        elif opt_match:
            # Extract option text, but stop at ** if present (for combined option/answer lines)
            option_raw = opt_match.group(2)
            # Stop at **Answer or ** if present
            option_parts = re.split(r'\s*\*\*\s*Answer|\s*\*\*$', option_raw, maxsplit=1, flags=re.IGNORECASE)
            option_text = process_base64_images(option_parts[0])
            option_text = remove_markdown_formatting(option_text).strip()
            options.append(option_text)
            # Check if this line also contains the answer
            if '**Answer' in line or re.search(r'\*\*\s*Answer', line, re.IGNORECASE):
                # Don't increment i, let the answer extraction handle this line
                break
            i += 1
        elif line:
            # Handle continuation lines - only if it's not starting with ** and not an answer line
            if options and not line.startswith('**') and not re.search(r'Answer', line, re.IGNORECASE):
                cleaned_line = process_base64_images(line)
                cleaned_line = remove_markdown_formatting(cleaned_line)
                options[-1] += ' ' + cleaned_line
            i += 1
        else:
            i += 1  # Empty line

    # Find answer and solution
    remaining_content = '\n'.join(lines[i:])

    # Split remaining content at Solution marker to avoid picking up answers from later questions
    # that might be embedded in the solution text
    solution_split = re.split(r'\*\*\s*Solution\s*:', remaining_content, maxsplit=1, flags=re.IGNORECASE)
    answer_section = solution_split[0] if solution_split else remaining_content

    # Extract answer from answer_section only (before Solution)
    # Pattern matches "**Answer: A.**" or "**Answer : A.**" or "**  Answer: A. option text**"
    answer_match = re.search(r'\*\*\s*Answer\s*:\s*\*?\s*([A-D])\.', answer_section, re.IGNORECASE)
    if not answer_match:
        # Try with single asterisk
        answer_match = re.search(r'\*\s*Answer\s*:\s*([A-D])\.', answer_section, re.IGNORECASE)
    if not answer_match:
        # Try without bold markers
        answer_match = re.search(r'Answer\s*:\s*([A-D])\.', answer_section, re.IGNORECASE)

    if answer_match:
        answer_letter = answer_match.group(1).upper()
        # Map letter to index (A=0, B=1, C=2, D=3)
        answer_index = ord(answer_letter) - ord('A')

    # Extract solution/explanation
    # Look for "**Solution:**" or "**Solution**" with optional colon
    solution_match = re.search(r'\*\*\s*Solution\s*:?\s*\*?\s*(.*)', remaining_content, re.DOTALL | re.IGNORECASE)
    if solution_match:
        explanation = solution_match.group(1).strip()
    else:
        # Try without bold markers
        solution_match = re.search(r'Solution\s*:?\s*(.*)', remaining_content, re.DOTALL | re.IGNORECASE)
        if solution_match:
            explanation = solution_match.group(1).strip()
        else:
            # Try to find any text after Answer
            answer_pos = remaining_content.lower().find('answer')
            if answer_pos != -1:
                explanation = remaining_content[answer_pos:].strip()

    # Process base64 images: upload to S3 and replace with signed URIs
    explanation = process_base64_images(explanation)

    # Remove markdown formatting and clean up explanation
    explanation = remove_markdown_formatting(explanation)
    # Clean up extra whitespace and newlines
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
    """Main function to process all md files and create individual CSV files."""
    # Paths
    base_dir = Path('/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib')
    md_dir = base_dir / 'md'
    csv_dir = base_dir / 'csv'

    # Create csv directory if it doesn't exist
    csv_dir.mkdir(exist_ok=True)

    # Find all md files
    md_files = list(md_dir.glob('*.md'))

    print(f"Found {len(md_files)} md files:")

    # Process each md file and create a corresponding CSV
    for md_file in md_files:
        print(f"\nProcessing: {md_file.name}")

        # Parse questions from this file
        questions = parse_questions_from_file(md_file)
        print(f"  Found {len(questions)} questions")

        # Create output CSV filename (same as md file but with .csv extension)
        csv_filename = md_file.stem + '.csv'
        output_csv = csv_dir / csv_filename

        # Write to individual CSV
        print(f"  Writing to: {output_csv}")
        write_to_csv(questions, output_csv)

    print(f"\nDone! Created {len(md_files)} CSV files in {csv_dir}/")


if __name__ == '__main__':
    main()
