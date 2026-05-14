# Contributing to Release Dashboard Application

Thank you for contributing! This guide explains how to work with this project.

## Code Standards

### Python Code Style

- **Formatter**: Use `black` for automatic code formatting
- **Linter**: Pass `flake8` and `pylint` checks
- **Naming Conventions**:
  - Functions and variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
- **Docstrings**: Use triple-quoted strings for all public functions and classes
- **Comments**: Explain "why", not "what" (code should be self-documenting)

### Python Example

```python
def convert_csv_to_json(input_path: str, output_path: str) -> bool:
    """
    Convert CSV file to JSON format.

    Args:
        input_path: Path to input CSV file
        output_path: Path to output JSON file

    Returns:
        True if conversion successful, False otherwise
    """
    # Convert the file
    return True
```

### HTML/CSS Style

- **Formatting**: Use 4-space indentation
- **Classes**: Use kebab-case (e.g., `incident-table`, `status-badge`)
- **Comments**: Document complex sections with descriptive comments

## Branch Naming

Use conventional branch names:

```
feature/description        # New feature
bugfix/description         # Bug fix
docs/description           # Documentation changes
refactor/description       # Refactoring
test/description          # Test additions
```

Example: `feature/add-export-to-csv`, `bugfix/fix-date-parsing`

## Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]
[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `test`: Adding or updating tests
- `chore`: Build, dependencies, configuration

**Examples**:

```
feat(converter): add support for UTF-8-sig encoding
fix(dashboard): correct date parsing for AM/PM times
docs: update quickstart with new directory structure
test(converter): add validation tests for required fields
```

## Pull Request Process

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Write/update code**: Follow code standards above
3. **Write tests**: Ensure new code has tests
4. **Run tests locally**: `pytest tests/ -v --cov=src`
5. **Run linting**:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   pylint src/ tests/
   ```
6. **Commit with message**: `git commit -m "feat: your change description"`
7. **Push to remote**: `git push origin feature/your-feature`
8. **Create PR**: Include description of changes, testing done, any breaking changes
9. **Wait for review**: Address feedback from reviewers
10. **Merge**: Once approved and CI passes, merge to main

## Testing Requirements

- **Coverage**: Minimum 80% code coverage required
- **Tests locations**:
  - Unit tests: `tests/unit/`
  - Integration tests: `tests/integration/`
  - Test fixtures: `tests/fixtures/`

### Running Tests

```bash
# Run all tests with coverage report
pytest tests/ -v --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_converter.py::test_encoding_detection -v

# Run tests matching pattern
pytest tests/ -k "converter" -v

# Run with detailed output
pytest tests/ -vv -s
```

### Writing Tests

Use pytest conventions:

```python
def test_converter_handles_utf8_encoding():
    """Test that converter correctly handles UTF-8 encoded CSV files."""
    # Arrange: Set up test data
    input_file = "tests/fixtures/sample_utf8.csv"
    expected_count = 10

    # Act: Run the conversion
    result = convert_csv_to_json(input_file, output_file)

    # Assert: Verify results
    assert result is True
    assert len(loaded_json) == expected_count
```

## Documentation

### When to Write Documentation

- New features: Add to relevant docs
- API changes: Update docs/API.md
- Setup changes: Update docs/DEVELOPMENT.md
- Deployment changes: Update docs/DEPLOYMENT.md

### Documentation Format

- Use Markdown
- Include code examples where helpful
- Keep examples tested and working
- Update links when moving files

## Security

### Secrets Management

**NEVER** commit:
- `.env` files (git-ignored automatically)
- API keys or credentials
- Passwords or tokens
- Private configuration

**Always**:
- Use `.env.example` for template variables
- Store production secrets in GitHub Secrets
- Run pre-commit hook: `config/pre-commit-hook.sh`

### Pre-commit Hook

The pre-commit hook automatically prevents committing:

```bash
# Install hook (one-time setup)
./scripts/deploy/install-hooks.sh

# Run manually
bash config/pre-commit-hook.sh
```

## Performance Considerations

- Dashboard load time target: < 2 seconds
- Converter throughput: 1000+ records/second
- Support 10,000+ incidents in memory

Profile code before optimizing:

```bash
python -m cProfile -s cumulative src/converters/convert_incidents.py data/input/sample.csv
```

## Release Process

1. Update VERSION file with new semantic version (MAJOR.MINOR.PATCH)
2. Update CHANGELOG.md with release notes
3. Create git tag: `git tag v0.2.0`
4. Push tags: `git push origin v0.2.0`
5. Create GitHub release with notes

Example semantic versioning:
- `0.1.0` → `0.2.0` (Minor: new features, backward compatible)
- `0.2.0` → `0.2.1` (Patch: bug fix only)
- `0.2.1` → `1.0.0` (Major: breaking changes)

## Questions?

- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
- Review [DIRECTORY-STRUCTURE.md](../DIRECTORY-STRUCTURE.md) for file organization
- Read existing code for patterns and conventions

## Code of Conduct

- Be respectful and constructive
- Assume good intentions
- Help others learn and grow
- Focus on the work, not the person

---

**Last Updated**: 2026-05-14
