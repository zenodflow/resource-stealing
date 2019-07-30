package main

import (
	"fmt"
	"github.com/opencontainers/runtime-spec/specs-go"
	"github.com/silveryfu/resource-lending/cgroups"
)

func createTest() {
	shares := uint64(100)
	control, err := cgroups.New(cgroups.V1, cgroups.StaticPath("/test"), &specs.LinuxResources{
		CPU: &specs.CPU{
			Shares: &shares,
		},
	})
	defer control.Delete()
}

func main() {
	control, err := cgroups.Load(cgroups.V1, cgroups.StaticPath("/cpu"))
	if err != nil {
		fmt.Println(err)
	} else {
		fmt.Println(control)
	}
}
