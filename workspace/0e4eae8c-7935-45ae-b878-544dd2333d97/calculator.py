def add(a, b):
    """Returns the sum of a and b."""
    return a + b


def subtract(a, b):
    """Returns the difference when b is subtracted from a."""
    return a - b


def multiply(a, b):
    """Returns the product of a and b."""
    return a * b


def main():
    """Gets user input, performs calculation, and prints the result."""
    try:
        num1 = float(input("Enter first number: "))
        num2 = float(input("Enter second number: "))
        operator = input("Enter operator (+, -, *): ").strip()

        if operator == "+":
            result = add(num1, num2)
        elif operator == "-":
            result = subtract(num1, num2)
        elif operator == "*":
            result = multiply(num1, num2)
        else:
            print(f"Invalid operator '{operator}'. Please use +, -, or *.")
            return

        print(f"{num1} {operator} {num2} = {result}")

    except ValueError:
        print("Invalid input. Please enter numeric values for numbers.")


if __name__ == "__main__":
    main()
