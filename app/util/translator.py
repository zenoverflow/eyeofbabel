import re, gc, ctranslate2, transformers, html
from abc import ABC, abstractmethod
from huggingface_hub import snapshot_download

from app.util.text import TextSplitter
from app.util.mode import mode_is_dev


class TextTranslator(ABC):
    @abstractmethod
    def translate(
        self,
        text: str,
        target_lang="en",
        source_lang: str | None = None,
    ) -> str:
        pass

    @abstractmethod
    def destroy(self):
        pass


# ct2-transformers-converter \
# --model ./data/madlad400-3b-mt/ \
# --output_dir ./data/madlad400-3b-mt-int8-float32 \
# --quantization int8_float32


class Madlad400Translator(TextTranslator):
    _translator: ctranslate2.Translator
    _tokenizer: transformers.T5Tokenizer

    def __init__(
        self,
        variant: str = "zenoverflow/madlad400-3b-mt-int8-float32",
        run_on_nvidia: bool = False,
    ) -> None:
        model_path = snapshot_download(variant)
        device = "auto" if run_on_nvidia else "cpu"
        self._translator = ctranslate2.Translator(model_path, device=device)
        self._tokenizer = transformers.T5Tokenizer.from_pretrained(model_path)

    def translate(
        self,
        text: str,
        target_lang="en",
        source_lang: str | None = None,  # redundant
    ) -> str:
        try:
            text = re.sub(r"\n+", " ", text).strip()
            text = re.sub(r"\r+", " ", text).strip()

            # This model seems to fail with short text.
            # This is a quick and dirty workaround.
            # If it works, it works.
            if len(text) < 12:
                text = text.rjust(12, "_")

            chunks = TextSplitter(
                counter=lambda t: len(self._tokenizer(t, return_tensors="pt")),
                limit=128,
            )(text)

            result: list[str] = []

            for chunk in chunks:
                txt = f"<2{target_lang}> {chunk}"

                if mode_is_dev():
                    print(txt)

                input_tokens = self._tokenizer.convert_ids_to_tokens(
                    self._tokenizer.encode(txt)
                )
                results = self._translator.translate_batch(
                    [input_tokens],
                    batch_type="tokens",
                    # max_batch_size=1024,
                    beam_size=4,
                    no_repeat_ngram_size=0,
                    repetition_penalty=1,
                )

                output_tokens = results[0].hypotheses[0]

                # Another workaround for output cleanup
                output_text = html.unescape(
                    self._tokenizer.decode(
                        self._tokenizer.convert_tokens_to_ids(
                            output_tokens,
                        )
                    ).replace(" &", "&"),
                )

                if mode_is_dev():
                    print(output_text)

                result.append(output_text)

            # Remove length-padding underscores (cleanup after short text workaround).
            return " ".join([r.lstrip("_").strip() for r in result]).strip()
        except Exception as e:
            if mode_is_dev():
                print(e)
            return ""

    def destroy(self):
        self._translator = None
        self._tokenizer = None
        # torch.cuda.empty_cache()
        gc.collect()
