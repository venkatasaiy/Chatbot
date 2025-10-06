import os
import json
import threading
import time
import datetime
import pygame
from tkinter import *
from tkinter import ttk, messagebox
from groq import Groq
from cohere import Client as CohereClient
from dotenv import dotenv_values
import edge_tts
import asyncio
import random
import mtranslate as mt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "CyberAI")
GroqAPIKEY = env_vars.get("GroqAPIKEY")
CohereAPIKey = env_vars.get("CohereAPIKey")
InputLanguage = env_vars.get("InputLanguage", "en-US")
AssistantVoice = env_vars.get("AssistantVoice", "en-US-JennyNeural")

# Cyberpunk Neon Theme Colors
CYBERPUNK_COLORS = {
    "background": "#0a0a12",
    "card_bg": "#12121f",
    "accent": "#00f3ff",  # Cyan neon
    "accent_secondary": "#ff00f7",  # Magenta neon
    "text": "#e0e0ff",
    "text_dim": "#8a8ab0",
    "success": "#00ff9d",
    "warning": "#ff9d00",
    "error": "#ff3864"
}

# Initialize Groq client
client = Groq(api_key=GroqAPIKEY) if GroqAPIKEY else None
cohere_client = CohereClient(api_key=CohereAPIKey) if CohereAPIKey else None

# Create necessary directories
os.makedirs("Data", exist_ok=True)
os.makedirs("Frontend/Files", exist_ok=True, mode=0o777)

