# Enhanced prompt with Function Calling support

RULES = {
    "Structure": """
    A patent claim is traditionally written as a single sentence in present tense. Each claim begins with a capital letter and ends with a period. Periods may not be used elsewhere in the claims (other than abbreviations). Semicolons are usually used to separate clauses and phrases. A patent claim is typically broken into three parts: a preamble, a transitional phrase, and a body. 

    - The preamble is an introductory phrase that identifies the category of the invention. In the example claim above, the preamble is "An apparatus". 

    - The transitional phrase follows the preamble, and can be a limited number of options. In the example claim above, the transitional phrase is "comprising". Transitional phrases may be open-ended, or closed. Open-ended phrases are inclusive, and include words such as "comprising", "containg", and "characterized by". This implies that the claim does not exclude any additional elements or method steps that are not recited in the claim. The body of the claim recites the elements and limitations of the claim, which also defines the scope or requirements of the claim. 
    Our example claim uses an open-ended transitional phrases, which means that its scope  extends to an apparatus that includes all the elements listed in the claim AND any other element. A patent drafter will rarely write – and must think twice before filing – a closed claim, because infringers can easily avoid infringement by simply adding another element. Closed phrases such as "consisting of" limit the claim.
    """,
    "Punctuation": """For the sake of clarity, claims are extensively punctuated. A comma typically separates
            the preamble from the transitional phrase and a colon typically separates the transition
            from the body. Additionally, the body itself is typically broken into small paragraphs that
            define the logical elements of the claim. Thus the "elements" of a claim are typically
            separated by semi-colons and the penultimate element is followed "; and," before the last
            ends with a full stop. For example, 
            An apparatus, comprising:
                – a plurality of printed pages;
                – a binding configured to hold the printed pages together; and
                – a cover attached to the binding.
    """,
    "Antecedent Basis": """
            The elements in a patent claim must demonstrate the correct antecedent basis. This
            means that an element is introduced with the indefinite article "a" or "an" on its first use.
            When referring back to that element, the definite article "the" will appear. Not only is this
            grammatically appropriate, but proper antecedent basis is also a matter of law. The
            italicized portions of the following set of claims will help to explain:
            A device, comprising:
            - **a** pencil; and
            - **a** light attached to the pencil.
            2.
            **The** device recited in claim 1 wherein the light is detachably attached to the
            pencil.
            3.
            **The** device recited in claim 2 wherein the pencil is red in color.
        """,
    "Ambiguity and Indefinite Issues": """
            Unless the claims are drafted clearly and distinctly, third parties will have difficulty
            analyzing what is and is not covered by a patent claim. Therefore, claims must meet
            clarity and definiteness requirements, which are fundamental requirements of law. To
            fulfill this requirement, the claims must distinctly define the subject matter of the
            invention, using neither vague nor indefinite terms. For example, the claim below would
            be considered an invalid claim because the terms "long", "effective", "bright" and "near"
            are subjective terms, and as such, the scope of the claim is vague, unclear, and not
            clearly defined.

            An apparatus, comprising:
            a long pencil having two ends;
            an effective eraser attached to one end of the pencil; and
            a bright light attached near a center of the pencil
        """,
    "Broadening Dependent Claims": """
            A set of claims in a patent specification will normally include one or more independent
            (or main) claims and a number of dependent or subsidiary claims (or subclaims), which
            depend from one or more preceding independent and/or dependent claim(s).
            Dependent claims, however, should always be narrower than the claim from which they
            depend. Therefore, a dependent claim that is at odds with, contradicts, or fails to further
            narrow the independent claim is an improper dependent claim. For example, example
            dependent claim 2 below contradicts with the last clause of example independent claim
            1 below; therefore, example dependent claim 2 is an improper dependent claim.
            A device, comprising
            a pencil; and
            a light attached to the pencil.
            wherein the light is detachably attached to the pencil.
            2.
            The device of claim 1, wherein the light is permanently attached to the pencil.
        """,
}

RULES_TEXT = "\n".join(
    [f"{name}: {description}\n" for name, description in RULES.items()]
)

