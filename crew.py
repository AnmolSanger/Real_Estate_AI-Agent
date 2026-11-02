from pipeline import run_analysis


def run():
    print("\n--- Real Estate Investment AI Agent ---\n")
    location = input("Enter the location to analyze (e.g., Mumbai, Berlin, New York): ").strip()
    property_type = input("Enter the property type (e.g., retail, residential, commercial): ").strip()

    if not location or not property_type:
        print("Both location and property type are required.")
        return

    print(f"\nAnalyzing {property_type} properties in {location}...\n")

    report = run_analysis(location, property_type)

    print("\n--- Final Investment Report ---\n")
    print(report)

    with open("investment_report.txt", "w", encoding="utf-8") as report_file:
        report_file.write(report)
    print("\nReport saved to investment_report.txt")


if __name__ == "__main__":
    run()
