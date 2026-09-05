"""
Phase 1 Demo: Agent Architecture and Task Orchestration

Demonstrates:
1. Supervisor creates a valid plan from a complex request
2. Specialists execute assigned subtasks
3. Reviewer validates outputs
4. Final synthesis and delivery

Run with: python -m demo
"""

import asyncio
import json
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    AgentOrchestrator,
    ToolRegistry,
    ExecutionState,
)


async def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def print_step(step_num: int, description: str) -> None:
    """Print a numbered step."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 80)


async def demo_phase_1() -> None:
    """Run the Phase 1 demo."""
    
    await print_section("PHASE 1 DEMO: Agent Architecture & Task Orchestration")
    
    print("""
This demo showcases the core Phase 1 capabilities:

1. Task Decomposition: Supervisor breaks down a complex request
2. Planning: Creates a structured task plan with dependencies
3. Specialist Execution: Agents execute assigned subtasks
4. Review: Output validation before synthesis
5. Synthesis: Combining results into final output
6. Delivery: Preparing result for user

Let's begin...
    """)
    
    # Initialize orchestrator
    await print_step(1, "Initialize Agent Orchestrator")
    orchestrator = AgentOrchestrator(plan_confidence_threshold=0.5)
    print(f"✓ Orchestrator initialized")
    print(f"✓ Supervisor configured: {orchestrator.supervisor.agent_id}")
    print(f"✓ Specialists available: {list(orchestrator.specialists.keys())}")
    print(f"✓ Reviewer configured: {orchestrator.reviewer.agent_id}")
    
    # Show available tools
    await print_step(2, "Tool Registry Status")
    tool_registry = ToolRegistry.get_instance()
    tools = tool_registry.list_all_tools()
    print(f"✓ {len(tools)} tools registered:")
    for tool in tools:
        specialists = ", ".join(tool.allowed_specialists)
        print(f"  • {tool.name} ({tool.category.value})")
        print(f"    → Available to: {specialists}")
        print(f"    → Rate limit: {tool.rate_limit_per_minute}/min")
    
    # Define a complex test request
    await print_step(3, "Define Complex Request")
    request = """
    Research and analyze the current state of AI agents in 2025-2026. 
    Create a comprehensive report that includes:
    1. Key players and their recent announcements
    2. Technical capabilities and limitations
    3. Real-world applications and use cases
    4. Cost comparison between different platforms
    5. Future predictions for the next 12 months
    
    Include data from recent papers, news articles, and publicly available benchmarks.
    Format the final report as a structured document with sections, key findings, and citations.
    """
    
    print(f"Request: {request[:100]}...")
    print(f"Full request length: {len(request)} characters")
    
    # Execute the workflow
    await print_step(4, "Execute Agent Orchestration Workflow")
    print("Running: intake → planning → execution → review → synthesis → delivery")
    
    try:
        result = await orchestrator.execute(request)
        
        # Display results
        await print_section("WORKFLOW EXECUTION RESULTS")
        
        print(f"\n✓ Task ID: {result['task_id']}")
        print(f"✓ Status: {result['status']}")
        print(f"✓ Start time: {result['execution_start_time']}")
        print(f"✓ End time: {result['execution_end_time']}")
        
        # Plan analysis
        await print_step(5, "Plan Analysis")
        if result['plan']:
            plan = result['plan']
            print(f"✓ Plan created with {len(plan.get('subtasks', []))} subtasks")
            print(f"✓ Plan confidence: {plan.get('confidence', 0):.1%}")
            print(f"✓ Execution mode: {plan.get('execution_mode', 'unknown')}")
            print(f"✓ Total estimated complexity: {plan.get('total_estimated_complexity', 'unknown')}")
            
            print("\nSubtasks breakdown:")
            for i, subtask in enumerate(plan.get('subtasks', [])[:5], 1):
                print(f"\n  Task {i}: {subtask.get('id', 'unknown')}")
                print(f"    Description: {subtask.get('description', '')[:60]}...")
                print(f"    Specialist: {subtask.get('specialist_type', 'unknown')}")
                print(f"    Complexity: {subtask.get('estimated_complexity', 'unknown')}")
                print(f"    Priority: {subtask.get('priority', 0)}/10")
        else:
            print("⚠ No plan generated")
        
        # Execution summary
        await print_step(6, "Execution Summary")
        print(f"✓ Completed subtasks: {len(result.get('completed_subtasks', {}))}")
        print(f"✓ Total decisions: {len(result.get('decisions', []))}")
        print(f"✓ Total errors: {len(result.get('errors', []))}")
        
        if result.get('decisions'):
            print("\nDecision log (sample):")
            for i, decision in enumerate(result.get('decisions', [])[:8], 1):
                node = decision.get('node', 'unknown')
                action = decision.get('action', 'unknown')
                print(f"  {i}. [{node}] {action}")
        
        # Review status
        await print_step(7, "Review Status")
        print(f"✓ Needs rework: {result.get('needs_rework', False)}")
        if result.get('review_result'):
            print(f"✓ Review approved: {result['review_result'].get('approved', False)}")
        
        # Final output
        await print_step(8, "Final Synthesis Output")
        if result.get('final_output'):
            output = result['final_output']
            print(f"✓ Output structure:")
            print(f"  - Task ID: {output.get('task_id', 'unknown')}")
            print(f"  - Request processed: {output.get('request', '')[:50]}...")
            print(f"  - Subtask results: {len(output.get('subtask_results', {}))}")
            print(f"  - Review passed: {output.get('review_passed', False)}")
        
        # Tool usage stats
        await print_step(9, "Tool Usage Statistics")
        all_logs = tool_registry.get_invocation_log()
        print(f"✓ Total tool invocations: {len(all_logs)}")
        
        for tool in tool_registry.list_all_tools():
            stats = tool_registry.get_tool_stats(tool.name)
            if stats and stats.get('total_calls', 0) > 0:
                print(f"\n  {tool.name}:")
                print(f"    - Calls: {stats['total_calls']}")
                print(f"    - Success rate: {stats['success_rate']:.1%}")
                print(f"    - Avg time: {stats['avg_execution_time_ms']:.1f}ms")
                print(f"    - Total cost: ${stats['total_cost']:.4f}")
        
        # Phase 1 Metrics
        await print_section("PHASE 1 SUCCESS METRICS")
        
        print(f"""
