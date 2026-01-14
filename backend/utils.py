import pdfplumber
from fuzzywuzzy import process

# Example ICD mapping (extend as needed)
ICD_DICT = {
    "diabetes mellitus": "E11",
    "hypertension": "I10",
    "asthma": "J45",
}


def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def normalize_icd(disease_name, icd_dict=ICD_DICT):
    match, score = process.extractOne(disease_name.lower(), icd_dict.keys())
    if score > 80:
        return icd_dict[match]
    return None
