from tools.browser_tool import BROWSER_TOOL_SCHEMAS


def test_batch_tool_exposes_semantic_selection_postcondition():
    tool = next(item for item in BROWSER_TOOL_SCHEMAS if item["name"] == "browser_batch_actions")
    properties = tool["parameters"]["properties"]["steps"]["items"]["properties"]
    assert properties["postcondition"]["properties"]["kind"]["enum"] == ["selected"]
    assert "ref" in properties

