#!/usr/bin/env python3
"""
Refactor tests to use pytest tmp_path instead of tests/test_data for outputs.

This script converts test files that write temporary JSON outputs to use
pytest's tmp_path fixture instead of hardcoded test_data directory paths.

Impact: Cleaner tests with no side effects, proper cleanup, parallelization support.
"""

import re
import sys
from pathlib import Path

# Test files that need refactoring
TEST_FILES_TO_FIX = [
    'tests/test_error_handling.py',
    'tests/test_performance.py',
    'tests/test_postmortem_e2e_conversion.py',
    'tests/test_postmortem_e2e_full.py',
    'tests/test_postmortem_normalization_integration.py',
]

def refactor_test_file(file_path):
    """Refactor a single test file to use tmp_path."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Add tmp_path parameter to test methods that don't have it
    # Pattern: def test_name(self): → def test_name(self, tmp_path):
    content = re.sub(
        r'def (test_\w+)\(self\):',
        r'def \1(self, tmp_path):',
        content
    )

    # 2. Replace hardcoded test_data output paths
    # Pattern: 'tests/test_data/name.json' → str(tmp_path / "name.json")
    # But only for output/error files (not input CSVs)

    # For convert_file output parameters, use tmp_path
    # Pattern: convert_file(input_csv, 'tests/test_data/output.json')
    content = re.sub(
        r"convert_file\(\s*'tests/test_data/[^']+\.csv',\s*'tests/test_data/([^']+\.json)'",
        r"convert_file(\n            'tests/test_data/valid-100.csv',\n            str(tmp_path / '\1')",
        content
    )

    # For error_report_path parameter
    content = re.sub(
        r",\s*'tests/test_data/([^']*_errors\.json)'",
        r",\n            str(tmp_path / '\1')",
        content
    )

    # 3. Replace Path('tests/test_data/...json') with tmp_path usage
    content = re.sub(
        r"error_file = Path\('tests/test_data/[^']*\.json'\)",
        r"error_file = tmp_path / 'errors.json'",
        content
    )

    content = re.sub(
        r"output_file = Path\('tests/test_data/[^']*\.json'\)",
        r"output_file = tmp_path / 'output.json'",
        content
    )

    return content if content != original_content else None

def main():
    """Main refactoring script."""
    print("=" * 80)
    print("Test Refactoring: tests/test_data → pytest tmp_path")
    print("=" * 80)

    refactored_count = 0

    for test_file in TEST_FILES_TO_FIX:
        test_path = Path(test_file)

        if not test_path.exists():
            print(f"⚠️  {test_file}: NOT FOUND")
            continue

        print(f"\n📝 Analyzing {test_file}...")
        refactored = refactor_test_file(test_path)

        if refactored:
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(refactored)
            print(f"✅ {test_file}: Refactored successfully")
            refactored_count += 1
        else:
            print(f"⏭️  {test_file}: No changes needed")

    print("\n" + "=" * 80)
    print(f"Refactored {refactored_count} test files")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review changes: git diff tests/")
    print("2. Run tests: pytest tests/ -v")
    print("3. Clean up test_data/ directory")
    print("4. Add tests/test_data/*.json to .gitignore")
    print("=" * 80)

if __name__ == '__main__':
    main()
