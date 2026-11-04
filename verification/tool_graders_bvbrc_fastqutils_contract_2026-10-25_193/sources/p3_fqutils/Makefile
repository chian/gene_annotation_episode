TOP_DIR = ../..
include $(TOP_DIR)/tools/Makefile.common

THIS_APP = $(shell basename $(shell pwd))
BUILD_VENV = $(shell pwd)/venv
TARGET_VENV = $(TARGET)/venv/$(THIS_APP)

TARGET ?= /kb/deployment
DEPLOY_RUNTIME ?= /kb/runtime

APP_SERVICE = app_service

WRAP_PYTHON_TOOL = wrap_python3
WRAP_PYTHON_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PYTHON3_TOOL).sh

SRC_PYTHON = $(wildcard scripts/*.py)

SRC_SERVICE_PERL = $(wildcard service-scripts/*.pl)
BIN_SERVICE_PERL = $(addprefix $(BIN_DIR)/,$(basename $(notdir $(SRC_SERVICE_PERL))))
DEPLOY_SERVICE_PERL = $(addprefix $(SERVICE_DIR)/bin/,$(basename $(notdir $(SRC_SERVICE_PERL))))

all: bin venv

bin: $(BIN_PYTHON) $(BIN_SERVICE_PERL)

.PHONY: venv
venv: venv/bin/python3

venv/bin/python3:
	rm -rf venv
	python3 -m venv $(BUILD_VENV)
	. $(BUILD_VENV)/bin/activate; pip3 install -r requirements.txt
	./venv-wrap.sh $(BUILD_VENV) p3x-predict-platform
	rsync -arv lib/* $(BUILD_VENV)/lib
	rsync -arv models $(BUILD_VENV)
	rm $(TOP_DIR)/bin/p3x-predict-platform
	ln -s $(BUILD_VENV)/bin/p3x-predict-platform $(TOP_DIR)/bin/p3x-predict-platform

deploy-venv:
	rm -rf $(TARGET_VENV)
	python3 -m venv $(TARGET_VENV)
	. $(TARGET_VENV)/bin/activate; pip3 install -r requirements.txt
	./venv-wrap.sh $(TARGET_VENV) p3x-predict-platform
	rsync -arv lib/* $(TARGET_VENV)/lib
	rsync -arv models $(TARGET_VENV)
	rm $(TARGET)/bin/p3x-predict-platform
	ln -s $(TARGET_VENV)/bin/p3x-predict-platform $(TARGET)/bin/p3x-predict-platform

deploy: deploy-client
deploy-all: deploy-client
deploy-client: deploy-scripts deploy-libs deploy-venv

deploy-service: deploy-libs deploy-scripts deploy-service-scripts deploy-specs

deploy-dir:
	if [ ! -d $(SERVICE_DIR) ] ; then mkdir $(SERVICE_DIR) ; fi
	if [ ! -d $(SERVICE_DIR)/bin ] ; then mkdir $(SERVICE_DIR)/bin ; fi

deploy-docs:

clean:

include $(TOP_DIR)/tools/Makefile.common.rules
