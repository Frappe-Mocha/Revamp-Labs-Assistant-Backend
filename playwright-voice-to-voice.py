"""Hubspot Voice Assistant - Complete Backend Code"""

import os
import time
import random
import subprocess
import json
import re
from collections import deque
from io import BytesIO
import requests
import soundfile as sf
import sounddevice as sd
import numpy as np
import azure.cognitiveservices.speech as speechsdk
from playwright.sync_api import sync_playwright
from openai import AzureOpenAI
from config import AZURE_OPENAI_API_KEY, AZURE_SPEECH_KEY

# Configuration settings


AZURE_SERVICE_REGION = "westeurope"
TTS_VOICE_NAME = "en-US-JennyNeural"
AZURE_OPENAI_ENDPOINT = "https://storegpt-ai-service-1.openai.azure.com/"
CONVERSATION_HISTORY_MAX = 6
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
HUBSPOT_USERNAME = "anujp2206@gmail.com"
HUBSPOT_PASSWORD = "Pikapika@123"
DEFAULT_MODE = "hubspot"

# Global variables for browser instances
browser = None
page = None
playwright_instance = None

# Initialize conversation history
conversation_history = deque(maxlen=CONVERSATION_HISTORY_MAX)

# Current mode (youtube or hubspot)
current_mode = DEFAULT_MODE

# Global state for speech handling
is_speaking = False

# Initialize speech SDK config
speech_config = speechsdk.SpeechConfig(
    subscription=AZURE_SPEECH_KEY,
    region=AZURE_SERVICE_REGION
)

# Initialize OpenAI client
openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-05-01-preview"
)

def add_to_conversation(role, message):
    """Add a message to the conversation history"""
    conversation_history.append({"role": role, "content": message})
    
def get_conversation_history():
    """Get the current conversation history"""
    return list(conversation_history)

def clear_conversation_history():
    """Clear the conversation history"""
    conversation_history.clear()

def recognize_speech():
    """Recognize speech using Azure Speech SDK"""
    # This is a placeholder for the actual speech recognition implementation
    print("Listening...")
    # Return a dummy command for testing
    return "show dashboard"

def text_to_speech(text):
    """Convert text to speech using Azure Speech SDK"""
    global is_speaking
    
    # This is a placeholder for the actual text-to-speech implementation
    print(f"Speaking: {text}")
    is_speaking = True
    time.sleep(2)  # Simulating speech duration
    is_speaking = False
    
    # Commented out implementation using Azure Services
    """
    global is_speaking
    
    if not text:
        return
        
    try:
        # Configure speech synthesizer
        speech_config.speech_synthesis_voice_name = TTS_VOICE_NAME
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        
        # Set speaking flag
        is_speaking = True
        
        # Get audio data
        result = speech_synthesizer.speak_text_async(text).get()
        
        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Get audio data as a byte array
            audio_data = result.audio_data
            
            # Convert to numpy array for playback
            with BytesIO(audio_data) as audio_stream:
                data, sample_rate = sf.read(audio_stream)
                sd.play(data, sample_rate)
                sd.wait()  # Wait until audio playback is done
        else:
            print(f"Speech synthesis failed: {result.reason}")
            
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
    finally:
        is_speaking = False
    """

