---
name: Questionnaire
description: Conduct a questionnaire by reading a TOML question file, presenting questions to the user one-by-one, and saving answers to a timestamped JSON file.
version: 1.0.0
trigger: qa, questionnaire, survey
---

# Questionnaire Skill

This skill enables conducting questionnaires with users by reading questions from a TOML file, presenting them one-by-one, and recording answers.

## Overview

The questionnaire skill:
1. Reads a TOML question file (specified by user or as argument)
2. Validates the question file format
3. Presents questions to the user one-by-one
4. Records user answers into a timestamped JSON file

## Commands

### Starting a Questionnaire

```
/qa <question_file.toml>
```

The question file must be a valid TOML file with the following structure:

```toml
title = "Project Survey"
description = "Please answer the following questions"

[[questions]]
id = "q1"
question = "What is your name?"
type = "text"
required = true

[[questions]]
id = "q2"  
question = "How satisfied are you?"
type = "choice"
options = ["Very satisfied", "Satisfied", "Neutral", "Dissatisfied"]
required = true

[[questions]]
id = "q3"
question = "Any additional comments?"
type = "text"
required = false
```

### Question Types

- **text**: Free-form text input
- **choice**: Single selection from options
- **yes_no**: Boolean yes/no question
- **number**: Numeric input

## Implementation

The skill is implemented as a Python script that:

1. **Parses TOML**: Uses Python's `toml` or `tomli` library to parse the question file
2. **Validates**: Checks for required fields (id, question, type) and validates question types
3. **Presents Questions**: Shows each question to the user with the `question` tool
4. **Records Answers**: Saves all responses to `answers_YYYYMMDD_HHMMSS.json`

## File Structure

```
skills/qa/
├── qa.md           # This skill file
└── qa_runner.py    # Python script that runs the questionnaire
```

## Answer File Format

Answers are saved to `answers_YYYYMMDD_HHMMSS.json`:

```json
{
  "questionnaire_title": "Project Survey",
  "completed_at": "2026-02-27T15:30:00",
  "questions": [
    {
      "id": "q1",
      "question": "What is your name?",
      "answer": "John Doe"
    },
    {
      "id": "q2",
      "question": "How satisfied are you?",
      "answer": "Very satisfied"
    }
  ]
}
```

## Error Handling

- Invalid TOML: Show error with specific parsing issue
- Missing required field: Ask user to provide or skip if optional
- Invalid question type: Skip question with warning
- File write error: Show error and offer to display answers on screen

## Usage Notes

- Always validate the question file before starting
- Present questions one at a time for better UX
- Mark required questions clearly
- Provide default values where applicable
- Confirm before saving answers
