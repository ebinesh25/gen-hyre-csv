import os
import sys
import time
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------

# Select AI provider: "GROQ" or "CLAUDE_CLI"
AI_PROVIDER = os.getenv("AI_PROVIDER", "GROQ")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Input/Output directories
INPUT_MD_DIR = sys.argv[1] if len(sys.argv) > 1 else "md-aptitude"
OUTPUT_CSV_DIR = "csv-ai"

# Rate limit retry settings
MAX_RETRIES = 5
BASE_RETRY_DELAY = 60  # seconds

# Initialize Groq client if using Groq
if AI_PROVIDER == "GROQ":
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------
# 2. SAMPLE DATA (Few-Shot Examples)
# ---------------------------------------------------------

SAMPLE_MD = """
1.A car travels 700 miles in seven hours, each hour covering 20 miles more than the previous hour. How many miles did it travel in the first hour?  

**Options:  
**A.10

B.25

C.20

D.40  

**Answer : D.40**

**Solution:**

Let x be the number of miles the car traveled in the first hour.

Then, in the second hour, it covered x + 25 miles.

In the third hour, it covered x + 50 miles. And so on.

We can set up the following equation based on the given information:

x + (x + 20) + (x + 40) + (x + 60) + (x + 80) + (x + 100) + (x + 120) = 700

Simplifying this equation, we get:

7x + 420 = 700

7x = 280

x = 40

6\. The sequence 12, 18, x, y, 36 is an arithmetic progression (AP). Find the values of x and y.

**Options:  
**A. x = 22, y = 28

B. x = 24, y = 30

C. x = 26, y = 32

D. x = 20, y = 26  

**Answer: B. x = 24, y = 30  
**

**Solution:**

Since the sequence is an arithmetic progression, the common difference (d) between consecutive terms is constant.

First, let's find the common difference using the first two terms:

d = 18 - 12 = 6

Now we can find x and y by adding the common difference to each previous term:

x = 18 + 6 = 24

y = 24 + 6 = 30

Let's verify our answer:

First term: 12

Second term: 12 + 6 = 18

Third term: 18 + 6 = 24

Fourth term: 24 + 6 = 30

Fifth term: 30 + 6 = 36

Therefore, x = 24 and y = 30.

10.What is the sum of the first 15 even natural numbers?

**Options:  
**A. 190

B.240

C. 210

D. 196  

**Answer: B.240  
**

**Solution:**

The sum of the first n even natural numbers is given by the formula n(n+1).

Since we want the sum of the first 15 even natural numbers,

we can substitute n=15 into the formula to get: 15(15+1) = 240.

Therefore, the sum of the first 15 even natural numbers is 240.

11.Does the following sentence have an S-V error? She and her friends was waiting outside.

Options:
 Yes
 No

Answer: Yes

Explanation: The subject "She and her friends" is a compound subject and is plural, so it requires the plural verb "were".

12.Rearrange the following five sentences in proper sequence:

1. Realising his mistake, Aman apologised.
2. Without checking facts, Aman believed the rumour.
3. Aman heard a rumour during lunch.
4. His friend explained the truth.
5. He avoided speaking to his friend.

Which sentence should come second?

Options:
 1
 2
 3
 4
 5

Answer: 2

Explanation: After hearing the rumour, Aman believed it and got angry.

NOTE: This question has 5 options but answer is 2 (within first 4), so we keep first 4 options.

13.A modern education system should not depend on outdated methods nor rely on obsolete technology.

Options:
 should not depend
 should neither depend
 should either depend
 No correction required

Answer: should neither depend

Explanation: The correlative conjunction "neither" must be paired with "nor".

14.Fill in the blank with the appropriate determiner:

_____ of the students who participated have been selected.

Options:
 A. Few
 B. Some
 C. Every
 D. No

Answer: B

Explanation: "Some" correctly indicates that not all, but a certain number have been selected.

NOTE: Original had 5 options (A-E), but option E was dropped. Answer B is within A-D.

15.Choose the best alternative for the underlined phrase:

The company decided to take the supplier to the court over the breach of contract.

to the court
 in the court
 to court
 into the court

Answer: to court

Explanation: The correct idiomatic expression is "to court".
"""

