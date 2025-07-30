# You shouldn't need to read any of this.

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

PROMPT = f"""
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

    Respond in valid JSON format:
    {{
        "issues": [
        {{
            "type": "<error_type>",
            "severity": "<high|medium|low>",
            "paragraph": <paragraph_number>,
            "description": "<description_of_error>",
            "suggestion": "<suggested_correction>"
        }}]
    }}

    DO NOT unnecesarily report an issue if there is no error in the document.
    If you receive an HTML document, you MUST return an error.
"""
