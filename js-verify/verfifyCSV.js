import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import CSVParser from "./csvParser.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ROOT_DIR = path.dirname(__dirname);
const SOURCE_DIR = path.join(ROOT_DIR, "csv");
const VERIFIED_DIR = path.join(__dirname, "csv-verified");
const FAILED_DIR = path.join(__dirname, "csv-failed");

// Configuration - maxOptionCount will be determined dynamically from CSV header
const CONFIG = {
  maxOptionCount: 4, // Default, will be overridden by actual CSV header
  maxTestCaseCount: 10,
  features: {
    hasQuestionExplanationFeature: true,
  },
};

// Parse CSV file into array of rows
function parseCSV(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const rows = [];
  let currentRow = [];
  let inQuotes = false;
  let currentCell = "";

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    const nextChar = content[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        // Escaped quote
        currentCell += '"';
        i++;
      } else {
        // Toggle quote mode
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      // End of cell
      currentRow.push(currentCell);
      currentCell = "";
    } else if ((char === "\r" || char === "\n") && !inQuotes) {
      // End of row
      if (currentCell || currentRow.length > 0) {
        currentRow.push(currentCell);
      }
      if (currentRow.length > 0) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentCell = "";
      // Skip \r\n
      if (char === "\r" && nextChar === "\n") {
        i++;
      }
    } else {
      currentCell += char;
    }
  }

  // Add last row/cell
  if (currentCell || currentRow.length > 0) {
    currentRow.push(currentCell);
    rows.push(currentRow);
  }

  return rows;
}

// Validate a single CSV file
function validateCSV(filePath) {
  try {
    const rows = parseCSV(filePath);

    if (rows.length === 0) {
      return { valid: false, error: "No data rows found", rowCount: 0 };
    }

    // Dynamically determine maxOptionCount from the header row
    const header = rows[0];
    let maxOptionCount = 0;
    for (let i = 0; i < header.length; i++) {
      const col = header[i].trim();
      if (col.startsWith("Options") || col.startsWith("option")) {
        const num = parseInt(col.replace(/\D+/g, ""), 10);
        if (!isNaN(num)) {
          maxOptionCount = num;
        }
      }
    }

    // If no option columns found in header, use default
    if (maxOptionCount === 0) {
      maxOptionCount = 4;
    }

    console.log(`  Dynamic maxOptionCount determined: ${maxOptionCount}`);

    const parser = new CSVParser(path.basename(filePath));

    // Filter out empty rows
    const dataRows = rows.filter(
      (row) => row.length > 0 && row[0] && row[0].trim(),
    );

    if (dataRows.length === 0) {
      return { valid: false, error: "No data rows found", rowCount: 0 };
    }

    // Validate row by row and collect ALL errors
    const errors = [];
    let validResult = [];
    let rowIndex = 0;

    for (const row of dataRows) {
      const questionType = row[0].replaceAll(" ", "").toLowerCase();

      if (questionType === "questiontype") {
        rowIndex++;
        continue;
      }

      try {
        const [result, error] = parser.validate(
          [row],
          maxOptionCount, // Use dynamically determined maxOptionCount
          CONFIG.maxTestCaseCount,
          CONFIG.features,
        );

        if (error) {
          const questionPreview = row[1]
            ? row[1].substring(0, 50)
            : "(no question)";

          // Try to extract column info from error message
          const errorLower = error.toLowerCase();
          let columnName = "Unknown";
          let columnValue = "";

          // Parse error to find column info
          if (errorLower.includes("option")) {
            const optionMatch = error.match(/Option\s*(\d+)/i);
            if (optionMatch) {
              columnName = `Option${optionMatch[1]}`;
              const optionIndex = parseInt(optionMatch[1]) - 1;
              // Options typically start at index 2 (after QuestionType and Question)
              columnValue = row[2 + optionIndex] || "";
            }
          } else if (errorLower.includes("answer")) {
            columnName = "Answer";
            // Find answer column index in header
            const answerColIndex = header.findIndex(h =>
              h.toLowerCase().includes("answer") ||
              h.toLowerCase().includes("correctanswer") ||
              h.toLowerCase().includes("correct answer")
            );
            if (answerColIndex >= 0 && row[answerColIndex]) {
              columnValue = row[answerColIndex];
            }
          } else if (errorLower.includes("question")) {
            columnName = "Question";
            columnValue = row[1] || "";
          } else if (errorLower.includes("testcase") || errorLower.includes("test case")) {
            const tcMatch = error.match(/TestCase\s*(\d+)/i);
            if (tcMatch) {
              columnName = `TestCase${tcMatch[1]}`;
            }
          } else if (errorLower.includes("explanation")) {
            columnName = "Explanation";
            const expColIndex = header.findIndex(h =>
              h.toLowerCase().includes("explanation") ||
              h.toLowerCase().includes("explantion") // common typo
            );
            if (expColIndex >= 0 && row[expColIndex]) {
              columnValue = row[expColIndex];
            }
          }

          errors.push({
            row: rowIndex,
            column: columnName,
            columnValue: columnValue.substring(0, 100), // Limit length
            error: error,
            reason: getFailureReason(error),
            questionPreview: questionPreview,
            rowData: row.map((cell, idx) => ({
              column: header[idx] || `Column${idx}`,
              value: cell.substring(0, 50) // Limit each cell value
            }))
          });
        }
        if (result && result.length > 0) {
          validResult.push(result[0]);
        }
      } catch (e) {
        const questionPreview = row[1]
          ? row[1].substring(0, 50)
          : "(no question)";

        errors.push({
          row: rowIndex,
          column: "Unknown",
          columnValue: "",
          error: e.message,
          reason: getFailureReason(e.message),
          questionPreview: questionPreview,
          rowData: row.map((cell, idx) => ({
            column: header[idx] || `Column${idx}`,
            value: cell.substring(0, 50)
          }))
        });
      }
      rowIndex++;
    }

    // Return result with all errors collected
    if (errors.length > 0) {
      return {
        valid: false,
        errors: errors,
        errorCount: errors.length,
        rowCount: dataRows.length,
        questionCount: validResult.length,
      };
    }

    return {
      valid: true,
      rowCount: dataRows.length - 1, // Exclude header
      questionCount: validResult.length,
    };
  } catch (e) {
    return {
      valid: false,
      errors: [{
        row: 0,
        column: "File",
        columnValue: "",
        error: e.message,
        reason: "File parsing error",
        questionPreview: "",
        rowData: []
      }],
      errorCount: 1,
      rowCount: 0
    };
  }
}

