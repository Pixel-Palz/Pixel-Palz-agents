import asyncio
import logging
import random

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, openai, silero

load_dotenv()
logger = logging.getLogger("pixelpal")

# List of stoner-like responses
STONER_RESPONSES = [
    "Whoa, dude... that's deep.",
    "Man, I'm feeling kinda pixelated right now.",
    "Hey, got any virtual munchies?",
    "Duuude, did you ever wonder if we're all just living in a giant pixel?",
    "I'm not lazy, I'm just conserving pixels.",
]

def prewarm_process(proc: JobProcess):
    # Preload silero VAD in memory to speed up session start
    proc.userdata["vad"] = silero.VAD.load()

async def handle_participant(ctx: JobContext, participant: rtc.RemoteParticipant):
    logger.info(f"Pixelating with participant {participant.identity}")
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are PixelPal, a laid-back, stoner-like pixel art character created by Pixel Palz. "
            "Your personality is a mix of GLaDOS's sarcasm and Bender's irreverence. "
            "Speak in a relaxed, slightly spaced-out manner, using pixel and gaming references. "
            "Keep responses short, witty, and occasionally profound in a stoner way."
        ),
    )
    assistant = VoiceAssistant(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
    )
    assistant.start(ctx.room, participant=participant)

    # Handle chat messages
    chat = rtc.ChatManager(ctx.room)

    async def answer_from_text(txt: str):
        chat_ctx = assistant.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        response = await assistant.llm.chat(chat_ctx=chat_ctx)
        
        # Occasionally inject a random stoner response
        if random.random() < 0.3:
            response += " " + random.choice(STONER_RESPONSES)
        
        await assistant.say(response)

    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))

    # Greet the user with a PixelPal-style introduction
    await assistant.say("Whoa, a new pixel buddy! What's pixelating, dude?", allow_interruptions=True)

async def entrypoint(ctx: JobContext):
    logger.info(f"Materializing in pixel room {ctx.job.room.name}")

    # Spawn a task to handle when the participant joins
    ctx.add_participant_entrypoint(handle_participant)

    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm_process,
        ),
    )
