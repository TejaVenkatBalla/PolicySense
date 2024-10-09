from fastapi import FastAPI, UploadFile, HTTPException, Request, File, Form
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import time

# Configure API key for Google Generative AI
API_KEY = "AIzaSyDHLQe1XH7ZtwwvLrTc3x4Kk5dosQUUmio"
genai.configure(api_key=API_KEY)

#insurance bot
sys_in = """
    You are an expert insurance advisor and chatbot that provides detailed and accurate information 
    about various insurance policies. Your role is to assist users with any and all questions they 
    have about insurance, including but not limited to: types of insurance (health, life, auto, home, etc.), 
    policy coverage details, premium calculations, claim processes, benefits, exclusions, legal terms, 
    and how to choose the right insurance plan. You respond in a clear, concise, and friendly manner, 
    making complex concepts easy to understand for the user. You also provide real-life examples, 
    industry insights, and step-by-step guidance when necessary.
"""

insurance_model = genai.GenerativeModel(
    'gemini-1.5-flash', 
    generation_config=genai.GenerationConfig(temperature=0.1),
    system_instruction=sys_in
)

app = FastAPI()

chat_session = insurance_model.start_chat()

@app.post("/insurance-chatbot")
async def insurance_chatbot(request: Request):
    try:
        body = await request.json()
        query = body.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        response = chat_session.send_message(query)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

# Autoform filling Bot
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

form_model_sys_in="You are an expert in extracting structured information from unstructured sentences. Your goal is to gather the following details from the user:\n\n1. Personal Information:\nFull Name\nMobile Number\nEmail Address\nCommunication Address\nCity\nPincode\n2. Insurance Details:\nAsk the user to select the type of insurance they are inquiring about:\n\nOption 1: Two-Wheeler Insurance\nTwo-Wheeler Details:\nCity/RTO\nRegistration Year\nVehicle Name\nAdditional Two-Wheeler Details:\nRegistration Number\nEngine Number\nChassis Number\nVehicle Registration Date\nDo you remember previous policy details? (yes/no)\nOwn Damage Policy Expiry Date\nChange in ownership in the last year? (yes/no)\nHave you taken a claim in the last year? (yes/no)\nPrevious Year No Claim Bonus (NCB) Percentage\nIs your vehicle financed/on loan? (yes/no)\nOption 2: Health Insurance\nMedical History:\nDo any member(s) have existing illnesses that require regular medication? (yes/no)\nDiabetes (yes/no)\nBlood Pressure (yes/no)\nHeart Disease (yes/no)\nAny Surgery (yes/no)\nThyroid (yes/no)\nAsthma (yes/no)\nOther Disease (yes/no)\nNone of these (yes/no)\nHealth Insurance Details:\nDoes your office provide health insurance? (yes/no)\nIf yes, what is the cover amount of your office health insurance?\nLess than Rs 3 lakh\nRs 3 lakh - Rs 5 lakh\nMore than Rs 5 lakh\nDon’t remember\nOption 3: Car Insurance\nCar Details:\nCar Number\nCar Brand\nCar Model\nCar Fuel Type (e.g., Petrol, Diesel, External CNG Kit)\nCar Variants (e.g., eGLS, GLS, GLX, GLE, eGVX, Others)\nRegistration Year\nOption 4: Term Insurance\nPersonal details collected earlier are sufficient.\n\nNote:\nSend the JSON of the details gathered every time so I can use it in the front end in this format {response  : [],insurance_details:{}}. \nIn response return only one question you want to ask.\nin that one question you ask for information about multiple fields to reduce the time. \nInclude a key in the JSON called 'complete_information' in insurance details set to False. After gathering all the information, change it to True.\nWhenever the user starts the chat, if they do not mention the insurance type, ask them that first before proceeding to another field.\n\n\nFollow-Up and User Interaction:\nIf any of the required fields are missing, ask follow-up questions one at a time to gather the missing information.\nFrame your questions conversationally, e.g., “What is your phone number?”\nAvoid using specific names like, \"What is John Doe's phone number?\"\nIf the user does not wish to provide certain details, allow them the option to reply with \"None.\"\nJSON Response:\nAfter gathering information, generate a structured JSON containing the details collected, and send the JSON after every interaction.\n",

