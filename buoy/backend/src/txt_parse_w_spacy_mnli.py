import spacy
from transformers import pipeline
from datasets import Dataset
from typing import List, Dict, Tuple, Set
from spacy.tokens.doc import Doc
from spacy.tokens.span import Span


def initiate_spacy() -> spacy.language.Language:
    """
    Initializes and returns a SpaCy Language model.

    Returns:
        spacy.language.Language: A SpaCy Language model instance loaded with "en_core_web_lg".
    """
    nlp_lg = spacy.load("en_core_web_lg")
    return nlp_lg


def advert_nlp_doc(advert: str, nlp_lg: spacy.language.Language) -> Doc:
    """
    Processes a text advertisement using a SpaCy Language model.

    Args:
        advert (str): The advertisement text to be processed.
        nlp_lg (spacy.language.Language): A SpaCy Language model.

    Returns:
        Doc: A SpaCy Doc object containing processed information of the advertisement.
    """
    doc = nlp_lg(advert)
    return doc


def get_entities(doc: Doc) -> List[Span]:
    """
    Extracts named entities from a SpaCy Doc object.

    Args:
        doc (Doc): A SpaCy Doc object.

    Returns:
        List[Span]: A list of named entity spans found in the document.
    """
    entities = list(doc.ents)
    # named_ent_labels = set([_.label_ for _ in entities])
    return entities


def exclude_ner_tags(
    entities: List[Span], list_exclude: List[str] = ["CARDINAL", "MONEY"]
) -> Dict[str, Span]:
    """
    Filters out specific named entity tags from a list of entities.

    Args:
        entities (List[Span]): A list of SpaCy named entity spans.
        list_exclude (List[str], optional): A list of entity labels to exclude. Defaults to ["CARDINAL", "MONEY"].

    Returns:
        Dict[str, Span]: A dictionary of entities that are not in the exclude list.
    """
    information_for_application = {}
    for _ in entities:
        if _.label_ not in list_exclude:
            information_for_application[_.text] = _
    return information_for_application


def gen_pipeline() -> pipeline:
    """
    Generates and returns a Hugging Face pipeline for zero-shot classification.

    Returns:
        pipeline: A Hugging Face pipeline for zero-shot classification.
    """
    created_pipe = pipeline(
        "zero-shot-classification",
        model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
        use_fast=False,
    )
    return created_pipe


def dataset_wrapper(ifa_var_values: List[str]) -> Dataset:
    """
    Wraps a list of values in a Hugging Face Dataset.

    Args:
        ifa_var_values (List[str]): ifa_var_values is list(information_for_application.values())

    Returns:
        Dataset: A Hugging Face Dataset containing the provided values.
    """
    data = Dataset.from_dict({"to_classify": ifa_var_values})
    return data


def zero_shot_classification(
    information_for_application: Dict[str, Span], classifier
) -> Tuple[List[str], Dict[str, str]]:
    """
    Performs zero-shot classification on named entities.

    Args:
        information_for_application (Dict[str, Span]): A dictionary of named entities.
        classifier: A Hugging Face classification pipeline.

    Returns:
        Tuple[List[str], Dict[str, str]]: A tuple containing a list of entity texts and a dictionary mapping entities to their classified labels.
    """
    new_label = {}
    ner_text, ner = (
        information_for_application.keys(),
        information_for_application.values(),
    )
    structure_ner_for_wrapper = [_.text for _ in ner]
    data = dataset_wrapper(structure_ner_for_wrapper)
    candidate_labels = [
        "skillset",
        "person",
        "location",
        "technology",
        "company",
        "time",
    ]
    result = classifier(data["to_classify"], candidate_labels, multi_label=False)
    new_label = {res["sequence"]: res["labels"][0] for res in result}
    return ner_text, new_label


def visualize_spacy_v_zero(
    information_for_application: Dict[str, Span],
    new_label: Dict[str, str],
    ner_text: List[str],
) -> None:
    """
    Prints a comparison between SpaCy's NER and zero-shot classification results.

    Args:
        information_for_application (Dict[str, Span]): A dictionary of named entities from SpaCy.
        new_label (Dict[str, str]): A dictionary mapping entities to their classified labels from zero-shot classification.
        ner_text (List[str]): A list of named entity texts.
    """
    print(f"{'NER TAGGED':40} {'spacy':10} {'bert'}".upper())
    for _ in ner_text:
        print(f"{_:40} {information_for_application[_].label_:10} {new_label[_]}")


def post_zero_shot_filter(
    ner_text: List[str],
    new_label: Dict[str, str],
    information_for_application: Dict[str, Span],
) -> Dict[str, Span]:
    """
    Filters named entities based on zero-shot classification results.

    Args:
        ner_text (List[str]): A list of named entity texts.
        new_label (Dict[str, str]): A dictionary mapping entities to their classified labels.
        information_for_application (Dict[str, Span]): A dictionary of named entities.

    Returns:
        Dict[str, Span]: A filtered dictionary of named entities.
    """
    ner_text = list(ner_text)
    filtered_info = {}
    for _ in ner_text:
        condition_1 = new_label[_] in ["skillset", "technology", "company"]
        if condition_1:
            filtered_info[_] = information_for_application[_]
    return filtered_info


def distill_information(
    information_for_application: Dict[str, Span], filtered_info: Dict[str, Span]
) -> List[str]:
    """
    Distills important information from filtered named entities.

    Args:
        information_for_application (Dict[str, Span]): A dictionary of named entities.
        filtered_info (Dict[str, Span]): A filtered dictionary of named entities.

    Returns:
        List[str]: A list of distilled information strings.
    """
    distilled_information = set()
    for _ in filtered_info:
        distilled_information.add(
            information_for_application[_].sent.text.rstrip(".").strip()
        )
    di_list = list(distilled_information)
    return di_list


def mega_job(text: str):
    """
    The main function to process a text advertisement and extract relevant information.

    Args:
        text (str): The text of the advertisement to be processed.

    Returns:
        List[str]: A list of extracted and processed information from the advertisement.
    """
    nlp_lg = initiate_spacy()
    doc = advert_nlp_doc(text, nlp_lg)
    entities = get_entities(doc)
    classifier = gen_pipeline()

    information_for_application = exclude_ner_tags(
        entities, list_exclude=["CARDINAL", "MONEY"]
    )
    ner_text, new_label = zero_shot_classification(
        information_for_application, classifier
    )
    filtered_info = post_zero_shot_filter(
        ner_text, new_label, information_for_application
    )
    final_information = distill_information(information_for_application, filtered_info)
    return final_information
