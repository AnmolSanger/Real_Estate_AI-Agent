from cities import INDIAN_CITIES, is_supported, to_location
from pipeline import run_analysis
from schemas import PROPERTY_TYPES


def run():
    print("\n--- EstateMind ---\n")
    state = input("Enter the state (e.g., Maharashtra, Karnataka): ").strip()
    if state not in INDIAN_CITIES:
        print("Unsupported state. Choose one of:\n" + ", ".join(INDIAN_CITIES))
        return

    city = input("Enter the city (e.g., Pune): ").strip()
    if not is_supported(state, city):
        print(f"Unsupported city. Cities in {state}:\n" + ", ".join(INDIAN_CITIES[state]))
        return

    property_type = input("Enter the property type (" + ", ".join(PROPERTY_TYPES) + "): ").strip()
    if property_type not in PROPERTY_TYPES:
        print("Unsupported property type.")
        return

    print(f"\nAnalyzing {property_type} properties in {city}, {state}...\n")

    result = run_analysis(to_location(state, city), property_type)

    print("\n--- Final Investment Report ---\n")
    print(result.markdown)

    with open("investment_report.txt", "w", encoding="utf-8") as report_file:
        report_file.write(result.markdown)
    print("\nReport saved to investment_report.txt")


if __name__ == "__main__":
    run()