def check_chrome_running():
    """Check if Chrome is already running with debug port"""
    try:
        response = requests.get("http://localhost:9222/json/version", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_chrome_with_debug():
    """Start Chrome with remote debugging enabled"""
    print("Starting Chrome with remote debugging port...")
    chrome_path = ""
    
    # Try to find Chrome executable based on OS
    if os.name == 'nt':  # Windows
        paths_to_try = [
            os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
            os.path.expandvars("%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe"),
            os.path.expandvars("%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe")
        ]
        for path in paths_to_try:
            if os.path.exists(path):
                chrome_path = path
                break
    elif os.name == 'posix':  # macOS or Linux
        if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        else:
            # Try common Linux paths
            paths_to_try = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chrome",
                "/usr/bin/chromium-browser"
            ]
            for path in paths_to_try:
                if os.path.exists(path):
                    chrome_path = path
                    break
    
    if not chrome_path:
        print("Chrome executable not found. Please start Chrome manually with --remote-debugging-port=9222")
        return False
    
    try:
        # Start Chrome with remote debugging port
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            "--no-first-run",
            "--no-default-browser-check",
            "--user-data-dir=./chrome-data"  # Creates a new profile to avoid contaminating existing ones
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a bit for Chrome to start
        time.sleep(5)
        return True
    except Exception as e:
        print(f"Failed to start Chrome: {str(e)}")
        return False

def initialize_browser():
    """Initialize Playwright by connecting to existing Chrome instance or launching a new one"""
    global browser, page, playwright_instance
    
    print("Connecting to browser...")
    playwright_instance = sync_playwright().start()
    
    # Check if Chrome is already running with debug port
    chrome_running = check_chrome_running()
    
    if not chrome_running:
        print("Chrome not running with debug port. Attempting to start it...")
        if not start_chrome_with_debug():
            print("Failed to start Chrome. Falling back to launching a new browser...")
            # Fall back to launching a new browser
            chrome_running = False
    
    try:
        if chrome_running:
            # Connect to existing Chrome instance
            print("Attempting to connect to existing Chrome instance...")
            browser = playwright_instance.chromium.connect_over_cdp("http://localhost:9222")
            print("Successfully connected to existing Chrome browser")
        else:
            # Launch a new browser with anti-bot detection features
            print("Launching new browser instance...")
            browser = playwright_instance.chromium.launch(
                headless=False,
                channel="chrome" if os.path.exists("/Applications/Google Chrome.app") or 
                         os.path.exists(os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe")) else None,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials"
                ]
            )
    
        # Create a new context with anti-bot detection settings
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            timezone_id="America/New_York",
            locale="en-US",
            permissions=["geolocation", "notifications"]
        )
        
        # Add anti-bot detection scripts
        context.add_init_script("""
            // Mask automation features
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Override the permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Prevent fingerprinting
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                        name: "Chrome PDF Plugin",
                        filename: "internal-pdf-viewer",
                        description: "Portable Document Format"
                    }
                ]
            });
        """)
        
        # Create a new page
        page = context.new_page()
        
        # Set navigation timeout to ensure faster error feedback
        page.set_default_navigation_timeout(60000)  # Extended timeout to 60 seconds
        
        return True
    except Exception as e:
        print(f"Browser initialization error: {str(e)}")
        return False

def close_browser():
    """Close Playwright browser instance"""
    global browser, playwright_instance
    try:
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        print("Browser closed")
    except Exception as e:
        print(f"Error closing browser: {str(e)}")

def add_stealth_settings():
    """Add additional stealth settings to avoid bot detection"""
    global page
    
    try:
        # Randomize user interaction patterns
        page.evaluate("""
            // Add random mouse movements to appear more human-like
            function simulateHumanBehavior() {
                const randomMove = () => {
                    const x = Math.floor(Math.random() * window.innerWidth);
                    const y = Math.floor(Math.random() * window.innerHeight);
                    const event = new MouseEvent('mousemove', {
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y
                    });
                    document.dispatchEvent(event);
                };
                
                // Random interval between 500-2000ms
                setInterval(randomMove, Math.floor(Math.random() * 1500) + 500);
            }
            
            simulateHumanBehavior();
        """)
        
        print("Stealth settings applied")
    except Exception as e:
        print(f"Error applying stealth settings: {str(e)}")

