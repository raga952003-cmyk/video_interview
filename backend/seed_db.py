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
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000004"),
        role_category="Java Automation Testing",
        question_text="What is the difference between == and .equals() in Java?",
        scraped_ideal_answer=(
            "`==` compares object references (same memory address). `.equals()` compares "
            "logical equality of values when overridden (e.g. String content). In automation, "
            "use `.equals()` for comparing expected vs actual text from the UI."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000005"),
        role_category="Java Automation Testing",
        question_text="What are the advantages of using Java for automation testing?",
        scraped_ideal_answer=(
            "Java is platform-independent, has mature frameworks (Selenium, TestNG, JUnit), "
            "strong libraries (POI for Excel, Rest Assured for APIs), good IDE support, and a "
            "large community—making it a default choice for enterprise test automation."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000006"),
        role_category="Java Automation Testing",
        question_text="How do try, catch, and finally work in Java for handling test failures?",
        scraped_ideal_answer=(
            "`try` wraps code that may throw, `catch` handles specific exceptions (e.g. "
            "TimeoutException, NoSuchElementException), and `finally` runs cleanup such as "
            "quitting the driver or closing files whether or not an error occurred."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000007"),
        role_category="Java Automation Testing",
        question_text="What is a fluent wait in Selenium, and how does it differ from explicit wait?",
        scraped_ideal_answer=(
            "Fluent wait (in older APIs) configures max wait time and polling interval before "
            "re-checking a condition. Explicit wait (`WebDriverWait` + `ExpectedConditions`) "
            "waits until a condition is met or a timeout occurs—both are preferable to fixed "
            "`Thread.sleep` for stability."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000008"),
        role_category="Java Automation Testing",
        question_text="How do you read test data from Excel in Java?",
        scraped_ideal_answer=(
            "Typically Apache POI: open the workbook (`XSSFWorkbook` for .xlsx), select a sheet, "
            "read rows/cells into data structures, and feed rows into parameterized tests "
            "(TestNG `@DataProvider` or JUnit equivalents) for data-driven automation."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000009"),
        role_category="Java Automation Testing",
        question_text="Explain hard vs soft assertions in TestNG.",
        scraped_ideal_answer=(
            "Hard assertions (`Assert.assert*`) stop the test on first failure. Soft assertions "
            "(`SoftAssert`) collect failures and report them at `assertAll()`, useful when you "
            "want to validate many UI fields in one test without stopping at the first mismatch."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000010"),
        role_category="Java Automation Testing",
        question_text="How would you perform API testing using Java?",
        scraped_ideal_answer=(
            "Common approach: Rest Assured to send GET/POST/PUT/DELETE, assert status codes, "
            "headers, and JSON body (JsonPath or Hamcrest). Integrate with TestNG/JUnit and CI "
            "for regression of services behind the UI."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000011"),
        role_category="Java Automation Testing",
        question_text="What is functional vs non-functional testing?",
        scraped_ideal_answer=(
            "Functional testing checks behavior against requirements (login, workflows). "
            "Non-functional covers performance, security, reliability, usability (load, stress, "
            "accessibility). Automation often focuses on functional regression plus selected "
            "non-functional checks (e.g. basic performance gates)."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000012"),
        role_category="Java Automation Testing",
        question_text="How do you handle browser alerts and pop-ups in Selenium WebDriver?",
        scraped_ideal_answer=(
            "Use `driver.switchTo().alert()` to get an `Alert`, then `getText()`, `accept()`, or "
            "`dismiss()`. For non-JS dialogs (e.g. file chooser), use different strategies "
            "(AutoIt, robot, or avoiding native dialogs in tests)."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000013"),
        role_category="Java Automation Testing",
        question_text="What are common automation challenges and how do you address them?",
        scraped_ideal_answer=(
            "Dynamic locators and timing → explicit waits and stable selectors (data-testid). "
            "Flaky tests → isolation, retries with logging, root-cause fixes. Maintenance → POM, "
            "reuse, coding standards. Environment drift → containerized or consistent CI agents."
        ),
        source_url="https://www.geeksforgeeks.org/software-testing/automation-testing-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000014"),
        role_category="Java Automation Testing",
        question_text="What is the difference between Selenium RC and WebDriver?",
        scraped_ideal_answer=(
            "Selenium RC is deprecated: it injected JavaScript into the browser. WebDriver "
            "drives the browser through vendor drivers (W3C WebDriver protocol), giving more "
            "stable, faster control—always use WebDriver for new projects."
        ),
        source_url="https://www.vskills.in/interview-questions/selenium-automation-tester-using-java-interview-questions",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000015"),
        role_category="Java Automation Testing",
        question_text="What is TestNG and why is it used with Selenium?",
        scraped_ideal_answer=(
            "TestNG is a Java testing framework providing annotations, parallel execution, "
            "grouping, dependency ordering, and reporting. It integrates cleanly with Selenium "
            "for structured suites and CI pipelines."
        ),
        source_url="https://staragile.com/blog/automation-testing-interview-questions-answers",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000016"),
        role_category="Java Automation Testing",
        question_text="How do you run Selenium tests in parallel with Java?",
        scraped_ideal_answer=(
            "Use TestNG `parallel` (methods/classes/suites) with a thread-safe driver pattern "
            "(e.g. ThreadLocal WebDriver), or JUnit 5 parallel config. Ensure tests do not share "
            "mutable state or the same browser instance across threads."
        ),
        source_url="https://staragile.com/blog/automation-testing-interview-questions-answers",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000017"),
        role_category="Java Automation Testing",
        question_text="What is the difference between driver.findElement and findElements?",
        scraped_ideal_answer=(
            "`findElement` returns the first matching element or throws "
            "`NoSuchElementException`. `findElements` returns a list (possibly empty). Use "
            "`findElements` when checking optional UI elements without failing immediately."
        ),
        source_url="https://www.geeksforgeeks.org/software-testing/automation-testing-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000018"),
        role_category="Java Automation Testing",
        question_text="How would you integrate Java automation tests with Jenkins or CI/CD?",
        scraped_ideal_answer=(
            "Run Maven/Gradle in a pipeline stage, publish JUnit/TestNG XML results, archive "
            "screenshots/videos on failure, parameterize browser/OS via agents or Selenium Grid, "
            "and gate merges on stable smoke suites."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000019"),
        role_category="Java Automation Testing",
        question_text="What is reflection in Java and when might it appear in test tooling?",
        scraped_ideal_answer=(
            "Reflection inspects or invokes classes/methods at runtime via the `Class` API. "
            "Frameworks (Spring, some runners) use it; in tests it is rarely needed unless "
            "testing legacy code or building custom runners—prefer public APIs when possible."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001a"),
        role_category="Java Automation Testing",
        question_text="How do you verify a file download using Selenium and Java?",
        scraped_ideal_answer=(
            "Options: configure browser download directory, wait for file to appear with "
            "FluentWait on the filesystem, assert size/name; or intercept download URL via network "
            "or API instead of UI when possible. Avoid OS-native dialogs that Selenium cannot control."
        ),
        source_url="https://hirist.tech/blog/top-40-java-automation-testing-interview-questions-and-answers/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001b"),
        role_category="Java Automation Testing",
        question_text="What is WebDriverManager (or similar) used for?",
        scraped_ideal_answer=(
            "It resolves and caches matching browser drivers (ChromeDriver, etc.) for the "
            "installed browser version, avoiding manual PATH setup—speeding local and CI setup."
        ),
        source_url="https://www.geeksforgeeks.org/software-testing/automation-testing-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001c"),
        role_category="Java Automation Testing",
        question_text="What is the difference between quit() and close() on WebDriver?",
        scraped_ideal_answer=(
            "`close()` closes the current window/tab; `quit()` ends the session and closes all "
            "windows and the driver process. Always `quit()` in teardown to avoid zombie "
            "browser processes in CI."
        ),
        source_url="https://www.vskills.in/interview-questions/selenium-automation-tester-using-java-interview-questions",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001d"),
        role_category="Java Automation Testing",
        question_text="What are XPath axes and when would you use them in Selenium?",
        scraped_ideal_answer=(
            "Axes (ancestor, following-sibling, etc.) navigate the DOM tree in XPath. Use when "
            "elements lack stable IDs; prefer shorter, resilient paths and combine with "
            "contains/text() carefully to reduce brittleness."
        ),
        source_url="https://staragile.com/blog/automation-testing-interview-questions-answers",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001e"),
        role_category="Java Automation Testing",
        question_text="What is BDD and how does Cucumber fit with Java automation?",
        scraped_ideal_answer=(
            "Behavior-Driven Development uses Given/When/Then specs (often Gherkin). Cucumber "
            "binds steps to Java methods so stakeholders can read scenarios while tests remain "
            "executable in CI."
        ),
        source_url="https://staragile.com/blog/automation-testing-interview-questions-answers",
    ),
    # --- Additional bank: Java + Maven + TestNG + Cucumber + Rest Assured + Selenium (curated; topic-aligned) ---
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000001f"),
        role_category="Java Automation Testing",
        question_text="What is pom.xml in Maven and what are the main lifecycle phases?",
        scraped_ideal_answer=(
            "`pom.xml` is the Project Object Model: project coordinates, dependencies, plugins, "
            "and build configuration. Default lifecycle phases include validate, compile, test, "
            "package, verify, install, and deploy—`mvn test` runs unit tests after compiling test "
            "sources; `mvn clean install` cleans, builds, runs tests, and installs the artifact "
            "to the local repository."
        ),
        source_url="https://www.javatpoint.com/maven-interview-questions",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000020"),
        role_category="Java Automation Testing",
        question_text="What is Maven dependency scope compile vs test vs provided?",
        scraped_ideal_answer=(
            "`compile` (default) is on the classpath for main and test. `test` is only for test "
            "compilation and execution (e.g. TestNG, JUnit). `provided` is expected at runtime "
            "from the container (e.g. servlet API) and is not packaged into the fat JAR—important "
            "when choosing what ships to CI agents."
        ),
        source_url="https://www.javatpoint.com/maven-interview-questions",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000021"),
        role_category="Java Automation Testing",
        question_text="In Cucumber, what is a feature file and how does it map to Java?",
        scraped_ideal_answer=(
            "A `.feature` file holds Gherkin scenarios (Feature, Scenario, Given/When/Then). "
            "Cucumber matches steps to glue code: Java methods annotated with regex or Cucumber "
            "expressions, often in a `steps` package, with shared state injected via PicoContainer "
            "or Spring if used."
        ),
        source_url="https://www.geeksforgeeks.org/cucumber-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000022"),
        role_category="Java Automation Testing",
        question_text="What are Cucumber tags and hooks (@Before, @After)?",
        scraped_ideal_answer=(
            "Tags (e.g. `@smoke`, `@regression`) label scenarios or features so you can filter "
            "runs from the runner or CI. Hooks run setup/teardown around scenarios or steps—"
            "`@Before`/`@After` in Java open/close browser or reset test data so scenarios stay "
            "isolated."
        ),
        source_url="https://www.geeksforgeeks.org/cucumber-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000023"),
        role_category="Java Automation Testing",
        question_text="What TestNG annotations would you use for setup, test, and teardown?",
        scraped_ideal_answer=(
            "Common pattern: `@BeforeSuite`/`@AfterSuite` for global resources, `@BeforeClass`/"
            "`@AfterClass` once per class, `@BeforeMethod`/`@AfterMethod` around each `@Test`, "
            "plus `@Test` with attributes like `priority`, `groups`, `dependsOnMethods`, and "
            "`dataProvider` for data-driven runs."
        ),
        source_url="https://www.tutorialspoint.com/testng/testng_interview_questions.htm",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000024"),
        role_category="Java Automation Testing",
        question_text="How does TestNG @DataProvider work for data-driven Selenium tests?",
        scraped_ideal_answer=(
            "A `@DataProvider` method returns a 2D `Object[][]` (or `Iterator`) of argument sets. "
            "`@Test(dataProvider = \"name\")` runs the test once per row—ideal for login datasets "
            "from Excel/CSV. For parallel data-driven runs, combine with suite parallel settings "
            "and thread-safe drivers."
        ),
        source_url="https://www.tutorialspoint.com/testng/testng_interview_questions.htm",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000025"),
        role_category="Java Automation Testing",
        question_text="How do you write a basic Rest Assured test in Java for a JSON API?",
        scraped_ideal_answer=(
            "Use fluent API: `given()` for headers/query/body, `when()` for HTTP verb and path, "
            "`then()` for assertions—e.g. `given().contentType(JSON).when().get(\"/users/1\")`."
            "`then().statusCode(200).body(\"name\", equalTo(\"...\"))` with Hamcrest or JsonPath. "
            "Reuse request specs and enable logging for failures in CI."
        ),
        source_url="https://github.com/rest-assured/rest-assured/wiki/Usage",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000026"),
        role_category="Java Automation Testing",
        question_text="What is Selenium Grid and how do Hub and Nodes relate?",
        scraped_ideal_answer=(
            "Grid distributes tests across browsers/OS: the Hub routes sessions; Nodes register "
            "capabilities (Chrome, Firefox, version). Tests point `RemoteWebDriver` at the Hub URL "
            "with desired capabilities so CI can scale parallel UI runs without one machine "
            "running every browser."
        ),
        source_url="https://www.softwaretestingmaterial.com/selenium-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000027"),
        role_category="Java Automation Testing",
        question_text="What is JavascriptExecutor in Selenium and when would you use it?",
        scraped_ideal_answer=(
            "`((JavascriptExecutor) driver).executeScript(...)` runs JS in the page context—"
            "use sparingly for scrolling, clicking hidden elements, or setting values when "
            "no stable WebDriver API exists. Prefer normal interactions first; document JS "
            "hacks because they can break across browsers and frameworks."
        ),
        source_url="https://www.edureka.co/blog/interview-questions/selenium-interview-questions/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000028"),
        role_category="Java Automation Testing",
        question_text="What is visual regression testing and how does it differ from functional UI checks?",
        scraped_ideal_answer=(
            "Functional checks assert behavior (text, navigation). Visual regression compares "
            "screenshots (full page or components) to baselines to catch unintended layout/CSS "
            "changes—tools like Applitools add AI-assisted diffing and run at scale. Use it for "
            "stable UIs where pixel-level drift matters alongside traditional assertions."
        ),
        source_url="https://testautomationuniversity.applitools.com/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-000000000029"),
        role_category="Java Automation Testing",
        question_text="Why use a BaseTest (or similar) class in a Selenium Java framework?",
        scraped_ideal_answer=(
            "Centralize driver creation, implicit/explicit wait defaults, base URL, window size, "
            "and teardown (`quit`) in `@BeforeMethod`/`@AfterMethod` so tests stay DRY. Subclasses "
            "focus on scenarios; you can swap local vs Grid URL from config or environment variables."
        ),
        source_url="https://github.com/shadabansari/Selenium-Java-Framework",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000002a"),
        role_category="Java Automation Testing",
        question_text="Explain Java encapsulation and why private fields with getters matter in page objects.",
        scraped_ideal_answer=(
            "Encapsulation hides internal state behind methods. In page objects, keep locators "
            "and low-level WebElement fields private and expose intent-based methods—callers "
            "cannot break invariants or depend on raw DOM details, improving maintainability."
        ),
        source_url="https://www.guru99.com/java-interview-questions-answers.html",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000002b"),
        role_category="Java Automation Testing",
        question_text="When would you use StringBuilder instead of String concatenation in Java test code?",
        scraped_ideal_answer=(
            "Strings are immutable—repeated `+` in loops creates many intermediate objects. "
            "`StringBuilder` mutates a buffer and is better for building log messages, dynamic "
            "XPath snippets, or large payloads in performance-sensitive test utilities."
        ),
        source_url="https://www.geeksforgeeks.org/top-50-java-coding-problems-for-interviews/",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000002c"),
        role_category="Java Automation Testing",
        question_text="What Java collections would you use for unique test IDs vs ordered test steps?",
        scraped_ideal_answer=(
            "`Set` (e.g. `HashSet`) enforces uniqueness and fast membership—good for deduping "
            "IDs or URLs. `List` preserves order for sequential steps. `Map` (e.g. `HashMap`) "
            "maps keys to values for environment config, row data, or API response fields in "
            "assertions."
        ),
        source_url="https://github.com/itv-github/Java-Interview-Questions",
    ),
    Row(
        question_id=uuid.UUID("d4000004-0004-4000-8000-00000000002d"),
        role_category="Java Automation Testing",
        question_text="What is method overloading vs overriding in Java (common in interview coding)?",
        scraped_ideal_answer=(
            "Overloading: same method name, different parameter lists in one class—resolved at "
            "compile time. Overriding: subclass replaces a superclass instance method with the "
            "same signature—resolved at runtime (dynamic dispatch). Know this for reading "
            "framework APIs and writing clean test utilities."
        ),
        source_url="https://www.hackerrank.com/domains/java",
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
