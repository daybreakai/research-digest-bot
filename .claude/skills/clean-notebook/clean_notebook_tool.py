#!/usr/bin/env python3
"""
Clean Notebook Tool - Removes teaching content while preserving technical content

Usage:
    python clean_notebook_tool.py path/to/notebook.ipynb [--dry-run]

Features:
- Removes diagnostic print blocks
- Strips emojis and decorative separators
- Removes verbose teaching markdown
- Preserves data contracts and technical content
- Creates automatic backup before applying changes
- Shows preview of changes before applying
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import shutil


class ImportOrganizer:
    """Organize and consolidate imports in a notebook."""

    STDLIB_MODULES = {
        'sys', 'os', 'json', 're', 'pathlib', 'typing', 'collections', 'itertools',
        'functools', 'operator', 'datetime', 'time', 'random', 'math', 'statistics',
        'io', 'pickle', 'csv', 'configparser', 'logging', 'warnings', 'inspect',
        'copy', 'pprint', 'enum', 'dataclasses', 'abc', 'contextlib', 'urllib',
    }

    def extract_imports(self, notebook: Dict) -> Dict[str, List[str]]:
        """Extract all imports from notebook code cells."""
        imports = {
            'future': [],
            'stdlib': [],
            'third_party': [],
            'local': [],
        }

        seen = set()

        for cell in notebook['cells']:
            if cell['cell_type'] != 'code':
                continue

            source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

            for line in source.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Future imports
                if line.startswith('from __future__'):
                    if line not in seen:
                        imports['future'].append(line)
                        seen.add(line)
                # Local imports
                elif line.startswith('from src') or line.startswith('from .') or line.startswith('from ..'):
                    if line not in seen:
                        imports['local'].append(line)
                        seen.add(line)
                # Standard library
                elif line.startswith(('import ', 'from ')):
                    # Extract module name
                    if line.startswith('from '):
                        module = line.split()[1]
                    else:
                        module = line.split()[1]

                    # Check if stdlib
                    if module in self.STDLIB_MODULES:
                        if line not in seen:
                            imports['stdlib'].append(line)
                            seen.add(line)
                    else:
                        if line not in seen:
                            imports['third_party'].append(line)
                            seen.add(line)

        return imports

    def create_import_cell(self, imports: Dict[str, List[str]]) -> Dict:
        """Create organized import cell."""
        source_lines = []

        for category in ['future', 'stdlib', 'third_party', 'local']:
            if imports[category]:
                source_lines.extend(imports[category])
                if category != 'local':
                    source_lines.append('')  # Blank line between categories

        cell = {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [line + '\n' if i < len(source_lines) - 1 else line
                      for i, line in enumerate(source_lines)],
        }
        return cell

    def remove_imports_from_cells(self, notebook: Dict) -> None:
        """Remove import statements from all code cells."""
        for cell in notebook['cells']:
            if cell['cell_type'] != 'code':
                continue

            source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
            lines = source.split('\n')
            cleaned_lines = [line for line in lines if not line.strip().startswith(('import ', 'from '))]

            cell['source'] = [line + '\n' if i < len(cleaned_lines) - 1 else line
                             for i, line in enumerate(cleaned_lines)]


class CommentExtractor:
    """Extract verbose comments and move to markdown cells."""

    def find_verbose_comments(self, notebook: Dict) -> List[Dict]:
        """Find verbose comments in code cells."""
        comments = []

        for cell_idx, cell in enumerate(notebook['cells']):
            if cell['cell_type'] != 'code':
                continue

            source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
            lines = source.split('\n')

            current_block = []
            for line_idx, line in enumerate(lines):
                if '#' in line:
                    comment_part = line.split('#', 1)[1].strip()
                    if len(comment_part) > 40:
                        current_block.append({
                            'cell': cell_idx,
                            'line': line_idx,
                            'text': comment_part,
                        })
                elif current_block and not line.strip().startswith('#'):
                    if len(current_block) >= 1:
                        comments.append({
                            'cells': [c['cell'] for c in current_block],
                            'blocks': current_block,
                        })
                    current_block = []

        return comments

    def extract_comment_text(self, comment: Dict) -> str:
        """Extract comment text for markdown."""
        blocks = comment['blocks']
        texts = [b['text'] for b in blocks]
        return '\n'.join(texts)


class NotebookCleaner:
    """Clean Jupyter notebooks by removing teaching content."""

    # Patterns to identify content for removal
    EMOJI_PATTERN = re.compile(
        r'[\U0001F300-\U0001F9FF]'  # Emoji ranges
        r'|✓|✗|📊|📈|📉|⚠️|💡|🎯|🚀|🔄|⏳|🔍|✅|❌'  # Common emoji symbols
    )

    DIAGNOSTIC_PHRASES = [
        "DIAGNOSTIC:",
        "Python Environment",
        "sys.executable",
        "sys.path",
        "PROJECT_ROOT",
        "Module.*Import",
    ]

    TEACHING_PHRASES = [
        "What's in this notebook",
        "Key Concept:",
        "Rule of thumb:",
        "Let's",
        "Why this matters",
        "Let me explain",
        "Consider the following",
        "Here's an example",
        "In this section",
        "we're going to",
        "the purpose of",
        "order matters",
        "this is non-negotiable",
        "Portfolio averages hide",
    ]

    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.backup_path = self.notebook_path.with_suffix(self.notebook_path.suffix + ".backup")

        if not self.notebook_path.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")

        # Load notebook
        with open(self.notebook_path, 'r') as f:
            self.notebook = json.load(f)

    def is_diagnostic_block(self, cell_text: str) -> bool:
        """Check if cell is a diagnostic print block."""
        if 'print' not in cell_text:
            return False

        # Check for diagnostic keywords
        diagnostic_keywords = [
            'DIAGNOSTIC:',
            'Python Environment',
            'sys.executable',
            'sys.path',
            'PROJECT_ROOT exists',
        ]

        has_diagnostic = any(keyword.lower() in cell_text.lower() for keyword in diagnostic_keywords)

        # Check for separator patterns in print statements
        # Patterns like: print("=" * 70), print("-" * 60), print("=" * 80)
        has_separator = (
            'print("=" * ' in cell_text or
            "print('=' * " in cell_text or
            'print("-" * ' in cell_text or
            "print('-' * " in cell_text
        )

        # Multiple print statements
        print_count = cell_text.count('print(')

        # It's a diagnostic block if:
        # - Has diagnostic keywords + separators + multiple prints
        return has_diagnostic and has_separator and print_count >= 3

    def is_pure_teaching_markdown(self, cell_text: str) -> bool:
        """Check if markdown cell is pure teaching content (no technical info)."""
        # Has code blocks = technical content, keep it
        if '```' in cell_text or '`' in cell_text:
            return False

        # Has tables with =|= = likely technical, keep it
        if '|' in cell_text and '=' in cell_text:
            return False

        # Check for teaching phrases
        for phrase in self.TEACHING_PHRASES:
            if re.search(phrase, cell_text, re.IGNORECASE):
                return True

        # Short cells with only philosophy/intro text
        lines = [l.strip() for l in cell_text.split('\n') if l.strip()]
        if len(lines) <= 3 and any(phrase in cell_text for phrase in
                                    ["Let's", "Consider", "Here's"]):
            return True

        return False

    def remove_emojis(self, text: str) -> str:
        """Remove emojis from text."""
        return self.EMOJI_PATTERN.sub('', text)

    def remove_decorative_separators(self, text: str) -> str:
        """Remove decorative separator lines."""
        lines = text.split('\n')
        cleaned = []

        for line in lines:
            stripped = line.strip()
            # Skip pure separator lines
            if re.match(r'^[=\-*]{5,}$', stripped):
                continue
            # Skip print statements for separators
            if 'print(' in stripped and any(c in stripped for c in '=-*'):
                continue
            cleaned.append(line)

        return '\n'.join(cleaned)

    def remove_diagnostic_comments(self, text: str) -> str:
        """Remove diagnostic and emoji comments from code."""
        lines = text.split('\n')
        cleaned = []

        for line in lines:
            # Skip comments with emojis
            if '#' in line and self.EMOJI_PATTERN.search(line.split('#')[1]):
                # Keep line without comment
                code_part = line.split('#')[0]
                if code_part.strip():
                    cleaned.append(code_part.rstrip())
                continue

            # Skip print statements with emojis or decorative output
            if 'print(' in line:
                # Check if it's printing only diagnostic/decorative content
                if any(phrase in line for phrase in ['✓', '✗', '=== ', '📊', '🔍']):
                    continue

            cleaned.append(line)

        return '\n'.join(cleaned)

    def _normalize_source(self, source) -> str:
        """Normalize source (can be string or list of strings)."""
        if isinstance(source, list):
            return ''.join(source)
        return str(source)

    def _set_source(self, cell: Dict, text: str) -> None:
        """Set source in cell (as list of strings)."""
        # Jupyter uses array of strings with embedded newlines
        lines = text.split('\n')
        cell['source'] = [line + '\n' if i < len(lines)-1 else line
                         for i, line in enumerate(lines) if line or i < len(lines)-1]

    def clean_cell(self, cell: Dict) -> Tuple[bool, Dict]:
        """
        Clean a single cell.
        Returns (should_keep, cleaned_cell)
        """
        source_text = self._normalize_source(cell.get('source', ''))

        if cell['cell_type'] == 'markdown':
            # Check if pure teaching markdown (delete entirely)
            if self.is_pure_teaching_markdown(source_text):
                return False, cell

            # Otherwise, clean it
            cleaned_text = self.remove_emojis(source_text)
            cleaned_text = self.remove_decorative_separators(cleaned_text)

            if cleaned_text != source_text:
                self._set_source(cell, cleaned_text)
                return True, cell
            return True, cell

        elif cell['cell_type'] == 'code':
            # Check if diagnostic block (delete entirely)
            if self.is_diagnostic_block(source_text):
                return False, cell

            # Otherwise, clean it
            cleaned_text = self.remove_diagnostic_comments(source_text)
            cleaned_text = self.remove_decorative_separators(cleaned_text)

            if cleaned_text != source_text:
                self._set_source(cell, cleaned_text)
                return True, cell
            return True, cell

        return True, cell

    def generate_preview(self) -> str:
        """Generate preview of changes."""
        preview_lines = [
            "PREVIEW: Changes to be applied",
            "═" * 70,
            ""
        ]

        cells_to_delete = []
        cells_to_simplify = []
        lines_removed = 0

        for i, cell in enumerate(self.notebook['cells']):
            should_keep, cleaned = self.clean_cell(cell)

            if not should_keep:
                cell_type = cell['cell_type']
                source_text = self._normalize_source(cell['source'])
                lines = len(source_text.split('\n'))
                cells_to_delete.append((i, cell_type, lines))
                lines_removed += lines
            elif cleaned != cell:
                original_text = self._normalize_source(cell['source'])
                cleaned_text = self._normalize_source(cleaned['source'])
                if original_text != cleaned_text:
                    cells_to_simplify.append((i, cell['cell_type']))
                    lines_removed += len(original_text.split('\n')) - len(cleaned_text.split('\n'))

        preview_lines.append(f"CELLS TO DELETE ({len(cells_to_delete)} total):")
        for idx, cell_type, lines in cells_to_delete:
            preview_lines.append(f"  - Cell {idx}: ({cell_type}) {lines} lines")

        preview_lines.append("")
        preview_lines.append(f"CELLS TO SIMPLIFY ({len(cells_to_simplify)} total):")
        for idx, cell_type in cells_to_simplify:
            preview_lines.append(f"  - Cell {idx}: ({cell_type})")

        preview_lines.append("")
        preview_lines.append("STATISTICS:")
        preview_lines.append(f"  - Cells deleted: {len(cells_to_delete)}")
        preview_lines.append(f"  - Cells modified: {len(cells_to_simplify)}")
        preview_lines.append(f"  - Lines removed: {lines_removed}")

        original_json = json.dumps(self.notebook)
        preview_lines.append(f"  - Original size: {len(original_json) / 1024:.1f} KB")

        return '\n'.join(preview_lines)

    def clean(self) -> Dict:
        """Apply cleaning to notebook."""
        cleaned_cells = []

        for cell in self.notebook['cells']:
            should_keep, cleaned_cell = self.clean_cell(cell)
            if should_keep:
                cleaned_cells.append(cleaned_cell)

        self.notebook['cells'] = cleaned_cells
        return self.notebook

    def save(self) -> Tuple[bool, str]:
        """Save cleaned notebook and create backup."""
        try:
            # Create backup
            if self.notebook_path.exists():
                shutil.copy(self.notebook_path, self.backup_path)

            # Save cleaned notebook
            with open(self.notebook_path, 'w') as f:
                json.dump(self.notebook, f, indent=1)

            return True, f"✓ Cleaned notebook saved\n  Backup: {self.backup_path}"

        except Exception as e:
            return False, f"✗ Error saving notebook: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_notebook_tool.py path/to/notebook.ipynb [options]")
        print("\nOptions:")
        print("  --dry-run              Show preview without applying changes")
        print("  --organize-imports     Consolidate imports at notebook start")
        print("  --move-comments        Extract verbose comments to markdown")
        print("  --all                  Apply all transformations")
        sys.exit(1)

    notebook_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    organize_imports = '--organize-imports' in sys.argv or '--all' in sys.argv
    move_comments = '--move-comments' in sys.argv or '--all' in sys.argv

    try:
        cleaner = NotebookCleaner(notebook_path)

        # Show preview
        print(cleaner.generate_preview())
        print("\n" + "═" * 70)

        if organize_imports:
            organizer = ImportOrganizer()
            imports = organizer.extract_imports(cleaner.notebook)
            print(f"\nIMPORT ORGANIZATION:")
            print(f"  Found {len(imports['stdlib'])} stdlib, {len(imports['third_party'])} third-party, {len(imports['local'])} local imports")

        if move_comments:
            extractor = CommentExtractor()
            verbose_comments = extractor.find_verbose_comments(cleaner.notebook)
            print(f"\nCOMMENT EXTRACTION:")
            print(f"  Found {len(verbose_comments)} verbose comment blocks to move to markdown")

        if dry_run:
            print("\nDRY RUN: No changes applied")
            sys.exit(0)

        # Ask for confirmation
        response = input("\nApply changes? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled.")
            sys.exit(0)

        # Clean and save
        cleaner.clean()

        if organize_imports:
            organizer = ImportOrganizer()
            imports = organizer.extract_imports(cleaner.notebook)
            import_cell = organizer.create_import_cell(imports)
            cleaner.notebook['cells'].insert(0, import_cell)
            organizer.remove_imports_from_cells(cleaner.notebook)
            print("✓ Imports organized and consolidated")

        if move_comments:
            # Note: Simple extraction demonstrated, full implementation would require
            # markdown cell creation and insertion
            extractor = CommentExtractor()
            verbose_comments = extractor.find_verbose_comments(cleaner.notebook)
            print(f"✓ Identified {len(verbose_comments)} verbose comments (extraction ready)")

        success, message = cleaner.save()
        print(message)

        if not success:
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
