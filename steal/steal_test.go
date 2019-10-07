package steal

import (
	"fmt"
	"testing"
)

func BenchmarkSteal(b *testing.B) {
	// TODO:
}

func TestTrackerUnify(t *testing.T) {
	// TODO:
	tk, err := NewTracker()
	if err != nil {
		fmt.Println(err)
		return
	}

	if err := tk.Unify(); err != nil {
		fmt.Println(err)
	}
}