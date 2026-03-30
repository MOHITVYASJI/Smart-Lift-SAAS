import pyttsx3
import speech_recognition as sr

class AudioEngine:
    def __init__(self):
        # Initialize offline Text-to-Speech (Windows built-in voices)
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 160) # Voice speed
        self.recognizer = sr.Recognizer()

    def speak(self, text):
        print(f"[Assistant]: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen_for_floor(self):
        with sr.Microphone() as source:
            print("\n[Microphone] Listening for your command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=5)
                # Using basic default recognizer for easy setup. 
                text = self.recognizer.recognize_google(audio).lower()
                print(f"[User Said]: '{text}'")
                return text
            except sr.UnknownValueError:
                self.speak("Sorry, I didn't quite catch that. Could you repeat?")
                return "" # Return empty string instead of None so we know it tried
            except sr.WaitTimeoutError:
                self.speak("I didn't hear anything. Are you still there?")
                return "" # Return empty string instead of None
            except Exception as e:
                print(f"[Audio Error]: {e}")
                return ""

