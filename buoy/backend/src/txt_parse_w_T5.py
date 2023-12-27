import re
import math

import torch
import transformers
from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from datasets import Dataset
from transformers.pipelines.pt_utils import KeyDataset


def clean_and_format_text(text):
    # Split the text into sentences based on various delimiters and filter out empty sentences
    sentences = filter(None, re.split(r"[.]\s+|\n+", text))

    # Reformat each sentence to end with a period (if it doesn't already have one) and strip leading/trailing whitespace
    formatted_sentences = [
        f"{sentence.strip()}{'' if sentence.strip().endswith('.') else '.'} "
        for sentence in sentences
    ]

    # Join the sentences back into a single text
    formatted_text = "".join(formatted_sentences)

    # Regular expression to remove unwanted characters (e.g., multiple underscores or dots)
    unwanted_chars_regex = r"(?<!\w)[_.]{2,}|[^\w\s.,:;!$@]"

    # Remove the unwanted characters from the text
    cleaned_text = re.sub(unwanted_chars_regex, "", formatted_text)

    return cleaned_text


def instantiate_T5_model_pipeline(model_id: str, batch_size=1):
    bnb_config = transformers.BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    if torch.cuda.is_available():
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id, quantization_config=bnb_config, device_map="auto"
        )
    else:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id, device_map="cpu")
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, max_length=512, device_map="auto"
    )
    t5_reader = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        batch_size=batch_size,
        min_length=5,
        max_length=1000,
    )
    return t5_reader, tokenizer


def token_size_of_sent(sentence: str, tokenizer: AutoTokenizer):
    tokens = tokenizer.tokenize(sentence, add_special_tokens=True)
    return len(tokens)


def token_limit_check(sentence: str, tokenizer: AutoTokenizer, max_tokens: int = 512):
    token_size = token_size_of_sent(sentence, tokenizer)
    return token_size > max_tokens


def truncate_sentence(sentence: str, tokenizer: AutoTokenizer, chunk_size: int = 512):
    # Tokenize the sentence and get token ids
    token_size = token_size_of_sent(sentence, tokenizer)
    word_counts = len(sentence.split())
    words_per_token = math.ceil(word_counts / token_size)
    # Split tokens into chunks of `chunk_size`
    chunks = [
        sentence[i : i + chunk_size * words_per_token]
        for i in range(0, word_counts, chunk_size * words_per_token)
    ]
    return chunks


def sentences_cleaner(
    sentences: list, tokenizer: AutoTokenizer, prompt_tok_size=100, max_size=512
):
    # prompt = "Read the sentence and identify vocabularies which could be either a soft or technical skillset. You are only allowed to use vocabulary found in the given sentence. The sentence: "
    prompt_sentences = []
    buffer_allowed = max_size - prompt_tok_size
    # trigger an update of dict if the sentences are restructured
    change_resume_of_dict = False
    for sent in sentences:
        if token_limit_check(sent, tokenizer, int(buffer_allowed)):
            sent_breaks = truncate_sentence(sent, tokenizer, int(buffer_allowed))
            prompt_sentences.extend(sent_breaks)
            change_resume_of_dict = True
        else:
            prompt_sentences.append(sent)
    return prompt_sentences, change_resume_of_dict


def create_dataset(sentences: list, prompt: str):
    # prompt = "Extract words or combination of words which might suggest either a soft or technical skills. You are only allowed to use vocabulary found in the given sentence. The sentence: "
    prompt_sentences = [prompt + sent for sent in sentences]
    temp_dict = {"sents": prompt_sentences}
    temp_data = Dataset.from_dict(temp_dict)
    return temp_data


def resume_to_sents(sentence: str):
    split_up = sentence.split(". ")
    sents = [_.strip() + "." for _ in split_up]
    return sents


def skills_from_sent(sentences: Dataset, t5_pipe_inst: pipeline, dataset_key: str):
    results = t5_pipe_inst(KeyDataset(sentences, dataset_key))
    return results
