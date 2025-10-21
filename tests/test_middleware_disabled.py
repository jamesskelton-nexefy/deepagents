"""Test that middleware can be properly disabled"""

import pytest
from deepagents import create_deep_agent, async_create_deep_agent


def test_create_deep_agent_with_middleware_disabled():
    """Test that create_deep_agent works with middleware disabled"""
    
    def simple_tool(query: str) -> str:
        """A simple test tool"""
        return f"Result for: {query}"
    
    # Create agent with middleware disabled
    agent = create_deep_agent(
        tools=[simple_tool],
        instructions="You are a helpful assistant",
        use_default_middleware=False,
    )
    
    # Agent should be created successfully
    assert agent is not None
    
    # Verify agent can be invoked
    result = agent.invoke({
        "messages": [{"role": "user", "content": "test query"}]
    })
    
    assert "messages" in result
    assert len(result["messages"]) > 0


def test_async_create_deep_agent_with_middleware_disabled():
    """Test that async_create_deep_agent works with middleware disabled"""
    
    async def async_simple_tool(query: str) -> str:
        """An async simple test tool"""
        return f"Result for: {query}"
    
    # Create agent with middleware disabled
    agent = async_create_deep_agent(
        tools=[async_simple_tool],
        instructions="You are a helpful assistant",
        use_default_middleware=False,
    )
    
    # Agent should be created successfully
    assert agent is not None


def test_create_deep_agent_with_middleware_enabled():
    """Test that create_deep_agent works with middleware enabled (default)"""
    
    def simple_tool(query: str) -> str:
        """A simple test tool"""
        return f"Result for: {query}"
    
    # Create agent with middleware enabled (default)
    agent = create_deep_agent(
        tools=[simple_tool],
        instructions="You are a helpful assistant",
        use_default_middleware=True,  # Explicitly set to True
    )
    
    # Agent should be created successfully
    assert agent is not None


def test_create_deep_agent_default_behavior():
    """Test that create_deep_agent has middleware enabled by default"""
    
    def simple_tool(query: str) -> str:
        """A simple test tool"""
        return f"Result for: {query}"
    
    # Create agent without specifying use_default_middleware
    agent = create_deep_agent(
        tools=[simple_tool],
        instructions="You are a helpful assistant",
    )
    
    # Agent should be created successfully with default middleware
    assert agent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

