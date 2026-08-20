import argparse

from agents.diagnostic_agent import run_diagnostic_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only incident investigation")
    parser.add_argument("service", help="Affected service name")
    parser.add_argument("alert", help="Alert message including its timestamp")
    args = parser.parse_args()
    result = run_diagnostic_agent(args.service, args.alert)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
