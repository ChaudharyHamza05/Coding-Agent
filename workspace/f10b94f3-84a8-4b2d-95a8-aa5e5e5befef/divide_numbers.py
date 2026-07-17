def divide(a, b):
    if b == 0:
        return 0  # Ye ghalti hai, yahan ZeroDivisionError raise honi chahiye
    return a / b

print(f"10 / 2 = {divide(10, 2)}")
print(f"5 / 0 = {divide(5, 0)}") # Yahan ghalti nazar aayegi
print(f"100 / 10 = {divide(100, 10)}")
