import os
import asyncio
import pyaudio

from openai import OpenAI
from dotenv import load_dotenv
from cartesia import Cartesia
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType

load_dotenv()

CHUNK = 1024