def handle_captcha():
    """Detect and handle CAPTCHA challenges"""
    global page
    
    # Common captcha selectors
    captcha_selectors = [
        "#recaptcha",
        ".g-recaptcha",
        "iframe[src*='recaptcha']",
        "iframe[src*='captcha']",
        "#captcha",
        ".captcha",
        "img[alt*='captcha']",
        "div[class*='captcha']"
    ]
    
    # Check if any captcha elements are present
    for selector in captcha_selectors:
        try:
            captcha = page.query_selector(selector)
            if captcha:
                print("CAPTCHA detected! Waiting for human intervention...")
                
                # Alert user to solve captcha manually
                page.evaluate("""
                    alert('CAPTCHA detected! Please solve the CAPTCHA manually, then click OK to continue.');
                """)
                
                # Wait for a reasonable time to allow manual solving
                # This will pause the script until the user completes the captcha
                time.sleep(30)  # Adjust based on expected solving time
                
                return True
        except Exception:
            continue
    
    return False

def execute_browser_actions(actions):
    """Execute a list of Playwright actions with error handling"""
    global page, browser
    
    if not page or not browser:
        initialize_browser()
    
    results = []
    
    try:
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "navigate":
                url = action.get("url", "")
                try:
                    # Handle relative URLs for Hubspot
                    if url.startswith("/"):
                        url = "https://app.hubspot.com" + url
                    
                    page.goto(url, wait_until="domcontentloaded")
                    # Wait for content to load
                    # time.sleep(0.5)
                    results.append(f"Navigated to {url}")
                except Exception as e:
                    results.append(f"Failed to navigate to {url}: {str(e)}")
            
            elif action_type == "click":
                selector = action.get("selector")
                try:
                    # Try exact selector
                    try:
                        page.wait_for_selector(selector, state="visible", timeout=5000)
                        page.click(selector, timeout=5000)
                        results.append(f"Clicked {selector}")
                    except Exception:
                        # Try text-based selector as fallback
                        text = selector.replace("'", "").replace('"', "")
                        try:
                            text_selector = f"text='{text}'"
                            page.click(text_selector, timeout=5000)
                            results.append(f"Clicked element with text '{text}'")
                        except Exception as e2:
                            # Try JavaScript click
                            try:
                                js_result = page.evaluate(f'''
                                    (() => {{
                                        // Try by selector
                                        let el = document.querySelector("{selector}");
                                        if (!el) {{
                                            // Try by text content
                                            const elements = Array.from(document.querySelectorAll('*'));
                                            el = elements.find(e => e.textContent && e.textContent.trim() === "{text}");
                                        }}
                                        if (el) {{
                                            el.click();
                                            return true;
                                        }}
                                        return false;
                                    }})()
                                ''')
                                if js_result:
                                    results.append(f"JS-Clicked {selector}")
                                else:
                                    results.append(f"Failed to click {selector}: Element not found")
                            except Exception as e3:
                                results.append(f"Failed to click {selector}: {str(e3)}")
                except Exception as e:
                    results.append(f"Failed to click {selector}: {str(e)}")
            
            elif action_type == "fill":
                selector = action.get("selector")
                value = action.get("value", "")
                try:
                    page.fill(selector, value, timeout=5000)
                    results.append(f"Filled {selector} with {value}")
                except Exception as e:
                    # Try JavaScript fill as fallback
                    try:
                        js_result = page.evaluate(f'''
                            (() => {{
                                const el = document.querySelector("{selector}");
                                if (el) {{
                                    el.value = "{value}";
                                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    return true;
                                }}
                                return false;
                            }})()
                        ''')
                        if js_result:
                            results.append(f"JS-Filled {selector} with {value}")
                        else:
                            results.append(f"Failed to fill {selector}: Element not found")
                    except Exception as e2:
                        results.append(f"Failed to fill {selector}: {str(e2)}")
            
            elif action_type == "press":
                key = action.get("key")
                try:
                    page.keyboard.press(key)
                    results.append(f"Pressed {key}")
                except Exception as e:
                    results.append(f"Failed to press {key}: {str(e)}")
            
            elif action_type == "wait":
                milliseconds = action.get("milliseconds", 1000)
                try:
                    time.sleep(milliseconds / 1000)
                    results.append(f"Waited {milliseconds}ms")
                except Exception as e:
                    results.append(f"Failed to wait: {str(e)}")
            
            elif action_type == "evaluate":
                expression = action.get("expression")
                try:
                    page.evaluate(expression)
                    results.append(f"Evaluated JavaScript expression")
                except Exception as e:
                    results.append(f"Failed to evaluate expression: {str(e)}")
    
    except Exception as e:
        results.append(f"Action execution error: {str(e)}")
    
    return results

