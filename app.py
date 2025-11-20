from flask import Flask, render_template, request
import os
import tempfile
from openai import OpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key='')

def analyze_with_llm(code, analysis_type):
    """Analyze code using OpenAI GPT"""
    
    prompts = {
        "errors": """Analyze the following Python code for errors, bugs, and potential issues. 
        Return ONLY a bulleted list of specific errors and warnings. Be concise and technical.
        
        Code:
        {code}
        
        Errors/Warnings:""",
        
        "comments": """Generate helpful code comments and suggestions for the following Python code.
        Focus on improving readability, best practices, and performance.
        Return ONLY a bulleted list of comments and suggestions.
        
        Code:
        {code}
        
        Comments/Suggestions:""",
        
        "review": """Provide an overall review of the following Python code.
        Consider code quality, structure, efficiency, and maintainability.
        Return a concise paragraph (2-3 sentences) summarizing your assessment.
        
        Code:
        {code}
        
        Overall Review:"""
    }
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert Python code reviewer. Provide clear, technical feedback."},
                {"role": "user", "content": prompts[analysis_type].format(code=code)}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"Error in analysis: {str(e)}"

def parse_llm_response(response):
    """Parse LLM response into list items"""
    # Split by bullet points, numbers, or newlines
    items = re.split(r'\n• |\n\d+\. |\n- |\n\* |\n', response)
    items = [item.strip() for item in items if item.strip()]
    
    # If no clear list structure, return as single item
    if len(items) <= 1:
        return [response]
    
    return items

def analyze_code(code):
    """Main code analysis function using LLM"""
    
    if not code.strip():
        return {
            "errors": ["No code provided for analysis."],
            "comments": ["Please provide Python code to analyze."],
            "review": "No code submitted for review."
        }
    
    try:
        # Get analysis from LLM
        errors_response = analyze_with_llm(code, "errors")
        comments_response = analyze_with_llm(code, "comments")
        review_response = analyze_with_llm(code, "review")
        
        # Parse responses
        errors = parse_llm_response(errors_response)
        comments = parse_llm_response(comments_response)
        
        return {
            "errors": errors if errors else ["No specific errors detected."],
            "comments": comments if comments else ["No specific comments generated."],
            "review": review_response if review_response else "Unable to generate review."
        }
    
    except Exception as e:
        return {
            "errors": [f"Analysis error: {str(e)}"],
            "comments": ["Failed to generate comments due to analysis error."],
            "review": "Code analysis failed. Please try again."
        }

@app.route('/', methods=['GET', 'POST'])
def index():
    input_method = 'paste'
    code_content = ""
    analysis_results = None
    filename = ""
    
    if request.method == 'POST':
        input_method = request.form.get('input_method', 'paste')
        
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                if file.filename.endswith('.py'):
                    try:
                        code_content = file.read().decode('utf-8')
                        filename = file.filename
                    except Exception as e:
                        analysis_results = {
                            "errors": [f"File reading error: {str(e)}"],
                            "comments": [],
                            "review": "Failed to read uploaded file."
                        }
                else:
                    analysis_results = {
                        "errors": ["Invalid file type. Please upload a .py file."],
                        "comments": [],
                        "review": "File upload failed."
                    }
        
        # Handle pasted code
        if not code_content:
            code_content = request.form.get('code', '')
        
        # Analyze the code if we have content
        if code_content.strip():
            analysis_results = analyze_code(code_content)
        else:
            analysis_results = {
                "errors": ["No code provided for analysis."],
                "comments": [],
                "review": "Please paste your code or upload a Python file."
            }
    
    return render_template('index.html', 
                         input_method=input_method,
                         code_content=code_content,
                         analysis_results=analysis_results,
                         filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
