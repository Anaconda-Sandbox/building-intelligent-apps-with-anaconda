from agent_tools import (
    build_agent_context,
    load_lightcurve,
    validate_lightcurve,
    run_feature_anomaly_pipeline,
)

if __name__ == "__main__":
    data_path = "../01-data-sources/wasp18b_lightcurve.csv"
    print("Building agent context for:", data_path)

    context = build_agent_context(data_path)
    print("\nAgent context:\n")
    print(context)

    # If you want to wire this into an agent framework, register these tools:
    # - load_lightcurve
    # - validate_lightcurve
    # - run_feature_anomaly_pipeline
    # Then give the agent `context` as the initial state and let it choose the next action.
