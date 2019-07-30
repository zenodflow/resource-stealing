SHELL := /bin/bash
THIS_VER := v0.1.0

# Extra environment variables
.EXPORT_ALL_VARIABLES:
OUT_DIR ?= _output
BIN_DIR := $(OUT_DIR)/bin
RELEASE_DIR := $(OUT_DIR)/$(THIS_VER)
# TODO
BINARY := lend
# TODO
CMD_ENTRY := lend.go


VERBOSE ?= 1

clean: @rm -r $(OUT_DIR) || true

# Build and test cli
.PHONY: cli

cli:
# TODO
	go build -o $(BIN_DIR)/$(BINARY) ./

install: | cli
	cp $(BIN_DIR)/$(BINARY) /usr/local/bin

# create test clusters
.PHONY: ec2, delete-ec2

ec2:
	cd ./hack/ec2; REGION=$(REGION); python3 -m build.kube.cluster up

show-ec2:
	cd ./hack/ec2; bash ./get_clusters.sh

delete-ec2:
	# TODO: make this directly use env variable
	cd ./hack/ec2; python3 -m build.kube.gen_spec $(CLUSTERID); python3 -m build.kube.cluster down
