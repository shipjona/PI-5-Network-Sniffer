from grizzl.services.polling import poll_charger


def main() -> None:
    result = poll_charger()

    if result["status"] == "success":
        print(f"Retrieved:  {result['retrieved']}")
        print(f"Inserted:   {result['inserted']}")
        print(f"Duplicates: {result['duplicates']}")
    else:
        raise SystemExit(f"Poll failed: {result['error']}")


if __name__ == "__main__":
    main()
