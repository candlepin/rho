DATE		= $(shell date)
PYTHON		= /usr/bin/python

MESSAGESPOT=po/rho.pot

TOPDIR = $(shell pwd)
DIRS	= test bin locale src
PYDIRS	= src bin 

#MANPAGES = funcd func func-inventory func-transmit func-build-map func-create-module

all: build

versionfile:
	echo "version:" $(VERSION) > etc/version
	echo "release:" $(RELEASE) >> etc/version
	echo "source build date:" $(DATE) >> etc/version
	echo "git commit:" $(shell git log -n 1 --pretty="format:%H") >> etc/version
	echo "git date:" $(shell git log -n 1 --pretty="format:%cd") >> etc/version

#	echo $(shell git log -n 1 --pretty="format:git commit: %H from \(%cd\)") >> etc/version 
#manpage:
#	for manpage in $(MANPAGES); do (pod2man --center=$$manpage --release="" ./docs/$$manpage.pod | gzip -c > ./docs/$$manpage.1.gz); done

build: clean versionfile
	$(PYTHON) setup.py build -f

clean:
	-rm -f  MANIFEST
	-rm -rf dist/ build/
	-rm -rf *~
	-rm -rf rpm-build/
	-rm -rf docs/*.gz
	-rm -f etc/version
#	-for d in $(DIRS); do ($(MAKE) -C $$d clean ); done


install: build
	$(PYTHON) setup.py install -f

install_rpm:
	-rpm -Uvh rpm-build/func-$(VERSION)-$(RELEASE)$(shell rpm -E "%{?dist}").noarch.rpm

clean_rpms:
	-rpm -e rho

sdist: messages
	$(PYTHON) setup.py sdist

pychecker:
	-for d in $(PYDIRS); do ($(MAKE) -C $$d pychecker ); done   
pyflakes:
	-for d in $(PYDIRS); do ($(MAKE) -C $$d pyflakes ); done	
money: clean
	-sloccount --addlang "makefile" $(TOPDIR) $(PYDIRS) 

rpms: build sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba func.spec
