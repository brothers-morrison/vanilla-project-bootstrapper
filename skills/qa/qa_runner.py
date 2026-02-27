#!/usr/bin/env python3
"""
Questionnaire Runner - Reads TOML question file, presents questions, saves answers.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class QuestionnaireRunner:
    """Run a questionnaire from a save TOML file and answers."""

    VALID_TYPES = {"text", "choice", "yes_no", "number"}

    def __init__(self, question_file: Path):
        self.question_file = question_file
        self.questions: list[dict[str, Any]] = []
        self.answers: list[dict[str, Any]] = []
        self.title = ""
        self.description = ""

    def validate(self) -> tuple[bool, str]:
        """Validate the question file format."""
        try:
            with open(self.question_file, "rb") as f:
                data = tomllib.load(f)
        except FileNotFoundError:
            return False, f"Question file not found: {self.question_file}"
        except tomllib.TOMLDecodeError as e:
            return False, f"Invalid TOML: {e}"

        if not data.get("questions"):
            return False, "No questions defined in file"

        self.title = data.get("title", "Untitled Questionnaire")
        self.description = data.get("description", "")

        for i, q in enumerate(data["questions"]):
            if "id" not in q:
                return False, f"Question {i + 1} missing required 'id' field"
            if "question" not in q:
                return (
                    False,
                    f"Question {q.get('id', i + 1)} missing required 'question' field",
                )
            if "type" not in q:
                return False, f"Question {q['id']} missing required 'type' field"
            if q["type"] not in self.VALID_TYPES:
                return False, f"Question {q['id']} has invalid type: {q['type']}"

            if q["type"] == "choice" and "options" not in q:
                return False, f"Question {q['id']} is choice type but has no options"

            self.questions.append(q)

        return True, "Valid"

    def get_answer_file_path(self) -> Path:
        """Generate timestamped answer file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(f"answers_{timestamp}.json")

    def format_question(self, q: dict[str, Any]) -> str:
        """Format a question for display."""
        required = " (required)" if q.get("required", False) else " (optional)"

        if q["type"] == "choice":
            options = ", ".join(q["options"])
            return f"{q['question']}{required}\nOptions: {options}"
        elif q["type"] == "yes_no":
            return f"{q['question']}{required}\nAnswer with yes or no"
        elif q["type"] == "number":
            return f"{q['question']}{required}\nEnter a number"
        else:
            return f"{q['question']}{required}"

    def save_answers(self) -> Path:
        """Save answers to JSON file."""
        output = {
            "questionnaire_title": self.title,
            "completed_at": datetime.now().isoformat(),
            "questions": self.answers,
        }

        output_path = self.get_answer_file_path()
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: qa_runner.py <question_file.toml>")
        sys.exit(1)

    question_file = Path(sys.argv[1])
    runner = QuestionnaireRunner(question_file)

    valid, msg = runner.validate()
    if not valid:
        print(f"Error: {msg}")
        sys.exit(1)

    print(f"Questionnaire: {runner.title}")
    print(f"{runner.description}\n" if runner.description else "")

    for q in runner.questions:
        print(f"\n{runner.format_question(q)}")

        answer = input("Your answer: ").strip()

        if not answer and q.get("required", False):
            print("This question is required. Please provide an answer.")
            while not answer:
                answer = input("Your answer: ").strip()

        runner.answers.append(
            {
                "id": q["id"],
                "question": q["question"],
                "answer": answer,
            }
        )

    output_path = runner.save_answers()
    print(f"\nAnswers saved to: {output_path}")


if __name__ == "__main__":
    main()