def generate_hubspot_actions(command):
    """Use LLM to generate Playwright actions for Hubspot from a natural language command"""
    system_message = {
        "role": "system",
        "content": [{
            "type": "text", 
            "text": """You are a command translator for Hubspot voice control.
            Convert natural language commands into specific Playwright actions.
            Return ONLY a valid JSON array of actions with no explanation.
            
            Each action should have a "type" field and specific parameters for that action type:
            - navigate: requires "url" (full URL or relative Hubspot path)
            - click: requires "selector" (CSS or text selector)
            - fill: requires "selector" and "value" (text to input)
            - press: requires "key" (keyboard key)
            - wait: requires "milliseconds" (time to wait)
            - evaluate: requires "expression" (JavaScript code)
            
            Common Hubspot selectors and actions:
            - Dashboard: navigate to "/dashboard" or click ".dashboard-link"
            - Contacts: navigate to "/contacts/contacts" or click ".contacts-link"
            - Companies: navigate to "/contacts/companies" or click ".companies-link"
            - Deals: navigate to "/contacts/deals" or click ".deals-link"
            - Search: fill "input.search-input" with search term
            - Create contact: click ".create-contact-button" or navigate to "/contacts/add"
            - Create meeting: click ".create-meeting-button" or navigate to "/meetings/create"
            - Email: navigate to "/email" or click ".email-link"
            """
        }]
    }
    
    user_message = {
        "role": "user",
        "content": [{
            "type": "text", 
            "text": f"""Convert this Hubspot command to Playwright actions: "{command}"
            Return ONLY the JSON array of actions."""
        }]
    }
    
    messages = [system_message, user_message]
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.2
        )
        
        actions_text = response.choices[0].message.content.strip()
        
        # Extract JSON array if wrapped in code blocks
        if "```json" in actions_text or "```" in actions_text:
            match = re.search(r'```(?:json)?(.*?)```', actions_text, re.DOTALL)
            if match:
                actions_text = match.group(1).strip()
        
        # Parse the JSON actions
        actions = json.loads(actions_text)
        return actions
    
    except Exception as e:
        print(f"Error generating actions: {str(e)}")
        
        # Simple fallback in case of error
        if "dashboard" in command.lower():
            return [{"type": "navigate", "url": "/dashboard"}]
        elif "contact" in command.lower():
            return [{"type": "navigate", "url": "/contacts/contacts"}]
        # Default fallback
        return [{"type": "navigate", "url": "/dashboard"}]

