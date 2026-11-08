package main

func ejecutar() int {
	var a int = 5
	var b int = 10
	var t1 int = a + b
	var t2 int = a + b

	var x int

	if t1 > 10 {
		x = 1
	} else {
		x = 0
	}

	var y int = x
	var z int = 20 + 30
	var w int = 100
	
	return y

	// Código inalcanzable
	w = 200
}

func main() {
	ejecutar()
}