class CyberpunkChatbot:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{Assistantname} - Cyberpunk AI Assistant")
        self.root.geometry("1000x700")
        self.root.configure(bg=CYBERPUNK_COLORS["background"])
        
        # Set up main layout
        self.setup_layout()
        
        # Initialize components
        self.initialize_chatbot()
        self.initialize_speech_recognition()
        self.initialize_tts()
        
        # Chat state variables
        self.is_voice_mode = False
        self.is_listening = False
        self.chat_history = []
        self.current_mode = "text"  # text or voice
        self.typing_indicator = None
        self.is_speaking = False
        self.stop_speaking_flag = False
        
        # Start listening for voice commands if in voice mode
        self.root.after(100, self.check_voice_mode)
        
        # Bind keyboard shortcuts
        self.root.bind('<Return>', self.send_message)
        self.root.bind('<Control-v>', self.toggle_mode)
        
        # Load chat history
        self.load_chat_history()
        
    def setup_layout(self):
        """Set up the Cyberpunk-themed UI layout"""
        # Main container
        self.main_container = Frame(self.root, bg=CYBERPUNK_COLORS["background"])
        self.main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.header_frame = Frame(self.main_container, bg=CYBERPUNK_COLORS["card_bg"])
        self.header_frame.pack(fill=X, pady=(0, 15))
        
        # Header content with neon glow effect
        self.header_label = Label(
            self.header_frame, 
            text=f"// {Assistantname} AI SYSTEM //",
            font=("Courier New", 16, "bold"),
            fg=CYBERPUNK_COLORS["accent"],
            bg=CYBERPUNK_COLORS["card_bg"]
        )
        self.header_label.pack(pady=10, padx=15)
        self.header_label.bind("<Enter>", self.add_glow)
        self.header_label.bind("<Leave>", self.remove_glow)
        
        # Status bar
        self.status_frame = Frame(self.header_frame, bg=CYBERPUNK_COLORS["card_bg"])
        self.status_frame.pack(fill=X, padx=15, pady=(5, 10))
        
        self.status_label = Label(
            self.status_frame,
            text="STATUS: READY | MODE: TEXT",
            font=("Courier New", 10),
            fg=CYBERPUNK_COLORS["success"],
            bg=CYBERPUNK_COLORS["card_bg"]
        )
        self.status_label.pack(side=LEFT)
        
        self.mode_button = Button(
            self.status_frame,
            text="SWITCH TO VOICE MODE",
            font=("Courier New", 9, "bold"),
            fg=CYBERPUNK_COLORS["text"],
            bg=CYBERPUNK_COLORS["card_bg"],
            activebackground=CYBERPUNK_COLORS["accent_secondary"],
            bd=1,
            relief="solid",
            highlightbackground=CYBERPUNK_COLORS["accent"],
            command=self.toggle_mode
        )
        self.mode_button.pack(side=RIGHT, padx=5)
        
        # Chat display area
        self.chat_frame = Frame(self.main_container, bg=CYBERPUNK_COLORS["card_bg"])
        self.chat_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        
        # Add scrollable chat area
        self.chat_canvas = Canvas(
            self.chat_frame, 
            bg=CYBERPUNK_COLORS["card_bg"],
            highlightthickness=0
        )
        self.chat_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(
            self.chat_frame, 
            orient="vertical", 
            command=self.chat_canvas.yview
        )
        self.scrollbar.pack(side=RIGHT, fill=Y)
        
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Frame inside canvas for messages
        self.messages_frame = Frame(self.chat_canvas, bg=CYBERPUNK_COLORS["card_bg"])
        self.canvas_window = self.chat_canvas.create_window(
            (0, 0), 
            window=self.messages_frame, 
            anchor="nw",
            width=self.chat_canvas.winfo_width()
        )
        
        # Configure canvas scrolling
        self.messages_frame.bind("<Configure>", self.on_frame_configure)
        self.chat_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Input area
        self.input_frame = Frame(self.main_container, bg=CYBERPUNK_COLORS["card_bg"])
        self.input_frame.pack(fill=X)
        
        # Input field with neon border
        self.input_entry = Entry(
            self.input_frame,
            font=("Consolas", 12),
            fg=CYBERPUNK_COLORS["text"],
            bg=CYBERPUNK_COLORS["background"],
            insertbackground=CYBERPUNK_COLORS["accent"],
            relief="solid",
            bd=2,
            highlightbackground=CYBERPUNK_COLORS["accent_secondary"],
            highlightcolor=CYBERPUNK_COLORS["accent"],
            highlightthickness=1
        )
        self.input_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10), pady=5, ipady=8)
        self.input_entry.focus()
        
        # Send button with neon glow
        self.send_button = Button(
            self.input_frame,
            text="SEND",
            font=("Courier New", 10, "bold"),
            fg=CYBERPUNK_COLORS["text"],
            bg=CYBERPUNK_COLORS["card_bg"],
            activebackground=CYBERPUNK_COLORS["accent"],
            bd=1,
            relief="solid",
            highlightbackground=CYBERPUNK_COLORS["accent"],
            width=8,
            command=self.send_message
        )
        self.send_button.pack(side=RIGHT, pady=5)
        self.send_button.bind("<Enter>", self.add_glow)
        self.send_button.bind("<Leave>", self.remove_glow)
        
        # Voice control button (initially hidden)
        self.voice_button = Button(
            self.input_frame,
            text="LISTEN ▶",
            font=("Courier New", 10, "bold"),
            fg=CYBERPUNK_COLORS["text"],
            bg=CYBERPUNK_COLORS["card_bg"],
            activebackground=CYBERPUNK_COLORS["accent_secondary"],
            bd=1,
            relief="solid",
            highlightbackground=CYBERPUNK_COLORS["accent_secondary"],
            width=10,
            command=self.toggle_voice_listening
        )
        
        # Add cyberpunk styling
        self.apply_cyberpunk_styling()
        
    def apply_cyberpunk_styling(self):
        """Apply Cyberpunk Neon styling to all UI elements"""
        # Custom style for ttk widgets
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure scrollbar style
        style.configure("Vertical.TScrollbar",
                        gripcount=0,
                        background=CYBERPUNK_COLORS["card_bg"],
                        darkcolor=CYBERPUNK_COLORS["card_bg"],
                        lightcolor=CYBERPUNK_COLORS["card_bg"],
                        troughcolor=CYBERPUNK_COLORS["background"],
                        bordercolor=CYBERPUNK_COLORS["background"],
                        arrowcolor=CYBERPUNK_COLORS["accent"])
        
        # Configure progressbar style for typing indicator
        style.configure("Cyber.Horizontal.TProgressbar",
                        background=CYBERPUNK_COLORS["accent"],
                        troughcolor=CYBERPUNK_COLORS["background"])
        
        # Add glowing effect to header
        self.animate_header_glow()
        
    def animate_header_glow(self):
        """Create a pulsing glow effect for the header"""
        def pulse_glow():
            if hasattr(self, 'header_label') and self.header_label.winfo_exists():
                current_color = self.header_label.cget("fg")
                next_color = CYBERPUNK_COLORS["accent"] if current_color == CYBERPUNK_COLORS["text_dim"] else CYBERPUNK_COLORS["text_dim"]
                self.header_label.config(fg=next_color)
                self.root.after(1000, pulse_glow)
        
        pulse_glow()
    
    def add_glow(self, event):
        """Add glow effect on hover"""
        event.widget.config(highlightbackground=CYBERPUNK_COLORS["accent"])
        
    def remove_glow(self, event):
        """Remove glow effect when not hovering"""
        if event.widget == self.mode_button:
            event.widget.config(highlightbackground=CYBERPUNK_COLORS["accent"])
        elif event.widget == self.send_button:
            event.widget.config(highlightbackground=CYBERPUNK_COLORS["accent"])
    
    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        
    def on_canvas_configure(self, event):
        """Reset the canvas window to match the width of the canvas"""
        canvas_width = event.width
        self.chat_canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def initialize_chatbot(self):
        """Initialize the Groq-based chatbot"""
        # System message for the chatbot
        self.system_message = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""
        
        # Load chat history
        try:
            with open("Data/ChatLog.json", "r") as f:
                self.chat_history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.chat_history = []
            with open("Data/ChatLog.json", "w") as f:
                json.dump([], f)
    
    def initialize_speech_recognition(self):
        """Initialize the speech recognition system"""
        # Create Voice.html for speech recognition
        html_code = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <script>
        const output = document.getElementById('output');
        let recognition;
        function startRecognition() {
            recognition = new webkitSpeechRecognition() || new SpeechRecognition();
            recognition.lang = '';
            recognition.continuous = true;
            recognition.onresult = function(event) {
                const transcript = event.results[event.results.length - 1][0].transcript;
                output.textContent += transcript;
            };
            recognition.onend = function() {
                recognition.start();
            };
            recognition.start();
        }
        function stopRecognition() {
            recognition.stop();
            output.innerHTML = "";
        }
    </script>