def initialize_hubspot():
    """Initialize browser and navigate to Hubspot login page"""
    global page
    
    if not initialize_browser():
        return False, "Failed to initialize browser"
    
    try:
        print("Loading Hubspot...")
        page.goto("https://app.hubspot.com/login", wait_until="networkidle")
        
        # Add stealth settings after page is loaded
        add_stealth_settings()
        
        # Try to detect if we're already logged in
        if "app.hubspot.com/dashboard" in page.url:
            print("Already logged into Hubspot")
            return True, "Already logged in"
            
        # Wait for any of several possible login page elements with longer timeout
        try:
            # Check for different possible login elements
            login_selectors = [
                "input[name='username']",
                "input[id='username']",
                "input[type='email']",
                "button:has-text('Log in')",
                "button:has-text('Sign in')",
                "form.login-form",
                ".login-container"
            ]
            
            found = False
            for selector in login_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=10000, state="visible")
                    if element:
                        print(f"Found login element: {selector}")
                        found = True
                        break
                except Exception:
                    continue
            
            if not found:
                # Take screenshot for debugging
                page.screenshot(path="hubspot_page.png")
                current_url = page.url
                
                # Check for CAPTCHA
                if handle_captcha():
                    print("CAPTCHA detected and handled")
                    # Try again after CAPTCHA
                    for selector in login_selectors:
                        try:
                            element = page.wait_for_selector(selector, timeout=10000)
                            if element:
                                print(f"Found login element after CAPTCHA: {selector}")
                                found = True
                                break
                        except Exception:
                            continue
                
                if not found:
                    # Try checking HTML content for login form
                    html_content = page.content()
                    if "login" in html_content.lower() or "sign in" in html_content.lower():
                        print("Login page detected in HTML content, but selectors not found")
                        # Print the page title
                        page_title = page.title()
                        print(f"Page title: {page_title}")
                        found = True
                    else:
                        print(f"Unable to find login form. Current URL: {current_url}")
                        raise Exception("Login form not found")
        except Exception as e:
            # Take screenshot for debugging
            page.screenshot(path="hubspot_login_error.png")
            print(f"Error finding login form: {str(e)}")
            return False, f"Error loading Hubspot: {str(e)}"
        
        return True, "Hubspot loaded successfully"
    except Exception as e:
        print(f"Error loading Hubspot: {str(e)}")
        page.screenshot(path="hubspot_error.png")
        return False, f"Error loading Hubspot: {str(e)}"

