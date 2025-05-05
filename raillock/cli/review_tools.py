def review_tools(client):
    """Review and display available tools."""
    import sys
    import traceback
    from raillock.exceptions import RailLockError

    try:
        print("[DEBUG] Validating tools...")
        tools = client.validate_tools()
        print(f"[DEBUG] Tools after validation: {tools}")
        if not tools:
            print("No tools available or all tools were filtered out.")
            return
        print("\nAvailable tools:")
        for tool_name, tool_data in tools.items():
            print(f"\n{tool_name}:")
            print(f"  Description: {tool_data['description']}")
            print(f"  Checksum: {tool_data['checksum']}")
    except RailLockError as e:
        print(f"Error reviewing tools: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"[DEBUG] Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
