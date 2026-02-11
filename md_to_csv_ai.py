import os
from groq import Groq

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
# Replace with your actual API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 

# Initialize Client
client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------
# 2. SAMPLE DATA (Few-Shot Examples)
# ---------------------------------------------------------
# We use specific examples from your provided data to teach the AI the pattern.
# We use Q1 (Standard), Q9 (Data Inadequate), and Q16 (Complex Solution).

SAMPLE_MD = """
1.The sum of the ages of 3 cousins born at intervals of 4 years is 33. What is the age of the youngest cousin?

**Options:  
**A.7

B.5

C.10

D.6

**Answer : A.7  
**

**Solution:**

Let's assume that the age of the youngest cousin is x.

Then, the age of the second and third cousin will be x+4 and x+8, respectively.

The sum of their ages is given as 33: x + (x+4) + (x+8) = 33.

Simplifying the above equation, we get:  
3x + 12 = 33.

Subtracting 12 from both sides, we get:

3x = 21.

Dividing by 3,

we get: x = 7.

Therefore, the age of the youngest cousin is 7 years old.

9.X is as much younger than Y as he is older than Z. If the sum of the ages of Y and Z is 70 years, what is definitely the difference between Y and X's age?

**Options:  
**A.1 year

B.2 years

C.25 years

D.Data inadequate  

**Answer: D.Data inadequate  
**

**Solution:**

Given that:

i. The difference of age between Y and X = The difference of age between X and Z.

ii. Sum of age of Y and Z is 50 i.e. (Y+Z) = 70.

Y -X = X -Z

(Y+Z) = 2X

Now given that, (Y+Z) = 70

So, 70 = 2X and therefore X = 35.

Here we know the value(age) of X (35),

but we don't know the age of Y.

Therefore, (Y-X) cannot be determined.so Data inadequate

16.One year ago, a man was 6 times as old as his son. Now his age is equal to the square of his son's age. Find their present ages.  

**Options:  
**A.25

B.30

C.33

D.24  

**Answer : A.25**

**Solution:**

Let's assume that the man's current age is "m" and his son's current age is "s".

We know that one year ago, the man was 6 times as old as his son.

So, one year ago:

m - 1 = 6(s - 1)

Expanding this equation:

m - 1 = 6s - 6

m = 6s - 5

We also know that the man's current age is equal to the square of his son's age:

m = s^2

Now we can substitute the second equation into the first equation:

s^2 = 6s - 5

Rearranging this equation:

s^2 - 6s + 5 = 0

This equation can be factored as:

(s - 5)(s - 1) = 0

So, either s = 5 or s = 1.

If s = 5, then the son's current age is 5 years old.

Substituting this into the equation m = s^2, we get:

m = 5^2 = 25

Therefore, the man's current age is 25 years old and his son's current age is 5 years old.
"""

SAMPLE_CSV = """Question Type,Question,Option count,Options1,Options2,Options3,Options4,Answer,Category,Difficulty,Score,Tags,Answer Explanation
objective,"The sum of the ages of 3 cousins born at intervals of 4 years is 33. What is the age of the youngest cousin?",4,7,5,10,6,1,Aptitude,medium,5,Aptitude,Numbers,"Let's assume that the age of the youngest cousin is x. n Then, the age of the second and third cousin will be x+4 and x+8, respectively. n The sum of their ages is given as 33: x + (x+4) + (x+8) = 33. n Simplifying the above equation, we get: n 3x + 12 = 33. n Subtracting 12 from both sides, we get: n 3x = 21. n Dividing by 3, n we get: x = 7. n Therefore, the age of the youngest cousin is 7 years old."
objective,"X is as much younger than Y as he is older than Z. If the sum of the ages of Y and Z is 70 years, what is definitely the difference between Y and X's age?",4,1 year,2 years,25 years,Data inadequate,4,Aptitude,medium,5,Aptitude,Numbers,"Given that: n i. The difference of age between Y and X = The difference of age between X and Z. n ii. Sum of age of Y and Z is 50 i.e. (Y+Z) = 70. n Y -X = X -Z n (Y+Z) = 2X n Now given that, (Y+Z) = 70 n So, 70 = 2X and therefore X = 35. n Here we know the value(age) of X (35), n but we don't know the age of Y. n Therefore, (Y-X) cannot be determined.so Data inadequate"
objective,"One year ago, a man was 6 times as old as his son. Now his age is equal to the square of his son's age. Find their present ages.",4,25,30,33,24,1,Aptitude,medium,5,Aptitude,Numbers,"Let's assume that the man's current age is \"m\" and his son's current age is \"s\". n We know that one year ago, the man was 6 times as old as his son. n So, one year ago: n m - 1 = 6(s - 1) n Expanding this equation: n m - 1 = 6s - 6 n m = 6s - 5 n We also know that the man's current age is equal to the square of his son's age: n m = s^2 n Now we can substitute the second equation into the first equation: n s^2 = 6s - 5 n Rearranging this equation: n s^2 - 6s + 5 = 0 n This equation can be factored as: n (s - 5)(s - 1) = 0 n So, either s = 5 or s = 1. n If s = 5, then the son's current age is 5 years old. n Substituting this into the equation m = s^2, we get: n m = 5^2 = 25 n Therefore, the man's current age is 25 years old and his son's current age is 5 years old."
"""

# ---------------------------------------------------------
# 3. YOUR NEW INPUT DATA
# ---------------------------------------------------------
# Paste your new Markdown questions inside this variable.
input_md_path = "/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib/md-aptitude/Ages Test - DB.md"
with open (input_md_path, 'r') as f:
    INPUT_MD = f.read()
    f.close()
# ---------------------------------------------------------
# 4. PROMPT ENGINEERING
# ---------------------------------------------------------

system_prompt = """You are an intelligent data extractor. Convert Markdown text into CSV format.
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

user_prompt = f"""Here are examples of how to convert Markdown to CSV:

### Example Input Markdown
{SAMPLE_MD}

### Example Output CSV
{SAMPLE_CSV}

---

Now, convert the following Markdown to CSV using the exact same logic:

### Input Markdown
{INPUT_MD}

### Output CSV
"""

# ---------------------------------------------------------
# 5. EXECUTION
# ---------------------------------------------------------
try:
    print("Processing data via Groq API...")
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model="llama-3.3-70b-versatile", # Use 70b for best accuracy on complex parsing
        temperature=0,
        max_tokens=16000,  # Increased to handle 23+ questions
    )

    csv_output = response.choices[0].message.content

    # Clean up any conversational prefix (e.g., "Here is the output CSV:")
    if "Question Type,Question" in csv_output:
        # Find where the CSV actually starts
        csv_start = csv_output.find("Question Type,Question")
        csv_output = csv_output[csv_start:]

    # Clean up if the AI accidentally wraps it in markdown
    if "```csv" in csv_output:
        csv_output = csv_output.replace("```csv", "").replace("```", "")

    csv_output = csv_output.strip()

    # Print result
    print("--- CSV Result ---")
    print(csv_output)

    # Save to file
    with open("converted_output.csv", "w", encoding="utf-8") as f:
        f.write(csv_output)
    
    print("\nSaved to 'converted_output.csv'")

except Exception as e:
    print(f"Error: {e}")