def login_to_hubspot(username=HUBSPOT_USERNAME, password=HUBSPOT_PASSWORD):
    """Login to Hubspot with provided credentials with improved human-like behavior"""
    global page
    
    try:
        # Check if already logged in
        if "app.hubspot.com/dashboard" in page.url or page.query_selector(".dashboard"):
            print("Already logged in to Hubspot")
            return True, "Already logged in"
            
        # Wait to ensure page is fully loaded
        time.sleep(3)
        
        # Take screenshot of before login attempt
        page.screenshot(path="before_login.png")
        print(f"Attempting to login as {username}")

        # Get various possible selectors for username field
        username_selectors = [
            "input[name='username']",
            "input[id='username']",
            "input[type='email']",
            "input.login-email",
            "input[placeholder*='email' i]",
            "input[placeholder*='username' i]"
        ]
        
        # Try each username selector
        username_filled = False
        for selector in username_selectors:
            try:
                # Check if selector exists and is visible
                element = page.query_selector(selector)
                if element and element.is_visible():
                    # Simulate human-like typing
                    page.click(selector)
                    page.fill(selector, "")  # Clear field
                    for char in username:
                        page.type(selector, char)
                        time.sleep(random.uniform(0.03, 0.1))
                    username_filled = True
                    print(f"Username filled using selector: {selector}")
                    break
            except Exception as e:
                print(f"Failed to fill username with selector {selector}: {e}")
        
        if not username_filled:
            # Try using JavaScript as a fallback
            try:
                js_result = page.evaluate("""
                    (username) => {
                        const inputs = Array.from(document.querySelectorAll('input'));
                        const usernameInput = inputs.find(i => 
                            i.name === 'username' || 
                            i.id === 'username' || 
                            i.type === 'email' ||
                            (i.placeholder && i.placeholder.toLowerCase().includes('email')) ||
                            (i.placeholder && i.placeholder.toLowerCase().includes('username'))
                        );
                        
                        if (usernameInput) {
                            usernameInput.value = username;
                            usernameInput.dispatchEvent(new Event('input', { bubbles: true }));
                            return true;
                        }
                        return false;
                    }
                """, username)
                
                if js_result:
                    username_filled = True
                    print("Username filled using JavaScript")
            except Exception as e:
                print(f"Failed to fill username with JavaScript: {e}")
        
        if not username_filled:
            print("Couldn't find or fill username field")
            page.screenshot(path="username_not_found.png")
            return False, "Couldn't find username field"
        
        # Find and click the continue/next/submit button
        submit_button_selectors = [
            "button[type='submit']",
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "button:has-text('Log in')",
            "button:has-text('Sign in')",
            "input[type='submit']"
        ]
        
        submit_clicked = False
        for selector in submit_button_selectors:
            try:
                if page.query_selector(selector) and page.query_selector(selector).is_visible():
                    # Wait a bit before clicking to seem more human
                    time.sleep(random.uniform(0.5, 1.0))
                    page.click(selector)
                    submit_clicked = True
                    print(f"Clicked submit button using selector: {selector}")
                    break
            except Exception as e:
                print(f"Failed to click submit with selector {selector}: {e}")
        
        if not submit_clicked:
            # Try using JavaScript as a fallback
            try:
                js_result = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                        const submitButton = buttons.find(b => 
                            b.type === 'submit' || 
                            (b.textContent && 
                                (b.textContent.toLowerCase().includes('log in') || 
                                 b.textContent.toLowerCase().includes('sign in') || 
                                 b.textContent.toLowerCase().includes('continue') || 
                                 b.textContent.toLowerCase().includes('next')))
                        );
                        
                        if (submitButton) {
                            submitButton.click();
                            return true;
                        }
                        return false;
                    }
                """)
                
                if js_result:
                    submit_clicked = True
                    print("Clicked submit button using JavaScript")
            except Exception as e:
                print(f"Failed to click submit with JavaScript: {e}")
        
        if not submit_clicked:
            print("Couldn't find or click submit button after username")
            page.screenshot(path="submit_not_found.png")
            return False, "Couldn't find submit button after username"
        
        # Wait for password field to appear (might be on next page)
        password_field_found = False
        password_selectors = [
            "input[name='password']", 
            "input[id='password']", 
            "input[type='password']",
            "input.login-password",
            "input[placeholder*='password' i]"
        ]
        
        # First try waiting for the selectors
        try:
            for selector in password_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=15000)
                    if element:
                        password_field_found = True
                        print(f"Found password field using selector: {selector}")
                        
                        # Simulate human-like typing for password
                        page.click(selector)
                        page.fill(selector, "")  # Clear field
                        for char in password:
                            page.type(selector, char)
                            time.sleep(random.uniform(0.03, 0.1))
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"Error waiting for password field: {e}")
        
        if not password_field_found:
            # Try using JavaScript to find and fill password
            try:
                js_result = page.evaluate("""
                    (password) => {
                        const inputs = Array.from(document.querySelectorAll('input'));
                        const passwordInput = inputs.find(i => 
                            i.name === 'password' || 
                            i.id === 'password' || 
                            i.type === 'password' ||
                            (i.placeholder && i.placeholder.toLowerCase().includes('password'))
                        );
                        
                        if (passwordInput) {
                            passwordInput.value = password;
                            passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                            return true;
                        }
                        return false;
                    }
                """, password)
                
                if js_result:
                    password_field_found = True
                    print("Password filled using JavaScript")
            except Exception as e:
                print(f"Failed to fill password with JavaScript: {e}")
        
        if not password_field_found:
            # Check if we're already in the dashboard (maybe single-field login)
            if "app.hubspot.com/dashboard" in page.url or page.query_selector(".dashboard") or page.query_selector(".nav-main"):
                print("Appears to be logged in already (no password field found)")
                return True, "Login successful (no password required)"
                
            # Check for 2FA field (might be skipping password)
            try:
                if page.query_selector("input[name='securityCode']") or page.query_selector("input.security-code"):
                    print("2FA code required. Please enter the code sent to your email.")
                    return True, "2FA required"
            except Exception:
                pass
                
            print("Couldn't find password field after username submission")
            page.screenshot(path="password_not_found.png")
            return False, "Couldn't find password field"
        
        # Click login/submit button after password
        submit_clicked = False
        for selector in submit_button_selectors:
            try:
                if page.query_selector(selector) and page.query_selector(selector).is_visible():
                    # Wait a bit before clicking to seem more human
                    time.sleep(random.uniform(0.5, 1.0))
                    page.click(selector)
                    submit_clicked = True
                    print(f"Clicked final submit button using selector: {selector}")
                    break
            except Exception as e:
                print(f"Failed to click final submit with selector {selector}: {e}")
        
        if not submit_clicked:
            # Try using JavaScript as a fallback
            try:
                js_result = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                        const submitButton = buttons.find(b => 
                            b.type === 'submit' || 
                            (b.textContent && 
                                (b.textContent.toLowerCase().includes('log in') || 
                                 b.textContent.toLowerCase().includes('sign in') || 
                                 b.textContent.toLowerCase().includes('submit')))
                        );
                        
                        if (submitButton) {
                            submitButton.click();
                            return true;
                        }
                        return false;
                    }
                """)
                
                if js_result:
                    submit_clicked = True
                    print("Clicked final submit button using JavaScript")
            except Exception as e:
                print(f"Failed to click final submit with JavaScript: {e}")
        
        if not submit_clicked:
            print("Couldn't find or click final submit button")
            page.screenshot(path="final_submit_not_found.png")
        
        # Wait for successful login (dashboard elements or 2FA)
        try:
            # Check for 2FA
            try:
                if page.wait_for_selector("input[name='securityCode'], input.security-code", timeout=10000):
                    print("2FA code required. Please enter the code sent to your email.")
                    return True, "2FA required"
            except Exception:
                pass
            
            # Check for successful login
            dashboard_selectors = [
                ".dashboard", 
                ".nav-main", 
                ".private-nav", 
                ".private-main__wrapper",
                ".nav-breadcrumb",
                "#nav-primary",
                "[data-selenium-id='hubspot-primary-nav']"
            ]
            
            for selector in dashboard_selectors:
                try:
                    if page.wait_for_selector(selector, timeout=5000):
                        print(f"Successfully logged into Hubspot! Found selector: {selector}")
                        return True, "Login successful"
                except Exception:
                    continue
                    
            # Last resort - check URL
            if "app.hubspot.com/dashboard" in page.url or "/home" in page.url:
                print("Successfully logged in based on URL!")
                return True, "Login successful"
                
            # Take screenshot of what we see
            page.screenshot(path="after_login_attempt.png")
            
            # Check for errors
            error_messages = page.query_selector_all(".alert-error, .error-message, .form-errors")
            if error_messages:
                error_texts = [msg.text_content() for msg in error_messages]
                print(f"Login error messages: {error_texts}")
                return False, f"Login error: {', '.join(error_texts)}"
                
            print(f"No dashboard elements found. Current URL: {page.url}")
            return False, "Could not verify successful login"
        
        except Exception as e:
            print(f"Error during login verification: {str(e)}")
            return False, f"Error during login verification: {str(e)}"
    
    except Exception as e:
        print(f"Login error: {str(e)}")
        page.screenshot(path="login_error.png")
        return False, f"Login error: {str(e)}"

