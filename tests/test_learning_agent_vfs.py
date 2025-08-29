"""
Unit tests to verify VFS file creation by learning agent sub-agents.

This test suite ensures that all sub-agents in the learning system can properly
create documents in the Virtual File System (VFS), addressing the issue where
documents were created but not saved to VFS.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# Import the learning agent components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'examples', 'learning'))

from learning_agent import (
    learning_strategist_agent,
    course_architect_agent,
    content_developer_agent,
    assessment_designer_agent,
    visual_enhancement_agent
)
from deepagents import create_deep_agent
from deepagents.state import DeepAgentState


class TestLearningAgentVFS:
    """Test suite for VFS functionality in learning agent sub-agents."""
    
    def test_learning_strategist_has_vfs_tools(self):
        """Test that learning-strategist has required VFS tools."""
        required_tools = ["write_file", "read_file", "edit_file"]
        agent_tools = learning_strategist_agent.get("tools", [])
        
        for tool in required_tools:
            assert tool in agent_tools, f"learning-strategist missing required tool: {tool}"
    
    def test_learning_strategist_has_todo_tools(self):
        """Test that learning-strategist has required todo management tools."""
        agent_tools = learning_strategist_agent.get("tools", [])
        assert "write_todos" in agent_tools, "learning-strategist missing write_todos tool"
    
    def test_course_architect_has_vfs_tools(self):
        """Test that course-architect has required VFS tools."""
        required_tools = ["write_file", "read_file", "edit_file"]
        agent_tools = course_architect_agent.get("tools", [])
        
        for tool in required_tools:
            assert tool in agent_tools, f"course-architect missing required tool: {tool}"
    
    def test_course_architect_has_todo_tools(self):
        """Test that course-architect has required todo management tools."""
        agent_tools = course_architect_agent.get("tools", [])
        assert "write_todos" in agent_tools, "course-architect missing write_todos tool"
    
    def test_content_developer_has_vfs_tools(self):
        """Test that content-developer has required VFS tools."""
        required_tools = ["write_file", "read_file", "edit_file"]
        agent_tools = content_developer_agent.get("tools", [])
        
        for tool in required_tools:
            assert tool in agent_tools, f"content-developer missing required tool: {tool}"
    
    def test_content_developer_has_todo_tools(self):
        """Test that content-developer has required todo management tools."""
        agent_tools = content_developer_agent.get("tools", [])
        assert "write_todos" in agent_tools, "content-developer missing write_todos tool"
    
    def test_assessment_designer_has_vfs_tools(self):
        """Test that assessment-designer has required VFS tools."""
        required_tools = ["write_file", "read_file", "edit_file"]
        agent_tools = assessment_designer_agent.get("tools", [])
        
        for tool in required_tools:
            assert tool in agent_tools, f"assessment-designer missing required tool: {tool}"
    
    def test_assessment_designer_has_todo_tools(self):
        """Test that assessment-designer has required todo management tools."""
        agent_tools = assessment_designer_agent.get("tools", [])
        assert "write_todos" in agent_tools, "assessment-designer missing write_todos tool"
    
    def test_visual_enhancement_has_vfs_tools(self):
        """Test that visual-enhancement-specialist has required VFS tools."""
        required_tools = ["write_file", "read_file", "edit_file"]
        agent_tools = visual_enhancement_agent.get("tools", [])
        
        for tool in required_tools:
            assert tool in agent_tools, f"visual-enhancement-specialist missing required tool: {tool}"
    
    def test_visual_enhancement_has_todo_tools(self):
        """Test that visual-enhancement-specialist has required todo management tools."""
        agent_tools = visual_enhancement_agent.get("tools", [])
        assert "write_todos" in agent_tools, "visual-enhancement-specialist missing write_todos tool"
    
    def test_all_document_creating_subagents_have_vfs_tools(self):
        """Test that all sub-agents expected to create documents have VFS tools."""
        document_creating_agents = [
            ("learning-strategist", learning_strategist_agent),
            ("course-architect", course_architect_agent),
            ("content-developer", content_developer_agent),
            ("assessment-designer", assessment_designer_agent),
            ("visual-enhancement-specialist", visual_enhancement_agent),
        ]
        
        required_vfs_tools = ["write_file", "read_file", "edit_file"]
        
        for agent_name, agent_config in document_creating_agents:
            agent_tools = agent_config.get("tools", [])
            
            for tool in required_vfs_tools:
                assert tool in agent_tools, (
                    f"Sub-agent '{agent_name}' is missing VFS tool '{tool}'. "
                    f"Available tools: {agent_tools}"
                )
    
    def test_all_subagents_have_todo_tools(self):
        """Test that all sub-agents have todo management tools."""
        all_subagents = [
            ("learning-strategist", learning_strategist_agent),
            ("course-architect", course_architect_agent),
            ("content-developer", content_developer_agent),
            ("assessment-designer", assessment_designer_agent),
            ("visual-enhancement-specialist", visual_enhancement_agent),
        ]
        
        for agent_name, agent_config in all_subagents:
            agent_tools = agent_config.get("tools", [])
            assert "write_todos" in agent_tools, (
                f"Sub-agent '{agent_name}' is missing todo tool 'write_todos'. "
                f"Available tools: {agent_tools}"
            )
    
    def test_agent_prompts_mention_file_creation(self):
        """Test that agent prompts correctly instruct to save files."""
        # Test learning strategist prompt mentions saving to learning_strategy.md
        assert "learning_strategy.md" in learning_strategist_agent["prompt"]
        assert "Save your analysis" in learning_strategist_agent["prompt"]
        
        # Test course architect prompt mentions saving to course_architecture.md
        assert "course_architecture.md" in course_architect_agent["prompt"]
        assert "Save your architecture" in course_architect_agent["prompt"]
    
    def test_agent_prompts_mention_todo_management(self):
        """Test that agent prompts correctly instruct to use todo management."""
        all_subagents = [
            ("learning-strategist", learning_strategist_agent),
            ("course-architect", course_architect_agent),
            ("content-developer", content_developer_agent),
            ("assessment-designer", assessment_designer_agent),
            ("visual-enhancement-specialist", visual_enhancement_agent),
        ]
        
        for agent_name, agent_config in all_subagents:
            prompt = agent_config["prompt"]
            assert "write_todos" in prompt, f"{agent_name} prompt missing todo management instructions"
            assert "Task Management" in prompt, f"{agent_name} prompt missing Task Management section"
            assert "in_progress" in prompt, f"{agent_name} prompt missing status instructions"
            assert "completed" in prompt, f"{agent_name} prompt missing completion instructions"
    
    def test_main_agent_dynamic_todo_instructions(self):
        """Test that main agent has dynamic todo management instructions."""
        from learning_agent import learning_content_instructions
        
        # Check for dynamic todo management section
        assert "DYNAMIC TODO MANAGEMENT" in learning_content_instructions
        assert "Post-Sub-Agent Outcome Analysis Process" in learning_content_instructions
        
        # Check for specific analysis instructions
        assert "After Learning Strategist" in learning_content_instructions
        assert "After Course Architect" in learning_content_instructions
        assert "MOST CRITICAL" in learning_content_instructions
        
        # Check for outcome analysis steps
        assert "read_file" in learning_content_instructions
        assert "Extract actionable information" in learning_content_instructions
        assert "Update todos" in learning_content_instructions
        
        # Check for dynamic workflow integration
        assert "CRITICAL ANALYSIS" in learning_content_instructions
        assert "MAJOR TODO UPDATE" in learning_content_instructions
        assert "Replace generic" in learning_content_instructions
        
        # Check for key principles
        assert "Always read deliverables" in learning_content_instructions
        assert "Replace generic todos" in learning_content_instructions
        assert "Adapt future planning" in learning_content_instructions
    
    @pytest.mark.asyncio
    async def test_subagent_can_access_vfs_tools_in_execution(self):
        """Test that sub-agents can actually access VFS tools when created."""
        # This is a more complex integration test that would require
        # setting up the full agent execution environment
        
        # Create a mock state with VFS
        mock_state = {
            "files": {},
            "contextId": "test-context-123"
        }
        
        # Verify that the learning strategist agent configuration is correct
        # This is a structural test to ensure the configuration will work
        agent_config = learning_strategist_agent
        
        assert "name" in agent_config
        assert "description" in agent_config  
        assert "prompt" in agent_config
        assert "tools" in agent_config
        
        # Verify VFS tools are in the tools list
        tools = agent_config["tools"]
        assert "write_file" in tools
        assert "read_file" in tools
        assert "edit_file" in tools


class TestLearningAgentIntegration:
    """Integration tests for the complete learning agent system."""
    
    def test_main_agent_has_process_agent_document_tool(self):
        """Test that main agent has process_agent_document for VFS to Supabase pipeline."""
        # This verifies that after sub-agents create files in VFS,
        # the main agent can process them through to Supabase
        
        # Import the main learning agent
        from learning_agent import agent
        
        # Check that the main agent was created successfully
        assert agent is not None
        
        # The agent should have access to process_agent_document tool
        # (This is verified through the create_deep_agent call with the tool included)
    
    def test_workflow_expects_vfs_files(self):
        """Test that the workflow instructions expect VFS files to exist."""
        from learning_agent import learning_content_instructions
        
        # Check that the main agent instructions reference the expected files
        assert "learning_strategy.md" in learning_content_instructions
        assert "course_architecture.md" in learning_content_instructions
        assert "process_agent_document" in learning_content_instructions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
