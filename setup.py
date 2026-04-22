#!/usr/bin/env python3
# setup.py — Run ONCE. Copy printed IDs into .env.
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

from research_digest.session import AGENT_TOOLS

SKILL_MD = os.path.expanduser("~/.claude/skills/research-brief/SKILL.md")


def main():
    client = anthropic.Anthropic()

    with open(SKILL_MD) as f:
        skill_md = f.read()

    print("Creating agent...")
    agent = client.beta.agents.create(
        name="Research Digest Bot",
        model="claude-opus-4-7",
        system=skill_md,
        tools=AGENT_TOOLS,
    )
    print("  AGENT_ID={}".format(agent.id))
    print("  AGENT_VERSION={}".format(agent.version))

    print("Creating environment...")
    env = client.beta.environments.create(
        name="research-digest-env",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    print("  ENV_ID={}".format(env.id))

    print("\nAdd AGENT_ID and ENV_ID to your .env file.")


if __name__ == "__main__":
    main()
