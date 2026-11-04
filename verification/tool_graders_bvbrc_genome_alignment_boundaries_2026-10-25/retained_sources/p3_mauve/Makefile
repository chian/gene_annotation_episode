TOP_DIR = ../..
DEPLOY_RUNTIME ?= /disks/patric-common/runtime
TARGET ?= /tmp/deployment
include $(TOP_DIR)/tools/Makefile.common

APP_SERVICE = app_service

SERVICE_SPEC = 
SERVICE_NAME = p3_mauve
SERVICE_DIR  = $(SERVICE_NAME)
SERVICE_APP_DIR      = $(TARGET)/lib/$(SERVICE_NAME)

SRC_SERVICE_PERL = $(wildcard service-scripts/*.pl)
BIN_SERVICE_PERL = $(addprefix $(BIN_DIR)/,$(basename $(notdir $(SRC_SERVICE_PERL))))
DEPLOY_SERVICE_PERL = $(addprefix $(SERVICE_DIR)/bin/,$(basename $(notdir $(SRC_SERVICE_PERL))))

APP_DIR = .
APP_COMPONENTS = node_modules scripts

PATH := $(DEPLOY_RUNTIME)/build-tools/bin:$(PATH)
NODE ?= $(DEPLOY_RUNTIME)/bin/node-v12
NPM ?= $(NODE) $(DEPLOY_RUNTIME)/bin/npm-v12
export NODE

DATA_API_URL = https://p3.theseed.org/services/data_api

TPAGE_BUILD_ARGS =  \
	--define kb_top=$(TARGET) \
	--define kb_runtime=$(DEPLOY_RUNTIME) 


TPAGE_DEPLOY_ARGS =  \
	--define kb_top=$(DEPLOY_TARGET) \
	--define kb_runtime=$(DEPLOY_RUNTIME) 

TPAGE_ARGS = \
	--define kb_service_name=$(SERVICE_NAME) \
	--define kb_service_dir=$(SERVICE_DIR) \
	--define kb_service_port=$(SERVICE_PORT) \
	--define kb_psgi=$(SERVICE_PSGI) \
	--define kb_app_dir=$(SERVICE_APP_DIR) \
	--define kb_app_script=$(APP_SCRIPT) \
	--define data_api_url=$(DATA_API_URL)

default: build-app $(BIN_NODEJS)

build-app: npm.completed 

npm.completed: package.json
	cd $(APP_DIR); $(NPM) install
	touch npm.completed

dist: 

test: 

deploy: deploy-client

deploy-all: deploy-client deploy-service

deploy-client: deploy-app deploy-nodejs-scripts

deploy-service: deploy-scripts deploy-service-scripts deploy-specs

deploy-app: build-app 
	-mkdir $(SERVICE_APP_DIR)
	cd $(APP_DIR); rsync --delete -ar $(APP_COMPONENTS) $(SERVICE_APP_DIR)

deploy-docs:
	-mkdir -p $(TARGET)/services/$(SERVICE_DIR)/webroot/.
	cp docs/*.html $(TARGET)/services/$(SERVICE_DIR)/webroot/.

deploy-nodejs-scripts:
	if [ "$(KB_OVERRIDE_TOP)" != "" ] ; then sbase=$(KB_OVERRIDE_TOP) ; else sbase=$(TARGET); fi; \
	export KB_TOP=$(TARGET); \
	export KB_RUNTIME=$(DEPLOY_RUNTIME); \
	for src in $(SRC_NODEJS) ; do \
		basefile=`basename $$src`; \
		base=`basename $$src .js`; \
		echo install $$src $$base ; \
		$(WRAP_NODEJS_SCRIPT) "$$sbase/lib/$(SERVICE_NAME)/scripts/$$basefile" $(TARGET)/bin/$$base ; \
	done 


build-libs:

$(BIN_DIR)/%: scripts/%.js $(TOP_DIR)/user-env.sh Makefile
	$(WRAP_NODEJS_SCRIPT) '$$KB_TOP/modules/$(CURRENT_DIR)/$<' $@


include $(TOP_DIR)/tools/Makefile.common.rules
