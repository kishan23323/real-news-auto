"""
Step 2: Turn the full article into a short, spoken-friendly summary,
and also expose it as individual sentences (used to pick relevant
images per segment, and as on-screen captions).
"""
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from nltk.tokenize import sent_tokenize
import nltk

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


def summarize(text: str, num_sentences: int = 8) -> str:
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    sentences = summarizer(parser.document, num_sentences)
    return " ".join(str(s) for s in sentences)


def get_sentences(summary: str):
    """Split the summary into individual sentences for captions/image queries."""
    return [s.strip() for s in sent_tokenize(summary) if s.strip()]


if __name__ == "__main__":
    sample = "Sentence one. Sentence two. Sentence three. " * 10
    s = summarize(sample, 3)
    print(s)
    print(get_sentences(s))
