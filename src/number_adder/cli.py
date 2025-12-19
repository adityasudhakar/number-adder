"""Command-line interface for number-adder."""

import argparse
from number_adder import add


def main():
    parser = argparse.ArgumentParser(description="Add two numbers")
    parser.add_argument("a", type=float, help="First number")
    parser.add_argument("b", type=float, help="Second number")
    args = parser.parse_args()

    result = add(args.a, args.b)
    print(result)


if __name__ == "__main__":
    main()
