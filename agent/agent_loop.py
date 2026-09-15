import logging
from typing import Dict, Any, List, Optional
from mcp_client.client import FinanceMCPClient
from mcp_client.tool_discovery import ToolDiscoverer
from agent.llm_policy import LLMPolicy
from agent.observations import ObservationTracker
from agent.schemas import AgentResponse
from reflection.evaluator import ReflectionEvaluator

logger = logging.getLogger("SmartFinanceAgent")

MAX_ITERATIONS = 5

class GoalBasedFinanceAgent:
    """Goal-Based Tool-Calling Agent with dynamic iteration loop, MCP client, and Reflection layer."""

    def __init__(
        self,
        mcp_client: Optional[FinanceMCPClient] = None,
        llm_policy: Optional[LLMPolicy] = None,
        evaluator: Optional[ReflectionEvaluator] = None
    ):
        self.mcp_client = mcp_client or FinanceMCPClient()
        self.tool_discoverer = ToolDiscoverer(self.mcp_client)
        self.llm_policy = llm_policy or LLMPolicy()
        self.evaluator = evaluator or ReflectionEvaluator()

    async def run(self, question: str) -> AgentResponse:
        """Execute the dynamic agent loop for a user natural-language financial question."""
        print("\n" + "=" * 60)
        print("SMART FINANCE AGENT - GOAL-BASED AGENT LOOP")
        print("=" * 60)
        print(f"USER QUESTION:\n\"{question}\"\n")

        # Step 1: Connect & Discover MCP Tools
        print("MCP SERVER & HANDSHAKE:")
        tools = await self.tool_discoverer.discover_tools()
        print("✓ Connected to MCP Server via stdio protocol")
        print("✓ MCP Handshake successful")
        
        tool_names = [t["name"] for t in tools]
        print(f"TOOLS DISCOVERED ({len(tools)}):")
        for tname in tool_names:
            print(f"  • {tname}")
        print("-" * 60)

        tools_formatted = self.tool_discoverer.format_tools_for_prompt(tools)
        observation_tracker = ObservationTracker()

        iterations_count = 0
        final_draft_answer = ""
        tools_used: List[str] = []

        # Step 2: Dynamic Agent Iteration Loop
        for iteration in range(1, MAX_ITERATIONS + 1):
            iterations_count = iteration
            print(f"\n[ITERATION {iteration}/{MAX_ITERATIONS}]")

            # LLM policy decision
            action_decision = await self.llm_policy.decide_next_action(
                question=question,
                tools_formatted=tools_formatted,
                observation_tracker=observation_tracker,
                iteration=iteration
            )

            if action_decision.action == "tool_call":
                t_name = action_decision.tool_name
                args = action_decision.arguments or {}
                
                print(f"  Selected Tool: `{t_name}`")
                print(f"  Arguments: {args}")
                if action_decision.thought:
                    print(f"  Reasoning: {action_decision.thought}")

                tools_used.append(t_name)

                # Execute tool strictly through MCP client
                tool_result = await self.mcp_client.invoke_tool(t_name, args)
                print(f"  OBSERVATION: {tool_result}")

                # Store real result as observation
                observation_tracker.add(
                    iteration=iteration,
                    tool_name=t_name,
                    arguments=args,
                    result=tool_result
                )

            elif action_decision.action == "final_answer":
                final_draft_answer = action_decision.answer or "Information processing complete."
                print(f"  FINAL DRAFT ANSWER:\n  {final_draft_answer}")
                break

        # Fallback if MAX_ITERATIONS reached without explicit final_answer
        if not final_draft_answer:
            final_draft_answer = (
                "Reached maximum iterations (5) without completing all tool steps. "
                "Current information gathered: " + observation_tracker.format_for_llm()
            )

        print("\n" + "-" * 60)
        print("REFLECTION & GROUNDING VERIFICATION:")
        
        # Step 3: Run Reflection & Verification
        reflection_result = self.evaluator.evaluate(
            draft_answer=final_draft_answer,
            observations=observation_tracker.get_all()
        )

        print(f"  GROUNDING STATUS: {reflection_result.grounding_status}")
        print(f"  SUMMARY: {reflection_result.summary}")
        if reflection_result.grounding_status == "UNSUPPORTED_CLAIMS":
            print(f"  CORRECTED ANSWER: {reflection_result.verified_answer}")
        print("=" * 60 + "\n")

        return AgentResponse(
            question=question,
            answer=reflection_result.verified_answer,
            tools_used=tools_used,
            observations=observation_tracker.get_all(),
            iterations=iterations_count,
            grounding_status=reflection_result.grounding_status,
            reflection=reflection_result.model_dump()
        )
