#!/usr/bin/env python3
"""Push aws/alfred_system_prompt.md to the Alfred managed agent."""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "aws", "alfred_system_prompt.md")
AGENT_ID    = os.environ["ALFRED_AGENT_ID"]


def main():
    with open(PROMPT_PATH) as f:
        system = f.read()

    client = anthropic.Anthropic()

    current = client.beta.agents.retrieve(AGENT_ID)
    agent = client.beta.agents.update(
        agent_id=AGENT_ID,
        version=current.version,
        system=system,
    )
    print("Updated: {} v{}".format(agent.id, getattr(agent, "version", "?")))
    print("Model:   {}".format(agent.model))
    print("Prompt:  {} chars".format(len(system)))


if __name__ == "__main__":
    main()
