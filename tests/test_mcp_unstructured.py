import os
import unittest
from unittest.mock import patch


class TestUnstructuredMCPTools(unittest.TestCase):
    def setUp(self) -> None:
        # Backup environment
        self._env_backup = os.environ.copy()

    def tearDown(self) -> None:
        # Restore environment
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_skips_when_api_key_missing(self):
        from deepagents.mcp_tools import get_unstructured_mcp_tools

        # Ensure envs are not set
        os.environ.pop("UNSTRUCTURED_API_KEY", None)
        os.environ.pop("UNSTRUCTURED_MCP_DIR", None)

        tools = get_unstructured_mcp_tools()
        self.assertEqual(tools, [])

    def test_skips_when_dir_missing(self):
        from deepagents.mcp_tools import get_unstructured_mcp_tools

        os.environ["UNSTRUCTURED_API_KEY"] = "dummy"
        os.environ.pop("UNSTRUCTURED_MCP_DIR", None)

        tools = get_unstructured_mcp_tools()
        self.assertEqual(tools, [])

    def test_calls_adapter_with_expected_config(self):
        import deepagents.mcp_tools as mcp_tools

        temp_dir = os.path.join(os.getcwd(), "mcp-unstructured-server")
        os.environ["UNSTRUCTURED_API_KEY"] = "dummy"
        os.environ["UNSTRUCTURED_MCP_DIR"] = temp_dir
        os.environ["UNSTRUCTURED_OUTPUT_DIR"] = "/tmp/unstructured_out"

        captured_config = {}

        def _fake_sync(server_config: dict):
            nonlocal captured_config
            captured_config = server_config
            return []

        with patch.object(mcp_tools, "_detect_python_interpreter_for_server", return_value="python"), \
             patch.object(mcp_tools, "_get_mcp_tools_sync", side_effect=_fake_sync):
            tools = mcp_tools.get_unstructured_mcp_tools()

        self.assertEqual(tools, [])
        # Validate structure
        self.assertIn("unstructured_partition", captured_config)
        cfg = captured_config["unstructured_partition"]
        self.assertEqual(cfg["transport"], "stdio")
        self.assertEqual(cfg["command"], "python")
        self.assertEqual(cfg["args"], [os.path.join(temp_dir, "doc_processor.py")])
        env = cfg["env"]
        self.assertEqual(env.get("UNSTRUCTURED_API_KEY"), "dummy")
        self.assertEqual(env.get("UNSTRUCTURED_OUTPUT_DIR"), "/tmp/unstructured_out")


if __name__ == "__main__":
    unittest.main()