SAMPLE_CSV = """Question Type,Question,Option count,Options1,Options2,Options3,Options4,Answer,Category,Difficulty,Score,Tags,Answer Explanation,,,,,
objective,"A car travels 700 miles in seven hours, each hour covering 20 miles more than the previous hour. How many miles did it travel in the first hour?",4,10,25,20,40,4,Aptitude,medium,5,"Aptitude,Numbers","* Let x be the number of miles the car traveled in the first hour. Then, in the second hour, it covered x + 25 miles. In the third hour, it covered x + 50 miles. And so on. We can set up the following equation based on the given information: x + (x + 20) + (x + 40) + (x + 60) + (x + 80) + (x + 100) + (x + 120) = 700 Simplifying this equation, we get: 7x + 420 = 700 7x = 280 x = 40",,,,,
objective,"A, B, C and D are four consecutive even numbers respectively and their average is 65. What is the product of A and D?",4,3968,4092,4216,4352,3,Aptitude,medium,5,"Aptitude,Numbers","* Let x, x + 2, x + 4 and x + 6 represent numbers A, B, C and D respectively. Then, x+(x+2)+(x+4)+(x+6)4=65 4x+12=260 4x=248 x=62 So, A = 62, B = 64, C = 66, D = 68 ∴ A × D = 62 × 68 = 4216",,,,,
objective,"The average of 5 consecutive multiples of 3 M, N, O, P, and Q is 54. What is the product of M and Q?",4,2916,2880,3136,3249,2,Aptitude,medium,5,"Aptitude,Numbers","* Since M, N, O, P, and Q are five consecutive multiples of 3, and we know that the average of numbers at equal intervals is the middle number. Here the average is 54. So the numbers are 48, 51, 54, 57, 60. Finally, the product of M and Q is 48 \* 60 = 2880.",,,,,
objective,The sum of 3 consecutive multiples of 5 is 60 more than the average of these numbers. What will be the highest of these numbers?,4,15,35,25,30,2,Aptitude,medium,5,"Aptitude,Numbers","* Let's call the smallest of the 3 consecutive multiples of 5 ""x"". Then we know that the next two numbers are x + 5 and x + 10. The sum of these numbers is x + (x + 5) + (x + 10) = 3x + 15. The average of these numbers is (x + (x + 5) + (x + 10)) / 3 = (3x + 15) / 3 = x + 5. So the sum of the numbers is 60 more than the average: 3x + 15 = (x + 5) + 60 2x + 15 = 65 2x = 50 x = 25 Therefore, the highest of the 3 numbers is x + 10 = 25 + 10 = 35.",,,,,
objective,Find the value of 1000 + 1010 + 1020 + … + 1300.,4,91000,93500,35650,98500,3,Aptitude,medium,5,"Aptitude,Numbers","* The sequence of numbers is 1000, 1010, 1020, …, 1300, and the number of terms in the sequence is (1300 - 1000) / 10 + 1 = 31. Summation of the series in AP = Average x Number of elements Here, the average of the arithmetic sequence is (first number + last number) / 2(1000 + 1300) / 2 = 1150 Total = 31 \* 1150 = 35650.",,,,,
objective,"The sequence 12, 18, x, y, 36 is an arithmetic progression (AP). Find the values of x and y.",4,"x = 22, y = 28","x = 24, y = 30","x = 26, y = 32","x = 20, y = 26",2,Aptitude,medium,5,"Aptitude,Numbers","* Since the sequence is an arithmetic progression, the common difference (d) between consecutive terms is constant. First, let's find the common difference using the first two terms: d = 18 - 12 = 6 Now we can find x and y by adding the common difference to each previous term: x = 18 + 6 = 24 y = 24 + 6 = 30 Let's verify our answer: First term: 12 Second term: 12 + 6 = 18 Third term: 18 + 6 = 24 Fourth term: 24 + 6 = 30 Fifth term: 30 + 6 = 36 Therefore, x = 24 and y = 30.",,,,,
objective,"Find the 9th term of the arithmetic progression 2, 5, 8, …",4,48,26,32,36,2,Aptitude,medium,5,"Aptitude,Numbers","* The common difference in this AP is 3. Therefore, a9 = a1 + (n-1)d \= 2 + (9-1)3 \= 26 Hence, the 9th term of the given AP is 26.",,,,,
objective,"If the first term of an AP is 12, the common difference is 2, and the last term is 22, find the total number of terms in the AP.",4,8,6,12,16,2,Aptitude,medium,5,"Aptitude,Numbers","* Using the same method as above, we get: 22 = 12 + (n - 1)2 10 = 2(n - 1) n - 1 = 5 n = 6 Therefore, there are 6 terms in the AP.",,,,,
objective,"Which term of the arithmetic progression (AP) 12, 18, 24, ... is 150?",4,19th term,20th term,21st term,23rd term,4,Aptitude,medium,5,"Aptitude,Numbers","* The common difference of the AP 12, 18, 24, ... is d = 18 - 12 = 6. To find which term is 150, we use the formula for the nth term of an arithmetic sequence: aₙ = a₁ + (n - 1)d Where: aₙ = 150 (the term we're looking for) a₁ = 12 (the first term) d = 6 (the common difference) n = term number (what we need to find) Substituting the values: 150 = 12 + (n - 1)(6) 150 = 12 + 6n - 6 150 = 6 + 6n 150 - 6 = 6n 144 = 6n n = 24 Wait, let me recalculate: 150 - 12 = (n - 1)(6) 138 = (n - 1)(6) 138 ÷ 6 = n - 1 23 = n - 1 n = 24 Actually: 138 = 6(n - 1) 23 = n - 1 n = 24 Let me verify: a₂₄ = 12 + (24-1)(6) = 12 + 138 = 150 Therefore, the 24th term of the AP is 150.",,,,,
objective,What is the sum of the first 15 even natural numbers?,4,190,240,210,196,2,Aptitude,medium,5,"Aptitude,Numbers","* The sum of the first n even natural numbers is given by the formula n(n+1). Since we want the sum of the first 15 even natural numbers, we can substitute n=15 into the formula to get: 15(15+1) = 240. Therefore, the sum of the first 15 even natural numbers is 240.",,,,,
objective,"Does the following sentence have an S-V error? She and her friends was waiting outside.",2,Yes,No,,,1,Aptitude,medium,5,"Aptitude,Grammar","* The subject ""She and her friends"" is a compound subject and is plural, so it requires the plural verb ""were"".",,,,,,
objective,"Rearrange the following five sentences in proper sequence: 1. Realising his mistake, Aman apologised. 2. Without checking facts, Aman believed the rumour. 3. Aman heard a rumour during lunch. 4. His friend explained the truth. 5. He avoided speaking to his friend. Which sentence should come second?",4,1,2,3,4,2,Aptitude,medium,5,"Aptitude,Paragraph Formation","* After hearing the rumour, Aman believed it and got angry. Note: Original had 5 options but answer is 2 (within first 4), so we kept first 4 options with option count = 4.",,,,,,
objective,"A modern education system should not depend on outdated methods nor rely on obsolete technology.",4,"should not depend","should neither depend","should either depend","No correction required",2,Aptitude,medium,5,"Aptitude,Sentence Improvement","* The correlative conjunction ""neither"" must be paired with ""nor"". Answer ""should neither depend"" matches option 2.",,,,,,
objective,"Fill in the blank with the appropriate determiner: _____ of the students who participated have been selected.",4,"A. Few","B. Some","C. Every","D. No",2,Aptitude,medium,5,"Aptitude,Determiners","* ""Some"" correctly indicates that not all, but a certain number have been selected. Note: Original had 5 options (A-E), but option E was dropped since answer B is within first 4.",,,,,,
objective,"Choose the best alternative for the underlined phrase: The company decided to take the supplier to the court over the breach of contract.",4,"to the court","in the court","to court","into the court",3,Aptitude,medium,5,"Aptitude,Idioms","* The correct idiomatic expression is ""to court"". Answer ""to court"" matches option 3.",,,,,,
"""

