from langchain_core.documents import Document

lab_dataset = [
    {
        "test": "Glucose",
        "description": "Measures blood sugar levels in the body",
        "unit": "mg/dL",
        "normal_range": "70-110"
    },
    {
        "test": "WBC",
        "description": "White blood cell count, indicating immune system status",
        "unit": "10^3/uL",
        "normal_range": "4-10"
    },
    {
        "test": "Hemoglobin",
        "description": "Measures the concentration of hemoglobin in red blood cells",
        "unit": "g/dL",
        "normal_range": "12-16"
    },
    {
        "test": "Creatinine",
        "description": "Indicator of kidney function",
        "unit": "mg/dL",
        "normal_range": "0.6-1.3"
    },
    {
        "test": "Platelets",
        "description": "Platelet count, important for blood clotting",
        "unit": "10^3/uL",
        "normal_range": "150-400"
    },
    {
        "test": "ALT",
        "description": "Alanine transaminase, a liver enzyme",
        "unit": "U/L",
        "normal_range": "7-56"
    },
    {
        "test": "AST",
        "description": "Aspartate transaminase, another liver enzyme",
        "unit": "U/L",
        "normal_range": "10-40"
    },
    {
        "test": "BUN",
        "description": "Blood urea nitrogen, kidney function indicator",
        "unit": "mg/dL",
        "normal_range": "7-20"
    },
    {
        "test": "Cholesterol",
        "description": "Total cholesterol in the blood",
        "unit": "mg/dL",
        "normal_range": "<200"
    },
    {
        "test": "Triglycerides",
        "description": "Fat in the blood, indicator of cardiovascular risk",
        "unit": "mg/dL",
        "normal_range": "<150"
    },
    # Add more lab tests here...
]


# Convert dataset into documents
lab_docs = []
for entry in lab_dataset:
    content = (
        f"{entry['test']}: {entry['description']}. "
        f"Unit: {entry['unit']}. Normal range: {entry['normal_range']}."
    )
    lab_docs.append(Document(page_content=content))
