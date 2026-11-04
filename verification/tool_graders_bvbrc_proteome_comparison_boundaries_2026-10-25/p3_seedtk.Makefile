TOP_DIR = ../..
DEPLOY_RUNTIME ?= /disks/patric-common/runtime
TARGET ?= /tmp/deployment
include $(TOP_DIR)/tools/Makefile.common

SERVICE_SPEC = 
SERVICE_NAME = p3_user_service
SERVICE_HOSTNAME = localhost
SERVICE_PORT = 3002
SERVICE_DIR  = $(SERVICE_NAME)
SERVICE_APP_DIR      = $(TARGET)/services/$(SERVICE_DIR)/app

PATH := $(DEPLOY_RUNTIME)/build-tools/bin:$(PATH)

CONFIG          = FIG_Config.pm
CONFIG_TEMPLATE = $(CONFIG).tt

GLOBAL_DATA = /disks/patric-common/seedtk/data
P3_DATA = /disks/patric-common/seedtk/data
CONSERVED_DOMAIN_SEARCH_URL = http://maple.mcs.anl.gov:5600
DATA_API_URL = https://www.bv-brc.org/api
#
# The site-wide default identity, landing in $FIG_Config::p3_data_api_user_agent
# and used by any client that does not declare a product of its own.
#
# It must stay in the bvbrc-* family: the agreement with the Cloudflare
# administrator is that BV-BRC traffic is identified by a bvbrc-* agent and a
# rule admits that family. The former value here, "BV-BRC P3 Client", does not
# match such a rule.
#
# This setting outranks P3ClientUA's own built-in default and is written into
# every deployment, so it -- not the module default -- is what most clients
# actually send.
#
DATA_API_USER_AGENT = bvbrc-client-perl


TPAGE_ARGS = --define kb_runas_user=$(SERVICE_USER) \
	--define kb_top=$(TARGET) \
	--define kb_runtime=$(DEPLOY_RUNTIME) \
	--define kb_service_name=$(SERVICE_NAME) \
	--define kb_service_dir=$(SERVICE_DIR) \
	--define kb_service_port=$(SERVICE_PORT) \
	--define kb_psgi=$(SERVICE_PSGI) \
	--define kb_app_dir=$(SERVICE_APP_DIR) \
	--define kb_app_script=$(APP_SCRIPT) \
	--define global_data=$(GLOBAL_DATA) \
	--define conserved_domain_search_url=$(CONSERVED_DOMAIN_SEARCH_URL) \
	--define data_api_url=$(DATA_API_URL) \
	--define "data_api_user_agent=$(DATA_API_USER_AGENT)" \
	--define p3_data=$(P3_DATA) \

default: build-config

dist: 

test: 

deploy: deploy-client deploy-service

deploy-all: deploy-client deploy-service

deploy-client: deploy-config

deploy-scripts:
	export KB_TOP=$(TARGET); \
	export KB_RUNTIME=$(DEPLOY_RUNTIME); \
	export KB_PERL_PATH=$(TARGET)/lib bash ; \
	for src in $(SRC_PERL) ; do \
		basefile=`basename $$src`; \
		base=`basename $$src .pl`; \
		echo install $$src $$base ; \
		cp $$src $(TARGET)/plbin ; \
		$(WRAP_PERL_SCRIPT) "$(TARGET)/plbin/$$basefile" $(TARGET)/bin/$$base ; \
	done

deploy-service: 

deploy-config: build-config
	mkdir -p $(TARGET)/lib
	$(TPAGE) $(TPAGE_ARGS) $(CONFIG_TEMPLATE) > $(TARGET)/lib/$(CONFIG)

build-config:
	mkdir -p lib
	$(TPAGE) $(TPAGE_ARGS) $(CONFIG_TEMPLATE) > lib/$(CONFIG)

build-libs:

include $(TOP_DIR)/tools/Makefile.common.rules