# ---------------------------------------------------------
# 3. RATE LIMIT PARSING
# ---------------------------------------------------------

def extract_retry_after(error_msg: str) -> int:
    """Extract retry time in seconds from rate limit error message."""
    # Look for patterns like "Please try again in 2h23m30.624s"
    match = re.search(r'Please try again in ([\dhms\.]+)', error_msg)
    if match:
        time_str = match.group(1)
        total_seconds = 0

        # Parse hours, minutes, seconds
        h_match = re.search(r'(\d+)h', time_str)
        m_match = re.search(r'(\d+)m', time_str)
        s_match = re.search(r'([\d\.]+)s', time_str)

        if h_match:
            total_seconds += int(h_match.group(1)) * 3600
        if m_match:
            total_seconds += int(m_match.group(1)) * 60
        if s_match:
            total_seconds += float(s_match.group(1))

        # Add 10% buffer and round up
        return int(total_seconds * 1.1) + 10

    return BASE_RETRY_DELAY


# ---------------------------------------------------------
# 4. PROCESSING FUNCTIONS
# ---------------------------------------------------------

def get_system_prompt() -> str:
    """Get the system prompt for conversion."""
    return """You are an intelligent data extractor. Convert Markdown text into CSV format.

## CRITICAL RULES - MUST FOLLOW EXACTLY

### CSV FORMAT REQUIREMENTS
1. Output ONLY valid CSV. No markdown code blocks (```csv). No introductory text.
2. Start IMMEDIATELY with header: Question Type,Question,Option count,Options1,Options2,Options3,Options4,Answer,Category,Difficulty,Score,Tags,Answer Explanation,,,,,
3. End IMMEDIATELY after the last question row. NO summaries, NO "here's the CSV", NO concluding remarks, NO "I've processed" messages.
4. 'Question Type' = "objective" (always)
5. 'Option count' = The ACTUAL number of options (2, 3, or 4) - NOT always 4!
6. Default values: Category="Aptitude", Difficulty="medium", Score="5", Tags="Aptitude,Numbers"

### CRITICAL CSV QUOTING RULES (MOST COMMON SOURCE OF ERRORS)

**RULE: ANY field containing commas MUST be enclosed in double quotes**

**MANDATORY QUOTING - ALWAYS QUOTE THESE FIELDS:**
1. **Options** - ALWAYS quote ALL options, regardless of whether they contain commas
2. **Question** - ALWAYS quote to be safe (questions often have commas)
3. **Tags** - ALWAYS quote (they always contain commas like "Aptitude,Numbers")
4. **Answer Explanation** - ALWAYS quote (explanations often have commas)
5. **Category** - ALWAYS quote (may contain commas like "Logical Reasoning,Directions")

**ZERO EXCEPTIONS POLICY:**
- Even if an option has no commas, QUOTE IT anyway for consistency
- This prevents ALL column shift issues

Examples of CORRECT quoting:
- `"Economical"` (quoted, even without commas)
- `"BOTH statements TOGETHER are sufficient, but NEITHER..."` (quoted, has commas)
- `"Select the correct option, and explain why."` (quoted, has commas)
- `"Logical Reasoning,Directions"` (quoted, has comma - CRITICAL!)
- objective,"Question text with comma...",2,"Yes","No",1,"Category,Subcategory",medium,5,"Tag1,Tag2","Explanation text..."

Examples of INCORRECT (will cause column shifts):
- Economical (not quoted - risky)
- BOTH statements TOGETHER (not quoted with comma - BROKEN!)
- Logical Reasoning,Directions (not quoted - BROKEN!)

Examples of CORRECT quoting:
- Question: `objective,"Does the following sentence have an error? Yes or no.",2,Yes,No,...`
- Tags: `objective,Question text...,2,Yes,No,,,1,Grammar,medium,5,"Grammar,Subject-Verb Agreement","Explanation"`
- Answer Explanation: `...,"Grammar,Pronoun Agreement","* The ""subject"" is singular, so use ""was""."`

Examples of INCORRECT (missing quotes):
- `objective,Does the following sentence have an error? Yes or no.,2,Yes,No,,,1,Grammar,medium,5,Grammar,Subject-Verb Agreement,Explanation`
  ^^^ WRONG - Question, Tags, and Explanation should be quoted!

**Remember: In CSV, anything with commas must be in quotes!**

### CRITICAL UNDERSTANDING OF CSV STRUCTURE

The CSV now supports DYNAMIC option counts based on the maximum options found in the data.
- The header will have Options1, Options2, Options3, Options4, Options5, Options6, etc. up to the maximum
- 'Option count' should reflect the ACTUAL number of options for each question
- All options up to 'Option count' MUST be non-empty
- Questions with different option counts can coexist in the same CSV

Example 2-option question:
- Question,2,Yes,No,,,,1,... (optionCount=2, Options3-6 are empty strings)

Example 4-option question:
- Question,4,A,B,C,D,,,3,... (optionCount=4, Options5-6 are empty strings)

Example 5-option question:
- Question,5,A,B,C,D,E,,,3,... (optionCount=5, Options6 is empty string)

Example 6-option question:
- Question,6,1,2,3,4,5,6,,,4,... (optionCount=6, all options filled)

### OPTION HANDLING

**Scenario 1: 2 options (Yes/No questions)**
- Set Option count = 2
- Options1="Yes", Options2="No"
- Options3+ are empty strings (padding columns)
- Answer: 1 for Yes, 2 for No

**Scenario 2: 3 options**
- Set Option count = 3
- Options1, Options2, Options3 filled with actual options
- Options4+ are empty strings

**Scenario 3: 4 options**
- Set Option count = 4
- Options1-4 filled with actual options
- Options5+ are empty strings

**Scenario 4: 5 options (A, B, C, D, E)**
- Set Option count = 5
- Options1-5 filled with all 5 options
- Options6+ are empty strings
- Answer can be 1-5

**Scenario 5: 6 options (1, 2, 3, 4, 5, 6)**
- Set Option count = 6
- Options1-6 filled with all 6 options
- Answer can be 1-6

### ANSWER HANDLING (CRITICAL)

**Type 1: Letter-based answers (A, B, C, D, E)**
- Map to position: A=1, B=2, C=3, D=4, E=5
- Example: Answer: "B" → Answer column: 2
- Example: Answer: "E" → Answer column: 5

**Type 2: Number-based answers (1, 2, 3, 4, 5, 6)**
- Use the number directly as the answer
- Example: Answer: 3 → Answer column: 3
- Example: Answer: 5 → Answer column: 5

**Type 3: Text-based answers (full text match)**
- Find which option matches the answer text
- Use the position number (1-6) of that option
- Example: Answer is "should neither depend" and option 2 is "should neither depend" → Answer column: 2
- Example: Answer is "history, geography and politics" and option 1 is "history, geography and politics" → Answer column: 1
- If no exact match, find closest partial match

**Type 4: Yes/No answers**
- Option count = 2
- Options1="Yes", Options2="No"
- Answer: 1 for Yes, 2 for No

### SPECIAL QUESTION TYPES

**Paragraph Formation Questions:**
- May have 5 or 6 options
- Include all options, set optionCount accordingly (5 or 6)
- No need to skip any questions

**Sentence Correction/Improvement Questions:**
- Usually have 2-4 options
- Extract options as listed
- Match text-based answer to option content

**Reading Comprehension Questions:**
- May have 5 options (A through E)
- Include all 5 options, set optionCount=5
- Answer can be 1-5

### EXTRACTION GUIDELINES

1. **CRITICAL: Remove ALL option letter prefixes (A., B., C., etc.)**
   - ALWAYS extract the option text WITHOUT the letter prefix and period
   - If option is "A. aloof" → Extract as "aloof" (NOT "A. aloof")
   - If option is "B. witty" → Extract as "witty" (NOT "B. witty")
   - If option is "A. EACH statement ALONE is sufficient." → Extract as "EACH statement ALONE is sufficient."
   - If option is "E. Statement I ALONE is sufficient..." → Extract as "Statement I ALONE is sufficient..."
   - **ZERO TOLERANCE:** Any option that starts with "A.", "B., "C.", "D.", or "E." is WRONG
   - The prefix MUST be stripped completely

2. **Extract options EXACTLY as written** - preserve capitalization and spelling
   - After removing the letter prefix, keep the rest exactly as-is
   - DO NOT drop leading letters or change spelling of the actual option text

3. Extract ALL options listed under "Options:" header
4. Handle multiline option formats - combine lines that belong to same option
5. Ignore "Correct sentence:" or similar labels in answer key - focus on the option content
6. For answer explanation, extract the explanation text and replace newlines with " n "
7. Process EVERY question in the input - do not skip any EXCEPT when answer exceeds available options

### VALIDATION CHECKS BEFORE OUTPUTING
- Determine MAXIMUM option count across all questions (2, 3, 4, 5, or 6)
- CSV header will have Options1 through Options[maxOptionCount]
- Each row must have: Question Type, Question, Option count, Options1-[maxOptionCount], Answer, Category, Difficulty, Score, Tags, Answer Explanation
- Option count must match actual number of non-empty options for that question
- All options 1 through optionCount must be non-empty
- Options beyond optionCount are empty strings (padding)
- Answer must be a number between 1 and optionCount
- If answer exceeds optionCount, skip that question
- **CRITICAL:** Tags must ALWAYS be quoted because they contain commas: `"Grammar,Subject-Verb Agreement"`
- **CRITICAL:** Quote any field that contains commas (Question, Options, Answer Explanation)

### FINAL VALIDATION CHECK BEFORE OUTPUT
After generating each CSV row, verify:
1. Do ANY options start with "A.", "B.", "C.", "D.", or "E."? → **WRONG** - Remove the prefix!
2. The options should be just the text content, no letter prefixes
3. If you find option prefixes, go back and fix them before output
4. Are ALL fields that may contain commas properly quoted?
5. Does the answer number match a valid option (1 through optionCount)?

### ANSWER VALIDATION CRITICAL RULES:
**The answer in the MD might be WRONG. Your job is to:**
1. Extract the answer AS GIVEN in the MD file
2. Match it to the option position (1-4, 1-5, or 1-6)
3. DO NOT try to "correct" the answer - use what's in the MD
4. If the MD answer doesn't match any option, use your best judgment to find the closest match

**Answer Matching Priority:**
1. **Letter-based (A, B, C, D, E):** Convert to position number (A=1, B=2, etc.)
2. **Text-based:** Find the option that matches the answer text exactly
3. **Partial match:** If no exact match, find the closest option
4. **Number-based:** Use the number directly if it's a valid option index
"""

