import re

def parse_single_question(content):
    """Parse a single question with its options, answer, and solution."""

    # Extract question text - from the number up to "**Options:**" or first option
    # First remove the question number prefix (handles bold, whitespace, and escaped variations)
    content = re.sub(r'^\s*\*\*\d+\s*\.\s*\*\*\s*|^\s*\d+\s*(\\.)?\.\s*', '', content, count=1)

    # Split into lines
    lines = content.split('\n')

    # Extract question text (everything before "**Options:**" or first option)
    question_lines = []
    options = []

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
            option_text = opt_match_bold.group(2).strip()
            options.append(option_text)
            i += 1
        elif opt_match:
            option_raw = opt_match.group(2)
            option_parts = re.split(r'\s*\*\*\s*Answer|\s*\*\*$', option_raw, maxsplit=1, flags=re.IGNORECASE)
            option_text = option_parts[0].strip()
            options.append(option_text)
            if '**Answer' in line or re.search(r'\*\*\s*Answer', line, re.IGNORECASE):
                break
            i += 1
        elif line:
            if options and not line.startswith('**') and not re.search(r'Answer', line, re.IGNORECASE):
                options[-1] += ' ' + line
            i += 1
        else:
            i += 1

    return {
        'question': question_text.strip(),
        'options': options,
    }

def parse_questions_from_file(file_path):
    """Parse questions from a markdown file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    questions = []

    # Unescape any escaped dots in the content
    content = content.replace(r'\.', '.')

    # Split by question number pattern at line start
    pattern = r'(?m)^(?=\s*\*\*\d+\s*\.\s*\*\*\s*|\s*\d+\s*(?:\\.)?\.\s*)'
    parts = re.split(pattern, content)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        question = parse_single_question(part)
        if question and question['question']:
            questions.append(question)

    return questions

# Test with actual file
md_file = "/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib/temp/request_123885416056864/md/Averages Test - DB.md"
questions = parse_questions_from_file(md_file)

print(f"Number of questions found: {len(questions)}")
for i, q in enumerate(questions[:5]):
    print(f"\n--- Question {i+1} ---")
    print(f"Question: {q['question'][:80]}...")
    print(f"Options: {len(q['options'])}")
