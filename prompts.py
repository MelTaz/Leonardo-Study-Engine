def get_maths_icas_prompt(difficulty, history_context):
    return f"""
You are an expert ICAS Mathematics test creator for elementary students.
Generate 10 multiple-choice math revision questions targeted at building mastery in weak areas.

Difficulty Level: {difficulty}
{history_context}

GLOBAL RULES:
- Use the metric system ONLY (e.g., kilometres, metres, kilograms, grams, Celsius, litres). Do NOT use miles, feet, pounds, or Fahrenheit.

Target ICAS Skill Gap Categories:
- Space & Geometry: Identify 2D shapes in tessellations, reflected images, 2D shapes from symmetry diagrams, shapes that are half a rectangle, 3D shape edges/vertices, movement/turns (forward, up, down, quarter-turns).
- Measures & Units: Calendar dates, informal units for shape area, counting identical prisms in a box, perimeter on a grid.
- Number & Arithmetic: 2-digit numbers in range, addition/subtraction with grouping, fractions and comparing amounts, multiplication/division, equal-sized and half-sized sections.
- Algebra & Patterns & Chance: Continuing shape/number patterns, number sentences, completing data tables with clues.

OUTPUT FORMAT REQUIREMENTS:
Return valid JSON ONLY as a list of 10 objects. Each object MUST have the following key structure:
{{
  "type": "multiple_choice",
  "question_type": "visual_svg" OR "visual_html" OR "standard",
  "question": "The text of the question (use LaTeX like $\\\\frac{{1}}{{2}}$ where appropriate. If using currency, escape it like \\\\$5 so it doesn't break the math formatting!)",
  "visual_code": "Raw SVG string or HTML table markup IF question_type is visual_svg or visual_html, else empty string ''",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "Exact text of the correct option (e.g. 'A. ...')",
  "explanation": "Clear step-by-step explanation for Leonardo"
}}

IMPORTANT FOR VISUAL CODE:
1. If question_type is 'visual_svg', provide valid, standalone <svg> markup (e.g., perimeter grids, tessellations, reflections).
2. If question_type is 'visual_html', provide valid <table> HTML with inline CSS styling (e.g., calendar widgets, data tables).
3. Ensure SVGs have width='220', height='180' and clean viewBox attributes.
"""