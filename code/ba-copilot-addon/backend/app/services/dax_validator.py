"""
DAX Validator for BA Copilot

Performs syntax validation and best practice checks on DAX expressions.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DAXValidator:
    """
    Validates DAX expressions for syntax and best practices.

    Note: This is a lightweight validator for common issues.
    For full validation, use the PowerBI API or Tabular Editor.
    """

    # Common DAX functions for validation
    KNOWN_FUNCTIONS = {
        # Aggregation
        "SUM", "SUMX", "AVERAGE", "AVERAGEX", "COUNT", "COUNTA", "COUNTX",
        "COUNTROWS", "MIN", "MINX", "MAX", "MAXX", "DISTINCTCOUNT",
        # Filter
        "CALCULATE", "CALCULATETABLE", "FILTER", "ALL", "ALLEXCEPT",
        "ALLSELECTED", "REMOVEFILTERS", "KEEPFILTERS",
        # Time Intelligence
        "DATEADD", "DATESBETWEEN", "DATESINPERIOD", "DATESYTD", "DATESQTD",
        "DATESMTD", "SAMEPERIODLASTYEAR", "PREVIOUSMONTH", "PREVIOUSQUARTER",
        "PREVIOUSYEAR", "TOTALMTD", "TOTALQTD", "TOTALYTD",
        # Table
        "SUMMARIZE", "SUMMARIZECOLUMNS", "ADDCOLUMNS", "SELECTCOLUMNS",
        "VALUES", "DISTINCT", "UNION", "INTERSECT", "EXCEPT",
        # Logical
        "IF", "SWITCH", "AND", "OR", "NOT", "TRUE", "FALSE", "IFERROR",
        "ISBLANK", "ISERROR", "ISLOGICAL", "ISNONTEXT", "ISNUMBER", "ISTEXT",
        # Text
        "CONCATENATE", "CONCATENATEX", "FORMAT", "LEFT", "RIGHT", "MID",
        "LEN", "UPPER", "LOWER", "TRIM", "SUBSTITUTE", "REPLACE",
        # Math
        "DIVIDE", "ABS", "ROUND", "ROUNDUP", "ROUNDDOWN", "INT", "MOD",
        "POWER", "SQRT", "LOG", "LOG10", "EXP",
        # Other
        "BLANK", "ERROR", "VAR", "RETURN", "SELECTEDVALUE", "HASONEVALUE",
        "RELATED", "RELATEDTABLE", "USERELATIONSHIP", "CROSSFILTER",
    }

    # Anti-patterns to warn about
    ANTI_PATTERNS = [
        (r"CALCULATE\s*\(\s*CALCULATE", "Nested CALCULATE - consider simplifying"),
        (r"FILTER\s*\(\s*ALL\s*\(", "FILTER(ALL(...)) - consider using REMOVEFILTERS"),
        (r"IF\s*\(\s*ISBLANK", "IF(ISBLANK(...)) - consider using COALESCE or +0"),
    ]

    def validate(self, dax: str) -> ValidationResult:
        """
        Validate a DAX expression.

        Args:
            dax: DAX expression to validate

        Returns:
            ValidationResult with validity status, errors, and warnings
        """
        errors = []
        warnings = []

        # Basic cleanup
        dax = dax.strip()

        if not dax:
            return ValidationResult(
                is_valid=False,
                errors=["Empty DAX expression"],
            )

        # Check for balanced parentheses
        if not self._check_balanced_parens(dax):
            errors.append("Unbalanced parentheses")

        # Check for balanced brackets
        if not self._check_balanced_brackets(dax):
            errors.append("Unbalanced square brackets")

        # Check for measure definition syntax
        if "=" in dax:
            parts = dax.split("=", 1)
            if len(parts) == 2:
                measure_name = parts[0].strip()
                if not measure_name:
                    errors.append("Missing measure name before '='")

        # Check for VAR/RETURN pattern
        has_var = "VAR" in dax.upper()
        has_return = "RETURN" in dax.upper()
        if has_var and not has_return:
            errors.append("VAR without RETURN - all VAR blocks must end with RETURN")
        if has_return and not has_var:
            warnings.append("RETURN without VAR - consider using variables for clarity")

        # Check for anti-patterns
        for pattern, message in self.ANTI_PATTERNS:
            if re.search(pattern, dax, re.IGNORECASE):
                warnings.append(message)

        # Check for unknown functions (potential typos)
        unknown = self._find_unknown_functions(dax)
        for func in unknown:
            warnings.append(f"Unknown function: {func} - verify spelling")

        # Check for common issues
        if "CALCULATE(" in dax.upper() and "FILTER(" in dax.upper():
            # Not necessarily wrong, but worth flagging
            pass

        # Check string literals are properly quoted
        if not self._check_string_literals(dax):
            warnings.append("Potential string quoting issue - use double quotes for strings")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_balanced_parens(self, dax: str) -> bool:
        """Check if parentheses are balanced."""
        count = 0
        in_string = False
        prev_char = ""

        for char in dax:
            if char == '"' and prev_char != "\\":
                in_string = not in_string
            elif not in_string:
                if char == "(":
                    count += 1
                elif char == ")":
                    count -= 1
                    if count < 0:
                        return False
            prev_char = char

        return count == 0

    def _check_balanced_brackets(self, dax: str) -> bool:
        """Check if square brackets are balanced."""
        count = 0
        in_string = False
        prev_char = ""

        for char in dax:
            if char == '"' and prev_char != "\\":
                in_string = not in_string
            elif not in_string:
                if char == "[":
                    count += 1
                elif char == "]":
                    count -= 1
                    if count < 0:
                        return False
            prev_char = char

        return count == 0

    def _find_unknown_functions(self, dax: str) -> list[str]:
        """Find potential function names that aren't recognized."""
        # Extract potential function names (word followed by open paren)
        pattern = r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("
        matches = re.findall(pattern, dax)

        unknown = []
        for match in matches:
            if match.upper() not in self.KNOWN_FUNCTIONS:
                # Could be a table or column reference, so only flag if it looks like a function
                if match[0].isupper() or "_" in match:
                    unknown.append(match)

        return unknown

    def _check_string_literals(self, dax: str) -> bool:
        """Check for properly quoted string literals."""
        # Simple check: odd number of quotes suggests unclosed string
        quote_count = dax.count('"')
        return quote_count % 2 == 0


# Example usage
if __name__ == "__main__":
    validator = DAXValidator()

    # Valid measure
    dax1 = """
    Sales YoY % =
    VAR CurrentSales = [Total Sales]
    VAR PriorSales = CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date]))
    RETURN
    DIVIDE(CurrentSales - PriorSales, PriorSales, BLANK())
    """

    result = validator.validate(dax1)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

    # Invalid measure (missing RETURN)
    dax2 = """
    Bad Measure =
    VAR X = [Total Sales]
    X + 1
    """

    result = validator.validate(dax2)
    print(f"\nValid: {result.is_valid}")
    print(f"Errors: {result.errors}")