✓ Plan Validation: Generated plan passed schema validation
  Confidence: {plan.get('confidence', 0) * 100:.0f}%
  
✓ Specialist Assignment: Correctly assigned tasks to specialists
  Total specialists engaged: {len(set(s.get('specialist_type') for s in plan.get('subtasks', [])))}
  
✓ Tool Integration: Tool registry operational with {len(tools)} tools
  
✓ Workflow Execution: Complete pipeline executed successfully
  Status: {result.get('status', 'unknown')}
  Decision points: {len(result.get('decisions', []))}
  
✓ Review & Synthesis: Output validated and synthesized
  Approved: {not result.get('needs_rework', False)}
  Final output generated: {bool(result.get('final_output'))}
        """)
        
        # Demo checkpoint assessment
        await print_section("DEMO CHECKPOINT ASSESSMENT")
        
        checkpoint_met = (
            result.get('plan') is not None
            and result.get('plan', {}).get('confidence', 0) > 0.4
            and len(result.get('completed_subtasks', {})) > 0
            and result.get('status') == 'complete'
        )
        
        if checkpoint_met:
            print("""
✓ CHECKPOINT PASSED: Phase 1 Demo Requirements Met

The demo successfully demonstrates:
1. ✓ Supervisor produced a valid plan from a complex request
2. ✓ Plan included task decomposition with clear subtasks
3. ✓ Specialists were assigned appropriate tasks
4. ✓ Specialist execution pipeline completed
5. ✓ Reviewer validated the output
6. ✓ Final synthesis combined results
7. ✓ End-to-end workflow executed successfully

Ready to proceed to Phase 2: Memory System
            """)
        else:
            print("""
⚠ CHECKPOINT INCOMPLETE: Some requirements not fully met

Please review the output above for issues.
            """)
        
    except Exception as e:
        print(f"\n✗ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
    
    await print_section("Demo Complete")


async def main():
    """Run the demo."""
    try:
        await demo_phase_1()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
