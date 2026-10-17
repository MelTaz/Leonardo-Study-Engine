import re

MATH_SUBJECTS = {
    "Maths ICAS Revision",
    "Fractions",
    "Multiplication and Division"
}

def escape_dollars(text: str, subject: str = None) -> str:
    r"""
    Escapes unescaped dollar signs (e.g., $10 -> \$10) to prevent Streamlit
    from mistaking money for LaTeX math formatting, unless it's a math subject.
    """
    if not isinstance(text, str):
        return "" if text is None else str(text)
    if subject in MATH_SUBJECTS:
        return str(text)
    return re.sub(r'(?<!\\)\$', r'\\$', str(text))


def clean_display_text(text: str, is_math: bool = False, is_icas: bool = False) -> str:
    """
    Cleans raw question text for Streamlit display by replacing HTML line breaks (<br>) 
    with Markdown breaks, and keeping math LaTeX intact for math subjects.
    """
    if not isinstance(text, str):
        return "" if text is None else str(text)
    
    # Replace rogue HTML break tags with Streamlit Markdown line breaks
    cleaned = text.replace("<br>", "  \n").replace("<br/>", "  \n").replace("<br />", "  \n")
    
    # Math subjects (ICAS, Fractions, Multiplication & Division) need $ intact for LaTeX math
    if is_math or is_icas:
        return cleaned
    return escape_dollars(cleaned)
