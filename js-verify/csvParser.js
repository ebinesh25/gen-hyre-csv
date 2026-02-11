class CSVParser {
  constructor(name) {
    this.name = name;
  }

  static parseHTML(html) {
    return html
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  validate(data, maxOptionCount, maxTestCaseCount, features) {
    this.error = null;
    this.result = [];
    try {
      data.forEach((row) => {
        this.questionType = row[0].replaceAll(' ', '').toLowerCase();

        switch (this.questionType) {
          case 'questiontype':
            break;
          case 'objective':
            this.obj = {};
            this.obj.questionType = 'objective';
            this.validateObjective(row, maxOptionCount, features);
            this.result.push(this.obj);
            break;
          case 'programming':
            this.obj = {};
            this.obj.questionType = 'programming';
            this.validateProgramming(row, maxTestCaseCount);
            this.result.push(this.obj);
            break;
          default:
            throw new Error('Invalid Question Type');
        }
      });
    } catch (e) {
      this.error = e.message;
    }
    if (this.error) return [[], this.error];
    return [this.result, this.error];
  }

  /**
 * OBJECTIVE
 * ---------
 * INDEX  -  HEADING
 * 0      -  questionType
 * 1      -  question
 * 2      -  optionCount
 * 3...N  -  options (dynamic, based on maxOptionCount)
 * N+1    -  answer
 * N+2    -  category
 * N+3    -  difficulty
 * N+4    -  score
 * N+5    -  tags
 * N+6    -  answerExplanation (if enabled)
 *
 * Example with maxOptionCount=4: options at columns 3-6, answer at column 7
 * Example with maxOptionCount=5: options at columns 3-7, answer at column 8
 * Example with maxOptionCount=6: options at columns 3-8, answer at column 9
 */
  validateObjective(row, maxOptionCount, features) {
    this.nextIndex = 0;
    this.validateQuestion(row);
    // OPTION COUNT
    this.nextIndex += 1;
    const optionCount = Number(row[this.nextIndex]);
    if (Number.isNaN(optionCount) || !Number.isInteger(optionCount)) throw new Error('Invalid option count');
    if (optionCount < 2) throw new Error('Option count must be at least 2');
    for (let i = 1; i <= optionCount; i += 1) {
      this.nextIndex += 1;
      const option = row[this.nextIndex].trim();
      if (!option) throw new Error('Option is missing');
      this.obj.options = this.obj.options ? this.obj.options : [];
      this.obj.options.push(CSVParser.parseHTML(option));
    }
    // Increment the pointer(nextIndex) to answer column when optionCount is min
    this.nextIndex += (maxOptionCount - optionCount);
    // ANSWER
    this.nextIndex += 1;
    const answer = Number(row[this.nextIndex]);
    if (Number.isNaN(answer) || !Number.isInteger(answer)) throw new Error('Invalid answer');
    if (answer < 1 || answer > optionCount) throw new Error(`Invalid answer: answer is ${answer} but only ${optionCount} options exist (answer must be 1-${optionCount})`);
    this.obj.answer = answer;
    this.validateCategory(row);
    this.validateDifficulty(row);
    this.validateScore(row);
    this.validateTags(row);
    if (features.hasQuestionExplanationFeature) {
      this.validateAnswerExplanation(row);
    }
  }

  /**
   * PROGRAMMING
   * -----------
   * INDEX  -   HEADING
   * 0      -   questionType
   * 1      -   question
   * 2      -   category
   * 3      -   difficulty
   * 4      -   score
   * 5      -   tags
   * 6      -   no of test-cases
   * 7      -   input
   * 8      -   output
   * 9      -   weighage
   * 10     -   no of sample test-cases
   * 11     -   input
   * 12     -   output
   */
  validateProgramming(row, maxTestCaseCount) {
    this.nextIndex = 0;
    this.validateQuestion(row);
    this.validateCategory(row);
    this.validateDifficulty(row);
    this.validateScore(row);
    this.validateTags(row);
    this.nextIndex += 1;
    const testCaseCount = Number(row[this.nextIndex]);
    if (Number.isNaN(testCaseCount) || !Number.isInteger(testCaseCount)) throw new Error('Invalid test case count');
    if (testCaseCount < 1 || testCaseCount > 10) throw new Error('Test case count must be between 1 to 10');
    this.obj.testcases = this.obj.testcases ? this.obj.testcases : [];
    let totalWeightage = 0;
    for (let i = 1; i <= testCaseCount * 3; i += 3) {
      const testCase = this.validateTestCase({ row, isSampleTestCase: false });
      totalWeightage += testCase.weightage;
      this.obj.testcases.push(testCase);
    }
    if (totalWeightage !== this.obj.weightage) throw new Error('Total weightage of test cases must be equal to score');
    this.nextIndex += (maxTestCaseCount - testCaseCount) * 3;
    this.nextIndex += 1;

    let sampleTestCaseCount = row[this.nextIndex];
    this.obj.sampleTestCases = this.obj.sampleTestCases ? this.obj.sampleTestCases : [];
    if (sampleTestCaseCount) {
      sampleTestCaseCount = Number(sampleTestCaseCount);
      if (Number.isNaN(sampleTestCaseCount) || !Number.isInteger(sampleTestCaseCount)) throw new Error('Invalid sample test case count');
      if (sampleTestCaseCount < 1) throw new Error('Sample test case count must be greater than 0');
      for (let i = 1; i <= sampleTestCaseCount * 2; i += 2) {
        const sampleTestCase = this.validateTestCase({ row, isSampleTestCase: true });
        this.obj.sampleTestCases.push(sampleTestCase);
        sampleTestCase.weightage = 0;
        sampleTestCase.isSampleTestCaseChecked = true;
        this.obj.testcases.push(sampleTestCase);
      }
    } else {
      const testCaseObj = {};
      testCaseObj.input = this.obj.testcases[0].input;
      testCaseObj.output = this.obj.testcases[0].output;
      this.obj.sampleTestCases.push(testCaseObj);
      testCaseObj.weightage = 0;
      testCaseObj.isSampleTestCaseChecked = true;
      this.obj.testcases.push(testCaseObj);
    }
  }

  validateQuestion(row) {
    this.nextIndex += 1;
    const question = row[this.nextIndex].trim();
    if (!question) throw new Error('Question is missing');
    this.obj.question = CSVParser.parseHTML(question);
  }

  validateCategory(row) {
    this.nextIndex += 1;
    const category = row[this.nextIndex].trim();
    if (!category.length) {
      throw new Error('Category is required');
    }
    if (/[,"']/g.test(category)) {
      throw new Error('Category should not contain commas or quotations');
    }
    if (!/^[\w\s-]+$/.test(category)) {
      throw new Error(
        'Category can only contain letters, numbers, spaces, or hyphens',
      );
    }
    this.obj.category = category;
  }

  validateDifficulty(row) {
    this.nextIndex += 1;
    const difficulty = row[this.nextIndex].trim().toLowerCase();
    if (!['easy', 'medium', 'hard'].includes(difficulty)) throw new Error('Difficulty should be easy/medium/hard');
    this.obj.difficulty = difficulty;
  }

  validateScore(row) {
    this.nextIndex += 1;
    const score = Number(row[this.nextIndex]);
    if (Number.isNaN(score) || !Number.isInteger(score)) throw new Error('Invalid score');
    if (score < 1) throw new Error('Score must be greater than 0');
    this.obj.weightage = score;
  }

  validateTags(row) {
    this.nextIndex += 1;
    const tags = row[this.nextIndex].trim().replaceAll(/\s*,\s*/g, ',').split(',');
    if (tags.some((ele) => ele === '')) throw new Error('Tags should not be empty');
    this.obj.tags = tags;
  }

  validateTestCase({ row, isSampleTestCase }) {
    const testCaseObj = {};
    this.nextIndex += 1;
    const input = row[this.nextIndex].trim();
    if (!input) throw new Error('Input is missing');
    testCaseObj.input = CSVParser.parseHTML(input);
    this.nextIndex += 1;
    const output = row[this.nextIndex].trim();
    if (!output) throw new Error('Output is missing');
    testCaseObj.output = CSVParser.parseHTML(output);
    if (!isSampleTestCase) {
      this.nextIndex += 1;
      const weightage = Number(row[this.nextIndex]);
      if (Number.isNaN(weightage) || !Number.isInteger(weightage)) throw new Error('Invalid weightage');
      if (weightage < 1) throw new Error('Weightage must be greater than 0');
      testCaseObj.weightage = weightage;
    }
    return testCaseObj;
  }

  validateAnswerExplanation(row) {
    this.nextIndex += 1;
    const answerExplanation = row[this.nextIndex].trim();
    if (!answerExplanation) throw new Error('Answer explanation is missing');
    this.obj.answerExplanation = CSVParser.parseHTML(answerExplanation);
  }
}
export default CSVParser;