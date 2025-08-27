import re
import PyPDF2

def extract_patient_info_from_pdf(file_path):
    """
    Extract patient identifiers from a hospital facesheet PDF.
    Looks for MRN, Name, DOB.
    Returns dict with available values.
    """
    result = {
        "patient_id": None,
        "patient_name": None,
        "dob": None
    }

    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            if not reader.pages:
                return result

            # Grab text from first page
            text = reader.pages[0].extract_text()

            if not text:
                return result

            # Debug: see raw text
            # print(text)

            # Regex patterns based on your sample
            mrn_match = re.search(r"MRN:\s*(\d+)", text)
            name_match = re.search(r"Name:\s*([A-Z,\- ]+)", text)
            dob_match = re.search(r"DOB:\s*([\d/]+)", text)

            if mrn_match:
                result["patient_id"] = mrn_match.group(1)

            if name_match:
                # clean up spacing
                result["patient_name"] = name_match.group(1).strip().title()

            if dob_match:
                result["dob"] = dob_match.group(1)

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return result
