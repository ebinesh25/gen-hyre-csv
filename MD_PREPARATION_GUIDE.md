# MD Preparation Guide for CSV Conversion

This guide helps you prepare markdown files for successful conversion to CSV format using the AI converter.

## Critical Formatting Rules

### 1. Question Format

Each question should follow this structure:

```markdown
N. [Question Text]

Options:
 A. [Option 1 text]
 B. [Option 2 text]
 C. [Option 3 text]
 D. [Option 4 text]

Answer: [Letter] [Full answer text]

Explanation:
[Explanation text]
```

### 2. Answer Format Requirements

**CRITICAL:** The answer MUST match one of the options exactly.

- **Use letter prefix:** `Answer: A. [text]`
- **Or use full text:** `Answer: The full text of option A`

**DO NOT:**
- Use just the letter without option text: `Answer: A` (ambiguous)
- Use text that doesn't match any option

**Examples:**
```
✓ CORRECT: Answer: A. Economical
✓ CORRECT: Answer: Economical
✗ WRONG: Answer: A (without text)
```

### 3. Option Format Requirements

**All options MUST be listed under the "Options:" header:**

```markdown
Options:
 A. First option
 B. Second option
 C. Third option
 D. Fourth option
```

**Rules:**
- Each option must start with a letter (A, B, C, D, E) followed by a period and space
- All options must be listed
- Do not skip options

### 4. Special Cases

#### Questions with 5 Options

```markdown
Options:
 A. First option
 B. Second option
 C. Third option
 D. Fourth option
 E. Fifth option

Answer: [A-E] [text]
```

#### Questions with Referential Options

For questions where options refer to parts of the question:

```markdown
Question: Which part contains an error? (A) Part 1 (B) Part 2 (C) Part 3 (D) No error

Options:
 A. A
 B. B
 C. C
 D. D

Answer: B. B
```

#### Data Sufficiency Questions

```markdown
Statement I: [statement]
Statement II: [statement]

Options:
 A. Statement I alone is sufficient
 B. Statement II alone is sufficient
 C. Both statements together are sufficient
 D. Neither statement is sufficient

Answer: [correct option]
```

### 5. Common Errors to Avoid

| Error | Problem | Solution |
|-------|---------|----------|
| Answer doesn't match options | Answer text not in any option | Use exact option text |
| Missing option letter | Option doesn't start with A./B./C. | Add letter prefix |
| Inconsistent numbering | Question numbers skip or duplicate | Use sequential numbering |
| Missing options section | Options listed directly under question | Add "Options:" header |

### 6. Verification Checklist

Before converting, verify:
- [ ] All questions have numbered options (A, B, C, D...)
- [ ] All answers match an option exactly
- [ ] No missing options
- [ ] No duplicate question numbers
- [ ] Special characters (commas, quotes) are properly formatted
- [ ] Code blocks are properly delimited

### 7. Example Well-Formatted Question

```markdown
5. What is the value of 7⁻²?

Options:
 A. 0.0204
 B. 0.0142
 C. 0.0408
 D. None of the above

Answer: A. 0.0204

Explanation:
A negative power means reciprocal. 7⁻² = 1/(7²) = 1/49 = 0.0204.
```

### 8. Pre-Processing Script

If you have MD files with formatting issues, you can pre-process them:

```python
import re

def fix_md_format(md_file):
    """Common MD format fixes"""
    with open(md_file, 'r') as f:
        content = f.read()

    # Fix: Ensure "Options:" header before each question's options
    # Fix: Ensure answer includes letter prefix
    # Fix: Ensure consistent spacing

    with open(md_file, 'w') as f:
        f.write(content)
```

## Troubleshooting

### "Invalid answer" Error
- **Cause:** Answer text doesn't match any option
- **Fix:** Ensure answer text exactly matches one of the options

### "Invalid option count" Error
- **Cause:** Mismatch between declared option count and actual options
- **Fix:** Count options carefully, ensure all are listed

### "Column shift" Errors
- **Cause:** Unquoted commas in options, questions, or categories
- **Fix:** The AI converter handles quoting, but verify no malformed content

### "Answer exceeds option count" Error
- **Cause:** Answer number is greater than number of options
- **Fix:** Verify the answer is within valid range (1 to optionCount)
