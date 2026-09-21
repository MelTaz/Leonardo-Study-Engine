def escape_dollars(text: str) -> str:
    """
    Escapes currency dollar signs (e.g., $10 -> \$10) to prevent Streamlit
    from mistaking money for LaTeX math formatting.
    """
    if not isinstance(text, str):
        return text
    return text.replace("$", "\\$")


def clean_display_text(text: str, is_icas: bool = False) -> str:
    """
    Cleans raw question text for Streamlit display by replacing HTML line breaks (<br>) 
    with Markdown breaks, and conditionally escaping dollar signs.
    """
    if not isinstance(text, str):
        return text
    
    # Replace rogue HTML break tags with Streamlit Markdown line breaks
    cleaned = text.replace("<br>", "  \n").replace("<br/>", "  \n").replace("<br />", "  \n")
    
    # ICAS mode needs $ intact for LaTeX math; other topics get escaped
    if is_icas:
        return cleaned
    return escape_dollars(cleaned)
