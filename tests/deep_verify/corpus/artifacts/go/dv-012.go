package main

// Artifact dv-012 - Synthetic test case
type Data12 struct {
    Value int
}

func Process12(data []int) int {
    sum := 0
    for _, v := range data {
        sum += v
    }
    return sum
}
