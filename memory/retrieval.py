"""
Memory retrieval and injection for planning.

Retrieves relevant past experiences and injects them into
the supervisor's planning prompt to improve decision-making.
"""

from typing import Any, Optional, Dict, List
from .long_term import LongTermMemory
from datetime import datetime


class MemoryRetriever:
    """
    Retrieves relevant memories and formats them for injection
    into the supervisor's planning prompt.
    """
    
    def __init__(self, long_term_memory: LongTermMemory):
        """
        Initialize retriever.
        
        Args:
            long_term_memory: LongTermMemory instance
        """
        self.memory = long_term_memory
    
    async def retrieve_relevant_context(
        self,
        request: str,
        user_id: Optional[str] = None,
        n_memories: int = 3,
        min_relevance: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memories for a request.
        
        Args:
            request: The new task request
            user_id: Optional user identifier for filtering
            n_memories: Number of memories to retrieve
            min_relevance: Minimum relevance threshold
            
        Returns:
            Dict with retrieved memories and formatting
        """
        # Query for similar memories
        memories = await self.memory.retrieve_similar_memories(
            query=request,
            n_results=n_memories,
            min_relevance=min_relevance,
        )
        
        # Extract insights from memories
        insights = self._extract_insights(memories)
        
        return {
            "memories_found": len(memories),
            "retrieved_memories": memories,
            "insights": insights,
            "recommendation": self._generate_recommendation(memories),
        }
    
    def _extract_insights(self, memories: List[Dict]) -> List[str]:
        """Extract key insights from retrieved memories."""
        insights = []
        
        for memory in memories:
            metadata = memory.get("metadata", {})
            text = memory.get("text", "")
            
            # Extract domain facts and tool usage
            if "Tools:" in text:
                tools_part = text.split("Tools:")[1].split("\n")[0]
                insights.append(f"Previously used tools: {tools_part.strip()}")
            
            if "Facts:" in text:
                facts_part = text.split("Facts:")[1].split("\n")[0]
                if facts_part.strip():
                    insights.append(f"Relevant fact: {facts_part.strip()}")
            
            success = metadata.get("success_score", 0)
            if success > 0.8:
                insights.append(f"This approach worked well (confidence: {success:.0%})")
            elif success < 0.4:
                insights.append(f"⚠ This approach had issues (confidence: {success:.0%})")
        
        return insights
    
    def _generate_recommendation(self, memories: List[Dict]) -> str:
        """Generate a recommendation based on retrieved memories."""
        if not memories:
            return "No relevant past experience found. Create a new plan."
        
        best_memory = memories[0]
        relevance = best_memory.get("relevance", 0)
        success = best_memory.get("metadata", {}).get("success_score", 0)
        
        if relevance > 0.8 and success > 0.8:
            return "Strong similarity to a successful past task. Consider reusing the previous approach."
        elif relevance > 0.6 and success > 0.6:
            return "Moderate similarity to a previous task. Use learnings but adapt for current request."
        else:
            return "Some similarity to past approaches. Use as reference but create adapted plan."
    
    def format_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format retrieved memories for injection into planning prompt.
        
        Args:
            context: Retrieved context from retrieve_relevant_context
            
        Returns:
            Formatted string for prompt injection
        """
        if context["memories_found"] == 0:
            return "\n# PAST EXPERIENCE\nNo relevant past experience available."
        
        prompt_text = "\n# PAST EXPERIENCE\n"
        prompt_text += f"Found {context['memories_found']} similar task(s) from history.\n\n"
        
        for i, memory in enumerate(context["retrieved_memories"], 1):
            relevance = memory.get("relevance", 0)
            metadata = memory.get("metadata", {})
            text = memory.get("text", "")
            
            prompt_text += f"## Similar Task #{i} (Relevance: {relevance:.0%})\n"
            prompt_text += f"Request: {metadata.get('request_preview', 'N/A')}\n"
            prompt_text += f"Success: {metadata.get('success_score', 0):.0%}\n"
            prompt_text += f"Cost: ${metadata.get('cost', 0):.2f}\n"
            prompt_text += f"Insights: {text[:200]}...\n\n"
        
        prompt_text += "## Recommendation\n"
        prompt_text += context["recommendation"] + "\n"
        
        if context["insights"]:
            prompt_text += "\n## Key Learnings\n"
            for insight in context["insights"]:
                prompt_text += f"• {insight}\n"
        
        return prompt_text


class PlanningWithMemory:
    """
    Supervisor planning enhanced with memory injection.
    
    Wraps the decomposition engine to inject relevant
    past experience into the planning prompt.
    """
    
    def __init__(
        self,
        decomposition_engine: Any,
        memory_retriever: MemoryRetriever,
    ):
        """
        Initialize planning with memory.
        
        Args:
            decomposition_engine: TaskDecompositionEngine instance
            memory_retriever: MemoryRetriever instance
        """
        self.decomposition_engine = decomposition_engine
        self.retriever = memory_retriever
    
    async def decompose_with_memory(
        self,
        request: str,
        context_facts: Optional[Dict] = None,
        retrieve_memory: bool = True,
    ) -> Dict[str, Any]:
        """
        Decompose a request with memory-enhanced planning.
        
        Args:
            request: Task request
            context_facts: Optional context
            retrieve_memory: Whether to retrieve and inject past memories
            
        Returns:
            Task plan
        """
        # Retrieve relevant memories
        memory_context = None
        if retrieve_memory:
            memory_context = await self.retriever.retrieve_relevant_context(
                request=request,
                n_memories=3,
                min_relevance=0.5,
            )
        
        # Decompose with or without memory
        if memory_context and memory_context["memories_found"] > 0:
            # Inject memory into planning
            enhanced_context = context_facts or {}
            enhanced_context["past_experience"] = memory_context
            
            # Add memory-aware prompt
            memory_prompt = self.retriever.format_for_prompt(memory_context)
            enhanced_context["memory_injection"] = memory_prompt
        else:
            enhanced_context = context_facts
        
        # Run decomposition
        plan = await self.decomposition_engine.decompose(request, context_facts=enhanced_context)
        
        # Track whether memory was used
        plan["memory_context"] = memory_context
        plan["memory_was_used"] = memory_context is not None and memory_context["memories_found"] > 0
        
        return plan
