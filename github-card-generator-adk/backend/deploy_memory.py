"""
deploy_memory.py — Set up Vertex AI Agent Engine with Memory Bank
Run once to get AGENT_ENGINE_ID, then add it to your .env
"""

import os
import sys

def main():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("❌ GOOGLE_CLOUD_PROJECT not set.")
        sys.exit(1)

    try:
        import vertexai
        from vertexai.preview import reasoning_engines
    except ImportError:
        print("❌ vertexai package not installed.")
        print("   Run: pip install google-cloud-aiplatform[adk,agent_engines]")
        sys.exit(1)

    print(f"🧠 Creating Vertex AI Agent Engine in project: {project}")
    vertexai.init(project=project, location="us-central1")

    # Create a reasoning engine (Agent Engine) for memory
    engine = reasoning_engines.ReasoningEngine.create(
        reasoning_engines.AdkApp(
            agent=None,  # Will be set at runtime
            enable_tracing=True,
        ),
        requirements=["google-adk", "httpx", "fastmcp"],
        display_name="github-card-generator-memory",
        description="Memory bank for GitHub Dev Card Generator — stores user card preferences",
    )

    engine_id = engine.resource_name.split("/")[-1]

    print(f"✅ Agent Engine created!")
    print(f"   Resource: {engine.resource_name}")
    print(f"   Engine ID: {engine_id}")
    print("")
    print(f"   Add to your .env:")
    print(f"   AGENT_ENGINE_ID={engine_id}")

    return engine_id


if __name__ == "__main__":
    main()
