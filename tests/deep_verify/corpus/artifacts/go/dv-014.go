package main

// Artifact dv-014 - Synthetic test case
type Data14 struct {
    Value int
}

func Process14(data []int) int {
    sum := 0
    for _, v := range data {
        sum += v
    }
    return sum
}
