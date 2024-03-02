import re
from typing import Callable


class TextSplitter:
    """
    Split a text into chunks with a size limit in tokens.
    """

    TokenCounter = Callable[[str], int]

    counter: TokenCounter

    limit: int

    def __init__(self, counter: TokenCounter, limit: int = 1024):
        """
        token_counter - function for counting tokens, typically from a Model.
        limit - max chunk len in tokens.
        """

        self.counter = counter
        self.limit = limit

    def _split_text_separators(self, text: str):
        SEPARATORS = [".", "!", "?", "。", "！", "？", "।", "،", "؛", "؟"]

        chunks: list[str] = []

        current_chunk = ""

        for i, char in enumerate(text):
            current_chunk += char
            if char in SEPARATORS:
                # period is not a sentence separator if part of a float
                if char == "." and i > 0 and i < len(text) - 1:
                    if text[i - 1].isdigit() and text[i + 1].isdigit():
                        continue
                chunks.append(current_chunk)
                current_chunk = ""

        if len(current_chunk):
            chunks.append(current_chunk)
            current_chunk = ""

        return [c.strip() for c in chunks]

    def _split_text(self, text: str) -> list[str]:
        result: list[str] = []

        temp = ""
        pos_ind = 0
        pos_count = 0

        for paragraph in re.split(r"(\\r?\\n){2,}", text.strip()):
            if not paragraph:
                continue
            paragraph = paragraph.strip()
            if not len(paragraph) or len(paragraph) == 1:
                continue

            paragraph_count = self.counter(paragraph)

            if paragraph_count > self.limit:
                for line in paragraph.splitlines():
                    if not line:
                        continue
                    line = line.strip()
                    if not len(line) or len(line) == 1:
                        continue

                    line_count = self.counter(line)

                    if line_count > self.limit:
                        for sentence in self._split_text_separators(line):
                            if not sentence or not len(sentence) or len(sentence) == 1:
                                continue

                            sentence_count = self.counter(sentence)

                            if sentence_count > self.limit:
                                words = re.split(r"\s", sentence)
                                for word in words:
                                    if not word:
                                        continue
                                    word = word.strip()
                                    if not len(word) or len(word) == 1:
                                        continue

                                    word_count = self.counter(word)

                                    if word_count > self.limit:
                                        raise f"Text chunk limit {self.limit} too small."

                                    word_cost = pos_count + word_count

                                    if word_cost <= self.limit:
                                        temp += f" {word}"
                                        pos_count = word_cost
                                    else:
                                        result.append(temp)
                                        temp = ""
                                        pos_ind += 1
                                        pos_count = 0
                            else:
                                sentence_cost = pos_count + sentence_count

                                if sentence_cost <= self.limit:
                                    temp += f" {sentence}"
                                    pos_count = sentence_cost
                                else:
                                    result.append(temp)
                                    temp = ""
                                    pos_ind += 1
                                    pos_count = 0
                    else:
                        line_cost = pos_count + line_count

                        if line_cost <= self.limit:
                            temp += f"\n{line}"
                            pos_count = line_cost
                        else:
                            result.append(temp)
                            temp = ""
                            pos_ind += 1
                            pos_count = 0
            else:
                paragraph_cost = pos_count + paragraph_count

                if paragraph_cost <= self.limit:
                    temp += f"\n{paragraph}"
                    pos_count = paragraph_cost
                else:
                    result.append(temp)
                    temp = ""
                    pos_ind += 1
                    pos_count = 0

        if len(temp.strip()):
            result.append(temp.strip())

        return result

    def __call__(self, input: str) -> list[str]:
        try:
            return self._split_text(input)
        except Exception as e:
            print(e)
            return ["Error. Corrupted message."]
