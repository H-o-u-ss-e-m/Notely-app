import re

class Postprocessor:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Nettoie les espaces superflus et formate le texte reconnu.
        """
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

postprocessor = Postprocessor()