// Main verification function
function verifyAllCSVs() {
  // Create output directories
  if (!fs.existsSync(VERIFIED_DIR)) {
    fs.mkdirSync(VERIFIED_DIR, { recursive: true });
  }
  if (!fs.existsSync(FAILED_DIR)) {
    fs.mkdirSync(FAILED_DIR, { recursive: true });
  }

  // Get all CSV files from source directory
  const files = fs.readdirSync(SOURCE_DIR).filter((f) => f.endsWith(".csv"));

  console.log(`Found ${files.length} CSV files to verify\n`);
  console.log("=".repeat(80));

  const results = {
    passed: [],
    failed: [],
  };

  for (const file of files) {
    const sourcePath = path.join(SOURCE_DIR, file);
    const validationResult = validateCSV(sourcePath);

    if (validationResult.valid) {
      // Copy to verified folder
      const destPath = path.join(VERIFIED_DIR, file);
      fs.copyFileSync(sourcePath, destPath);
      results.passed.push({
        file,
        ...validationResult,
      });
      console.log(`✓ PASS: ${file}`);
      console.log(`  Questions: ${validationResult.questionCount}`);
    } else {
      // Copy to failed folder
      const destPath = path.join(FAILED_DIR, file);
      fs.copyFileSync(sourcePath, destPath);

      // Handle both old format (single error) and new format (errors array)
      const errorData = validationResult.errors
        ? {
            file,
            errorCount: validationResult.errorCount,
            errors: validationResult.errors,
          }
        : {
            file,
            error: validationResult.error,
          };

      results.failed.push(errorData);

      console.log(`✗ FAIL: ${file}`);
      if (validationResult.errors) {
        console.log(`  Error Count: ${validationResult.errorCount}`);
        validationResult.errors.forEach((e, idx) => {
          console.log(`  [${idx + 1}] Row ${e.row}, Column: ${e.column}`);
          console.log(`      Error: ${e.error}`);
          console.log(`      Reason: ${e.reason}`);
          if (e.columnValue) {
            console.log(`      Value: "${e.columnValue}"`);
          }
        });
      } else {
        console.log(`  Error: ${validationResult.error}`);
      }
    }
    console.log("-".repeat(80));
  }

  // Summary
  console.log("\n" + "=".repeat(80));
  console.log("SUMMARY");
  console.log("=".repeat(80));
  console.log(`Total files: ${files.length}`);
  console.log(`Passed: ${results.passed.length}`);
  console.log(`Failed: ${results.failed.length}`);
  console.log("\nVerified files saved to:", VERIFIED_DIR);
  console.log("Failed files saved to:", FAILED_DIR);

  if (results.failed.length > 0) {
    console.log("\nFailed files:");
    results.failed.forEach((f) => {
      if (f.errors) {
        console.log(`  - ${f.file}: ${f.errorCount} error(s)`);
        f.errors.forEach((e) => {
          console.log(`    Row ${e.row}, Col ${e.column}: ${e.reason}`);
        });
      } else {
        console.log(`  - ${f.file}: ${f.error}`);
      }
    });
  }

  // Generate JSON report with detailed errors
  const reportPath = path.join(__dirname, "verification-report.json");
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: files.length,
      passed: results.passed.length,
      failed: results.failed.length,
    },
    passed: results.passed.map((p) => ({
      file: p.file,
      rowCount: p.rowCount,
      questionCount: p.questionCount,
    })),
    failed: results.failed.map((f) => {
      if (f.errors) {
        return {
          file: f.file,
          errorCount: f.errorCount,
          errors: f.errors.map((e) => ({
            row: e.row,
            column: e.column,
            columnValue: e.columnValue,
            error: e.error,
            reason: e.reason,
            questionPreview: e.questionPreview,
            rowData: e.rowData,
          })),
        };
      }
      // Backward compatibility for old format
      return {
        file: f.file,
        error: f.error,
        reason: getFailureReason(f.error),
      };
    }),
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log("\nJSON report saved to:", reportPath);

  return results;
}

