#!/usr/bin/env python3
"""
Simple Flask Web UI for MathLLM
A single-file application that provides a clean web interface for solving math problems.
"""

import os
import uuid
import json
import logging
import argparse
from flask import Flask, render_template_string, request, jsonify, session, redirect
from mathllm import MathLLM

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "math-secret-key-change-this")


# Initialize the MathLLM
def create_math_llm(base_url=None, api_key=None, model=None):
    """Create and configure the MathLLM"""
    try:
        base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL", "http://localhost:11434/v1"
        )
        api_key = api_key or os.environ.get("OPENAI_API_KEY", "ollama")
        model = model or os.environ.get("OPENAI_MODEL", "llama3.1")

        # Create MathLLM instance
        math_llm = MathLLM(
            ip=base_url, model_name=model, api_key=api_key, base_url=base_url
        )

        return math_llm

    except Exception as e:
        print(f"Error creating MathLLM: {e}")
        raise


# Global MathLLM instance (will be initialized in main)
math_llm = None


def generate_session_id():
    """Generate a unique session ID for new visitors"""
    return f"session_{str(uuid.uuid4())[:8]}"


def get_or_create_session():
    """Get existing session from Flask session or create new one"""
    if "session_id" not in session:
        session["session_id"] = generate_session_id()
        session["problem_history"] = []
    return session["session_id"]


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MathLLM Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .session-info {
            opacity: 0.9;
            font-size: 1.1em;
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
        }
        
        .content {
            padding: 30px;
        }
        
        .math-section {
            background: #fff8f0;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .math-section h2 {
            color: #d63031;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: 400;
        }
        
        .result-area {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: none;
        }
        
        .result-area.show {
            display: block;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .result-tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1em;
            color: #666;
            transition: all 0.3s ease;
        }
        
        .result-tab.active {
            background: white;
            color: #ff6b35;
            font-weight: 500;
        }
        
        .result-content {
            padding: 25px;
            display: none;
        }
        
        .result-content.active {
            display: block;
        }
        
        .solution {
            font-size: 1.2em;
            color: #2d3436;
            line-height: 1.6;
            background: #e8f5e8;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #00b894;
        }
        
        .code-block {
            background: #2d3748;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 10px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        
        .output-block {
            background: #f8f9fa;
            color: #2d3436;
            padding: 20px;
            border-radius: 10px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            overflow-x: auto;
            white-space: pre-wrap;
            border: 1px solid #e0e0e0;
        }
        
        .input-section {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #ff6b35;
            background: #fff8f0;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #ff6b35;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .input-form {
            padding: 25px;
        }
        
        .input-group {
            display: flex;
            gap: 15px;
            align-items: flex-end;
        }
        
        .input-wrapper {
            flex: 1;
        }
        
        .input-wrapper label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        .math-input {
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1.1em;
            outline: none;
            transition: border-color 0.3s ease;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
        }
        
        .math-input:focus {
            border-color: #ff6b35;
        }
        
        .solve-btn {
            background: linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            font-weight: 500;
        }
        
        .solve-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        }
        
        .solve-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .examples {
            margin-top: 20px;
            padding: 20px;
            background: #fff8f0;
            border-radius: 10px;
        }
        
        .examples h3 {
            color: #d63031;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .example-item {
            background: white;
            padding: 10px 15px;
            margin: 8px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-style: italic;
            color: #666;
        }
        
        .example-item:hover {
            background: #ff6b35;
            color: white;
            transform: translateX(5px);
        }
        
        @media (max-width: 600px) {
            .input-group {
                flex-direction: column;
            }
            
            .result-tabs {
                flex-direction: column;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .math-input {
                min-height: 80px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔢 MathLLM Assistant</h1>
            <div class="session-info">Session: {{ session_id }}</div>
        </div>
        
        <div class="content">
            <div class="math-section">
                <h2>Mathematical Problem Solver</h2>
                <p>Ask me any math question and I'll solve it step by step using Python!</p>
            </div>
            
            <div id="result-area" class="result-area">
                <div class="result-tabs">
                    <button class="result-tab active" onclick="showTab('solution')">Solution</button>
                    <button class="result-tab" onclick="showTab('code')">Generated Code</button>
                    <button class="result-tab" onclick="showTab('output')">Execution Output</button>
                </div>
                
                <div id="solution-content" class="result-content active">
                    <div id="solution-text" class="solution"></div>
                </div>
                
                <div id="code-content" class="result-content">
                    <pre id="code-text" class="code-block"></pre>
                </div>
                
                <div id="output-content" class="result-content">
                    <pre id="output-text" class="output-block"></pre>
                </div>
            </div>
            
            <div class="input-section">
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    Solving your math problem...
                </div>
                
                <div class="input-form">
                    <form id="math-form" class="input-group">
                        <div class="input-wrapper">
                            <label for="math-input">Enter your math problem:</label>
                            <textarea 
                                id="math-input" 
                                class="math-input" 
                                placeholder="e.g., 'Solve the quadratic equation x² + 5x + 6 = 0' or 'Calculate the derivative of sin(x) * cos(x)'"
                                rows="4"
                            ></textarea>
                        </div>
                        <button type="submit" class="solve-btn" id="solve-btn">Solve</button>
                    </form>
                    
                    <div class="examples">
                        <h3>Example Problems:</h3>
                        <div class="example-item" onclick="fillExample('Calculate the integral of x² from 0 to 3')">
                            Calculate the integral of x² from 0 to 3
                        </div>
                        <div class="example-item" onclick="fillExample('Find the derivative of sin(x) * cos(x)')">
                            Find the derivative of sin(x) * cos(x)
                        </div>
                        <div class="example-item" onclick="fillExample('Calculate the factorial of 10')">
                            Calculate the factorial of 10
                        </div>
                        <div class="example-item" onclick="fillExample('Find the roots of the equation x³ - 6x² + 11x - 6 = 0')">
                            Find the roots of the equation x³ - 6x² + 11x - 6 = 0
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const form = document.getElementById('math-form');
        const input = document.getElementById('math-input');
        const solveBtn = document.getElementById('solve-btn');
        const loading = document.getElementById('loading');
        const resultArea = document.getElementById('result-area');
        
        // Handle form submission
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const mathProblem = input.value.trim();
            if (!mathProblem) return;
            
            // Show loading state
            solveBtn.disabled = true;
            loading.classList.add('show');
            resultArea.classList.remove('show');
            
            try {
                const response = await fetch('/solve', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ problem: mathProblem })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update result tabs with the solution data
                    document.getElementById('solution-text').textContent = data.solution;
                    document.getElementById('code-text').textContent = data.code;
                    document.getElementById('output-text').textContent = data.output;
                    
                    // Show result area and switch to solution tab
                    resultArea.classList.add('show');
                    showTab('solution');
                } else {
                    alert('Error: ' + (data.error || 'Something went wrong'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Network error. Please try again.');
            } finally {
                // Hide loading state
                loading.classList.remove('show');
                solveBtn.disabled = false;
            }
        });
        
        function showTab(tabName) {
            // Hide all tabs and content
            document.querySelectorAll('.result-tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.result-content').forEach(content => content.classList.remove('active'));
            
            // Show selected tab and content
            document.querySelector(`.result-tab[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName + '-content').classList.add('active');
        }
        
        function fillExample(exampleText) {
            input.value = exampleText;
            input.focus();
            // Auto-resize
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';
        }
        
        // Auto-resize textarea
        input.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
        
        // Focus input on page load
        window.addEventListener('load', function() {
            input.focus();
        });
        
        // Handle Enter key (Ctrl+Enter to submit)
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Main page showing the math problem solver interface"""
    session_id = get_or_create_session()
    return render_template_string(HTML_TEMPLATE, session_id=session_id)


@app.route("/solve", methods=["POST"])
def solve():
    """Handle math problem solving requests"""
    try:
        data = request.get_json()
        math_problem = data.get("problem", "").strip()

        if not math_problem:
            return jsonify({"success": False, "error": "No problem provided"})

        session_id = get_or_create_session()

        # Solve the math problem using MathLLM
        result = math_llm.calculate(math_problem)

        # Handle different return formats
        if isinstance(result, tuple) and len(result) == 3:
            code, output, solution = result
        elif isinstance(result, str):
            # Error case
            code = "No code generated"
            output = result
            solution = result
        else:
            code = str(result)
            output = "Unknown output format"
            solution = "Could not extract solution"

        # Store in session history
        if "problem_history" not in session:
            session["problem_history"] = []

        session["problem_history"].append(
            {
                "problem": math_problem,
                "code": code,
                "output": output,
                "solution": solution,
            }
        )

        return jsonify(
            {
                "success": True,
                "code": code,
                "output": output,
                "solution": solution,
                "session_id": session_id,
            }
        )

    except Exception as e:
        print(f"Error in solve endpoint: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/history")
def history():
    """Get problem solving history for current session"""
    session_id = get_or_create_session()
    history = session.get("problem_history", [])
    return jsonify({"session_id": session_id, "history": history})


@app.route("/reset")
def reset_session():
    """Reset the current session"""
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MathLLM Web UI")
    parser.add_argument(
        "--api-endpoint",
        type=str,
        default="http://localhost:11434/v1",
        help="API endpoint URL (default: http://localhost:11434/v1)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="ollama",
        help="API key for the LLM service (default: ollama)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3.1",
        help="Model name to use (default: llama3.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port to run the web server on (default: 5001)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the web server on (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    # Initialize the MathLLM with command line parameters
    temp_math_llm = create_math_llm(args.api_endpoint, args.api_key, args.model)

    # Update global variable
    globals()["math_llm"] = temp_math_llm

    # Configure logging for production
    logging.basicConfig(level=logging.WARNING)

    print("Starting MathLLM Web UI...")
    print("Configuration:")
    print(f"  API Endpoint: {args.api_endpoint}")
    print(f"  API Key: {args.api_key}")
    print(f"  Model: {args.model}")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print("\nMake sure you have:")
    print("1. An LLM server running")
    print("2. Docker available for PyDocker execution")
    print("3. Flask and required dependencies installed")
    print(f"\nStarting server at http://{args.host}:{args.port}")

    app.run(debug=True, host=args.host, port=args.port)