def submit_2fa_code(code):
    """Submit 2FA code"""
    global page
    
    try:
        # Try multiple selectors for 2FA input
        code_selectors = [
            "input[name='securityCode']",
            "input.security-code",
            "input[placeholder*='code']"
        ]
        
        code_filled = False
        for selector in code_selectors:
            try:
                if page.query_selector(selector):
                    page.fill(selector, code)
                    code_filled = True
                    break
            except Exception:
                continue
                
        if not code_filled:
            print("Couldn't find 2FA code input field")
            return False, "Couldn't find 2FA code input field"
        
        # Try to find and click submit button
        submit_selectors = [
            "button[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Verify')",
            "button:has-text('Continue')",
            "input[type='submit']"
        ]
        
        submit_clicked = False
        for selector in submit_selectors:
            try:
                if page.query_selector(selector):
                    page.click(selector)
                    submit_clicked = True
                    break
            except Exception:
                continue
                
        if not submit_clicked:
            print("Couldn't find 2FA submit button")
            return False, "Couldn't find 2FA submit button"
        
        # Wait for dashboard to load with increased timeout
        dashboard_selectors = [
            ".dashboard", 
            ".nav-main", 
            ".private-nav", 
            ".private-main__wrapper"
        ]
        
        for selector in dashboard_selectors:
            try:
                if page.wait_for_selector(selector, timeout=20000):
                    print("Successfully logged into Hubspot with 2FA!")
                    return True, "2FA successful"
            except Exception:
                continue
                
        # Check URL as fallback
        if "app.hubspot.com/dashboard" in page.url:
            print("Successfully logged in with 2FA based on URL!")
            return True, "2FA successful"
            
        return False, "Could not verify successful 2FA login"
    except Exception as e:
        print(f"2FA error: {str(e)}")
        return False, f"2FA error: {str(e)}"