</body>
</html>'''
        
        # Replace language setting
        html_code = html_code.replace("recognition.lang = '';", f"recognition.lang = '{InputLanguage}';")
        
        # Write to file
        with open("Data/Voice.html", "w", encoding="utf-8") as f:
            f.write(html_code)
        
        # Set up Chrome options
        chrome_options = Options()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.142.86 Safari/537.36"
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument("--use-fake-device-for-media-stream")
        chrome_options.add_argument("--headless=new")
        
        # Initialize WebDriver
        try:
            self.service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=self.service, options=chrome_options)
            self.driver.get(f"file:///{os.path.abspath('Data/Voice.html')}")
        except Exception as e:
            print(f"Error initializing speech recognition: {e}")
            self.driver = None
    
    def initialize_tts(self):
        """Initialize text-to-speech system"""
        pygame.mixer.init()
        self.is_speaking = False
        self.stop_speaking_flag = False
    
    def toggle_mode(self, event=None):
        """Toggle between text and voice modes"""
        self.is_voice_mode = not self.is_voice_mode
        
        if self.is_voice_mode:
            self.current_mode = "voice"
            self.status_label.config(text="STATUS: READY | MODE: VOICE", fg=CYBERPUNK_COLORS["accent_secondary"])
            self.mode_button.config(text="SWITCH TO TEXT MODE")
            self.input_entry.pack_forget()
            self.send_button.pack_forget()
            self.voice_button.pack(side=RIGHT, pady=5)
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, "Voice mode active - click LISTEN to start speaking")
            self.input_entry.config(state="disabled")
        else:
            self.current_mode = "text"
            self.status_label.config(text="STATUS: READY | MODE: TEXT", fg=CYBERPUNK_COLORS["success"])
            self.mode_button.config(text="SWITCH TO VOICE MODE")
            self.voice_button.pack_forget()
            self.input_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10), pady=5, ipady=8)
            self.send_button.pack(side=RIGHT, pady=5)
            self.input_entry.config(state="normal")
            self.input_entry.delete(0, END)
            self.input_entry.focus()
    
    def toggle_voice_listening(self):
        """Toggle voice listening on/off"""
        if not self.driver:
            messagebox.showerror("Error", "Speech recognition system failed to initialize")
            return
            
        if not self.is_listening:
            self.is_listening = True
            self.voice_button.config(text="STOP ■", bg=CYBERPUNK_COLORS["error"])
            self.status_label.config(text="STATUS: LISTENING...", fg=CYBERPUNK_COLORS["warning"])
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, "Listening...")
            
            # Start listening in a separate thread
            threading.Thread(target=self.process_voice_input, daemon=True).start()
        else:
            self.is_listening = False
            self.voice_button.config(text="LISTEN ▶", bg=CYBERPUNK_COLORS["card_bg"])
            self.status_label.config(text="STATUS: READY | MODE: VOICE", fg=CYBERPUNK_COLORS["accent_secondary"])
            self.driver.find_element(by=By.ID, value="end").click()
    
    def process_voice_input(self):
        """Process voice input and convert to text"""
        try:
            self.driver.find_element(by=By.ID, value="start").click()
            
            while self.is_listening:
                try:
                    text = self.driver.find_element(by=By.ID, value="output").text
                    if text:
                        self.root.after(0, lambda t=text: self.process_recognized_text(t))
                        break
                except:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error in voice recognition: {e}")
            self.root.after(0, lambda: self.reset_voice_ui())
    
    def process_recognized_text(self, text):
        """Process the recognized text and send to chatbot"""
        if InputLanguage.lower() != "en-us" and "en" not in InputLanguage.lower():
            self.status_label.config(text="STATUS: TRANSLATING...", fg=CYBERPUNK_COLORS["warning"])
            try:
                translated_text = mt.translate(text, "en", "auto")
                self.input_entry.delete(0, END)
                self.input_entry.insert(0, translated_text)
                self.send_message()
            except Exception as e:
                print(f"Translation error: {e}")
                self.input_entry.delete(0, END)
                self.input_entry.insert(0, text)
                self.send_message()
        else:
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, text)
            self.send_message()
        
        self.reset_voice_ui()
    
    def reset_voice_ui(self):
        """Reset the voice UI state"""
        self.is_listening = False
        self.root.after(0, lambda: self.voice_button.config(text="LISTEN ▶", bg=CYBERPUNK_COLORS["card_bg"]))
        self.root.after(0, lambda: self.status_label.config(text="STATUS: READY | MODE: VOICE", fg=CYBERPUNK_COLORS["accent_secondary"]))
        try:
            self.driver.find_element(by=By.ID, value="end").click()
        except:
            pass
    
    def get_real_time_info(self):
        """Get real-time date and time information"""
        now = datetime.datetime.now()
        return f"Day: {now.strftime('%A')}\nDate: {now.strftime('%d')}\nMonth: {now.strftime('%B')}\nYear: {now.strftime('%Y')}\nTime: {now.strftime('%H')}:{now.strftime('%M')}:{now.strftime('%S')}"
    
    def categorize_query(self, query):
        """Categorize the query using Cohere Decision-Making Model"""
        if not cohere_client:
            return ["general"]
            
        funcs = [
            "exit", "general", "realtime", "open", "close", "play",
            "generate image", "system", "content", "google search",
            "youtube search", "reminder"
        ]
        
        preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information...
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information...
-> Respond with 'open (application name or website name)' if a query is asking to open any application...
-> Respond with 'close (application name)' if a query is asking to close any application...
-> Respond with 'play (song name)' if a query is asking to play any song...
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt...
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder...
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc...
-> Respond with 'content (topic)' if a query is asking to write any type of content...
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google...
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube...
*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye jarvis.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""
        
        try:
            response = cohere_client.chat(
                model='command-r-plus',
                message=query,
                preamble=preamble,
                temperature=0.7
            )
            
            # Process the response
            response_text = response.text.replace("\n", "")
            response_list = [item.strip() for item in response_text.split(",")]
            
            # Filter valid categories
            categories = []
            for task in response_list:
                for func in funcs:
                    if task.startswith(func):
                        categories.append(task)
                        break
            
            return categories if categories else ["general"]
        except Exception as e:
            print(f"Error in query categorization: {e}")
            return ["general"]
    
    def send_message(self, event=None):
        """Send a message to the chatbot and display response"""
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
            
        # Clear input field
        self.input_entry.delete(0, END)
        
        # Add user message to chat
        self.add_message(user_input, "user")
        
        # Save to chat history
        self.chat_history.append({"role": "user", "content": user_input})
        
        # Save chat history
        with open("Data/ChatLog.json", "w") as f:
            json.dump(self.chat_history, f, indent=4)
        
        # Show typing indicator
        self.typing_indicator = Frame(self.messages_frame, bg=CYBERPUNK_COLORS["card_bg"])
        self.typing_indicator.pack(anchor=E, padx=10, pady=5)
        
        self.typing_label = Label(
            self.typing_indicator,
            text="TYPING...",
            font=("Courier New", 10, "bold"),
            fg=CYBERPUNK_COLORS["accent"],
            bg=CYBERPUNK_COLORS["card_bg"]
        )
        self.typing_label.pack(side=LEFT, padx=(5, 0))
        
        self.typing_bar = ttk.Progressbar(
            self.typing_indicator,
            orient=HORIZONTAL,
            mode='indeterminate',
            length=60,
            style="Cyber.Horizontal.TProgressbar"
        )
        self.typing_bar.pack(side=LEFT, padx=(5, 0))
        self.typing_bar.start(10)
        
        # Update UI
        self.root.update()
        
        # Process the message in a separate thread to avoid freezing UI
        threading.Thread(target=self.process_message, args=(user_input,), daemon=True).start()
    
    def process_message(self, user_input):
        """Process the user's message and get chatbot response"""
        try:
            # Get real-time information
            realtime_info = self.get_real_time_info()
            
            # Create message history for API call
            messages = [
                {"role": "system", "content": self.system_message},
                {"role": "system", "content": f"Real-time information:\n{realtime_info}"}
            ] + self.chat_history
            
            # Get chatbot response
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                top_p=1,
                stream=False
            )
            
            # Extract response
            response = completion.choices[0].message.content
            
            # Remove any unwanted tokens
            response = response.replace("</s>", "").strip()
            
            # Add assistant message to chat
            self.root.after(0, lambda: self.add_message(response, "assistant"))
            
            # Save to chat history
            self.chat_history.append({"role": "assistant", "content": response})
            
            # Save chat history
            with open("Data/ChatLog.json", "w") as f:
                json.dump(self.chat_history, f, indent=4)
            
            # Play response as speech if in voice mode
            if self.is_voice_mode:
                self.root.after(0, lambda: self.speak_response(response))
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.add_message(error_msg, "error"))
            print(f"Chatbot error: {e}")
        finally:
            # Remove typing indicator
            self.root.after(0, self.remove_typing_indicator)
    
    def remove_typing_indicator(self):
        """Remove the typing indicator from the chat"""
        if hasattr(self, 'typing_indicator') and self.typing_indicator and self.typing_indicator.winfo_exists():
            self.typing_indicator.destroy()
    
    def add_message(self, text, sender):
        """Add a message to the chat display with proper Tkinter anchor values"""
        # Create message frame
        msg_frame = Frame(self.messages_frame, bg=CYBERPUNK_COLORS["card_bg"])
        
        # Determine alignment and colors based on sender
        if sender == "user":
            msg_frame.pack(anchor=E, padx=10, pady=5)
            bg_color = CYBERPUNK_COLORS["accent"]
            fg_color = CYBERPUNK_COLORS["background"]
            align = "e"  # Use 'e' for east (right) instead of "right"
        elif sender == "assistant":
            msg_frame.pack(anchor=W, padx=10, pady=5)
            bg_color = CYBERPUNK_COLORS["card_bg"]
            fg_color = CYBERPUNK_COLORS["accent"]
            align = "w"  # Use 'w' for west (left) instead of "left"
        else:  # error
            msg_frame.pack(anchor=W, padx=10, pady=5)
            bg_color = CYBERPUNK_COLORS["error"]
            fg_color = CYBERPUNK_COLORS["background"]
            align = "w"  # Use 'w' for west (left) instead of "left"
        
        # Add sender label (only for assistant)
        if sender == "assistant":
            sender_label = Label(
                msg_frame,
                text=Assistantname,
                font=("Courier New", 8, "bold"),
                fg=CYBERPUNK_COLORS["accent_secondary"],
                bg=CYBERPUNK_COLORS["card_bg"]
            )
            sender_label.pack(anchor=W, padx=5, pady=(0, 2))
        
        # Add message bubble
        msg_bubble = Frame(
            msg_frame,
            bg=bg_color,
            padx=10,
            pady=8,
            relief="flat",
            bd=0
        )
        msg_bubble.pack(side=RIGHT if sender == "user" else LEFT, anchor=align)
        
        # Format long messages
        max_width = 80
        if len(text) > max_width:
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                if len(' '.join(current_line + [word])) <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            text = '\n'.join(lines)
        
        # Add message text
        msg_text = Label(
            msg_bubble,
            text=text,
            font=("Consolas", 11),
            fg=fg_color,
            bg=bg_color,
            wraplength=600,
            justify=LEFT if sender != "user" else RIGHT,
            anchor=W if sender != "user" else E
        )
        msg_text.pack(padx=5, pady=2)
        
        # Update scroll region
        self.messages_frame.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        
        # Auto-scroll to bottom
        self.chat_canvas.yview_moveto(1.0)
    
    def speak_response(self, text):
        """Convert text response to speech"""
        if self.is_speaking:
            return
            
        self.is_speaking = True
        self.stop_speaking_flag = False
        
        try:
            # Convert text to speech
            asyncio.run(self.text_to_speech_async(text))
        except Exception as e:
            print(f"Speech error: {e}")
        finally:
            self.is_speaking = False
    
    async def text_to_speech_async(self, text):
        """Async function to handle text-to-speech conversion"""
        try:
            # Create the communicate object
            communicate = edge_tts.Communicate(text, AssistantVoice, pitch='+5Hz', rate='+13%')
            
            # Generate speech file
            await communicate.save("Data/speech.mp3")
            
            # Play the audio
            pygame.mixer.music.load("Data/speech.mp3")
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy() and not self.stop_speaking_flag:
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            try:
                pygame.mixer.music.stop()
            except:
                pass
    
    def stop_speaking(self):
        """Stop the current speech playback"""
        self.stop_speaking_flag = True
    
    def load_chat_history(self):
        """Load and display chat history"""
        for message in self.chat_history:
            if message["role"] == "user":
                self.add_message(message["content"], "user")
            elif message["role"] == "assistant":
                self.add_message(message["content"], "assistant")
    
    def check_voice_mode(self):
        """Periodically check voice mode status"""
        if self.is_voice_mode and self.is_listening and not self.driver:
            self.reset_voice_ui()
            messagebox.showerror("Error", "Speech recognition system disconnected")
        
        self.root.after(1000, self.check_voice_mode)
    
    def cleanup(self):
        """Clean up resources before closing"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
            pygame.mixer.quit()
        except:
            pass

def main():
    # Create .env file if it doesn't exist with default values
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(f"""Username=User
Assistantname=CyberAI
GroqAPIKEY=your_groq_api_key_here
CohereAPIKey=your_cohere_api_key_here
InputLanguage=en-US
AssistantVoice=en-US-JennyNeural""")
        print("Created default .env file. Please edit it with your API keys.")
    
    # Initialize main window
    root = Tk()
    
    # Set window icon (optional)
    try:
        # Create a simple icon if none is available
        icon = PhotoImage(width=1, height=1)
        root.iconphoto(True, icon)
    except:
        pass
    
    # Create chatbot application
    app = CyberpunkChatbot(root)
    
    # Handle window close event
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()