def convert_with_groq(md_content: str) -> str:
    """Convert markdown content to CSV using Groq API with retry on rate limit."""

    user_prompt = f"""Here are examples of how to convert Markdown to CSV:

### Example Input Markdown
{SAMPLE_MD}

### Example Output CSV
{SAMPLE_CSV}

---

## CRITICAL REMINDERS FOR CONVERSION:

0. **MOST CRITICAL - Option Prefix Removal:**
   - ALWAYS strip "A.", "B.", "C.", "D.", "E." from option text
   - "A. Economical" → "Economical" (NOT "A. Economical")
   - "B. Wasteful" → "Wasteful" (NOT "B. Wasteful")
   - **VERIFY YOUR OUTPUT:** Check that NO option starts with a letter + period!

1. **CSV QUOTING - ALWAYS QUOTE THESE FIELDS:**
   - **ALL Options** - Quote every single option, even if no commas
   - **Question** - Always quote
   - **Tags** - Always quote (always has commas)
   - **Category** - Always quote (may have commas like "Logical Reasoning,Directions")
   - **Answer Explanation** - Always quote
   - This prevents ALL column shift issues!

2. **DETERMINE MAXIMUM OPTION COUNT FIRST**
   - Read ALL questions first to find maximum option count (could be 2, 3, 4, 5, or 6)
   - CSV header will have Options1 through Options[maxCount]
   - Each question row has its actual optionCount and only that many non-empty options

3. **Option Count = ACTUAL number of options** (2, 3, 4, 5, or 6)
   - 2 options: Set optionCount=2, fill Options1-2
   - 4 options: Set optionCount=4, fill Options1-4
   - 5 options: Set optionCount=5, fill Options1-5
   - 6 options: Set optionCount=6, fill Options1-6
   - Options beyond actual count are empty strings

4. **Every row must have consistent column count** based on maxOptionCount

5. **Text-based answers:** Match the answer text to find the correct option number (1-6)

6. **Letter answers (A, B, C, D, E):** Convert to numbers (A=1, B=2, C=3, D=4, E=5)

7. **Number answers (1, 2, 3, 4, 5, 6):** Use directly as the answer

Now, convert the following Markdown to CSV using the exact same logic:

### Input Markdown
{md_content}

### Output CSV
IMPORTANT: Output ONLY the CSV. Start immediately with the header row.
"""

    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0,
                max_tokens=16000,
            )

            csv_output = response.choices[0].message.content

            # Clean up any conversational prefix
            if "Question Type,Question" in csv_output:
                csv_start = csv_output.find("Question Type,Question")
                csv_output = csv_output[csv_start:]

            # Clean up markdown code blocks - handle both ```csv and standalone ```
            if "```csv" in csv_output:
                csv_output = csv_output.replace("```csv", "").replace("```", "")
            # Also remove any standalone ``` lines (for cases where AI didn't use ```csv)
            csv_output = re.sub(r'^```\s*$', '', csv_output, flags=re.MULTILINE)

            # Clean up conversational text at the end (AI summaries like "I've processed all...")
            # Split by lines and only keep valid CSV lines (start with "objective" or header)
            lines = csv_output.split('\n')
            csv_lines = []
            for line in lines:
                line = line.strip()
                # Keep header line and lines starting with "objective"
                if line.startswith("Question Type,") or line.startswith("objective,"):
                    csv_lines.append(line)
                # Stop at first non-CSV line (conversational text)
                elif csv_lines and not (line.startswith("Question Type,") or line.startswith("objective,")):
                    break
            csv_output = '\n'.join(csv_lines)

            return csv_output.strip()

        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error
            if "rate_limit" in error_str.lower() or "429" in error_str:
                retry_after = extract_retry_after(error_str)
                retry_count += 1

                if retry_count >= MAX_RETRIES:
                    raise Exception(f"Rate limit: Max retries ({MAX_RETRIES}) reached")

                # Convert seconds to readable format
                hours = retry_after // 3600
                minutes = (retry_after % 3600) // 60
                seconds = retry_after % 60
                wait_str = ""
                if hours > 0:
                    wait_str += f"{hours}h "
                if minutes > 0:
                    wait_str += f"{minutes}m "
                wait_str += f"{seconds}s"

                print(f"  Rate limit hit. Waiting {wait_str}before retry {retry_count}/{MAX_RETRIES}...")
                time.sleep(retry_after)
            else:
                # Non-rate-limit error, raise immediately
                raise

    raise Exception("Max retries reached")

