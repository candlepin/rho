DATE		= $(shell date)
PYTHON		= /usr/bin/python

MESSAGESPOT=po/rho.pot

TOPDIR = $(shell pwd)
DIRS	= test bin locale src
PYDIRS	= src/rho
PYFILES = $(wildcard src/rho/*.py)

BINDIR  = bin

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
	-rm -f  MANIFEST etc/version .figleaf_interesting
	-rm -rf dist/ build/ test/coverage rpm-build/
	-rm -rf *~
	-rm -rf .figleaf
	-rm -rf docs/*.gz
#	-for d in $(DIRS); do ($(MAKE) -C $$d clean ); done

confclean:
	-rm -rf ~/.rho.conf

# this is slightly nuts,we keep "versioned" copies of the conf file, just in case
confbackup:
	-cp ~/.rho.conf ./.rho.conf-backup/rho.conf-backup-`date +"%s"`

# pop the latest stored
confrestore:
	-mv ./.rho.conf-backup/`ls -t ./.rho.conf-backup/ | head -1` ~/.rho.conf


install: build
	$(PYTHON) setup.py install -f


tests:
	-nosetests -d -v -a '!slow' 

coverage:
	# figleaf needs full paths...
	# needs figleaf installed, see http://darcs.idyll.org/~t/projects/figleaf/doc/
	-rm -f .figleaf_interesting
	-for file in $(PYFILES); do echo $(TOPDIR)/$$file >> .figleaf_interesting; done
	-figleaf -i /usr/bin/nosetests -d -v -a '!slow'
	-figleaf2html -d test/coverage -f .figleaf_interesting .figleaf

sdist: messages
	$(PYTHON) setup.py sdist

pychecker:
	-for d in $(PYDIRS); do PYTHONPATH=$(TOPDIR)/src pychecker --limit 100 --only $$d/*.py;  done
	-PYTHONPATH=$(TOPDIR)/src pychecker bin/rho
pyflakes:
	-for d in $(PYDIRS); do PYTHONPATH=$(TOPDIR)/src pyflakes $$d/*.py; done
	-PYTHONPATH=$(TOPDIR)/src pyflakes bin/rho
pylint:
	-for d in $(PYDIRS); do PYTHONPATH=$(TOPDIR)/src pylint $$d/*.py; done
	-PYTHONPATH=$(TOPDIR)/src pylint bin/rho
money: clean
	-sloccount --addlang "makefile" $(TOPDIR) $(PYDIRS) 

