import os
import sys

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import asyncio

from mlx_use import Agent
from pydantic import SecretStr
from mlx_use.controller.service import Controller
from mlx_use.agent.context_manager import create_agent_with_context


def set_llm(llm_provider: str = None):
	if not llm_provider:
		raise ValueError('No llm provider was set')

	if llm_provider == 'OAI':
		api_key = os.getenv('OPENAI_API_KEY')
		return ChatOpenAI(model='gpt-4o', api_key=SecretStr(api_key))

	if llm_provider == 'google':
		api_key = os.getenv('GEMINI_API_KEY')
		return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(api_key))


llm = set_llm('google')
llm = set_llm('OAI')


controller = Controller()

task = 'open the notes app and create a new folder called "Lunch"'


# Agent will be created in the async main function


async def main():
	agent = await create_agent_with_context(
		task=task,
		llm=llm,
		session_id='lunch_notes_session',
		controller=controller,
		use_vision=False,
		max_actions_per_step=5,
	)
	await agent.run(max_steps=25)


asyncio.run(main())
