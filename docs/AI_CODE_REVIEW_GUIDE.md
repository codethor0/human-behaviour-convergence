# AI-Powered Code Review Guide
**Project:** Human Behavior Convergence
**Last Updated:** November 5, 2025
**Purpose:** Comprehensive guide for using AI assistants to review and improve code quality

---

## Table of Contents
1. [Introduction](#introduction)
2. [Universal Code Review Template](#universal-code-review-template)
3. [Language-Specific Review Templates](#language-specific-review-templates)
4. [Integration with Development Workflow](#integration-with-development-workflow)
5. [Specialized Review Types](#specialized-review-types)
6. [Best Practices](#best-practices)
7. [Examples from This Repository](#examples-from-this-repository)

---

## Introduction

This guide provides a framework for using AI assistants (GitHub Copilot, ChatGPT, Claude, etc.) to perform comprehensive code reviews. It's based on industry best practices and tailored for this repository's technology stack:

- **Backend:** Python 3.12+, FastAPI, Pandas
- **Frontend:** TypeScript, Next.js, React
- **Infrastructure:** Mermaid diagrams, GitHub Actions
- **Testing:** pytest, pytest-cov, FastAPI TestClient

### Benefits of AI Code Review

**Consistency** - Same review criteria applied across all code
**Speed** - Instant feedback on pull requests
**Education** - Learn best practices through AI explanations
**Complementary** - Augments (not replaces) human review---

## Universal Code Review Template

Use this template as a foundation for all code reviews. Copy and customize as needed.

### Basic Template

This template provides a structured approach to code review. Use it as a framework when conducting reviews or requesting reviews from team members.

**Review Context:**
- **Language:** [Python/TypeScript/etc.]
- **Framework:** [FastAPI/Next.js/etc.]
- **Purpose:** [What this code does]
- **Environment:** [Production/Development/Test]

**Code to Review:**
```[language]
[paste code here]
```

**Review Checklist:**
Analyze the code for:

1. **Logic & Correctness**
   - Are there any bugs or logic errors?
   - Does it handle edge cases?
   - Are there off-by-one errors or race conditions?

2. **Security**
   - Input validation and sanitization
   - SQL injection, XSS, CSRF vulnerabilities
   - Hardcoded secrets or credentials
   - Authentication/authorization issues

3. **Performance**
   - Algorithmic complexity (time/space)
   - Inefficient loops or nested operations
   - Missing caching opportunities
   - Resource management (memory leaks, connection pools)

4. **Code Quality**
   - Adherence to style guide (PEP 8, Airbnb, etc.)
   - Readability and maintainability
   - Documentation (docstrings, comments)
   - DRY, SOLID principles

5. **Error Handling**
   - Proper exception handling
   - Meaningful error messages
   - Appropriate HTTP status codes (if API)
   - Logging for debugging

**Output Format:**
For each issue found:
- **Category:** [Logic/Security/Performance/Quality/Error Handling]
- **Severity:** [Critical/High/Medium/Low]
- **Location:** [Line number or function name]
- **Issue:** [Clear description]
- **Why:** [Explanation of the problem]
- **Fix:** [Corrected code snippet]
```

---

## Language-Specific Review Templates

### Python / FastAPI

```markdown
# Additional Python-Specific Checks
- PEP 8 compliance (use black, isort)
- Type hints on all function signatures
- Docstrings (Google or NumPy style)
- Pythonic constructs (list comprehensions, context managers)
- Proper exception handling (don't use bare `except:`)
- Use of `raise...from` for exception chaining
- Asyncio best practices (for async endpoints)

# FastAPI-Specific
- Dependency injection usage
- Pydantic model validation
- Response model schemas
- Proper HTTP status codes
- CORS configuration
- Authentication middleware
```

**Example Review Checklist for This Repository:**

```markdown
Review this FastAPI endpoint for:
- Proper error handling with HTTPException
- Input validation (limit parameter should be >=0)
- CSV parsing error handling
- Cache management and memory safety
- Type hints and docstrings
- Test coverage gaps
```

### TypeScript / Next.js

```markdown
# Additional TypeScript Checks
- Strong typing (avoid `any` types)
- Proper use of interfaces vs types
- Null/undefined handling
- ESLint compliance
- React hooks dependencies
- Async/await error handling

# Next.js-Specific
- Server vs client component usage
- API route security
- Data fetching patterns (SSR/SSG/CSR)
- SEO optimization
- Performance (bundle size, lazy loading)
```

### Mermaid Diagrams

```markdown
# Diagram Review Checklist
- Syntax validity (test in mermaid.live)
- Logical flow correctness
- Completeness (all components represented)
- Clarity (readable labels, proper grouping)
- Consistency with codebase
- Accessibility (contrast, font size)
```

---

## Integration with Development Workflow

### 1. GitHub Copilot Integration

#### In-IDE Suggestions
Use comments to trigger Copilot assistance:

```python
# @copilot review this function for security vulnerabilities
def process_user_input(data: str):
    ...

# @copilot suggest performance improvements
def calculate_metrics(df: pd.DataFrame):
    ...
```

#### Copilot Chat
Open Copilot Chat and ask:
- `@workspace What is the attack surface of this API?`
- `Are there any security vulnerabilities in /api/forecasts?`
- `How can I improve the test coverage for main.py?`

### 2. ChatGPT / Claude Integration

#### Pull Request Review
1. Copy the PR diff
2. Use this review template:

```markdown
Review this pull request for a Python FastAPI backend:

**Context:** Population forecasting API with CSV data sources

**Changes:**
```diff
[paste git diff here]
```

**Focus areas:**
- Breaking changes
- Security implications
- Test coverage adequacy
- Performance impact
```

#### Pre-Commit Review
Before committing, run:
```bash
git diff | pbcopy  # Copy diff to clipboard
# Paste into code review tool with review template
```

### 3. GitHub Actions Automation

This repository uses automated quality gates (`.github/workflows/quality-gates.yml`):

-  Test coverage ≥70%
-  Cyclomatic complexity avg ≤10
-  Maintainability index ≥20
-  Pylint score ≥7.0
-  Bandit security scan (no high severity)

**To add AI review to CI:**

```yaml
# .github/workflows/ai-code-review.yml
name: AI Code Review
on: [pull_request]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: AI Code Review
        uses: some-org/ai-code-review-action@v1
        with:
          ai_model: gpt-4
          api_key: ${{ secrets.OPENAI_API_KEY }}
          focus: security,performance,bugs
```

*(Note: Replace with actual AI review action from GitHub Marketplace)*

---

## Specialized Review Types

### Security-Focused Review

**Review Template:**
```markdown
Security-focused code review checklist:

**OWASP Top 10 focus:**
1. Injection attacks (SQL, NoSQL, command)
2. Broken authentication
3. Sensitive data exposure
4. XML external entities (XXE)
5. Broken access control
6. Security misconfiguration
7. XSS (cross-site scripting)
8. Insecure deserialization
9. Using components with known vulnerabilities
10. Insufficient logging & monitoring

For each finding, reference CVE/CWE and provide secure code example.
```

**Example from This Repository:**
```python
# Before (potential issue)
def _read_csv(name: str, limit: int = 1000):
    csv_path = RESULTS_DIR / name  # Path traversal risk?
    df = pd.read_csv(csv_path)

# After (improved)
def _read_csv(name: str, limit: int = 1000):
    # Validate filename to prevent path traversal
    if ".." in name or "/" in name:
        raise ValueError("Invalid filename")
    if limit < 0:
        raise ValueError("limit must be non-negative")
    csv_path = RESULTS_DIR / name
```

### Performance-Focused Review

**Review Template:**
```markdown
Performance-focused code review checklist:

1. **Algorithmic complexity:** Time/space complexity analysis
2. **Database queries:** N+1 problems, missing indexes
3. **Caching:** Opportunities for memoization/caching
4. **Resource usage:** Memory leaks, connection pooling
5. **Async opportunities:** Could this be async?

Provide before/after examples with performance impact estimates.
```

**Example from This Repository:**
```python
# Before: No caching (disk I/O on every request)
def get_forecasts():
    df = pd.read_csv("forecasts.csv")
    return df.to_dict(orient="records")

# After: 5-minute cache (10-100x faster)
_cache = {}
_cache_ttl = {}
CACHE_DURATION = timedelta(minutes=5)

def _read_csv(name: str, limit: int = 1000):
    cache_key = (name, limit)
    if cache_key in _cache and datetime.now() < _cache_ttl[cache_key]:
        return _cache[cache_key]  # Cache hit
    # ... read CSV ...
    _cache[cache_key] = result
    _cache_ttl[cache_key] = datetime.now() + CACHE_DURATION
    return result
```

### Debugging-Focused Review

**Review Template:**
```markdown
Debugging-focused review checklist:

**Error message:**
```
[paste error/stack trace]
```

**Code:**
```python
[paste problematic code]
```

**Steps:**
1. Walk through the function line by line
2. Track variable values at each step
3. Identify where the logic breaks down
4. Suggest a fix with explanation
```

---

## Best Practices

### 1. Review Template Engineering

 **DO:**
- Be specific: "Check for SQL injection" > "Review security"
- Provide context: language, framework, purpose
- Ask for explanations: "Why is this a problem?"
- Request examples: "Show me the corrected code"

 **DON'T:**
- Use vague requests: "Is this good?"
- Omit context: "Review this code" (which language?)
- Accept suggestions blindly: Always verify recommendations
- Skip human review: Automated tools augment, don't replace human judgment

### 2. Iterative Review

```
First pass:  Quick scan for critical issues (security, bugs)
Second pass: Performance and optimization
Third pass:  Code quality and style
Fourth pass: Documentation and tests
```

### 3. Combining AI with Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **AI (ChatGPT/Copilot)** | Semantic understanding, design review | Complex logic, architecture |
| **Pylint/ESLint** | Style and simple bugs | Pre-commit, CI |
| **Bandit/Snyk** | Security vulnerabilities | Pre-commit, CI |
| **pytest** | Functional correctness | Development, CI |
| **radon** | Complexity metrics | Pre-PR, refactoring |

### 4. Limitations & Risks

 **False Positives:** AI may flag valid code as problematic
 **False Negatives:** AI may miss subtle bugs
 **Context Limitations:** AI has limited understanding of business logic
 **Outdated Knowledge:** AI may suggest deprecated patterns

**Mitigation:**
- Always have a human review AI findings
- Run automated tests to verify AI suggestions
- Use multiple AI models for critical code
- Keep review templates updated with latest best practices

---

## Examples from This Repository

### Example 1: Cache Improvement

**Original Issue:** Unbounded cache could cause memory issues

**Review Checklist:**
```markdown
Review this caching implementation for memory safety:

```python
_cache: Dict[str, List[Dict]] = {}
_cache_ttl: Dict[str, datetime] = {}

def _read_csv(name: str, limit: int = 1000):
    cache_key = f"{name}:{limit}"
    if cache_key in _cache and datetime.now() < _cache_ttl[cache_key]:
        return _cache[cache_key]
    # ...
```

Issues to check:
- Unbounded growth
- Memory leaks
- Cache key collisions
- Eviction strategy
```

**AI Findings:**
1.  **No size limit** → cache grows unbounded
2.  **String cache keys** → potential collision if name contains `:`
3.  **No eviction** → expired entries stay in memory

**Applied Fix:**
```python
MAX_CACHE_SIZE = 100
_cache: Dict[tuple, List[Dict]] = {}  # Tuple keys avoid collisions

def _read_csv(name: str, limit: int = 1000):
    if limit < 0:
        raise ValueError("limit must be non-negative")

    cache_key = (name, limit)  # Tuple instead of string

    # Evict oldest entry if cache is full
    if len(_cache) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(_cache))
        _cache.pop(oldest_key)
        _cache_ttl.pop(oldest_key)

    # ...
```

**Result:**  Memory-safe caching with LRU-like eviction

### Example 2: Input Validation

**Original Issue:** Negative limit values not validated

**Review Checklist:**
```markdown
Check this function for input validation issues:

```python
def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)  # What if limit is negative?
```

**AI Findings:**
1.  `limit=-1` would return all rows (pandas behavior)
2.  `limit=0` would return empty DataFrame
3.  No explicit validation

**Applied Fix:**
```python
def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    """
    Args:
        limit: Maximum rows to return. Must be >= 0.

    Raises:
        ValueError: If limit is negative.
    """
    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")
    # ...
```

**Result:**  Explicit validation with clear error message

### Example 3: Test Coverage

**Review Checklist:**
```markdown
Current test coverage: 74% on app/backend/app/main.py

Uncovered lines:
- Lines 24: RESULTS_DIR = None case
- Lines 80-85: EmptyDataError exception
- Lines 106-109: FileNotFoundError exception
- Lines 119-122: pd.errors.ParserError exception

Generate pytest test cases to cover these lines.
```

**AI Generated Tests:**
```python
def test_csv_negative_limit_validation(temp_results_dir, monkeypatch):
    """Test that negative limit values are rejected."""
    with pytest.raises(ValueError, match="limit must be non-negative"):
        main._read_csv("forecasts.csv", limit=-1)

def test_cache_eviction(temp_results_dir, monkeypatch):
    """Test cache eviction when MAX_CACHE_SIZE exceeded."""
    monkeypatch.setattr(main, "MAX_CACHE_SIZE", 3)
    # Fill cache to max...
    # Verify oldest entry evicted
```

**Result:**  Coverage increased from 74% to 77%

---

## Quick Reference

### Pre-Commit Checklist
```bash
# 1. Run code review locally
git diff | pbcopy  # Copy changes
# Use code review tool with review template

# 2. Run automated checks
pytest tests/ --cov=app --cov-report=term
pylint app/ tests/
bandit -r app/

# 3. Pre-commit hooks (auto-runs)
git commit -m "feat: your message"
# black, isort, trailing-whitespace auto-fix

# 4. Push and check CI
git push
# GitHub Actions runs quality-gates.yml
```

### Emergency Security Review
```markdown
 Critical security review needed:

**Code:** [paste code]
**Context:** This handles user input / credentials / payment data
**Deployment:** Production in 24 hours

Focus on:
1. Injection attacks
2. Auth bypass
3. Data leaks
4. DoS vulnerabilities

Provide CVE references and OWASP Top 10 mapping.
```

### Quick Performance Check
```markdown
 Quick performance audit:

**Code:** [paste function]
**Problem:** Slow response time (>5s)
**Scale:** 10K requests/day

Check:
- Algorithmic complexity
- Database query count
- Missing indexes
- Caching opportunities
```

---

## Further Reading

- [OWASP Code Review Guide](https://owasp.org/www-project-code-review-guide/)
- [Google Engineering Practices - Code Review](https://google.github.io/eng-practices/review/)
- [PEP 8 - Python Style Guide](https://peps.python.org/pep-0008/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)

---

## Contributing

Found an issue with this guide or have suggestions?
1. Open an issue with the `documentation` label
2. Submit a PR to improve the examples
3. Share your AI code review experiences in Discussions

---

**Last Updated:** November 5, 2025
**Maintainer:** @codethor0
**License:** MIT
