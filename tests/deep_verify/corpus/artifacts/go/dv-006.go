package main

// Artifact dv-006 - Synthetic test case
type Data6 struct {
    Value int
}

func Process6(data []int) int {
    sum := 0
    for _, v := range data {
        sum += v
    }
    return sum
}