// Get human-readable failure reason
function getFailureReason(error) {
  if (error.includes("No data rows found")) {
    return "File is empty or contains no valid data rows";
  }
  if (error.includes("only") && error.includes("options exist")) {
    return "Answer key exceeds option count - the answer number is greater than the number of options provided";
  }
  if (error.includes("Question")) {
    return "Invalid question format or missing required question fields";
  }
  if (error.includes("Option")) {
    return "Invalid option format or exceeds maximum option count";
  }
  if (error.includes("Answer")) {
    return "Invalid answer key or answer does not match any option";
  }
  if (error.includes("TestCase")) {
    return "Invalid test case format or exceeds maximum test case count";
  }
  if (error.includes("Explanation")) {
    return "Invalid explanation format";
  }
  return "Unknown validation error";
}

function verifyCSV(file_path) {
  const validationResult = validateCSV(file_path);
  const file = path.basename(file_path);
  const results = {
    passed: [],
    failed: [],
  };

  if (validationResult.valid) {
    // Copy to verified folder
    const destPath = path.join(VERIFIED_DIR, file);
    fs.copyFileSync(file_path, destPath);
    results.passed.push({
      file,
      ...validationResult,
    });
    console.log(`✓ PASS: ${file}`);
    console.log(`  Questions: ${validationResult.questionCount}`);
  } else {
    // Copy to failed folder
    const destPath = path.join(FAILED_DIR, file);
    fs.copyFileSync(file_path, destPath);

    const errorData = validationResult.errors
      ? {
          file,
          errorCount: validationResult.errorCount,
          errors: validationResult.errors,
        }
      : {
          file,
          error: validationResult.error,
        };

    results.failed.push(errorData);
    console.log(`✗ FAIL: ${file}`);

    if (validationResult.errors) {
      console.log(`  Error Count: ${validationResult.errorCount}`);
      validationResult.errors.forEach((e, idx) => {
        console.log(`  [${idx + 1}] Row ${e.row}, Column: ${e.column}`);
        console.log(`      Error: ${e.error}`);
        console.log(`      Reason: ${e.reason}`);
        if (e.columnValue) {
          console.log(`      Value: "${e.columnValue}"`);
        }
      });
    } else {
      console.log(`  Error: ${validationResult.error}`);
    }
  }
  console.log("-".repeat(80));
}

// Run verification for a CSV
// const file_path =
//   "/home/positron/Documents/Guvi/test-automation/hyrenet-question-lib/aptitude_all_questions.csv";
// verifyCSV(fileURLToPath)

// Run verification for all CSV
verifyAllCSVs();
