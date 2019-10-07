package main

import (
	"fmt"
	"github.com/silveryfu/resource-lending/steal"
)

func main() {
	// e2e testing
	tk, err := steal.NewTracker()
	if err != nil {
		fmt.Println(err)
		return
	}

	// steal
	if err := tk.Steal([]string{"system.slice", "docker.service"}, []string{"user.slice"}, 100); err != nil {
		fmt.Println(err)
	}

	// return
	if err := tk.Steal([]string{"user.slice"}, []string{"system.slice", "docker.service"}, 100); err != nil {
		fmt.Println(err)
	}
}
