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

2.A, B, C and D are four consecutive even numbers respectively and their average is 65. What is the product of A and D?  

**Options:  
**A. 3968

B. 4092

C. 4216

D. 4352  

**Answer: C.4216**

**Solution:**

Let x, x + 2, x + 4 and x + 6 represent numbers A, B, C and D respectively.

Then,  
x+(x+2)+(x+4)+(x+6)4=65

4x+12=260

4x=248

x=62

So, A = 62, B = 64, C = 66, D = 68

∴ A × D = 62 × 68 = 4216

3.The average of 5 consecutive multiples of 3 M, N, O, P, and Q is 54. What is the product of M and Q?

**Options:  
**A. 2916

B. 2880

C. 3136

D. 3249  

**Answer: B. 2880**

**Solution:**

Since M, N, O, P, and Q are five consecutive multiples of 3,

and we know that the average of numbers at equal intervals is the middle number.

Here the average is 54. So the numbers are 48, 51, 54, 57, 60.

Finally, the product of M and Q is 48 \* 60 = 2880.

4.The sum of 3 consecutive multiples of 5 is 60 more than the average of these numbers. What will be the highest of these numbers?  

**Options:  
**A. 15

B. 35

C. 25

D. 30  

**Answer: B. 35**

**Solution:**

Let's call the smallest of the 3 consecutive multiples of 5 "x".

Then we know that the next two numbers are x + 5 and x + 10.

The sum of these numbers is x + (x + 5) + (x + 10) = 3x + 15.

The average of these numbers is (x + (x + 5) + (x + 10)) / 3 = (3x + 15) / 3 = x + 5.

So the sum of the numbers is 60 more than the average:

3x + 15 = (x + 5) + 60

2x + 15 = 65

2x = 50

x = 25

Therefore, the highest of the 3 numbers is x + 10 = 25 + 10 = 35.

5.Find the value of 1000 + 1010 + 1020 + … + 1300.

**Options:  
**A. 91000

B. 93500

C. 35650

D. 98500  

**Answer: C. 35650**

**Solution:**

The sequence of numbers is 1000, 1010, 1020, …, 1300, and the number of terms in the sequence is (1300 - 1000) / 10 + 1 = 31.

Summation of the series in AP = Average x Number of elements

Here, the average of the arithmetic sequence is (first number + last number) / 2(1000 + 1300) / 2 = 1150

Total = 31 \* 1150 = 35650.

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

7.Find the 9th term of the arithmetic progression 2, 5, 8, …

**Options:  
**A. 48

B. 26

C. 32

D. 36  

**Answer: B. 26  
**

**Solution:**

The common difference in this AP is 3.

Therefore,

a9 = a1 + (n-1)d

\= 2 + (9-1)3

\= 26

Hence, the 9th term of the given AP is 26.

8.If the first term of an AP is 12, the common difference is 2, and the last term is 22, find the total number of terms in the AP.

**Options:  
**A. 8

B. 6

C. 12

D. 16  

**Answer: B. 6  
**

**Solution:**

Using the same method as above, we get:

22 = 12 + (n - 1)2

10 = 2(n - 1)

n - 1 = 5

n = 6

Therefore, there are 6 terms in the AP.

9\. Which term of the arithmetic progression (AP) 12, 18, 24, ... is 150?

**Options:  
**A. 19th term  
B. 20th term  
C. 21st term  
D. 23rd term

**Answer: D. 23rd term**

**Solution:**

The common difference of the AP 12, 18, 24, ... is d = 18 - 12 = 6.

To find which term is 150, we use the formula for the nth term of an arithmetic sequence:

aₙ = a₁ + (n - 1)d

Where:  
aₙ = 150 (the term we're looking for)

a₁ = 12 (the first term)

d = 6 (the common difference)

n = term number (what we need to find)

Substituting the values:

150 = 12 + (n - 1)(6)  
150 = 12 + 6n - 6  
150 = 6 + 6n  
150 - 6 = 6n  
144 = 6n  
n = 24

Wait, let me recalculate: 150 - 12 = (n - 1)(6)  
138 = (n - 1)(6)  
138 ÷ 6 = n - 1  
23 = n - 1  
n = 24

Actually: 138 = 6(n - 1)  
23 = n - 1  
n = 24

Let me verify: a₂₄ = 12 + (24-1)(6) = 12 + 138 = 150

Therefore, the 24th term of the AP is 150.  

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
Follow these STRICT rules:
1. Output ONLY valid CSV. Do not use markdown code blocks (```csv). Do NOT include any introductory text like "Here is the output CSV:" or similar.
2. Start IMMEDIATELY with the header row: Question Type,Question,Option count,Options1,Options2,Options3,Options4,Answer,Category,Difficulty,Score,Tags,Answer Explanation
3. 'Question Type' is always "objective".
4. 'Option count' is always 4.
5. 'Category', 'Difficulty', 'Score', 'Tags' should be filled as "Aptitude", "medium", "5", "Aptitude,Numbers" respectively if not specified.
6. For the 'Answer' column: Map the option letter to a number (A=1, B=2, C=3, D=4).
7. In 'Answer Explanation', replace newlines with " n " to keep the CSV valid.
8. Process ALL questions in the input. Do not skip any questions.
"""

def convert_with_groq(md_content: str) -> str:
    """Convert markdown content to CSV using Groq API with retry on rate limit."""

    user_prompt = f"""Here are examples of how to convert Markdown to CSV:

### Example Input Markdown
{SAMPLE_MD}

### Example Output CSV
{SAMPLE_CSV}

---

Now, convert the following Markdown to CSV using the exact same logic:

### Input Markdown
{md_content}

### Output CSV
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

            # Clean up markdown code blocks
            if "```csv" in csv_output:
                csv_output = csv_output.replace("```csv", "").replace("```", "")

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

Now, convert the following Markdown to CSV using the exact same logic:

### Input Markdown
{md_content}

### Output CSV

IMPORTANT: Output ONLY valid CSV. Start with the header row. Do not include any introductory text.
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

            # Clean up markdown code blocks
            if "```csv" in csv_output:
                csv_output = csv_output.replace("```csv", "").replace("```", "")

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
