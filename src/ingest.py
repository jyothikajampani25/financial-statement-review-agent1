from __future__ import annotations

"""Optional ingest entrypoint — sample CSVs ship ready; this validates them."""

from src.store import list_companies, load_statement, available_years


def main() -> None:
    companies = list_companies()
    print(f"Companies: {len(companies)}")
    for cid, meta in companies.items():
        years = available_years(cid)
        print(f"  - {cid}: {meta['name']} years={years}")
        for year in years:
            bundle = load_statement(cid, year)
            print(f"      {year}: {len(bundle.lines)} lines loaded")
    print("Ingest check OK.")


if __name__ == "__main__":
    main()
