import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

public class EvenOddSeparator {

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        List<Integer> evenNumbers = new ArrayList<>();
        List<Integer> oddNumbers = new ArrayList<>();

        System.out.println("Numbers enter karein (rukne ke liye koi bhi non-integer input dein, maslan 'done'):");

        while (scanner.hasNextInt()) {
            int number = scanner.nextInt();
            if (number % 2 == 0) {
                evenNumbers.add(number);
            } else {
                oddNumbers.add(number);
            }
        }

        System.out.println("\nEven Numbers: " + evenNumbers);
        System.out.println("Odd Numbers: " + oddNumbers);

        scanner.close();
    }
}
