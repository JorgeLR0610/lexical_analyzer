package main
import "fmt"

func doble(n int) int {
    return n * 2
}

func factorial(n int) int {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

func main() {
    total := 0
    for i := 0; i < 5; i++ {
        total += doble(i)
    }
    if total == 20 {
        fmt.Println(total, true)
    } else {
        fmt.Println(total, false)
    }
    fmt.Println(factorial(6))
    fmt.Println(-7 / 3, -7 % 3)
}
