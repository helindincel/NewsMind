from transformers import pipeline

class TextSummarizer:
    def __init__(self):
        self.model = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
        self.cache = {}

    def summarize(self, text, max_length=60, min_length=15):
        if not text or len(text.split()) < 10:
            return "No sufficient content for summarization."

        if text in self.cache:
            return self.cache[text]

        words = len(text.split())

        # max_length, input uzunluğundan büyük olmasın
        adjusted_max_length = min(max_length, words - 1)
        # min_length, adjusted_max_length'den büyük olmasın
        adjusted_min_length = min(min_length, max(5, adjusted_max_length // 2))

        try:
            summary = self.model(
                text,
                max_length=adjusted_max_length,
                min_length=adjusted_min_length,
                do_sample=False
            )[0]['summary_text']
            self.cache[text] = summary
            return summary
        except Exception as e:
            return f"Error during summarization: {str(e)}"
