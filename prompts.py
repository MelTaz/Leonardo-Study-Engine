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
  "question": "The text of the question (use LaTeX like $\\\\frac{{1}}{{2}}$ where appropriate, and wrap ALL number sentences in single dollar signs like $6 \\\\times \\\\Box = 42$. NEVER use plain parentheses like ( ) or \\\\( \\\\) for math. If using currency, escape it like \\\\$5 so it doesn't break the formatting!)",
  "visual_code": "Raw SVG string or HTML table markup IF question_type is visual_svg or visual_html, else empty string ''",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "Exact text of the correct option (e.g. 'A. ...')",
  "explanation": "Clear step-by-step explanation for Leonardo"
}}

IMPORTANT FOR VISUAL CODE:
1. If question_type is 'visual_svg', provide valid, standalone <svg> markup. For perimeter or area questions, you MUST explicitly draw visible grid lines using a <pattern> and <path> so the student can physically count the squares.
2. If question_type is 'visual_html', provide valid <table> HTML with inline CSS styling (e.g., calendar widgets, data tables).
3. Ensure SVGs have width='300', height='250' and clean viewBox attributes so that shapes and long text labels are never cropped.
4. If your visual includes labeled shapes (A, B, C, D), the text in your "options" array MUST perfectly describe the exact shapes you coded in the SVG. Do not list a shape in the options if you did not draw it.
5. NEVER use LaTeX (like $\Box$ or $\frac{1}{2}$) inside visual_code HTML/SVG. If you need to show an empty box or missing number inside a table or diagram, use a standard keyboard symbol like "[ ]" or "?".
6. If the question requires choosing the correct visual figure (e.g., reflections, rotations, shape matching), you MUST draw all four options (labeled A, B, C, D) side-by-side inside the main SVG canvas. The "options" array in your JSON should then simply be ["A", "B", "C", "D"].
"""

def get_standard_prompt(subject_focus, difficulty, history_context):
  """Generates the prompt for all standard subjects outside of ICAS."""
  
  # --- GLOBAL RULES ---
  global_rules = "- Use the metric system ONLY (e.g., kilometres, metres, kilograms, grams, Celsius, litres). Do NOT use miles, feet, pounds, or Fahrenheit."

  # --- SUBJECT-SPECIFIC RULES ---
  subject_rules = ""
  if subject_focus == "Italian":
      subject_rules = """
      SPECIAL RULES FOR ITALIAN (BILINGUAL SCHOOL STUDENT):
      - Leonardo attends an Italian bilingual school. Do NOT treat him as an absolute beginner; NEVER test isolated single-word flashcards.
      - NEVER include English translations in brackets next to Italian words in questions or options. Use Italian context or natural scenario prompts.
      - If difficulty is '1 - Easy': Realistic dialogues and everyday situational responses.
      - If difficulty is '2 - Medium': Expressing preferences, daily routines, telling time, and question words.
      - If difficulty is '3 - Hard': Present a short 2–3 sentence mini-story followed by a comprehension question in Italian.
      - For any 'free_text' questions, ensure the expected correct_answer is concise (1 to 3 words) so a Year 3 student can type it easily.
      """
  elif subject_focus == "Fractions":
      subject_rules = """
      SPECIAL RULES FOR FRACTIONS:
      - Do NOT use confusing emojis to represent fractions. 
      - Instead, embed helpful drawing hints directly into the question or explanation.
      - NEVER use LaTeX or math formatting inside visual_code HTML/SVG.
      """
      if difficulty == "1 - Easy":
          subject_rules += "\n- Include a drawing prompt or hint in almost every question, helping him visualize shapes."
      elif difficulty == "2 - Medium":
          subject_rules += "\n- Mix standard word problems with occasional drawing hints."
      elif difficulty == "3 - Hard":
          subject_rules += "\n- Focus on abstract numerical fractions and complex multi-step word problems without drawing hints."

  # --- ASSEMBLE FINAL PROMPT ---
  return f"""
  Generate 10 practice questions for a Year 3 student. 
  Topic: {subject_focus}
  Difficulty Level: {difficulty}
  
  {history_context}
  
  {subject_rules}
  
  GLOBAL RULES:
  {global_rules}
  """