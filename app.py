from flask import Flask, render_template, request
import os
import tempfile
from openai import OpenAI
from dotenv import load_dotenv
import re
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key='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')

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
        
        "review": """Provide an overall review and rating of the following Python code.
        Consider code quality, structure, efficiency, and maintainability.
        Return a JSON object with two keys: 
        - "rating": a number from 1-10 representing the code quality
        - "review": a concise paragraph (2-3 sentences) summarizing your assessment
        
        Format your response as valid JSON only.
        
        Code:
        {code}
        
        Response:""",
        
        "rating": """Rate the following Python code on a scale of 1-10 based on quality, structure, and best practices.
        Return ONLY a single number between 1 and 10.
        
        Code:
        {code}
        
        Rating:"""
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
    items = re.split(r'\n• |\n\d+\. |\n- |\n\* |\n', response)
    items = [item.strip() for item in items if item.strip()]
    
    if len(items) <= 1:
        return [response]
    
    return items

def extract_rating_from_text(text):
    """Extract rating from text response"""
    # Look for numbers 1-10 in the text
    numbers = re.findall(r'\b(10|[1-9])\b', text)
    if numbers:
        return min(10, max(1, int(numbers[0])))
    return 5  # Default rating if none found

def parse_review_response(response):
    """Parse review response to extract rating and text"""
    try:
        # Try to parse as JSON first
        data = json.loads(response)
        rating = data.get('rating', 5)
        review_text = data.get('review', 'No review generated.')
        return rating, review_text
    except:
        # If JSON parsing fails, extract rating from text
        rating = extract_rating_from_text(response)
        review_text = response
        return rating, review_text
    
@app.template_filter('rating_class')
def rating_class(rating):
    if rating >= 9:
        return "excellent"
    elif rating >= 7:
        return "good"
    elif rating >= 5:
        return "average"
    elif rating >= 3:
        return "needs-improvement"
    else:
        return "poor"

def analyze_code(code):
    """Main code analysis function using LLM"""
    
    if not code.strip():
        return {
            "errors": ["No code provided for analysis."],
            "comments": ["Please provide Python code to analyze."],
            "review": "No code submitted for review.",
            "rating": 0
        }
    
    try:
        # Get analysis from LLM
        errors_response = analyze_with_llm(code, "errors")
        comments_response = analyze_with_llm(code, "comments")
        review_response = analyze_with_llm(code, "review")
        
        # Get separate rating
        rating_response = analyze_with_llm(code, "rating")
        rating = extract_rating_from_text(rating_response)
        
        # Parse responses
        errors = parse_llm_response(errors_response)
        comments = parse_llm_response(comments_response)
        
        # Parse review to get both rating and text
        llm_rating, review_text = parse_review_response(review_response)
        
        # Use the rating from the dedicated rating call, fallback to review rating
        final_rating = rating if rating else llm_rating
        
        return {
            "errors": errors if errors else ["No specific errors detected."],
            "comments": comments if comments else ["No specific comments generated."],
            "review": review_text if review_text else "Unable to generate review.",
            "rating": final_rating
        }
    
    except Exception as e:
        return {
            "errors": [f"Analysis error: {str(e)}"],
            "comments": ["Failed to generate comments due to analysis error."],
            "review": "Code analysis failed. Please try again.",
            "rating": 0
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
                            "review": "Failed to read uploaded file.",
                            "rating": 0
                        }
                else:
                    analysis_results = {
                        "errors": ["Invalid file type. Please upload a .py file."],
                        "comments": [],
                        "review": "File upload failed.",
                        "rating": 0
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
                "review": "Please paste your code or upload a Python file.",
                "rating": 0
            }
    
    return render_template('index.html', 
                         input_method=input_method,
                         code_content=code_content,
                         analysis_results=analysis_results,
                         filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