# Enhanced prompt for Function Calling
ENHANCED_PROMPT = f"""
Your job is to review the "Claims" section of a patent document. You must comment on its strength, and decide whether it passes a set of rules. 
If it does not pass a given rule, suggest a change that would make it pass.

Here is a description of a patent claim:

A patent is a legal document that gives an inventor the right to exclude others from practicing an
invention.

The claims are the most important section of a patent. The claims define the scope of protection provided by the patent and are the legally operative part of a patent application. The claims must be clear and concise, must be supported by the detailed description, and must be written in a particular format. 

For example, below is a sample claim.
An apparatus, comprising:
- a pencil having an elongated structure with two ends and a center therebetween;
- an eraser attached to one end of the pencil; and
- a light attached to the center of the pencil.

Here are the rules you should check for: {RULES_TEXT}

IMPORTANT: You must thoroughly review the entire document and identify ALL issues you find. For EACH problematic sentence or phrase, call the create_suggestion function ONCE, providing:

1. The originalText - Use ONLY a single sentence or short phrase (ideally one line, max 2-3 lines). Do NOT include entire multi-line paragraphs.
2. The replaceTo - Provide the corrected version of that same sentence or phrase.
3. An array of all issues found in that text segment.

CRITICAL TEXT MATCHING RULES:
- Copy the exact text formatting including punctuation and spacing
- If a claim has multiple issues across different sentences, create separate suggestions for each sentence
- Make sure the originalText does NOT overlap with each other.

EXAMPLES:
- GOOD: originalText = "a device being designed to be placed near a neural cell"
- BAD: originalText = entire multi-line claim with line breaks

This approach ensures accurate text matching and allows users to accept individual corrections.

When you find issues, use the create_suggestion function to report them. 
IMPORTANT: Always evaluate your confidence level (0-1) for each suggestion based on:
- How clear and unambiguous the issue is
- How certain you are about the correction
- The completeness of your proposed fix
Use higher confidence (0.8-1.0) for obvious errors and lower confidence (0.5-0.7) for stylistic suggestions.

For diagrams or flowcharts requested by the user, use the create_diagram function.
"""

# Function tools definition for OpenAI
FUNCTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_suggestion",
            "description": "Create a document suggestion for patent claim issues",
            "parameters": {
                "type": "object",
                "properties": {
                    "originalText": {
                        "type": "string",
                        "description": "A short, specific piece of text (single sentence or phrase) that contains the issue. Keep it as brief as possible while being specific enough for accurate matching. Avoid multi-line paragraphs."
                    },
                    "replaceTo": {
                        "type": "string", 
                        "description": "A SINGLE comprehensive replacement text that fixes ALL issues found in this text segment. Combine all necessary corrections into one final version."
                    },
                    "issues": {
                        "type": "array",
                        "description": "Array of all issues found in this text segment",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "The type of issue: Structure, Punctuation, Antecedent Basis, Ambiguity, Broadening Dependent Claims, etc."
                                },
                                "severity": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "The severity level of the issue"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Explanation of the issue with no more than 20 words"
                                }
                            },
                            "required": ["type", "severity", "description"]
                        }
                    },
                    "paragraph": {
                        "type": "integer",
                        "description": "The paragraph number (1-based index) where the issue occurs"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Your confidence level in this suggestion (0-1). Consider: clarity of the issue, certainty of the correction, and completeness of the fix. Use 0.9-1.0 for obvious errors, 0.7-0.9 for likely issues, 0.5-0.7 for possible improvements, below 0.5 for uncertain suggestions."
                    }
                },
                "required": ["originalText", "replaceTo", "issues", "paragraph", "confidence"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "create_diagram",
            "description": "Generate a diagram using Mermaid syntax for chat responses",
            "parameters": {
                "type": "object",
                "properties": {
                    "mermaid_syntax": {
                        "type": "string",
                        "description": "The Mermaid diagram syntax code"
                    },
                    "diagram_type": {
                        "type": "string",
                        "enum": ["flowchart", "sequence", "class", "er", "gantt", "pie", "mindmap"],
                        "description": "The type of diagram to create"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title or description of the diagram"
                    }
                },
                "required": ["mermaid_syntax", "diagram_type"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "insert_diagram",
            "description": "Insert a Mermaid diagram into the document after specified text",
            "parameters": {
                "type": "object",
                "properties": {
                    "insert_after_text": {
                        "type": "string",
                        "description": "The exact text in the document after which to insert the diagram"
                    },
                    "mermaid_syntax": {
                        "type": "string",
                        "description": "The Mermaid diagram syntax code"
                    },
                    "diagram_type": {
                        "type": "string",
                        "enum": ["flowchart", "sequence", "class", "er", "gantt", "pie", "mindmap"],
                        "description": "The type of diagram to create"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title or description of the diagram"
                    }
                },
                "required": ["insert_after_text", "mermaid_syntax", "diagram_type"]
            }
        }
    }
]

# For backward compatibility
PROMPT = ENHANCED_PROMPT