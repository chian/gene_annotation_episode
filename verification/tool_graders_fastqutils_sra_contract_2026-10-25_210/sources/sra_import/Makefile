TOP_DIR = ../..
include $(TOP_DIR)/tools/Makefile.common

TARGET ?= /kb/deployment
DEPLOY_RUNTIME ?= /kb/runtime

WRAP_PYTHON_TOOL = wrap_python3
WRAP_PYTHON_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PYTHON3_TOOL).sh

SRC_PYTHON = $(wildcard scripts/*.py)

all: bin 

bin: $(BIN_PYTHON)

deploy: deploy-client 
deploy-all: deploy-client 
deploy-client: deploy-scripts deploy-libs

include $(TOP_DIR)/tools/Makefile.common.rules
