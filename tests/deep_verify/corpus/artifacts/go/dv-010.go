package main

// Artifact dv-010 - Synthetic test case
type Data10 struct {
    Value int
}

func Process10(data []int) int {
    sum := 0
    for _, v := range data {
        sum += v
    }
    return sum
}
