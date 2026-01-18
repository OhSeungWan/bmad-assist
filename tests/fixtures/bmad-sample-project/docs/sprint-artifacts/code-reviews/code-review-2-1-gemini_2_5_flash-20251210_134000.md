### Code Review 2.1

### Architectural Sins
- **Pydantic Model for Data Structures (Violation):** The `BmadDocument` class (in `src/bmad_assist/bmad/parser.py`) is implemented as a `dataclass`. This directly contradicts the project standard explicitly stated in `docs/project-context.md`: "Pydantic models for all config/data structures (not dataclasses)". While `dataclass` serves the immediate functional purpose, this is an architectural deviation that impacts consistency and future extensibility (e.g., built-in validation, serialization, schema generation that Pydantic offers).

### Pythonic Crimes & Readability
- **Broad Exception Catching (`except Exception`):** In `src/bmad_assist/bmad/parser.py`, the `parse_bmad_file` function uses a broad `except Exception as e:` block to catch parsing failures from the `python-frontmatter` library. The `docs/project-context.md` explicitly states: "No bare `except:` - always catch specific exceptions from `core/exceptions.py`". While `Exception` is not a bare `except`, it is still overly general. A more robust implementation would catch specific exceptions (e.g., `yaml.YAMLError` or other exceptions documented by `python-frontmatter` for parsing issues) and then wrap them in `ParserError`. Catching `Exception` can mask other, unrelated issues.

### Performance & Scalability
[No specific issues identified.]

### Correctness & Safety
[No specific issues identified. Tests are comprehensive and cover edge cases.]

### Maintainability Issues
[No additional maintainability issues beyond the architectural and pythonic crimes identified above.]

### Suggested Fixes
1.  **Replace `dataclass` with `Pydantic BaseModel` for `BmadDocument`:**
    **File:** `src/bmad_assist/bmad/parser.py`
    **Instruction:** Convert `BmadDocument` from a `dataclass` to a `Pydantic.BaseModel` to align with project standards.
    **Old String (example of what needs to change, exact content requires reading the file):**
    ```python
    from dataclasses import dataclass
    # ...
    @dataclass
    class BmadDocument:
        """Parsed BMAD document with frontmatter and content."""
        frontmatter: dict[str, Any]
        content: str
        path: str
    ```
    **New String (example of what it should be, exact content requires reading the file):**
    ```python
    from pydantic import BaseModel
    # ...
    class BmadDocument(BaseModel):
        """Parsed BMAD document with frontmatter and content."""
        frontmatter: dict[str, Any]
        content: str
        path: str
    ```
2.  **Refine Exception Handling in `parse_bmad_file`:**
    **File:** `src/bmad_assist/bmad/parser.py`
    **Instruction:** Replace the general `except Exception` with a more specific exception for YAML parsing errors (e.g., `yaml.YAMLError` or `frontmatter.FrontmatterError` if provided by the library).
    **Old String (example of what needs to change, exact content requires reading the file):**
    ```python
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ParserError(f"Failed to parse {path}: {e}") from e
    ```
    **New String (example of what it should be, exact content requires reading the file):**
    ```python
        except FileNotFoundError:
            raise
        except (frontmatter.FrontmatterError, yaml.YAMLError) as e: # Assuming these are the exceptions raised
            raise ParserError(f"Failed to parse {path}: {e}") from e
        except Exception as e: # Catch any other unexpected errors
            # Log this unexpected error as critical for review
            raise ParserError(f"Unexpected parsing error for {path}: {e}") from e
    ```
    *(Note: The exact exceptions raised by `python-frontmatter` for malformed YAML would need to be confirmed. `yaml.YAMLError` is a common one.)*

### Final Score (1-10)
7

### Verdict: MAJOR REWORK
