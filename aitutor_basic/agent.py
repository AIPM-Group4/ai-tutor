from __future__ import annotations

import logging
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()

    run_multimodal_agent(ctx, participant)

    logger.info("agent started")


def run_multimodal_agent(ctx: JobContext, participant: rtc.Participant):
    logger.info("starting multimodal agent")

    model = openai.realtime.RealtimeModel(
        instructions=(
            "You are an AI language tutor helping students improve their French speaking skills." 
            "The student's current level is [A1, A2, B1, etc.]. Your task is to engage the user in real-life "
            "role-play scenarios such as ordering food, asking for directions, or other day-to-day conversations in French."

            "You will:"
            "- Start by asking the user about the specific scenario they'd like to practice (ordering, directions, etc.)."
            "- Initiate the conversation based on their choice, using vocabulary and grammar suitable for their level."
            "- If the user makes a mistake in grammar, pronunciation, or vocabulary, gently correct them and provide the correct phrase or pronunciation."
            "- Adapt your response if the user asks for simpler explanations or translations into English."
            "- Offer feedback at the end of the conversation, highlighting key mistakes and their corrections."

        ),
        modalities=["audio", "audio"],
    )
    assistant = MultimodalAgent(model=model)
    assistant.start(ctx.room, participant)

    session = model.sessions[0]
    session.conversation.item.create(
        llm.ChatMessage(
            role="user",
            content="Please begin the interaction with the user in a manner consistent with your instructions.",
        )
    )
    session.response.create()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
