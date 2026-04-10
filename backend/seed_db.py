"""Load curated questions (idempotent by question_id). Run from backend/: python seed_db.py"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent
load_dotenv(_root / ".env")
load_dotenv(_root.parent / ".env")


@dataclass(frozen=True)
class Row:
    question_id: uuid.UUID
    role_category: str
    question_text: str
    scraped_ideal_answer: str
    source_url: str | None = None


ROWS: tuple[Row, ...] = (
    Row(
        question_id=uuid.UUID("a1000001-0001-4000-8000-000000000001"),
        role_category="Python Developer",
        question_text="What is the difference between a list and a tuple in Python?",
        scraped_ideal_answer=(
            "Lists are mutable: you can change elements, append, and remove items. "
            "Tuples are immutable: once created, their contents cannot be changed. "
            "Lists use more memory and are slightly slower for some operations; tuples "
            "can be used as dict keys when they contain only hashable items. "
            "Use lists for homogeneous sequences that change over time; use tuples for "
            "fixed records, function return bundles, and hashable compound keys."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("a1000001-0001-4000-8000-000000000002"),
        role_category="Python Developer",
        question_text="Explain what a decorator is in Python and give a simple use case.",
        scraped_ideal_answer=(
            "A decorator is a callable that takes a function (or class) and returns a "
            "replacement function, letting you wrap behavior around the original without "
            "changing its body. It is syntactic sugar for `fn = my_decorator(fn)`. "
            "Common uses include logging, timing, access control, caching, and registering "
            "routes in web frameworks. A minimal example is a decorator that prints the "
            "function name before calling the wrapped function."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("a1000001-0001-4000-8000-000000000003"),
        role_category="Python Developer",
        question_text="What are list comprehensions and when would you prefer a plain for-loop?",
        scraped_ideal_answer=(
            "List comprehensions build a new list in a single expression: "
            "`[expr for x in iterable if cond]`. They are idiomatic, often faster than "
            "append loops for simple transforms, and keep mapping and filtering readable. "
            "Prefer a for-loop when the logic is complex, has side effects, needs multiple "
            "steps with intermediate state, or would make a comprehension hard to debug."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("b2000002-0002-4000-8000-000000000001"),
        role_category="Data Scientist",
        question_text="What is overfitting and how do you detect it?",
        scraped_ideal_answer=(
            "Overfitting means the model fits training noise instead of generalizable "
            "patterns, showing low training error but poor performance on held-out data. "
            "Detect it by comparing training vs validation metrics, using cross-validation, "
            "learning curves, and regularization or simpler models as sanity checks."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("b2000002-0002-4000-8000-000000000002"),
        role_category="Data Scientist",
        question_text="Explain precision and recall in classification.",
        scraped_ideal_answer=(
            "Precision is the fraction of positive predictions that are correct: "
            "TP / (TP + FP). Recall is the fraction of actual positives found: "
            "TP / (TP + FN). High precision means fewer false alarms; high recall means "
            "fewer missed positives. They trade off depending on the cost of errors."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("c3000003-0003-4000-8000-000000000001"),
        role_category="Project Manager",
        question_text="How do you handle a critical deadline slip?",
        scraped_ideal_answer=(
            "Re-validate scope with stakeholders, identify the critical path, and "
            "communicate impact early with options: descope, add resources where helpful, "
            "parallelize work, or adjust the date with documented trade-offs. "
            "Document decisions, update the plan, and run a short retrospective to prevent "
            "repeat slips."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("c3000003-0003-4000-8000-000000000002"),
        role_category="Project Manager",
        question_text="What is the purpose of a RACI matrix?",
        scraped_ideal_answer=(
            "A RACI clarifies who is Responsible, Accountable, Consulted, and Informed "
            "for each task or deliverable. It reduces duplicated work, prevents gaps in "
            "ownership, and speeds decision-making by making roles explicit across teams."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000001"),
        role_category="Java Automation Testing",
        question_text=(
            "What is the Page Object Model in Selenium with Java, and why use it?"
        ),
        scraped_ideal_answer=(
            "The Page Object Model (POM) represents each page or major UI fragment as a "
            "Java class that exposes methods and locators instead of scattering raw XPath "
            "or CSS across tests. Tests call high-level actions like `loginPage.signIn(user, pass)` "
            "so when the UI changes you update one class, not every test. It improves "
            "readability, reuse, and maintenance for larger automation suites."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000002"),
        role_category="Java Automation Testing",
        question_text=(
            "How would you reduce flaky tests in a Java + Selenium (or similar) suite?"
        ),
        scraped_ideal_answer=(
            "Flakiness often comes from timing, environment, or unstable locators. Use "
            "explicit waits tied to expected conditions instead of fixed sleeps, stabilize "
            "locators (IDs, data-test attributes), run tests in isolated order or with "
            "clean data, retry only where appropriate with logging, and quarantine or fix "
            "chronically flaky tests rather than ignoring failures. CI parallelism and "
            "screenshots/logs help diagnose race conditions."
        ),
        source_url="seed:curated",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000003"),
        role_category="Java Automation Testing",
        question_text=(
            "Explain implicit wait vs explicit wait in Selenium WebDriver with Java."
        ),
        scraped_ideal_answer=(
            "Implicit wait tells the driver to poll for elements for up to N seconds "
            "whenever it searches the DOM; it applies globally and can interact badly with "
            "explicit waits if overused. Explicit wait uses `WebDriverWait` with "
            "`ExpectedConditions` (or custom predicates) for a specific element or state, "
            "so you wait only where needed and fail fast with clear timeouts. Best practice "
            "is usually prefer explicit waits for stability and predictability."
        ),
        source_url="seed:curated",
    ),
)


def main() -> None:
    from app import create_app
    from app.models import Question

    app = create_app()
    Session = app.extensions["Session"]
    with app.app_context():
        s = Session()
        for row in ROWS:
            existing = s.get(Question, row.question_id)
            if existing:
                continue
            s.add(
                Question(
                    question_id=row.question_id,
                    role_category=row.role_category,
                    question_text=row.question_text,
                    scraped_ideal_answer=row.scraped_ideal_answer,
                    source_url=row.source_url,
                )
            )
        s.commit()
        print(f"Seeded {len(ROWS)} questions (skipped existing).")


if __name__ == "__main__":
    main()
