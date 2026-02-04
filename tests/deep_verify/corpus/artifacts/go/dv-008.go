package main

// Artifact dv-008 - Synthetic test case
type Data8 struct {
    Value int
}

func Process8(data []int) int {
    sum := 0
    for _, v := range data {
        sum += v
    }
    return sum
}