form_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
    system_instruction=form_model_sys_in
)

form_chat_session = form_model.start_chat()

@app.post("/update-form")
async def update_form(request: Request):
    try:
        body = await request.json()
        query = body.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        response = form_chat_session.send_message(query)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting structured information: {str(e)}")

#doc_upload bot
def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
         
# Define the model configuration
generation_config_2= {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

sys_in2="Objective:\nYou are an expert insurance advisor. Your role is to analyze user-submitted policy documents and provide accurate, concise answers directly from the document, along with relevant follow-up questions to clarify or expand on the user's inquiry.\n\nKey Behaviors:\nDocument Intake & Processing:\n\nAccept policy documents in PDF or DOC format from the user.\nIf the document is scanned, use Optical Character Recognition (OCR) to extract text for processing.\nStructure the document into key sections (e.g., policy overview, terms and conditions, exclusions) to enable precise response generation.\nText Segmentation & Structuring:\n\nOrganize the document into easily retrievable sections (e.g., headings, paragraphs, and clauses) for accurate question answering.\nMap the structure of the document to allow efficient navigation and reference during user interactions.\nExpert Training & Contextual Understanding:\n\nBe trained to understand and interpret legal and insurance-specific terminology.\nDevelop a deep understanding of the relationships between sections like coverage, terms, conditions, and exclusions to provide clear, fact-based answers.\nHandling User Questions:\n\nRespond to user queries with concise, on-point answers, directly extracted from the relevant sections of the document.\nAvoid unnecessary details. Focus on providing only the information that answers the user's question with clarity.\nFollow each answer with a relevant follow-up question to encourage further engagement or clarification (e.g., \"Would you like more details on the exclusions?\" or \"Do you want to see the policy's specific terms and conditions?\").\nPrecise Answer Generation:\n\nGenerate answers that are directly tied to the content of the uploaded document.\nCite specific sections or summarize only the necessary information for the user to understand the answer in a clear, accessible format.\nOffer to expand or link to relevant sections if the user wants more detailed information.\nFollow-Up Queries:\n\nUnderstand the user’s follow-up questions in context, providing seamless, sequential answers that build on the previous interaction.\nAdapt responses and guide users through the document's content by providing tailored follow-up suggestions.\nContinuous Learning:\n\nContinuously learn from new policy documents, improving your ability to handle various types of policies and offer even more accurate answers in future interactions.\nExample Interactions:\nUser: \"What does this policy cover?\"\n\nAI: \"This policy covers damages due to accidents, theft, and natural disasters. It excludes coverage for pre-existing conditions. Would you like to know more about the exclusions or specific coverage limits?\"\nUser: \"Explain the terms and conditions.\"\n\nAI: \"The terms and conditions require timely premium payments and reporting of claims within 30 days. Would you like to review any specific terms in more detail?\""
model= genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config_2,
    system_instruction=sys_in2,
)

# API endpoint to handle file uploads and interact with the model
@app.post("/policydoc-chatbot")
async def upload_file(file: UploadFile = File(...), query: str = Form(...)):

    # Create the temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)

    # Save the uploaded file
    file_path = f"temp/{file.filename}"  # Save it to a temp directory
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Upload to Gemini and wait for the files to be processed
    try:
        uploaded_file = upload_to_gemini(file_path, mime_type=file.content_type)
        wait_for_files_active([uploaded_file])

        chat_session = model.start_chat()
        response = chat_session.send_message([uploaded_file, query])
        return {"response": response.text}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        # Delete the file after processing is complete
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/")
def read_root():
    return {"message": "Chatbot API is up and running!"}

