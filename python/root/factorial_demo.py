from typing import Union

def factorial(n: int) -> Union[int, str]:
    """
    Calculates the factorial of a given number using recursion.

    Parameters:
        n (int): The number for which to calculate the factorial.

    Returns:
        int: The factorial of the input number if it's positive and non-zero, otherwise returns an error message as a string.

    Raises:
        ValueError: When the input number is negative or zero.
    """
    if n < 0:
        raise ValueError("Input must be a non-negative integer.")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

if __name__ == "__main__":
    for num in range(1, 11):
        try:
            result = factorial(num)
            print(f"Factorial of {num}: {result}")
        except ValueError as e:
            print(e)