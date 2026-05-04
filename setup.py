#!/usr/bin/env python3
# setup.py — Run ONCE. Copy printed IDs into .env.
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

from research_digest.session import AGENT_TOOLS

SKILL_MD = os.path.expanduser("~/.claude/skills/research-brief/SKILL.md")
ALFRED_PROMPT_MD = os.path.expanduser("~/docs/superpowers/alfred-bot/alfred-oneshot-prompt.md")


def main():
    client = anthropic.Anthropic()

    with open(SKILL_MD) as f:
        skill_md = f.read()

    with open(ALFRED_PROMPT_MD) as f:
        alfred_prompt = f.read()

    print("Creating research digest agent...")
    agent = client.beta.agents.create(
        name="Research Digest Bot",
        model="claude-opus-4-7",
        system=skill_md,
        tools=AGENT_TOOLS,
    )
    print("  AGENT_ID={}".format(agent.id))
    print("  AGENT_VERSION={}".format(agent.version))

    print("Creating Alfred agent...")
    alfred = client.beta.agents.create(
        name="Alfred Paper Assistant",
        model="claude-sonnet-4-6",
        system=alfred_prompt,
        tools=[{"type": "agent_toolset_20260401"}],
    )
    print("  ALFRED_AGENT_ID={}".format(alfred.id))
    print("  ALFRED_AGENT_VERSION={}".format(alfred.version))

    print("Creating environment...")
    env = client.beta.environments.create(
        name="research-digest-env",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    print("  ENV_ID={}".format(env.id))

    print("\nAdd AGENT_ID, ALFRED_AGENT_ID, and ENV_ID to your .env file.")


if __name__ == "__main__":
    main()