def convert_with_claude_cli(md_content: str) -> str:
    """Convert markdown content to CSV using Claude Code CLI in print mode."""

    user_prompt = f"""Here are examples of how to convert Markdown to CSV:

### Example Input Markdown
{SAMPLE_MD}

### Example Output CSV
{SAMPLE_CSV}

---

## CRITICAL REMINDERS FOR CONVERSION:

0. **MOST CRITICAL - Option Prefix Removal:**
   - ALWAYS strip "A.", "B.", "C.", "D.", "E." from option text
   - "A. Economical" → "Economical" (NOT "A. Economical")
   - "B. Wasteful" → "Wasteful" (NOT "B. Wasteful")
   - **VERIFY YOUR OUTPUT:** Check that NO option starts with a letter + period!

1. **CSV QUOTING - ALWAYS QUOTE THESE FIELDS:**
   - **ALL Options** - Quote every single option, even if no commas
   - **Question** - Always quote
   - **Tags** - Always quote (always has commas)
   - **Category** - Always quote (may have commas like "Logical Reasoning,Directions")
   - **Answer Explanation** - Always quote
   - This prevents ALL column shift issues!

2. **DETERMINE MAXIMUM OPTION COUNT FIRST**
   - Read ALL questions first to find maximum option count (could be 2, 3, 4, 5, or 6)
   - CSV header will have Options1 through Options[maxCount]
   - Each question row has its actual optionCount and only that many non-empty options

3. **Option Count = ACTUAL number of options** (2, 3, 4, 5, or 6)
   - 2 options: Set optionCount=2, fill Options1-2
   - 4 options: Set optionCount=4, fill Options1-4
   - 5 options: Set optionCount=5, fill Options1-5
   - 6 options: Set optionCount=6, fill Options1-6
   - Options beyond actual count are empty strings

4. **Every row must have consistent column count** based on maxOptionCount

5. **Text-based answers:** Match the answer text to find the correct option number (1-6)

6. **Letter answers (A, B, C, D, E):** Convert to numbers (A=1, B=2, C=3, D=4, E=5)

7. **Number answers (1, 2, 3, 4, 5, 6):** Use directly as the answer

Now, convert the following Markdown to CSV using the exact same logic:

### Input Markdown
{md_content}

### Output CSV

IMPORTANT: Output ONLY the CSV data. Start with the header row. Do NOT include any introductory text. Do NOT include any concluding remarks, summaries, or "I've processed" messages at the end. JUST the CSV and nothing else.
"""

    # Create the prompt file for Claude CLI
    prompt = f"""{get_system_prompt()}

{user_prompt}"""

    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            # Use claude command in print mode with stdin
            result = subprocess.run(
                ["claude", "--print", "--tools", "", "--no-session-persistence"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise Exception(f"Claude CLI error: {error_msg}")

            csv_output = result.stdout.strip()

            # Clean up any conversational prefix
            if "Question Type,Question" in csv_output:
                csv_start = csv_output.find("Question Type,Question")
                csv_output = csv_output[csv_start:]

            # Clean up markdown code blocks - handle both ```csv and standalone ```
            if "```csv" in csv_output:
                csv_output = csv_output.replace("```csv", "").replace("```", "")
            # Also remove any standalone ``` lines (for cases where AI didn't use ```csv)
            csv_output = re.sub(r'^```\s*$', '', csv_output, flags=re.MULTILINE)

            # Clean up conversational text at the end (AI summaries like "I've processed all...")
            # Split by lines and only keep valid CSV lines (start with "objective" or header)
            lines = csv_output.split('\n')
            csv_lines = []
            for line in lines:
                line = line.strip()
                # Keep header line and lines starting with "objective"
                if line.startswith("Question Type,") or line.startswith("objective,"):
                    csv_lines.append(line)
                # Stop at first non-CSV line (conversational text)
                elif csv_lines and not (line.startswith("Question Type,") or line.startswith("objective,")):
                    break
            csv_output = '\n'.join(csv_lines)

            return csv_output.strip()

        except subprocess.TimeoutExpired:
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                raise Exception("Claude CLI: Max retries reached due to timeout")
            print(f"  Timeout. Retrying {retry_count}/{MAX_RETRIES}...")
            time.sleep(10)

        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error
            if "rate limit" in error_str.lower() or "429" in error_str:
                retry_after = extract_retry_after(error_str)
                retry_count += 1

                if retry_count >= MAX_RETRIES:
                    raise Exception(f"Rate limit: Max retries ({MAX_RETRIES}) reached")

                hours = retry_after // 3600
                minutes = (retry_after % 3600) // 60
                seconds = retry_after % 60
                wait_str = ""
                if hours > 0:
                    wait_str += f"{hours}h "
                if minutes > 0:
                    wait_str += f"{minutes}m "
                wait_str += f"{seconds}s"

                print(f"  Rate limit hit. Waiting {wait_str}before retry {retry_count}/{MAX_RETRIES}...")
                time.sleep(retry_after)
            else:
                raise

def convert_md_to_csv(md_content: str) -> str:
    """Convert markdown content to CSV using the configured AI provider."""

    print(f"  Using AI provider: {AI_PROVIDER}")

    if AI_PROVIDER == "GROQ":
        return convert_with_groq(md_content)
    elif AI_PROVIDER == "CLAUDE_CLI":
        return convert_with_claude_cli(md_content)
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {AI_PROVIDER}. Use 'GROQ' or 'CLAUDE_CLI'")


# ---------------------------------------------------------
# 5. MAIN EXECUTION
# ---------------------------------------------------------

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)

    # Get all MD files from input directory
    input_path = Path(INPUT_MD_DIR)
    if not input_path.exists():
        print(f"Error: Directory '{INPUT_MD_DIR}' not found.")
        sys.exit(1)

    md_files = list(input_path.glob("*.md"))
    if not md_files:
        print(f"No .md files found in '{INPUT_MD_DIR}'")
        sys.exit(1)

    print(f"Found {len(md_files)} MD files in '{INPUT_MD_DIR}'")
    print(f"Output directory: '{OUTPUT_CSV_DIR}/'")
    print(f"AI Provider: {AI_PROVIDER}")
    print("-" * 50)

    success_count = 0
    error_count = 0

    for md_file in md_files:
        csv_filename = md_file.stem + ".csv"
        csv_path = Path(OUTPUT_CSV_DIR) / csv_filename

        # Skip if CSV already exists
        if csv_path.exists():
            print(f"Skipping {md_file.name} (CSV already exists)")
            continue

        print(f"Processing: {md_file.name}...")

        try:
            # Read MD content
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Convert to CSV (with automatic retry on rate limit)
            csv_output = convert_md_to_csv(md_content)

            # Validate CSV output
            if not csv_output or not csv_output.startswith("Question Type,Question"):
                raise Exception("Invalid CSV output - missing header")

            # Save to file
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_output)

            # Count questions (lines starting with "objective,")
            question_count = csv_output.count("\nobjective,") + 1 if csv_output.startswith("objective,") else csv_output.count("\nobjective,")
            print(f"  Saved to: {csv_path} ({question_count} questions)")
            success_count += 1

        except Exception as e:
            print(f"  Error: {e}")
            error_count += 1

    print("-" * 50)
    print(f"Done! Success: {success_count}, Errors: {error_count}")


if __name__ == "__main__":
    main()
