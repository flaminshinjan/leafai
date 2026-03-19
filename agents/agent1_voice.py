import os
import asyncio
import pyaudio

from openai import OpenAI
from dotenv import load_dotenv
from cartesia import Cartesia
from deepgram import DeepgramClient
from deepgram.core.events import EventType

load_dotenv()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class VoiceAgent:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cartesia = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))
        self.deepgram = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
        self.pa = pyaudio.PyAudio()

        self.is_speaking = False
        self.final_transcript = ""

        self.history =[
            {
                "role": "system",
                "content": (
                    "You are a professional enterprise support agent for Feather AI. "
                    "Help customers with billing, accounts, and support. "
                    "Keep responses under 2 sentences — this is a voice call, not a chat. Never use bullet points or markdown."
                ),
            }
        ]
    def speak(self, text: str ):
        self.is_speaking = True
        print(f"\n🤖 Agent: {text}\n")

        audio_buffer = b""
        for chunk in self.cartesia.tts.sse(
            model_id="sonic-english",
            transcript=text,
            voice={"mode": "id", "id": "a0e99841-438c-4a64-b679-ae501e7d6091"},
            output_format={
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": RATE,
            },
        ):
            if hasattr(chunk, "audio") and chunk.audio:
                audio_buffer += chunk.audio
        out = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            output=True,
        )
        out.write(audio_buffer)
        out.stop_stream()
        out.close()

        self.is_speaking = False        

    
    def get_llm_response(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.history,
            max_tokens=100,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": reply})
        return reply


    def run(self):
        import threading

        print("🎙️  Voice Agent starting... (say 'bye' to stop)\n")

        with self.deepgram.listen.v1.connect(
            model="nova-3",
            encoding="linear16",
            sample_rate=16000,
        ) as connection:

            def on_message(message) -> None:
                if hasattr(message, "channel") and hasattr(message.channel, "alternatives"):
                    transcript = message.channel.alternatives[0].transcript
                    if getattr(message, "is_final", False) and transcript.strip():
                        self.final_transcript = transcript

            connection.on(EventType.OPEN,  lambda _: print("[Deepgram] Connected"))
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, lambda _: print("[Deepgram] Closed"))
            connection.on(EventType.ERROR, lambda e: print(f"[Deepgram] Error: {e}"))

            def listen_thread():
                try:
                    connection.start_listening()
                except Exception as e:
                    print(f"[Listen thread] {e}")

            t = threading.Thread(target=listen_thread)
            t.start()

            mic = self.pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            self.speak("Hello! I'm your Feather AI support agent. How can I help you today?")

            while True:
                if not self.is_speaking:
                    data = mic.read(CHUNK, exception_on_overflow=False)
                    connection.send_media(data)
                else:
                    silence = b'\x00' * CHUNK * 2
                    connection.send_media(silence)

                if self.final_transcript:
                    user_text = self.final_transcript
                    self.final_transcript = ""
                    print(f"👤 User: {user_text}")

                    if user_text.lower().strip() in {"bye", "exit", "quit", "goodbye"}:
                        self.speak("Goodbye! Have a great day.")
                        break

                    reply = self.get_llm_response(user_text)
                    self.speak(reply)

            mic.stop_stream()
            mic.close()
            self.pa.terminate()
            print("\n[Agent stopped]")

def run_agent():
    agent = VoiceAgent()
    agent.run()