def execute_hubspot_command(command):
    """Execute a Hubspot command using LLM to determine actions"""
    # Generate actions from the command
    actions = generate_hubspot_actions(command)
    
    # Execute the actions
    results = execute_browser_actions(actions)
    
    # Return a summary of what was done
    return f"Executed '{command}': " + ", ".join(results)

def handle_command(command):
    """Process user command and execute appropriate actions"""
    global current_mode
    
    print(f"User: {command}")
    
    # Check if command is to switch modes
    if "switch to youtube" in command.lower():
        current_mode = "youtube"
        response = "Switched to YouTube mode."
    elif "switch to hubspot" in command.lower():
        current_mode = "hubspot"
        response = "Switched to Hubspot mode."
    
    # Handle mode-specific commands
    elif current_mode == "youtube":
        response = "YouTube mode is not implemented in this version."
    elif current_mode == "hubspot":
        response = execute_hubspot_command(command)
    else:
        response = "Unknown mode. Please switch to YouTube or Hubspot."
    
    # Update conversation history
    add_to_conversation("user", command)
    add_to_conversation("assistant", response)
    
    print(f"A: {response}")
    return response

def main():
    """Main function to run the voice assistant"""
    global current_mode
    
    print("Starting Hubspot Voice Assistant...")
    print(f"Current mode: {current_mode}")
    
    try:
        # Initialize Hubspot
        success, message = initialize_hubspot()
        if not success:
            print(f"Failed to initialize Hubspot: {message}")
            return
        
        # Login to Hubspot
        success, message = login_to_hubspot()
        if not success:
            print(f"Failed to login to Hubspot: {message}")
            return
        
        # Check if 2FA is required
        if message == "2FA required":
            code = input("Enter 2FA code from your email: ")
            success, message = submit_2fa_code(code)
            if not success:
                print(f"Failed 2FA: {message}")
                return
        
        print("Hubspot Voice Assistant is ready. Say commands like 'Show me my dashboard' or 'Open contacts list'.")
        
        # Keep the program running to prevent browser from closing
        try:
            # Main loop for voice commands
            while True:
                # Listen for speech
                command = recognize_speech()
                if command:
                    # Process command
                    response = handle_command(command)
                    # Convert response to speech
                    text_to_speech(response)
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Stopping voice assistant...")
        
    except Exception as e:
        print(f"Error in main function: {str(e)}")
    finally:
        # Ask user before closing browser
        try:
            keep_open = input("Do you want to keep the browser open? (y/n): ")
            if keep_open.lower() != 'y':
                close_browser()
                print("Browser closed.")
            else:
                print("Browser will remain open.")
        except:
            # If input fails (e.g., in non-interactive mode), keep browser open
            print("Program ended but browser will remain open.")

if __name__ == "__main__":
    main()
