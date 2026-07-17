from calculator import add, subtract, multiply

def main():
    try:
        num1 = float(input("Enter first number: "))
        num2 = float(input("Dusra number enter karein: "))
        operation = input("Operation choose karein (+, -, *): ")

        if operation == '+':
            result = add(num1, num2)
            print(f"Result: {num1} + {num2} = {result}")
        elif operation == '-':
            result = subtract(num1, num2)
            print(f"Result: {num1} - {num2} = {result}")
        elif operation == '*':
            result = multiply(num1, num2)
            print(f"Result: {num1} * {num2} = {result}")
        else:
            print("Invalid operation. Please choose from +, -, *.")
    except ValueError:
        print("Invalid input. Please enter numbers only.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
