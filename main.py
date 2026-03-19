import asyncio
import sys

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    agent = sys.argv[1].lower()

    if agent == "voice":
        from agents.voice_agent import run_agent
        run_agent()

    elif agent == "tools":
        from agents.agent2_tools import run_agent
        run_agent()

    elif agent == "orchestrator":
        from agents.agent3_orchestrator import run_agent
        asyncio.run(run_agent())

    else:
        print("Choose from: voice, tools, orchestrator")
        sys.exit(1)

if __name__ == "__main__":
    main()