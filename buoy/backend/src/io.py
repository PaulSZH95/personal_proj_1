import re
import mimetypes


from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError
from bs4 import BeautifulSoup
import html2text
import docx2txt


def remove_special_characters(input_string: str) -> str:
    """
    Removes special characters from a given string.

    Args:
        input_string (str): The string from which special characters need to be removed.

    Returns:
        str: The cleaned string with special characters removed.
    """

    pattern = r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]"
    cleaned_string = re.sub(pattern, "", input_string)
    return cleaned_string


def get_text_from_doc(document_path: str) -> str:
    """
    Extracts text from a DOC or DOCX file.

    Args:
        document_path (str): The file path of the DOC or DOCX file.

    Returns:
        str: Extracted text from the document.

    Raises:
        ValueError: If the document does not contain any text.
    """
    text = docx2txt.process(document_path)
    text = remove_special_characters(text)
    if text:
        return text
    else:
        raise ValueError("Make sure your document has text")


def get_text_from_pdf(document_path: str) -> str:
    """
    Extracts text from a PDF file.

    Args:
        document_path (str): The file path of the PDF file.

    Returns:
        str: Extracted text from the PDF file.

    Raises:
        PDFSyntaxError: If the PDF does not contain any text.
    """
    text = extract_text(document_path)
    text = remove_special_characters(text)
    if text:
        return text
    else:
        raise PDFSyntaxError("Make sure your pdf has text")


def get_text_from_html(document_path: str) -> str:
    """
    Extracts text from an HTML file.

    Args:
        document_path (str): The file path of the HTML file.

    Returns:
        str: Extracted text from the HTML file.

    Raises:
        ValueError: If the HTML file does not contain any text.
    """
    with open(document_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")
    text = html2text.html2text(soup)
    text = remove_special_characters(text)
    if text:
        return text
    else:
        raise ValueError("Make sure your html file has text")


def file_parsing_by_type(file_type: str, file_path: str) -> str:
    """
    Parses a file and extracts text based on its MIME type.

    Args:
        file_type (str): The MIME type of the file (e.g., 'html', 'pdf', 'docs').
        file_path (str): The file path of the file to be parsed.

    Returns:
        str: Extracted text from the file.

    Raises:
        ValueError: If the file type is not one of 'html', 'pdf', or 'docs'.
    """
    match file_type:
        case "html":
            text = get_text_from_html(file_path)
        case "pdf":
            text = get_text_from_pdf(file_path)
        case "docs":
            text = get_text_from_doc(file_path)
        case _:
            raise ValueError(f"{file_type} must either be html, pdf or docs")
    return text


def get_mime_type(file_path: str) -> str:
    """
    Determines the MIME type of a file based on its file path.

    Args:
        file_path (str): The file path of the file.

    Returns:
        str: The MIME type of the file.
    """
    allowed_types = {
        "text/xml": "html",
        "text/html": "html",
        "application/pdf": "pdf",
        "application/msword": "docs",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docs",
    }
    mime_type, _ = mimetypes.guess_type(file_path)
    file_type = allowed_types.get(mime_type, None)
    return file_type


def clean_and_format_text(text: str) -> str:
    """
    Cleans and formats a given text by removing unwanted characters and formatting sentences.

    Args:
        text (str): The text to be cleaned and formatted.

    Returns:
        str: The cleaned and formatted text.
    """
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
